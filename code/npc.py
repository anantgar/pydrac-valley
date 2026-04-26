"""
NPC AI system — lightweight finite-state / schedule-driven NPCs.

Each NPC has:
- A state (sleeping, patrolling, pacing, idle, stationary, watching)
- Zone bounds they cannot leave
- Waypoints for patrol/pace movement or random wandering
- Simple animation using named character sprites

Named subclasses encode behaviour from the Dracula novel:
- Lucy: always sleeping in her bedroom
- Mina: sleeping in her own bedroom
- Guardian (Arthur, Van Helsing, Quincey): frantic movement inside Lucy's house
- Renfield: wandering randomly in his asylum cell
- Seward: pacing beside Renfield's asylum cell
- JonathanHarker: stationary at the Budapest convent
"""
import os
from random import randint

import pygame
from settings import *
from support import import_folder, get_path

# ─── NPC States ──────────────────────────────────────────────────────────────
NPC_SLEEPING = 'sleeping'
NPC_PATROLLING = 'patrolling'
NPC_PACING = 'pacing'
NPC_IDLE = 'idle'
NPC_STATIONARY = 'stationary'
NPC_WATCHING = 'watching'
NPC_VAMPIRIZED = 'vampirized'
NPC_WANDERING = 'wandering'

# Tint applied to NPC sprites when turned into a vampire
_VAMPIRE_TINT = (255, 100, 100)

_NPC_CHARACTER_FOLDERS = {
    'lucy': 'Lucy',
    'mina': 'Mina',
    'arthur': 'Young_Man',
    'van helsing': 'Van_Helsing',
    'quincey': 'Young_Man',
    'renfield': 'Renfield',
    'seward': 'Young_Man',
    'jonathan harker': 'Jonathan_Harker',
}

_ROTATION_FILENAMES = {
    'up': 'north.png',
    'down': 'south.png',
    'left': 'west.png',
    'right': 'east.png',
}


