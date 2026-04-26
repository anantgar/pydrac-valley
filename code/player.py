"""
Dracula — the player-controlled entity.

Extends the original Player with:
- Three forms (Human / Bat / Werewolf) with distinct movement & abilities
- Blood resource system (via BloodSystem component)
- Predation intent (processed by Level)
- Coffin / sleep mechanic
- Elisabeta portrait as an inspectable inventory item
- Form-based visual tinting of shared character sprites
"""
import pygame
from settings import *
from support import get_path
from timer import Timer
from blood import BloodSystem


class Dracula(pygame.sprite.Sprite):
    def __init__(self, pos, group, collision_sprites, interaction):
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
            'transform': Timer(400),   # cooldown after transforming
            'feed': Timer(PREDATION_COOLDOWN_MS),
        }

        # ── Inventory ────────────────────────────────────────────────
        self.item_inventory = {}
        self.money = 200
        self.has_portrait = True  # Elisabeta portrait — always carried

        # ── Interaction ──────────────────────────────────────────────
        self.interaction = interaction
        self.sleep = False  # True → coffin transition playing

        # ── Predation intent (consumed by Level) ─────────────────────
        self.wants_to_feed = False

        # ── Portrait inspection ──────────────────────────────────────
        self.inspecting_portrait = False
        self._p_was_down = False

    # ==================================================================
    # ASSET LOADING
    # ==================================================================
    def _import_assets(self):
        """Load directional human sprites and single-image transformed forms."""
        def load_sprite(filename):
            path = get_path(f'{CHARACTER_SPRITE_PATH}/{filename}')
            return pygame.image.load(path).convert_alpha()

        human_directional = {
            'up': load_sprite('north.png'),
            'down': load_sprite('south.png'),
            'left': load_sprite('west.png'),
            'right': load_sprite('east.png'),
        }
        bat_sprite = load_sprite('bat.png')
        werewolf_sprite = load_sprite('werewolf.png')

        # Keep movement and idle states mapped to the shared directional sprites.
        all_statuses = [
            'up', 'down', 'left', 'right',
            'up_idle', 'down_idle', 'left_idle', 'right_idle',
        ]

        human_animations = {}
        bat_animations = {}
        werewolf_animations = {}
        for status in all_statuses:
            direction = status.split('_')[0]
            human_animations[status] = [human_directional[direction]]
            bat_animations[status] = [bat_sprite]
            werewolf_animations[status] = [werewolf_sprite]

        self.form_animations = {
            FORM_HUMAN: human_animations,
            FORM_BAT: bat_animations,
            FORM_WEREWOLF: werewolf_animations,
        }

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

        if not self.sleep:
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

            # ── Interaction (coffin) ─────────────────────────────────
            if keys[pygame.K_RETURN]:
                collided = pygame.sprite.spritecollide(
                    self, self.interaction, False)
                if collided:
                    name = collided[0].name
                    if name in ('Bed', 'Coffin'):
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
            p_down = keys[pygame.K_p]
            if p_down and not self._p_was_down:
                self.inspecting_portrait = not self.inspecting_portrait
            self._p_was_down = p_down

    # ==================================================================
    # STATUS / ANIMATION
    # ==================================================================
    def get_status(self):
        if self.direction.magnitude() == 0:
            self.status = self.status.split('_')[0] + '_idle'

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
        self.move(dt)
        self.animate(dt)
