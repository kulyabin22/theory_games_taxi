# main.py
"""Запуск симуляции + визуализация + аналитика для MVP"""
import random
import numpy as np
import sys
import os

# Добавляем пути для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Попытка импортировать модули визуализации и аналитики
try:
    from utils.visualization import TaxiSimulationVisualizer
    from utils.statistics import CoverageAnalytics, run_analysis

    HAS_VISUALIZATION = True
    HAS_ANALYTICS = True
except ImportError as e:
    print(f"⚠️ Модуль не найден: {e}")
    # Пробуем альтернативные пути
    try:
        # Пробуем импорт из корневой директории
        sys.path.append('.')
        from visualization import TaxiSimulationVisualizer
        from statistics import CoverageAnalytics, run_analysis

        HAS_VISUALIZATION = True
        HAS_ANALYTICS = True
    except ImportError:
        print("❌ Модули visualization и statistics не найдены")
        HAS_VISUALIZATION = False
        HAS_ANALYTICS = False

# Импортируем основные модули симуляции
try:
    from core.simulation import CitySimulation
    from core.enums import DriverStatus, OrderStatus
except ImportError:
    # Пробуем альтернативный путь
    sys.path.append('core')
    from simulation import CitySimulation
    from enums import DriverStatus, OrderStatus


def zone_snapshot(sim: CitySimulation):
    zones = list(sim.zones.values())

    free_by_zone = {z.id: 0 for z in zones}
    pending_by_zone = {z.id: 0 for z in zones}

    for d in sim.drivers.values():
        if d.status == DriverStatus.FREE:
            free_by_zone[d.current_zone.id] += 1

    for o in sim.orders.values():
        if o.status == OrderStatus.PENDING:
            pending_by_zone[o.start_zone.id] += 1

    free_counts = [free_by_zone[z.id] for z in zones]
    pend_counts = [pending_by_zone[z.id] for z in zones]

    free_arr = np.array(free_counts, dtype=float)
    pend_arr = np.array(pend_counts, dtype=float)

    free_mean = float(free_arr.mean()) if len(free_arr) else 0.0
    free_var = float(free_arr.var()) if len(free_arr) else 0.0
    free_cv = float(free_arr.std() / free_mean) if free_mean > 1e-9 else 0.0

    pend_mean = float(pend_arr.mean()) if len(pend_arr) else 0.0
    pend_var = float(pend_arr.var()) if len(pend_arr) else 0.0

    surge = {z.name: z.surge_multiplier for z in zones}

    return zones, free_by_zone, pending_by_zone, free_var, free_cv, pend_var, surge


def collect_simulation_history(sim, minutes):
    """
    Собирает историю симуляции для визуализации
    """
    history = {
        "timestamps": [],
        "surge": {zone_id: [] for zone_id in sim.zones.keys()},
        "drivers": {zone_id: [] for zone_id in sim.zones.keys()},
        "drivers_positions": [],  # Список словарей {driver_id: zone_id}
        "drivers_statuses": [],  # Список словарей {driver_id: status}
        "orders_created": [],
        "orders_completed": [],
        "orders_cancelled": [],
        "orders": [],  # Список состояний заказов на каждом шаге
        "zones": sim.zones  # Сохраняем ссылки на зоны для анимации
    }

    # Функция для снимка текущего состояния
    def take_snapshot():
        history["timestamps"].append(sim.time)

        # Surge по зонам
        for zone_id, zone in sim.zones.items():
            history["surge"][zone_id].append(zone.surge_multiplier)

        # Водители по зонам (только свободные для графика)
        for zone_id in sim.zones.keys():
            count = len([d for d in sim.drivers.values()
                         if d.current_zone.id == zone_id and d.status == DriverStatus.FREE])
            history["drivers"][zone_id].append(count)

        # Позиции ВСЕХ водителей (для анимации)
        positions = {}
        for driver_id, driver in sim.drivers.items():
            positions[driver_id] = driver.current_zone.id
        history["drivers_positions"].append(positions)

        # Статусы ВСЕХ водителей (для анимации)
        statuses = {}
        for driver_id, driver in sim.drivers.items():
            statuses[driver_id] = driver.status
        history["drivers_statuses"].append(statuses)

        # Статистика заказов
        history["orders_created"].append(sim.orders_created_this_minute)
        history["orders_completed"].append(sim.orders_completed_this_minute)
        history["orders_cancelled"].append(sim.orders_cancelled_this_minute)

        # Состояния заказов
        orders_state = []
        for order in sim.orders.values():
            orders_state.append({
                'id': order.id,
                'start_zone_id': order.start_zone.id,
                'end_zone_id': order.end_zone.id if order.end_zone else None,
                'status': order.status,
                'price': order.price,
                'waiting_time': order.waiting_time
            })
        history["orders"].append(orders_state)

    return history, take_snapshot


