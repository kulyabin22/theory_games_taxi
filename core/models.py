"""Модели данных: Zone, Driver, Order"""
from core.enums import DriverStatus, OrderStatus
import numpy as np
import random
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class Zone:
    """
    Класс, представляющий зону города

    Attributes:
        id: Уникальный идентификатор зоны
        name: Название зоны
        base_demand_rate: Базовая интенсивность спроса (заказов в минуту)
        base_price_multiplier: Базовый множитель тарифа
        surge_multiplier: Текущий динамический множитель цены
        travel_time_matrix: Время перемещения в другие зоны (в минутах)
        color: Цвет для визуализации
    """

    id: int
    name: str
    base_demand_rate: float
    base_price_multiplier: float = 1.0
    surge_multiplier: float = 1.0
    travel_time_matrix: Dict[str, float] = None
    color: str = "white"

    def __post_init__(self):
        """Инициализация после создания объекта"""
        if self.travel_time_matrix is None:
            self.travel_time_matrix = {}

    def get_travel_time_to(self, target_zone: 'Zone') -> float:
        """
        Получить время перемещения в другую зону

        Args:
            target_zone: Целевая зона

        Returns:
            Время в минутах
        """
        key = f"{self.name}->{target_zone.name}"
        return self.travel_time_matrix.get(key, 10.0)  # Значение по умолчанию

    def generate_demand(self, time_interval: float = 1.0) -> int:
        """
        Сгенерировать количество заказов за интервал времени

        Args:
            time_interval: Интервал времени в минутах

        Returns:
            Количество новых заказов
        """
        # БАЗОВЫЙ спрос уменьшается при высоких ценах!
        # Чем выше цена (surge_multiplier), тем меньше спрос
        effective_demand_rate = self.base_demand_rate / max(1.0, self.surge_multiplier ** 0.7)

        # Распределение Пуассона для генерации заказов
        expected_orders = effective_demand_rate * time_interval

        # Упрощенная реализация распределения Пуассона
        orders = 0
        L = 2.718281828459045 ** (-expected_orders)  # e^(-λ)
        p = 1.0

        while p > L:
            orders += 1
            p *= random.random()

        return orders - 1

    def __str__(self) -> str:
        return f"Зона '{self.name}' (спрос: {self.base_demand_rate}/мин, цена: x{self.surge_multiplier:.2f})"

    def __hash__(self):
        # Используем id для хеширования
        return hash(self.id)

    def __eq__(self, other):
        # Сравниваем по id
        if isinstance(other, Zone):
            return self.id == other.id
        return False

