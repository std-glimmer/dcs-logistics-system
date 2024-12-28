from typing import Dict, List, Optional
from enum import Enum
from ...models.transport import Transport, TransportUnit
from ...models.maintenance_facility import MaintenanceFacility

class MaintenanceState(Enum):
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"
    REPAIR = "repair"

class MaintenanceManager:
    WEAR_PER_MISSION = 5
    REPAIR_RATE = 25
    WARNING_THRESHOLD = 60
    CRITICAL_THRESHOLD = 30

    def __init__(self, facilities: Dict[str, MaintenanceFacility], logger):
        self.facilities = facilities
        self.logger = logger

    def process_daily_maintenance(self, vehicles: Dict[str, Transport]) -> None:
        """Process maintenance for all facilities"""
        # Process repairs in facilities
        completed_repairs = []
        for facility in self.facilities.values():
            repaired_units = facility.process_daily_repairs(self.REPAIR_RATE)
            completed_repairs.extend(repaired_units)

        # Update repaired units
        for unit_id in completed_repairs:
            self._return_unit_to_service(vehicles, unit_id)

        # Check units needing maintenance
        self._check_units_maintenance(vehicles)

    def _check_units_maintenance(self, vehicles: Dict[str, Transport]) -> None:
        """Check all units for maintenance needs"""
        for vehicle in vehicles.values():
            if vehicle.transport_type != "air":
                continue

            for base in vehicle.units_on_bases:
                for unit in base.units:
                    if unit.status == "ready":
                        state = self._get_maintenance_state(unit)
                        if state == MaintenanceState.CRITICAL:
                            self._send_to_maintenance(unit, base.node)

    def _get_maintenance_state(self, unit: TransportUnit) -> MaintenanceState:
        """Get unit maintenance state"""
        if unit.status == "repair":
            return MaintenanceState.REPAIR
        if unit.maintance <= self.CRITICAL_THRESHOLD:
            return MaintenanceState.CRITICAL
        if unit.maintance <= self.WARNING_THRESHOLD:
            return MaintenanceState.WARNING
        return MaintenanceState.GOOD
    
    def apply_mission_wear(self, unit: TransportUnit) -> None:
        """Apply wear from mission"""
        if unit.transport_type == "air":
            unit.maintance -= self.WEAR_PER_MISSION
            unit.stats["missions_completed"] += 1

    def _send_to_maintenance(self, unit: TransportUnit, node: str) -> bool:
        """Send unit for maintenance"""
        facility = self._find_nearest_facility(node)
        if not facility:
            self.logger.warning(f"No maintenance facility available for {unit.id}")
            return False

        if facility.add_unit_for_repair(unit.id, unit.maintance):
            unit.status = "repair"
            unit.repair_remaining = self._calculate_repair_time(unit.maintance)
            self.logger.info(f"Unit {unit.id} sent to maintenance at {facility.node}")
            return True
        return False
    
    def _calculate_repair_time(self, maintenance_level: float) -> int:
        """Calculate days needed for repair"""
        repair_needed = 100 - maintenance_level
        return max(1, int((repair_needed + self.REPAIR_RATE - 1) // self.REPAIR_RATE))

    def _return_unit_to_service(self, vehicles: Dict[str, Transport], 
                              unit_id: str) -> None:
        """Return repaired unit to service"""
        for vehicle in vehicles.values():
            if vehicle.transport_type != "air":
                continue
                
            for base in vehicle.units_on_bases:
                for unit in base.units:
                    if unit.id == unit_id:
                        unit.status = "ready"
                        unit.maintance = 100
                        unit.repair_remaining = 0
                        self.logger.info(f"Unit {unit_id} returned to service")
                        return

    def _find_nearest_facility(self, node: str) -> Optional[MaintenanceFacility]:
        """Find nearest available maintenance facility"""
        # First check local facility
        if node in self.facilities:
            facility = self.facilities[node]
            if facility.has_capacity():
                return facility

        # Then check other facilities
        for facility in self.facilities.values():
            if facility.has_capacity():
                return facility

        return None