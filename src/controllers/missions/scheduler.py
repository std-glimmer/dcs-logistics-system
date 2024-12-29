from typing import Dict, List, Tuple
from datetime import datetime
from ...models.mission import Mission
from ...models.node import Node

class MissionScheduler:
    def __init__(self, node_controller, transport_controller, logger):
        self.node_controller = node_controller
        self.transport_controller = transport_controller
        self.logger = logger

    def process_missions(self, scheduled_missions: List[Mission], 
                            active_missions: Dict[str, Mission]) -> Dict:
            """Process scheduled and active missions"""
            try:
                current_date = datetime.now().strftime("%Y-%m-%d")
                completed_missions = []

                # Process active missions
                for dest, mission in list(active_missions.items()):
                    # Complete mission
                    completed_missions.append(mission)
                    
                    # Update destination resources
                    dest_node = self.node_controller.get_node(dest)
                    for resource in mission.resources:
                        dest_node.state[resource.type] += resource.quantity
                    
                    # Complete transport assignment
                    self.transport_controller.complete_mission(
                        mission.id, 
                        mission.route.to_node
                    )
                    
                    # Update mission status
                    mission.complete()
                    active_missions.pop(dest)
                    
                    self.logger.info(
                        f"Mission {mission.id} completed at {mission.completed_at}"
                    )

                # Process new missions for current date
                for mission in list(scheduled_missions):
                    if mission.date == current_date and mission.status == "scheduled":
                        # Skip if destination already has active mission
                        if mission.route.to_node in active_missions:
                            continue
                            
                        # Try to assign transport
                        transport = self.transport_controller.assign_transport(
                            mission.id,
                            mission.route.from_node,
                            mission.transport_type,
                            {r.type: r.quantity for r in mission.resources}
                        )
                        
                        if transport:
                            mission.status = "in_progress"
                            mission.transport = transport
                            active_missions[mission.route.to_node] = mission
                            scheduled_missions.remove(mission)
                            
                            self.logger.info(
                                f"Started mission {mission.id} to {mission.route.to_node}"
                            )

                return {
                    "scheduled": scheduled_missions,
                    "active": active_missions,
                    "completed": completed_missions
                }
                
            except Exception as e:
                self.logger.error(f"Error processing missions: {str(e)}")
                raise

    def get_active_missions_status(self, active_missions: Dict[str, Mission]) -> Dict:
        """Get status summary of active missions"""
        try:
            status = {
                "total": len(active_missions),
                "by_type": {},
                "by_destination": {}
            }
            
            for dest, mission in active_missions.items():
                # Count by transport type
                if mission.transport_type not in status["by_type"]:
                    status["by_type"][mission.transport_type] = 0
                status["by_type"][mission.transport_type] += 1
                
                # Count by destination type
                dest_node = self.node_controller.get_node(dest)
                if dest_node.node_type not in status["by_destination"]:
                    status["by_destination"][dest_node.node_type] = 0
                status["by_destination"][dest_node.node_type] += 1
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting missions status: {str(e)}")
            return {"error": str(e)}

    def _plan_transport_relocation(self, mission: Dict) -> None:
        """Plan transport relocation mission if needed"""
        required_type = mission["transport_type"]
        target_node = mission.route.from_node
        
        # Find available transport at other nodes
        for node in self.node_controller.get_all_nodes():
            if node.name == target_node:
                continue
                
            transport = self.transport_controller.find_available_transport(
                node.name,
                required_type,
                sum(r["quantity"] for r in mission["resources"])
            )
            
            if transport:
                # Create relocation mission
                relocation_mission = {
                    "id": f"reloc_{mission['id']}",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "time": "00:00",
                    "route": {
                        "from": node.name,
                        "to": target_node
                    },
                    "transport_type": required_type,
                    "status": "scheduled",
                    "is_relocation": True,
                    "original_mission_id": mission["id"]
                }
                
                self.logger.info(
                    f"Planning transport relocation: {node.name} -> {target_node}"
                )
                return relocation_mission
                
        self.logger.warning(
            f"No available transport found for relocation to {target_node}"
        )