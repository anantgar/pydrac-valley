"""
World / region system.

Divides the single large game map into named rectangular regions used for:
- Sunlight exposure checks (indoor vs outdoor, safe vs unsafe)
- NPC zone constraints
- Location identification (castle, London, asylum, Budapest, etc.)

All region coordinates are defined in settings.py and are easily tunable.
"""
import pygame
from settings import WORLD_REGIONS, SAFE_REGIONS, INDOOR_REGIONS


class Region:
    """A named rectangular area of the world map."""

    def __init__(self, name, bounds_tuple):
        """
        Args:
            name:  region key (e.g. 'castle_interior')
            bounds_tuple: (x, y, width, height) in pixels
        """
        self.name = name
        x, y, w, h = bounds_tuple
        self.rect = pygame.Rect(x, y, w, h)
        self.is_indoor = name in INDOOR_REGIONS
        self.is_safe = name in SAFE_REGIONS

    def contains(self, pos):
        """Return True if pixel position *pos* is inside this region."""
        return self.rect.collidepoint(pos)


class WorldManager:
    """Provides spatial queries over the set of world regions."""

    def __init__(self):
        self.regions = {}
        for name, bounds in WORLD_REGIONS.items():
            self.regions[name] = Region(name, bounds)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get_region_at(self, pos):
        """Return the *most specific* Region containing *pos*, or None.

        Smaller regions (sub-rooms) are checked first so that e.g.
        'lucy_bedroom' wins over 'lucy_house'.
        """
        # Sort by area ascending so the smallest matching region wins.
        for region in sorted(self.regions.values(), key=lambda r: r.rect.width * r.rect.height):
            if region.contains(pos):
                return region
        return None

    def get_region_rect(self, name):
        """Return the pygame.Rect for a named region, or None."""
        region = self.regions.get(name)
        return region.rect if region else None

    def is_indoors(self, pos):
        """True if *pos* is inside any indoor region."""
        region = self.get_region_at(pos)
        return region is not None and region.is_indoor

    def is_outdoors(self, pos):
        """True if *pos* is NOT inside any indoor region."""
        return not self.is_indoors(pos)

    def is_safe_for_dracula(self, pos):
        """True if *pos* is inside a region marked safe (e.g. castle interior)."""
        region = self.get_region_at(pos)
        return region is not None and region.is_safe

    def is_castle_interior(self, pos):
        castle = self.regions.get('castle_interior')
        return castle is not None and castle.contains(pos)
