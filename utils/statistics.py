"""
Аналитика покрытия зон города - отслеживание ZCI во времени
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import Dict
from datetime import datetime
import random
import os

from core import CitySimulation
from core.enums import OrderStatus


class CoverageAnalytics:
    """
    Класс для сбора и визуализации аналитики покрытия зон
    """

    def __init__(self, simulation: CitySimulation, save_path: str = "coverage_data"):
        """
        Инициализация аналитики

        Args:
            simulation: Объект симуляции
            save_path: Путь для сохранения данных
        """
        self.simulation = simulation
        self.save_path = save_path

        # Создаем папку для сохранения данных
        os.makedirs(save_path, exist_ok=True)

        # Структура для хранения исторических данных
        self.history = {
            'timestamps': [],  # Время симуляции в минутах
            'zones': {},  # Данные по зонам
            'city_metrics': []  # Общие метрики города
        }

        # Инициализируем структуру для каждой зоны
        for zone in self.simulation.zones.values():
            self.history['zones'][zone.name] = {
                'zci': [],  # Zone Coverage Index
                'coverage_ratio': [],  # Отношение водителей к заказам
                'free_drivers': [],  # Свободные водители
                'pending_orders': [],  # Ожидающие заказы
                'wait_time': [],  # Среднее время ожидания
                'busy_drivers': [],  # Занятые водители
                'surge_multiplier': []  # Множитель цены
            }

    def collect_current_metrics(self) -> Dict:
        """
        Собрать текущие метрики покрытия
        """
        current_time = self.simulation.time

        # Добавляем временную метку
        self.history['timestamps'].append(current_time)

        # Собираем данные по каждой зоне
        for zone in self.simulation.zones.values():
            zone_name = zone.name

            # Считаем метрики для зоны
            free_drivers = len([d for d in self.simulation.drivers.values()
                                if d.current_zone == zone and d.status.value == 'свободен'])

            busy_drivers = len([d for d in self.simulation.drivers.values()
                                if d.current_zone == zone and d.status.value == 'выполняет заказ'])

            pending_orders = [o for o in self.simulation.orders.values()
                              if o.start_zone == zone and o.status == OrderStatus.PENDING]

            # Коэффициент покрытия
            coverage_ratio = free_drivers / max(1, len(pending_orders))

            # Среднее время ожидания
            avg_wait_time = sum(o.waiting_time for o in pending_orders) / max(1, len(pending_orders))

            # Рассчитываем ZCI (упрощенная версия)
            zci = self._calculate_zci(coverage_ratio, avg_wait_time, len(pending_orders))

            # Сохраняем данные
            self.history['zones'][zone_name]['zci'].append(zci)
            self.history['zones'][zone_name]['coverage_ratio'].append(coverage_ratio)
            self.history['zones'][zone_name]['free_drivers'].append(free_drivers)
            self.history['zones'][zone_name]['pending_orders'].append(len(pending_orders))
            self.history['zones'][zone_name]['wait_time'].append(avg_wait_time)
            self.history['zones'][zone_name]['busy_drivers'].append(busy_drivers)
            self.history['zones'][zone_name]['surge_multiplier'].append(zone.surge_multiplier)

        # Собираем общие метрики города
        city_metrics = self._calculate_city_metrics()
        self.history['city_metrics'].append(city_metrics)

        return city_metrics

    def _calculate_zci(self, coverage_ratio: float, avg_wait_time: float,
                       pending_orders: int) -> float:
        """
        Рассчитать Zone Coverage Index

        Формула: ZCI = 0.5 × CoverageScore + 0.3 × WaitScore + 0.2 × DemandScore
        """
        # 1. Оценка по покрытию (0-100)
        coverage_score = min(100, coverage_ratio * 50)  # 2.0 = 100 баллов

        # 2. Оценка по времени ожидания (0-100, чем меньше - тем лучше)
        wait_score = max(0, 100 - avg_wait_time * 5)  # 0 мин = 100, 20 мин = 0

        # 3. Оценка по нагрузке (наличие заказов - хорошо, но не слишком много)
        if pending_orders == 0:
            demand_score = 80  # Нет заказов - не плохо, но и не идеально
        elif pending_orders <= 3:
            demand_score = 100  # Оптимальная нагрузка
        elif pending_orders <= 10:
            demand_score = 100 - (pending_orders - 3) * 5  # Линейное снижение
        else:
            demand_score = 0  # Перегрузка

        # Итоговый ZCI
        zci = (
                coverage_score * 0.5 +
                wait_score * 0.3 +
                demand_score * 0.2
        )

        return round(zci, 2)

    def _calculate_city_metrics(self) -> Dict:
        """
        Рассчитать общие метрики города
        """
        # Собираем ZCI всех зон
        all_zci = []
        for zone_name in self.simulation.zones.values():
            if self.history['zones'][zone_name.name]['zci']:
                all_zci.append(self.history['zones'][zone_name.name]['zci'][-1])

        if not all_zci:
            return {}

        # Рассчитываем неравенство покрытия (стандартное отклонение)
        zci_std = np.std(all_zci)

        # Процент зон с проблемами
        problematic_zones = sum(1 for zci in all_zci if zci < 60)

        return {
            'avg_zci': np.mean(all_zci),
            'min_zci': np.min(all_zci),
            'max_zci': np.max(all_zci),
            'zci_std': zci_std,
            'problematic_zones': problematic_zones,
            'problematic_percentage': problematic_zones / len(all_zci) * 100
        }

    def plot_zci_over_time(self, save_fig: bool = True):
        """
        Построить график ZCI по времени для каждой зоны
        """
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('Динамика покрытия зон (ZCI) во времени', fontsize=16, fontweight='bold')

        timestamps = self.history['timestamps']

        if not timestamps:
            print("Нет данных для построения графика")
            return

        # 1. Основной график: ZCI по времени
        ax1 = axes[0, 0]

        colors = plt.cm.Set2(np.linspace(0, 1, len(self.simulation.zones)))

        for idx, (zone_name, zone_data) in enumerate(self.history['zones'].items()):
            if zone_data['zci']:
                ax1.plot(timestamps, zone_data['zci'],
                         label=zone_name,
                         color=colors[idx],
                         linewidth=2,
                         marker='o' if len(timestamps) < 20 else None,
                         markersize=4)

        # Горизонтальные линии для уровней ZCI
        ax1.axhline(y=90, color='green', linestyle='--', alpha=0.3, label='Отлично (>90)')
        ax1.axhline(y=75, color='yellow', linestyle='--', alpha=0.3, label='Хорошо (75-90)')
        ax1.axhline(y=60, color='orange', linestyle='--', alpha=0.3, label='Удовлетв. (60-75)')
        ax1.axhline(y=40, color='red', linestyle='--', alpha=0.3, label='Проблемы (<60)')

        ax1.set_xlabel('Время (минуты)')
        ax1.set_ylabel('ZCI (Zone Coverage Index)')
        ax1.set_title('Динамика ZCI по зонам')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 105)

        # 2. График: Среднее время ожидания
        ax2 = axes[0, 1]

        for idx, (zone_name, zone_data) in enumerate(self.history['zones'].items()):
            if zone_data['wait_time']:
                ax2.plot(timestamps, zone_data['wait_time'],
                         label=zone_name,
                         color=colors[idx],
                         linewidth=2)

        ax2.axhline(y=5, color='green', linestyle='--', alpha=0.3, label='Цель: <5 мин')
        ax2.axhline(y=10, color='orange', linestyle='--', alpha=0.3, label='Порог: 10 мин')
        ax2.axhline(y=15, color='red', linestyle='--', alpha=0.3, label='Критично: >15 мин')

        ax2.set_xlabel('Время (минуты)')
        ax2.set_ylabel('Среднее время ожидания (минуты)')
        ax2.set_title('Время ожидания заказов по зонам')
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)

        # 3. График: Коэффициент покрытия
        ax3 = axes[1, 0]

        for idx, (zone_name, zone_data) in enumerate(self.history['zones'].items()):
            if zone_data['coverage_ratio']:
                ax3.plot(timestamps, zone_data['coverage_ratio'],
                         label=zone_name,
                         color=colors[idx],
                         linewidth=2)

        ax3.axhline(y=1.0, color='green', linestyle='--', alpha=0.3, label='Баланс (=1.0)')
        ax3.axhline(y=2.0, color='blue', linestyle='--', alpha=0.3, label='Избыток (>2.0)')
        ax3.axhline(y=0.5, color='red', linestyle='--', alpha=0.3, label='Дефицит (<0.5)')

        ax3.set_xlabel('Время (минуты)')
        ax3.set_ylabel('Коэффициент покрытия\n(Своб. водители / Ожид. заказы)')
        ax3.set_title('Соотношение спроса и предложения')
        ax3.legend(loc='best')
        ax3.grid(True, alpha=0.3)

        # 4. График: Surge Multiplier
        ax4 = axes[1, 1]

        for idx, (zone_name, zone_data) in enumerate(self.history['zones'].items()):
            if zone_data['surge_multiplier']:
                ax4.plot(timestamps, zone_data['surge_multiplier'],
                         label=zone_name,
                         color=colors[idx],
                         linewidth=2)

        ax4.axhline(y=1.0, color='gray', linestyle='--', alpha=0.3, label='Базовая цена')
        ax4.axhline(y=1.5, color='orange', linestyle='--', alpha=0.3, label='Повышенный спрос')
        ax4.axhline(y=2.0, color='red', linestyle='--', alpha=0.3, label='Высокий спрос')

        ax4.set_xlabel('Время (минуты)')
        ax4.set_ylabel('Surge Multiplier (x)')
        ax4.set_title('Динамическое ценообразование')
        ax4.legend(loc='best')
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_fig:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.save_path}/zci_analysis_{timestamp}.jpeg"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"График сохранен: {filename}")

        plt.show()

    def plot_city_summary(self, save_fig: bool = True):
        """
        Построить сводный график по городу
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Аналитика покрытия города', fontsize=16, fontweight='bold')

        timestamps = self.history['timestamps']

        if not timestamps or not self.history['city_metrics']:
            print("Нет данных для построения графика")
            return

        # 1. Средний ZCI по городу
        ax1 = axes[0, 0]

        avg_zci = [m['avg_zci'] for m in self.history['city_metrics']]
        min_zci = [m['min_zci'] for m in self.history['city_metrics']]
        max_zci = [m['max_zci'] for m in self.history['city_metrics']]

        ax1.fill_between(timestamps, min_zci, max_zci, alpha=0.2, color='skyblue', label='Диапазон ZCI')
        ax1.plot(timestamps, avg_zci, 'b-', linewidth=2, label='Средний ZCI')

        ax1.axhline(y=80, color='green', linestyle='--', alpha=0.5, label='Цель: >80')
        ax1.axhline(y=60, color='orange', linestyle='--', alpha=0.5, label='Порог: 60')

        ax1.set_xlabel('Время (минуты)')
        ax1.set_ylabel('ZCI')
        ax1.set_title('Средний ZCI города')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 105)

        # 2. Неравенство покрытия (стандартное отклонение ZCI)
        ax2 = axes[0, 1]

        zci_std = [m['zci_std'] for m in self.history['city_metrics']]

        ax2.plot(timestamps, zci_std, 'r-', linewidth=2, label='Стандартное отклонение')

        ax2.axhline(y=10, color='green', linestyle='--', alpha=0.5, label='Хорошая равномерность')
        ax2.axhline(y=20, color='orange', linestyle='--', alpha=0.5, label='Умеренное неравенство')
        ax2.axhline(y=30, color='red', linestyle='--', alpha=0.5, label='Высокое неравенство')

        ax2.set_xlabel('Время (минуты)')
        ax2.set_ylabel('σ(ZCI)')
        ax2.set_title('Неравномерность покрытия по зонам')
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)

        # 3. Процент проблемных зон
        ax3 = axes[1, 0]

        problematic_percentage = [m['problematic_percentage'] for m in self.history['city_metrics']]

        ax3.fill_between(timestamps, 0, problematic_percentage, alpha=0.3, color='red', label='Проблемные зоны')
        ax3.plot(timestamps, problematic_percentage, 'r-', linewidth=2)

        ax3.axhline(y=25, color='orange', linestyle='--', alpha=0.5, label='Допустимо: <25%')
        ax3.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='Критично: >50%')

        ax3.set_xlabel('Время (минуты)')
        ax3.set_ylabel('Процент проблемных зон (%)')
        ax3.set_title('Доля зон с ZCI < 60')
        ax3.legend(loc='best')
        ax3.grid(True, alpha=0.3)
        ax3.set_ylim(0, 105)

        # 4. Heatmap ZCI по зонам (в конце симуляции)
        ax4 = axes[1, 1]

        # Получаем последние значения ZCI для каждой зоны
        final_zci = {}
        for zone_name, zone_data in self.history['zones'].items():
            if zone_data['zci']:
                final_zci[zone_name] = zone_data['zci'][-1]

        if final_zci:
            zones = list(final_zci.keys())
            zci_values = list(final_zci.values())

            # Создаем цветовую карту в зависимости от значения ZCI
            colors = []
            for value in zci_values:
                if value >= 80:
                    colors.append('green')
                elif value >= 60:
                    colors.append('yellow')
                else:
                    colors.append('red')

            bars = ax4.bar(zones, zci_values, color=colors, edgecolor='black')

            # Добавляем значения на столбцы
            for bar in bars:
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width() / 2., height + 1,
                         f'{height:.1f}', ha='center', va='bottom')

            ax4.axhline(y=80, color='darkgreen', linestyle='--', alpha=0.5, label='Отлично')
            ax4.axhline(y=60, color='darkorange', linestyle='--', alpha=0.5, label='Удовлетв.')

            ax4.set_xlabel('Зоны')
            ax4.set_ylabel('ZCI')
            ax4.set_title('ZCI по зонам (финальные значения)')
            ax4.legend(loc='lower right')
            ax4.grid(True, alpha=0.3, axis='y')
            ax4.set_ylim(0, 105)

        plt.tight_layout()

        if save_fig:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.save_path}/city_summary_{timestamp}.jpeg"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Сводный график сохранен: {filename}")

        plt.show()

