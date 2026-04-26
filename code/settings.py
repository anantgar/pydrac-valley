# =============================================================================
# WINDOW & DISPLAY
# =============================================================================
WINDOW_TITLE = 'PyDrac Valley'
FPS = 60
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 768
TILE_SIZE = 64

# =============================================================================
# RENDERING LAYERS
# =============================================================================
LAYERS = {
    'water': 0,
    'ground': 1,
    'rain floor': 4,
    'house bottom': 5,
    'main': 7,
    'house top': 8,
    'rain drops': 10,
}

# =============================================================================
# DRACULA FORMS
# =============================================================================
FORM_HUMAN = 'human'
FORM_BAT = 'bat'
FORM_WEREWOLF = 'werewolf'

DRACULA_SPEED = {
    FORM_HUMAN: 300,
    FORM_BAT: 450,
    FORM_WEREWOLF: 400,
}

# Visual tints applied to character sprites per form (RGB multiply)
FORM_TINT = {
    FORM_HUMAN: None,
    FORM_BAT: (100, 100, 220),
    FORM_WEREWOLF: (220, 160, 100),
}

# =============================================================================
# BLOOD / HEALTH SYSTEM
# =============================================================================
MAX_BLOOD = 100.0
BLOOD_DRAIN_TRANSFORM = {
    FORM_BAT: 15.0,
    FORM_WEREWOLF: 20.0,
}
BLOOD_DRAIN_SUNLIGHT_PER_SEC = 10.0
BLOOD_GAIN_FEEDING = 25.0

PREDATION_RANGE = {
    FORM_HUMAN: 80,
    FORM_WEREWOLF: 120,
}
PREDATION_COOLDOWN_MS = 1000

# =============================================================================
# TIME / DAY-NIGHT CYCLE
# =============================================================================
GAME_HOURS_PER_SECOND = 0.04
GAME_START_HOUR = 20.0

DAY_START_HOUR = 6.0
DAY_END_HOUR = 20.0
DAWN_START = 6.0
DAWN_END = 8.0
DUSK_START = 18.0
DUSK_END = 20.0

# Sky overlay colors (used with BLEND_RGBA_MULT — white = full bright)
SKY_DAY_COLOR = (255, 255, 255)
SKY_NIGHT_COLOR = (80, 80, 140)  # Brighter night — still visible

# =============================================================================
# EXPANDED WORLD LAYOUT
# =============================================================================
# The original TMX map occupies (0,0) to (3200,2560).
# New areas are placed to the west (negative x) and east (positive x past 3200).
#
# Layout (approximate):
#   Castle (-3200, 800)  ---- Road ---- London (0,0 area) ---- Road ---- Asylum (4800, 800)
#                                              |
#                                              Road
#                                              |
#                                        Budapest (4800, 3800)
#
ORIGINAL_MAP_WIDTH = 3200
ORIGINAL_MAP_HEIGHT = 2560

# ── Building definitions ─────────────────────────────────────────────────────
# Each building: (x, y, width_tiles, height_tiles)
# Tiles are 64x64.  Floor = interior, walls = perimeter collision.

CASTLE_BUILDING = (-3000, 800, 10, 8)       # Dracula's castle
GRAVEYARD_AREA  = (-3000, 1700, 10, 6)      # Graveyard below castle

ASYLUM_BUILDING = (4800, 800, 10, 8)        # Asylum (east of London)
CONVENT_BUILDING = (4800, 3800, 8, 6)       # Budapest convent (far south-east)
MUSEUM_BUILDING = (2400, -800, 6, 5)        # Museum north of London

LUCY_BEDROOM_BUILDING = (960, 1408, 5, 4)   # Bedroom attached west of London house
MINA_BEDROOM_BUILDING = (1792, 1408, 5, 4)  # Bedroom attached east of London house

# ── Road definitions (start_pos, end_pos, width_in_tiles) ────────────────────
# Roads are horizontal or vertical strips of path tiles.
# Coordinates must align with fence exit gaps at:
#   West:  x=384  (tile 6),  y=1088-1280 (tiles 17-19)
#   East:  x=2944 (tile 46), y=1088-1280 (tiles 17-19)
#   North: x=2368 (tile 37), y=128-320   (tiles 2-4)
ROADS = [
    # Castle → London west exit (horizontal road at y≈1150, through west gap)
    {'start': (-2360, 1088), 'end': (500, 1088), 'width': 3, 'axis': 'horizontal'},
    # London east exit → Asylum (horizontal road through east gap)
    {'start': (2880, 1088), 'end': (4800, 1088), 'width': 3, 'axis': 'horizontal'},
    # London north exit → Museum (vertical road through north gap)
    {'start': (2368, -800), 'end': (2368, 400), 'width': 3, 'axis': 'vertical'},
    # Junction down to Budapest road (from asylum)
    {'start': (4928, 1088), 'end': (4928, 3800), 'width': 2, 'axis': 'vertical'},
]