# ─── Base NPC ────────────────────────────────────────────────────────────────
class NPC(pygame.sprite.Sprite):
    """Base NPC with zone-constrained waypoint movement."""

    def __init__(self, name, pos, groups, zone_rect=None, waypoints=None,
                 speed=100, initial_state=NPC_IDLE, can_be_preyed_on=True,
                 collision_sprites=None):
        super().__init__(groups)

        self.name = name
        self.state = initial_state
        self.speed = speed
        self.can_be_preyed_on = can_be_preyed_on
        self.turned_vampire = False

        # Defaults used for reset-on-player-death
        self._initial_state = initial_state
        self._initial_can_be_preyed_on = can_be_preyed_on

        # Position & movement
        self.pos = pygame.math.Vector2(pos)
        self.direction = pygame.math.Vector2(0, 0)
        self.facing = 'down'

        # Zone constraint (NPC stays within this rect)
        self.zone_rect = zone_rect

        # Collision sprites (walls, fences, water, etc.)
        self.collision_sprites = collision_sprites

        # Waypoints
        self.waypoints = waypoints or [pos]
        self.current_waypoint = 0
        self.waypoint_threshold = 8  # pixels — "close enough" to a waypoint
        self._pacing_forward = True  # for ping-pong movement

        # Animation
        self._import_assets()
        # Keep pristine (human) animations so vampirism can be reverted.
        # Frames are treated as immutable; we only swap references.
        self._base_animations = {k: list(v) for k, v in self.animations.items()}
        self.frame_index = 0
        self.status = 'down_idle'
        anim = self.animations.get(self.status, [])
        self.image = anim[0] if anim else pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.rect = self.image.get_rect(center=pos)
        self.z = LAYERS['main']
        self.hitbox = self.rect.copy().inflate(-126, -70)

        # Spawn snapshot (position + movement intent)
        self._spawn_pos = pygame.math.Vector2(pos)
        self._spawn_facing = self.facing
        self._spawn_waypoints = list(self.waypoints)
        self._spawn_current_waypoint = self.current_waypoint
        self._spawn_pacing_forward = self._pacing_forward

    # ------------------------------------------------------------------
    # Asset loading
    # ------------------------------------------------------------------
    def _import_assets(self):
        """Load walking + idle animations for this named character."""
        self.animations = {}
        character_folder = self._character_sprite_folder()
        if character_folder and self._import_character_rotations(character_folder):
            return

        for anim_key in ('up', 'down', 'left', 'right',
                         'up_idle', 'down_idle', 'left_idle', 'right_idle'):
            path = get_path(f'{CHARACTER_SPRITE_PATH}/{anim_key}')
            self.animations[anim_key] = import_folder(path)

    def _character_sprite_folder(self):
        normalized_name = self.name.lower().replace('_', ' ').strip()
        return _NPC_CHARACTER_FOLDERS.get(normalized_name)

    def _import_character_rotations(self, character_folder):
        character_path = get_path(f'{CHARACTER_SPRITE_PATH}/{character_folder}')
        rotations_path = os.path.join(character_path, 'rotations')
        sprite_path = rotations_path if os.path.isdir(rotations_path) else character_path

        directional_frames = {}
        for direction, filename in _ROTATION_FILENAMES.items():
            image_path = os.path.join(sprite_path, filename)
            if not os.path.exists(image_path):
                self.animations = {}
                return False
            directional_frames[direction] = [
                pygame.image.load(image_path).convert_alpha()
            ]

        for anim_key in ('up', 'down', 'left', 'right',
                         'up_idle', 'down_idle', 'left_idle', 'right_idle'):
            direction = anim_key.split('_')[0]
            self.animations[anim_key] = directional_frames[direction]
        return True

    # ------------------------------------------------------------------
    # Vampire transformation
    # ------------------------------------------------------------------
    def turn_vampire(self):
        """Turn this NPC into a vampire — tint sprites red and disable predation."""
        if self.turned_vampire:
            return
        self.turned_vampire = True
        self.can_be_preyed_on = False

        # Tint every animation frame with a reddish hue
        for key, frames in self.animations.items():
            self.animations[key] = [self._tint(f) for f in frames]

        # Refresh current image immediately
        frames = self.animations.get(self.status, [])
        if frames:
            idx = int(self.frame_index) % len(frames)
            self.image = frames[idx]

    def reset_state(self):
        """Restore NPC to its initial (human) state and spawn behaviour."""
        # Restore behaviour/state
        self.state = self._initial_state
        self.can_be_preyed_on = self._initial_can_be_preyed_on

        # Restore vampire transformation
        self.turned_vampire = False
        self.animations = {k: list(v) for k, v in self._base_animations.items()}

        # Restore movement/position snapshot
        self.pos = self._spawn_pos.copy()
        self.direction.update(0, 0)
        self.facing = self._spawn_facing
        self.waypoints = list(self._spawn_waypoints)
        self.current_waypoint = self._spawn_current_waypoint
        self._pacing_forward = self._spawn_pacing_forward

        # If this NPC is a wanderer, re-roll a wander target inside its zone.
        if self.state == NPC_WANDERING:
            self._choose_random_waypoint()

        # Refresh rect/hitbox/image based on restored animation state
        self._update_status()
        frames = self.animations.get(self.status, [])
        if frames:
            self.frame_index = 0
            self.image = frames[0]
            center = (round(self.pos.x), round(self.pos.y))
            self.rect = self.image.get_rect(center=center)
            self.hitbox.center = self.rect.center

    @staticmethod
    def _tint(surf):
        """Return a copy of *surf* with the vampire-red tint applied."""
        tinted = surf.copy()
        tinted.fill(_VAMPIRE_TINT, special_flags=pygame.BLEND_RGB_MULT)
        return tinted

    # ------------------------------------------------------------------
    # Movement helpers
    # ------------------------------------------------------------------
    def _target_waypoint(self):
        if not self.waypoints:
            return self.pos
        return pygame.math.Vector2(self.waypoints[self.current_waypoint])

    def _advance_waypoint_cycle(self):
        """Advance to the next waypoint, wrapping around."""
        self.current_waypoint = (self.current_waypoint + 1) % len(self.waypoints)

    def _advance_waypoint_pingpong(self):
        """Advance waypoint in a back-and-forth pattern."""
        if len(self.waypoints) < 2:
            return
        if self._pacing_forward:
            self.current_waypoint += 1
            if self.current_waypoint >= len(self.waypoints):
                self.current_waypoint = len(self.waypoints) - 2
                self._pacing_forward = False
        else:
            self.current_waypoint -= 1
            if self.current_waypoint < 0:
                self.current_waypoint = 1
                self._pacing_forward = True

    def _choose_random_waypoint(self):
        """Pick a random point inside this NPC's zone."""
        if not self.zone_rect:
            return

        margin = TILE_SIZE // 2
        min_x = self.zone_rect.left + margin
        max_x = self.zone_rect.right - margin
        min_y = self.zone_rect.top + margin
        max_y = self.zone_rect.bottom - margin

        if min_x > max_x or min_y > max_y:
            target = self.zone_rect.center
        else:
            target = (randint(min_x, max_x), randint(min_y, max_y))

        self.waypoints = [target]
        self.current_waypoint = 0

    def _check_collision(self, direction):
        """Resolve collisions with world obstacles (walls, fences, etc.)."""
        if not self.collision_sprites:
            return
        for sprite in self.collision_sprites.sprites():
            if sprite is self or isinstance(sprite, NPC):
                continue
            if hasattr(sprite, 'hitbox'):
                if sprite.hitbox.colliderect(self.hitbox):
                    if direction == 'horizontal':
                        if self.direction.x > 0:
                            self.hitbox.right = sprite.hitbox.left
                        elif self.direction.x < 0:
                            self.hitbox.left = sprite.hitbox.right
                        self.pos.x = self.hitbox.centerx
                    elif direction == 'vertical':
                        if self.direction.y > 0:
                            self.hitbox.bottom = sprite.hitbox.top
                        elif self.direction.y < 0:
                            self.hitbox.top = sprite.hitbox.bottom
                        self.pos.y = self.hitbox.centery

    def _move_toward_waypoint(self, dt):
        target = self._target_waypoint()
        diff = target - self.pos
        dist = diff.magnitude()

        if dist < self.waypoint_threshold:
            if self.state == NPC_WANDERING:
                self._choose_random_waypoint()
            elif self.state == NPC_PACING:
                self._advance_waypoint_pingpong()
            else:
                self._advance_waypoint_cycle()
            self.direction = pygame.math.Vector2(0, 0)
            return

        self.direction = diff.normalize()

        # Update facing direction
        if abs(self.direction.x) > abs(self.direction.y):
            self.facing = 'right' if self.direction.x > 0 else 'left'
        else:
            self.facing = 'down' if self.direction.y > 0 else 'up'

        # Move with per-axis collision resolution
        # Horizontal
        self.pos.x += self.direction.x * self.speed * dt
        self.hitbox.centerx = round(self.pos.x)
        self.rect.centerx = self.hitbox.centerx
        self._check_collision('horizontal')

        # Vertical
        self.pos.y += self.direction.y * self.speed * dt
        self.hitbox.centery = round(self.pos.y)
        self.rect.centery = self.hitbox.centery
        self._check_collision('vertical')

        # Constrain to zone
        if self.zone_rect:
            self.pos.x = max(self.zone_rect.left,
                             min(self.pos.x, self.zone_rect.right))
            self.pos.y = max(self.zone_rect.top,
                             min(self.pos.y, self.zone_rect.bottom))

        self.rect.center = (round(self.pos.x), round(self.pos.y))
        self.hitbox.center = self.rect.center

    # ------------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------------
    def _update_status(self):
        if self.state in (NPC_SLEEPING, NPC_IDLE, NPC_STATIONARY):
            self.status = f'{self.facing}_idle'
        elif self.direction.magnitude() > 0:
            self.status = self.facing
        else:
            self.status = f'{self.facing}_idle'

    def _animate(self, dt):
        self.frame_index += 4 * dt
        frames = self.animations.get(self.status, [])
        if frames:
            if self.frame_index >= len(frames):
                self.frame_index = 0
            self.image = frames[int(self.frame_index)]

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------
    def update(self, dt):
        if self.state in (NPC_PATROLLING, NPC_PACING, NPC_WATCHING, NPC_WANDERING):
            self._move_toward_waypoint(dt)
        else:
            self.direction = pygame.math.Vector2(0, 0)

        self._update_status()
        self._animate(dt)


