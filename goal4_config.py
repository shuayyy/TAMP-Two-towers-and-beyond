"""Goal 4 Configuration - Position Mapping and Utilities

This module defines the spatial configuration for Goal 4 structures:
- Yellow cross/plus tower (12 blocks)
- Green hollow square (6 blocks)

Provides mapping from PDDL position names to Genesis (x,y,z) coordinates.
"""

from typing import Dict, Tuple
import numpy as np

# Physical constants (must match scenes.py)
BLOCK_SIZE = 0.04  # 4cm cubes
SPACING = 0.04     # 4cm between block centers - blocks touching

# Base coordinates for structures - BUILD ADJACENT
YELLOW_BASE_X = 0.5  # Yellow cross center position
YELLOW_BASE_Y = 0.0
GREEN_BASE_X = 0.5   # Green square ADJACENT to yellow (same X)
GREEN_BASE_Y = 0.15  # Offset in Y to be next to yellow cross

# Position tolerance for detecting if block is at a position
POSITION_XY_THRESHOLD = 0.015  # 1.5cm tolerance in XY plane
POSITION_Z_THRESHOLD = 0.01    # 1cm tolerance in Z


# ===== POSITION COORDINATES MAPPING =====
# Maps PDDL position names to absolute (x, y, z) coordinates in Genesis

def _compute_absolute_coords() -> Dict[str, Tuple[float, float, float]]:
    """Compute absolute coordinates for all Goal 4 positions.

    Returns:
        Dictionary mapping position names to (x, y, z) tuples
    """
    coords = {}

    # ===== YELLOW CROSS/PLUS POSITIONS =====
    # 12 positions total: 3 rows × 4 columns × 2 layers
    # Pattern per layer (6 positions):
    #   r1:      [c2][c3]
    #   r2: [c1]        [c4]
    #   r3:      [c2][c3]

    yellow_offsets = {
        # Row 1 (front): [c2][c3]
        "pos_r1_c2_bottom": (0, -SPACING/2, 0.02),
        "pos_r1_c3_bottom": (0, SPACING/2, 0.02),
        "pos_r1_c2_top": (0, -SPACING/2, 0.06),
        "pos_r1_c3_top": (0, SPACING/2, 0.06),

        # Row 2 (middle): [c1] and [c4]
        "pos_r2_c1_bottom": (SPACING, -1.5*SPACING, 0.02),
        "pos_r2_c4_bottom": (SPACING, 1.5*SPACING, 0.02),
        "pos_r2_c1_top": (SPACING, -1.5*SPACING, 0.06),
        "pos_r2_c4_top": (SPACING, 1.5*SPACING, 0.06),

        # Row 3 (back): [c2][c3]
        "pos_r3_c2_bottom": (2*SPACING, -SPACING/2, 0.02),
        "pos_r3_c3_bottom": (2*SPACING, SPACING/2, 0.02),
        "pos_r3_c2_top": (2*SPACING, -SPACING/2, 0.06),
        "pos_r3_c3_top": (2*SPACING, SPACING/2, 0.06),
    }

    # Convert offsets to absolute coordinates
    for pos_name, (dx, dy, dz) in yellow_offsets.items():
        coords[pos_name] = (YELLOW_BASE_X + dx, YELLOW_BASE_Y + dy, dz)

    # ===== GREEN HOLLOW SQUARE POSITIONS =====
    # 6 positions + 1 empty center: 3×3 grid with center empty
    # All at z=0.02 (bottom layer only)

    green_offsets = {
        "pos_front_center_bottom": (0, 0, 0.02),
        "pos_front_right_bottom": (0, SPACING, 0.02),
        "pos_middle_left_bottom": (SPACING, -SPACING, 0.02),
        "pos_middle_right_bottom": (SPACING, SPACING, 0.02),
        "pos_back_left_bottom": (2*SPACING, -SPACING, 0.02),
        "pos_back_center_bottom": (2*SPACING, 0, 0.02),
    }

    # Convert offsets to absolute coordinates
    for pos_name, (dx, dy, dz) in green_offsets.items():
        coords[pos_name] = (GREEN_BASE_X + dx, GREEN_BASE_Y + dy, dz)

    # Add the center empty position (for completeness, even though not used in goal)
    coords["pos_middle_center_bottom"] = (GREEN_BASE_X + SPACING, GREEN_BASE_Y, 0.02)

    return coords


