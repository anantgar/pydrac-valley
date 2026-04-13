"""
Sky / day-night cycle with game-time tracking.

Changes from the original:
- Tracks a floating-point game_hour (0–24) that advances each frame.
- Bidirectional sky colour: day → dusk → night → dawn → day.
- Exposes is_daytime() / is_nighttime() for the sunlight-damage system.
- Rain system unchanged.
"""
import pygame
from settings import *
from support import import_folder, get_path
from sprites import Generic
from random import randint, choice


def _lerp_color(a, b, t):
    """Linearly interpolate between two RGB tuples by factor *t* (0–1)."""
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


class Sky:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.full_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # Game-time tracking
        self.game_hour = GAME_START_HOUR  # Dracula awakens at night

    # ------------------------------------------------------------------
    # Time queries
    # ------------------------------------------------------------------
    def is_daytime(self):
        return DAY_START_HOUR <= self.game_hour < DAY_END_HOUR

    def is_nighttime(self):
        return not self.is_daytime()

    def get_hour_minute_string(self):
        """Return a 'HH:MM' string for display."""
        h = int(self.game_hour) % 24
        m = int((self.game_hour % 1) * 60)
        return f'{h:02d}:{m:02d}'

    # ------------------------------------------------------------------
    # Sky colour based on current game hour
    # ------------------------------------------------------------------
    def _sky_color(self):
        h = self.game_hour % 24

        if DAWN_START <= h < DAWN_END:
            t = (h - DAWN_START) / (DAWN_END - DAWN_START)
            return _lerp_color(SKY_NIGHT_COLOR, SKY_DAY_COLOR, t)

        if DAWN_END <= h < DUSK_START:
            return SKY_DAY_COLOR

        if DUSK_START <= h < DUSK_END:
            t = (h - DUSK_START) / (DUSK_END - DUSK_START)
            return _lerp_color(SKY_DAY_COLOR, SKY_NIGHT_COLOR, t)

        # Night
        return SKY_NIGHT_COLOR

    # ------------------------------------------------------------------
    # Reset (called when Dracula sleeps in coffin → skip to next night)
    # ------------------------------------------------------------------
    def reset_to_night(self):
        self.game_hour = GAME_START_HOUR

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------
    def display(self, dt):
        # Advance game clock
        self.game_hour += GAME_HOURS_PER_SECOND * dt
        if self.game_hour >= 24.0:
            self.game_hour -= 24.0

        color = self._sky_color()
        self.full_surf.fill(color)
        self.display_surface.blit(
            self.full_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)


# ─── Rain (unchanged) ────────────────────────────────────────────────────────

class Drop(Generic):
    def __init__(self, surf, pos, moving, groups, z):
        super().__init__(pos, surf, groups, z)
        self.lifetime = randint(400, 500)
        self.start_time = pygame.time.get_ticks()

        self.moving = moving
        if self.moving:
            self.pos = pygame.math.Vector2(self.rect.topleft)
            self.direction = pygame.math.Vector2(-2, 4)
            self.speed = randint(200, 250)

    def update(self, dt):
        if self.moving:
            self.pos += self.direction * self.speed * dt
            self.rect.topleft = (round(self.pos.x), round(self.pos.y))
        if pygame.time.get_ticks() - self.start_time >= self.lifetime:
            self.kill()


class Rain:
    def __init__(self, all_sprites):
        self.all_sprites = all_sprites

        drops_path = get_path('../graphics/rain/drops')
        self.rain_drops = import_folder(drops_path)

        floor_path = get_path('../graphics/rain/floor')
        self.rain_floor = import_folder(floor_path)

        ground_path = get_path('../graphics/world/ground.png')
        self.floor_w, self.floor_h = pygame.image.load(ground_path).get_size()

    def create_floor(self):
        Drop(
            surf=choice(self.rain_floor),
            pos=(randint(0, self.floor_w), randint(0, self.floor_h)),
            moving=False, groups=self.all_sprites, z=LAYERS['rain floor'])

    def create_drops(self):
        Drop(
            surf=choice(self.rain_drops),
            pos=(randint(0, self.floor_w), randint(0, self.floor_h)),
            moving=True, groups=self.all_sprites, z=LAYERS['rain drops'])

    def update(self):
        self.create_floor()
        self.create_drops()
