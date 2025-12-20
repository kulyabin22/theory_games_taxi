import random
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.animation as animation
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.lines import Line2D

# =========================
# GIF АНИМАЦИЯ ГОРОДА
# =========================

def animate_city(history, zones, interval=600, filename="city_simulation.gif"):
    ZONE_SIZE = (2.6, 1.6)
    ZONE_GAP = 1.2

    ZONE_COORDS = {
        1: (-3.0,  2.0),   # Центр (верхний левый)
        2: ( 3.0,  2.0),   # Спальный район 2 (верхний правый)
        3: (-3.0, -2.0),   # Спальный район 1 (нижний левый)
        4: ( 3.0, -2.0),   # Периферия (нижний правый)
    }

    def surge_to_color(surge):
        value = min(1.0, max(0.0, (surge - 1) / 2))
        return cm.Reds(value)

    fig, ax = plt.subplots(figsize=(10, 6))

    legend_elements = [
        Line2D([0], [0], marker="^", color="w",
               label="Свободный водитель",
               markerfacecolor="green", markeredgecolor="black", markersize=10),
        Line2D([0], [0], marker="s", color="w",
               label="Переезд",
               markerfacecolor="red", markeredgecolor="black", markersize=10),
        Line2D([0], [0], color="purple", lw=3,
               label="Смена зоны")
    ]

    def draw_frame(t):
        ax.clear()
        ax.set_facecolor("#f2f2f2")
        ax.set_xlim(-7, 7)
        ax.set_ylim(-3, 4)
        ax.axis("off")

        ax.set_title(f"Taxi simulation — minute {t + 1}",
                     fontsize=14, weight="bold", pad=20)

        # --- ЗОНЫ ---
        for zone in zones.values():
            cx, cy = ZONE_COORDS[zone.id]
            w, h = ZONE_SIZE
            surge = history["surge"][zone.id][t]

            rect = Rectangle(
                (cx - w / 2, cy - h / 2),
                w, h,
                facecolor=surge_to_color(surge),
                edgecolor="black",
                linewidth=2,
                alpha=0.6
            )
            ax.add_patch(rect)

            ax.text(
                cx, cy + h / 2 + 0.35,
                f"{zone.name}\nPrice x{surge:.2f}",
                ha="center",
                fontsize=11,
                bbox=dict(boxstyle="round", fc="white", alpha=0.9)
            )

        # --- СТРЕЛКИ ПЕРЕЕЗДА ---
        if t > 0:
            prev = history["drivers_positions"][t - 1]
            curr = history["drivers_positions"][t]

            for driver_id in curr:
                if prev[driver_id] != curr[driver_id]:
                    x1, y1 = ZONE_COORDS[prev[driver_id]]
                    x2, y2 = ZONE_COORDS[curr[driver_id]]

                    arrow = FancyArrowPatch(
                        (x1, y1),
                        (x2, y2),
                        arrowstyle="->",
                        connectionstyle="arc3,rad=0.25",
                        color="purple",
                        linewidth=3,
                        alpha=0.7
                    )
                    ax.add_patch(arrow)

        # --- ВОДИТЕЛИ ---
        snapshot = history["drivers_positions"][t]
        for driver_id, zone_id in snapshot.items():
            cx, cy = ZONE_COORDS[zone_id]

            dx = random.uniform(-ZONE_SIZE[0] / 2 + 0.3,
                                ZONE_SIZE[0] / 2 - 0.3)
            dy = random.uniform(-ZONE_SIZE[1] / 2 + 0.3,
                                ZONE_SIZE[1] / 2 - 0.3)

            is_moving = False
            if t > 0:
                is_moving = history["drivers_positions"][t - 1][driver_id] != zone_id

            marker = "s" if is_moving else "^"
            color = "red" if is_moving else "green"

            ax.scatter(cx + dx, cy + dy,
                       marker=marker, s=80,
                       color=color, edgecolors="black", zorder=3)

        ax.legend(handles=legend_elements,
                  loc="lower center",
                  bbox_to_anchor=(0.5, -0.05),
                  ncol=3, frameon=True)

    anim = animation.FuncAnimation(
        fig, draw_frame,
        frames=len(history["drivers_positions"]),
        interval=interval
    )

    plt.subplots_adjust(bottom=0.18)
    anim.save(filename, writer="pillow")
    plt.close(fig)

    return anim