@dataclass
class Driver:
    """
    Класс, представляющий водителя

    Attributes:
        id: Уникальный идентификатор водителя
        name: Имя водителя
        current_zone: Текущая зона
        status: Текущий статус
        total_earnings: Общий заработок
        strategy_params: Параметры стратегии
        current_order: Текущий заказ
        time_to_complete: Время до завершения текущего действия
        satisfaction: Уровень удовлетворенности (0-100)
        color: Цвет для визуализации
    """

    id: int
    name: str
    current_zone: Zone
    status: DriverStatus = DriverStatus.FREE
    total_earnings: float = 0.0
    strategy_params: Dict = None
    current_order: Optional['Order'] = None
    time_to_complete: float = 0.0
    satisfaction: float = 100.0
    color: str = "blue"
    simulation: Optional['CitySimulation'] = None

    def __post_init__(self):
        # Добавляем параметры стоимости
        if self.strategy_params is None:
            self.strategy_params = {
                "min_profit_threshold": 3.0,
                "risk_tolerance": 0.5,
                "exploration_rate": 0.1,
                "patience": 0.8,
                "cost_per_minute": 0.2,  # Стоимость минуты (бензин, амортизация)
                "time_value_per_minute": 0.1,  # Ценность времени водителя
            }

        self.cost_per_minute = self.strategy_params.get("cost_per_minute", 0.2)
        self.time_value_per_minute = self.strategy_params.get("time_value_per_minute", 0.1)

    def start_moving(self, target_zone: Zone) -> None:
        """Начать перемещение в другую зону"""
        self.status = DriverStatus.MOVING
        travel_time = self.current_zone.get_travel_time_to(target_zone)
        self.time_to_complete = travel_time
        # Обновляем удовлетворенность (перемещение снижает удовлетворенность)
        self.satisfaction = max(0, self.satisfaction - 5)

    def start_order(self, order: 'Order') -> None:
        """Начать выполнение заказа"""
        print(f"DEBUG_START_ORDER: {self.name} начинает заказ #{order.id}")

        self.status = DriverStatus.BUSY

        # Время на подачу (от 1 до 5 минут если в той же зоне)
        if self.current_zone == order.start_zone:
            pickup_time = random.uniform(1, 5)
        else:
            pickup_time = self.current_zone.get_travel_time_to(order.start_zone)

        # ОБЩЕЕ время = подача + поездка
        total_time = pickup_time + order.estimated_duration

        self.current_order = order
        self.time_to_complete = total_time
        order.status = OrderStatus.ACCEPTED

        print(f"DEBUG_START_ORDER: pickup_time={pickup_time:.1f}, "
              f"trip={order.estimated_duration:.1f}, total={total_time:.1f}")

        self.satisfaction = min(100, self.satisfaction + 10)

    def complete_current_action(self) -> None:
        """Завершить текущее действие (поездку или заказ)"""
        #print(f"DEBUG_COMPLETE: {self.name} начинает завершение, статус={self.status.value}")

        if self.status == DriverStatus.MOVING:
            #print(f"DEBUG_COMPLETE: {self.name} прибыл в зону")
            self.status = DriverStatus.FREE
            self.time_to_complete = 0.0
            self.satisfaction = min(100, self.satisfaction + 3)

        elif self.status == DriverStatus.BUSY and self.current_order:
            #print(f"DEBUG_COMPLETE: {self.name} завершает заказ #{self.current_order.id}")
            #print(f"DEBUG_COMPLETE: Заработок до: {self.total_earnings}")

            # Завершаем заказ
            self.status = DriverStatus.FREE
            self.total_earnings += self.current_order.price
            self.current_order.status = OrderStatus.COMPLETED
            self.current_zone = self.current_order.end_zone
            self.current_order = None
            self.time_to_complete = 0.0
            self.satisfaction = min(100, self.satisfaction + 15)

            print(f"DEBUG_COMPLETE: Заработок после: {self.total_earnings}")
            print(f"DEBUG_COMPLETE: Новый статус: {self.status.value}")
        else:
            print(f"DEBUG_COMPLETE: {self.name} статус {self.status.value}, current_order={self.current_order}")

    def update(self, time_elapsed: float = 1.0) -> None:
        """
        Обновить состояние водителя
        """
        #print(f"DEBUG_UPDATE: {self.name} статус={self.status.value}, "
              #f"time_to_complete={self.time_to_complete}, "
              #f"time_elapsed={time_elapsed}")

        if self.status in [DriverStatus.MOVING, DriverStatus.BUSY]:
            old_time = self.time_to_complete
            self.time_to_complete -= time_elapsed
            #print(f"DEBUG_UPDATE: {self.name} {old_time:.1f} -> {self.time_to_complete:.1f}")

            if self.time_to_complete <= 0:
                #print(f"DEBUG_UPDATE: {self.name} завершает действие!")
                self.complete_current_action()
            #else:
                #print(f"DEBUG_UPDATE: {self.name} еще ждет {self.time_to_complete:.1f} мин")

        # Постепенное снижение удовлетворенности при бездействии
        if self.status == DriverStatus.FREE:
            self.satisfaction = max(0, self.satisfaction - 0.5)
    def __str__(self) -> str:
        status_str = f"{self.status.value}"
        if self.current_order:
            status_str += f" (заказ #{self.current_order.id})"
        return (f"Водитель {self.name} [{self.id}]: {status_str}, "
                f"зона: {self.current_zone.name}, "
                f"заработал: {self.total_earnings:.2f}, "
                f"удовлетворенность: {self.satisfaction:.1f}")

    def get_time_to_pickup(self, order: 'Order') -> float:
        """
        Получить время чтобы доехать до клиента
        """
        if self.current_zone == order.start_zone:
            # Уже в той же зоне - 2-5 минут
            return random.uniform(2, 5)
        else:
            # Нужно ехать в другую зону
            return self.current_zone.get_travel_time_to(order.start_zone)

    def complete_current_action(self) -> None:
        """Завершить текущее действие (поездку или заказ)"""
        if self.status == DriverStatus.MOVING:
            self.status = DriverStatus.FREE
            self.time_to_complete = 0.0
            self.satisfaction = min(100, self.satisfaction + 3)

        elif self.status == DriverStatus.BUSY and self.current_order:
            # ЗАПОМИНАЕМ ЧТО ЗАКАЗ ЗАВЕРШЕН В ЭТУ МИНУТУ
            if hasattr(self, '_simulation'):  # Если есть ссылка на симуляцию
                self._simulation.orders_completed_this_minute += 1

            # Завершаем заказ
            self.status = DriverStatus.FREE
            self.total_earnings += self.current_order.price
            self.current_order.status = OrderStatus.COMPLETED
            self.current_zone = self.current_order.end_zone
            self.current_order = None
            self.time_to_complete = 0.0
            self.satisfaction = min(100, self.satisfaction + 15)

@dataclass
class Order:
    """
    Класс, представляющий заказ

    Attributes:
        id: Уникальный идентификатор заказа
        start_zone: Зона подачи
        end_zone: Зона назначения
        price: Стоимость поездки
        status: Текущий статус
        created_time: Время создания
        estimated_duration: Оценочная длительность поездки
        waiting_time: Время ожидания водителя
    """

    id: int
    start_zone: Zone
    end_zone: Zone
    price: float
    status: OrderStatus = OrderStatus.PENDING
    created_time: float = None
    estimated_duration: float = None
    waiting_time: float = 0.0

    def __post_init__(self):
        """Инициализация после создания объекта"""
        if self.estimated_duration is None:
            base_time = self.start_zone.get_travel_time_to(self.end_zone)
            #print(f"DEBUG_ORDER: Заказ {self.id} base_time={base_time}")

            # МИНИМУМ 10 минут, МАКСИМУМ 40 минут
            min_trip_time = max(10, min(40, base_time))

            # Логнормальное распределение
            mu = np.log(min_trip_time)
            sigma = 0.3

            normal_sample = np.random.normal(mu, sigma)
            self.estimated_duration = max(5, min(60, np.exp(normal_sample)))

            #print(f"DEBUG_ORDER: estimated_duration={self.estimated_duration:.1f}")

    def update(self, time_elapsed: float = 1.0) -> None:
        """
        Обновить состояние заказа
        """
        if self.status == OrderStatus.PENDING:
            self.waiting_time += time_elapsed
            # Отменяем заказ ЧЕРЕЗ 2 МИНУТЫ максимум
            if self.waiting_time > 2:  # Было 3, стало 2
                #print(f"DEBUG_ORDER_CANCEL: Заказ #{self.id} отменен (ждал {self.waiting_time} мин)")
                self.status = OrderStatus.CANCELLED

    def __str__(self) -> str:
        return (f"Заказ #{self.id}: {self.start_zone.name} → {self.end_zone.name}, "
                f"цена: {self.price:.2f}, статус: {self.status.value}")