def run_simulation_with_analytics():
    """Запуск симуляции с аналитикой покрытия"""
    print("=" * 80)
    print("ЗАПУСК СИМУЛЯЦИИ С АНАЛИТИКОЙ ПОКРЫТИЯ")
    print("=" * 80)

    if HAS_ANALYTICS:
        run_analysis()
    else:
        print("❌ Модуль аналитики недоступен. Запускаю базовую симуляцию...")
        main_simulation()


def run_simulation_with_visualization():
    """Запуск симуляции с визуализацией"""
    print("=" * 80)
    print("ЗАПУСК СИМУЛЯЦИИ С ВИЗУАЛИЗАЦИЕЙ")
    print("=" * 80)

    random.seed()
    np.random.seed()

    sim = CitySimulation()
    minutes = 60  # Уменьшено для более быстрой генерации GIF

    # Инициализируем сбор истории
    history, take_snapshot = collect_simulation_history(sim, minutes)

    # Первый снимок (начальное состояние - время 0)
    take_snapshot()

    print(f"Запуск симуляции на {minutes} минут...\n")

    for t in range(1, minutes + 1):
        sim.run_iteration()

        # Делаем снимок после каждой минуты
        take_snapshot()

        if t % 5 == 0:
            print(f"Минута {t}/{minutes} завершена...")

    print("\n" + "=" * 80)
    print("СИМУЛЯЦИЯ ЗАВЕРШЕНА")
    print("=" * 80)

    # Вывод финальной статистики
    stats = sim.get_statistics()
    print(f"\nВремя: {stats['time']:.0f} мин")
    print(f"Заработок всего: {stats['total_earnings']:.2f}")
    print(f"Средний заработок: {stats['avg_earnings']:.2f}")
    print(f"Создано/выполн/отмен: {sim.total_created_orders}/{sim.total_completed_orders}/{sim.total_cancelled_orders}")

    if sim.total_created_orders:
        print(f"Выполнение: {100.0 * sim.total_completed_orders / sim.total_created_orders:.1f}%")
        print(f"Отмена:     {100.0 * sim.total_cancelled_orders / sim.total_created_orders:.1f}%")

    # Запуск визуализации
    if HAS_VISUALIZATION:
        print("\n" + "=" * 80)
        print("СОЗДАНИЕ ВИЗУАЛИЗАЦИИ")
        print("=" * 80)

        try:
            print("🎬 Создаю анимацию симуляции...")

            # Создаем симуляцию для визуализатора (начальное состояние)
            sim_for_viz = CitySimulation()

            # Создаем визуализатор с историей
            visualizer = TaxiSimulationVisualizer(sim_for_viz, history)

            # Запускаем анимацию по истории
            visualizer.animate_from_history(frames=minutes, interval=600)

            print("✅ Анимация создана и отображена")

            # Дополнительная статистика
            print("\n📈 СТАТИСТИКА ПЕРЕМЕЩЕНИЙ:")
            total_moves = 0
            for t in range(1, len(history['drivers_positions'])):
                prev = history['drivers_positions'][t - 1]
                curr = history['drivers_positions'][t]
                moves = sum(1 for d_id in curr if prev.get(d_id) != curr.get(d_id))
                total_moves += moves

            print(f"Всего перемещений между зонами: {total_moves}")
            print(f"Среднее перемещений в минуту: {total_moves / minutes:.1f}")

            # Surge статистика
            print("\n📊 SURGE СТАТИСТИКА:")
            for zone_id, zone in sim.zones.items():
                avg_surge = sum(history['surge'][zone_id]) / len(history['surge'][zone_id])
                max_surge = max(history['surge'][zone_id])
                print(f"  {zone.name}: средний x{avg_surge:.2f}, максимум x{max_surge:.2f}")

        except Exception as e:
            print(f"❌ Ошибка при создании анимации: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n⚠️ Визуализация недоступна")


