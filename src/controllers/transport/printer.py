from typing import Dict
from ...models.transport import Transport

class TransportPrinter:
    def __init__(self, logger):
        self.logger = logger

    def print_transport(self, vehicles: Dict[str, Transport]) -> None:
        """Print current transport status"""
        print("\nTransport Assets Status:")
        print("=======================")
        
        for vehicle in vehicles.values():
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
        
        print("=======================\n")