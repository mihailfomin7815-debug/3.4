"""Отрисовка игровых объектов, заставки и анимации."""

import math
import random

import pygame

from .model import INITIAL_LIVES, INITIAL_SCORE


SPACE_COLOR = (8, 14, 29)
TEXT_COLOR = (231, 242, 251)
ACCENT_COLOR = (117, 224, 220)


class Renderer:
    """Подготовить фон и отрисовывать игровое поле."""

    def __init__(self, screen):
        """Подготовить графические слои, заставку и подписи для окна."""
        self.screen = screen
        self.starfield = self._make_starfield()
        self.asteroid_layer = self._make_asteroid_layer()
        self.splash_rect = pygame.Rect(0, 0, 468, 182)
        self.splash_rect.center = screen.get_rect().center

        title_font = pygame.font.SysFont("arial,dejavusans", 48, bold=True)
        label_font = pygame.font.SysFont("arial,dejavusans", 23)
        self.title = title_font.render("Астероиды", True, TEXT_COLOR)
        self.start_label = label_font.render(
            "Нажмите, чтобы начать", True, ACCENT_COLOR
        )
        self.lives_label = label_font.render(
            f"Жизни: {INITIAL_LIVES}", True, TEXT_COLOR
        )
        self.score_label = label_font.render(
            f"Счёт: {INITIAL_SCORE}", True, TEXT_COLOR
        )

    def draw(self, background_offset, show_splash):
        """Нарисовать фон, счётчики и при необходимости заставку."""
        self.screen.blit(self.starfield, (0, 0))
        left = -int(background_offset)
        self.screen.blit(self.asteroid_layer, (left, 0))
        self.screen.blit(
            self.asteroid_layer, (left + self.screen.get_width(), 0)
        )

        self.screen.blit(self.lives_label, (24, 20))
        score_rect = self.score_label.get_rect(
            topright=(self.screen.get_width() - 24, 20)
        )
        self.screen.blit(self.score_label, score_rect)

        if show_splash:
            self._draw_splash()

    def _draw_splash(self):
        """Нарисовать панель запуска в центре окна."""
        pygame.draw.rect(
            self.screen, (14, 25, 43), self.splash_rect, border_radius=16
        )
        pygame.draw.rect(
            self.screen, ACCENT_COLOR, self.splash_rect,
            width=1, border_radius=16,
        )
        center_x, center_y = self.splash_rect.center
        self.screen.blit(
            self.title, self.title.get_rect(center=(center_x, center_y - 23))
        )
        self.screen.blit(
            self.start_label,
            self.start_label.get_rect(center=(center_x, center_y + 37)),
        )

    def _make_starfield(self):
        """Создать неподвижное звёздное поле."""
        width, height = self.screen.get_size()
        starfield = pygame.Surface((width, height)).convert()
        starfield.fill(SPACE_COLOR)
        rng = random.Random(4)

        for _ in range(220):
            center = (rng.randrange(width), rng.randrange(height))
            brightness = rng.randint(55, 176)
            color = (brightness - 16, brightness, brightness + 24)
            pygame.draw.circle(starfield, color, center, rng.choice((1, 1, 2)))

        return starfield

    def _make_asteroid_layer(self):
        """Создать полупрозрачный слой, повторяемый по горизонтали."""
        width, height = self.screen.get_size()
        layer = pygame.Surface((width, height), pygame.SRCALPHA)
        rng = random.Random(17)

        for _ in range(25):
            center_x = rng.randrange(width)
            center_y = rng.randrange(height)
            radius = rng.randint(12, 37)
            points = []
            # Неравные радиусы на равномерных углах дают неровный контур.
            for vertex in range(9):
                angle = vertex * math.tau / 9
                distance = radius * rng.uniform(0.68, 1)
                points.append((
                    round(center_x + distance * math.cos(angle)),
                    round(center_y + distance * math.sin(angle)),
                ))

            # Копии за границами тайла сохраняют контур на стыке слоя.
            for shift in (-width, 0, width):
                outline = [(x + shift, y) for x, y in points]
                pygame.draw.polygon(layer, (59, 79, 115, 105), outline)
                pygame.draw.polygon(layer, (114, 145, 181, 135), outline, 1)

        return layer
