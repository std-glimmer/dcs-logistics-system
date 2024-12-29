from typing import Dict, List, Optional
from ...models.transport import Transport

class TransportAllocation:
    def __init__(self, logger):
        self.logger = logger

    def assign_transport(self, vehicles: Dict[str, Transport], mission_id: str,
                        node: str, transport_type: str, cargo: Dict) -> Optional[Dict]:
        """
        Assign transport units to mission
        
        Args:
            vehicles: Available transport vehicles
            mission_id: Mission identifier
            node: Source node name
            transport_type: Required transport type
            cargo: Cargo to transport {resource_type: amount}
            
        Returns:
            Dict with assignment details or None if failed
        """
        try:
            # Find suitable vehicle type
            vehicle = self._find_suitable_vehicle(vehicles, transport_type, node, cargo)
            if not vehicle:
                self.logger.error(
                    f"No suitable {transport_type} transport at {node} for cargo {cargo}"
                )
                return None

            # Calculate needed units
            total_cargo = sum(cargo.values())
            units_needed = self._calculate_units_needed(total_cargo, vehicle.capacity)

            # Check if enough units available
            available = vehicle.get_available_units(node)
            if available < units_needed:
                self.logger.error(
                    f"Insufficient {vehicle.name} units at {node}. "
                    f"Need {units_needed}, have {available}"
                )
                return None

            # Assign to mission
            success = vehicle.assign_to_mission(node, mission_id, units_needed, cargo)
            if not success:
                self.logger.error(
                    f"Failed to assign {vehicle.name} units to mission {mission_id}"
                )
                return None

            self.logger.info(
                f"Assigned {units_needed} {vehicle.name} units to mission {mission_id}"
            )
            return {
                "vehicle": vehicle.name,
                "units": units_needed,
                "capacity": vehicle.capacity * units_needed
            }

        except Exception as e:
            self.logger.error(f"Error in transport assignment: {str(e)}")
            return None

    def _find_suitable_vehicle(self, vehicles: Dict[str, Transport],
                             transport_type: str, node: str,
                             cargo: Dict) -> Optional[Transport]:
        """Find most suitable vehicle type for mission"""
        total_cargo = sum(cargo.values())
        best_vehicle = None
        best_efficiency = 0

        for vehicle in vehicles.values():
            # Check type compatibility
            if vehicle.transport_type != transport_type:
                continue

            # Check if vehicle has units at node
            available = vehicle.get_available_units(node)
            if available == 0:
                continue

            # Calculate cargo efficiency
            units_needed = self._calculate_units_needed(total_cargo, vehicle.capacity)
            if units_needed > available:
                continue

            efficiency = total_cargo / (units_needed * vehicle.capacity)
            if efficiency > best_efficiency:
                best_vehicle = vehicle
                best_efficiency = efficiency

        return best_vehicle

    def _calculate_units_needed(self, cargo_amount: float, 
                              unit_capacity: float) -> int:
        """Calculate number of transport units needed"""
        return max(1, int((cargo_amount + unit_capacity - 1) // unit_capacity))

    def complete_mission(self, vehicles: Dict[str, Transport],
                        mission_id: str, destination: str) -> bool:
        """
        Complete mission and process transport return
        
        Args:
            vehicles: Transport vehicles
            mission_id: Mission identifier
            destination: Destination node name
            
        Returns:
            bool indicating success
        """
        try:
            for vehicle in vehicles.values():
                cargo = vehicle.complete_mission(mission_id, destination)
                if cargo is not None:
                    self.logger.info(
                        f"Completed mission {mission_id}, "
                        f"delivered cargo: {cargo}"
                    )
                    return True
            
            self.logger.warning(f"No transport found for mission {mission_id}")
            return False

        except Exception as e:
            self.logger.error(f"Error completing mission: {str(e)}")
            return False

    def get_allocation_status(self, vehicles: Dict[str, Transport]) -> Dict:
        """Get current allocation status summary"""
        try:
            status = {
                "total_missions": 0,
                "active_units": 0,
                "by_type": {}
            }

            for vehicle in vehicles.values():
                v_type = vehicle.transport_type
                if v_type not in status["by_type"]:
                    status["by_type"][v_type] = {
                        "total": 0,
                        "available": 0,
                        "on_mission": 0
                    }

                # Count units on missions
                for mission in vehicle.units_on_missions:
                    status["total_missions"] += 1
                    status["active_units"] += mission.count
                    status["by_type"][v_type]["on_mission"] += mission.count

                # Count total and available units
                for base in vehicle.units_on_bases:
                    total = base.count if base.count is not None else 0
                    status["by_type"][v_type]["total"] += total
                    status["by_type"][v_type]["available"] += total

            return status

        except Exception as e:
            self.logger.error(f"Error getting allocation status: {str(e)}")
            return {"error": str(e)}