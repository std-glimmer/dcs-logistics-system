import os
from src.controllers.logistics_controller import LogisticsController
from src.controllers.node_controller import NodeController

from src.controllers.missions.controller import MissionController 
from src.controllers.transport.printer import TransportPrinter
from src.controllers.transport.allocation import TransportAllocation
from src.controllers.transport.controller import TransportController

from src.services.logger import LoggerService
from src.services.udp_service import UDPService
from src.config.settings import *
import shutil

def setup_data_files(base_dir: str, logger: LoggerService) -> dict:
    """Setup and initialize data files"""
    # Create directories
    for directory in [CURRENT_STATE_DIR, DEFAULT_STATE_DIR, BACKUP_DIR, LOG_DIR]:
        path = os.path.join(base_dir, directory)
        os.makedirs(path, exist_ok=True)
    
    # Define required default files
    required_files = {
        "structure": ("structure.jsonc", "current_structure.jsonc"),
        "transport": ("transport.jsonc", "current_transport.jsonc")
    }
    
    # Define generated files
    generated_files = {
        "missions": (None, "current_missions.jsonc")
    }
    
    current_files = {}
    
    # Process required files with defaults
    for name, (default_file, current_file) in required_files.items():
        default_path = os.path.join(base_dir, DEFAULT_STATE_DIR, default_file)
        current_path = os.path.join(base_dir, CURRENT_STATE_DIR, current_file)
        
        if not os.path.exists(current_path):
            if os.path.exists(default_path):
                shutil.copy2(default_path, current_path)
                logger.info(f"Created {current_file} from default")
            else:
                raise FileNotFoundError(f"Required default file {default_file} not found")
        
        current_files[name] = current_path
    
    # Process generated files
    for name, (_, current_file) in generated_files.items():
        current_path = os.path.join(base_dir, CURRENT_STATE_DIR, current_file)
        if not os.path.exists(current_path):
            # Create empty missions file
            with open(current_path, 'w') as f:
                f.write('{"missions": []}')
            logger.info(f"Created new empty {current_file}")
        
        current_files[name] = current_path
    
    return current_files

def main():
    try:
        # Clear console
        os.system('cls')
        
        # Setup paths and logger
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logger = LoggerService(os.path.join(base_dir, LOG_DIR, "logistics.log"))
        logger.info("DCS Logistics System Starting...")
        
        # Setup data files
        files = setup_data_files(base_dir, logger)
        
        # Initialize services
        udp_service = UDPService(UDP_HOST, UDP_PORT)
        
        # Initialize controllers
        node_controller = NodeController(files["structure"], logger)
        # node_controller.print_graph()
        
        # Initialize transport subsystem
        transport_printer = TransportPrinter(logger)
        transport_allocation = TransportAllocation(logger)
        
        transport_controller = TransportController(
            files["transport"], 
            logger,
            printer=transport_printer,
            allocation=transport_allocation
        )
        
        # Initialize mission subsystem
        mission_controller = MissionController(
            files["missions"],
            node_controller,
            transport_controller,
            logger
        )

        # Initialize logistics controller with new components
        logistics_controller = LogisticsController(
            node_controller=node_controller,
            mission_controller=mission_controller,  # Renamed from missions_controller
            transport_controller=transport_controller,
            udp_service=udp_service,
            logger=logger,
            backup_dir=os.path.join(base_dir, BACKUP_DIR),
            cycle_interval=TEST_CYCLE_INTERVAL
        )
        
        # Start system
        logger.info("Starting logistics system...")
        logistics_controller.start()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        logistics_controller.stop()
        return 0
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())