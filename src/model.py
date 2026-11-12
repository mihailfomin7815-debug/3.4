"""Параметры игры, игровые объекты и правила их взаимодействия."""

import math
import random
from dataclasses import dataclass


WINDOW_SIZE = (960, 640)  # Ширина и высота игрового поля в пикселях.
TARGET_FPS = 60  # Максимальная частота обновления окна.
PHYSICS_STEP = 1 / 120  # Шаг расчёта движения в секундах.
MAX_FRAME_TIME = 0.25  # Ограничение задержки при перемещении окна.
BACKGROUND_SPEED = 36  # Скорость движения фонового слоя в пикселях в секунду.
INITIAL_LIVES = 3  # Число возрождений корабля.
INITIAL_SCORE = 0  # Счёт в начале новой игры.
SHIP_RADIUS = 20  # Радиус столкновения корабля в пикселях.
SHIP_TURN_SPEED = 210  # Скорость поворота в градусах в секунду.
SHIP_ACCELERATION = 250  # Ускорение тяги в пикселях в секунду за секунду.
SHIP_MAX_SPEED = 340  # Максимальная скорость корабля.
SHIP_DRAG = 1.5  # Коэффициент затухания скорости без тяги.
SHIP_STOP_SPEED = 3  # Порог полной остановки, пиксели в секунду.
ASTEROID_RADIUS = 32  # Радиус столкновения астероида в пикселях.
ASTEROID_SPEED = (35, 105)  # Диапазон линейной скорости, пиксели в секунду.
ASTEROID_SPIN = (-70, 70)  # Диапазон угловой скорости, градусы в секунду.
SPAWN_INTERVAL = 1.2  # Интервал появления астероидов в секундах.
MAX_ASTEROIDS = 18  # Максимальное число астероидов на поле.
SPAWN_DISTANCE = 150  # Минимальное расстояние от корабля при появлении.
ROCKET_SPEED = 500  # Скорость ракеты в пикселях в секунду.
ROCKET_RADIUS = 4  # Радиус столкновения ракеты в пикселях.
ROCKET_RANGE_RATIO = 0.85  # Доля меньшей стороны поля для дальности ракеты.
FIRE_INTERVAL = 0.2  # Минимальное время между выстрелами в секундах.


@dataclass
class Body:
    """Хранить положение, скорость и радиус движущегося объекта."""

    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    angle: float = 0.0
    angular_speed: float = 0.0
    radius: float = ASTEROID_RADIUS

    def update(self, elapsed, size):
        """Переместить объект с переходом через границы игрового поля."""
        self.x = (self.x + self.vx * elapsed) % size[0]
        self.y = (self.y + self.vy * elapsed) % size[1]
        self.angle = (self.angle + self.angular_speed * elapsed) % 360


@dataclass
class Ship(Body):
    """Хранить состояние корабля игрока."""

    radius: float = SHIP_RADIUS
    thrusting: bool = False

    def steer(self, elapsed, turn, thrust):
        """Изменить скорость корабля по командам поворота и тяги."""
        self.angular_speed = max(-1, min(1, turn)) * SHIP_TURN_SPEED
        self.thrusting = thrust
        if thrust:
            direction = math.radians(self.angle)
            self.vx += math.cos(direction) * SHIP_ACCELERATION * elapsed
            self.vy += math.sin(direction) * SHIP_ACCELERATION * elapsed
            speed = math.hypot(self.vx, self.vy)
            if speed > SHIP_MAX_SPEED:
                self.vx *= SHIP_MAX_SPEED / speed
                self.vy *= SHIP_MAX_SPEED / speed
        else:
            # Экспоненциальное затухание не зависит от частоты кадров.
            damping = math.exp(-SHIP_DRAG * elapsed)
            self.vx *= damping
            self.vy *= damping
            if math.hypot(self.vx, self.vy) < SHIP_STOP_SPEED:
                self.vx = self.vy = 0.0


