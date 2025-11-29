"""Scene factory helpers.

Provide functions to create common demo scenes. Each factory returns a
tuple (scene, franka, blocks_state, end_effector) to be used by demos.
"""
from typing import Any, Dict, Tuple
import random
import time
random.seed(time.time())

import numpy as np
import genesis as gs
from robot_adapter import RobotAdapter


def _build_base_scene(camera_pos=(3, -1, 1.5), camera_lookat=(0.0, 0.0, 0.5)) -> gs.Scene:
    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=0.01, substeps=8),
        viewer_options=gs.options.ViewerOptions(
            camera_pos=camera_pos,
            camera_lookat=camera_lookat,
            camera_fov=30,
            max_FPS=60,
        ),
        show_viewer=True,
    )
    return scene

def _elevate_robot_base(franka: Any) -> None:
    """Slightly raise robot base to avoid initial collisions."""
    # Get position as tensor (might be on GPU)
    base_pos_tensor = franka.get_pos()
    
    # Move to CPU if necessary and convert to numpy
    if base_pos_tensor.is_cuda:
        base_pos = base_pos_tensor.cpu().numpy()
    else:
        base_pos = base_pos_tensor.numpy()
    
    new_pos = base_pos.copy()
    new_pos[2] += 0.01
    franka.set_pos(new_pos) 


def _rand_xy(base, noise=0.05):
        dx = random.uniform(-noise, noise)
        dy = random.uniform(-noise, noise)
        return (base[0] + dx, base[1] + dy, base[2])

def create_scene_6blocks() -> Tuple[Any, Any, Dict[str, Any], Any]:
    """Create the default demo scene (layout 1).

    Returns:
        scene, franka_adapter, blocks_state, end_effector
    """
    scene = _build_base_scene()

    # basic geometry
    plane = scene.add_entity(gs.morphs.Plane())
    # add some random noise up to 5 cm in x/y


    posR = _rand_xy((0.65, 0.0, 0.02))
    posG = _rand_xy((0.65, 0.2, 0.02))
    posB = _rand_xy((0.65, 0.4, 0.02))
    posY = _rand_xy((0.45, 0.0, 0.02))
    posM = _rand_xy((0.45, 0.2, 0.02))
    posC = _rand_xy((0.45, 0.4, 0.02))

    cubeR = scene.add_entity(
        gs.morphs.Box(size=(0.04, 0.04, 0.04), pos= posR),
        surface=gs.options.surfaces.Plastic(color=(1.0, 0.0, 0.0)),
    )
    cubeG = scene.add_entity(
        gs.morphs.Box(size=(0.04, 0.04, 0.04), pos= posG),
        surface=gs.options.surfaces.Plastic(color=(0.0, 1.0, 0.0)),
    )
    cubeB = scene.add_entity(
        gs.morphs.Box(size=(0.04, 0.04, 0.04), pos= posB),
        surface=gs.options.surfaces.Plastic(color=(0.0, 0.0, 1.0)),
    )
    cubeY = scene.add_entity(
        gs.morphs.Box(size=(0.04, 0.04, 0.04), pos=posY),
        surface=gs.options.surfaces.Plastic(color=(1.0, 1.0, 0.0)),
    )
    cubeM = scene.add_entity(
        gs.morphs.Box(size=(0.04, 0.04, 0.04), pos=posM),
        surface=gs.options.surfaces.Plastic(color=(1.0, 0, 1.0)),
    )

    cubeC = scene.add_entity(
        gs.morphs.Box(size=(0.04, 0.04, 0.04), pos=posC),
        surface=gs.options.surfaces.Plastic(color=(0, 1.0, 1.0)),
    )

    franka_raw = scene.add_entity(gs.morphs.MJCF(file="xml/franka_emika_panda/panda.xml"))
    franka = RobotAdapter(franka_raw, scene)

    # build scene (construct physics/visuals)
    scene.build()

    # initial robot pose (7 arm joints + 2 gripper fingers)
    franka.set_qpos(np.array([0.0, -0.5, -0.2, -1.0, 0.0, 1.00, 0.5, 0.02, 0.02]))

    # slightly raise robot base to avoid initial collisions
    _elevate_robot_base(franka)

    blocks_state: Dict[str, Any] = {"r": cubeR, "g": cubeG, "b": cubeB, "y": cubeY, "m": cubeM, "c": cubeC}

    return scene, franka, blocks_state


