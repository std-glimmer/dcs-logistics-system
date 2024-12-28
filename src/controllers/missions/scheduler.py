from typing import Dict, List, Tuple
from datetime import datetime

class MissionScheduler:
    def __init__(self, node_controller, transport_controller, logger):
        self.node_controller = node_controller
        self.transport_controller = transport_controller
        self.logger = logger

    def process_missions(self, scheduled_missions: List[Dict], 
                        active_missions: Dict[str, Dict]) -> Tuple[List[Dict], Dict[str, Dict]]:
        """Process scheduled and active missions"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Check active missions completion
        active_missions = self._check_active_missions(active_missions)
        
        # Start new missions
        for mission in list(scheduled_missions):
            if mission["date"] == current_date and mission["status"] == "scheduled":
                if mission["route"]["to"] in active_missions:
                    continue
                    
                transport = self.transport_controller.assign_transport(
                    mission["id"],
                    mission["route"]["from"],
                    mission["transport_type"],
                    {r["type"]: r["quantity"] for r in mission["resources"]}
                )
                
                if transport:
                    mission["status"] = "in_progress"
                    mission["transport"] = transport
                    active_missions[mission["route"]["to"]] = mission
                    scheduled_missions.remove(mission)
        
        return scheduled_missions, active_missions

    def _check_active_missions(self, active_missions: Dict[str, Dict]) -> Dict[str, Dict]:
        """Check and update active missions status"""
        for dest, mission in list(active_missions.items()):
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
                
                mission["status"] = "completed"
                mission["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                active_missions.pop(dest)
                
                self.logger.info(f"Mission {mission['id']} completed")
        
        return active_missions