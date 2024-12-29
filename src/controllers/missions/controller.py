from datetime import datetime
from typing import Dict, List, Optional
from ...utils.json_handler import JSONHandler
from .planner import MissionPlanner
from .scheduler import MissionScheduler
from .validator import MissionValidator
from .printer import MissionPrinter
from ...models.mission import Mission

class MissionController:
    def __init__(self, missions_file: str, node_controller, transport_controller, logger):
        self.missions_file = missions_file
        self.node_controller = node_controller
        self.transport_controller = transport_controller
        self.logger = logger
        
        # Initialize components
        self.planner = MissionPlanner(node_controller, transport_controller, logger)
        self.scheduler = MissionScheduler(node_controller, transport_controller, logger)
        self.validator = MissionValidator(node_controller, transport_controller, logger)
        self.printer = MissionPrinter(logger)
        
        # State tracking
        self.active_missions: Dict[str, dict] = {}
        self.scheduled_missions: List[dict] = []
        self.completed_missions: List[dict] = []
        self.current_cycle = 0
        
        self.load_missions()

    def load_missions(self) -> None:
        """Load missions from file"""
        try:
            json_handler = JSONHandler(self.missions_file)
            data = json_handler.read_json()
            
            # Convert JSON to Mission objects
            for mission_data in data.get("missions", []):
                mission = Mission.from_json(mission_data)
                
                if mission.status == "completed":
                    self.completed_missions.append(mission)
                elif mission.status == "in_progress":
                    self.active_missions[mission.route.to_node] = mission
                else:
                    self.scheduled_missions.append(mission)
                    
            self.logger.info(
                f"Loaded {len(self.scheduled_missions)} scheduled, "
                f"{len(self.active_missions)} active, "
                f"{len(self.completed_missions)} completed missions"
            )
            
        except Exception as e:
            self.logger.error(f"Error loading missions: {str(e)}")
            self.scheduled_missions = []
            self.active_missions = {}
            self.completed_missions = []

    def save_missions(self) -> None:
        """Save current missions state"""
        try:
            data = {
                "missions": [
                    mission.to_json() for mission in (
                        self.scheduled_missions + 
                        list(self.active_missions.values()) + 
                        self.completed_missions
                    )
                ]
            }
            
            json_handler = JSONHandler(self.missions_file)
            json_handler.write_json(data)
            
            self.logger.info(
                f"Saved {len(self.scheduled_missions)} scheduled, "
                f"{len(self.active_missions)} active, "
                f"{len(self.completed_missions)} completed missions"
            )
            
        except Exception as e:
            self.logger.error(f"Error saving missions: {str(e)}")
            raise

    def plan_missions(self) -> None:
        """Plan new missions based on resource forecasts"""
        self.current_cycle += 1
        current_date = datetime.now()
        
        try:
            # Get resource forecasts
            resource_forecast = self.planner.forecast_resources(current_date)
            
            # Create new missions with transport allocation
            new_missions = self.planner.create_missions(
                resource_forecast, 
                current_date,
                self.current_cycle
            )
            
            # Validate and add missions to schedule
            validated_missions = []
            for mission in new_missions:
                if self.validator.validate_mission(mission, self.scheduled_missions):
                    validated_missions.append(mission)
                    self.logger.info(f"Planned mission: {mission.id}")
            
            self.scheduled_missions.extend(validated_missions)
            
            # Print mission schedule
            self.printer.print_missions(
                self.scheduled_missions,
                self.active_missions,
                show_all=False,
                current_cycle=self.current_cycle
            )
            
            self.save_missions()
            
        except Exception as e:
            self.logger.error(f"Error planning missions: {str(e)}")

    def check_scheduled_missions(self) -> None:
        """Process scheduled missions for current date"""
        try:
            # Process missions through scheduler
            processed = self.scheduler.process_missions(
                self.scheduled_missions,
                self.active_missions
            )
            
            # Update mission states
            self.scheduled_missions = processed["scheduled"]
            self.active_missions = processed["active"]
            self.completed_missions.extend(processed["completed"])
            
            # Maintain only last 100 completed missions
            if len(self.completed_missions) > 100:
                self.completed_missions = self.completed_missions[-100:]
            
            self.save_missions()
            
        except Exception as e:
            self.logger.error(f"Error processing missions: {str(e)}")

    def get_mission_status(self, mission_id: str) -> Optional[Dict]:
        """Get current status of specific mission"""
        # Check active missions
        if mission_id in self.active_missions:
            return self.active_missions[mission_id]
            
        # Check scheduled missions
        for mission in self.scheduled_missions:
            if mission["id"] == mission_id:
                return mission
                
        # Check completed missions
        for mission in self.completed_missions:
            if mission["id"] == mission_id:
                return mission
                
        return None

    def get_missions_for_node(self, node_name: str) -> Dict[str, List[Dict]]:
        """Get all missions related to specific node"""
        node_missions = {
            "scheduled": [],
            "active": [],
            "completed": []
        }
        
        # Check scheduled missions
        node_missions["scheduled"] = [
            m for m in self.scheduled_missions
            if (m.route.from_node == node_name or 
                m["route"]["to"] == node_name)
        ]
        
        # Check active missions
        node_missions["active"] = [
            m for m in self.active_missions.values()
            if (m.route.from_node == node_name or 
                m["route"]["to"] == node_name)
        ]
        
        # Check completed missions
        node_missions["completed"] = [
            m for m in self.completed_missions
            if (m.route.from_node == node_name or 
                m["route"]["to"] == node_name)
        ]
        
        return node_missions