# ─── Named NPC Sub-classes ───────────────────────────────────────────────────

class Lucy(NPC):
    """Lucy Westenra — sleeps in her large bed constantly."""
    def __init__(self, groups, collision_sprites=None):
        zone = pygame.Rect(*WORLD_REGIONS['lucy_bedroom'])
        super().__init__(
            name='Lucy',
            pos=NPC_POSITIONS['lucy'],
            groups=groups,
            zone_rect=zone,
            initial_state=NPC_SLEEPING,
            can_be_preyed_on=True,
            collision_sprites=collision_sprites,
        )


class Mina(NPC):
    """Mina Murray — sleeps in a separate bedroom."""
    def __init__(self, groups, collision_sprites=None):
        zone = pygame.Rect(*WORLD_REGIONS['mina_bedroom'])
        super().__init__(
            name='Mina',
            pos=NPC_POSITIONS['mina'],
            groups=groups,
            zone_rect=zone,
            initial_state=NPC_SLEEPING,
            can_be_preyed_on=True,
            collision_sprites=collision_sprites,
        )


class Guardian(NPC):
    """One of the three guardians frantically moving through Lucy's house."""
    _all_guardians = []
    _watch_index = 0
    _rotation_timer = 0.0

    @classmethod
    def reset_rotation(cls):
        """Call once during Level setup before creating Guardians."""
        cls._all_guardians = []
        cls._watch_index = 0
        cls._rotation_timer = 0.0

    @classmethod
    def update_rotation(cls, dt):
        """Kept for Level's existing update call; guardians now all wander."""
        return

    def __init__(self, name, groups, collision_sprites=None):
        zone = pygame.Rect(*WORLD_REGIONS['lucy_house_inner'])
        self._sleep_pos = GUARDIAN_SLEEP_POSITIONS[name.lower().replace(' ', '_')]

        super().__init__(
            name=name,
            pos=self._sleep_pos,
            groups=groups,
            zone_rect=zone,
            speed=NPC_FRANTIC_SPEED,
            initial_state=NPC_WANDERING,
            can_be_preyed_on=True,
            collision_sprites=None,
        )
        self.waypoint_threshold = 18
        Guardian._all_guardians.append(self)
        self._choose_random_waypoint()

    def _sync_watch_state(self):
        """Keep compatibility with older rotation code paths."""
        self.state = NPC_WANDERING
        self._choose_random_waypoint()

    def _is_on_watch(self):
        try:
            idx = Guardian._all_guardians.index(self)
        except ValueError:
            return False
        return idx == Guardian._watch_index


