class Node:
    WARNING_DAYS = 3

    def __init__(self, name, node_type, state, consumption, supply_routes):
        self.name = name
        self.node_type = node_type
        self.state = state
        self.consumption = consumption
        self.supply_routes = supply_routes
        self.emergency_mode = False

    def apply_consumption(self):
        """Apply daily consumption and check resource levels"""
        warnings = []

        # Process each resource
        for resource in ['fuel', 'ammo']:
            # Calculate new value but don't apply yet
            new_value = self.state[resource] - self.consumption[resource]
            
            # Check if would go below 0
            if new_value <= 0:
                self.state[resource] = 0
                if not self.emergency_mode:
                    self.emergency_mode = True
                    warnings.append(f"EMERGENCY: Node has depleted {resource} and entered emergency mode")
            else:
                # Apply consumption and check warning threshold
                self.state[resource] = new_value
                if self.consumption[resource] > 0:
                    days_remaining = new_value / self.consumption[resource]
                    if days_remaining <= self.WARNING_DAYS:
                        warnings.append(f"{resource}: {days_remaining:.1f} days remaining")

        return warnings if warnings else None

    def to_json(self):
        return {
            "name": self.name,
            "type": self.node_type,
            "state": self.state,
            "consumption": self.consumption,
            "supplyRoutes": self.supply_routes,
            "emergency_mode": self.emergency_mode
        }

    @classmethod
    def from_json(cls, json_data):
        node = cls(
            name=json_data['name'],
            node_type=json_data['type'],
            state=json_data['state'],
            consumption=json_data['consumption'],
            supply_routes=json_data['supplyRoutes']
        )
        node.emergency_mode = json_data.get('emergency_mode', False)
        return node