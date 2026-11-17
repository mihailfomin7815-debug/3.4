"""Проверки движения объектов, столкновений и жизненного цикла игры."""

import math
import random
import unittest

from src.model import (
    ASTEROID_SPEED,
    Body,
    EXPLOSION_DURATION,
    Explosion,
    FIRE_INTERVAL,
    Game,
    INITIAL_LIVES,
    MAX_ASTEROIDS,
    MIN_SPAWN_INTERVAL,
    PHYSICS_STEP,
    RESPAWN_PROTECTION,
    ROCKET_SPEED,
    Rocket,
    SHIP_MAX_SPEED,
    SPAWN_DISTANCE,
    SPAWN_INTERVAL,
    SPAWN_RAMP_DURATION,
    Ship,
    WINDOW_SIZE,
    distance_squared,
)


class MovementTests(unittest.TestCase):
    """Проверить движение на тороидальном поле и управление кораблём."""

    def test_wrapping_preserves_velocity(self):
        """Переносить координаты через все края, сохраняя обе скорости."""
        for x, y, vx, vy in (
            (959, 639, 240, 240), (1, 1, -240, -240),
            (959, 1, 240, -240), (1, 639, -240, 240),
        ):
            with self.subTest(x=x, y=y):
                body = Body(x, y, vx, vy, 359, 240)
                body.update(PHYSICS_STEP, WINDOW_SIZE)
                self.assertEqual(body.x, (x + vx * PHYSICS_STEP) % 960)
                self.assertEqual(body.y, (y + vy * PHYSICS_STEP) % 640)
                self.assertEqual((body.vx, body.vy), (vx, vy))
                self.assertEqual(body.angular_speed, 240)
                self.assertEqual(body.angle, 1)

    def test_corner_distance(self):
        """Учитывать кратчайшее расстояние через угол поля."""
        self.assertEqual(
            distance_squared(Body(1, 1), Body(959, 639), WINDOW_SIZE), 8
        )

    def test_thrust_and_speed_limit(self):
        """Разгонять корабль по ориентации и ограничивать его скорость."""
        ship = Ship(0, 0, angle=90)
        for _ in range(600):
            ship.steer(PHYSICS_STEP, 0, True)
        self.assertAlmostEqual(ship.vx, 0)
        self.assertAlmostEqual(ship.vy, SHIP_MAX_SPEED)
        self.assertTrue(ship.thrusting)

    def test_braking_reaches_full_stop(self):
        """Полностью останавливать корабль после выключения двигателя."""
        ship = Ship(0, 0, vx=100, vy=100)
        for _ in range(600):
            ship.steer(PHYSICS_STEP, 0, False)
        self.assertEqual((ship.vx, ship.vy), (0, 0))
        self.assertFalse(ship.thrusting)

    def test_turning_and_release(self):
        """Прекращать поворот после отпускания клавиши."""
        ship = Ship(0, 0)
        ship.steer(0.1, 1, False)
        ship.update(0.1, WINDOW_SIZE)
        self.assertEqual(ship.angle, 21)
        ship.steer(0.1, 0, False)
        ship.update(0.1, WINDOW_SIZE)
        self.assertEqual(ship.angle, 21)

    def test_active_braking_is_stronger_and_overrides_thrust(self):
        """Ускорять торможение и отключать тягу при нажатом тормозе."""
        coasting = Ship(0, 0, vx=100, vy=50)
        braking = Ship(0, 0, vx=100, vy=50)
        coasting.steer(0.2, 0, False)
        braking.steer(0.2, 0, True, braking=True)
        self.assertLess(braking.vx, coasting.vx)
        self.assertLess(braking.vy, coasting.vy)
        self.assertFalse(braking.thrusting)


