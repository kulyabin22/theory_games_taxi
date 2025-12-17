# utils/pygame_visualizer.py
import pygame
import sys
from pygame.locals import *
from core import CitySimulation


class PyGameVisualizer:
    """Интерактивная визуализация с PyGame"""

    def __init__(self, simulation, width=1200, height=800):
        self.simulation = simulation
        self.width = width
        self.height = height

        # Инициализация PyGame
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Симуляция Такси - Теория Игр")

        # Шрифты
        self.font = pygame.font.SysFont('Arial', 20)
        self.title_font = pygame.font.SysFont('Arial', 32, bold=True)

        # Цвета
        self.colors = {
            'background': (240, 240, 245),
            'zone_center': (255, 100, 100),
            'zone_residential': (100, 255, 100),
            'zone_periphery': (100, 100, 255),
            'driver_free': (50, 200, 50),
            'driver_busy': (255, 50, 50),
            'driver_moving': (255, 200, 50),
            'text': (30, 30, 30),
            'grid': (200, 200, 200)
        }

        # Позиции зон
        self.zone_positions = {
            'Центр': (3*width // 5, height // 2),
            'Спальный район 1': (width // 5, height // 2),
            'Спальный район 2': (2*width // 5, height // 2),
            'Периферия': (4 * width // 5, height // 2)
        }

        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = False
        self.speed = 1.0  # Скорость симуляции

    def draw_zone(self, zone, position):
        """Рисование зоны"""
        x, y = position
        radius = 100

        # Цвет зоны
        color_map = {
            'Центр': self.colors['zone_center'],
            'Спальный район': self.colors['zone_residential'],
            'Периферия': self.colors['zone_periphery']
        }

        color = color_map.get(zone.name, (150, 150, 150))

        # Рисуем зону
        pygame.draw.circle(self.screen, color, (x, y), radius)
        pygame.draw.circle(self.screen, (0, 0, 0), (x, y), radius, 3)

        # Название зоны
        text = self.font.render(zone.name, True, self.colors['text'])
        text_rect = text.get_rect(center=(x, y - 120))
        self.screen.blit(text, text_rect)

        # surge множитель
        surge_text = self.font.render(f"x{zone.surge_multiplier:.2f}",
                                      True, (255, 255, 0))
        surge_rect = surge_text.get_rect(center=(x, y - 90))
        self.screen.blit(surge_text, surge_rect)

        # Количество водителей
        drivers_count = len([d for d in self.simulation.drivers.values()
                             if d.current_zone == zone])
        drivers_text = self.font.render(f"Водителей: {drivers_count}",
                                        True, self.colors['text'])
        drivers_rect = drivers_text.get_rect(center=(x, y - 60))
        self.screen.blit(drivers_text, drivers_rect)

        return radius

    def draw_driver(self, driver, zone_position):
        """Рисование водителя"""
        x, y = zone_position
        driver_index = list(self.simulation.drivers.keys()).index(driver.id)

        # Позиция водителя (распределяем по кругу)
        angle = (driver_index * 2 * 3.14159) / len(self.simulation.drivers)
        offset_x = 70 * (len(self.simulation.drivers) / 15) * pygame.math.Vector2(1, 0).rotate(angle * 57.3).x
        offset_y = 70 * (len(self.simulation.drivers) / 15) * pygame.math.Vector2(1, 0).rotate(angle * 57.3).y

        pos_x = int(x + offset_x)
        pos_y = int(y + offset_y)

        # Цвет в зависимости от статуса
        if driver.status.value == 'свободен':
            color = self.colors['driver_free']
            radius = 15
        elif driver.status.value == 'выполняет заказ':
            color = self.colors['driver_busy']
            radius = 18
        else:  # moving
            color = self.colors['driver_moving']
            radius = 16

        # Рисуем водителя
        pygame.draw.circle(self.screen, color, (pos_x, pos_y), radius)
        pygame.draw.circle(self.screen, (0, 0, 0), (pos_x, pos_y), radius, 2)

        # Имя водителя
        name_text = self.font.render(driver.name[:3], True, (0, 0, 0))
        name_rect = name_text.get_rect(center=(pos_x, pos_y))
        self.screen.blit(name_text, name_rect)

        # Заработок (маленьким шрифтом)
        earnings_text = pygame.font.SysFont('Arial', 12).render(
            f"${driver.total_earnings:.0f}", True, (0, 0, 0))
        earnings_rect = earnings_text.get_rect(center=(pos_x, pos_y + 20))
        self.screen.blit(earnings_text, earnings_rect)

        return (pos_x, pos_y)

    def draw_stats(self):
        """Рисование статистики"""
        stats = self.simulation.get_statistics()

        # Панель статистики
        stats_panel = pygame.Rect(10, 10, 300, 150)
        pygame.draw.rect(self.screen, (255, 255, 255, 200), stats_panel)
        pygame.draw.rect(self.screen, (0, 0, 0), stats_panel, 2)

        # Текст статистики
        lines = [
            f"Время: {stats['time']:.1f} мин",
            f"Водителей: {stats['total_drivers']}",
            f"  Свободны: {stats['free_drivers']}",
            f"  Заняты: {stats['busy_drivers']}",
            f"  В пути: {stats['moving_drivers']}",
            f"Заказы: {stats['active_orders']} активных",
            f"Выполнено: {stats.get('total_orders_completed', 0)}",
            f"Общий заработок: ${stats['total_earnings']:.2f}"
        ]

        for i, line in enumerate(lines):
            text = self.font.render(line, True, self.colors['text'])
            self.screen.blit(text, (20, 20 + i * 20))

    def draw_controls(self):
        """Рисование элементов управления"""
        controls_text = self.font.render(
            "Пробел: Пауза/Продолжить | Стрелки: Скорость | R: Сброс | ESC: Выход",
            True, (100, 100, 100))
        self.screen.blit(controls_text, (10, self.height - 30))

    def run(self):
        """Основной цикл визуализации"""
        while self.running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                elif event.type == KEYDOWN:
                    if event.key == K_SPACE:
                        self.paused = not self.paused
                    elif event.key == K_UP:
                        self.speed = min(5.0, self.speed + 0.5)
                    elif event.key == K_DOWN:
                        self.speed = max(0.1, self.speed - 0.5)
                    elif event.key == K_r:
                        # Сброс симуляции
                        self.simulation = CitySimulation()
                    elif event.key == K_ESCAPE:
                        self.running = False

            # Очистка экрана
            self.screen.fill(self.colors['background'])

            # Обновление симуляции если не на паузе
            if not self.paused:
                self.simulation.run_iteration()
                pygame.time.delay(int(1000 / self.speed))  # Задержка по скорости

            # Рисование зон
            for zone_name, position in self.zone_positions.items():
                zone = next((z for z in self.simulation.zones.values()
                             if z.name == zone_name), None)
                if zone:
                    self.draw_zone(zone, position)

            # Рисование водителей
            for driver in self.simulation.drivers.values():
                zone_name = driver.current_zone.name
                if zone_name in self.zone_positions:
                    self.draw_driver(driver, self.zone_positions[zone_name])

            # Рисование статистики и контролов
            self.draw_stats()
            self.draw_controls()

            # Статус паузы
            if self.paused:
                pause_text = self.title_font.render("ПАУЗА", True, (255, 0, 0))
                pause_rect = pause_text.get_rect(center=(self.width // 2, 40))
                self.screen.blit(pause_text, pause_rect)

            # Скорость
            speed_text = self.font.render(f"Скорость: {self.speed:.1f}x",
                                          True, (0, 0, 200))
            self.screen.blit(speed_text, (self.width - 150, 20))

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

def main():
    # Создаем симуляцию
    sim = CitySimulation()

    # Создаем визуализатор
    visualizer = PyGameVisualizer(sim)

    # Запускаем анимацию на 60 кадров (минут)
    visualizer.run()# 1 секунда на кадр


if __name__ == "__main__":
    main()