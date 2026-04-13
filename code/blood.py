"""
Blood / health resource system for Dracula.

Designed as a standalone component owned by the Dracula player entity.
All tuning values come from settings.py so the system is data-driven.
"""
from settings import (
    MAX_BLOOD,
    BLOOD_DRAIN_TRANSFORM,
    BLOOD_DRAIN_SUNLIGHT_PER_SEC,
    BLOOD_GAIN_FEEDING,
)


class BloodSystem:
    """Manages Dracula's blood resource (acts as both health and mana)."""

    def __init__(self, initial_blood=None):
        self.max_blood = MAX_BLOOD
        self.blood = initial_blood if initial_blood is not None else self.max_blood

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @property
    def ratio(self):
        """Return blood as a 0-1 fraction (useful for HUD bars)."""
        return self.blood / self.max_blood if self.max_blood > 0 else 0.0

    def is_empty(self):
        """True when Dracula has no blood left."""
        return self.blood <= 0

    # ------------------------------------------------------------------
    # Modifiers
    # ------------------------------------------------------------------
    def drain(self, amount):
        """Remove *amount* blood, clamped to 0."""
        self.blood = max(0.0, self.blood - amount)

    def gain(self, amount):
        """Add *amount* blood, clamped to max."""
        self.blood = min(self.max_blood, self.blood + amount)

    def apply_sunlight_damage(self, dt):
        """Called each frame when Dracula is exposed to sunlight."""
        self.drain(BLOOD_DRAIN_SUNLIGHT_PER_SEC * dt)

    def apply_transform_cost(self, target_form):
        """Deduct the blood cost to transform into *target_form*.

        Always succeeds — if Dracula doesn't have enough blood the
        remaining amount is drained to zero (which may trigger death).
        Returns True so the caller can proceed with the transformation.
        """
        cost = BLOOD_DRAIN_TRANSFORM.get(target_form, 0.0)
        self.drain(cost)
        return True

    def apply_feeding(self):
        """Gain blood from successfully preying on a victim."""
        self.gain(BLOOD_GAIN_FEEDING)
