from typing import Dict, List
from datetime import datetime

class MissionPrinter:
    def __init__(self, logger):
        self.logger = logger

    def print_missions(self, missions: List[Dict], 
                      active_missions: Dict[str, Dict] = None,
                      show_all: bool = False,
                      current_cycle: int = None) -> None:
        """Print ASCII visualization of missions"""
        print("\nMission Schedule:")
        print("================")
        
        if active_missions and show_all:
            print("Active Missions:")
            for dest, mission in active_missions.items():
                print(f"├── To: {dest}")
                print(f"│   ├── From: {mission['route']['from']}")
                print(f"│   ├── Resources: {mission['resources']}")
                print(f"│   └── Status: {mission['status']}")
        
        # Filter missions if needed
        if not show_all and current_cycle is not None:
            missions = [m for m in missions if m.get("creation_cycle") == current_cycle]
        
        if missions:
            print("\nScheduled Missions:")
            current_date = None
            for mission in sorted(missions, key=lambda x: (x['date'], x['time'])):
                if mission['date'] != current_date:
                    current_date = mission['date']
                    print(f"\n{current_date}:")
                print(f"├── {mission['time']} - {mission['id']}")
                print(f"│   ├── Route: {mission['route']['from']} -> {mission['route']['to']}")
                print(f"│   ├── Type: {mission['transport_type']}")
                print(f"│   └── Resources: {mission['resources']}")
        print("================\n")