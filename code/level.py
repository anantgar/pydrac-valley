"""
Level — main scene manager that integrates all game systems.

The expanded world works as follows:
- The original TMX map (50x40 tiles) sits at (0,0) and represents London.
- Additional buildings (Castle, Asylum, Convent, Museum) are constructed
  programmatically using tiles from the House tileset.
- Roads (path tiles) connect the major locations.
- A much larger ground surface is generated to cover the full world.
- Water tiles from the TMX are added to collision_sprites so nobody walks on water.
- NPCs are placed inside their respective buildings.
- Certain TMX fence/collision tiles at map edges are skipped to create exit
  gaps so the player can walk to other locations.
"""
import os
import pygame
from settings import *
from support import *
from player import Dracula
from overlay import Overlay
from sprites import Generic, Water, Wildflower, Tree, Interaction, Particle
from pytmx.util_pygame import load_pygame
from transition import Transition
from soil import SoilLayer
from sky import Rain, Sky
from random import randint
from menu import Menu
from world import WorldManager
from npc import (
    Guardian, Lucy, Mina, Renfield, Seward, JonathanHarker,
)

# ── Exit gap definitions ─────────────────────────────────────────────────────
# Tile coordinates (col, row) that should NOT be made into collision/fence
# sprites so that the player can exit London and reach other locations.
# West exit: remove fence at x=6, y=17-19 (gap at road height ~y=1150)
# East exit: remove fence at x=46, y=17-19 (gap at road height)
# North exit: remove fence at x=37, y=2 and collision at x=37-38, y=5
#             to allow path to museum
_WEST_EXIT_GAP = {(6, y) for y in range(16, 21)}
_EAST_EXIT_GAP = {(46, y) for y in range(16, 21)}
_NORTH_EXIT_GAP = {(37, y) for y in range(2, 6)} | {(38, y) for y in range(2, 6)}
_EXIT_GAPS_FENCE = _WEST_EXIT_GAP | _EAST_EXIT_GAP | _NORTH_EXIT_GAP
_EXIT_GAPS_COLLISION = {
    (9, y) for y in range(16, 22)
} | {
    (x, 5) for x in range(35, 41)
} | {
    (40, y) for y in range(5, 10)
}


