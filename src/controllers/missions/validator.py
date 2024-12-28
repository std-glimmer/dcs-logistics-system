from typing import Dict, List
from datetime import datetime

class MissionValidator:
    def __init__(self, node_controller, transport_controller, logger):
        self.node_controller = node_controller
        self.transport_controller = transport_controller
        self.logger = logger

    def validate_mission(self, mission: Dict, existing_missions: List[Dict]) -> bool:
        """
        Validate mission parameters
        Args:
            mission: Mission to validate
            existing_missions: List of existing missions to check for redundancy
        """
        if not self._validate_source_resources(mission):
            return False
            
        if not self._validate_transport_availability(mission):
            return False
            
        if self._is_redundant_mission(mission, existing_missions):
            self.logger.warning(f"Mission {mission['id']} is redundant with existing missions")
            return False
            
        return True

    def _validate_source_resources(self, mission: Dict) -> bool:
        """Check if source has sufficient resources"""
        if mission["route"]["from"] == "global":
            return True
            
        source = self.node_controller.get_node(mission["route"]["from"])
        for resource in mission["resources"]:
            if source.state[resource["type"]] < resource["quantity"]:
                self.logger.warning(
                    f"Insufficient {resource['type']} at {source.name}"
                )
                return False
        return True

    def _validate_transport_availability(self, mission: Dict) -> bool:
        """Check transport availability"""
        transport = self.transport_controller.find_available_transport(
            mission["route"]["from"],
            mission["transport_type"],
            sum(r["quantity"] for r in mission["resources"])
        )
        if not transport:
            self.logger.warning(
                f"No available {mission['transport_type']} transport at {mission['route']['from']}"
            )
            return False
        return True

    def _is_redundant_mission(self, mission: Dict, existing_missions: List[Dict]) -> bool:
        """Check if mission duplicates existing ones"""
        target = mission["route"]["to"]
        date = datetime.strptime(mission["date"], "%Y-%m-%d")
        
        for existing in existing_missions:
            if existing["route"]["to"] != target:
                continue
                
            existing_date = datetime.strptime(existing["date"], "%Y-%m-%d")
            if abs((date - existing_date).days) <= 1:
                for new_resource in mission["resources"]:
                    for existing_resource in existing["resources"]:
                        if new_resource["type"] == existing_resource["type"]:
                            return True
        return False