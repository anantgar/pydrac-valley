# PyDrac Valley Architecture & Context

This document contains the critical context for "PyDrac Valley", a gothic Dracula survival/hunting game built by refactoring a Stardew Valley-style base game (PydewValley).

## Core Architecture

The game is built in Pygame using a sprite and component-based structure. Everything is managed by `Level` (`code/level.py`).

- **`code/settings.py`**: Contains all game configuration (Dracula forms, base speeds, blood tuning, time scale, world region coords, NPC positions).
- **`code/level.py`**: The scene manager. Loads the TMX map, procedurally generates the expanded world, runs sunlight & predation checks, manages NPC/player updates, and handles drawing via `CameraGroup`.
- **`code/player.py` (`Dracula`)**: The main character. Has three forms (`human`, `bat`, `werewolf`), an instance of `BloodSystem`, and predation capabilities. 
- **`code/npc.py`**: Stateful AI system. `NPC` base class handles movement to waypoints within constrained zone rects. Inheriting classes (Lucy, Mina, Guardians, Renfield, Seward, Jonathan Harker) have distinct behaviors (sleeping, pacing, patrolling, stationary, or rotating watch).
- **`code/world.py` (`WorldManager`)**: Divides the expanded map into `Region` bounding boxes (e.g., `castle_interior`, `lucy_bedroom`). Used for logic checks (`is_outdoors`, `is_safe_for_dracula`).
- **`code/blood.py` (`BloodSystem`)**: A standalone component on Dracula tracking blood loss (sunlight, transformations) and gain (feeding).
- **`code/sky.py` (`Sky`)**: Manages the day/night cycle. Tracks `game_hour` (0-24) and smoothly transitions sky colors (day/night are distinct values using `BLEND_RGBA_MULT`).
- **`code/overlay.py`**: The HUD. Shows blood bar, current form, time, and sunlight warnings overlaying the screen.
- **`code/transition.py`**: Handles screen fades when interacting with the coffin to skip to the next night.
- **`code/soil.py` + `timer.py` + `menu.py`**: Legacy farming code maintained and intentionally left functional for a planned "dead body farm" reskin context.

## Systems & Mechanics

1. **Transformations**: Dracula can swap forms via `H` (Human), `B` (Bat), `W` (Werewolf). Bat ignores collisions (including water). Forms apply RGB tints to sprites. Costs blood.
2. **Blood & Sunlight**: Exposed to sunlight outside safe areas (e.g., Castle Interior) during daytime drains blood.
3. **Predation (Feeding)**: Press `F` near an NPC to feed and regain blood. Has range and form constraints (no feeding in Bat form).
4. **NPC AI**: 
    - Lucy & Mina sleep. 
    - Guardians (Arthur, Van Helsing, Quincey) use a class-level rotation: 1 patrols, 2 sleep.
    - Renfield paces a cell, Seward patrols asylum halls, Harker sits stationary in a convent.
5. **Expanded World Generation**: 
    - The original TMX map resides at (0,0) as London. 
    - Extra locations (Castle, Asylum, Convent, Museum) are generated prodecurally by pasting `House.png` tiles and connected using `Paths.png`. 
    - All NPCs are placed inside these procedural structures.
6. **Water Collision**: The `Water` generic sprite was modified to retain a full 64x64 hitbox so nothing can walk through rivers/oceans.
7. **Portrait & Coffin**: Press `P` for the Elisabeta portrait inspection overlay. Interact with the Coffin to sleep.

## Important Note

- Do not rip out the original `soil`, `tool`, or `seed` planting mechanics. The player uses standard controls (`Space`, `Q`, `LCTRL`, `E`) to do farming, but it is to be refactored visually into a graveyard mechanic.
- Assets are assumed to exist and `support.py`'s `get_path` loads from the `graphics/` dir. 