class Level:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()

        # sprite groups
        self.all_sprites = CameraGroup()
        self.collision_sprites = pygame.sprite.Group()
        self.tree_sprites = pygame.sprite.Group()
        self.interaction_sprites = pygame.sprite.Group()
        self.npc_sprites = pygame.sprite.Group()

        # world regions
        self.world_manager = WorldManager()

        # load tilesets for procedural building
        self._load_tilesets()

        # soil layer (kept for graveyard farming)
        self.soil_layer = SoilLayer(self.all_sprites, self.collision_sprites)

        # map + player + NPCs
        self.setup()

        # sky & weather
        self.rain = Rain(self.all_sprites)
        self.raining = randint(0, 10) > 7
        self.soil_layer.raining = self.raining
        self.sky = Sky()

        # HUD & menus
        self.overlay = Overlay(self.player, self.sky)
        self.transition = Transition(self.reset, self.player)
        self.menu = Menu(self.player, self.toggle_shop)
        self.shop_active = False

        # ── Death screen state ───────────────────────────────────────
        self.dead = False
        self._death_timer = 0.0
        self._death_alpha = 0
        _font_path = get_path(FONT_PATH)
        self._death_font = pygame.font.Font(_font_path, 48)
        self._death_font_small = pygame.font.Font(_font_path, 24)

        # sounds
        success_sound_path = get_path('../audio/success.wav')
        self.success = pygame.mixer.Sound(success_sound_path)
        self.success.set_volume(0.2)

        music_path = get_path('../audio/music.mp3')
        self.music = pygame.mixer.Sound(music_path)
        self.music.set_volume(0.1)
        self.music.play(loops=-1)

    # ==================================================================
    # TILESET LOADING
    # ==================================================================
    def _load_tilesets(self):
        """Load House and Paths tilesets for procedural building."""
        house_path = get_path(HOUSE_TILESET_PATH)
        self._house_sheet = pygame.image.load(house_path).convert_alpha()

        paths_path = get_path(PATHS_TILESET_PATH)
        self._paths_sheet = pygame.image.load(paths_path).convert_alpha()

    def _get_house_tile(self, col, row):
        """Extract a 64x64 tile from the House tileset."""
        return self._house_sheet.subsurface(col * 64, row * 64, 64, 64)

    def _get_path_tile(self, col, row):
        """Extract a 64x64 tile from the Paths tileset."""
        return self._paths_sheet.subsurface(col * 64, row * 64, 64, 64)

    # ==================================================================
    # PROCEDURAL BUILDING CONSTRUCTION
    # ==================================================================
    def _build_structure(self, bx, by, w_tiles, h_tiles, label=''):
        """Build a rectangular building at pixel position (bx, by).

        Uses the same House tileset tile arrangement as the TMX main house
        so all buildings look consistent:
        - Tile (col, row) in the 7-column House.png sheet:
          Top-left corner: (0,1)  Top edge: (1,1)  Top-right corner: (2,1)
          Left wall:       (0,2)  Floor:    (1,2)  Right wall:       (2,2)
          Bot-left corner: (0,3)  Bot edge: (1,3)  Bot-right corner: (2,3)
          Roof tiles:      (1,0) for chimney/top accent row
          Door:            (6,0) upper + open floor below
        """
        # ── Tile extraction ─────────────────────────────────────────
        # Corners
        tl_corner = self._get_house_tile(0, 1)   # top-left
        tr_corner = self._get_house_tile(2, 1)   # top-right
        bl_corner = self._get_house_tile(0, 3)   # bottom-left
        br_corner = self._get_house_tile(2, 3)   # bottom-right
        # Edges
        top_edge  = self._get_house_tile(1, 1)   # top wall segment
        bot_edge  = self._get_house_tile(1, 3)   # bottom wall segment
        left_wall = self._get_house_tile(0, 2)   # left wall
        right_wall = self._get_house_tile(2, 2)  # right wall
        # Interior
        floor_tile = self._get_house_tile(1, 2)  # floor / interior
        # Roof accent (placed one row above the top wall)
        roof_tile  = self._get_house_tile(1, 0)
        # Door opening
        door_top   = self._get_house_tile(6, 0)  # door lintel

        door_col = w_tiles // 2  # door in center of bottom wall

        # ── Optional roof accent row above the structure ──────────
        for tx in range(w_tiles):
            px = bx + tx * TILE_SIZE
            py = by - TILE_SIZE  # one tile above
            Generic((px, py), roof_tile,
                    self.all_sprites, LAYERS['house bottom'])

        for tx in range(w_tiles):
            for ty in range(h_tiles):
                px = bx + tx * TILE_SIZE
                py = by + ty * TILE_SIZE

                is_top    = (ty == 0)
                is_bottom = (ty == h_tiles - 1)
                is_left   = (tx == 0)
                is_right  = (tx == w_tiles - 1)
                is_door   = (is_bottom and tx == door_col)

                if is_door:
                    # Door opening — floor underneath, door lintel on top
                    Generic((px, py), floor_tile,
                            self.all_sprites, LAYERS['house bottom'])
                    Generic((px, py), door_top,
                            self.all_sprites, LAYERS['main'])
                elif is_top and is_left:
                    Generic((px, py), tl_corner,
                            [self.all_sprites, self.collision_sprites])
                elif is_top and is_right:
                    Generic((px, py), tr_corner,
                            [self.all_sprites, self.collision_sprites])
                elif is_bottom and is_left:
                    Generic((px, py), bl_corner,
                            [self.all_sprites, self.collision_sprites])
                elif is_bottom and is_right:
                    Generic((px, py), br_corner,
                            [self.all_sprites, self.collision_sprites])
                elif is_top:
                    Generic((px, py), top_edge,
                            [self.all_sprites, self.collision_sprites])
                elif is_bottom:
                    Generic((px, py), bot_edge,
                            [self.all_sprites, self.collision_sprites])
                elif is_left:
                    Generic((px, py), left_wall,
                            [self.all_sprites, self.collision_sprites])
                elif is_right:
                    Generic((px, py), right_wall,
                            [self.all_sprites, self.collision_sprites])
                else:
                    # Interior floor
                    Generic((px, py), floor_tile,
                            self.all_sprites, LAYERS['house bottom'])

    def _replicate_house_furniture(self, bx, by, bw_tiles, bh_tiles):
        """Place furniture from the TMX main house into a procedural building.

        The main house is 8×6 tiles.  For larger buildings the furniture
        layout is centred; for same-size buildings it lines up exactly.
        """
        offset_tx = max(0, (bw_tiles - 8) // 2)
        offset_ty = max(0, (bh_tiles - 6) // 2)
        for rel_tx, rel_ty, surf, z in self._house_furniture:
            px = bx + (rel_tx + offset_tx) * TILE_SIZE
            py = by + (rel_ty + offset_ty) * TILE_SIZE
            Generic((px, py), surf, self.all_sprites, z)

    def _build_roads(self):
        """Create road/path tiles connecting major locations."""
        # Use a center path tile (row 1, col 1) and edges
        path_center = self._get_path_tile(1, 1)
        path_h_edge = self._get_path_tile(1, 0)
        path_v_edge = self._get_path_tile(0, 1)

        for road in ROADS:
            sx, sy = road['start']
            ex, ey = road['end']
            width = road['width']

            if road['axis'] == 'horizontal':
                # Draw horizontal road strip
                start_tx = int(sx) // TILE_SIZE
                end_tx = int(ex) // TILE_SIZE
                base_ty = int(sy) // TILE_SIZE
                for tx in range(min(start_tx, end_tx), max(start_tx, end_tx) + 1):
                    for w in range(width):
                        px = tx * TILE_SIZE
                        py = (base_ty + w) * TILE_SIZE
                        tile = path_center if w > 0 else path_h_edge
                        Generic((px, py), tile,
                                self.all_sprites, LAYERS['ground'])
            else:
                # Draw vertical road strip
                start_ty = int(sy) // TILE_SIZE
                end_ty = int(ey) // TILE_SIZE
                base_tx = int(sx) // TILE_SIZE
                for ty in range(min(start_ty, end_ty), max(start_ty, end_ty) + 1):
                    for w in range(width):
                        px = (base_tx + w) * TILE_SIZE
                        py = ty * TILE_SIZE
                        tile = path_center if w > 0 else path_v_edge
                        Generic((px, py), tile,
                                self.all_sprites, LAYERS['ground'])

    # ==================================================================
    # EXPANDED GROUND
    # ==================================================================
    def _create_expanded_ground(self):
        """Create ground surfaces covering the full expanded world.

        The original ground.png covers the London area (0,0).
        Additional ground patches are created for areas outside that range.
        """
        # Original ground (London)
        path_floor = get_path('../graphics/world/ground.png')
        london_ground = pygame.image.load(path_floor).convert_alpha()
        Generic(
            pos=(0, 0), surf=london_ground,
            groups=self.all_sprites, z=LAYERS['ground'])

        # For expanded areas, create simple grass-colored ground patches.
        # We tile with reasonably sized surfaces to avoid one massive allocation.
        grass_color = (69, 108, 58)  # Dark green grass
        dark_grass = (50, 80, 45)    # Slightly darker variation

        # Define ground patches needed for each area
        patches = [
            # Castle / graveyard area (west)
            (-3200, 400, 1600, 2000, grass_color),
            # Road area between castle and London
            (-1600, 800, 1600, 800, dark_grass),
            # East of London (towards asylum)
            (3200, 400, 2400, 2000, grass_color),
            # Road / terrain to Budapest
            (4400, 1600, 1200, 2800, dark_grass),
            # Budapest area
            (4400, 3400, 1600, 1200, grass_color),
            # North area (museum)
            (1600, -1200, 1600, 1200, grass_color),
        ]

        for px, py, pw, ph, color in patches:
            patch_surf = pygame.Surface((pw, ph))
            patch_surf.fill(color)
            # Add some subtle texture variation
            for vx in range(0, pw, TILE_SIZE):
                for vy in range(0, ph, TILE_SIZE):
                    if (vx // TILE_SIZE + vy // TILE_SIZE) % 3 == 0:
                        r = pygame.Rect(vx, vy, TILE_SIZE, TILE_SIZE)
                        darker = (max(0, color[0] - 8),
                                  max(0, color[1] - 8),
                                  max(0, color[2] - 8))
                        patch_surf.fill(darker, r)
            Generic(pos=(px, py), surf=patch_surf,
                    groups=self.all_sprites, z=LAYERS['ground'])

    # ==================================================================
    # SETUP
    # ==================================================================
    def setup(self):
        path_map = get_path('../data/map.tmx')
        tmx_data = load_pygame(path_map)

        # ── Expanded ground (must be first for correct layer ordering) ───
        self._create_expanded_ground()

        # ── TMX house layers (Lucy's house in London) ────────────────
        # Main house occupies tiles (20,21)-(27,26) = 8×6 tiles.
        _HOUSE_TX0, _HOUSE_TY0 = 20, 21
        _HOUSE_TW, _HOUSE_TH = 8, 6

        for layer in ['HouseFloor', 'HouseFurnitureBottom']:
            for x, y, surf in tmx_data.get_layer_by_name(layer).tiles():
                Generic((x * TILE_SIZE, y * TILE_SIZE), surf,
                        self.all_sprites, LAYERS['house bottom'])

        for layer in ['HouseWalls', 'HouseFurnitureTop']:
            for x, y, surf in tmx_data.get_layer_by_name(layer).tiles():
                Generic((x * TILE_SIZE, y * TILE_SIZE), surf, self.all_sprites)

        # Capture furniture tiles for replication to other buildings
        self._house_furniture = []
        for layer_name, z in [('HouseFurnitureBottom', LAYERS['house bottom']),
                              ('HouseFurnitureTop', LAYERS['main'])]:
            for x, y, surf in tmx_data.get_layer_by_name(layer_name).tiles():
                if (_HOUSE_TX0 <= x < _HOUSE_TX0 + _HOUSE_TW and
                        _HOUSE_TY0 <= y < _HOUSE_TY0 + _HOUSE_TH):
                    self._house_furniture.append(
                        (x - _HOUSE_TX0, y - _HOUSE_TY0, surf, z))

        # ── Fence (skip tiles at exit gaps so player can leave London) ──
        for x, y, surf in tmx_data.get_layer_by_name('Fence').tiles():
            if (x, y) in _EXIT_GAPS_FENCE:
                continue  # leave gap for road exit
            Generic((x * TILE_SIZE, y * TILE_SIZE), surf,
                    [self.all_sprites, self.collision_sprites])

        # ── Water tiles — collision so nobody walks on them ─────────
        # Skip water tiles near road exit points so the paths aren’t blocked.
        _WATER_SKIP = set()  # no water directly blocks exits in the data, but keep for safety
        water_path = get_path('../graphics/water')
        water_frames = import_folder(water_path)
        for x, y, surf in tmx_data.get_layer_by_name('Water').tiles():
            if (x, y) in _WATER_SKIP:
                continue
            Water((x * TILE_SIZE, y * TILE_SIZE), water_frames,
                  [self.all_sprites, self.collision_sprites])

        # ── Trees (skip any in exit corridors) ──────────────────────
        # North exit corridor: x=2300-2550, y=0-500
        _north_corridor = pygame.Rect(2300, 0, 250, 500)
        for obj in tmx_data.get_layer_by_name('Trees'):
            if _north_corridor.collidepoint(obj.x, obj.y):
                # Place tree visually only, not as collision
                Generic((obj.x, obj.y), obj.image,
                        self.all_sprites, LAYERS['main'])
                continue
            Tree(
                pos=(obj.x, obj.y),
                surf=obj.image,
                groups=[self.all_sprites, self.collision_sprites,
                        self.tree_sprites],
                name=obj.name,
                player_add=self.player_add,
            )

        # ── Wildflowers / decoration (skip any in exit corridors) ────
        for obj in tmx_data.get_layer_by_name('Decoration'):
            if _north_corridor.collidepoint(obj.x, obj.y):
                Generic((obj.x, obj.y), obj.image,
                        self.all_sprites, LAYERS['main'])
                continue
            Wildflower((obj.x, obj.y), obj.image,
                       [self.all_sprites, self.collision_sprites])

        # ── Collision tiles (skip exit gaps) ─────────────────────────────
        for x, y, surf in tmx_data.get_layer_by_name('Collision').tiles():
            if (x, y) in _EXIT_GAPS_COLLISION:
                continue
            Generic((x * TILE_SIZE, y * TILE_SIZE),
                    pygame.Surface((TILE_SIZE, TILE_SIZE)),
                    self.collision_sprites)

        # ── Player (Dracula) — spawns inside the Castle ──────────────
        castle_bx, castle_by, castle_w, castle_h = CASTLE_BUILDING
        player_start = (
            castle_bx + (castle_w // 2) * TILE_SIZE,
            castle_by + (castle_h // 2) * TILE_SIZE,
        )
        self.player = Dracula(
            pos=player_start,
            group=self.all_sprites,
            collision_sprites=self.collision_sprites,
            tree_sprites=self.tree_sprites,
            interaction=self.interaction_sprites,
            soil_layer=self.soil_layer,
            toggle_shop=self.toggle_shop,
        )
        for obj in tmx_data.get_layer_by_name('Player'):

            if obj.name == 'Bed':
                Interaction((obj.x, obj.y), (obj.width, obj.height),
                            self.interaction_sprites, obj.name)

            if obj.name == 'Trader':
                Interaction((obj.x, obj.y), (obj.width, obj.height),
                            self.interaction_sprites, obj.name)

        # ── Build expanded world structures ──────────────────────────
        self._build_expanded_world()

        # ── NPCs ─────────────────────────────────────────────────────
        self._setup_npcs()

    def _build_expanded_world(self):
        """Construct all buildings outside the original TMX map + roads."""

        # Castle (Dracula's home)
        bx, by, w, h = CASTLE_BUILDING
        self._build_structure(bx, by, w, h, 'Castle')
        self._replicate_house_furniture(bx, by, w, h)

        # Coffin inside castle
        Interaction(COFFIN_POSITION, COFFIN_SIZE,
                    self.interaction_sprites, 'Coffin')

        # Graveyard area (just ground, reuses farmable area look)
        gx, gy, gw, gh = GRAVEYARD_AREA
        grave_surf = pygame.Surface((gw * TILE_SIZE, gh * TILE_SIZE))
        grave_surf.fill((45, 55, 40))  # Dark earthy color
        # Grave markers (simple dark rectangles)
        for i in range(gw):
            for j in range(gh):
                if (i + j) % 3 == 0:
                    marker = pygame.Rect(i * 64 + 20, j * 64 + 10, 24, 44)
                    pygame.draw.rect(grave_surf, (60, 60, 60), marker)
                    pygame.draw.rect(grave_surf, (40, 40, 40), marker, 2)
        Generic((gx, gy), grave_surf, self.all_sprites, LAYERS['ground'])

        # Asylum
        bx, by, w, h = ASYLUM_BUILDING
        self._build_structure(bx, by, w, h, 'Asylum')

        # Budapest convent
        bx, by, w, h = CONVENT_BUILDING
        self._build_structure(bx, by, w, h, 'Convent')
        self._replicate_house_furniture(bx, by, w, h)

        # Museum
        bx, by, w, h = MUSEUM_BUILDING
        self._build_structure(bx, by, w, h, 'Museum')

        # Roads connecting everything
        self._build_roads()

    def _setup_npcs(self):
        """Create all named NPCs inside their buildings."""
        groups = [self.all_sprites, self.npc_sprites]
        cs = self.collision_sprites

        Guardian.reset_rotation()

        # Lucy's house occupants (inside the TMX house)
        Lucy(groups, collision_sprites=cs)
        Mina(groups, collision_sprites=cs)
        Guardian('arthur', groups, collision_sprites=cs)
        Guardian('van_helsing', groups, collision_sprites=cs)
        Guardian('quincey', groups, collision_sprites=cs)

        # Asylum occupants
        Renfield(groups, collision_sprites=cs)
        Seward(groups, collision_sprites=cs)

        # Budapest convent
        JonathanHarker(groups, collision_sprites=cs)

    # ==================================================================
    # CALLBACKS
    # ==================================================================
    def player_add(self, item, amount=1):
        self.player.item_inventory[item] += amount
        self.success.play()

    def toggle_shop(self):
        self.shop_active = not self.shop_active

    # ==================================================================
    # GAME LOGIC (per-frame)
    # ==================================================================
    def _check_sunlight(self, dt):
        if (self.sky.is_daytime()
                and self.world_manager.is_outdoors(self.player.pos)
                and not self.world_manager.is_safe_for_dracula(self.player.pos)):
            self.player.blood_system.apply_sunlight_damage(dt)
            self.player.taking_sun_damage = True
        else:
            self.player.taking_sun_damage = False

    def _check_death(self):
        """If Dracula's blood reaches 0, trigger the death screen."""
        if self.player.blood_system.is_empty() and not self.dead:
            self.dead = True
            self._death_timer = 0.0
            self._death_alpha = 0

    def _run_death_screen(self, dt):
        """Show 'YOU DIED' overlay, then respawn at coffin."""
        DEATH_FADE_SPEED = 200   # alpha per second
        DEATH_HOLD_TIME = 2.0    # seconds to show the screen

        if self._death_alpha < 255:
            self._death_alpha = min(255, self._death_alpha + int(DEATH_FADE_SPEED * dt))
        else:
            self._death_timer += dt

        # Draw dark overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, self._death_alpha))
        self.display_surface.blit(overlay, (0, 0))

        if self._death_alpha >= 255:
            # Title text
            title = self._death_font.render('YOU DIED', True, (180, 0, 0))
            title_rect = title.get_rect(
                center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
            self.display_surface.blit(title, title_rect)

            # Subtitle
            sub = self._death_font_small.render(
                'The blood of the undead has run dry...', True, (140, 100, 100))
            sub_rect = sub.get_rect(
                center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
            self.display_surface.blit(sub, sub_rect)

        # After hold time, respawn
        if self._death_timer >= DEATH_HOLD_TIME:
            self._respawn_at_coffin()

    def _respawn_at_coffin(self):
        """Move Dracula back to his coffin and restore blood."""
        coffin_center = (
            COFFIN_POSITION[0] + COFFIN_SIZE[0] // 2,
            COFFIN_POSITION[1] + COFFIN_SIZE[1] // 2,
        )
        self.player.pos = pygame.math.Vector2(coffin_center)
        self.player.rect.center = coffin_center
        self.player.hitbox.center = coffin_center
        self.player.blood_system.blood = self.player.blood_system.max_blood
        self.player.current_form = FORM_HUMAN
        self.player.speed = DRACULA_SPEED[FORM_HUMAN]
        self.player.taking_sun_damage = False
        self.sky.reset_to_night()
        self.dead = False
        self._death_timer = 0.0
        self._death_alpha = 0

    def _check_predation(self):
        if not self.player.wants_to_feed:
            return
        self.player.wants_to_feed = False

        pred_range = PREDATION_RANGE.get(self.player.current_form, 0)
        if pred_range <= 0:
            return

        player_pos = pygame.math.Vector2(self.player.rect.center)
        for npc in self.npc_sprites.sprites():
            if not npc.can_be_preyed_on:
                continue
            npc_pos = pygame.math.Vector2(npc.rect.center)
            if player_pos.distance_to(npc_pos) <= pred_range:
                self.player.blood_system.apply_feeding()
                npc.turn_vampire()
                break

    def plant_collision(self):
        if self.soil_layer.plant_sprites:
            for plant in self.soil_layer.plant_sprites.sprites():
                if plant.harvestable and plant.rect.colliderect(self.player.hitbox):
                    self.player_add(plant.plant_type)
                    plant.kill()
                    Particle(plant.rect.topleft, plant.image,
                             self.all_sprites, z=LAYERS['main'])
                    x = plant.rect.centerx // TILE_SIZE
                    y = plant.rect.centery // TILE_SIZE
                    self.soil_layer.grid[y][x].remove('P')

    # ==================================================================
    # RESET
    # ==================================================================
    def reset(self):
        self.soil_layer.update_plants()
        self.soil_layer.remove_water()
        self.raining = randint(0, 10) > 7
        self.soil_layer.raining = self.raining
        if self.raining:
            self.soil_layer.water_all()

        for tree in self.tree_sprites.sprites():
            for apple in tree.apple_sprites.sprites():
                apple.kill()
            tree.create_fruit()

        self.sky.reset_to_night()

    # ==================================================================
    # MAIN RUN LOOP
    # ==================================================================
    def run(self, dt):
        # ── Death screen takes over ──────────────────────────────────
        if self.dead:
            self.display_surface.fill('black')
            self.all_sprites.custom_draw(self.player)
            self._run_death_screen(dt)
            return

        # drawing
        self.display_surface.fill('black')
        self.all_sprites.custom_draw(self.player)

        # updates
        if self.shop_active:
            self.menu.update()
        else:
            self.all_sprites.update(dt)
            self.plant_collision()
            Guardian.update_rotation(dt)
            self._check_sunlight(dt)
            self._check_predation()
            self._check_death()

        # weather & HUD
        self.overlay.display(dt)
        if self.raining and not self.shop_active:
            self.rain.update()
        self.sky.display(dt)

        # transition
        if self.player.sleep:
            self.transition.play()


# ─── Camera ──────────────────────────────────────────────────────────────────

class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()

    def custom_draw(self, player):
        self.offset.x = player.rect.centerx - SCREEN_WIDTH / 2
        self.offset.y = player.rect.centery - SCREEN_HEIGHT / 2

        for layer in LAYERS.values():
            for sprite in sorted(self.sprites(), key=lambda s: s.rect.centery):
                if sprite.z == layer:
                    offset_rect = sprite.rect.copy()
                    offset_rect.center -= self.offset
                    self.display_surface.blit(sprite.image, offset_rect)