def run_analysis():
    """
    Запустить симуляцию с аналитикой покрытия
    """
    # Настройки симуляции
    random.seed()
    np.random.seed()

    print("Запуск симуляции с аналитикой покрытия...")
    print("=" * 60)

    # Создаем симуляцию
    sim = CitySimulation()

    # Создаем аналитику
    analytics = CoverageAnalytics(sim, save_path="coverage_analysis")

    # Запускаем симуляцию на N минут
    minutes = 50

    for i in range(minutes):
        print(f"\nМинута {i + 1}/{minutes}")

        # Запускаем итерацию
        sim.run_iteration()

        # Собираем метрики
        analytics.collect_current_metrics()

        # Выводим краткую статистику
        if (i + 1) % 10 == 0 or i == minutes - 1:
            print(f"  Время: {sim.time:.1f} мин")
            sim.print_zone_coverage()

    print("\n" + "=" * 60)
    print("СИМУЛЯЦИЯ ЗАВЕРШЕНА")
    print("=" * 60)

    # Генерируем аналитику
    print("\nГенерация аналитики...")

    # 1. Графики ZCI по времени
    analytics.plot_zci_over_time(save_fig=True)

    # 2. Сводные графики по городу
    analytics.plot_city_summary(save_fig=True)

    print("\n" + "=" * 60)
    print("АНАЛИТИКА ЗАВЕРШЕНА")
    print("=" * 60)


if __name__ == "__main__":
    run_analysis()