class GameTests(unittest.TestCase):
    """Проверить правила игры на воспроизводимых начальных данных."""

    def setUp(self):
        """Создать активную игру с отложенным появлением астероидов."""
        self.game = Game(rng=random.Random(1))
        self.game.start()
        self.game.spawn_timer = 100

    def test_splash_does_not_simulate_or_fire(self):
        """Сохранять исходные счётчики и пустое поле на заставке."""
        game = Game()
        game.update(2, thrust=True, firing=True)
        self.assertFalse(game.fire())
        self.assertEqual(game.lives, INITIAL_LIVES)
        self.assertEqual(game.score, 0)
        self.assertEqual(game.asteroids, [])
        self.assertEqual(game.rockets, [])
        self.assertEqual((game.ship.x, game.ship.y), (480, 320))

    def test_rocket_origin_direction_and_range(self):
        """Создавать ракету у носа с фиксированной скоростью и дальностью."""
        for angle in (0, 90, 180, 270):
            with self.subTest(angle=angle):
                self.game.ship = Ship(959, 639, vx=200, angle=angle)
                self.game.fire_timer = 0
                self.assertTrue(self.game.fire())
                rocket = self.game.rockets[-1]
                direction = math.radians(angle)
                self.assertAlmostEqual(
                    rocket.x, (959 + 24 * math.cos(direction)) % 960
                )
                self.assertAlmostEqual(
                    rocket.y, (639 + 24 * math.sin(direction)) % 640
                )
                self.assertAlmostEqual(
                    math.hypot(rocket.vx, rocket.vy), ROCKET_SPEED
                )
                self.assertLess(rocket.remaining * ROCKET_SPEED, 640)

    def test_fire_cooldown(self):
        """Ограничивать частоту повторных выстрелов."""
        self.assertTrue(self.game.fire())
        self.assertFalse(self.game.fire())
        self.game.update(FIRE_INTERVAL)
        self.assertTrue(self.game.fire())

    def test_expired_rocket_cannot_score(self):
        """Удалять истёкшую ракету до обработки попаданий."""
        self.game.rockets = [Rocket(100, 100, remaining=0.001)]
        self.game.asteroids = [Body(100, 100)]
        self.game.update(PHYSICS_STEP)
        self.assertEqual(self.game.rockets, [])
        self.assertEqual(self.game.score, 0)
        self.assertEqual(len(self.game.asteroids), 1)

    def test_rocket_hit_and_explosion(self):
        """Начислять одно очко, удалять объекты и проигрывать взрыв."""
        self.game.rockets = [Rocket(100, 100, remaining=1)]
        self.game.asteroids = [Body(100, 100)]
        self.game.update(PHYSICS_STEP)
        self.assertEqual(self.game.score, 1)
        self.assertEqual(self.game.rockets, [])
        self.assertEqual(self.game.asteroids, [])
        self.assertEqual(len(self.game.explosions), 1)
        self.assertEqual(self.game.explosions[0].age, 0)
        self.game.update(EXPLOSION_DURATION / 2)
        self.assertEqual(len(self.game.explosions), 1)
        self.game.update(EXPLOSION_DURATION / 2)
        self.assertEqual(self.game.explosions, [])

    def test_one_rocket_hits_only_one_overlapping_asteroid(self):
        """Обрабатывать одно попадание для каждой ракеты."""
        self.game.rockets = [Rocket(100, 100, remaining=1)]
        self.game.asteroids = [Body(100, 100), Body(100, 100)]
        self.game.update(PHYSICS_STEP)
        self.assertEqual(self.game.score, 1)
        self.assertEqual(len(self.game.asteroids), 1)

    def test_two_rockets_do_not_score_twice_for_one_asteroid(self):
        """Начислять очко за один астероид только один раз."""
        self.game.rockets = [
            Rocket(100, 100, remaining=1), Rocket(100, 100, remaining=1)
        ]
        self.game.asteroids = [Body(100, 100)]
        self.game.update(PHYSICS_STEP)
        self.assertEqual(self.game.score, 1)
        self.assertEqual(len(self.game.rockets), 1)

    def test_collision_through_corner(self):
        """Регистрировать попадание по копии астероида через угол поля."""
        self.game.rockets = [Rocket(1, 1, remaining=1)]
        self.game.asteroids = [Body(959, 639)]
        self.game.update(PHYSICS_STEP)
        self.assertEqual(self.game.score, 1)

    def test_ship_respawns_at_rest(self):
        """Восстанавливать корабль в центре и снимать одну жизнь."""
        self.game.ship = Ship(100, 100, vx=50, vy=30, angle=90)
        self.game.asteroids = [Body(100, 100), Body(100, 100)]
        self.game.update(PHYSICS_STEP)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.score, 0)
        self.assertEqual((self.game.ship.x, self.game.ship.y), (480, 320))
        self.assertEqual((self.game.ship.vx, self.game.ship.vy), (0, 0))
        self.assertEqual(self.game.ship.angular_speed, 0)
        self.assertEqual(len(self.game.asteroids), 1)
        self.assertEqual(len(self.game.explosions), 1)

    def test_respawn_protection_expires(self):
        """Предотвращать повторную потерю жизни до окончания защиты."""
        self.game.asteroids = [Body(480, 320)]
        self.game.update(PHYSICS_STEP)
        self.game.asteroids = [Body(480, 320)]
        self.game.update(RESPAWN_PROTECTION / 2)
        self.assertEqual(self.game.lives, 2)
        self.game.update(RESPAWN_PROTECTION / 2)
        self.assertEqual(self.game.lives, 1)

    def test_game_ends_on_collision_with_zero_lives(self):
        """Следовать условию задания о гибели при исходном нуле жизней."""
        self.game.score = 7
        for expected in (2, 1, 0):
            self.game.protection = 0
            self.game.asteroids = [Body(480, 320)]
            self.game.update(PHYSICS_STEP)
            self.assertEqual(self.game.lives, expected)
            self.assertTrue(self.game.active)
        self.game.protection = 0
        self.game.asteroids = [Body(480, 320)]
        self.game.rockets = [Rocket(100, 100, remaining=1)]
        self.game.update(PHYSICS_STEP)
        self.assertFalse(self.game.active)
        self.assertEqual((self.game.lives, self.game.score), (0, 7))
        self.assertEqual(self.game.asteroids, [])
        self.assertEqual(self.game.rockets, [])
        self.assertEqual(self.game.explosions, [])

    def test_restart_resets_game(self):
        """Сбрасывать счёт, объекты и таймеры при новом запуске."""
        self.game.active = False
        self.game.lives = 0
        self.game.score = 9
        self.game.asteroids = [Body(10, 10)]
        self.game.rockets = [Rocket(10, 10)]
        self.game.explosions = [Explosion(10, 10)]
        self.game.protection = 1
        self.game.fire_timer = 1
        self.game.elapsed_time = SPAWN_RAMP_DURATION
        self.game.paused = True
        self.game.start()
        self.assertTrue(self.game.active)
        self.assertFalse(self.game.paused)
        self.assertEqual((self.game.lives, self.game.score), (3, 0))
        self.assertEqual(self.game.asteroids, [])
        self.assertEqual(self.game.rockets, [])
        self.assertEqual(self.game.explosions, [])
        self.assertEqual(self.game.protection, 0)
        self.assertEqual(self.game.fire_timer, 0)
        self.assertEqual(self.game.elapsed_time, 0)
        self.assertEqual(self.game.spawn_interval, SPAWN_INTERVAL)
        self.assertEqual(self.game.spawn_timer, 0)

    def test_pause_freezes_objects_timers_and_firing(self):
        """Сохранять всё состояние игры на время открытого меню."""
        game = self.game
        game.ship.vx = 100
        game.asteroids = [Body(100, 100, vx=50)]
        game.rockets = [Rocket(200, 200, vx=500, remaining=1)]
        game.explosions = [Explosion(300, 300, age=0.1)]
        game.protection = 1
        game.fire_timer = 0.2
        game.paused = True
        game.update(30, turn=1, thrust=True, firing=True, braking=True)
        self.assertEqual(game.ship.x, 480)
        self.assertEqual(game.ship.angle, 0)
        self.assertEqual(game.ship.vx, 100)
        self.assertEqual(game.asteroids[0].x, 100)
        self.assertEqual(game.rockets[0].x, 200)
        self.assertEqual(game.rockets[0].remaining, 1)
        self.assertEqual(game.explosions[0].age, 0.1)
        self.assertEqual(game.elapsed_time, 0)
        self.assertEqual(game.spawn_timer, 100)
        self.assertEqual(game.fire_timer, 0.2)
        self.assertEqual(game.protection, 1)
        self.assertFalse(game.fire())

    def test_spawn_interval_decreases_to_minimum(self):
        """Плавно сокращать паузу и удерживать минимальный интервал."""
        for elapsed, expected in (
            (0, SPAWN_INTERVAL),
            (SPAWN_RAMP_DURATION / 2,
             (SPAWN_INTERVAL + MIN_SPAWN_INTERVAL) / 2),
            (SPAWN_RAMP_DURATION, MIN_SPAWN_INTERVAL),
            (SPAWN_RAMP_DURATION * 10, MIN_SPAWN_INTERVAL),
        ):
            with self.subTest(elapsed=elapsed):
                self.game.elapsed_time = elapsed
                self.assertAlmostEqual(self.game.spawn_interval, expected)

    def test_later_game_spawns_more_asteroids_in_same_time(self):
        """Проверить рост частоты через обычное обновление модели."""
        counts = []
        for initial_time in (0, SPAWN_RAMP_DURATION):
            game = Game(rng=random.Random(1))
            game.start()
            game.elapsed_time = initial_time
            count = 0
            for _ in range(6 * 120):
                game.update(PHYSICS_STEP)
                count += len(game.asteroids)
                # Убираем объекты, чтобы лимит поля не влиял на частоту.
                game.asteroids.clear()
            counts.append(count)
        self.assertGreater(counts[1], counts[0] * 2)

    def test_game_time_freezes_on_splash_and_after_game_over(self):
        """Учитывать время только активной партии."""
        game = Game()
        game.update(30)
        self.assertEqual(game.elapsed_time, 0)
        game.start()
        game.spawn_timer = 100
        game.update(1)
        self.assertEqual(game.elapsed_time, 1)
        game.lives = 0
        game.asteroids = [Body(480, 320)]
        game.update(PHYSICS_STEP)
        self.assertFalse(game.active)
        final_time = game.elapsed_time
        game.update(30)
        self.assertEqual(game.elapsed_time, final_time)

    def test_respawn_preserves_difficulty(self):
        """Сохранять накопленную сложность после потери жизни."""
        self.game.elapsed_time = SPAWN_RAMP_DURATION
        self.game.asteroids = [Body(480, 320)]
        self.game.update(PHYSICS_STEP)
        self.assertEqual(self.game.lives, 2)
        self.assertGreater(self.game.elapsed_time, SPAWN_RAMP_DURATION)
        self.assertEqual(self.game.spawn_interval, MIN_SPAWN_INTERVAL)

    def test_asteroids_pass_through_each_other(self):
        """Сохранять оба астероида при пересечении их траекторий."""
        self.game.asteroids = [Body(100, 100), Body(100, 100)]
        self.game.update(PHYSICS_STEP)
        self.assertEqual(len(self.game.asteroids), 2)

    def test_spawn_interval_distance_and_limit(self):
        """Соблюдать интервал, безопасную область и ограничение числа."""
        self.game.spawn_timer = 0
        self.game.update(PHYSICS_STEP)
        asteroid = self.game.asteroids[0]
        self.assertGreaterEqual(
            distance_squared(asteroid, self.game.ship, self.game.size),
            SPAWN_DISTANCE ** 2,
        )
        speed = math.hypot(asteroid.vx, asteroid.vy)
        self.assertGreaterEqual(speed, ASTEROID_SPEED[0])
        self.assertLessEqual(speed, ASTEROID_SPEED[1])
        self.game.update(SPAWN_INTERVAL / 2)
        self.assertEqual(len(self.game.asteroids), 1)
        self.game.asteroids = [Body(100, 100) for _ in range(MAX_ASTEROIDS)]
        self.game.spawn_timer = 0
        self.game.update(PHYSICS_STEP)
        self.assertEqual(len(self.game.asteroids), MAX_ASTEROIDS)

    def test_small_field_does_not_hang_when_spawn_is_impossible(self):
        """Завершать попытки появления астероида на тесном поле."""
        game = Game(size=(50, 50))
        game.start()
        game.update(PHYSICS_STEP)
        self.assertEqual(game.asteroids, [])
