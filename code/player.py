"""
Dracula — the player-controlled entity.

Extends the original Player with:
- Three forms (Human / Bat / Werewolf) with distinct movement & abilities
- Blood resource system (via BloodSystem component)
- Predation intent (processed by Level)
- Coffin / sleep mechanic
- Elisabeta portrait as an inspectable inventory item
- Form-based visual tinting of shared character sprites

Farming tools & seeds are KEPT (graveyard / dead-body farm reuse).
"""
import os
import pygame
from settings import *
from support import import_folder, get_path
from timer import Timer
from blood import BloodSystem


def _tint_surface(surf, color):
    """Return a copy of *surf* with an RGB multiply tint applied."""
    tinted = surf.copy()
    tinted.fill(color, special_flags=pygame.BLEND_RGB_MULT)
    return tinted


class Dracula(pygame.sprite.Sprite):
    def __init__(self, pos, group, collision_sprites, tree_sprites,
                 interaction, soil_layer, toggle_shop):
        super().__init__(group)

        # ── Animation ────────────────────────────────────────────────
        self._import_assets()
        self.status = 'down'
        self.frame_index = 0
        self.image = self.form_animations[FORM_HUMAN][self.status][self.frame_index]
        self.rect = self.image.get_rect(center=pos)
        self.z = LAYERS['main']

        # ── Form / transformation ────────────────────────────────────
        self.current_form = FORM_HUMAN

        # ── Blood / health ───────────────────────────────────────────
        self.blood_system = BloodSystem()
        self.taking_sun_damage = False  # set by Level each frame

        # ── Movement ─────────────────────────────────────────────────
        self.direction = pygame.math.Vector2(0, 0)
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed = DRACULA_SPEED[FORM_HUMAN]

        # ── Collision ────────────────────────────────────────────────
        self.hitbox = self.rect.copy().inflate((-126, -70))
        self.collision_sprites = collision_sprites

        # ── Timers ───────────────────────────────────────────────────
        self.timers = {
            'tool use': Timer(350, self.use_tool),
            'tool switch': Timer(200),
            'seed use': Timer(350, self.use_seed),
            'seed switch': Timer(200),
            'transform': Timer(400),   # cooldown after transforming
            'feed': Timer(PREDATION_COOLDOWN_MS),
        }

        # ── Tools (kept for graveyard farming) ───────────────────────
        self.tools = ['hoe', 'axe', 'water']
        self.tool_index = 0
        self.selected_tool = self.tools[self.tool_index]

        # ── Seeds ────────────────────────────────────────────────────
        self.seeds = ['corn', 'tomato']
        self.seed_index = 0
        self.selected_seed = self.seeds[self.seed_index]

        # ── Inventory ────────────────────────────────────────────────
        self.item_inventory = {
            'wood': 0,
            'apple': 0,
            'corn': 0,
            'tomato': 0,
        }
        self.seed_inventory = {
            'corn': 5,
            'tomato': 5,
        }
        self.money = 200
        self.has_portrait = True  # Elisabeta portrait — always carried

        # ── Interaction ──────────────────────────────────────────────
        self.tree_sprites = tree_sprites
        self.interaction = interaction
        self.sleep = False  # True → coffin transition playing
        self.soil_layer = soil_layer
        self.toggle_shop = toggle_shop

        # ── Predation intent (consumed by Level) ─────────────────────
        self.wants_to_feed = False

        # ── Portrait inspection ──────────────────────────────────────
        self.inspecting_portrait = False

        # ── Sound ────────────────────────────────────────────────────
        watering_sound_path = get_path('../audio/water.mp3')
        self.watering = pygame.mixer.Sound(watering_sound_path)
        self.watering.set_volume(0.2)

    # ==================================================================
    # ASSET LOADING
    # ==================================================================
    def _import_assets(self):
        """Load character animations and pre-compute per-form tinted variants."""
        base_animations = {
            'up': [], 'down': [], 'left': [], 'right': [],
            'up_idle': [], 'down_idle': [], 'left_idle': [], 'right_idle': [],
            'up_hoe': [], 'down_hoe': [], 'left_hoe': [], 'right_hoe': [],
            'up_axe': [], 'down_axe': [], 'left_axe': [], 'right_axe': [],
            'up_water': [], 'down_water': [], 'left_water': [], 'right_water': [],
        }

        for animation in base_animations:
            path = get_path(f'{CHARACTER_SPRITE_PATH}/{animation}')
            base_animations[animation] = import_folder(path)

        # Build per-form animation dicts (tinted copies for non-human forms)
        self.form_animations = {FORM_HUMAN: base_animations}
        for form_key in (FORM_BAT, FORM_WEREWOLF):
            tint = FORM_TINT[form_key]
            if tint:
                self.form_animations[form_key] = {
                    key: [_tint_surface(f, tint) for f in frames]
                    for key, frames in base_animations.items()
                }
            else:
                self.form_animations[form_key] = base_animations

    # ==================================================================
    # TOOLS (kept for graveyard farming)
    # ==================================================================
    def use_tool(self):
        if self.current_form == FORM_BAT:
            return  # bats cannot use tools

        if self.selected_tool == 'hoe':
            self.soil_layer.get_hit(self.target_pos)
        if self.selected_tool == 'axe':
            for tree in self.tree_sprites.sprites():
                if tree.rect.collidepoint(self.target_pos):
                    tree.damage()
        if self.selected_tool == 'water':
            self.soil_layer.water(self.target_pos)
            self.watering.play()

    def get_target_pos(self):
        self.target_pos = self.rect.center + \
            PLAYER_TOOL_OFFSET[self.status.split('_')[0]]

    def use_seed(self):
        if self.current_form == FORM_BAT:
            return
        if self.seed_inventory[self.selected_seed] > 0:
            self.soil_layer.plant_seed(self.target_pos, self.selected_seed)
            self.seed_inventory[self.selected_seed] -= 1

    # ==================================================================
    # TRANSFORMATION
    # ==================================================================
    def transform(self, target_form):
        """Switch to *target_form* if allowed and Dracula has enough blood."""
        if target_form == self.current_form:
            return
        if self.timers['transform'].active:
            return

        # Human form is free; other forms cost blood
        if target_form != FORM_HUMAN:
            if not self.blood_system.apply_transform_cost(target_form):
                return  # not enough blood

        self.current_form = target_form
        self.speed = DRACULA_SPEED[target_form]
        self.timers['transform'].activate()

    # ==================================================================
    # INPUT
    # ==================================================================
    def input(self):
        keys = pygame.key.get_pressed()

        if not self.timers['tool use'].active and not self.sleep:
            # ── Movement ─────────────────────────────────────────────
            if keys[pygame.K_UP]:
                self.direction.y = -1
                self.status = 'up'
            elif keys[pygame.K_DOWN]:
                self.direction.y = 1
                self.status = 'down'
            else:
                self.direction.y = 0

            if keys[pygame.K_RIGHT]:
                self.direction.x = 1
                self.status = 'right'
            elif keys[pygame.K_LEFT]:
                self.direction.x = -1
                self.status = 'left'
            else:
                self.direction.x = 0

            # ── Tool use (blocked in bat form) ───────────────────────
            if keys[pygame.K_SPACE] and self.current_form != FORM_BAT:
                self.timers['tool use'].activate()
                self.direction = pygame.math.Vector2()
                self.frame_index = 0

            # ── Tool switch ──────────────────────────────────────────
            if keys[pygame.K_q] and not self.timers['tool switch'].active:
                self.timers['tool switch'].activate()
                self.tool_index = (self.tool_index + 1) % len(self.tools)
                self.selected_tool = self.tools[self.tool_index]

            # ── Seed use (blocked in bat form) ───────────────────────
            if keys[pygame.K_LCTRL] and self.current_form != FORM_BAT:
                self.timers['seed use'].activate()
                self.direction = pygame.math.Vector2()
                self.frame_index = 0

            # ── Seed switch ──────────────────────────────────────────
            if keys[pygame.K_e] and not self.timers['seed switch'].active:
                self.timers['seed switch'].activate()
                self.seed_index = (self.seed_index + 1) % len(self.seeds)
                self.selected_seed = self.seeds[self.seed_index]

            # ── Interaction (coffin / trader) ────────────────────────
            if keys[pygame.K_RETURN]:
                collided = pygame.sprite.spritecollide(
                    self, self.interaction, False)
                if collided:
                    name = collided[0].name
                    if name == 'Trader':
                        self.toggle_shop()
                    elif name in ('Bed', 'Coffin'):
                        self.status = 'left_idle'
                        self.sleep = True

            # ── Form transformations ─────────────────────────────────
            if keys[pygame.K_h]:
                self.transform(FORM_HUMAN)
            if keys[pygame.K_b]:
                self.transform(FORM_BAT)
            if keys[pygame.K_w]:
                self.transform(FORM_WEREWOLF)

            # ── Predation ────────────────────────────────────────────
            if keys[pygame.K_f] and self.current_form != FORM_BAT:
                if not self.timers['feed'].active:
                    self.wants_to_feed = True
                    self.timers['feed'].activate()

            # ── Elisabeta portrait ───────────────────────────────────
            if keys[pygame.K_p]:
                self.inspecting_portrait = not self.inspecting_portrait

    # ==================================================================
    # STATUS / ANIMATION
    # ==================================================================
    def get_status(self):
        if self.direction.magnitude() == 0:
            self.status = self.status.split('_')[0] + '_idle'
        if self.timers['tool use'].active:
            self.status = self.status.split('_')[0] + '_' + self.selected_tool

    def animate(self, dt):
        anims = self.form_animations[self.current_form]
        self.frame_index += 4 * dt
        frames = anims.get(self.status, [])
        if frames:
            if self.frame_index >= len(frames):
                self.frame_index = 0
            self.image = frames[int(self.frame_index)]

    # ==================================================================
    # MOVEMENT & COLLISION
    # ==================================================================
    def collision(self, direction):
        # Bat form bypasses ground obstacles
        if self.current_form == FORM_BAT:
            return

        for sprite in self.collision_sprites.sprites():
            if hasattr(sprite, 'hitbox'):
                if sprite.hitbox.colliderect(self.hitbox):
                    if direction == 'horizontal':
                        if self.direction.x > 0:
                            self.hitbox.right = sprite.hitbox.left
                        if self.direction.x < 0:
                            self.hitbox.left = sprite.hitbox.right
                        self.rect.centerx = self.hitbox.centerx
                        self.pos.x = self.hitbox.centerx
                    if direction == 'vertical':
                        if self.direction.y > 0:
                            self.hitbox.bottom = sprite.hitbox.top
                        if self.direction.y < 0:
                            self.hitbox.top = sprite.hitbox.bottom
                        self.rect.centery = self.hitbox.centery
                        self.pos.y = self.hitbox.centery

    def move(self, dt):
        if self.direction.magnitude() > 0:
            self.direction = self.direction.normalize()

        # horizontal
        self.pos.x += self.direction.x * self.speed * dt
        self.hitbox.centerx = round(self.pos.x)
        self.rect.centerx = self.hitbox.centerx
        self.collision('horizontal')

        # vertical
        self.pos.y += self.direction.y * self.speed * dt
        self.hitbox.centery = round(self.pos.y)
        self.rect.centery = round(self.pos.y)
        self.collision('vertical')

    # ==================================================================
    # TIMERS
    # ==================================================================
    def update_timers(self):
        for timer in self.timers.values():
            timer.update()

    # ==================================================================
    # MAIN UPDATE
    # ==================================================================
    def update(self, dt):
        self.input()
        self.get_status()
        self.update_timers()
        self.get_target_pos()
        self.move(dt)
        self.animate(dt)
