"""Окно игры, обработка ввода и игровой цикл."""

import pygame

from .model import (
    BACKGROUND_SPEED,
    Game,
    MAX_FRAME_TIME,
    PHYSICS_STEP,
    TARGET_FPS,
    WINDOW_SIZE,
)
from .renderer import Renderer


def handle_event(event, game, renderer):
    """Обработать событие и вернуть признак продолжения работы приложения."""
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN and not getattr(event, "repeat", False):
        if event.key == pygame.K_ESCAPE:
            game.paused = not game.paused
        elif event.key == pygame.K_r:
            game.start()
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if game.paused:
            for action, rect in renderer.menu_buttons.items():
                if rect.collidepoint(event.pos):
                    if action == "exit":
                        return False
                    if action == "restart":
                        game.start()
                    else:
                        game.paused = False
                    break
        elif not game.active and renderer.splash_rect.collidepoint(event.pos):
            game.start()
    return True


def run():
    """Открыть окно и обновлять кадры до выхода из игры."""
    pygame.init()
    try:
        screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("Астероиды")
        clock = pygame.time.Clock()
        renderer = Renderer(screen)
        game = Game()
        accumulator = 0.0
        background_offset = 0.0

        while True:
            elapsed = min(clock.tick(TARGET_FPS) / 1000, MAX_FRAME_TIME)
            for event in pygame.event.get():
                if not handle_event(event, game, renderer):
                    return

            if game.paused:
                accumulator = 0.0
            else:
                accumulator += elapsed
                keys = pygame.key.get_pressed()
                turn_right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
                turn_left = keys[pygame.K_LEFT] or keys[pygame.K_a]
                while accumulator >= PHYSICS_STEP:
                    game.update(
                        PHYSICS_STEP,
                        turn=int(turn_right) - int(turn_left),
                        thrust=bool(keys[pygame.K_UP] or keys[pygame.K_w]),
                        firing=bool(keys[pygame.K_SPACE]),
                        braking=bool(keys[pygame.K_DOWN] or keys[pygame.K_s]),
                    )
                    accumulator -= PHYSICS_STEP
                background_offset += BACKGROUND_SPEED * elapsed
                background_offset %= screen.get_width()
            renderer.draw(background_offset, game)
            pygame.display.flip()
    finally:
        pygame.quit()
