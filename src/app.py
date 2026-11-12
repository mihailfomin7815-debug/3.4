"""Окно игры, обработка ввода и игровой цикл."""

import pygame

from .model import BACKGROUND_SPEED, TARGET_FPS, WINDOW_SIZE
from .renderer import Renderer


def run():
    """Открыть окно и обновлять кадры до выхода из игры."""
    pygame.init()
    try:
        screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("Астероиды")
        clock = pygame.time.Clock()
        renderer = Renderer(screen)
        started = False
        background_offset = 0.0

        while True:
            elapsed = clock.tick(TARGET_FPS) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if (
                    not started
                    and event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                    and renderer.splash_rect.collidepoint(event.pos)
                ):
                    started = True

            background_offset += BACKGROUND_SPEED * elapsed
            background_offset %= screen.get_width()
            renderer.draw(background_offset, show_splash=not started)
            pygame.display.flip()
    finally:
        pygame.quit()
