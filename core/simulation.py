"""Основной класс симуляции"""
from core.models import Zone, Driver, Order
from core.enums import DriverStatus, OrderStatus
from algorithms.pricing import PricingStrategy
from algorithms.driver_strategy import DriverStrategy
import random
from typing import Dict

class CitySimulation:
    """
    Основной класс симуляции города
    """

    def __init__(self):
        """Инициализация симуляции"""
        self.zones: Dict[int, Zone] = {}
        self.drivers: Dict[int, Driver] = {}
        self.orders: Dict[int, Order] = {}
        self.time: float = 0.0
        self.order_counter: int = 0
        self.driver_counter: int = 0
        self.count_zones: int = 4

        # Создаем зоны города
        self._initialize_zones()

        # Создаем водителей
        self._initialize_drivers()
        # Счетчики за текущую минуту
        self.orders_completed_this_minute = 0
        self.orders_cancelled_this_minute = 0
        self.orders_created_this_minute = 0
        # Общие счетчики
        self.total_created_orders = 0
        self.total_completed_orders = 0
        self.total_cancelled_orders = 0
        # История по минутам
        self.minute_history = []  # Будем хранить статистику по каждой минуте

    def _initialize_zones(self) -> None:
        """Инициализация зон города"""
        # Матрица времени перемещения между зонами (в минутах)
        travel_times = {
            "Центр->Центр": 5,
            "Центр->Спальный район": 15,
            "Центр->Периферия": 25,
            "Спальный район 1->Центр": 20,
            "Спальный район 1->Спальный район 2": 8,
            "Спальный район 1->Периферия": 18,
            "Периферия->Центр": 30,
            "Периферия->Спальный район": 22,
            "Периферия->Периферия": 12,
            "Спальный район 2->Центр": 20,
            "Спальный район 2->Спальный район 1": 8,
            "Спальный район 2->Периферия": 18,
            "Спальный район 2->Спальный район 2": 15
        }

        # Создаем зоны
        self.zones[1] = Zone(
            id=1,
            name="Центр",
            base_demand_rate=2.0,  # БЫЛО 10.0, СТАЛО 2.0 (2 заказа в минуту)
            base_price_multiplier=1.2,
            surge_multiplier=1.0,
            travel_time_matrix=travel_times,
            color="red"
        )

        self.zones[2] = Zone(
            id=2,
            name="Спальный район 1",
            base_demand_rate=0.8,  # БЫЛО 4.0, СТАЛО 0.8
            base_price_multiplier=1.0,
            surge_multiplier=1.0,
            travel_time_matrix=travel_times,
            color="green"
        )

        self.zones[3] = Zone(
            id=3,
            name="Периферия",
            base_demand_rate=0.3,  # БЫЛО 1.5, СТАЛО 0.3
            base_price_multiplier=0.8,
            surge_multiplier=1.0,
            travel_time_matrix=travel_times,
            color="blue"
        )

        self.zones[4] = Zone(
            id=4,
            name="Спальный район 2",
            base_demand_rate=0.8,  # БЫЛО 4.0, СТАЛО 0.8
            base_price_multiplier=1.0,
            surge_multiplier=1.0,
            travel_time_matrix=travel_times,
            color="yellow"
        )

    def _initialize_drivers(self) -> None:
        """Инициализация водителей"""
        driver_names = ["Аббасали", "Алексей", "Бексултан", "Чумабой", "Михаил",
                        "Пчелубель", "Чынасыл", "Владимир", "Бобир", "Николай",
                        "Олег", "Абдуллох", "Борис", "Григорий", "Сухроб",
                        "Константин", "Мухаммадали", "Артем", "Сулейман", "Роман"]

        # Создаем 15 водителей вместо 8
        for i, name in enumerate(driver_names[:15]):
            zone_id = (i % self.count_zones) + 1
            self.driver_counter += 1
            self.drivers[self.driver_counter] = Driver(
                id=self.driver_counter,
                name=name,
                current_zone=self.zones[zone_id],
                simulation=self,
                color=f"#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}"
            )

    def generate_orders(self) -> None:
        """Генерация новых заказов"""
        # Не генерируем новые заказы, если уже много ожидающих
        pending_count = len([o for o in self.orders.values()
                             if o.status == OrderStatus.PENDING])

        if pending_count > 20:  # Максимум 20 ожидающих заказов
            return

        for zone in self.zones.values():
            num_orders = zone.generate_demand()
            self.total_created_orders += num_orders

            for _ in range(num_orders):
                self.order_counter += 1

                # Выбираем случайную зону назначения
                end_zone = random.choice(list(self.zones.values()))

                # Рассчитываем цену
                price = PricingStrategy.calculate_order_price(zone, end_zone)

                # Создаем заказ
                order = Order(
                    id=self.order_counter,
                    start_zone=zone,
                    end_zone=end_zone,
                    price=price
                )

                self.orders[self.order_counter] = order

    def match_orders_to_drivers(self) -> None:
        """Сопоставление заказов со свободными водителями"""
        pending_orders = [o for o in self.orders.values()
                          if o.status == OrderStatus.PENDING]

        free_drivers = [d for d in self.drivers.values()
                        if d.status == DriverStatus.FREE]

        for order in pending_orders:

            for driver in free_drivers:
                if DriverStrategy.decide_on_order(driver, order):
                    driver.start_order(order)
                    free_drivers.remove(driver)
                    # print(f"{driver.name} принял {order}")
                    break

    def update_drivers_movement(self) -> None:
        """Обновление перемещения водителей"""
        # Считаем количество водителей в каждой зоне
        drivers_per_zone = {}
        available_orders_by_zone = {}

        for zone in self.zones.values():
            drivers_count = len([d for d in self.drivers.values()
                                 if d.current_zone == zone and
                                 d.status == DriverStatus.FREE])
            drivers_per_zone[zone] = drivers_count

            # Собираем доступные заказы в зоне
            zone_orders = [o for o in self.orders.values()
                           if o.start_zone == zone and
                           o.status == OrderStatus.PENDING]
            available_orders_by_zone[zone.id] = zone_orders

        # Каждый свободный водитель решает, перемещаться ли
        for driver in self.drivers.values():
            if driver.status == DriverStatus.FREE:
                target_zone = DriverStrategy.decide_zone_move(
                    driver,
                    list(self.zones.values()),
                    drivers_per_zone,
                    available_orders_by_zone # передаем доступные заказы
                )

                if target_zone and target_zone != driver.current_zone:
                    driver.start_moving(target_zone)
                    # print(f"{driver.name} едет из {driver.current_zone.name} в {target_zone.name}")

    def update_surge_pricing(self) -> None:
        """Обновление динамического ценообразования"""
        PricingStrategy.update_zones_pricing(self.zones, self.drivers)

    def cleanup_completed_orders(self) -> None:
        completed_ids = []
        for order_id, order in self.orders.items():
            if order.status == OrderStatus.COMPLETED:
                self.total_completed_orders += 1  # ← Считаем выполненные
                completed_ids.append(order_id)
            elif order.status == OrderStatus.CANCELLED:
                self.total_cancelled_orders += 1  # ← Считаем отмененные
                completed_ids.append(order_id)

        for order_id in completed_ids:
            del self.orders[order_id]
    def run_iteration(self, time_step: float = 1.0) -> None:
        """
        Выполнить одну итерацию симуляции (1 минута)
        """
        # ОБНУЛЯЕМ счетчики на начало минуты
        self.orders_completed_this_minute = 0
        self.orders_cancelled_this_minute = 0
        self.orders_created_this_minute = 0

        # 1. Обновляем состояние водителей
        for driver in self.drivers.values():
            # Запоминаем статус до обновления
            was_busy = (driver.status == DriverStatus.BUSY)
            had_order = driver.current_order is not None

            # Обновляем водителя
            driver.update(time_step)

            # ПРОВЕРЯЕМ ЗАВЕРШИЛСЯ ЛИ ЗАКАЗ
            if was_busy and driver.status == DriverStatus.FREE and had_order:
                self.orders_completed_this_minute += 1

        # 2. Обновляем состояние заказов
        cancelled_this_minute = 0
        for order in self.orders.values():
            old_status = order.status
            order.update(time_step)
            if old_status == OrderStatus.PENDING and order.status == OrderStatus.CANCELLED:
                cancelled_this_minute += 1

        self.orders_cancelled_this_minute = cancelled_this_minute

        # 3. Генерируем новые заказы
        orders_before = len(self.orders)
        self.generate_orders()
        orders_after = len(self.orders)
        self.orders_created_this_minute = orders_after - orders_before

        # 4. Сопоставляем заказы с водителями
        self.match_orders_to_drivers()

        # 5. Обновляем перемещение водителей
        self.update_drivers_movement()

        # 6. Обновляем динамическое ценообразование
        self.update_surge_pricing()

        # 7. Очищаем завершенные заказы
        self.cleanup_completed_orders()

        # 9. Обновляем время
        self.time += time_step

    def get_statistics(self) -> Dict:
        """Получить статистику по симуляции"""
        total_earnings = sum(d.total_earnings for d in self.drivers.values())
        avg_earnings = total_earnings / len(self.drivers) if self.drivers else 0

        # Считаем заказы по статусам
        order_stats = {
            "pending": 0,
            "accepted": 0,
            "completed": 0,
            "cancelled": 0
        }

        for order in self.orders.values():
            if order.status == OrderStatus.PENDING:
                order_stats["pending"] += 1
            elif order.status == OrderStatus.ACCEPTED:
                order_stats["accepted"] += 1
            elif order.status == OrderStatus.COMPLETED:
                order_stats["completed"] += 1
            elif order.status == OrderStatus.CANCELLED:
                order_stats["cancelled"] += 1

        # Активные = ожидающие + принятые
        active_orders = order_stats["pending"] + order_stats["accepted"]

        # Статусы водителей
        free_drivers = len([d for d in self.drivers.values()
                            if d.status == DriverStatus.FREE])
        busy_drivers = len([d for d in self.drivers.values()
                            if d.status == DriverStatus.BUSY])
        moving_drivers = len([d for d in self.drivers.values()
                              if d.status == DriverStatus.MOVING])

        avg_satisfaction = (sum(d.satisfaction for d in self.drivers.values()) /
                            len(self.drivers) if self.drivers else 0)

        return {
            "time": self.time,
            "total_drivers": len(self.drivers),
            "free_drivers": free_drivers,
            "busy_drivers": busy_drivers,
            "moving_drivers": moving_drivers,

            # КЛЮЧЕВОЕ ИЗМЕНЕНИЕ:
            "active_orders": active_orders,  # Активные заказы
            "pending_orders": order_stats["pending"],  # Ожидают водителя
            "accepted_orders": order_stats["accepted"],  # Выполняются
            "completed_orders": order_stats["completed"],  # Завершены
            "cancelled_orders": order_stats["cancelled"],  # Отменены
            "total_orders_in_system": len(self.orders),  # Все в системе

            "total_earnings": total_earnings,
            "avg_earnings": avg_earnings,
            "avg_satisfaction": avg_satisfaction,

            "zone_stats": {
                zone.name: {
                    "surge_multiplier": zone.surge_multiplier,
                    "drivers_count": len([d for d in self.drivers.values()
                                          if d.current_zone == zone])
                }
                for zone in self.zones.values()
            }
        }

    def print_status(self) -> None:
        """Вывести текущий статус симуляции"""
        stats = self.get_statistics()

        print(f"\n=== Время: {stats['time']:.1f} мин ===")
        print(f"Водители: {stats['total_drivers']} всего, "
              f"{stats['free_drivers']} свободны, "
              f"{stats['busy_drivers']} заняты, "
              f"{stats['moving_drivers']} в пути")

        # НОВЫЙ ФОРМАТ:
        print(f"Заказы: {stats['active_orders']} активных "
              f"({stats['pending_orders']} ожидают, {stats['accepted_orders']} выполняются)")
        print(f"   📈 Создано новых заказов: {self.orders_created_this_minute}")
        print(f"   ✅ Выполнено заказов: {self.orders_completed_this_minute}")
        print(f"   ❌ Отменено заказов: {self.orders_cancelled_this_minute}")

        print(f"Всего заказов в системе: {stats['total_orders_in_system']}")

        print(f"Заработок: всего {stats['total_earnings']:.2f}, "
              f"в среднем {stats['avg_earnings']:.2f}")
        print(f"Удовлетворенность водителей: {stats['avg_satisfaction']:.1f}")

        print("\nСтатистика по зонам:")
        for zone_name, zone_stats in stats['zone_stats'].items():
            print(f"  {zone_name}: множитель цены x{zone_stats['surge_multiplier']:.2f}, "
                  f"водителей: {zone_stats['drivers_count']}")

    def debug_simulation(self):
        """Вывод отладочной информации"""
        print("\n" + "=" * 60)
        print("ОТЛАДОЧНАЯ ИНФОРМАЦИЯ:")
        print("=" * 60)

        # 1. Водителиf
        print("\n📋 ВОДИТЕЛИ:")
        for driver in self.drivers.values():
            status_info = f"{driver.status.value}"
            if driver.status == DriverStatus.BUSY:
                status_info += f" (осталось {driver.time_to_complete:.1f} мин)"
            elif driver.status == DriverStatus.MOVING:
                status_info += f" в {driver.current_zone.name} (осталось {driver.time_to_complete:.1f} мин)"

            print(f"  {driver.name}: {status_info}, заработок: {driver.total_earnings:.1f}")

        # 2. Заказы
        print("\n📋 ЗАКАЗЫ:")
        order_types = {"ожидает": 0, "выполняется": 0, "завершен": 0, "отменен": 0}

        for order in self.orders.values():
            if order.status == OrderStatus.PENDING:
                order_types["ожидает"] += 1
                print(f"  ⏳ #{order.id}: {order.start_zone.name}->{order.end_zone.name}, "
                      f"цена: {order.price:.1f}, ждет: {order.waiting_time:.1f} мин")
            elif order.status == OrderStatus.ACCEPTED:
                order_types["выполняется"] += 1
                # Найдем водителя
                driver_name = "?"
                for d in self.drivers.values():
                    if d.current_order and d.current_order.id == order.id:
                        driver_name = d.name
                        break
                print(f"  🚗 #{order.id}: {order.start_zone.name}->{order.end_zone.name}, "
                      f"водитель: {driver_name}, длительность: {order.estimated_duration:.1f} мин")
            elif order.status == OrderStatus.COMPLETED:
                order_types["завершен"] += 1
            elif order.status == OrderStatus.CANCELLED:
                order_types["отменен"] += 1

        print(f"\n📊 Сводка: {order_types}")

        # 3. Зоны
        print("\n📋 ЗОНЫ:")
        for zone in self.zones.values():
            drivers_in_zone = len([d for d in self.drivers.values()
                                   if d.current_zone == zone])
            free_in_zone = len([d for d in self.drivers.values()
                                if d.current_zone == zone and d.status == DriverStatus.FREE])
            print(f"  {zone.name}: {drivers_in_zone} водителей ({free_in_zone} свободно), "
                  f"множитель цены: x{zone.surge_multiplier:.2f}")


