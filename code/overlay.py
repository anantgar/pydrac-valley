"""
Dracula HUD overlay.

Displays:
- Blood bar (top-left)
- Current form indicator (below blood bar)
- Time-of-day display (top-right)
- Sunlight warning (flashing red text when taking damage)
- Elisabeta portrait text overlay (centered, toggled with P)
- Current tool / seed icons (bottom — kept for graveyard farming)
"""
import os
import pygame
from settings import *


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

        # Tool / seed overlays (kept for farming)
        overlay_dir = os.path.join(os.path.dirname(__file__), '../graphics/overlay/')
        self.tools_surf = {}
        for tool in player.tools:
            path = f'{overlay_dir}{tool}.png'
            if os.path.exists(path):
                self.tools_surf[tool] = pygame.image.load(path).convert_alpha()
        self.seeds_surf = {}
        for seed in player.seeds:
            path = f'{overlay_dir}{seed}.png'
            if os.path.exists(path):
                self.seeds_surf[seed] = pygame.image.load(path).convert_alpha()

        # Sunlight warning flash timer
        self._warning_timer = 0.0

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

        # Title
        title = self.font_large.render('Portrait of Elisabeta', True, (220, 180, 120))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60))
        self.display_surface.blit(title, title_rect)

        # Description lines
        for i, line in enumerate(ELISABETA_PORTRAIT_TEXT.split('\n')):
            line_surf = self.font.render(line.strip(), True, (200, 200, 200))
            line_rect = line_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + i * 30))
            self.display_surface.blit(line_surf, line_rect)

        # Dismiss hint
        hint = self.font_small.render('Press P to close', True, (150, 150, 150))
        hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
        self.display_surface.blit(hint, hint_rect)

    def _draw_tool_seed(self):
        """Bottom HUD — current tool and seed (kept for farming)."""
        if self.player.selected_tool in self.tools_surf:
            tool_surf = self.tools_surf[self.player.selected_tool]
            tool_rect = tool_surf.get_rect(midbottom=OVERLAY_POSITIONS['tool'])
            self.display_surface.blit(tool_surf, tool_rect)

        if self.player.selected_seed in self.seeds_surf:
            seed_surf = self.seeds_surf[self.player.selected_seed]
            seed_rect = seed_surf.get_rect(midbottom=OVERLAY_POSITIONS['seed'])
            self.display_surface.blit(seed_surf, seed_rect)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------
    def display(self, dt=0):
        self._draw_blood_bar()
        self._draw_form_indicator()
        self._draw_time_indicator()
        self._draw_sunlight_warning(dt)
        self._draw_tool_seed()
        self._draw_portrait_overlay()
