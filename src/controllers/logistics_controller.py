from datetime import datetime
import shutil
import os
from typing import Optional
import time

class LogisticsController:
    def __init__(self, 
                 node_controller, 
                 mission_controller, 
                 transport_controller,
                 udp_service,
                 logger,
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
        
        os.makedirs(self.backup_dir, exist_ok=True)

    def start(self):
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

    def stop(self):
        """Stop the logistics system"""
        self.is_running = False
        self.save_state()
        self.logger.info("Logistics system stopped")

    def run_daily_cycle(self):
        """Execute daily logistics cycle"""
        current_time = datetime.now()
        self.logger.info(f"Starting daily cycle at {current_time}")

        try:
            # Process node consumption
            self.node_controller.apply_daily_consumption()
            
            # Process transport maintenance
            self.transport_controller.process_daily_maintenance()
            
            # Plan and check missions using new controller
            self.mission_controller.plan_missions()
            self.mission_controller.check_scheduled_missions()
            
            # Save current state
            self.save_state()
            
            self.logger.info("Daily cycle completed")

        except Exception as e:
            self.logger.error(f"Error in daily cycle: {str(e)}")

    def save_state(self):
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
            self._cleanup_old_backups()
            
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")

    def _backup_files(self, backup_suffix: str):
        """Create backup of current state files"""
        files_to_backup = {
            "structure": "current_structure.jsonc",
            "missions": "current_missions.jsonc",
            "transport": "current_transport.jsonc"
        }
        
        for name, filename in files_to_backup.items():
            source = os.path.join("data", filename)
            backup_name = f"{os.path.splitext(filename)[0]}_{backup_suffix}.jsonc"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            shutil.copy2(source, backup_path)
            self.logger.info(f"Created backup: {backup_path}")

    def _cleanup_old_backups(self):
        """Maintain only the last 3 backups for each file type"""
        backup_groups = {}
        
        for filename in os.listdir(self.backup_dir):
            if not filename.endswith(".jsonc"):
                continue
                
            base_name = filename.split("_backup_")[0]
            if base_name not in backup_groups:
                backup_groups[base_name] = []
            backup_groups[base_name].append(filename)
        
        for backups in backup_groups.values():
            backups.sort(reverse=True)
            for old_backup in backups: # TODO stay last 3
                os.remove(os.path.join(self.backup_dir, old_backup))

    def get_system_status(self) -> dict:
        """Get current status of the logistics system"""
        return {
            "is_running": self.is_running,
            "cycle_interval": self.cycle_interval,
            "active_missions": len(self.mission_controller.active_missions),
            "scheduled_missions": len(self.mission_controller.scheduled_missions),
            "nodes_count": len(self.node_controller.get_all_nodes()),
            "active_transports": self.transport_controller.get_active_transports()
        }