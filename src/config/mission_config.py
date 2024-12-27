# Mission planning
PLANNING_HORIZON_DAYS = 7
MISSION_TIME_SLOTS = ["06:00", "12:00", "18:00", "00:00"]

# Global supply settings
GLOBAL_SUPPLY_RATES = {
    "airbase": {
        "fuel": 500,
        "ammo": 100
    }
}

# Mission generation
MIN_RESOURCE_THRESHOLD = 0.3  # 30% of capacity
OPTIMAL_RESOURCE_LEVEL = 0.8  # 80% of capacity