# Global position coordinates dictionary
GOAL4_POSITION_COORDS = _compute_absolute_coords()


# ===== HELPER FUNCTIONS =====

def get_position_coords(position_name: str) -> Tuple[float, float, float]:
    """Get absolute (x, y, z) coordinates for a position name.

    Args:
        position_name: PDDL position name (e.g., "pos_r1_c2_bottom")

    Returns:
        Tuple of (x, y, z) coordinates

    Raises:
        KeyError: If position_name is not valid
    """
    return GOAL4_POSITION_COORDS[position_name]


def is_block_at_position(block_pos: np.ndarray,
                         position_name: str,
                         xy_threshold: float = POSITION_XY_THRESHOLD,
                         z_threshold: float = POSITION_Z_THRESHOLD) -> bool:
    """Check if a block is at a specific named position.

    Args:
        block_pos: [x, y, z] numpy array of block center position
        position_name: PDDL position name to check
        xy_threshold: Tolerance for XY distance (default: 1.5cm)
        z_threshold: Tolerance for Z distance (default: 1cm)

    Returns:
        True if block is at the position, False otherwise
    """
    target_pos = np.array(GOAL4_POSITION_COORDS[position_name])

    # Check XY distance
    xy_distance = np.linalg.norm(block_pos[:2] - target_pos[:2])
    if xy_distance > xy_threshold:
        return False

    # Check Z distance
    z_distance = abs(block_pos[2] - target_pos[2])
    if z_distance > z_threshold:
        return False

    return True


def find_block_position(block_pos: np.ndarray) -> str | None:
    """Find which named position a block is at (if any).

    Args:
        block_pos: [x, y, z] numpy array of block center position

    Returns:
        Position name if block is at a known position, None otherwise
    """
    for pos_name in GOAL4_POSITION_COORDS.keys():
        if is_block_at_position(block_pos, pos_name):
            return pos_name
    return None


def get_all_position_names() -> list[str]:
    """Get list of all valid position names.

    Returns:
        List of position name strings
    """
    return list(GOAL4_POSITION_COORDS.keys())


def get_yellow_positions() -> list[str]:
    """Get list of yellow cross/plus position names.

    Returns:
        List of position names for yellow structure
    """
    return [name for name in GOAL4_POSITION_COORDS.keys() if name.startswith("pos_r")]


def get_green_positions() -> list[str]:
    """Get list of green hollow square position names.

    Returns:
        List of position names for green structure
    """
    return [name for name in GOAL4_POSITION_COORDS.keys()
            if name.startswith("pos_") and not name.startswith("pos_r")]


def visualize_positions():
    """Print all position coordinates for debugging."""
    print("\n" + "=" * 80)
    print("GOAL 4 POSITION COORDINATES")
    print("=" * 80)

    print("\nYellow Cross/Plus Positions (12 total):")
    for name in sorted(get_yellow_positions()):
        x, y, z = GOAL4_POSITION_COORDS[name]
        print(f"  {name:25s} → ({x:.4f}, {y:.4f}, {z:.4f})")

    print("\nGreen Hollow Square Positions (6 used + 1 empty center):")
    for name in sorted(get_green_positions()):
        x, y, z = GOAL4_POSITION_COORDS[name]
        marker = " [CENTER - EMPTY]" if "center" in name and "middle" in name else ""
        print(f"  {name:30s} → ({x:.4f}, {y:.4f}, {z:.4f}){marker}")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    print("Goal 4 Configuration Module")
    print(f"\nTotal positions defined: {len(GOAL4_POSITION_COORDS)}")
    print(f"  Yellow positions: {len(get_yellow_positions())}")
    print(f"  Green positions: {len(get_green_positions())}")

    visualize_positions()

    # Test position lookup
    print("\nExample usage:")
    pos_name = "pos_r1_c2_bottom"
    coords = get_position_coords(pos_name)
    print(f'  get_position_coords("{pos_name}") → {coords}')

    test_pos = np.array([0.5, -0.02, 0.02])
    print(f'\n  is_block_at_position({test_pos}, "{pos_name}") → {is_block_at_position(test_pos, pos_name)}')

    found = find_block_position(test_pos)
    print(f'  find_block_position({test_pos}) → "{found}"')
