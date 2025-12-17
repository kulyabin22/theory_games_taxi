"""Алгоритмы динамического ценообразования (MVP)"""
from typing import Dict
from core.models import Zone, Driver
from core.enums import DriverStatus


class PricingStrategy:
    @staticmethod
    def calculate_order_price(zone: Zone, destination_zone: Zone, base_fare: float = 5.0) -> float:
        distance_factor = zone.get_travel_time_to(destination_zone) / 10.0
        price = base_fare * distance_factor * zone.base_price_multiplier * zone.surge_multiplier
        return round(float(price), 2)

    @staticmethod
    def update_zones_pricing(zones: Dict[int, Zone], drivers: Dict[int, Driver], pending_by_zone: Dict[int, int] | None = None) -> None:
        """
        MVP: обновляем surge на основе ratio = (pending_orders + 1) / (free_drivers + 1)
        pending_by_zone можно передать извне; если нет — оцениваем как 0 (surge будет стремиться к 1).
        """
        for zone in zones.values():
            free_drivers = sum(
                1 for d in drivers.values()
                if d.current_zone == zone and d.status == DriverStatus.FREE
            )

            pending = 0
            if pending_by_zone is not None:
                pending = int(pending_by_zone.get(zone.id, 0))

            ratio = (pending + 1.0) / (free_drivers + 1.0)

            # таргет: линейно, с клипом
            alpha = 0.8
            target = 1.0 + alpha * (ratio - 1.0)
            target = max(0.7, min(3.0, target))

            # сглаживание, чтобы не дергалось
            smooth = 0.2
            zone.surge_multiplier = (1 - smooth) * zone.surge_multiplier + smooth * target
            zone.surge_multiplier = max(0.7, min(3.0, zone.surge_multiplier))