def create_scene_stacked() -> Tuple[Any, Any, Dict[str, Any], Any]:
    """Create an alternative demo scene (layout 2) with cube positions. one on top of the other."""
    scene = _build_base_scene(camera_pos=(2.5, -1.2, 1.2), camera_lookat=(0.6, 0.0, 0.2))

    plane = scene.add_entity(gs.morphs.Plane())

    # slightly different positions
    startx, starty, _ = _rand_xy((0.45, 0.0, 0.02), noise=0.2) 
    cubeR = scene.add_entity(
        gs.morphs.Box(size=(0.04, 0.04, 0.04), pos=(startx, starty, 0.02)),
        surface=gs.options.surfaces.Plastic(color=(1.0, 0.0, 0.0)),
    )
    cubeG = scene.add_entity(
        gs.morphs.Box(size=(0.04, 0.04, 0.04), pos=(startx, starty, 0.06)),
        surface=gs.options.surfaces.Plastic(color=(0.0, 1.0, 0.0)),
    )
    cubeB = scene.add_entity(
        gs.morphs.Box(size=(0.04, 0.04, 0.04), pos=(startx, starty, 0.10)),
        surface=gs.options.surfaces.Plastic(color=(0.0, 0.0, 1.0)),
    )
    cubeY = scene.add_entity(
        gs.morphs.Box(size=(0.04, 0.04, 0.04), pos=(startx, starty, 0.14)),
        surface=gs.options.surfaces.Plastic(color=(1.0, 1.0, 0.0)),
    )

    cubeM = scene.add_entity(
        gs.morphs.Box(size=(0.04, 0.04, 0.04), pos=(startx, starty, 0.18)),
        surface=gs.options.surfaces.Plastic(color=(1.0, 0, 1.0)),
    )

    cubeC = scene.add_entity(
        gs.morphs.Box(size=(0.04, 0.04, 0.04), pos=(startx, starty, 0.22)),
        surface=gs.options.surfaces.Plastic(color=(0, 1.0, 1.0)),
    )

    franka_raw = scene.add_entity(gs.morphs.MJCF(file="xml/franka_emika_panda/panda.xml"))
    franka = RobotAdapter(franka_raw, scene)
    scene.build()

    franka.set_qpos(np.array([0.0, -0.5, -0.2, -1.0, 0.0, 1.00, 0.5, 0.02, 0.02]))

    _elevate_robot_base(franka)

    blocks_state: Dict[str, Any] = {"r": cubeR, "g": cubeG, "b": cubeB, "y": cubeY, "m": cubeM, "c": cubeC}

    return scene, franka, blocks_state

