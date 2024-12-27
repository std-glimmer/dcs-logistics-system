from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class MaintenanceFacility:
    node: str  # Facility location
    max_concurrent_repairs: int  # Maximum simultaneous repairs
    repair_queue: List[Dict] = field(default_factory=list)  # Units waiting for repair
    current_repairs: Dict[str, Dict] = field(default_factory=dict)  # Active repairs
    stats: Dict = field(default_factory=lambda: {
        "total_repairs": 0,
        "total_days": 0,
        "units_processed": set()
    })

    def add_unit_for_repair(self, unit_id: str, current_maintance: int) -> bool:
        """Add unit to repair queue or start repair if capacity available"""
        if len(self.current_repairs) >= self.max_concurrent_repairs:
            self.repair_queue.append({
                "unit_id": unit_id,
                "maintance": current_maintance,
                "queued_at": datetime.now()
            })
            return False

        self._start_repair(unit_id, current_maintance)
        return True

    def process_daily_maintenance(self) -> List[str]:
        """Process daily maintenance and return completed unit IDs"""
        completed_units = []

        # Process current repairs
        for unit_id, repair_data in list(self.current_repairs.items()):
            repair_data["days_remaining"] -= 1
            repair_data["maintance"] += 25

            if repair_data["days_remaining"] <= 0:
                completed_units.append(unit_id)
                self.current_repairs.pop(unit_id)
                self.stats["total_repairs"] += 1
                self.stats["units_processed"].add(unit_id)

        # Process queue if capacity available
        while self.repair_queue and len(self.current_repairs) < self.max_concurrent_repairs:
            next_unit = self.repair_queue.pop(0)
            self._start_repair(next_unit["unit_id"], next_unit["maintance"])

        return completed_units

    def _start_repair(self, unit_id: str, current_maintance: int) -> None:
        """Start repair process for unit"""
        days_needed = (100 - current_maintance + 24) // 25  # Round up
        self.current_repairs[unit_id] = {
            "days_remaining": days_needed,
            "maintance": current_maintance,
            "started_at": datetime.now()
        }
        self.stats["total_days"] += days_needed

    def get_status(self) -> Dict:
        """Get current facility status"""
        return {
            "node": self.node,
            "active_repairs": len(self.current_repairs),
            "queue_length": len(self.repair_queue),
            "capacity": self.max_concurrent_repairs,
            "total_repairs": self.stats["total_repairs"],
            "average_repair_time": (
                self.stats["total_days"] / len(self.stats["units_processed"])
                if self.stats["units_processed"] else 0
            )
        }

    def serialize(self) -> Dict:
        """Convert to JSON format"""
        return {
            "node": self.node,
            "max_concurrent_repairs": self.max_concurrent_repairs,
            "repair_queue": self.repair_queue,
            "current_repairs": self.current_repairs,
            "stats": {
                "total_repairs": self.stats["total_repairs"],
                "total_days": self.stats["total_days"],
                "units_processed": list(self.stats["units_processed"])
            }
        }

    @classmethod
    def from_json(cls, data: Dict):
        """Create from JSON data"""
        facility = cls(
            node=data["node"],
            max_concurrent_repairs=data["max_concurrent_repairs"]
        )
        facility.repair_queue = data.get("repair_queue", [])
        facility.current_repairs = data.get("current_repairs", {})
        
        stats = data.get("stats", {})
        facility.stats = {
            "total_repairs": stats.get("total_repairs", 0),
            "total_days": stats.get("total_days", 0),
            "units_processed": set(stats.get("units_processed", []))
        }
        return facility