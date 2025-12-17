"""
Модуль core - основные классы симуляции такси
"""

# Экспортируем основные классы для удобного импорта
from .models import Zone, Driver, Order
from .enums import DriverStatus, OrderStatus
from .simulation import CitySimulation


# Версия пакета
__version__ = "0.1.0"
__all__ = ['Zone', 'Driver', 'Order', 'DriverStatus', 'OrderStatus', 'CitySimulation']