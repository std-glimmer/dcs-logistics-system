from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class Resource:
    """Ресурс для транспортировки"""
    type: str
    quantity: float

@dataclass
class Route:
    """Маршрут миссии"""
    from_node: str
    to_node: str

@dataclass
class TransportAssignment:
    """Назначенный транспорт"""
    vehicle_type: str
    vehicle_name: str
    units: int
    capacity: float
    
class Mission:
    def __init__(self, 
                 mission_id: str,
                 date: str,
                 time: str,
                 route: Route,
                 resources: List[Resource],
                 transport_type: str,
                 creation_cycle: int,
                 is_relocation: bool = False,
                 original_mission_id: Optional[str] = None):
        """
        Initialize mission
        
        Args:
            mission_id: Unique identifier
            date: Mission date
            time: Mission time
            route: Route details
            resources: Resources to transport
            transport_type: Required transport type
            creation_cycle: Creation cycle number
            is_relocation: If this is a relocation mission
            original_mission_id: ID of original mission for relocations
        """
        self.id = self._sanitize_id(mission_id)
        self.date = date
        self.time = time
        self.route = route
        self.resources = resources
        self.transport_type = transport_type
        self.status = "scheduled"
        self.creation_cycle = creation_cycle
        self.is_relocation = is_relocation
        self.original_mission_id = original_mission_id
        self.transport: TransportAssignment = None
        self.completed_at: Optional[str] = None

    @staticmethod
    def _sanitize_id(mission_id: str) -> str:
        """Replace spaces with underscores in mission ID"""
        return mission_id.replace(" ", "_")

    def assign_transport(self, vehicle_name: str, vehicle_type: str, 
                        units: int, capacity: float) -> None:
        """Assign transport to mission"""
        self.transport = TransportAssignment(
            vehicle_type=vehicle_type,
            vehicle_name=vehicle_name,
            units=units,
            capacity=capacity
        )

    def complete(self) -> None:
        """Mark mission as completed"""
        self.status = "completed"
        self.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    def to_json(self) -> Dict:
        """Convert mission to JSON format"""
        data = {
            "id": self.id,
            "date": self.date,
            "time": self.time,
            "route": {
                "from": self.route.from_node,
                "to": self.route.to_node
            },
            "resources": [
                {"type": r.type, "quantity": r.quantity}
                for r in self.resources
            ],
            "transport_type": self.transport_type,
            "status": self.status,
            "creation_cycle": self.creation_cycle,
            "is_relocation": self.is_relocation
        }

        if self.original_mission_id:
            data["original_mission_id"] = self.original_mission_id

        if self.transport:
            data["transport"] = {
                "vehicle": self.transport.vehicle_name,
                "type": self.transport.vehicle_type,
                "units": self.transport.units,
                "capacity": self.transport.capacity
            }

        if self.completed_at:
            data["completed_at"] = self.completed_at

        return data

    @classmethod
    def from_json(cls, json_data: Dict):
        """Create mission from JSON data"""
        mission = cls(
            mission_id=json_data["id"],
            date=json_data["date"],
            time=json_data["time"],
            route=Route(
                from_node=json_data.route.from_node,
                to_node=json_data.route.to_node
            ),
            resources=[
                Resource(r["type"], r["quantity"])
                for r in json_data["resources"]
            ],
            transport_type=json_data["transport_type"],
            creation_cycle=json_data["creation_cycle"],
            is_relocation=json_data.get("is_relocation", False),
            original_mission_id=json_data.get("original_mission_id")
        )

        mission.status = json_data["status"]

        if "transport" in json_data:
            mission.assign_transport(
                vehicle_name=json_data["transport"]["vehicle"],
                vehicle_type=json_data["transport"]["type"],
                units=json_data["transport"]["units"],
                capacity=json_data["transport"]["capacity"]
            )

        if "completed_at" in json_data:
            mission.completed_at = json_data["completed_at"]

        return mission