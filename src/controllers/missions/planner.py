from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ...models.node import Node

class MissionPlanner:
    def __init__(self, node_controller, transport_controller, logger):
        self.node_controller = node_controller
        self.transport_controller = transport_controller
        self.logger = logger
        self.time_slots = {
            "airbase": ["06:00", "18:00"],
            "FOB": ["10:00", "14:00"],
            "COP": ["12:00"]
        }

    def create_missions(self, forecast: Dict, start_date: datetime, 
                       cycle: int) -> List[Dict]:
        """Create new missions based on forecast"""
        # Calculate priorities
        priorities = self._calculate_priorities(forecast)
        
        # Create optimal schedule
        return self._optimize_schedule(priorities, forecast, start_date, cycle)

    def _calculate_priorities(self, forecast: Dict) -> List:
        """Calculate priorities based on resource forecast"""
        priorities = []
        
        for node in self.node_controller.get_all_nodes():
            for resource in ["fuel", "ammo"]:
                resource_days = forecast[node.name][resource]["daily"]
                
                # Find critical point
                days_until_critical = 7
                for i, day in enumerate(resource_days):
                    if day["level"] <= node.consumption[resource] * 2:
                        days_until_critical = i
                        break
                
                if days_until_critical < 7:
                    priority_score = self._calculate_priority_score(
                        node, days_until_critical, resource
                    )
                    
                    priorities.append({
                        "node": node,
                        "resource": resource,
                        "days_remaining": days_until_critical,
                        "priority_score": priority_score
                    })
        
        return sorted(priorities, key=lambda x: x["priority_score"], reverse=True)

    def _optimize_schedule(self, priorities: List, forecast: Dict,
                         start_date: datetime, cycle: int) -> List:
        """Create optimal delivery schedule"""
        new_missions = []
        processed_nodes = set()
        
        for priority in priorities:
            node = priority["node"]
            resource = priority["resource"]
            
            node_key = f"{node.name}_{resource}"
            if node_key in processed_nodes:
                continue
                
            source = self._find_supply_source(node, resource)
            if not source:
                continue
                
            amount = self._calculate_required_amount(node, resource)
            delivery_date = self._get_optimal_delivery_date(
                forecast[node.name][resource]["daily"],
                start_date
            )
            
            if delivery_date:
                mission = {
                    "id": f"{node.name}_{delivery_date.strftime('%Y%m%d')}_{resource}",
                    "date": delivery_date.strftime("%Y-%m-%d"),
                    "time": self._get_mission_time(node),
                    "route": {
                        "from": source.name,
                        "to": node.name
                    },
                    "resources": [{
                        "type": resource,
                        "quantity": amount
                    }],
                    "transport_type": self._determine_transport_type(node, source, amount),
                    "status": "scheduled",
                    "creation_cycle": cycle
                }
                
                new_missions.append(mission)
                processed_nodes.add(node_key)
        
        return new_missions

    def _calculate_required_amount(self, node: Node, resource: str) -> int:
        """Calculate optimal delivery amount"""
        # Base amount for 7 days
        base_amount = node.consumption[resource] * 7
        
        # Add 20% safety margin
        base_amount *= 1.2
        
        # Add extra for subordinate nodes
        if node.name in self.node_controller.hierarchy:
            for child_name in self.node_controller.hierarchy[node.name]:
                child = self.node_controller.get_node(child_name)
                # Add 3 days supply for each child node
                base_amount += child.consumption[resource] * 3
        
        # Round up to nearest 100
        return int((base_amount + 99) // 100 * 100)

    def _calculate_priority_score(self, node: Node, days: int, resource: str) -> float:
        """Calculate mission priority score"""
        type_multiplier = {
            "airbase": 3.0,
            "FOB": 2.0,
            "COP": 1.0
        }
        
        resource_multiplier = {
            "fuel": 1.0,
            "ammo": 1.2
        }
        
        base_score = 100 - (days * 10)
        return base_score * type_multiplier[node.node_type] * resource_multiplier[resource]
    
    def _get_optimal_delivery_date(self, resource_forecast: List[Dict], 
                                 start_date: datetime) -> Optional[datetime]:
        """Find optimal delivery date based on resource levels"""
        # Get first day when levels drop below 50%
        max_level = max(day["level"] for day in resource_forecast)
        threshold = max_level * 0.5

        for i, day in enumerate(resource_forecast):
            if day["level"] <= threshold:
                return start_date + timedelta(days=i)
        
        return None

    # Additional helper methods remain the same as in original MissionsController
    def _find_supply_source(self, node: Node, resource: str) -> Optional[Node]:
        """Find nearest supply source with sufficient resources"""
        current = node
        while True:
            parent_name = None
            for parent, children in self.node_controller.hierarchy.items():
                if current.name in children:
                    parent_name = parent
                    break
            
            if not parent_name:
                break
                
            parent = self.node_controller.get_node(parent_name)
            if parent.state[resource] > node.consumption[resource] * (node.WARNING_DAYS + 2):
                return parent
            current = parent
        
        return None

    def _get_mission_time(self, node: Node) -> str:
        """Get mission execution time based on node type"""
        return self.time_slots[node.node_type][0]

    def _determine_transport_type(self, node: Node, source: Node,
                                required_amount: float) -> Optional[str]:
        """Determine appropriate transport type"""
        valid_routes = node.supply_routes
        if not valid_routes:
            self.logger.warning(f"No valid supply routes for {node.name}")
            return None
            
        for route in valid_routes:
            transport = self.transport_controller.find_available_transport(
                source.name,
                route,
                required_amount
            )
            if transport:
                return route
                
        return None