class Renfield(NPC):
    """Renfield — trapped in an asylum cell, wandering unpredictably."""
    def __init__(self, groups, collision_sprites=None):
        zone = pygame.Rect(*WORLD_REGIONS['asylum_cell'])
        super().__init__(
            name='Renfield',
            pos=NPC_POSITIONS['renfield'],
            groups=groups,
            zone_rect=zone,
            speed=NPC_PACE_SPEED,
            initial_state=NPC_WANDERING,
            can_be_preyed_on=False,  # locked in cell
            collision_sprites=collision_sprites,
        )
        self._choose_random_waypoint()


class Seward(NPC):
    """Dr. Seward — paces in a straight line beside Renfield's cell."""
    def __init__(self, groups, collision_sprites=None):
        zone = pygame.Rect(*WORLD_REGIONS['asylum_halls'])
        super().__init__(
            name='Seward',
            pos=NPC_POSITIONS['seward'],
            groups=groups,
            zone_rect=zone,
            waypoints=SEWARD_WAYPOINTS,
            speed=NPC_PATROL_SPEED,
            initial_state=NPC_PACING,
            can_be_preyed_on=True,
            collision_sprites=collision_sprites,
        )


class JonathanHarker(NPC):
    """Jonathan Harker — stationary at the Budapest convent."""
    def __init__(self, groups, collision_sprites=None):
        zone = pygame.Rect(*WORLD_REGIONS['budapest_convent'])
        super().__init__(
            name='Jonathan Harker',
            pos=NPC_POSITIONS['jonathan'],
            groups=groups,
            zone_rect=zone,
            initial_state=NPC_STATIONARY,
            can_be_preyed_on=True,
            collision_sprites=collision_sprites,
        )

