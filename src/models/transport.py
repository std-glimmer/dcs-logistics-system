from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class BaseAllocation:
    """Transport units allocated to a base"""
    node: str  # Base name
    count: int  # Number of units

@dataclass
class MissionAllocation:
    """Transport units allocated to a mission"""
    mission: str  # Mission identifier
    count: int  # Number of units assigned
    cargo: Optional[Dict] = None  # Mission cargo

class Transport:
    """Transport vehicle type with unit management"""
    
    def __init__(self, name: str, transport_type: str, category: str,
                 capacity: int, routes: List[str], description: str,
                 is_player_available: bool = True,
                 total_count: Optional[int] = None,
                 units_on_bases: Optional[List[Dict]] = None,
                 units_on_missions: Optional[List[Dict]] = None):
        """
        Initialize transport vehicle type
        
        Args:
            name: Vehicle name
            transport_type: Type (air/ground/strategic)
            category: Cargo category
            capacity: Cargo capacity
            routes: Supported route types
            description: Vehicle description
            is_player_available: If available for player missions
            total_count: Total units available
            units_on_bases: Initial base allocations
            units_on_missions: Initial mission allocations
        """
        self.name = name
        self.transport_type = transport_type
        self.category = category
        self.capacity = capacity
        self.routes = routes
        self.description = description
        self.is_player_available = is_player_available
        self.total_count = total_count
        
        # Initialize unit allocations
        self.units_on_bases: List[BaseAllocation] = []
        self.units_on_missions: List[MissionAllocation] = []
        
        # Process base allocations
        if units_on_bases:
            for base in units_on_bases:
                if not base:  # Skip empty allocations
                    continue
                
                # Create base allocation
                self.units_on_bases.append(
                    BaseAllocation(
                        node=base["node"],
                        count=base.get("count", 0)
                    )
                )
        
        # Process mission allocations
        if units_on_missions:
            for mission in units_on_missions:
                if not mission:  # Skip empty allocations
                    continue
                
                # Create mission allocation
                self.units_on_missions.append(
                    MissionAllocation(
                        mission=mission["mission"],
                        count=mission.get("count", 0),
                        cargo=mission.get("cargo")
                    )
                )

    def get_available_units(self, node: str) -> int:
        """
        Get number of available units at node
        
        Args:
            node: Base name to check
            
        Returns:
            Number of available units
        """
        if not node:
            return 0
            
        for base in self.units_on_bases:
            if base.node == node:
                return base.count
        return 0

    def assign_to_mission(self, node: str, mission: str, count: int, 
                         cargo: Optional[Dict] = None) -> bool:
        """
        Assign units from base to mission
        
        Args:
            node: Source base
            mission: Mission identifier  
            count: Number of units needed
            cargo: Cargo to transport
            
        Returns:
            True if assignment successful
        """
        if count > self.get_available_units(node):
            return False
            
        # Find base allocation
        base_allocation = next(
            (b for b in self.units_on_bases if b.node == node),
            None
        )
        if not base_allocation:
            return False
        
        # Update counts and create mission allocation
        base_allocation.count -= count
        self.units_on_missions.append(
            MissionAllocation(mission, count, cargo)
        )
        return True

    def complete_mission(self, mission: str, destination: str) -> Optional[Dict]:
        """
        Complete mission and return units to destination
        
        Args:
            mission: Mission identifier
            destination: Destination base
            
        Returns:
            Delivered cargo or None if mission not found
        """
        # Find mission allocation
        mission_allocation = next(
            (m for m in self.units_on_missions if m.mission == mission),
            None
        )
        if not mission_allocation:
            return None
            
        # Find or create destination allocation
        dest_allocation = next(
            (b for b in self.units_on_bases if b.node == destination),
            None
        )
        if not dest_allocation:
            dest_allocation = BaseAllocation(destination, 0)
            self.units_on_bases.append(dest_allocation)
        
        # Update counts
        dest_allocation.count += mission_allocation.count
        cargo = mission_allocation.cargo
        self.units_on_missions.remove(mission_allocation)
        return cargo

    def serialize(self) -> Dict:
        """Convert to JSON format"""
        return {
            "name": self.name,
            "type": self.transport_type,
            "category": self.category,
            "capacity": self.capacity,
            "routes": self.routes,
            "description": self.description,
            "is_player_available": self.is_player_available,
            "total_count": self.total_count,
            "units_on_bases": [
                {
                    "node": b.node,
                    "count": b.count
                } for b in self.units_on_bases
            ],
            "units_on_missions": [
                {
                    "mission": m.mission,
                    "count": m.count,
                    "cargo": m.cargo
                } for m in self.units_on_missions
            ]
        }

    @classmethod
    def from_json(cls, data: Dict):
        """Create from JSON data"""
        return cls(
            name=data["name"],
            transport_type=data["type"],
            category=data["category"],
            capacity=data["capacity"],
            routes=data["routes"],
            description=data["description"],
            is_player_available=data.get("is_player_available", True),
            total_count=data.get("total_count"),
            units_on_bases=data.get("units_on_bases"),
            units_on_missions=data.get("units_on_missions")
        )