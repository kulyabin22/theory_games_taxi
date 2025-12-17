"""Стратегии принятия решений водителями"""
import random
from typing import Dict, List, Optional
from core.models import Zone, Driver, Order
from core.enums import DriverStatus


class DriverStrategy:
    """Класс со стратегиями принятия решений водителями"""

    @staticmethod
    def calculate_expected_order_profit(driver: Driver, order: Order) -> float:
        """
        Рассчитать ожидаемую прибыль от конкретного заказа

        Args:
            driver: Водитель
            order: Заказ

        Returns:
            Ожидаемая прибыль
        """
        # 1. Доход от заказа
        order_income = order.price

        # 2. Стоимость подачи машины
        if driver.current_zone != order.start_zone:
            pickup_time = driver.current_zone.get_travel_time_to(order.start_zone)
            pickup_cost = pickup_time * driver.cost_per_minute
        else:
            pickup_time = random.uniform(2, 5)  # 2-5 минут в той же зоне
            pickup_cost = pickup_time * driver.cost_per_minute

        # 3. Стоимость выполнения поездки
        trip_time = order.estimated_duration
        trip_cost = trip_time * driver.cost_per_minute

        # 4. Альтернативная стоимость времени
        opportunity_cost = (pickup_time + trip_time) * driver.time_value_per_minute

        # 5. Общая прибыль
        total_profit = order_income - pickup_cost - trip_cost - opportunity_cost

        return total_profit

    @staticmethod
    def calculate_expected_profit_in_zone(
            driver: Driver,
            zone: Zone,
            drivers_count: int,
            available_orders: List[Order],
            travel_cost: bool = False
    ) -> float:
        """
        Рассчитать ожидаемый доход в зоне

        Args:
            driver: Водитель
            zone: Целевая зона
            drivers_count: Количество водителей в зоне
            available_orders: Доступные заказы в зоне
            travel_cost: Учитывать ли стоимость перемещения в зону

        Returns:
            Ожидаемый доход
        """
        total_expected_profit = 0.0

        # Если есть доступные заказы
        if available_orders:
            # Вероятность получить конкретный заказ
            probability_per_order = 1.0 / max(1, drivers_count + 1)

            # Считаем ожидаемый доход от каждого заказа
            for order in available_orders:
                profit = DriverStrategy.calculate_expected_order_profit(driver, order)
                if travel_cost:
                    # Вычитаем стоимость перемещения в зону
                    travel_time = driver.current_zone.get_travel_time_to(zone)
                    travel_cost_amount = travel_time * driver.cost_per_minute
                    profit -= travel_cost_amount

                total_expected_profit += probability_per_order * profit

        # Если нет доступных заказов, считаем ожидаемый доход от будущих заказов
        else:
            # Ожидаемое количество заказов в минуту
            expected_orders_per_minute = zone.base_demand_rate / max(1.0, zone.surge_multiplier)

            # Средняя стоимость заказа в зоне
            avg_order_price = 20.0 * zone.base_price_multiplier * zone.surge_multiplier

            # Ожидаемый доход в минуту
            expected_profit_per_minute = (expected_orders_per_minute * avg_order_price) / max(1, drivers_count + 1)

            # Минус стоимость ожидания
            waiting_cost_per_minute = driver.cost_per_minute + driver.time_value_per_minute

            total_expected_profit = expected_profit_per_minute - waiting_cost_per_minute

            if travel_cost:
                travel_time = driver.current_zone.get_travel_time_to(zone)
                travel_cost_amount = travel_time * driver.cost_per_minute
                total_expected_profit -= travel_cost_amount

        return total_expected_profit

    @staticmethod
    def decide_on_order(driver: Driver, order: Order) -> bool:
        """
        Принять решение о принятии заказа

        Args:
            driver: Водитель
            order: Предлагаемый заказ

        Returns:
            True если водитель принимает заказ
        """
        if driver.status != DriverStatus.FREE:
            return False

        profit = DriverStrategy.calculate_expected_order_profit(driver, order)
        min_threshold = driver.strategy_params["min_profit_threshold"]

        # Учитываем уровень удовлетворенности
        threshold_adjustment = 1.0 - (100 - driver.satisfaction) / 200
        effective_threshold = min_threshold * threshold_adjustment

        # С вероятностью, зависящей от терпения, принимаем заказы с меньшей прибылью
        if profit < effective_threshold and random.random() > driver.strategy_params["patience"]:
            return False

        return profit >= effective_threshold

    @staticmethod
    def decide_zone_move(
            driver: Driver,
            zones: List[Zone],
            drivers_in_zones: Dict[int, int],
            available_orders_by_zone: Dict[int, List[Order]]
    ) -> Optional[Zone]:
        """
        Принять решение о перемещении в другую зону

        Args:
            driver: Водитель
            zones: Список доступных зон
            drivers_in_zones: Количество водителей в каждой зоне
            available_orders_by_zone: Заказы доступные в каждой зоне

        Returns:
            Зона для перемещения или None если остаться
        """
        if driver.status != DriverStatus.FREE:
            return None

        # Эпсилон-жадная стратегия
        if random.random() < driver.strategy_params["exploration_rate"]:
            # Исследование: выбираем случайную зону
            target_zone = random.choice(zones)
            if target_zone != driver.current_zone:
                return target_zone
            return None

        # Эксплуатация: выбираем зону с максимальным ожидаемым доходом
        best_zone = None
        best_expected_profit = -float('inf')

        # Для зоны считаем доход от доступных заказов
        for zone in zones:
            expected_profit = DriverStrategy.calculate_expected_profit_in_zone(
                driver,
                zone,
                drivers_in_zones.get(zone.id, 0),
                available_orders_by_zone.get(zone.id, []),
                travel_cost=(zone != driver.current_zone)
            )

            if expected_profit > best_expected_profit:
                best_expected_profit = expected_profit
                best_zone = zone

        # Перемещаемся только если ожидаемая прибыль значительно выше
        if best_zone and best_zone != driver.current_zone and best_expected_profit > 5.0:
            return best_zone

        return None