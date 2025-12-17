"""Алгоритмы динамического ценообразования"""
from typing import Dict, List
from core.models import Zone, Driver
from core.enums import DriverStatus


class PricingStrategy:
    """Класс для управления динамическим ценообразованием"""

    @staticmethod
    def update_surge_multiplier(zone: Zone, demand_supply_ratio: float) -> None:
        """
        Обновить динамический множитель цены для зоны

        Args:
            zone: Зона для обновления
            demand_supply_ratio: Соотношение спроса и предложения
        """
        # Простая модель динамического ценообразования
        if demand_supply_ratio > 1.5:
            zone.surge_multiplier = min(3.0, zone.surge_multiplier * 1.2)
        elif demand_supply_ratio > 1.2:
            zone.surge_multiplier = min(2.5, zone.surge_multiplier * 1.1)
        elif demand_supply_ratio < 0.8:
            zone.surge_multiplier = max(0.7, zone.surge_multiplier * 0.95)
        elif demand_supply_ratio < 0.5:
            zone.surge_multiplier = max(0.5, zone.surge_multiplier * 0.9)
        else:
            # Плавное возвращение к 1.0
            if zone.surge_multiplier > 1.0:
                zone.surge_multiplier = max(1.0, zone.surge_multiplier * 0.98)
            elif zone.surge_multiplier < 1.0:
                zone.surge_multiplier = min(1.0, zone.surge_multiplier * 1.02)

    @staticmethod
    def calculate_order_price(zone: Zone, destination_zone: Zone, base_fare: float = 5.0) -> float:
        """
        Рассчитать стоимость заказа

        Args:
            zone: Зона подачи
            destination_zone: Зона назначения
            base_fare: Базовая стоимость

        Returns:
            Стоимость поездки
        """
        distance_factor = zone.get_travel_time_to(destination_zone) / 10.0
        price = (base_fare * distance_factor *
                 zone.base_price_multiplier *
                 zone.surge_multiplier)
        return round(price, 2)

    @staticmethod
    def update_zones_pricing(zones: Dict[int, Zone], drivers: Dict[int, Driver]) -> None:
        """
        Обновить динамическое ценообразование для всех зон

        Args:
            zones: Словарь зон
            drivers: Словарь водителей
        """
        for zone in zones.values():
            # Считаем количество свободных водителей в зоне
            free_drivers = len([d for d in drivers.values()
                                if d.current_zone == zone and
                                d.status == DriverStatus.FREE])

            # Рассчитываем соотношение спроса и предложения
            demand = zone.base_demand_rate * zone.surge_multiplier
            supply = max(1, free_drivers)
            ratio = demand / supply

            # Обновляем множитель цены
            PricingStrategy.update_surge_multiplier(zone, ratio)