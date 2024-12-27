from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class TransportUnit:
    id: str  # Vehicle identifier
    maintance: int  # Maintenance level (0-100)
    status: str  # ready/in_mission/on_repair
    stats: Dict  # Mission history stats
    cargo: Optional[Dict] = None  # Current cargo
    repair_remaining: Optional[int] = None  # Days until repair complete

@dataclass
class BaseAllocation:
    node: str  # Base location
    count: int  # Number of vehicles
    units: Optional[List[TransportUnit]] = None  # Individual units (air only)

@dataclass
class MissionAllocation:
    mission: str  # Mission identifier
    count: int  # Vehicles assigned
    cargo: Optional[Dict] = None  # Mission cargo
    units: Optional[List[TransportUnit]] = None  # Individual units (air only)

class Transport:
    def __init__(self, name: str, transport_type: str, category: str,
                 capacity: int, routes: List[str], description: str,
                 is_player_available: bool = True,
                 total_count: Optional[int] = None,
                 units_on_bases: Optional[List[Dict]] = None,
                 units_on_missions: Optional[List[Dict]] = None):
        self.name = name
        self.transport_type = transport_type
        self.category = category
        self.capacity = capacity
        self.routes = routes
        self.description = description
        self.is_player_available = is_player_available
        self.total_count = total_count
        
        # Initialize allocations
        self.units_on_bases: List[BaseAllocation] = []
        self.units_on_missions: List[MissionAllocation] = []
        
        if units_on_bases:
            for base in units_on_bases:
                units = None
                if base and "units" in base and base["units"]:  # Check if base and units exist
                    units = [TransportUnit(**u) for u in base["units"]]
                self.units_on_bases.append(
                    BaseAllocation(
                    base.get("node", ""),  # Default empty string if node is null
                    base.get("count", 0),  # Default 0 if count is null
                    units
                    )
                )

        if units_on_missions:
            for mission in units_on_missions:
                units = None
                if mission and "units" in mission and mission["units"]:  # Check if mission and units exist
                    units = [TransportUnit(**u) for u in mission["units"]]
                self.units_on_missions.append(
                    MissionAllocation(
                    mission.get("mission", ""),  # Default empty string if mission is null
                    mission.get("count", 0),  # Default 0 if count is null
                    mission.get("cargo"),  # cargo can be None
                    units
                    )
                )

    def get_available_units(self, node: str) -> int:
        """Get number of available units at node"""
        if not node:
            return 0
            
        for base in self.units_on_bases or []:
            if base and base.node == node:
                if self.transport_type == "air":
                    if base.units:
                        return sum(1 for u in base.units if u and u.status == "ready")
                    return 0
                return base.count or 0
        return 0

    def assign_to_mission(self, node: str, mission: str, count: int, 
                         cargo: Optional[Dict] = None) -> bool:
        """Move units from base to mission"""
        if count > self.get_available_units(node):
            return False
            
        base_allocation = next(b for b in self.units_on_bases if b.node == node)
        mission_units = None
        
        if self.transport_type == "air":
            mission_units = []
            ready_units = [u for u in base_allocation.units if u.status == "ready"][:count]
            for unit in ready_units:
                unit.status = "in_mission"
                unit.cargo = cargo
                mission_units.append(unit)
                base_allocation.units.remove(unit)
        
        base_allocation.count -= count
        self.units_on_missions.append(
            MissionAllocation(mission, count, cargo, mission_units)
        )
        return True

    def complete_mission(self, mission: str, destination: str) -> Optional[Dict]:
        """Complete mission and move units to destination"""
        mission_allocation = next(
            (m for m in self.units_on_missions if m.mission == mission), 
            None
        )
        if not mission_allocation:
            return None
            
        # Add units to destination
        dest_allocation = next(
            (b for b in self.units_on_bases if b.node == destination),
            None
        )
        if not dest_allocation:
            dest_allocation = BaseAllocation(destination, 0, [])
            self.units_on_bases.append(dest_allocation)
            
        if self.transport_type == "air":
            for unit in mission_allocation.units:
                unit.status = "ready"
                unit.cargo = None
                dest_allocation.units.append(unit)
        
        dest_allocation.count += mission_allocation.count
        self.units_on_missions.remove(mission_allocation)
        return mission_allocation.cargo

    def serialize(self) -> dict:
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
                    "count": b.count,
                    "units": [vars(u) for u in b.units] if b.units else None
                }
                for b in self.units_on_bases
            ],
            "units_on_missions": [
                {
                    "mission": m.mission,
                    "count": m.count,
                    "cargo": m.cargo,
                    "units": [vars(u) for u in m.units] if m.units else None
                }
                for m in self.units_on_missions
            ]
        }

    @classmethod
    def from_json(cls, data: dict):
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