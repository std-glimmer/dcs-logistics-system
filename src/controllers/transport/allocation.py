from typing import Dict, List, Optional
from ...models.transport import Transport, TransportUnit

class TransportAllocation:
    def __init__(self, logger):
        self.logger = logger

    def assign_transport(self, vehicles: Dict[str, Transport], mission_id: str,
                        node: str, transport_type: str, cargo: Dict) -> Optional[Dict]:
        """Assign transport units to mission"""
        vehicle = next((v for v in vehicles.values() 
                       if v.transport_type == transport_type), None)
        if not vehicle:
            self.logger.error(f"No {transport_type} transport available")
            return None

        # Calculate units needed
        total_cargo = sum(cargo.values())
        units_needed = (total_cargo + vehicle.capacity - 1) // vehicle.capacity

        # Check availability
        available = vehicle.get_available_units(node)
        if available < units_needed:
            self.logger.error(f"Insufficient {vehicle.name} units at {node}")
            return None

        # Assign to mission
        if vehicle.assign_to_mission(node, mission_id, units_needed, cargo):
            return {"vehicle": vehicle.name, "units": units_needed}
        
        return None

    def complete_mission(self, vehicles: Dict[str, Transport], 
                        mission_id: str, destination: str) -> None:
        """Complete mission and return units"""
        for vehicle in vehicles.values():
            if vehicle.complete_mission(mission_id, destination):
                self.logger.info(f"Mission {mission_id} completed")
                break