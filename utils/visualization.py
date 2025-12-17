# utils/visualization.py
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle, Rectangle
import numpy as np
from core.models import Zone, Driver, DriverStatus
from core import CitySimulation


class TaxiSimulationVisualizer:
    """Визуализатор симуляции такси"""

    def __init__(self, simulation):
        self.simulation = simulation
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.time_text = None
        self.stats_text = None

        # Цвета для зон
        self.zone_colors = {
            'Центр': 'red',
            'Спальный район 1': 'green',
            'Спальный район 2': 'yellow',
            'Периферия': 'blue'
        }

        # Позиции зон на графике
        self.zone_positions = {
            'Центр': (0.5, 0.5),
            'Спальный район 1': (0.15, 0.6),
            'Спальный район 2': (0.8, 0.2),
            'Периферия': (0.8, 0.8)
        }

    def setup_plot(self):
        """Настройка графика"""
        self.ax.clear()
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.set_title('Симуляция такси: Распределение водителей по зонам')
        self.ax.axis('off')

        # Рисуем зоны
        for zone_name, (x, y) in self.zone_positions.items():
            zone_color = self.zone_colors.get(zone_name, 'gray')

            # Прямоугольник зоны
            rect = Rectangle((x - 0.15, y - 0.1), 0.3, 0.2,
                             facecolor=zone_color, alpha=0.3,
                             edgecolor='black', linewidth=2)
            self.ax.add_patch(rect)

            # Название зоны
            self.ax.text(x, y + 0.15, zone_name,
                         fontsize=12, fontweight='bold',
                         ha='center', va='center')

            # surge множитель
            zone = next((z for z in self.simulation.zones.values()
                         if z.name == zone_name), None)
            if zone:
                self.ax.text(x, y - 0.15, f'Цена: x{zone.surge_multiplier:.2f}',
                             fontsize=10, ha='center', va='center',
                             bbox=dict(boxstyle="round,pad=0.3",
                                       facecolor="yellow", alpha=0.7))

    def update_animation(self, frame):
        """Обновление кадра анимации"""
        self.setup_plot()

        # Запускаем одну минуту симуляции
        self.simulation.run_iteration()

        # Время
        current_time = int(self.simulation.time)
        self.time_text = self.ax.text(0.02, 0.98, f'Время: {current_time} мин',
                                      fontsize=12, transform=self.ax.transAxes,
                                      bbox=dict(boxstyle="round,pad=0.5",
                                                facecolor="white", alpha=0.8))

        # Статистика
        stats = self.simulation.get_statistics()
        stats_str = (f"Водители: {stats['free_drivers']} свободны, "
                     f"{stats['busy_drivers']} заняты\n"
                     f"Заказы: {stats['active_orders']} активных, "
                     f"{stats['completed_orders']} выполнено")

        self.stats_text = self.ax.text(0.02, 0.9, stats_str,
                                       fontsize=10, transform=self.ax.transAxes,
                                       bbox=dict(boxstyle="round,pad=0.5",
                                                 facecolor="lightblue", alpha=0.8))

        # Рисуем водителей
        self.draw_drivers()

        # Рисуем заказы
        self.draw_orders()

        return []

    def draw_drivers(self):
        """Рисование водителей"""
        for driver in self.simulation.drivers.values():
            zone_name = driver.current_zone.name
            if zone_name in self.zone_positions:
                x, y = self.zone_positions[zone_name]

                # Смещаем позицию чтобы водители не накладывались
                driver_index = list(self.simulation.drivers.keys()).index(driver.id)
                offset_x = (driver_index % 5) * 0.05 - 0.1
                offset_y = (driver_index // 5) * 0.05 - 0.05

                # Цвет водителя в зависимости от статуса
                if driver.status == DriverStatus.FREE:
                    color = 'green'
                    marker = 'o'
                    size = 80
                elif driver.status == DriverStatus.BUSY:
                    color = 'red'
                    marker = 's'  # квадрат
                    size = 100
                elif driver.status == DriverStatus.MOVING:
                    color = 'orange'
                    marker = '^'  # треугольник
                    size = 90
                else:
                    color = 'gray'
                    marker = 'o'
                    size = 80

                # Рисуем водителя
                self.ax.scatter(x + offset_x, y + offset_y,
                                c=color, marker=marker, s=size,
                                edgecolors='black', linewidth=1)

                # Имя водителя
                self.ax.text(x + offset_x, y + offset_y + 0.03,
                             driver.name[:3],  # Первые 3 буквы имени
                             fontsize=8, ha='center', va='center')

                # Заработок
                self.ax.text(x + offset_x, y + offset_y - 0.03,
                             f"${driver.total_earnings:.0f}",
                             fontsize=7, ha='center', va='center')

    def draw_orders(self):
        """Рисование заказов"""
        for order in self.simulation.orders.values():
            if order.status.value == 'ожидает водителя':  # Только ожидающие
                start_zone = order.start_zone.name
                end_zone = order.end_zone.name

                if start_zone in self.zone_positions and end_zone in self.zone_positions:
                    x1, y1 = self.zone_positions[start_zone]
                    x2, y2 = self.zone_positions[end_zone]

                    # Стрелка заказа
                    self.ax.annotate('',
                                     xy=(x2, y2), xycoords='data',
                                     xytext=(x1, y1), textcoords='data',
                                     arrowprops=dict(arrowstyle="->",
                                                     color="purple",
                                                     alpha=0.5,
                                                     lw=2,
                                                     connectionstyle="arc3,rad=0.2"))

                    # Цена заказа
                    mid_x = (x1 + x2) / 2
                    mid_y = (y1 + y2) / 2
                    self.ax.text(mid_x, mid_y + 0.02,
                                 f"${order.price:.0f}",
                                 fontsize=8, ha='center', va='center',
                                 bbox=dict(boxstyle="round,pad=0.2",
                                           facecolor="white", alpha=0.7))

    def animate(self, frames=60, interval=500):
        """Запуск анимации"""
        ani = animation.FuncAnimation(self.fig, self.update_animation,
                                      frames=frames, interval=interval,
                                      blit=False, repeat=False)
        plt.show()


def main():
    # Создаем симуляцию
    sim = CitySimulation()

    # Создаем визуализатор
    visualizer = TaxiSimulationVisualizer(sim)

    # Запускаем анимацию на 60 кадров (минут)
    visualizer.animate(frames=60, interval=1000)  # 1 секунда на кадр


if __name__ == "__main__":
    main()