@dataclass
class Rocket(Body):
    """Хранить состояние ракеты с ограниченным временем жизни."""

    radius: float = ROCKET_RADIUS
    remaining: float = 0.0

    def update(self, elapsed, size):
        """Переместить ракету и уменьшить оставшееся время полёта."""
        super().update(elapsed, size)
        self.remaining = max(0.0, self.remaining - elapsed)


def distance_squared(first, second, size):
    """Вычислить квадрат кратчайшего расстояния на тороидальном поле."""
    # Остаток от деления выбирает ближайшую копию объекта за границей поля.
    dx = (first.x - second.x + size[0] / 2) % size[0] - size[0] / 2
    dy = (first.y - second.y + size[1] / 2) % size[1] - size[1] / 2
    return dx * dx + dy * dy


class Game:
    """Управлять состоянием игры независимо от графического окна."""

    def __init__(self, size=WINDOW_SIZE, rng=None):
        """Создать игровое поле и начальное состояние заставки."""
        self.size = size
        self.rng = rng if rng is not None else random.Random()
        self.active = False
        self.ship = Ship(size[0] / 2, size[1] / 2)
        self.asteroids = []
        self.rockets = []
        self.lives = INITIAL_LIVES
        self.score = INITIAL_SCORE
        self.spawn_timer = 0.0
        self.fire_timer = 0.0

    def start(self):
        """Начать новую игру с кораблём в центре и исходными счётчиками."""
        self.active = True
        self.ship = Ship(self.size[0] / 2, self.size[1] / 2)
        self.asteroids.clear()
        self.rockets.clear()
        self.lives = INITIAL_LIVES
        self.score = INITIAL_SCORE
        self.spawn_timer = 0.0
        self.fire_timer = 0.0

    def update(self, elapsed, turn=0, thrust=False, firing=False):
        """Обновить движение объектов и таймер появления астероидов."""
        if not self.active:
            return
        self.ship.steer(elapsed, turn, thrust)
        self.ship.update(elapsed, self.size)
        self.fire_timer = max(0.0, self.fire_timer - elapsed)
        if firing:
            self.fire()
        for asteroid in self.asteroids:
            asteroid.update(elapsed, self.size)
        for rocket in self.rockets:
            rocket.update(elapsed, self.size)
        self.rockets = [r for r in self.rockets if r.remaining > 0]
        self.spawn_timer -= elapsed
        if self.spawn_timer <= 0:
            self._spawn_asteroid()
            self.spawn_timer += SPAWN_INTERVAL

    def fire(self):
        """Выпустить ракету из носа корабля, если завершилась перезарядка."""
        if not self.active or self.fire_timer > 0:
            return False
        direction = math.radians(self.ship.angle)
        dx, dy = math.cos(direction), math.sin(direction)
        nose_distance = self.ship.radius + ROCKET_RADIUS
        self.rockets.append(Rocket(
            x=(self.ship.x + dx * nose_distance) % self.size[0],
            y=(self.ship.y + dy * nose_distance) % self.size[1],
            vx=dx * ROCKET_SPEED,
            vy=dy * ROCKET_SPEED,
            angle=self.ship.angle,
            remaining=ROCKET_RANGE_RATIO * min(self.size) / ROCKET_SPEED,
        ))
        self.fire_timer = FIRE_INTERVAL
        return True

    def _spawn_asteroid(self):
        """Добавить астероид вдали от корабля при наличии места."""
        if len(self.asteroids) >= MAX_ASTEROIDS:
            return
        # Ограничение попыток исключает зависание на тесном игровом поле.
        for _ in range(20):
            asteroid = Body(
                self.rng.uniform(0, self.size[0]),
                self.rng.uniform(0, self.size[1]),
            )
            if distance_squared(asteroid, self.ship, self.size) >= (
                SPAWN_DISTANCE ** 2
            ):
                direction = self.rng.uniform(0, math.tau)
                speed = self.rng.uniform(*ASTEROID_SPEED)
                asteroid.vx = math.cos(direction) * speed
                asteroid.vy = math.sin(direction) * speed
                asteroid.angle = self.rng.uniform(0, 360)
                asteroid.angular_speed = self.rng.uniform(*ASTEROID_SPIN)
                self.asteroids.append(asteroid)
                return
