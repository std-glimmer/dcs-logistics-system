from typing import Dict, List, Optional
from ..models.transport import Transport, TransportUnit
from ..models.maintenance_facility import MaintenanceFacility
from ..services.logger import LoggerService
from ..utils.json_handler import JSONHandler

class TransportController:
    MAINTENANCE_PENALTY = 5  # Points reduced per mission
    REPAIR_RATE = 25        # Points recovered per day
    MAINTENANCE_THRESHOLD = 50  # Level requiring maintenance
    
    def __init__(self, transport_file: str, logger: LoggerService):
        self.transport_file = transport_file
        self.logger = logger
        self.vehicles: Dict[str, Transport] = {}
        self.maintenance_facilities: Dict[str, MaintenanceFacility] = {}
        self.load_transport()

    def load_transport(self) -> None:
        """Load transport and facility data from file"""
        json_handler = JSONHandler(self.transport_file)
        data = json_handler.read_json()
        
        # Load vehicles
        for vehicle_data in data["vehicles"]:
            vehicle = Transport.from_json(vehicle_data)
            self.vehicles[vehicle.name] = vehicle
            
        # Load maintenance facilities
        for facility in data["maintenance_facilities"]:
            self.maintenance_facilities[facility["node"]] = MaintenanceFacility(**facility)

    def find_available_transport(self, node: str, transport_type: str, 
                               cargo_amount: float) -> Optional[Transport]:
        """Find available transport at node for cargo amount"""
        for vehicle in self.vehicles.values():
            if (vehicle.transport_type == transport_type and 
                vehicle.get_available_units(node) > 0):
                units_needed = (cargo_amount + vehicle.capacity - 1) // vehicle.capacity
                if vehicle.get_available_units(node) >= units_needed:
                    return vehicle
        return None

    def assign_transport(self, mission_id: str, from_node: str, transport_type: str, 
                        cargo: Dict) -> Optional[Dict]:
        """Assign transport to mission"""
        vehicle = next((v for v in self.vehicles.values() 
                       if v.transport_type == transport_type), None)
        if not vehicle:
            self.logger.error(f"No {transport_type} transport available")
            return None

        # Calculate required units
        total_cargo = sum(cargo.values())
        units_needed = (total_cargo + vehicle.capacity - 1) // vehicle.capacity

        # Check availability
        available = vehicle.get_available_units(from_node)
        if available < units_needed:
            self.logger.error(f"Insufficient {vehicle.name} units at {from_node}")
            return None

        # Assign to mission
        if vehicle.assign_to_mission(from_node, mission_id, units_needed, cargo):
            self.save_transport()
            return {"vehicle": vehicle.name, "units": units_needed}
        
        return None

    def complete_mission(self, mission_id: str, to_node: str) -> None:
        """Complete mission and process transport return"""
        for vehicle in self.vehicles.values():
            mission_allocation = next(
                (m for m in vehicle.units_on_missions if m.mission == mission_id), 
                None
            )
            if mission_allocation:
                # Apply maintenance penalty to air units
                if vehicle.transport_type == "air":
                    for unit in mission_allocation.units:
                        unit.maintance -= self.MAINTENANCE_PENALTY
                        unit.stats["missions_completed"] += 1
                        if "cargo" in mission_allocation:
                            unit.stats["cargo_delivered"] += sum(
                                mission_allocation.cargo.values()
                            )
                        
                        # Check if maintenance needed
                        if unit.maintance <= self.MAINTENANCE_THRESHOLD:
                            self._schedule_maintenance(unit, to_node)
                            continue
                
                # Return units to destination base
                remaining_cargo = vehicle.complete_mission(mission_id, to_node)
                if remaining_cargo:
                    self.logger.info(
                        f"Mission {mission_id} completed, delivered {remaining_cargo}"
                    )
                
                self.save_transport()
                break

    def process_daily_maintenance(self) -> None:
        """Process daily maintenance for all facilities"""
        for facility in self.maintenance_facilities.values():
            completed_units = facility.process_daily_maintenance()
            
            for unit_id in completed_units:
                # Find and update unit
                for vehicle in self.vehicles.values():
                    if vehicle.transport_type == "air":
                        for base in vehicle.units_on_bases:
                            for unit in base.units:
                                if unit.id == unit_id:
                                    unit.status = "ready"
                                    unit.maintance = 100
                                    self.logger.info(
                                        f"Unit {unit_id} completed maintenance"
                                    )
        
        self.save_transport()

    def _schedule_maintenance(self, unit: TransportUnit, node: str) -> bool:
        """Schedule unit for maintenance at nearest facility"""
        # Find nearest facility
        facility = self.maintenance_facilities.get(node)
        if not facility:
            # Find alternative facility
            for alt_facility in self.maintenance_facilities.values():
                if alt_facility.can_accept_unit():
                    facility = alt_facility
                    break
        
        if not facility:
            self.logger.warning(f"No maintenance facility available for {unit.id}")
            return False
            
        # Schedule maintenance
        if facility.add_unit_for_repair(unit.id, unit.maintance):
            unit.status = "on_repair"
            self.logger.info(f"Unit {unit.id} scheduled for maintenance at {facility.node}")
            return True
            
        return False

    def save_transport(self) -> None:
        """Save current transport state"""
        data = {
            "vehicles": [v.serialize() for v in self.vehicles.values()],
            "maintenance_facilities": [
                f.serialize() for f in self.maintenance_facilities.values()
            ]
        }
        
        json_handler = JSONHandler(self.transport_file)
        json_handler.write_json(data)

    def print_transport(self) -> None:
        """Print current transport status"""
        print("\nTransport Assets Status:")
        print("=======================")
        
        for vehicle in self.vehicles.values():
            print(f"\n{vehicle.name} ({vehicle.transport_type}):")
            print(f"Total Count: {vehicle.total_count if vehicle.total_count else 'unlimited'}")
            
            if vehicle.units_on_bases:
                print("\nBased at:")
                for base in vehicle.units_on_bases:
                    print(f"  {base.node}: {base.count} units")
                    if base.units:
                        for unit in base.units:
                            status = f"[{unit.status.upper()}]"
                            if unit.status == "on_repair":
                                status += f" ({unit.repair_remaining}d)"
                            print(f"    {unit.id} - Maint: {unit.maintance}% {status}")
            
            if vehicle.units_on_missions:
                print("\nOn Missions:")
                for mission in vehicle.units_on_missions:
                    print(f"  {mission.mission}: {mission.count} units")
                    if mission.units:
                        for unit in mission.units:
                            print(f"    {unit.id} - Cargo: {unit.cargo}")
        
        print("\nMaintenance Facilities:")
        for node, facility in self.maintenance_facilities.items():
            print(f"  {node}: {facility.max_concurrent_repairs} slots")
            if facility.current_repairs:
                print("    Current repairs:")
                for unit_id, repair in facility.current_repairs.items():
                    print(f"      {unit_id}: {repair['days_remaining']}d remaining")
        print("=======================\n")