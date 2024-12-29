from typing import Dict, List
from datetime import datetime

class MissionPrinter:
    def __init__(self, logger):
        self.logger = logger

    def print_missions(self, scheduled_missions: List[Dict], 
                      active_missions: Dict[str, Dict] = None,
                      show_all: bool = False,
                      current_cycle: int = None) -> None:
        """Print ASCII visualization of mission schedule"""
        print("\nMission Schedule:")
        print("================")
        
        if active_missions:
            print("\nActive Missions:")
            for dest, mission in active_missions.items():
                print(f"├── Mission {mission.id}")
                print(f"│   ├── Route: {mission.route.from_node} -> {mission.route.to_node}")
                print(f"│   ├── Transport: {mission.transport_type}")
                for resource in mission.resources:
                    print(f"│   ├── {resource.type}: {resource.quantity}")
                print(f"│   └── Status: {mission.status}")
        
        # Filter and sort scheduled missions
        display_missions = scheduled_missions
        if not show_all and current_cycle is not None:
            display_missions = [
                m for m in scheduled_missions 
                if m.creation_cycle == current_cycle
            ]
        
        if display_missions:
            print("\nScheduled Missions:")
            print("-----------------")
            
            # Group by date
            current_date = None
            sorted_missions = sorted(
                display_missions, 
                key=lambda x: (x.date, x.time)
            )
            
            for mission in sorted_missions:
                # Print date header if changed
                if mission.date != current_date:
                    current_date = mission.date
                    print(f"\n{current_date}:")
                
                # Print mission details
                print(f"├── {mission.time} - {mission.id}")
                print(f"│   ├── Route: {mission.route.from_node} -> {mission.route.to_node}")
                print(f"│   ├── Transport: {mission.transport_type}")
                
                # Print resources
                for resource in mission.resources:
                    print(f"│   ├── {resource.type}: {resource.quantity}")
                
                # Print additional info
                if hasattr(mission, 'transport'):
                    print(f"│   ├── Assigned: {mission.transport.vehicle_name} "
                          f"({mission.transport.units} units)")
                    
                print(f"│   └── Status: {mission.status}")
        
        # Print summary
        print("\nSummary:")
        print(f"├── Active Missions: {len(active_missions) if active_missions else 0}")
        print(f"└── Scheduled Missions: {len(display_missions)}")
        print("================\n")

    def print_mission_details(self, mission: Dict) -> None:
        """Print detailed information about a specific mission"""
        if not mission:
            print("Mission not found")
            return
            
        print("\nMission Details:")
        print("===============")
        print(f"ID: {mission.id}")
        print(f"Status: {mission.status}")
        print(f"Date: {mission.date} {mission.time}")
        print("\nRoute:")
        print(f"├── From: {mission.route.from_node}")
        print(f"└── To: {mission.route.to_node}")
        print("\nResources:")
        for resource in mission.resources:
            print(f"├── {resource.type}: {resource.quantity}")
        print("\nTransport:")
        print(f"└── Type: {mission.transport_type}")
        if hasattr(mission, 'transport'):
            print(f"    └── Assigned: {mission.transport.vehicle_name} "
                  f"({mission.transport.units} units)")
        if hasattr(mission, 'completed_at'):
            print(f"\nCompleted: {mission.completed_at}")
        print("===============\n")