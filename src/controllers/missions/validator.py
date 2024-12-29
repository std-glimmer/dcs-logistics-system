from typing import Dict, List, Optional
from datetime import datetime
from ...models.node import Node
from ...config.mission_config import MIN_RESOURCE_THRESHOLD
from ...models.mission import Mission

class MissionValidator:
    def __init__(self, node_controller, transport_controller, logger):
        self.node_controller = node_controller
        self.transport_controller = transport_controller
        self.logger = logger

    def validate_mission(self, mission: Mission, 
                        existing_missions: List[Mission]) -> bool:
        """Validate mission parameters and constraints"""
        try:
            # Basic validation
            if not self._validate_basic_params(mission):
                return False

            # Route validation    
            if not self._validate_route(mission):
                return False

            # Resource validation (skip for relocation)
            if not mission.is_relocation and not self._validate_resources(mission):
                return False
            
            # Transport validation
            if not self._validate_transport(mission):
                return False

            # Check for conflicts with existing missions
            if self._has_conflicts(mission, existing_missions):
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating mission {mission.id}: {str(e)}")
            return False

    def _validate_basic_params(self, mission: Mission) -> bool:
        """Validate basic mission parameters"""
        if not isinstance(mission, Mission):
            self.logger.error("Invalid mission object type")
            return False

        if not all([
            mission.id,
            mission.date,
            mission.time,
            mission.route,
            mission.resources,
            mission.transport_type
        ]):
            self.logger.error("Missing required mission fields")
            return False
                
        return True

    def _validate_route(self, mission: Mission) -> bool:
        """Validate mission route"""
        # Check source node
        source = self.node_controller.get_node(mission.route.from_node)
        if not source:
            self.logger.error(f"Invalid source node: {mission.route.from_node}")
            return False
            
        # Check destination node
        dest = self.node_controller.get_node(mission.route.to_node)
        if not dest:
            self.logger.error(f"Invalid destination node: {mission.route.to_node}")
            return False
            
        # Check supply routes compatibility
        if mission.transport_type not in dest.supply_routes:
            self.logger.error(
                f"Transport type {mission.transport_type} not supported at {dest.name}"
            )
            return False
            
        return True

    def _validate_resources(self, mission: Mission) -> bool:
        """Validate resource quantities and availability""" 
        source = self.node_controller.get_node(mission.route.from_node)
        dest = self.node_controller.get_node(mission.route.to_node)
        
        for resource in mission.resources:
            # Check if source has sufficient resources
            if resource.quantity > source.state[resource.type]:
                self.logger.error(
                    f"Insufficient {resource.type} at {source.name}: "
                    f"needs {resource.quantity}, has {source.state[resource.type]}"
                )
                return False
                
            # Check if delivery amount makes sense
            if resource.quantity <= 0:
                self.logger.error(
                    f"Invalid quantity for {resource.type}: {resource.quantity}"
                )
                return False
                
            # Validate against node capacity
            daily_consumption = dest.consumption[resource.type]
            if resource.quantity < daily_consumption * MIN_RESOURCE_THRESHOLD:
                self.logger.warning(
                    f"Delivery amount for {resource.type} is below minimum threshold"
                )
        
        return True

    def _validate_transport(self, mission: Mission) -> bool:
        """Validate transport availability and capacity"""
        # Для обычных миссий проверяем общий вес груза
        if not mission.is_relocation:
            total_cargo = sum(r.quantity for r in mission.resources)
        else:
            # Для релокации просто проверяем наличие транспорта
            total_cargo = 0
        
        transport = self.transport_controller.find_available_transport(
            mission.route.from_node,
            mission.transport_type,
            total_cargo
        )
        
        if not transport:
            self.logger.error(
                f"No suitable transport available at {mission.route.from_node}"
                + (f" for cargo amount {total_cargo}" if not mission.is_relocation else "")
            )
            return False
            
        return True

    def _has_conflicts(self, mission: Mission, 
                      existing_missions: List[Mission]) -> bool:
        """Check for conflicts with existing missions"""
        mission_date = datetime.strptime(mission.date, "%Y-%m-%d")
        
        for existing in existing_missions:
            # Skip completed missions
            if existing.status == "completed":
                continue
                
            # Check same destination missions
            if existing.route.to_node == mission.route.to_node:
                existing_date = datetime.strptime(existing.date, "%Y-%m-%d")
                
                # Check for same-day missions
                if abs((mission_date - existing_date).days) <= 1:
                    # Check for resource overlap
                    if self._resources_overlap(mission, existing):
                        self.logger.error(
                            f"Mission {mission.id} conflicts with existing "
                            f"mission {existing.id}"
                        )
                        return True
                        
        return False

    def _resources_overlap(self, mission1: Mission, mission2: Mission) -> bool:
        """Check if missions have overlapping resources"""
        resources1 = {r.type for r in mission1.resources}
        resources2 = {r.type for r in mission2.resources}
        
        return bool(resources1.intersection(resources2))