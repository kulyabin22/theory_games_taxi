"""Модели данных: Zone, Driver, Order (MVP)"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional
import random
import numpy as np

from core.enums import DriverStatus, OrderStatus


@dataclass
class Zone:
    id: int
    name: str
    base_demand_rate: float  # заказов в минуту
    base_price_multiplier: float = 1.0
    surge_multiplier: float = 1.0
    travel_time_matrix: Dict[str, float] = field(default_factory=dict)
    color: str = "white"

    def get_travel_time_to(self, target_zone: "Zone") -> float:
        key = f"{self.name}->{target_zone.name}"
        return float(self.travel_time_matrix.get(key, 10.0))

    def generate_demand(self, time_interval: float = 1.0) -> int:
        """
        MVP: спрос не зависит от surge (чтобы сначала проверить механику стимулов).
        """
        lam = max(0.0, self.base_demand_rate * time_interval/ max(1.0, self.surge_multiplier ** 0.7))
        return int(np.random.poisson(lam))

    def __hash__(self):
        return hash(self.id)

    def __str__(self) -> str:
        return f"Zone({self.name}, demand={self.base_demand_rate:.2f}/min, surge={self.surge_multiplier:.2f})"


@dataclass
class Order:
    id: int
    start_zone: Zone
    end_zone: Zone
    price: float
    status: OrderStatus = OrderStatus.PENDING
    created_time: Optional[float] = None
    estimated_duration: Optional[float] = None
    waiting_time: float = 0.0

    def __post_init__(self):
        if self.estimated_duration is None:
            base = self.start_zone.get_travel_time_to(self.end_zone)
            # УМЕНЬШЕНО В 2 РАЗА для MVP
            self.estimated_duration = max(3.0, (base + random.uniform(-1.0, 3.0))*0.5)

    def update(self, time_elapsed: float = 1.0, max_wait: float = 30.0) -> None:  # УВЕЛИЧЕНО до 30!
        if self.status == OrderStatus.PENDING:
            self.waiting_time += time_elapsed
            if self.waiting_time >= max_wait:
                self.status = OrderStatus.CANCELLED


@dataclass
class Driver:
    id: int
    name: str
    current_zone: Zone
    status: DriverStatus = DriverStatus.FREE
    total_earnings: float = 0.0

    # MVP-параметры (оставляем, потому что стратегия их использует)
    strategy_params: Dict = field(default_factory=dict)

    # состояние действий
    current_order: Optional[Order] = None
    time_to_complete: float = 0.0
    move_target_zone: Optional[Zone] = None

    color: str = "blue"
    simulation: Optional[object] = None  # не используем в MVP, но не ломаем интерфейс

    def __post_init__(self):
        defaults = {
            "min_profit_threshold": 0.0,   # MVP: без порога (или 0)
            "exploration_rate": 0.05,      # немного шума
            "cost_per_minute": 0.2,
            "time_value_per_minute": 0.1,
        }
        for k, v in defaults.items():
            self.strategy_params.setdefault(k, v)

        self.cost_per_minute = float(self.strategy_params["cost_per_minute"])
        self.time_value_per_minute = float(self.strategy_params["time_value_per_minute"])

    def start_moving(self, target_zone: Zone) -> None:
        if self.status != DriverStatus.FREE:
            return
        if target_zone == self.current_zone:
            return
        self.status = DriverStatus.MOVING
        self.move_target_zone = target_zone
        self.time_to_complete = self.current_zone.get_travel_time_to(target_zone)

    def start_order(self, order: Order) -> None:
        if self.status != DriverStatus.FREE:
            return
        if order.status != OrderStatus.PENDING:
            return

        self.status = DriverStatus.BUSY
        self.current_order = order
        order.status = OrderStatus.ACCEPTED

        # Время подачи
        if self.current_zone == order.start_zone:
            pickup_time = 2.0
        else:
            pickup_time = self.current_zone.get_travel_time_to(order.start_zone)

        self.time_to_complete = pickup_time + float(order.estimated_duration)

    def complete_current_action(self) -> None:
        if self.status == DriverStatus.MOVING:
            if self.move_target_zone is not None:
                self.current_zone = self.move_target_zone
            self.move_target_zone = None
            self.status = DriverStatus.FREE
            self.time_to_complete = 0.0
            return

        if self.status == DriverStatus.BUSY and self.current_order is not None:
            self.total_earnings += float(self.current_order.price)
            self.current_order.status = OrderStatus.COMPLETED
            self.current_zone = self.current_order.end_zone
            self.current_order = None
            self.status = DriverStatus.FREE
            self.time_to_complete = 0.0

    def update(self, time_elapsed: float = 1.0) -> None:  # УБРАЛИ max_wait
        """Обновляет состояние водителя."""
        if self.status in [DriverStatus.BUSY, DriverStatus.MOVING]:
            # Уменьшаем время до завершения текущего действия
            self.time_to_complete -= time_elapsed
            if self.time_to_complete <= 0:
                self.complete_current_action()