def run_combined_simulation():
    """Запуск полной симуляции с аналитикой и визуализацией"""
    print("=" * 80)
    print("ПОЛНАЯ СИМУЛЯЦИЯ: АНАЛИТИКА + ВИЗУАЛИЗАЦИЯ")
    print("=" * 80)

    # Сначала запускаем аналитику (длительная симуляция)
    if HAS_ANALYTICS:
        print("📊 Запуск аналитики покрытия...")
        print("=" * 40)

        # Создаем симуляцию для аналитики
        random.seed()
        np.random.seed()

        sim_analytics = CitySimulation()
        analytics = CoverageAnalytics(sim_analytics, save_path="coverage_analysis")

        # Запускаем симуляцию на 50 минут
        minutes_analytics = 60
        for i in range(minutes_analytics):
            sim_analytics.run_iteration()
            analytics.collect_current_metrics()

            if (i + 1) % 10 == 0:
                print(f"  Аналитика: {i + 1}/{minutes_analytics} минут...")

        # Генерируем аналитику
        print("\nГенерация аналитики...")
        analytics.plot_zci_over_time(save_fig=True)
        analytics.plot_city_summary(save_fig=True)

        print("\n✅ Аналитика завершена!")
        print("   Файлы сохранены в папке 'coverage_analysis/'")

    # Затем запускаем визуализацию (более короткая симуляция)
    print("\n" + "=" * 40)
    print("🎬 Запуск визуализации...")
    run_simulation_with_visualization()


def main_simulation():
    """Основная симуляция (только текстовый вывод)"""
    random.seed()
    np.random.seed()

    sim = CitySimulation()

    minutes = 50
    report_every = 5

    print(f"Запуск симуляции на {minutes} минут...\n")

    for t in range(1, minutes + 1):
        sim.run_iteration()

        if t % report_every == 0:
            # Существующий вывод
            zones, free_by_zone, pending_by_zone, free_var, free_cv, pend_var, surge = zone_snapshot(sim)

            zone_names = [z.name for z in zones]
            free_str = ", ".join(f"{name}:{free_by_zone[z.id]}" for name, z in zip(zone_names, zones))
            pend_str = ", ".join(f"{name}:{pending_by_zone[z.id]}" for name, z in zip(zone_names, zones))
            surge_str = ", ".join(f"{name}:x{surge[name]:.2f}" for name in zone_names)

            created = sim.total_created_orders
            completed = sim.total_completed_orders
            cancelled = sim.total_cancelled_orders
            comp_rate = (100.0 * completed / created) if created else 0.0
            canc_rate = (100.0 * cancelled / created) if created else 0.0

            print(f"\n{'=' * 60}")
            print(f"МИНУТА {t}")
            print(f"{'=' * 60}")

            print(f"FREE по зонам:    {free_str}")
            print(f"PENDING по зонам: {pend_str}")
            print(f"SURGE:            {surge_str}")
            print(
                f"Создано/выполн/отмен: {created}/{completed}/{cancelled} | выполн={comp_rate:.1f}% отмен={canc_rate:.1f}%")

            # Детальное покрытие по зонам
            sim.print_zone_coverage()

    print("\n" + "=" * 80)
    print("ФИНАЛЬНАЯ СТАТИСТИКА")
    print("=" * 80)

    # Финальное покрытие
    sim.print_zone_coverage()

    stats = sim.get_statistics()
    print(f"\nВремя: {stats['time']:.0f} мин")
    print(f"Заработок всего: {stats['total_earnings']:.2f}")
    print(f"Средний заработок: {stats['avg_earnings']:.2f}")
    print(f"Создано/выполн/отмен: {sim.total_created_orders}/{sim.total_completed_orders}/{sim.total_cancelled_orders}")
    #print(sim.total_created_orders)
    if sim.total_created_orders:
        print(f"Выполнение: {100.0 * sim.total_completed_orders / sim.total_created_orders:.1f}%")
        print(f"Отмена:     {100.0 * sim.total_cancelled_orders / sim.total_created_orders:.1f}%")

    print("\nТоп-5 водителей по заработку:")
    top = sorted(sim.drivers.values(), key=lambda d: d.total_earnings, reverse=True)[:5]
    for d in top:
        print(f"  {d.name}: {d.total_earnings:.2f} | зона={d.current_zone.name} | статус={d.status.value}")


