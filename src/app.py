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
                if event.type == pygame.QUIT:
                    return
                if (
                    not game.active
                    and event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                    and renderer.splash_rect.collidepoint(event.pos)
                ):
                    game.start()

            accumulator += elapsed
            while accumulator >= PHYSICS_STEP:
                game.update(PHYSICS_STEP)
                accumulator -= PHYSICS_STEP
            background_offset += BACKGROUND_SPEED * elapsed
            background_offset %= screen.get_width()
            renderer.draw(background_offset, game)
            pygame.display.flip()
    finally:
        pygame.quit()
