"""Стратегии принятия решений водителями (MVP)"""
import random
from typing import Dict, List, Optional
from core.models import Zone, Driver, Order
from core.enums import DriverStatus


class DriverStrategy:
    @staticmethod
    def calculate_expected_order_profit(driver: Driver, order: Order) -> float:
        income = float(order.price)

        if driver.current_zone == order.start_zone:
            pickup_time = 2.0
        else:
            pickup_time = driver.current_zone.get_travel_time_to(order.start_zone)

        trip_time = float(order.estimated_duration)
        total_time = pickup_time + trip_time

        cost = total_time * (driver.cost_per_minute + driver.time_value_per_minute)
        return income - cost

    @staticmethod
    def decide_on_order(driver: Driver, order: Order) -> bool:
        if driver.status != DriverStatus.FREE:
            return False
        profit = DriverStrategy.calculate_expected_order_profit(driver, order)
        threshold = float(driver.strategy_params.get("min_profit_threshold", 0.0))
        return profit >= threshold

    @staticmethod
    def decide_zone_move(driver, zones, drivers_per_zone, available_orders_by_zone):
        # Текущая зона
        current = driver.current_zone

        # Оценка всех зон
        scores = {}
        for zone in zones:
            if zone == current:
                continue

            # Базовый доход (surge * базовая цена)
            surge_bonus = zone.surge_multiplier ** 2  # Квадратичный бонус!

            # Прогноз спроса (простейший - по текущим заказам)
            forecast_demand = len(available_orders_by_zone[zone.id]) * 1.5

            # Конкуренция (чем меньше водителей - тем лучше)
            competition = max(1, drivers_per_zone.get(zone.id, 0))

            # Время в пути
            travel_cost = driver.current_zone.get_travel_time_to(zone) * driver.cost_per_minute

            # Итоговый score
            scores[zone] = (
                    surge_bonus * forecast_demand / competition - travel_cost
            )

        # С вероятностью exploration_rate выбираем случайную зону
        if random.random() < driver.strategy_params["exploration_rate"]:
            return random.choice([z for z in zones if z != current])

        # Иначе - лучшую по score
        if scores:
            best_zone = max(scores, key=scores.get)
            if scores[best_zone] > 0:  # Только если это выгодно
                return best_zone

        return None  # Остаемся на месте
    '''def decide_zone_move(
        driver: Driver,
        zones: List[Zone],
        drivers_in_zones: Dict[int, int],
        available_orders_by_zone: Dict[int, List[Order]],
    ) -> Optional[Zone]:
        if driver.status != DriverStatus.FREE:
            return None

        current_pending = len(available_orders_by_zone.get(driver.current_zone.id, []))
        if current_pending > 0:
            return None
        # немного шума/исследования
        if random.random() < float(driver.strategy_params.get("exploration_rate", 0.05)):
            z = random.choice(zones)
            return z if z != driver.current_zone else None

        best_zone = None
        best_score = -1e9

        for z in zones:
            pending_here = len(available_orders_by_zone.get(z.id, []))
            free_here = int(drivers_in_zones.get(z.id, 0))

            # ожидаемые заказы/мин: базовый спрос
            expected_orders = z.base_demand_rate

            # ожидаемый доход/заказ: растёт с surge и базовой ценой зоны
            expected_price = 12.0 * z.base_price_multiplier * z.surge_multiplier

            # конкуренция: делим на число свободных+1
            expected_income_per_min = (expected_orders * expected_price) / (free_here + 1.0)

            # плюс бонус за уже висящие pending (явный сигнал дисбаланса)
            expected_income_per_min += 2.0 * pending_here

            # штраф ожидания/работы
            wait_cost_per_min = driver.cost_per_minute + driver.time_value_per_minute
            score = expected_income_per_min - wait_cost_per_min

            # штраф за переезд
            if z != driver.current_zone:
                travel = driver.current_zone.get_travel_time_to(z)
                score -= travel * driver.cost_per_minute

            if score > best_score:
                best_score = score
                best_zone = z

        # двигаемся, если реально лучше, чем оставаться
        if best_zone and best_zone != driver.current_zone:
            # небольшой порог, чтобы не дергались туда-сюда
            if best_score > 0.5:
                return best_zone

        return None'''
