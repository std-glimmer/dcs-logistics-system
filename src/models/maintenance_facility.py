from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class MaintenanceFacility:
    node: str
    max_concurrent_repairs: int
    repair_queue: List[Dict] = field(default_factory=list)
    current_repairs: Dict[str, Dict] = field(default_factory=dict)
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

    def process_daily_repairs(self, repair_rate: int) -> List[str]:
        """Process repairs for all units in facility"""
        completed_units = []

        # Process current repairs
        for unit_id, repair in list(self.current_repairs.items()):
            repair["maintance"] += repair_rate
            if repair["maintance"] >= 100:
                completed_units.append(unit_id)
                self._complete_repair(unit_id)

        # Process queue if capacity available
        while self.repair_queue and len(self.current_repairs) < self.max_concurrent_repairs:
            next_unit = self.repair_queue.pop(0)
            self._start_repair(next_unit["unit_id"], next_unit["maintance"])

        return completed_units

    def _start_repair(self, unit_id: str, current_maintance: int) -> None:
        """Start repair process for unit"""
        self.current_repairs[unit_id] = {
            "maintance": current_maintance,
            "started_at": datetime.now()
        }

    def _complete_repair(self, unit_id: str) -> None:
        """Complete repair and update statistics"""
        repair = self.current_repairs.pop(unit_id)
        repair_time = (datetime.now() - repair["started_at"]).days
        
        self.stats["total_repairs"] += 1
        self.stats["total_days"] += repair_time
        self.stats["units_processed"].add(unit_id)

    def has_capacity(self) -> bool:
        """Check if facility can accept new units"""
        return len(self.current_repairs) < self.max_concurrent_repairs

    def serialize(self) -> Dict:
        """Serialize facility data for storage"""
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
    def deserialize(cls, data: Dict) -> 'MaintenanceFacility':
        """Create facility from serialized data"""
        facility = cls(
            node=data["node"],
            max_concurrent_repairs=data["max_concurrent_repairs"]
        )
        facility.repair_queue = data["repair_queue"]
        facility.current_repairs = data["current_repairs"]
        facility.stats = {
            "total_repairs": data["stats"]["total_repairs"],
            "total_days": data["stats"]["total_days"],
            "units_processed": set(data["stats"]["units_processed"])
        }
        return facility