def main():
    """Главное меню"""
    print("=" * 80)
    print("СИМУЛЯТОР РАСПРЕДЕЛЕНИЯ ТАКСИ ПО ГОРОДУ")
    print("=" * 80)
    print("Доступные режимы:")
    print("  1. Базовая симуляция (только текстовый вывод)")
    print("  2. Симуляция с аналитикой покрытия (графики ZCI)")
    print("  3. Симуляция с визуализацией (GIF анимация)")
    print("  4. Полная симуляция (аналитика + визуализация)")
    print("  5. Выход")
    print("=" * 80)

    # Проверка доступности модулей
    if not HAS_ANALYTICS:
        print("⚠️  Модуль аналитики (statistics.py) недоступен")
    if not HAS_VISUALIZATION:
        print("⚠️  Модуль визуализации (visualization.py) недоступен")

    while True:
        try:
            choice = input("\nВыберите режим (1-5): ").strip()

            if choice == "1":
                print("\nЗапуск базовой симуляции...")
                print("=" * 40)
                main_simulation()
                break

            elif choice == "2":
                if HAS_ANALYTICS:
                    run_simulation_with_analytics()
                else:
                    print(
                        "❌ Модуль аналитики недоступен. Убедитесь, что файл statistics.py находится в корневой папке проекта")
                break

            elif choice == "3":
                if HAS_VISUALIZATION:
                    run_simulation_with_visualization()
                else:
                    print(
                        "❌ Модуль визуализации недоступен. Убедитесь, что файл visualization.py находится в корневой папке проекта")
                break

            elif choice == "4":
                if HAS_ANALYTICS and HAS_VISUALIZATION:
                    run_combined_simulation()
                else:
                    print("❌ Не все модули доступны:")
                    if not HAS_ANALYTICS:
                        print("  - statistics.py не найден")
                    if not HAS_VISUALIZATION:
                        print("  - visualization.py не найден")
                break

            elif choice == "5":
                print("Выход...")
                return

            else:
                print("❌ Неверный выбор. Введите число от 1 до 5.")

        except KeyboardInterrupt:
            print("\n\nПрограмма прервана пользователем.")
            return
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # Проверяем структуру проекта
    print("Проверка структуры проекта...")
    print(f"Текущая директория: {os.getcwd()}")
    print(f"Файлы в директории: {os.listdir('.')}")

    # Проверяем наличие core
    if os.path.exists('core'):
        print(f"Папка 'core' найдена, содержимое: {os.listdir('core')}")

    main()