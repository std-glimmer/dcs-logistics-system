# Mission planning parameters
PLANNING_HORIZON_DAYS = 7  # Days to forecast ahead
MISSION_TIME_SLOTS = {
    "airbase": ["06:00", "12:00", "18:00", "00:00"],
    "FOB": ["08:00", "14:00", "20:00"],
    "COP": ["10:00", "16:00"]
}

# Global supply settings for major bases
GLOBAL_SUPPLY_RATES = {
    "airbase": {
        "fuel": 500,
        "ammo": 100
    },
    "FOB": {
        "fuel": 200,
        "ammo": 50
    }
}

# Resource thresholds
MIN_RESOURCE_THRESHOLD = 0.3  # Critical level (30% of capacity)
WARNING_RESOURCE_THRESHOLD = 0.5  # Warning level (50% of capacity)
OPTIMAL_RESOURCE_LEVEL = 0.8  # Target level (80% of capacity)
MAX_RESOURCE_LEVEL = 0.9  # Maximum fill level (90% of capacity)

# Mission priority factors
PRIORITY_WEIGHTS = {
    "node_type": {
        "airbase": 3.0,  # Critical infrastructure
        "FOB": 2.0,      # Forward Operating Base
        "COP": 1.0       # Combat Outpost
    },
    "resource_type": {
        "fuel": 1.0,
        "ammo": 1.2  # Slightly higher priority for ammo
    },
    "distance": 0.8  # Priority decreases with distance
}

# Transport allocation settings
TRANSPORT_SETTINGS = {
    "air": {
        "min_cargo_efficiency": 0.7,  # Minimum cargo/capacity ratio
        "max_missions_per_day": 3,    # Maximum missions per day per unit
    },
    "ground": {
        "min_cargo_efficiency": 0.8,
        "max_missions_per_day": 2,
    }
}

# Mission scheduling constraints
SCHEDULING_CONSTRAINTS = {
    "max_concurrent_missions": {
        "airbase": 5,
        "FOB": 3,
        "COP": 2
    },
    "min_mission_interval": {
        "airbase": 2,  # Hours between missions
        "FOB": 4,
        "COP": 6
    },
    "blackout_periods": [
        ("22:00", "05:00")  # Night operations restricted
    ]
}

# Resource consumption factors
CONSUMPTION_FACTORS = {
    "combat_operations": 1.5,    # 50% more during combat
    "bad_weather": 1.2,         # 20% more in bad weather
    "weekend": 0.8              # 20% less on weekends
}

# Mission validation rules
VALIDATION_RULES = {
    "min_resource_amount": {
        "fuel": 100,
        "ammo": 50
    },
    "max_resource_amount": {
        "fuel": 2000,
        "ammo": 1000
    },
    "required_resource_ratio": {
        "ammo": 0.3,  # Ammo should be at least 30% of fuel amount
        "fuel": 0.5   # Fuel should be at least 50% of total cargo
    }
}

# Relocation mission settings
RELOCATION_SETTINGS = {
    "max_distance": 200,        # Maximum relocation distance
    "min_efficiency_gain": 0.3, # Minimum improvement in resource distribution
    "cooldown_hours": 48       # Hours before another relocation allowed
}