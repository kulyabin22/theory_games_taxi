# main.py
"""Запуск симуляции + быстрые метрики для теста MVP"""
import random
import numpy as np

from core.simulation import CitySimulation
from core.enums import DriverStatus, OrderStatus


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


def main():
    random.seed(42)
    np.random.seed(42)

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

            print(f"\n{'='*60}")
            print(f"МИНУТА {t}")
            print(f"{'='*60}")
            
            print(f"FREE по зонам:    {free_str}")
            print(f"PENDING по зонам: {pend_str}")
            print(f"SURGE:            {surge_str}")
            print(f"Создано/выполн/отмен: {created}/{completed}/{cancelled} | выполн={comp_rate:.1f}% отмен={canc_rate:.1f}%")
            
            # НОВОЕ: Детальное покрытие по зонам
            sim.print_zone_coverage()

    print("\n" + "="*80)
    print("ФИНАЛЬНАЯ СТАТИСТИКА")
    print("="*80)
    
    # Финальное покрытие
    sim.print_zone_coverage()
    
    stats = sim.get_statistics()
    print(f"\nВремя: {stats['time']:.0f} мин")
    print(f"Заработок всего: {stats['total_earnings']:.2f}")
    print(f"Средний заработок: {stats['avg_earnings']:.2f}")
    print(f"Создано/выполн/отмен: {sim.total_created_orders}/{sim.total_completed_orders}/{sim.total_cancelled_orders}")

    if sim.total_created_orders:
        print(f"Выполнение: {100.0 * sim.total_completed_orders / sim.total_created_orders:.1f}%")
        print(f"Отмена:     {100.0 * sim.total_cancelled_orders / sim.total_created_orders:.1f}%")

    print("\nТоп-5 водителей по заработку:")
    top = sorted(sim.drivers.values(), key=lambda d: d.total_earnings, reverse=True)[:5]
    for d in top:
        print(f"  {d.name}: {d.total_earnings:.2f} | зона={d.current_zone.name} | статус={d.status.value}")

if __name__ == "__main__":
    main()