def create_scene_goal4_initial() -> Tuple[Any, Any, Dict[str, Any]]:
    """Create Goal 4 scene with blocks SCATTERED on table (initial state for TAMP).

    This creates 18 blocks randomly positioned on the table:
    - Yellow blocks: y1-y12 (12 blocks)
    - Green blocks: g1-g6 (6 blocks)

    Total: 18 blocks, all scattered on the table surface

    Returns:
        scene, franka_adapter, blocks_state
    """
    scene = _build_base_scene(camera_pos=(2.5, -1.5, 1.2), camera_lookat=(0.6, 0.0, 0.15))

    plane = scene.add_entity(gs.morphs.Plane())

    BLOCK_SIZE = 0.04  # 4cm cubes

    # Yellow color (pure yellow)
    yellow_color = (1.0, 1.0, 0.0)

    # Green color (pure green)
    green_color = (0.0, 1.0, 0.0)

    blocks_state: Dict[str, Any] = {}

    # ===== CREATE 12 YELLOW BLOCKS (scattered) =====
    # Use a wider grid pattern with larger random noise for more scattered positions
    yellow_base_positions = [
        (0.40, -0.15), (0.40, 0.05), (0.40, 0.25), (0.40, 0.45),
        (0.55, -0.15), (0.55, 0.05), (0.55, 0.25), (0.55, 0.45),
        (0.70, -0.15), (0.70, 0.05), (0.70, 0.25), (0.70, 0.45),
    ]

    for i, (base_x, base_y) in enumerate(yellow_base_positions, start=1):
        block_name = f"y{i}"
        pos = _rand_xy((base_x, base_y, 0.02), noise=0.06)

        cube = scene.add_entity(
            gs.morphs.Box(size=(BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), pos=pos),
            surface=gs.options.surfaces.Plastic(color=yellow_color),
        )
        blocks_state[block_name] = cube

    # ===== CREATE 6 GREEN BLOCKS (scattered) =====
    green_base_positions = [
        (0.45, -0.30), (0.60, -0.30), (0.75, -0.30),
        (0.45, 0.60), (0.60, 0.60), (0.75, 0.60),
    ]

    for i, (base_x, base_y) in enumerate(green_base_positions, start=1):
        block_name = f"g{i}"
        pos = _rand_xy((base_x, base_y, 0.02), noise=0.06)

        cube = scene.add_entity(
            gs.morphs.Box(size=(BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), pos=pos),
            surface=gs.options.surfaces.Plastic(color=green_color),
        )
        blocks_state[block_name] = cube

    # Add robot
    franka_raw = scene.add_entity(gs.morphs.MJCF(file="xml/franka_emika_panda/panda.xml"))
    franka = RobotAdapter(franka_raw, scene)

    # Build scene
    scene.build()

    # Initial robot pose (retracted, out of the way)
    franka.set_qpos(np.array([0.0, -0.5, -0.2, -1.0, 0.0, 1.00, 0.5, 0.02, 0.02]))

    _elevate_robot_base(franka)

    return scene, franka, blocks_state

