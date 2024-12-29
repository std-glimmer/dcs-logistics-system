from typing import Dict
from ...models.transport import Transport

class TransportPrinter:
    def __init__(self, logger):
        self.logger = logger

    def print_transport(self, vehicles: Dict[str, Transport]) -> None:
        """Print current transport status with ASCII visualization"""
        print("\nTransport Assets Status:")
        print("=======================")
        
        for vehicle in vehicles.values():
            # Print vehicle header
            print(f"\n{vehicle.name} ({vehicle.transport_type}):")
            print(f"Capacity: {vehicle.capacity} units")
            print(f"Total Count: {vehicle.total_count if vehicle.total_count else 'unlimited'}")
            
            # Print bases and units
            if vehicle.units_on_bases:
                print("\nBased at:")
                for base in vehicle.units_on_bases:
                    if base.count > 0:
                        print(f"├── {base.node}: {base.count} units")
            
            # Print active missions
            if vehicle.units_on_missions:
                print("\nOn Missions:")
                for mission in vehicle.units_on_missions:
                    print(f"├── Mission {mission.mission}: {mission.count} units")
                    if mission.cargo:
                        cargo_str = ", ".join(f"{k}: {v}" for k, v in mission.cargo.items())
                        print(f"│   └── Cargo: {cargo_str}")
        
        print("=======================\n")