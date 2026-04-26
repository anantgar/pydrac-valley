"""
Dracula HUD overlay.

Displays:
- Blood bar (top-left)
- Current form indicator (below blood bar)
- Time-of-day display (top-right)
- Sunlight warning (flashing red text when taking damage)
- Elisabeta portrait overlay (centered, toggled with P)
"""
import os
import pygame
from settings import *
from support import get_path


class Overlay:
    def __init__(self, player, sky):
        self.display_surface = pygame.display.get_surface()
        self.player = player
        self.sky = sky

        # Font
        font_path = os.path.join(os.path.dirname(__file__), FONT_PATH)
        self.font = pygame.font.Font(font_path, 22)
        self.font_large = pygame.font.Font(font_path, 30)
        self.font_small = pygame.font.Font(font_path, 16)

        # Sunlight warning flash timer
        self._warning_timer = 0.0

        # Elisabeta portrait image
        portrait_path = get_path('../graphics/objects/elisabeta_portrait.png')
        self.elisabeta_portrait = pygame.image.load(portrait_path).convert_alpha()

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------
    def _draw_blood_bar(self):
        x, y = BLOOD_BAR_POS
        w, h = BLOOD_BAR_SIZE
        ratio = self.player.blood_system.ratio

        # Background
        bg_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.display_surface, (40, 0, 0), bg_rect, border_radius=4)

        # Fill
        fill_w = int(w * ratio)
        if fill_w > 0:
            fill_rect = pygame.Rect(x, y, fill_w, h)
            pygame.draw.rect(self.display_surface, (180, 0, 0), fill_rect, border_radius=4)

        # Border
        pygame.draw.rect(self.display_surface, (100, 0, 0), bg_rect, 2, border_radius=4)

        # Label
        blood_val = int(self.player.blood_system.blood)
        label = self.font_small.render(f'Blood: {blood_val}/{int(MAX_BLOOD)}', True, (220, 200, 200))
        self.display_surface.blit(label, (x + 4, y + 2))

    def _draw_form_indicator(self):
        x, y = FORM_INDICATOR_POS
        form_name = self.player.current_form.upper()

        color_map = {
            FORM_HUMAN: (200, 200, 200),
            FORM_BAT: (120, 120, 255),
            FORM_WEREWOLF: (255, 180, 80),
        }
        color = color_map.get(self.player.current_form, (200, 200, 200))
        label = self.font.render(f'Form: {form_name}', True, color)
        self.display_surface.blit(label, (x, y))

    def _draw_time_indicator(self):
        x, y = TIME_INDICATOR_POS
        time_str = self.sky.get_hour_minute_string()
        period = 'NIGHT' if self.sky.is_nighttime() else 'DAY'
        color = (200, 200, 255) if self.sky.is_nighttime() else (255, 255, 150)

        label = self.font.render(f'{time_str}  {period}', True, color)
        self.display_surface.blit(label, (x, y))

    def _draw_sunlight_warning(self, dt):
        if not self.player.taking_sun_damage:
            return
        self._warning_timer += dt * 8
        # Flash by toggling visibility with a sine-like pattern
        if int(self._warning_timer) % 2 == 0:
            x, y = SUNLIGHT_WARNING_POS
            label = self.font_large.render('SUNLIGHT!', True, (255, 60, 60))
            rect = label.get_rect(center=(x, y))
            self.display_surface.blit(label, rect)

    def _draw_portrait_overlay(self):
        if not self.player.inspecting_portrait:
            return
        # Semi-transparent dark backdrop
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.display_surface.blit(overlay, (0, 0))

        # Portrait (scaled to fit)
        portrait = self.elisabeta_portrait
        max_w = int(SCREEN_WIDTH * 0.6)
        max_h = int(SCREEN_HEIGHT * 0.75)
        scale = min(max_w / portrait.get_width(), max_h / portrait.get_height(), 1.0)
        if scale != 1.0:
            portrait = pygame.transform.smoothscale(
                portrait,
                (int(portrait.get_width() * scale), int(portrait.get_height() * scale)),
            )

        portrait_rect = portrait.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        # subtle frame
        frame_rect = portrait_rect.inflate(10, 10)
        pygame.draw.rect(self.display_surface, (220, 200, 180), frame_rect, border_radius=6)
        pygame.draw.rect(self.display_surface, (60, 50, 40), frame_rect, 2, border_radius=6)
        self.display_surface.blit(portrait, portrait_rect)

        # Dismiss hint
        hint = self.font_small.render('Press P to close', True, (150, 150, 150))
        hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, min(SCREEN_HEIGHT - 40, portrait_rect.bottom + 30)))
        self.display_surface.blit(hint, hint_rect)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------
    def display(self, dt=0):
        self._draw_blood_bar()
        self._draw_form_indicator()
        self._draw_time_indicator()
        self._draw_sunlight_warning(dt)
        self._draw_portrait_overlay()
