"""Проверки запуска приложения и отрисовки без физического дисплея."""

import os
import runpy
import unittest
from collections import defaultdict
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from src.model import (
    Body,
    EXPLOSION_FRAMES,
    EXPLOSION_SIZE,
    Game,
    WINDOW_SIZE,
)
from src.renderer import Renderer
from src.app import handle_event


class AppTests(unittest.TestCase):
    """Проверить обработку событий через обычную точку входа."""

    def setUp(self):
        """Подготовить виртуальные устройства SDL на время проверки."""
        environment = patch.dict(os.environ, {
            "SDL_VIDEODRIVER": "dummy",
            "SDL_AUDIODRIVER": "dummy",
        })
        environment.start()
        self.addCleanup(environment.stop)

    def tearDown(self):
        """Освободить Pygame после каждой проверки."""
        pygame.quit()

    def test_start_controls_game_over_and_restart(self):
        """Пройти запуск, управление, проигрыш и повторную игру."""
        game = Game()
        frames = []
        draw = Renderer.draw
        event = pygame.event.Event
        center = (480, 320)

        def events():
            """Сформировать последовательность действий пользователя."""
            yield [event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0))]
            yield [event(pygame.MOUSEBUTTONDOWN, button=3, pos=center)]
            yield [event(pygame.MOUSEBUTTONDOWN, button=1, pos=center)]
            yield []
            game.lives = 0
            game.score = 9
            game.rockets.clear()
            game.asteroids = [Body(game.ship.x - 40, game.ship.y)]
            yield []
            yield [event(pygame.MOUSEBUTTONDOWN, button=1, pos=center)]
            yield [event(pygame.QUIT)]

        def capture(renderer, offset, state):
            """Нарисовать кадр и сохранить наблюдаемое состояние."""
            draw(renderer, offset, state)
            frames.append((
                state.active, state.lives, state.score,
                state.ship.vx, len(state.rockets),
            ))

        def keys():
            """Удерживать тягу и стрельбу до столкновения."""
            pressed = defaultdict(bool)
            pressed[pygame.K_UP] = game.lives > 0
            pressed[pygame.K_SPACE] = game.lives > 0
            return pressed

        sequence = events()
        clock = SimpleNamespace(tick=lambda fps: 16)
        with (
            patch("src.app.Game", return_value=game),
            patch("pygame.event.get", side_effect=lambda: next(sequence)),
            patch("pygame.key.get_pressed", side_effect=keys),
            patch("pygame.time.Clock", return_value=clock),
            patch.object(Renderer, "draw", capture),
        ):
            runpy.run_module("main", run_name="__main__")
        self.assertEqual(
            [frame[0] for frame in frames],
            [False, False, True, True, False, True],
        )
        self.assertGreater(frames[3][3], 0)
        self.assertGreater(frames[3][4], 0)
        self.assertEqual(frames[4][1:3], (0, 9))
        self.assertEqual(frames[5][1:3], (3, 0))
        self.assertFalse(pygame.get_init())

    def test_window_is_released_after_error(self):
        """Закрывать Pygame при ошибке подготовки изображения."""
        with patch("src.app.Renderer", side_effect=RuntimeError("asset")):
            with self.assertRaisesRegex(RuntimeError, "asset"):
                runpy.run_module("main", run_name="__main__")
        self.assertFalse(pygame.get_init())

    def test_menu_buttons_restart_and_escape(self):
        """Проверить кнопки, клавишу R и повторное нажатие Esc."""
        pygame.init()
        renderer = Renderer(pygame.display.set_mode(WINDOW_SIZE))
        game = Game()
        event = pygame.event.Event
        escape = event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        handle_event(escape, game, renderer)
        self.assertTrue(game.paused)
        handle_event(
            event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)),
            game, renderer,
        )
        self.assertTrue(game.paused)
        handle_event(
            event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=True),
            game, renderer,
        )
        self.assertTrue(game.paused)
        handle_event(escape, game, renderer)
        self.assertFalse(game.paused)
        self.assertFalse(game.active)

        game.start()
        game.score = 12
        game.lives = 1
        game.elapsed_time = 60
        game.paused = True
        handle_event(event(
            pygame.MOUSEBUTTONDOWN, button=1,
            pos=renderer.menu_buttons["resume"].center,
        ), game, renderer)
        self.assertFalse(game.paused)
        self.assertEqual(
            (game.score, game.lives, game.elapsed_time), (12, 1, 60)
        )

        restart_events = (
            event(pygame.KEYDOWN, key=pygame.K_r),
            event(pygame.MOUSEBUTTONDOWN, button=1,
                  pos=renderer.menu_buttons["restart"].center),
        )
        for restart in restart_events:
            with self.subTest(event=restart):
                game.score = 20
                game.lives = 0
                game.elapsed_time = 60
                game.active = False
                game.paused = True
                handle_event(restart, game, renderer)
                self.assertTrue(game.active)
                self.assertFalse(game.paused)
                self.assertEqual(
                    (game.score, game.lives, game.elapsed_time), (0, 3, 0)
                )

    def test_wasd_pause_and_menu_exit_through_main(self):
        """Проверить WASD, неподвижность паузы и выход через меню."""
        game = Game()
        frames = []
        draw = Renderer.draw
        event = pygame.event.Event
        menu_buttons = {}
        pressed = defaultdict(bool)

        def events():
            """Сформировать управление и выход через настоящие кнопки."""
            pressed.update({pygame.K_w: True, pygame.K_d: True})
            yield [event(pygame.KEYDOWN, key=pygame.K_r)]
            pressed.clear()
            pressed.update({pygame.K_a: True, pygame.K_s: True})
            yield []
            yield [event(pygame.KEYDOWN, key=pygame.K_ESCAPE)]
            yield []
            yield [event(
                pygame.MOUSEBUTTONDOWN, button=1,
                pos=menu_buttons["exit"].center,
            )]

        def capture(renderer, offset, state):
            """Сохранить состояние движения и отрисовать кадр."""
            draw(renderer, offset, state)
            menu_buttons.update(renderer.menu_buttons)
            frames.append((
                state.ship.vx, state.ship.angular_speed,
                state.ship.thrusting, state.elapsed_time,
                offset, state.paused,
            ))

        sequence = events()
        with (
            patch("src.app.Game", return_value=game),
            patch("pygame.event.get", side_effect=lambda: next(sequence)),
            patch("pygame.key.get_pressed", return_value=pressed),
            patch("pygame.time.Clock",
                  return_value=SimpleNamespace(tick=lambda fps: 16)),
            patch.object(Renderer, "draw", capture),
        ):
            runpy.run_module("main", run_name="__main__")
        self.assertGreater(frames[0][0], 0)
        self.assertGreater(frames[0][1], 0)
        self.assertTrue(frames[0][2])
        self.assertLess(frames[1][0], frames[0][0])
        self.assertLess(frames[1][1], 0)
        self.assertFalse(frames[1][2])
        self.assertEqual(frames[1][:-1], frames[2][:-1])
        self.assertEqual(frames[2], frames[3])
        self.assertTrue(frames[2][-1])
        self.assertFalse(pygame.get_init())

    def test_rendered_hud_tiles_and_background(self):
        """Проверить счётчики, тайлы взрыва и повторение фонового слоя."""
        pygame.init()
        screen = pygame.display.set_mode(WINDOW_SIZE)
        renderer = Renderer(screen)
        game = Game()
        renderer.draw(0, game)
        original = pygame.image.tobytes(screen, "RGB")
        renderer.draw(WINDOW_SIZE[0], game)
        self.assertEqual(pygame.image.tobytes(screen, "RGB"), original)
        renderer.draw(100, game)
        self.assertNotEqual(pygame.image.tobytes(screen, "RGB"), original)
        renderer.draw(0, game)
        hud = screen.subsurface((0, 0, 960, 60))
        old_hud = pygame.image.tobytes(hud, "RGB")
        game.lives = 2
        game.score = 12
        renderer.draw(0, game)
        self.assertNotEqual(pygame.image.tobytes(hud, "RGB"), old_hud)
        self.assertEqual(len(renderer.explosion_frames), EXPLOSION_FRAMES)
        first = renderer.explosion_frames[0]
        last = renderer.explosion_frames[-1]
        self.assertEqual(first.get_size(), (EXPLOSION_SIZE, EXPLOSION_SIZE))
        self.assertGreater(pygame.mask.from_surface(first).count(), 0)
        self.assertEqual(pygame.mask.from_surface(last).count(), 0)
        self.assertNotEqual(
            pygame.image.tobytes(renderer.ship_frames[0], "RGBA"),
            pygame.image.tobytes(renderer.ship_frames[1], "RGBA"),
        )
