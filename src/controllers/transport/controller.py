from typing import Dict, List, Optional
from ...models.transport import Transport
from ...models.maintenance_facility import MaintenanceFacility
from ...utils.json_handler import JSONHandler
from .maintenance import MaintenanceManager
from .allocation import TransportAllocation
from .printer import TransportPrinter

class TransportController:
    def __init__(self, transport_file: str, logger, 
                 printer: TransportPrinter,
                 allocation: TransportAllocation,
                 maintenance: MaintenanceManager):
        self.transport_file = transport_file
        self.logger = logger
        self.vehicles: Dict[str, Transport] = {}
        self.printer = printer
        self.allocation = allocation
        self.maintenance = maintenance
        self.load_transport()

    def load_transport(self) -> None:
        """Load transport data from file"""
        json_handler = JSONHandler(self.transport_file)
        data = json_handler.read_json()
        
        # Load vehicles
        for vehicle_data in data["vehicles"]:
            vehicle = Transport.from_json(vehicle_data)
            self.vehicles[vehicle.name] = vehicle
            
        # Load maintenance facilities
        for facility_data in data.get("maintenance_facilities", []):
            facility = MaintenanceFacility(**facility_data)
            self.maintenance.facilities[facility.node] = facility

    def find_available_transport(self, node: str, transport_type: str, 
                               cargo_amount: float) -> Optional[Transport]:
        """Find available transport at node"""
        for vehicle in self.vehicles.values():
            if (vehicle.transport_type == transport_type and 
                vehicle.get_available_units(node) > 0):
                units_needed = (cargo_amount + vehicle.capacity - 1) // vehicle.capacity
                if vehicle.get_available_units(node) >= units_needed:
                    return vehicle
        return None

    def assign_transport(self, mission_id: str, from_node: str,
                        transport_type: str, cargo: Dict) -> Optional[Dict]:
        """Assign transport to mission"""
        return self.allocation.assign_transport(
            self.vehicles,
            mission_id,
            from_node,
            transport_type,
            cargo
        )

    def complete_mission(self, mission_id: str, to_node: str) -> None:
        """Complete mission and process transport return"""
        for vehicle in self.vehicles.values():
            mission_allocation = next(
                (m for m in vehicle.units_on_missions if m.mission == mission_id),
                None
            )
            if not mission_allocation:
                continue

            # Process air units maintenance
            if vehicle.transport_type == "air" and mission_allocation.units:
                for unit in mission_allocation.units:
                    # Apply mission wear
                    self.maintenance.apply_mission_wear(unit)
                    
                    # Check if maintenance needed
                    if unit.maintance <= self.maintenance.MAINTENANCE_THRESHOLD:
                        if not self.maintenance.schedule_maintenance(unit, to_node):
                            self.logger.warning(
                                f"Could not schedule maintenance for {unit.id}"
                            )

            # Return units to destination
            cargo = vehicle.complete_mission(mission_id, to_node)
            if cargo:
                self.logger.info(
                    f"Mission {mission_id} completed, delivered {cargo}"
                )
            
            self.save_transport()
            break

    def process_daily_maintenance(self) -> None:
        """Process daily maintenance"""
        self.maintenance.process_daily_maintenance(self.vehicles)
        self.save_transport()

    def is_mission_complete(self, mission_id: str) -> bool:
        """Check if mission is complete"""
        for vehicle in self.vehicles.values():
            mission = next(
                (m for m in vehicle.units_on_missions if m.mission == mission_id),
                None
            )
            if mission:
                # Ground transport completes instantly
                if vehicle.transport_type == "ground":
                    return True
                    
                # Air transport needs all units ready
                if vehicle.transport_type == "air":
                    return all(u.status == "ready" for u in mission.units)
        return False

    def save_transport(self) -> None:
        """Save current transport state"""
        data = {
            "vehicles": [v.serialize() for v in self.vehicles.values()],
            "maintenance_facilities": [
                f.serialize() for f in self.maintenance.facilities.values()
            ]
        }
        
        json_handler = JSONHandler(self.transport_file)
        json_handler.write_json(data)

    def print_status(self) -> None:
        """Print current transport status"""
        self.printer.print_transport(self.vehicles)

    def get_active_transports(self) -> Dict:
        """Get summary of active transports"""
        summary = {
            "ground": 0,
            "air": 0,
            "on_mission": 0,
            "in_maintenance": 0
        }
        
        for vehicle in self.vehicles.values():
            for mission in vehicle.units_on_missions:
                summary["on_mission"] += mission.count
                summary[vehicle.transport_type] += mission.count
                
            if vehicle.transport_type == "air":
                for base in vehicle.units_on_bases:
                    for unit in base.units:
                        if unit.status == "on_repair":
                            summary["in_maintenance"] += 1
        
        return summary