# Пример использования
if __name__ == "__main__":
    # Инициализация симуляции
    print("Инициализация симуляции города...")
    sim = CitySimulation()

    # Запускаем несколько итераций
    minutes = 50
    print(f"\nЗапуск симуляции на {minutes} минут...")
    for i in range(minutes):
        print(f"\n--- Минута {i + 1} ---")
        sim.run_iteration()
        sim.print_status()
        #sim.debug_simulation()

        # Небольшая пауза для удобства чтения
        #import time

        #time.sleep(0.5)

    print("\n=== Итоги симуляции ===")
    stats = sim.get_statistics()
    print(f"Всего времени: {stats['time']} минут")
    print(f"Общий заработок всех водителей: {stats['total_earnings']:.2f}")
    print(f"Средний заработок на водителя: {stats['avg_earnings']:.2f}")

    # Выводим информацию по каждому водителю
    print("\nИнформация по водителям:")
    for driver in sim.drivers.values():
        print(f"  {driver.name}: {driver.total_earnings:.2f}, "
              f"удовлетворенность: {driver.satisfaction:.1f}")

    print(f"\nВсего создано заказов: {sim.total_created_orders}")
    print(f"Всего выполнено заказов: {sim.total_completed_orders}")
    print(f"Всего отменено заказов: {sim.total_cancelled_orders}")

    if sim.total_created_orders > 0:
        completion_rate = (sim.total_completed_orders / sim.total_created_orders) * 100
        print(f"Процент выполнения: {completion_rate:.1f}%")