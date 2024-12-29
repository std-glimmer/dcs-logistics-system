from typing import Dict, List, Optional
from ...models.transport import Transport
from ...utils.json_handler import JSONHandler
from .allocation import TransportAllocation
from .printer import TransportPrinter

class TransportController:
    def __init__(self, transport_file: str, logger, 
                 printer: TransportPrinter,
                 allocation: TransportAllocation):
        self.transport_file = transport_file
        self.logger = logger
        self.vehicles: Dict[str, Transport] = {}
        self.printer = printer
        self.allocation = allocation
        self.load_transport()

    def load_transport(self) -> None:
        """Load transport from file"""
        try:
            json_handler = JSONHandler(self.transport_file)
            data = json_handler.read_json()
            
            # Load vehicles
            for vehicle_data in data["vehicles"]:
                vehicle = Transport.from_json(vehicle_data)
                self.vehicles[vehicle.name] = vehicle
                
            self.logger.info(f"Loaded {len(self.vehicles)} vehicle types")
            
        except Exception as e:
            self.logger.error(f"Error loading transport data: {str(e)}")
            raise

    def find_available_transport(self, node: str, transport_type: str, 
                               cargo_amount: float) -> Optional[Transport]:
        """Find suitable transport at node for cargo amount"""
        try:
            for vehicle in self.vehicles.values():
                if (vehicle.transport_type == transport_type and 
                    vehicle.get_available_units(node) > 0):
                    units_needed = (cargo_amount + vehicle.capacity - 1) // vehicle.capacity
                    if vehicle.get_available_units(node) >= units_needed:
                        return vehicle
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding transport: {str(e)}")
            return None

    def assign_transport(self, mission_id: str, from_node: str,
                        transport_type: str, cargo: Dict) -> Optional[Dict]:
        """Assign transport to mission"""
        try:
            result = self.allocation.assign_transport(
                self.vehicles,
                mission_id,
                from_node,
                transport_type,
                cargo
            )
            
            if result:
                self.save_transport()
                self.logger.info(
                    f"Assigned {result['vehicle']} ({result['units']} units) to mission {mission_id}"
                )
            return result
            
        except Exception as e:
            self.logger.error(f"Error assigning transport: {str(e)}")
            return None

    def complete_mission(self, mission_id: str, to_node: str) -> None:
        """Complete mission and process transport return"""
        try:
            # Find mission in vehicles
            for vehicle in self.vehicles.values():
                mission_allocation = next(
                    (m for m in vehicle.units_on_missions if m.mission == mission_id),
                    None
                )
                if not mission_allocation:
                    continue

                # Return units to destination
                cargo = vehicle.complete_mission(mission_id, to_node)
                if cargo:
                    self.logger.info(
                        f"Mission {mission_id} completed, delivered {cargo}"
                    )
                
                self.save_transport()
                break
                
        except Exception as e:
            self.logger.error(f"Error completing mission: {str(e)}")

    def save_transport(self) -> None:
        """Save current transport state"""
        try:
            data = {
                "vehicles": [v.serialize() for v in self.vehicles.values()],
            }
            
            json_handler = JSONHandler(self.transport_file)
            json_handler.write_json(data)
            
        except Exception as e:
            self.logger.error(f"Error saving transport state: {str(e)}")

    def print_status(self) -> None:
        """Print current transport status"""
        try:
            self.printer.print_transport(self.vehicles)
            
        except Exception as e:
            self.logger.error(f"Error printing status: {str(e)}")

    def get_active_transports(self) -> Dict:
        """Get summary of active transports"""
        try:
            summary = {
                "ground": 0,
                "air": 0,
                "on_mission": 0
            }
            
            for vehicle in self.vehicles.values():
                # Count units on missions
                for mission in vehicle.units_on_missions:
                    summary["on_mission"] += mission.count
                    summary[vehicle.transport_type] += mission.count
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting transport summary: {str(e)}")
            return {"error": str(e)}