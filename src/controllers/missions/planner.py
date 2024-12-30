from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ...models.node import Node
from ...models.mission import Mission, Resource, Route
from ...config.mission_config import (
    PLANNING_HORIZON_DAYS, 
    MISSION_TIME_SLOTS,
    MIN_RESOURCE_THRESHOLD,
    OPTIMAL_RESOURCE_LEVEL
)

class MissionPlanner:
    def __init__(self, node_controller, transport_controller, logger):
        self.node_controller = node_controller
        self.transport_controller = transport_controller
        self.logger = logger
        self.forecast_days = PLANNING_HORIZON_DAYS

    def forecast_resources(self, start_date: datetime) -> Dict[str, Dict]:
        """Calculate resource forecast for all nodes"""
        forecast = {}
        
        for node in self.node_controller.get_all_nodes():
            forecast[node.name] = self._forecast_node_resources(node, start_date)
            
        return forecast
    
    def _forecast_node_resources(self, node: Node, start_date: datetime) -> Dict:
        """Calculate resource forecast for specific node"""
        forecast = {
            "fuel": {"daily": []},
            "ammo": {"daily": []}
        }
        
        # Get child nodes consumption
        child_consumption = {
            "fuel": 0,
            "ammo": 0
        }
        
        if node.name in self.node_controller.hierarchy:
            for child_name in self.node_controller.hierarchy[node.name]:
                child = self.node_controller.get_node(child_name)
                child_consumption["fuel"] += child.consumption["fuel"]
                child_consumption["ammo"] += child.consumption["ammo"]
        
        # Calculate daily levels
        for resource in ["fuel", "ammo"]:
            current_level = node.state[resource]
            daily_usage = node.consumption[resource] + child_consumption[resource]
            
            for day in range(self.forecast_days):
                current_level = max(0, current_level - daily_usage)
                
                forecast[resource]["daily"].append({
                    "date": (start_date + timedelta(days=day)).strftime("%Y-%m-%d"),
                    "level": current_level,
                    "consumption": daily_usage,
                    "is_critical": current_level <= daily_usage * 2
                })
                
        return forecast

    def create_missions(self, forecast: Dict, start_date: datetime, cycle: int) -> List[Mission]:
        """Создание миссий на основе прогноза"""
        missions = []
        
        # Расчет приоритетов для узлов
        priorities = self._calculate_node_priorities(forecast)
        
        # Создание миссий для узлов с высоким приоритетом
        for priority in priorities:
            if priority["priority_score"] < 50:  # Пропускаем низкоприоритетные узлы
                continue
                
            node = priority["node"]
            resource_type = priority["resource"]
            
            # Поиск источника снабжения
            source = self._find_best_supply_source(node, resource_type)
            if not source:
                self.logger.warning(f"Не найден источник снабжения для {node.name}")
                continue
            
            # Определение транспорта
            transport_info = self._find_optimal_transport(source, node, resource_type)
            if not transport_info:
                # Планируем миссию релокации транспорта
                relocation_mission = self._plan_transport_relocation(source, node, cycle)
                if relocation_mission:
                    missions.append(relocation_mission)
                continue

            # Расчет количества ресурсов с учетом транспорта
            amount = self._calculate_delivery_amount(
                node, 
                resource_type,
                transport_info["capacity"] * transport_info["units"]
            )

            # Создание миссии
            mission = Mission(
                mission_id=f"M{cycle}_{source.name}_{node.name}_{resource_type}",
                date=priority["delivery_date"],
                time=self._get_delivery_time(node),
                route=Route(
                    from_node=source.name,
                    to_node=node.name
                ),
                resources=[Resource(resource_type, amount)],
                transport_type=transport_info["type"],
                creation_cycle=cycle
            )

            # Назначение транспорта
            mission.assign_transport(
                vehicle_name=transport_info["vehicle"],
                vehicle_type=transport_info["type"],
                units=transport_info["units"],
                capacity=transport_info["capacity"]
            )
            
            missions.append(mission)
            
            self.logger.info(
                f"Создана миссия {mission.id} для {node.name}: "
                f"{amount} {resource_type} ({transport_info['vehicle']} x{transport_info['units']})"
            )
                
        return missions

    def _find_optimal_transport(self, source: Node, dest: Node, 
                            resource_type: str) -> Optional[Dict]:
        """Поиск оптимального транспорта"""
        best_result = None
        best_efficiency = 0

        # Расчет требуемого количества ресурсов
        required_amount = dest.consumption[resource_type] * 7
        if dest.name in self.node_controller.hierarchy:
            child_consumption = sum(
                self.node_controller.get_node(child).consumption[resource_type]
                for child in self.node_controller.hierarchy[dest.name]
            )
            required_amount += child_consumption * 3

        for route_type in dest.supply_routes:
            transport = self.transport_controller.find_available_transport(
                source.name,
                route_type,
                required_amount
            )
            
            if not transport:
                continue

            # Расчет необходимых юнитов
            units_needed = max(1, int((required_amount + transport.capacity - 1) 
                                    // transport.capacity))
            
            if units_needed > transport.get_available_units(source.name):
                continue

            # Расчет эффективности
            efficiency = required_amount / (units_needed * transport.capacity)
            
            if efficiency > best_efficiency:
                best_efficiency = efficiency
                best_result = {
                    "vehicle": transport.name,
                    "type": transport.transport_type,
                    "units": units_needed,
                    "capacity": transport.capacity
                }

        return best_result
    
    def _calculate_transport_efficiency(self, transport: Dict, 
                                     source: Node, dest: Node) -> float:
        """Расчет эффективности использования транспорта"""
        base_efficiency = transport.capacity / transport.total_count
        
        # Учитываем расстояние
        distance_factor = 1.0
        if hasattr(source, "distance_to"):
            distance = source.distance_to(dest)
            distance_factor = max(0.5, 1 - (distance / 1000))
            
        # Учитываем тип транспорта
        type_factor = 1.2 if transport.transport_type == "air" else 1.0
            
        return base_efficiency * distance_factor * type_factor
    
    def _plan_transport_relocation(self, source: Node, dest: Node, cycle: int) -> Optional[Mission]:
        """
        Планирование релокации транспорта
        
        Args:
            source: Узел, куда нужен транспорт
            dest: Узел назначения
        
        Returns:
            Mission если релокация запланирована, None если нет
        """
        for node in self.node_controller.get_all_nodes():
            if node == source or node == dest:
                continue
                
            for route_type in dest.supply_routes:
                transport = self.transport_controller.find_available_transport(
                    node.name,
                    route_type,
                    0  # Ищем любой доступный транспорт
                )
                
                if transport and transport.get_available_units(node.name) > 0:
                    # Рассчитываем количество транспорта для релокации
                    units_to_relocate = min(
                        2,  # Перемещаем не более 2 единиц за раз
                        transport.get_available_units(node.name)
                    )
                    
                    # Создаем миссию релокации
                    relocation_mission = Mission(
                        mission_id=f"RELOC_{transport.name}_{node.name}_{source.name}",
                        date=datetime.now().strftime("%Y-%m-%d"),
                        time="00:00",
                        route=Route(
                            from_node=node.name,
                            to_node=source.name
                        ),
                        resources=[Resource('fuel', 0)],  # Пустой список ресурсов для релокации
                        transport_type=transport.transport_type,
                        creation_cycle=cycle,
                        is_relocation=True
                    )
                    
                    # Назначаем транспорт на миссию
                    relocation_mission.assign_transport(
                        vehicle_name=transport.name,
                        vehicle_type=transport.transport_type,
                        units=units_to_relocate,
                        capacity=transport.capacity
                    )
                    
                    self.logger.info(
                        f"Создана миссия релокации {relocation_mission.id}: "
                        f"{transport.name} ({units_to_relocate} units) "
                        f"из {node.name} в {source.name}"
                    )
                    
                    return relocation_mission
                    
        self.logger.warning(f"Не найден доступный транспорт для релокации в {source.name}")
        return None
    
    def _calculate_node_priorities(self, forecast: Dict) -> List[Dict]:
        """Calculate priority scores for all nodes"""
        priorities = []
        
        for node in self.node_controller.get_all_nodes():
            for resource in ["fuel", "ammo"]:
                node_forecast = forecast[node.name][resource]["daily"]
                
                # Find critical day
                critical_day = None
                delivery_date = None
                
                for i, day in enumerate(node_forecast):
                    if day["is_critical"]:
                        critical_day = i
                        delivery_date = day["date"]
                        break
                
                if critical_day is not None:
                    priority = {
                        "node": node,
                        "resource": resource,
                        "days_until_critical": critical_day,
                        "delivery_date": delivery_date,
                        "priority_score": self._calculate_priority_score(
                            node, critical_day, resource, node_forecast[0]["level"]
                        )
                    }
                    priorities.append(priority)
                    
        return sorted(priorities, key=lambda x: x["priority_score"], reverse=True)

    def _calculate_priority_score(self, node: Node, days: int, 
                                resource: str, current_level: float) -> float:
        """Calculate mission priority score based on multiple factors"""
        # Base priority based on days until critical
        base_score = 100 - (days * 10)
        
        # Node type importance
        type_multiplier = {
            "airbase": 3.0,
            "FOB": 2.0,
            "COP": 1.0
        }[node.node_type]
        
        # Resource type priority
        resource_multiplier = {
            "fuel": 1.0,
            "ammo": 1.2  # Higher priority for ammo
        }[resource]
        
        # Current level factor
        optimal_level = node.consumption[resource] * 7  # 7 days supply
        level_factor = 1 + (1 - (current_level / optimal_level))
        
        # Child nodes factor
        child_factor = 1.0
        if node.name in self.node_controller.hierarchy:
            child_factor = 1.5  # 50% boost if node has children
            
        return base_score * type_multiplier * resource_multiplier * level_factor * child_factor

    def _find_best_supply_source(self, node: Node, resource: str) -> Optional[Node]:
        """Find best source for supplies based on availability and distance"""
        def has_sufficient_resources(source: Node) -> bool:
            return source.state[resource] >= (
                node.consumption[resource] * 7 +  # 7 days for destination
                source.consumption[resource] * 3   # 3 days buffer for source
            )
        
        # First try parent node
        for parent, children in self.node_controller.hierarchy.items():
            if node.name in children:
                parent_node = self.node_controller.get_node(parent)
                if has_sufficient_resources(parent_node):
                    return parent_node
        
        # Then try airbases
        for potential in self.node_controller.get_all_nodes():
            if (potential.node_type == "airbase" and 
                has_sufficient_resources(potential)):
                return potential
                
        return None

    def _calculate_delivery_amount(self, node: Node, resource: str, 
                                 max_capacity: float) -> float:
        """Расчет оптимального количества ресурсов для доставки"""
        # Базовая потребность на неделю
        base_amount = node.consumption[resource] * 7
        
        # Добавляем буфер для дочерних узлов
        if node.name in self.node_controller.hierarchy:
            child_consumption = sum(
                self.node_controller.get_node(child).consumption[resource]
                for child in self.node_controller.hierarchy[node.name]
            )
            base_amount += child_consumption * 3
        
        # Учитываем доступную вместимость транспорта
        amount = min(base_amount, max_capacity)
        
        # Округляем до сотен
        return amount

    def _get_delivery_time(self, node: Node) -> str:
        """Get appropriate delivery time slot based on node type"""
        return MISSION_TIME_SLOTS[node.node_type][0]