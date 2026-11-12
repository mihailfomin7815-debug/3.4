"""Отрисовка игровых объектов, заставки и анимации."""

import random
from pathlib import Path

import pygame

from .model import INITIAL_LIVES, INITIAL_SCORE


ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
TEXT_COLOR = (231, 242, 251)
ACCENT_COLOR = (0, 255, 0)


class Renderer:
    """Подготовить фон и отрисовывать игровое поле."""

    def __init__(self, screen):
        """Подготовить графические слои, заставку и подписи для окна."""
        self.screen = screen
        asteroid = pygame.image.load(
            ASSETS_DIR / "asteroid.png"
        ).convert_alpha()
        self.asteroid_sprite = pygame.transform.smoothscale(asteroid, (76, 76))
        ship = pygame.image.load(ASSETS_DIR / "ship.png").convert_alpha()
        ship = ship.subsurface(ship.get_bounding_rect()).copy()
        self.ship_sprite = pygame.transform.smoothscale(ship, (52, 46))
        self.ship_frames = self._make_ship_frames()
        self.rocket_sprite = pygame.Surface((16, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(self.rocket_sprite, (255, 110, 20), (0, 0, 16, 8))
        pygame.draw.ellipse(self.rocket_sprite, (255, 250, 190), (5, 2, 10, 4))
        background = pygame.image.load(ASSETS_DIR / "background.png").convert()
        self.starfield = pygame.transform.smoothscale(
            background, screen.get_size()
        )
        self.asteroid_layer = self._make_asteroid_layer()
        self.splash_rect = pygame.Rect(0, 0, 468, 224)
        self.splash_rect.center = screen.get_rect().center
        self.splash_panel = pygame.Surface(
            self.splash_rect.size, pygame.SRCALPHA
        )
        self.splash_panel.fill((25, 14, 72, 175))
        pygame.draw.rect(
            self.splash_panel, (130, 117, 222, 220),
            self.splash_panel.get_rect(), width=2,
        )

        title_font = pygame.font.SysFont("arial,dejavusans", 48, bold=True)
        label_font = pygame.font.SysFont("arial,dejavusans", 27)
        self.title = title_font.render("Астероиды", True, TEXT_COLOR)
        self.start_label = label_font.render(
            "Нажмите, чтобы начать", True, TEXT_COLOR
        )
        self.lives_label = label_font.render(
            f"Жизни: {INITIAL_LIVES}", True, ACCENT_COLOR
        )
        self.score_label = label_font.render(
            f"Счёт: {INITIAL_SCORE}", True, ACCENT_COLOR
        )

    def draw(self, background_offset, game):
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

        if game.active:
            for asteroid in game.asteroids:
                self._draw_body(self.asteroid_sprite, asteroid)
            for rocket in game.rockets:
                self._draw_body(self.rocket_sprite, rocket)
            self._draw_body(
                self.ship_frames[int(game.ship.thrusting)], game.ship
            )
        else:
            self._draw_splash()

    def _draw_body(self, sprite, body):
        """Нарисовать повёрнутый объект и его копии у границ поля."""
        rotated = pygame.transform.rotate(sprite, -body.angle)
        width, height = self.screen.get_size()
        # Угловые копии сохраняют цельное изображение на тороидальном поле.
        for dx in (-width, 0, width):
            for dy in (-height, 0, height):
                rect = rotated.get_rect(
                    center=(round(body.x + dx), round(body.y + dy))
                )
                if rect.colliderect(self.screen.get_rect()):
                    self.screen.blit(rotated, rect)

    def _draw_splash(self):
        """Нарисовать панель запуска в центре окна."""
        self.screen.blit(self.splash_panel, self.splash_rect)
        center_x, center_y = self.splash_rect.center
        self.screen.blit(
            self.title, self.title.get_rect(center=(center_x, center_y - 23))
        )
        self.screen.blit(
            self.start_label,
            self.start_label.get_rect(center=(center_x, center_y + 37)),
        )

    def _make_ship_frames(self):
        """Подготовить изображения корабля с выключенной и включённой тягой."""
        idle = pygame.Surface((72, 64), pygame.SRCALPHA)
        idle.blit(self.ship_sprite, (10, 9))
        thrust = pygame.Surface((72, 64), pygame.SRCALPHA)
        pygame.draw.polygon(
            thrust, (255, 105, 20), [(18, 23), (0, 32), (18, 41)]
        )
        pygame.draw.polygon(
            thrust, (255, 245, 160), [(18, 27), (5, 32), (18, 37)]
        )
        thrust.blit(self.ship_sprite, (10, 9))
        return idle, thrust

    def _make_asteroid_layer(self):
        """Создать полупрозрачный слой, повторяемый по горизонтали."""
        width, height = self.screen.get_size()
        layer = pygame.Surface((width, height), pygame.SRCALPHA)
        asteroid = pygame.image.load(
            ASSETS_DIR / "asteroid.png"
        ).convert_alpha()
        asteroid = pygame.transform.smoothscale(asteroid, (80, 80))
        rng = random.Random(17)

        for _ in range(40):
            center_x = rng.randrange(width)
            center_y = rng.randrange(height)
            diameter = rng.randint(12, 54)
            sprite = pygame.transform.rotozoom(
                asteroid, rng.randrange(360), diameter / 80
            )
            sprite.set_alpha(rng.randint(100, 180))

            # Копии за границами тайла сохраняют контур на стыке слоя.
            for shift in (-width, 0, width):
                position = sprite.get_rect(center=(center_x + shift, center_y))
                layer.blit(sprite, position)

        return layer
