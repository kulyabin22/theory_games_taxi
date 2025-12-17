"""Основной класс симуляции (MVP)"""
from core.models import Zone, Driver, Order
from core.enums import DriverStatus, OrderStatus
from algorithms.pricing import PricingStrategy
from algorithms.driver_strategy import DriverStrategy
import random
import numpy as np
from typing import Dict, List


class CitySimulation:
    def __init__(self):
        self.zones: Dict[int, Zone] = {}
        self.drivers: Dict[int, Driver] = {}
        self.orders: Dict[int, Order] = {}
        self.time: float = 0.0
        self.order_counter: int = 0
        self.driver_counter: int = 0

        # счетчики по минуте
        self.orders_completed_this_minute = 0
        self.orders_cancelled_this_minute = 0
        self.orders_created_this_minute = 0

        # общие
        self.total_created_orders = 0
        self.total_completed_orders = 0
        self.total_cancelled_orders = 0

        self._initialize_zones()
        self._initialize_drivers()

    def _initialize_zones(self) -> None:
        travel_times = {
            "Центр->Центр": 5,
            "Центр->Спальный район": 10,
            "Центр->Периферия": 15,
            "Спальный район->Центр": 12,
            "Спальный район->Спальный район": 8,
            "Спальный район->Периферия": 7,
            "Периферия->Центр": 17,
            "Периферия->Спальный район": 9,
            "Периферия->Периферия": 8,
        }

        self.zones[1] = Zone(1, "Центр", base_demand_rate=0.6, base_price_multiplier=1.2, surge_multiplier=1.0, travel_time_matrix=travel_times, color="red")
        self.zones[2] = Zone(2, "Спальный район", base_demand_rate=0.25, base_price_multiplier=1.0, surge_multiplier=1.0, travel_time_matrix=travel_times, color="green")
        self.zones[3] = Zone(3, "Периферия", base_demand_rate=0.1, base_price_multiplier=0.8, surge_multiplier=1.0, travel_time_matrix=travel_times, color="blue")

    def _initialize_drivers(self) -> None:
        driver_names = ["Аббасали", "Алексей", "Бексултан", "Чумабой", "Михаил",
                        "Пчелубель", "Чынасыл", "Владимир", "Бобир", "Николай",
                        "Олег", "Абдуллох", "Борис", "Григорий", "Сухроб"]

        for i, name in enumerate(driver_names[:15]):
            zone_id = (i % 3) + 1
            self.driver_counter += 1
            self.drivers[self.driver_counter] = Driver(
                id=self.driver_counter,
                name=name,
                current_zone=self.zones[zone_id],
                simulation=self,
                color=f"#{random.randint(0,255):02x}{random.randint(0,255):02x}{random.randint(0,255):02x}"
            )

    def generate_orders(self) -> None:
        """УПРОЩЕННАЯ версия - только базовый спрос"""
        created_now = 0
        
        for zone in self.zones.values():
            # Только базовый спрос
            num_orders = int(np.random.poisson(zone.base_demand_rate))
            
            for _ in range(num_orders):
                self.order_counter += 1
                end_zone = random.choice(list(self.zones.values()))
                price = PricingStrategy.calculate_order_price(zone, end_zone)
                
                order = Order(
                    id=self.order_counter,
                    start_zone=zone,
                    end_zone=end_zone,
                    price=price,
                    created_time=self.time
                )
                self.orders[self.order_counter] = order
                created_now += 1
        
        self.total_created_orders += created_now
        self.orders_created_this_minute = created_now

    def match_orders_to_drivers(self) -> None:
        pending_orders = [o for o in self.orders.values() if o.status == OrderStatus.PENDING]
        free_drivers = [d for d in self.drivers.values() if d.status == DriverStatus.FREE]

        for order in pending_orders:
            if not free_drivers:
                break

            same_zone = [d for d in free_drivers if d.current_zone == order.start_zone]
            candidates = same_zone if same_zone else free_drivers
            
            best_driver = None
            best_score = -1e9

            for d in candidates:
                profit = DriverStrategy.calculate_expected_order_profit(d, order)

                if profit > best_score and DriverStrategy.decide_on_order(d, order):
                    best_score = profit
                    best_driver = d

            if best_driver is not None:
                best_driver.start_order(order)
                free_drivers.remove(best_driver)


    def update_drivers_movement(self) -> None:
        drivers_per_zone = {z.id: 0 for z in self.zones.values()}
        available_orders_by_zone: Dict[int, List[Order]] = {z.id: [] for z in self.zones.values()}

        for d in self.drivers.values():
            if d.status == DriverStatus.FREE:
                drivers_per_zone[d.current_zone.id] += 1

        for o in self.orders.values():
            if o.status == OrderStatus.PENDING:
                available_orders_by_zone[o.start_zone.id].append(o)

        for driver in self.drivers.values():
            if driver.status == DriverStatus.FREE:
                target = DriverStrategy.decide_zone_move(
                    driver,
                    list(self.zones.values()),
                    drivers_per_zone,
                    available_orders_by_zone
                )
                if target and target != driver.current_zone:
                    driver.start_moving(target)

    def update_surge_pricing(self) -> None:
        # pending_by_zone для корректного сигнала дисбаланса
        pending_by_zone = {z.id: 0 for z in self.zones.values()}
        for o in self.orders.values():
            if o.status == OrderStatus.PENDING:
                pending_by_zone[o.start_zone.id] += 1

        PricingStrategy.update_zones_pricing(self.zones, self.drivers, pending_by_zone=pending_by_zone)

    def cleanup_completed_orders(self) -> None:
        to_delete = []
        for oid, order in self.orders.items():
            if order.status == OrderStatus.COMPLETED:
                self.total_completed_orders += 1
                to_delete.append(oid)
            elif order.status == OrderStatus.CANCELLED:
                self.total_cancelled_orders += 1
                to_delete.append(oid)

        for oid in to_delete:
            del self.orders[oid]

    def run_iteration(self, time_step: float = 1.0) -> None:
        self.orders_completed_this_minute = 0
        self.orders_cancelled_this_minute = 0
        self.orders_created_this_minute = 0

        # 1) обновляем водителей
        for driver in self.drivers.values():
            was_busy = (driver.status == DriverStatus.BUSY)
            had_order = (driver.current_order is not None)

            driver.update(time_step)

            if was_busy and driver.status == DriverStatus.FREE and had_order:
                self.orders_completed_this_minute += 1

        # 2) обновляем заказы (отмена по ожиданию)
        cancelled_now = 0
        for order in list(self.orders.values()):
            old = order.status
            order.update(time_step)
            if old == OrderStatus.PENDING and order.status == OrderStatus.CANCELLED:
                cancelled_now += 1
        self.orders_cancelled_this_minute = cancelled_now

        # 3) генерируем новые заказы
        before = len(self.orders)
        self.generate_orders()
        after = len(self.orders)
        self.orders_created_this_minute = after - before

        # 4) матчинг
        self.match_orders_to_drivers()

        # 5) перемещения
        self.update_drivers_movement()

        # 6) обновление surge
        self.update_surge_pricing()

        # 7) очистка завершенных/отмененных
        self.cleanup_completed_orders()

        self.time += time_step

    def get_statistics(self) -> Dict:
        total_earnings = sum(d.total_earnings for d in self.drivers.values())
        avg_earnings = total_earnings / len(self.drivers) if self.drivers else 0

        order_stats = {"pending": 0, "accepted": 0, "completed": 0, "cancelled": 0}
        for order in self.orders.values():
            if order.status == OrderStatus.PENDING:
                order_stats["pending"] += 1
            elif order.status == OrderStatus.ACCEPTED:
                order_stats["accepted"] += 1
            elif order.status == OrderStatus.COMPLETED:
                order_stats["completed"] += 1
            elif order.status == OrderStatus.CANCELLED:
                order_stats["cancelled"] += 1

        active_orders = order_stats["pending"] + order_stats["accepted"]

        free_drivers = sum(1 for d in self.drivers.values() if d.status == DriverStatus.FREE)
        busy_drivers = sum(1 for d in self.drivers.values() if d.status == DriverStatus.BUSY)
        moving_drivers = sum(1 for d in self.drivers.values() if d.status == DriverStatus.MOVING)


        return {
            "time": self.time,
            "total_drivers": len(self.drivers),
            "free_drivers": free_drivers,
            "busy_drivers": busy_drivers,
            "moving_drivers": moving_drivers,
            "active_orders": active_orders,
            "pending_orders": order_stats["pending"],
            "accepted_orders": order_stats["accepted"],
            "completed_orders": order_stats["completed"],
            "cancelled_orders": order_stats["cancelled"],
            "total_orders_in_system": len(self.orders),
            "total_earnings": total_earnings,
            "avg_earnings": avg_earnings,
            "zone_stats": {
                zone.name: {
                    "surge_multiplier": zone.surge_multiplier,
                    "drivers_count": sum(1 for d in self.drivers.values() if d.current_zone == zone)
                }
                for zone in self.zones.values()
            }
        }

    def print_status(self) -> None:
        stats = self.get_statistics()

        print(f"\n=== Время: {stats['time']:.1f} мин ===")
        print(f"Водители: {stats['total_drivers']} всего, "
              f"{stats['free_drivers']} свободны, "
              f"{stats['busy_drivers']} заняты, "
              f"{stats['moving_drivers']} в пути")

        print(f"Заказы: {stats['active_orders']} активных "
              f"({stats['pending_orders']} ожидают, {stats['accepted_orders']} выполняются)")
        print(f"   📈 Создано новых заказов: {self.orders_created_this_minute}")
        print(f"   ✅ Выполнено заказов: {self.orders_completed_this_minute}")
        print(f"   ❌ Отменено заказов: {self.orders_cancelled_this_minute}")

        print(f"Заработок: всего {stats['total_earnings']:.2f}, "
              f"в среднем {stats['avg_earnings']:.2f}")

        print("\nСтатистика по зонам:")
        for zone_name, z in stats["zone_stats"].items():
            print(f"  {zone_name}: x{z['surge_multiplier']:.2f}, водителей: {z['drivers_count']}")

    def get_zone_coverage(self) -> Dict[str, Dict]:
        """Возвращает детальную статистику по зонам."""
        coverage = {}
    
        for zone in self.zones.values():
            # Водители в зоне
            total_drivers = 0
            free_drivers = 0
            busy_drivers = 0
            moving_drivers = 0
        
            for driver in self.drivers.values():
                if driver.current_zone == zone:
                    total_drivers += 1
                    if driver.status == DriverStatus.FREE:
                        free_drivers += 1
                    elif driver.status == DriverStatus.BUSY:
                        busy_drivers += 1
                    elif driver.status == DriverStatus.MOVING:
                        moving_drivers += 1
        
            # Заказы в зоне
            pending_orders = 0
            for order in self.orders.values():
                if order.status == OrderStatus.PENDING and order.start_zone == zone:
                    pending_orders += 1
        
            # Баланс
            balance = "НОРМА"
            if pending_orders > 0 and free_drivers == 0:
                balance = "ДЕФИЦИТ"
            elif free_drivers > pending_orders * 2:
                balance = "ИЗБЫТОК"
        
            coverage[zone.name] = {
                "zone_id": zone.id,
                "total_drivers": total_drivers,
                "free_drivers": free_drivers,
                "busy_drivers": busy_drivers,
                "moving_drivers": moving_drivers,
                "pending_orders": pending_orders,
                "surge_multiplier": zone.surge_multiplier,
                "base_demand_rate": zone.base_demand_rate,
                "balance": balance,
                "driver_to_order_ratio": free_drivers / max(1, pending_orders) if pending_orders > 0 else float('inf')
            }
    
        return coverage
    
    def print_zone_coverage(self):
        """Выводит таблицу покрытия по зонам."""
        coverage = self.get_zone_coverage()
    
        print("\n" + "="*80)
        print("ПОКРЫТИЕ ПО ЗОНАМ")
        print("="*80)
        print(f"{'Зона':<20} {'Всего':<6} {'Своб':<6} {'Занят':<6} {'В пути':<6} {'Ожидает':<8} {'Surge':<8} {'Баланс':<12} {'Соотн.':<8}")
        print("-"*80)
    
        for zone_name, stats in coverage.items():
            ratio = stats["driver_to_order_ratio"]
            ratio_str = f"{ratio:.1f}" if ratio != float('inf') else "∞"
        
            print(f"{zone_name:<20} "
                f"{stats['total_drivers']:<6} "
                f"{stats['free_drivers']:<6} "
                f"{stats['busy_drivers']:<6} "
                f"{stats['moving_drivers']:<6} "
                f"{stats['pending_orders']:<8} "
                f"x{stats['surge_multiplier']:<7.2f} "
                f"{stats['balance']:<12} "
                f"{ratio_str:<8}")
    
        # Сводка
        total_free = sum(stats["free_drivers"] for stats in coverage.values())
        total_pending = sum(stats["pending_orders"] for stats in coverage.values())
        avg_surge = sum(stats["surge_multiplier"] for stats in coverage.values()) / len(coverage)
    
        print("-"*80)
        print(f"ИТОГО: Свободных водителей: {total_free}, Ожидающих заказов: {total_pending}, Средний surge: {avg_surge:.2f}")
    
        # Рекомендации
        print("\nРЕКОМЕНДАЦИИ:")
        for zone_name, stats in coverage.items():
            if stats["balance"] == "ДЕФИЦИТ":
                print(f"  • {zone_name}: Не хватает водителей! {stats['pending_orders']} заказов ждут, свободных: {stats['free_drivers']}")
            elif stats["balance"] == "ИЗБЫТОК":
                print(f"  • {zone_name}: Слишком много свободных водителей ({stats['free_drivers']}), можно перераспределить")
if __name__ == "__main__":
    random.seed(42)
    np.random.seed(42)

    sim = CitySimulation()
    minutes = 50
    for i in range(minutes):
        print(f"\n--- Минута {i + 1} ---")
        sim.run_iteration()
        sim.print_status()

    stats = sim.get_statistics()
    print("\n=== Итоги симуляции ===")
    print(f"Всего создано заказов: {sim.total_created_orders}")
    print(f"Всего выполнено заказов: {sim.total_completed_orders}")
    print(f"Всего отменено заказов: {sim.total_cancelled_orders}")
    if sim.total_created_orders > 0:
        print(f"Процент выполнения: {100 * sim.total_completed_orders / sim.total_created_orders:.1f}%")


    