from datetime import datetime
import shutil
import os
from typing import Dict, List, Optional
import time
from ..services.logger import LoggerService

class LogisticsController:
    def __init__(self, 
                 node_controller, 
                 mission_controller, 
                 transport_controller,
                 udp_service,
                 logger: LoggerService,
                 backup_dir: str = "data/backups",
                 cycle_interval: int = 86400):
        
        self.node_controller = node_controller
        self.mission_controller = mission_controller
        self.transport_controller = transport_controller
        self.udp_service = udp_service
        self.logger = logger
        self.backup_dir = backup_dir
        self.cycle_interval = cycle_interval
        self.is_running = False
        
        # Create backup directory
        os.makedirs(self.backup_dir, exist_ok=True)

    def start(self) -> None:
        """Start the logistics system main loop"""
        self.is_running = True
        self.logger.info("Logistics system starting...")
        
        try:
            while self.is_running:
                self.run_daily_cycle()
                time.sleep(self.cycle_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Graceful shutdown initiated...")
            self.stop()
            
        except Exception as e:
            self.logger.error(f"Error in main loop: {str(e)}")
            self.stop()
            raise

    def stop(self) -> None:
        """Stop the logistics system"""
        self.is_running = False
        self.save_state()
        self.udp_service.close()
        self.logger.info("Logistics system stopped")

    def run_daily_cycle(self) -> None:
        """Execute daily logistics cycle"""
        current_time = datetime.now()
        self.logger.info(f"Starting daily cycle at {current_time}")

        try:
            # 1. Process resource consumption
            self.node_controller.apply_daily_consumption()
            # self.node_controller.print_graph()
            
            # 2. Process vehicle
            # self.transport_controller.print_status()
            
            # 3. Handle missions
            self._process_missions()
            
            # 4. Save state and create backup
            self.save_state()

            self.print_debug_info()
            
            self.logger.info("Daily cycle completed")

        except Exception as e:
            self.logger.error(f"Error in daily cycle: {str(e)}")
            raise

    def _process_missions(self) -> None:
        """Process all mission-related operations"""
        try:
            # First process active and scheduled missions
            self.mission_controller.check_scheduled_missions()
            
            # Then plan new missions
            self.mission_controller.plan_missions()
            
        except Exception as e:
            self.logger.error(f"Error processing missions: {str(e)}")
            raise

    def save_state(self) -> None:
        """Save current system state and create backup"""
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Save current state
            self.node_controller.save_structure()
            self.mission_controller.save_missions()
            self.transport_controller.save_transport()
            
            # Create backup
            backup_suffix = f"backup_{current_time}"
            self._backup_files(backup_suffix)
            
            # Maintain only last 3 backups
            self._cleanup_old_backups(3)
            
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
            raise

    def _backup_files(self, backup_suffix: str) -> None:
        """Create backup of current state files"""
        files_to_backup = {
            "structure": "current_structure.jsonc",
            "missions": "current_missions.jsonc",
            "transport": "current_transport.jsonc"
        }
        
        for name, filename in files_to_backup.items():
            try:
                source = os.path.join("data", filename)
                backup_name = f"{os.path.splitext(filename)[0]}_{backup_suffix}.jsonc"
                backup_path = os.path.join(self.backup_dir, backup_name)
                
                shutil.copy2(source, backup_path)
                # self.logger.info(f"Created backup: {backup_path}")
                
            except Exception as e:
                self.logger.error(f"Error backing up {filename}: {str(e)}")
        
        self.logger.info(f"Created backups.")

    def _cleanup_old_backups(self, keep_count: int = 3) -> None:
        """Maintain only the specified number of recent backups for each file"""
        backup_groups: Dict[str, List[str]] = {}
        
        # Group backups by base filename
        for filename in os.listdir(self.backup_dir):
            if not filename.endswith(".jsonc"):
                continue
                
            base_name = filename.split("_backup_")[0]
            if base_name not in backup_groups:
                backup_groups[base_name] = []
            backup_groups[base_name].append(filename)
        
        # Remove old backups
        for base_name, backups in backup_groups.items():
            if len(backups) <= keep_count:
                continue
                
            # Sort by timestamp (newest first)
            backups.sort(reverse=True)
            
            # Remove old backups
            for old_backup in backups[keep_count:]:
                try:
                    os.remove(os.path.join(self.backup_dir, old_backup))
                    # self.logger.info(f"Removed old backup: {old_backup}")
                except Exception as e:
                    self.logger.error(f"Error removing backup {old_backup}: {str(e)}")

    def get_system_status(self) -> Dict:
        """Get current status of the logistics system"""
        return {
            "is_running": self.is_running,
            "cycle_interval": self.cycle_interval,
            "active_missions": len(self.mission_controller.active_missions),
            "scheduled_missions": len(self.mission_controller.scheduled_missions),
            "completed_missions": len(self.mission_controller.completed_missions),
            "nodes_count": len(self.node_controller.get_all_nodes()),
            "active_transports": self.transport_controller.get_active_transports(),
            "next_cycle": datetime.fromtimestamp(time.time() + self.cycle_interval).strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def print_debug_info(self) -> None:
        """Display system debug information in console"""
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n=== DCS LOGISTICS SYSTEM DEBUG INFO ===")
            
            # System Status
            print("\nSystem Status:")
            print(f"Running: {self.is_running}")
            print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Next Cycle: {datetime.fromtimestamp(time.time() + self.cycle_interval).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Mission Stats
            print("\nMission Statistics:")
            print(f"├── Active Missions: {len(self.mission_controller.active_missions)}")
            print(f"├── Scheduled: {len(self.mission_controller.scheduled_missions)}")
            print(f"└── Completed: {len(self.mission_controller.completed_missions)}")

            # Critical Nodes
            print("\nCritical Nodes (< 3 days supply):")
            critical_found = False
            for node in self.node_controller.get_all_nodes():
                warnings = []
                for resource in ['fuel', 'ammo']:
                    if node.consumption[resource] > 0:
                        days = node.state[resource] / node.consumption[resource]
                        if days <= 3:
                            warnings.append(f"{resource}: {days:.1f}d")
                
                if warnings:
                    critical_found = True
                    print(f"├── {node.name} ({node.node_type})")
                    for warning in warnings:
                        print(f"│   └── {warning}")
            
            if not critical_found:
                print("└── None")

            # Transport Status
            print("\nTransport Assets:")
            total_available = {"air": 0, "ground": 0}
            total_on_mission = {"air": 0, "ground": 0}
            
            for vehicle in self.transport_controller.vehicles.values():
                print(f"\n{vehicle.name} ({vehicle.transport_type}):")
                
                # Count available units
                available = sum(base.count for base in vehicle.units_on_bases)
                total_available[vehicle.transport_type] += available
                
                # Count units on missions
                on_mission = sum(mission.count for mission in vehicle.units_on_missions)
                total_on_mission[vehicle.transport_type] += on_mission
                
                # Print vehicle details
                print(f"├── Available: {available}")
                print(f"└── On Mission: {on_mission}")
                
                # Show base distribution
                if vehicle.units_on_bases:
                    print("    └── Distribution:")
                    for base in vehicle.units_on_bases:
                        if base.count > 0:
                            print(f"        └── {base.node}: {base.count}")

            # Active Missions Detail
            if self.mission_controller.active_missions:
                print("\nActive Mission Details:")
                for dest, mission in self.mission_controller.active_missions.items():
                    print(f"\n├── Mission {mission.id}")
                    print(f"│   ├── Route: {mission.route.from_node} -> {mission.route.to_node}")
                    print(f"│   ├── Transport: {mission.transport.vehicle_name} ({mission.transport.units} units)")
                    for resource in mission.resources:
                        print(f"│   └── Cargo: {resource.type}: {resource.quantity}")
            
            print("\n====================================")
            
        except Exception as e:
            self.logger.error(f"Error printing debug info: {str(e)}")