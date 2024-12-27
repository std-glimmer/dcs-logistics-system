from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..models.node import Node
from ..utils.json_handler import JSONHandler

class MissionsController:
    def __init__(self, missions_file: str, node_controller, transport_controller, logger):
        self.missions_file = missions_file
        self.node_controller = node_controller
        self.transport_controller = transport_controller
        self.logger = logger
        self.active_missions: Dict[str, dict] = {}
        self.scheduled_missions: List[dict] = []
        self.load_missions()

    def load_missions(self) -> None:
        """Load missions from JSON file"""
        try:
            json_handler = JSONHandler(self.missions_file)
            data = json_handler.read_json()
            self.scheduled_missions = data.get("missions", [])
        except FileNotFoundError:
            self.logger.info("No existing missions file found, starting fresh")
            self.scheduled_missions = []

    def plan_missions(self) -> None:
        """Plan missions for next 7 days considering existing schedule"""
        current_date = datetime.now()
        planning_horizon = current_date + timedelta(days=7)
        
        # Get resource forecast including existing missions
        resource_forecast = self._forecast_resources(current_date, planning_horizon)
        
        # Get prioritized needs list
        priorities = self._calculate_priorities(resource_forecast)
        
        # Create optimal schedule
        new_missions = self._optimize_schedule(priorities, resource_forecast, current_date)
        
        # Add valid missions to schedule
        self._validate_and_add_missions(new_missions)
        
        self.save_missions()

    def _forecast_resources(self, start_date: datetime, end_date: datetime) -> Dict:
        """Forecast resource levels including existing missions impact"""
        forecast = {}
        
        # Initialize forecast for each node
        for node in self.node_controller.get_all_nodes():
            forecast[node.name] = {
                "fuel": {"current": node.state["fuel"], "daily": []},
                "ammo": {"current": node.state["ammo"], "daily": []}
            }
            
        # Calculate day by day impact
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Process daily consumption and scheduled deliveries
            for node in self.node_controller.get_all_nodes():
                node_forecast = forecast[node.name]
                
                # Apply daily consumption
                for resource in ["fuel", "ammo"]:
                    node_forecast[resource]["current"] -= node.consumption[resource]
                    
                    # Add scheduled deliveries
                    scheduled_amount = sum(
                        r["quantity"] for m in self.scheduled_missions 
                        for r in m["resources"]
                        if m["route"]["to"] == node.name 
                        and m["date"] == date_str 
                        and r["type"] == resource
                    )
                    node_forecast[resource]["current"] += scheduled_amount
                    
                    # Record daily state
                    node_forecast[resource]["daily"].append({
                        "date": date_str,
                        "level": node_forecast[resource]["current"]
                    })
            
            current_date += timedelta(days=1)
            
        return forecast
    
    def _calculate_priorities(self, forecast: Dict) -> List:
        """Calculate prioritized list of supply needs"""
        priorities = []
        
        for node in self.node_controller.get_all_nodes():
            for resource in ["fuel", "ammo"]:
                # Find days until critical/depletion
                days_remaining = self._calculate_days_remaining(
                    forecast[node.name][resource]["daily"]
                )
                
                if days_remaining <= node.WARNING_DAYS + 2:
                    priorities.append({
                        "node": node,
                        "resource": resource,
                        "days_remaining": days_remaining,
                        "priority_score": self._calculate_priority_score(
                            node, days_remaining, resource
                        )
                    })
        
        return sorted(priorities, key=lambda x: x["priority_score"], reverse=True)
    
    def _optimize_schedule(self, priorities: List, forecast: Dict, 
                         start_date: datetime) -> List:
        """Create optimal delivery schedule"""
        new_missions = []
        processed_nodes = set()
        
        for priority in priorities:
            node = priority["node"]
            resource = priority["resource"]
            
            # Skip if node already processed
            node_key = f"{node.name}_{resource}"
            if node_key in processed_nodes:
                continue
                
            source = self._find_supply_source(node, resource)
            if not source:
                continue
                
            # Calculate optimal delivery amount and date
            amount = self._calculate_required_amount(node, resource)
            delivery_date = self._get_optimal_delivery_date(
                forecast[node.name][resource]["daily"],
                start_date
            )

            transport_type = self._determine_transport_type(node, source, amount)
            if not transport_type:
                self.logger.warning(f"Could not determine transport type for {node.name}")
                continue
            
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
                    "transport_type": transport_type,
                    "status": "scheduled"
                }
                
                if self._validate_mission(mission):
                    new_missions.append(mission)
                    processed_nodes.add(node_key)
        
        return new_missions
    
    def _calculate_priority_score(self, node: Node, days_remaining: float, 
                                resource: str) -> float:
        """Calculate priority score for resource need"""
        type_weights = {
            "airbase": 3.0,
            "FOB": 2.0,
            "COP": 1.0
        }
        
        resource_weights = {
            "fuel": 1.0,
            "ammo": 1.2
        }
        
        base_score = 100 - (days_remaining * 10)
        return base_score * type_weights[node.node_type] * resource_weights[resource]

    def _validate_and_add_missions(self, new_missions: List[Dict]) -> None:
        """Validate and add new missions to schedule"""
        for mission in new_missions:
            # Check source resources
            if not self._validate_source_resources(mission):
                continue
                
            # Check transport availability
            if not self._validate_transport_availability(mission):
                continue
                
            # Check for duplicate/redundant missions
            if self._is_redundant_mission(mission):
                continue
                
            self.scheduled_missions.append(mission)
            self.logger.info(
                f"Scheduled mission {mission['id']} from {mission['route']['from']} "
                f"to {mission['route']['to']} on {mission['date']} at {mission['time']}, "
                f"resources: {mission['resources']}, transport: {mission['transport_type']}"
            )

    def _validate_source_resources(self, mission: Dict) -> bool:
        """Validate source has sufficient resources"""
        if mission["route"]["from"] == "global":
            return True
            
        source = self.node_controller.get_node(mission["route"]["from"])
        for resource in mission["resources"]:
            if source.state[resource["type"]] < resource["quantity"]:
                return False
        return True

    def _validate_transport_availability(self, mission: Dict) -> bool:
        """Check transport availability for mission date"""
        transport = self.transport_controller.find_available_transport(
            mission["route"]["from"],
            mission["transport_type"],
            sum(r["quantity"] for r in mission["resources"])
        )
        return transport is not None

    def _is_redundant_mission(self, new_mission: Dict) -> bool:
        """Check if mission is redundant with existing schedule"""
        target = new_mission["route"]["to"]
        date = datetime.strptime(new_mission["date"], "%Y-%m-%d")
        
        # Check missions within ±1 day
        for mission in self.scheduled_missions:
            if mission["route"]["to"] != target:
                continue
                
            mission_date = datetime.strptime(mission["date"], "%Y-%m-%d")
            if abs((date - mission_date).days) <= 1:
                # Check if resources overlap
                for new_resource in new_mission["resources"]:
                    for existing_resource in mission["resources"]:
                        if new_resource["type"] == existing_resource["type"]:
                            return True
        return False

    def _get_optimal_delivery_date(self, resource_forecast: List[Dict], 
                                start_date: datetime) -> Optional[datetime]:
        """Calculate optimal delivery date based on forecast"""
        # Find first day below 50% of maximum
        max_level = max(day["level"] for day in resource_forecast)
        threshold = max_level * 0.5
        
        for i, day in enumerate(resource_forecast):
            if day["level"] <= threshold:
                return start_date + timedelta(days=i)
        
        return None

    def _calculate_days_remaining(self, forecast: List[Dict]) -> float:
        """Calculate days until resource depletion"""
        for i, day in enumerate(forecast):
            if day["level"] <= 0:
                return float(i)
        return float('inf')

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

    def _calculate_required_amount(self, node: Node, resource: str) -> int:
        """Calculate optimal resupply amount"""
        days_supply = 7
        base_amount = node.consumption[resource] * days_supply
        
        if node.name in self.node_controller.hierarchy:
            for child_name in self.node_controller.hierarchy[node.name]:
                child = self.node_controller.get_node(child_name)
                base_amount += child.consumption[resource] * (days_supply / 2)
        
        return int(base_amount)

    def _get_mission_time(self, node: Node) -> str:
        """Get mission execution time based on node type"""
        time_slots = {
            "airbase": ["06:00", "18:00"],
            "FOB": ["10:00", "14:00"],
            "COP": ["12:00"]
        }
        return time_slots[node.node_type][0]

    def _determine_transport_type(self, node: Node, source_node: Node, required_amount: int) -> str:
        """Determine appropriate transport type based on available supply routes"""
        
        # Get common supply routes between source and destination
        available_routes = set(source_node.supply_routes) & set(node.supply_routes)
        
        if not available_routes:
            self.logger.warning(
                f"No common supply routes between {source_node.name} and {node.name}"
            )
            return None

        # Try each available route type
        for route in available_routes:
            # Try to find available transport of this type
            transport = self.transport_controller.find_available_transport(
                source_node.name, 
                route,
                required_amount
            )
            if transport:
                return route
                
        # No available transport found for any route
        self.logger.warning(
            f"No available transport for routes {available_routes} between {source_node.name} and {node.name}"
        )
        return None

    def _validate_mission(self, mission: Dict) -> bool:
        """Validate mission parameters"""
        try:
            if mission["route"]["from"] != "global":
                source = self.node_controller.get_node(mission["route"]["from"])
                for resource in mission["resources"]:
                    if source.state[resource["type"]] < resource["quantity"]:
                        self.logger.warning(
                            f"Insufficient {resource['type']} at {source.name}"
                        )
                        return False
            
            transport = self.transport_controller.find_available_transport(
                mission["route"]["from"],
                mission["transport_type"],
                sum(r["quantity"] for r in mission["resources"])
            )
            if not transport:
                self.logger.warning(
                    f"No available {mission['transport_type']} transport at {mission['route']['from']} for delivery to {mission['route']['to']}"
                )
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Mission validation error: {str(e)}")
            return False

    def check_scheduled_missions(self) -> None:
        """Check and start scheduled missions for current date"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # First check active missions completion
        self._check_active_missions()
        
        # Then process scheduled missions
        for mission in list(self.scheduled_missions):
            if mission["date"] == current_date and mission["status"] == "scheduled":
                # Check if destination already has active mission
                if mission["route"]["to"] in self.active_missions:
                    continue
                    
                if self._validate_mission(mission):
                    transport = self.transport_controller.assign_transport(
                        mission["id"],
                        mission["route"]["from"],
                        mission["transport_type"],
                        {r["type"]: r["quantity"] for r in mission["resources"]}
                    )
                    if transport:
                        mission["status"] = "in_progress"
                        mission["transport"] = transport
                        self.active_missions[mission["route"]["to"]] = mission
                        self.scheduled_missions.remove(mission)
                        self.save_missions()

    def _check_active_missions(self) -> None:
        """Check and update status of active missions"""
        for dest, mission in list(self.active_missions.items()):
            if self.transport_controller.is_mission_complete(mission["id"]):
                # Update resources at destination
                dest_node = self.node_controller.get_node(dest)
                for resource in mission["resources"]:
                    dest_node.state[resource["type"]] += resource["quantity"]
                
                # Complete transport assignment
                self.transport_controller.complete_mission(
                    mission["id"], 
                    mission["route"]["to"]
                )
                
                # Remove from active missions
                self.active_missions.pop(dest)
                
                # Add to mission history
                mission["status"] = "completed"
                mission["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.scheduled_missions.append(mission)
                
                self.logger.info(f"Mission {mission['id']} completed")
                self.save_missions()

    def cancel_mission(self, mission_id: str) -> bool:
        """Cancel scheduled or active mission"""
        # Check scheduled missions
        for mission in self.scheduled_missions:
            if mission["id"] == mission_id:
                mission["status"] = "cancelled"
                self.logger.info(f"Mission {mission_id} cancelled")
                self.save_missions()
                return True
        
        # Check active missions
        for dest, mission in self.active_missions.items():
            if mission["id"] == mission_id:
                # Return transport to base
                self.transport_controller.cancel_mission(
                    mission_id,
                    mission["route"]["from"]
                )
                
                mission["status"] = "cancelled"
                self.scheduled_missions.append(mission)
                self.active_missions.pop(dest)
                
                self.logger.info(f"Active mission {mission_id} cancelled")
                self.save_missions()
                return True
        
        return False

    def save_missions(self) -> None:
        """Save missions to JSON file"""
        data = {"missions": self.scheduled_missions}
        json_handler = JSONHandler(self.missions_file)
        json_handler.write_json(data)

    def print_missions(self) -> None:
        """Print ASCII visualization of missions"""
        print("\nMission Schedule:")
        print("================")
        
        print("Active Missions:")
        for dest, mission in self.active_missions.items():
            print(f"├── To: {dest}")
            print(f"│   ├── From: {mission['route']['from']}")
            print(f"│   ├── Resources: {mission['resources']}")
            print(f"│   └── Status: {mission['status']}")
        
        print("\nScheduled Missions:")
        current_date = None
        for mission in sorted(self.scheduled_missions, 
                            key=lambda x: (x['date'], x['time'])):
            if mission['date'] != current_date:
                current_date = mission['date']
                print(f"\n{current_date}:")
            print(f"├── {mission['time']}")
            print(f"│   ├── {mission['route']['from']} -> {mission['route']['to']}")
            print(f"│   ├── Type: {mission['transport_type']}")
            print(f"│   └── Resources: {mission['resources']}")
        print("================\n")