def create_scene_goal4_final() -> Tuple[Any, Any, Dict[str, Any]]:
    """Create Goal 4 scene with blocks in FINAL positions (for visualization/testing).

    This creates:
    - Yellow Tower: 12 yellow blocks in 2×3×2 formation
    - Green Hollow Square: 6 green blocks in ring pattern

    Total: 18 blocks

    Coordinate system (right-handed):
    - x: depth (front → middle → back)
    - y: width (left → center → right)
    - z: height (bottom → top)

    Returns:
        scene, franka_adapter, blocks_state
    """
    scene = _build_base_scene(camera_pos=(2.5, -1.5, 1.2), camera_lookat=(0.6, 0.0, 0.15))

    plane = scene.add_entity(gs.morphs.Plane())

    # Define grid spacing
    BLOCK_SIZE = 0.04  # 4cm cubes
    SPACING = 0.04     # 4cm between block centers - blocks touching

    # Yellow structure is a 3D cross/plus shape:
    # Grid: 3 rows (r1=front, r2=middle, r3=back) × 4 columns (c1=left, c2=left-center, c3=right-center, c4=right)
    # Pattern per layer (6 cubes):
    #   r1:      [c2][c3]
    #   r2: [c1]        [c4]
    #   r3:      [c2][c3]

    # Define base coordinates for yellow cross (centered)
    YELLOW_BASE_X = 0.5  # Start position in x
    YELLOW_BASE_Y = 0.0  # Center position in y

    # Define base coordinates for green square (offset to the side)
    GREEN_BASE_X = 0.7   # Offset in x
    GREEN_BASE_Y = 0.3   # Offset in y

    # Position mapping for yellow cross/plus tower (12 blocks total, 6 per layer)
    # Format: position_name -> (x_offset, y_offset, z_offset)
    # Using a 4-column grid: c1 (far left), c2 (left-center), c3 (right-center), c4 (far right)
    yellow_positions = {
        # Row 1 (front): [c2][c3]
        "pos_r1_c2_bottom": (0, -SPACING/2, 0.02),       # front, left-center
        "pos_r1_c3_bottom": (0, SPACING/2, 0.02),        # front, right-center
        "pos_r1_c2_top": (0, -SPACING/2, 0.06),
        "pos_r1_c3_top": (0, SPACING/2, 0.06),

        # Row 2 (middle): [c1] and [c4]
        "pos_r2_c1_bottom": (SPACING, -1.5*SPACING, 0.02),  # middle, far left
        "pos_r2_c4_bottom": (SPACING, 1.5*SPACING, 0.02),   # middle, far right
        "pos_r2_c1_top": (SPACING, -1.5*SPACING, 0.06),
        "pos_r2_c4_top": (SPACING, 1.5*SPACING, 0.06),

        # Row 3 (back): [c2][c3]
        "pos_r3_c2_bottom": (2*SPACING, -SPACING/2, 0.02),  # back, left-center
        "pos_r3_c3_bottom": (2*SPACING, SPACING/2, 0.02),   # back, right-center
        "pos_r3_c2_top": (2*SPACING, -SPACING/2, 0.06),
        "pos_r3_c3_top": (2*SPACING, SPACING/2, 0.06),
    }

    # Position mapping for green hollow square (3×3 grid with center empty)
    green_positions = {
        "pos_front_center_bottom": (0, 0, 0.02),
        "pos_front_right_bottom": (0, SPACING, 0.02),
        "pos_middle_left_bottom": (SPACING, -SPACING, 0.02),
        "pos_middle_right_bottom": (SPACING, SPACING, 0.02),
        "pos_back_left_bottom": (2*SPACING, -SPACING, 0.02),
        "pos_back_center_bottom": (2*SPACING, 0, 0.02),
    }

    # Yellow color (pure yellow)
    yellow_color = (1.0, 1.0, 0.0)

    # Green color (pure green)
    green_color = (0.0, 1.0, 0.0)

    blocks_state: Dict[str, Any] = {}

    # ===== CREATE YELLOW CROSS/PLUS TOWER (12 blocks) =====
    # 6 blocks per layer in cross pattern
    yellow_block_positions = [
        # Row 1 (front): 2 blocks at center columns
        ("y1", "pos_r1_c2_bottom"),
        ("y2", "pos_r1_c3_bottom"),
        ("y3", "pos_r1_c2_top"),
        ("y4", "pos_r1_c3_top"),

        # Row 2 (middle): 2 blocks at far left and far right
        ("y5", "pos_r2_c1_bottom"),
        ("y6", "pos_r2_c4_bottom"),
        ("y7", "pos_r2_c1_top"),
        ("y8", "pos_r2_c4_top"),

        # Row 3 (back): 2 blocks at center columns
        ("y9", "pos_r3_c2_bottom"),
        ("y10", "pos_r3_c3_bottom"),
        ("y11", "pos_r3_c2_top"),
        ("y12", "pos_r3_c3_top"),
    ]

    for block_name, pos_name in yellow_block_positions:
        dx, dy, dz = yellow_positions[pos_name]
        pos = (YELLOW_BASE_X + dx, YELLOW_BASE_Y + dy, dz)

        cube = scene.add_entity(
            gs.morphs.Box(size=(BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), pos=pos),
            surface=gs.options.surfaces.Plastic(color=yellow_color),
        )
        blocks_state[block_name] = cube

    # ===== CREATE GREEN HOLLOW SQUARE (6 blocks) =====
    green_block_positions = [
        ("g1", "pos_front_center_bottom"),
        ("g2", "pos_front_right_bottom"),
        ("g3", "pos_middle_left_bottom"),
        ("g4", "pos_middle_right_bottom"),
        ("g5", "pos_back_left_bottom"),
        ("g6", "pos_back_center_bottom"),
    ]

    for block_name, pos_name in green_block_positions:
        dx, dy, dz = green_positions[pos_name]
        pos = (GREEN_BASE_X + dx, GREEN_BASE_Y + dy, dz)

        cube = scene.add_entity(
            gs.morphs.Box(size=(BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), pos=pos),
            surface=gs.options.surfaces.Plastic(color=green_color),
        )
        blocks_state[block_name] = cube

    # Add robot
    franka_raw = scene.add_entity(gs.morphs.MJCF(file="xml/franka_emika_panda/panda.xml"))
    franka = RobotAdapter(franka_raw, scene)

    # Build scene
    scene.build()

    # Initial robot pose (retracted, out of the way)
    franka.set_qpos(np.array([0.0, -0.5, -0.2, -1.0, 0.0, 1.00, 0.5, 0.02, 0.02]))

    _elevate_robot_base(franka)

    return scene, franka, blocks_state
