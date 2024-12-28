from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .planner import MissionPlanner
from .validator import MissionValidator
from .printer import MissionPrinter
from ...models.node import Node
from ...utils.json_handler import JSONHandler

class MissionController:
    def __init__(self, missions_file: str, node_controller, transport_controller, logger):
        self.missions_file = missions_file
        self.node_controller = node_controller
        self.transport_controller = transport_controller
        self.logger = logger
        self.active_missions: Dict[str, dict] = {}
        self.scheduled_missions: List[dict] = []
        self.current_cycle = 0

        # Initialize components
        self.planner = MissionPlanner(node_controller, transport_controller, logger)
        self.validator = MissionValidator(node_controller, transport_controller, logger)
        self.printer = MissionPrinter(logger)

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
        """Plan missions for next 7 days"""
        self.current_cycle += 1
        current_date = datetime.now()
        planning_horizon = current_date + timedelta(days=7)
        
        # Get resource forecast
        resource_forecast = self._forecast_resources(current_date, planning_horizon)
        
        # Plan new missions
        new_missions = self.planner.create_missions(
            resource_forecast, 
            current_date, 
            self.current_cycle
        )
        
        # Add valid missions to schedule
        self._validate_and_add_missions(new_missions)
        self.save_missions()

    def _forecast_resources(self, start_date: datetime, end_date: datetime) -> Dict:
        """Forecast resource levels"""
        forecast = {}
        for node in self.node_controller.get_all_nodes():
            forecast[node.name] = {
                "fuel": {"current": node.state["fuel"], "daily": []},
                "ammo": {"current": node.state["ammo"], "daily": []}
            }
            
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            
            for node in self.node_controller.get_all_nodes():
                node_forecast = forecast[node.name]
                for resource in ["fuel", "ammo"]:
                    # Apply consumption
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

    def _validate_and_add_missions(self, new_missions: List[Dict]) -> None:
        """Validate and add new missions to schedule"""
        added_missions = []

        for mission in new_missions:
            # Add creation cycle
            mission["creation_cycle"] = self.current_cycle
            
            # Validate mission including redundancy check with existing missions
            if not self.validator.validate_mission(mission, self.scheduled_missions):
                continue
            
            # Add to schedule
            self.scheduled_missions.append(mission)
            added_missions.append(mission)
            self.logger.info(f"Scheduled mission: {mission['id']}")
        
        # Print new missions if any added
        if added_missions:
            self.printer.print_missions(added_missions, show_all=False)

    def save_missions(self) -> None:
        """Save missions to JSON file"""
        data = {"missions": self.scheduled_missions}
        json_handler = JSONHandler(self.missions_file)
        json_handler.write_json(data)

    def check_scheduled_missions(self) -> None:
        """Process scheduled missions for current date"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # First check active missions completion
        self._check_active_missions()
        
        # Process scheduled missions for current date
        for mission in list(self.scheduled_missions):
            if mission["date"] == current_date and mission["status"] == "scheduled":
                # Skip if destination has active mission
                if mission["route"]["to"] in self.active_missions:
                    continue
                    
                # Try to assign transport
                transport = self.transport_controller.assign_transport(
                    mission["id"],
                    mission["route"]["from"],
                    mission["transport_type"],
                    {r["type"]: r["quantity"] for r in mission["resources"]}
                )
                
                if transport:
                    # Update mission status
                    mission["status"] = "in_progress"
                    mission["transport"] = transport
                    self.active_missions[mission["route"]["to"]] = mission
                    self.scheduled_missions.remove(mission)
                    self.save_missions()
                    
    def _check_active_missions(self) -> None:
        """Check and update active mission status"""
        for dest, mission in list(self.active_missions.items()):
            if self.transport_controller.is_mission_complete(mission["id"]):
                # Update destination resources
                dest_node = self.node_controller.get_node(dest)
                for resource in mission["resources"]:
                    dest_node.state[resource["type"]] += resource["quantity"]
                
                # Complete transport assignment
                self.transport_controller.complete_mission(
                    mission["id"], 
                    mission["route"]["to"]
                )
                
                # Update mission status
                mission["status"] = "completed"
                mission["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.scheduled_missions.append(mission)
                self.active_missions.pop(dest)
                
                self.logger.info(f"Mission {mission['id']} completed")
                self.save_missions()