# ── World regions (for sunlight / NPC logic) ─────────────────────────────────
# (x, y, w, h) in pixels
WORLD_REGIONS = {
    'castle_interior':  (-3000, 800,  640, 512),
    'graveyard':        (-3000, 1700, 640, 384),

    'london_streets':   (0,    0,   3200, 2560),
    'lucy_house':       (1280, 1344, 512, 384),
    'lucy_house_inner': (1344, 1408, 384, 256),
    'lucy_bedroom':     (1024, 1472, 192, 128),
    'mina_bedroom':     (1856, 1472, 192, 128),
    'guardian_room':    (1344, 1600, 192, 128),
    'garden':           (1280, 1728, 512, 256),
    'museum':           (2400, -800, 384, 320),

    'asylum':           (4800, 800,  640, 512),
    'asylum_cell':      (4864, 864,  192, 192),
    'asylum_halls':     (5056, 864,  320, 448),

    'budapest_convent': (4800, 3800, 512, 384),
}

SAFE_REGIONS = {'castle_interior'}

INDOOR_REGIONS = {
    'castle_interior', 'lucy_house', 'lucy_bedroom', 'mina_bedroom',
    'guardian_room', 'museum', 'asylum', 'asylum_cell', 'asylum_halls',
    'budapest_convent',
}

# =============================================================================
# KEY POSITIONS (pixels)
# =============================================================================
# Coffin inside castle interior
COFFIN_POSITION = (-2700, 1000)
COFFIN_SIZE = (TILE_SIZE * 2, TILE_SIZE)

# =============================================================================
# NPC CONFIGURATION
# =============================================================================
NPC_PATROL_SPEED = 100
NPC_PACE_SPEED = 60
NPC_FRANTIC_SPEED = 360
WATCH_ROTATION_DURATION = 30.0

# NPC positions — inside their respective buildings
NPC_POSITIONS = {
    # Side bedrooms attached to the London house
    'lucy':        (1056, 1568),
    'mina':        (1888, 1568),
    'arthur':      (1408, 1600),     # Main London house interior
    'van_helsing': (1536, 1472),
    'quincey':     (1664, 1600),

    # Asylum interior (4864-5376, 864-1312)
    'renfield':    (4928, 960),      # In the cell area
    'seward':      (5200, 1050),     # In the halls

    # Budapest convent interior (4864-5312, 3864-4120)
    'jonathan':    (5050, 4000),
}

# Guardian patrol waypoints (around Lucy's house interior and entrance)
GUARDIAN_PATROL_WAYPOINTS = [
    (1350, 1420), (1700, 1420),
    (1700, 1700), (1350, 1700),
]
GUARDIAN_SLEEP_POSITIONS = {
    'arthur':      (1408, 1600),
    'van_helsing': (1536, 1472),
    'quincey':     (1664, 1600),
}

# Seward pacing in a straight line beside Renfield's cell
SEWARD_WAYPOINTS = [
    (5184, 900), (5184, 1216),
]

# =============================================================================
# ELISABETA PORTRAIT
# =============================================================================
ELISABETA_PORTRAIT_TEXT = (
    "A faded portrait of Elisabeta, your eternal beloved.\n"
    "Her eyes seem to follow you through the centuries.\n"
    "You carry this always, close to your undead heart."
)

# =============================================================================
# HUD LAYOUT
# =============================================================================
BLOOD_BAR_POS = (20, 20)
BLOOD_BAR_SIZE = (200, 24)
FORM_INDICATOR_POS = (20, 56)
TIME_INDICATOR_POS = (SCREEN_WIDTH - 160, 20)
SUNLIGHT_WARNING_POS = (SCREEN_WIDTH // 2, 60)

# =============================================================================
# ASSET PATH CONSTANTS
# =============================================================================
CHARACTER_SPRITE_PATH = '../graphics/character'
FONT_PATH = '../font/LycheeSoda.ttf'
HOUSE_TILESET_PATH = '../graphics/environment/House.png'
HOUSE_DECORATION_TILESET_PATH = '../graphics/environment/House Decoration.png'
PATHS_TILESET_PATH = '../graphics/environment/Paths.png'
