"""Symbolic Abstraction Module (Person 2 - TAMP Project)

This module converts continuous scene geometry into discrete PDDL predicates.
It implements the "lifting" operation that bridges the continuous world state
to symbolic task planning.

For Goal 1: Build two towers
  - Tower 1: RED-GREEN-BLUE (top to bottom)
  - Tower 2: YELLOW-MAGENTA-CYAN (top to bottom)

Author: Person 2
Date: 2024
"""

from typing import Dict, Set, Tuple, Any
import numpy as np


# Constants - Block properties
BLOCK_SIZE = 0.04  # 4cm cubes
BLOCK_HALF_HEIGHT = BLOCK_SIZE / 2  # 0.02m

# Tuning thresholds (experimentally determined)
TABLE_HEIGHT = 0.0  # Table Z-coordinate
TABLE_THRESHOLD = 0.03  # Tolerance for "on table" check
XY_ALIGNMENT_THRESHOLD = 0.015  # XY centering tolerance for stacking
Z_STACK_THRESHOLD = 0.005  # Z-distance tolerance for "on" relation
HOLDING_THRESHOLD = 0.05  # Distance threshold for gripper holding block


def get_block_positions(blocks_state: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """Query all block positions from the Genesis scene.

    Args:
        blocks_state: Dictionary mapping block names to Genesis entities
                     {"r": cubeR, "g": cubeG, "b": cubeB, ...}

    Returns:
        Dictionary mapping block names to [x, y, z] positions
        Example: {"r": [0.65, 0.0, 0.02], "g": [0.65, 0.2, 0.02], ...}
    """
    positions = {}
    for block_name, block_entity in blocks_state.items():
        pos = block_entity.get_pos()
        # Convert to numpy array for easier manipulation
        try:
            positions[block_name] = pos.cpu().numpy()
        except:
            positions[block_name] = np.array(pos, dtype=float)

    return positions


def get_gripper_state(robot: Any) -> Tuple[np.ndarray, bool]:
    """Get robot gripper position and state.

    Args:
        robot: RobotAdapter instance

    Returns:
        Tuple of (gripper_position, is_closed)
        - gripper_position: [x, y, z] numpy array
        - is_closed: True if gripper is closed (grasping), False if open
    """
    # Get end effector (hand) link position
    hand_link = robot.get_link("hand")
    pos = hand_link.get_pos()
    try:
        gripper_pos = pos.cpu().numpy()
    except Exception:
        gripper_pos = np.array(pos, dtype=float)

    # Get gripper joint positions (last 2 DOFs are gripper fingers)
    qpos = robot.get_qpos()
    if hasattr(qpos, "cpu"):
        try:
            qpos_cpu = qpos.detach().cpu().numpy()
        except Exception:
            qpos_cpu = np.array(qpos, dtype=float)
    else:
        qpos_cpu = np.array(qpos, dtype=float)

    # Defensive: ensure we have at least two values for fingers
    if qpos_cpu.size >= 2:
        gripper_width = float(qpos_cpu[-2] + qpos_cpu[-1])
    else:
        gripper_width = float(np.sum(qpos_cpu)) if qpos_cpu.size > 0 else 0.0

    # Gripper is considered closed if width is small
    is_closed = gripper_width < 0.04

    return gripper_pos, is_closed


def is_on_table(block_pos: np.ndarray, table_height: float = TABLE_HEIGHT,
                threshold: float = TABLE_THRESHOLD) -> bool:
    """Check if a block is on the table.

    Args:
        block_pos: [x, y, z] position of block center
        table_height: Z-coordinate of table surface (default: 0.0)
        threshold: Tolerance for height check

    Returns:
        True if block is on table, False otherwise

    Note:
        Block positions are at their center. A 4cm block sitting on the table
        has its center at Z = 0.02 (half the block height above table).
    """
    expected_z = table_height + BLOCK_HALF_HEIGHT
    return abs(block_pos[2] - expected_z) < threshold


def is_on(block_a_pos: np.ndarray, block_b_pos: np.ndarray,
          xy_threshold: float = XY_ALIGNMENT_THRESHOLD,
          z_threshold: float = Z_STACK_THRESHOLD) -> bool:
    """Check if block_a is directly on top of block_b.

    Args:
        block_a_pos: [x, y, z] position of top block (block A)
        block_b_pos: [x, y, z] position of bottom block (block B)
        xy_threshold: Tolerance for XY alignment (centering)
        z_threshold: Tolerance for Z distance

    Returns:
        True if block_a is on block_b, False otherwise

    Logic:
        - XY distance must be small (blocks are centered)
        - Z distance must equal one block height (0.04m)
    """
    # Check XY alignment (blocks should be centered on each other)
    xy_distance = np.linalg.norm(block_a_pos[:2] - block_b_pos[:2])
    if xy_distance > xy_threshold:
        return False

    # Check Z distance (should be one block height)
    z_distance = block_a_pos[2] - block_b_pos[2]
    expected_z_diff = BLOCK_SIZE

    return abs(z_distance - expected_z_diff) < z_threshold


def is_clear(block_name: str, all_block_positions: Dict[str, np.ndarray]) -> bool:
    """Check if a block has nothing on top of it.

    Args:
        block_name: Name of block to check (e.g., "r", "g", "b")
        all_block_positions: Dictionary of all block positions

    Returns:
        True if no other block is on top of this block, False otherwise
    """
    target_pos = all_block_positions[block_name]

    # Check if any other block is on top of this one
    for other_name, other_pos in all_block_positions.items():
        if other_name == block_name:
            continue

        if is_on(other_pos, target_pos):
            return False

    return True

def is_holding(block_name: str,
               robot: Any,
               blocks_state: Dict[str, Any]) -> bool:
    """
    Ground-truth holding check using RobotAdapter.attached_object.
    """
    attached = robot.attached_object
    block_obj = blocks_state[block_name]

    is_holding_block = (attached is block_obj)

    print(f"[HOLDING] block={block_name}, "
          f"attached_obj={attached}, "
          f"is_holding={is_holding_block}")

    return is_holding_block



def is_handempty(gripper_pos: np.ndarray, gripper_closed: bool,
                 all_block_positions: Dict[str, np.ndarray],
                 threshold: float = HOLDING_THRESHOLD) -> bool:
    """Check if the robot gripper is empty (not holding anything).

    Args:
        gripper_pos: [x, y, z] position of gripper
        gripper_closed: True if gripper is closed
        all_block_positions: Dictionary of all block positions
        threshold: Distance tolerance

    Returns:
        True if gripper is not holding any block, False otherwise
    """
    # If gripper is open, it's definitely empty
    if not gripper_closed:
        return True

    # Even if closed, check if it's actually holding any block
    for block_name, block_pos in all_block_positions.items():
        if is_holding(block_name, gripper_pos, block_pos, gripper_closed, threshold):
            return False

    return True


def abstract_state(scene: Any, robot: Any, blocks_state: Dict[str, Any],
                   goal_id: int = 1) -> Set[Tuple]:
    """Convert continuous scene state into symbolic PDDL predicates.

    This is the main function for symbolic abstraction (lifting).

    Args:
        scene: Genesis scene object
        robot: RobotAdapter instance
        blocks_state: Dictionary mapping block names to Genesis entities
        goal_id: Goal identifier (1-3: standard blocks, 4: position-aware)

    Returns:
        Set of tuples representing true predicates

    Example output:
        {
            ("ontable", "r"),     # Red block on table
            ("ontable", "b"),     # Blue block on table
            ("on", "g", "r"),     # Green block on red block
            ("clear", "b"),       # Blue block is clear
            ("clear", "g"),       # Green block is clear
            ("handempty",)        # Robot not holding anything
        }

    Predicates (Goals 1-3):
        - (ontable, block): block is on the table
        - (on, block_a, block_b): block_a is on top of block_b
        - (clear, block): nothing is on top of block
        - (holding, block): robot is holding block
        - (handempty,): robot gripper is empty

    Additional Predicates (Goal 4):
        - (at-position, block, position): block is at named position
        - (position-free, position): position is not occupied
    """
    predicates = set()

    # Get all current positions
    block_positions = get_block_positions(blocks_state)
    gripper_pos, gripper_closed = get_gripper_state(robot)

    # Evaluate predicates for each block
    for block_name in blocks_state.keys():
        block_pos = block_positions[block_name]

        # Check if block is on table
        if is_on_table(block_pos):
            predicates.add(("ontable", block_name))

        # Check if block is clear (nothing on top)
        if is_clear(block_name, block_positions):
            predicates.add(("clear", block_name))

        # Check if robot is holding this block
        if is_holding(block_name, robot, blocks_state):
            predicates.add(("holding", block_name))

        # Check "on" relationships with all other blocks
        for other_name in blocks_state.keys():
            if other_name == block_name:
                continue

            other_pos = block_positions[other_name]
            if is_on(block_pos, other_pos):
                predicates.add(("on", block_name, other_name))

    # Check if hand is empty
    if robot.attached_object is None:
        predicates.add(("handempty",))

    # Goal 4 (and sub-goals 41, 42): Add position predicates
    if goal_id in [4, 41, 42]:
        try:
            from goal4_config import find_block_position, get_all_position_names

            # Track which positions are occupied
            occupied_positions = set()

            # Check each block's position at goal locations
            for block_name in blocks_state.keys():
                block_pos = block_positions[block_name]
                pos_name = find_block_position(block_pos)

                if pos_name is not None:
                    predicates.add(("at-position", block_name, pos_name))
                    occupied_positions.add(pos_name)

            # Mark free positions
            all_positions = get_all_position_names()
            for pos_name in all_positions:
                if pos_name not in occupied_positions:
                    predicates.add(("position-free", pos_name))

        except ImportError:
            # Goal 4 config not available, skip position predicates
            pass

    return predicates


def visualize_predicates(predicates: Set[Tuple], title: str = "Current State") -> None:
    """Print predicates in human-readable format.

    Args:
        predicates: Set of predicate tuples
        title: Optional title for the output
    """
    print(f"\n{'='*60}")
    print(f"{title:^60}")
    print(f"{'='*60}")

    # Sort predicates by type for better readability
    ontable = [p for p in predicates if p[0] == "ontable"]
    on_relations = [p for p in predicates if p[0] == "on"]
    clear = [p for p in predicates if p[0] == "clear"]
    holding = [p for p in predicates if p[0] == "holding"]
    handempty = [p for p in predicates if p[0] == "handempty"]
    at_position = [p for p in predicates if p[0] == "at-position"]
    position_free = [p for p in predicates if p[0] == "position-free"]

    if ontable:
        print("\nBlocks on table:")
        for pred in sorted(ontable):
            print(f"  - {pred[1].upper()} is on table")

    if on_relations:
        print("\nStacking relationships:")
        for pred in sorted(on_relations):
            print(f"  - {pred[1].upper()} is on {pred[2].upper()}")

    if clear:
        print("\nClear blocks (nothing on top):")
        for pred in sorted(clear):
            print(f"  - {pred[1].upper()} is clear")

    if holding:
        print("\nRobot holding:")
        for pred in sorted(holding):
            print(f"  - Holding {pred[1].upper()}")

    if handempty:
        print("\nRobot hand: EMPTY")

    if at_position:
        print(f"\nBlocks at positions ({len(at_position)} occupied):")
        for pred in sorted(at_position):
            print(f"  - {pred[1].upper()} at {pred[2]}")

    if position_free:
        print(f"\nFree positions ({len(position_free)} available):")
        # Only show first 10 to avoid clutter
        for pred in sorted(position_free)[:10]:
            print(f"  - {pred[1]}")
        if len(position_free) > 10:
            print(f"  ... and {len(position_free) - 10} more")

    print(f"{'='*60}\n")


def visualize_ascii_blocks(predicates: Set[Tuple]) -> None:
    """Generate ASCII art representation of block configuration.

    Args:
        predicates: Set of predicate tuples
    """
    print("\nASCII Block Configuration:")
    print("-" * 40)

    # Build tower structure from predicates
    on_relations = {p[1]: p[2] for p in predicates if p[0] == "on"}
    ontable = {p[1] for p in predicates if p[0] == "ontable"}

    # Find all towers (blocks on table are roots)
    towers = []
    for root in ontable:
        tower = [root]
        current = root
        # Build tower upward
        while True:
            # Find what's on current
            found = None
            for top, bottom in on_relations.items():
                if bottom == current:
                    found = top
                    break
            if found:
                tower.append(found)
                current = found
            else:
                break
        towers.append(tower)

    # Print towers
    if not towers:
        print("  No towers (all blocks scattered or held)")
    else:
        for i, tower in enumerate(towers, 1):
            print(f"\n  Tower {i}:")
            for j, block in enumerate(reversed(tower)):
                indent = "    "
                print(f"{indent}[{block.upper()}]")
                if j < len(tower) - 1:
                    print(f"{indent} | ")

    print("-" * 40 + "\n")


def log_predicate_changes(old_predicates: Set[Tuple], new_predicates: Set[Tuple]) -> None:
    """Log changes in predicates between two states.

    Useful for debugging and tracking state evolution during execution.

    Args:
        old_predicates: Previous state predicates
        new_predicates: Current state predicates
    """
    added = new_predicates - old_predicates
    removed = old_predicates - new_predicates

    if not added and not removed:
        print("No changes in predicates.")
        return

    print("\n" + "="*60)
    print("PREDICATE CHANGES")
    print("="*60)

    if added:
        print("\nADDED:")
        for pred in sorted(added):
            print(f"  + {pred}")

    if removed:
        print("\nREMOVED:")
        for pred in sorted(removed):
            print(f"  - {pred}")

    print("="*60 + "\n")


# Helper function for tuning thresholds
def debug_spatial_relationships(blocks_state: Dict[str, Any], robot: Any) -> None:
    """Debug tool to print all spatial relationships and distances.

    Useful for experimentally tuning threshold values.

    Args:
        blocks_state: Dictionary of block entities
        robot: RobotAdapter instance
    """
    positions = get_block_positions(blocks_state)
    gripper_pos, gripper_closed = get_gripper_state(robot)

    print("\n" + "="*60)
    print("SPATIAL DEBUG INFO")
    print("="*60)

    print(f"\nGripper: pos={gripper_pos}, closed={gripper_closed}")

    print("\nBlock positions:")
    for name, pos in sorted(positions.items()):
        print(f"  {name.upper()}: {pos}")

    print("\nTable height checks:")
    for name, pos in sorted(positions.items()):
        expected = TABLE_HEIGHT + BLOCK_HALF_HEIGHT
        diff = abs(pos[2] - expected)
        on_table = is_on_table(pos)
        print(f"  {name.upper()}: z={pos[2]:.4f}, expected={expected:.4f}, diff={diff:.4f}, on_table={on_table}")

    print("\nPairwise 'on' relationships:")
    block_names = sorted(positions.keys())
    for i, name_a in enumerate(block_names):
        for name_b in block_names[i+1:]:
            pos_a = positions[name_a]
            pos_b = positions[name_b]

            xy_dist = np.linalg.norm(pos_a[:2] - pos_b[:2])
            z_diff = pos_a[2] - pos_b[2]

            on_ab = is_on(pos_a, pos_b)
            on_ba = is_on(pos_b, pos_a)

            if on_ab or on_ba or xy_dist < 0.05:  # Show close blocks
                print(f"  {name_a.upper()}-{name_b.upper()}: xy_dist={xy_dist:.4f}, z_diff={z_diff:.4f}")
                if on_ab:
                    print(f"    -> {name_a.upper()} is ON {name_b.upper()}")
                if on_ba:
                    print(f"    -> {name_b.upper()} is ON {name_a.upper()}")

    print("="*60 + "\n")


if __name__ == "__main__":
    print("Symbolic Abstraction Module - Person 2")
    print("This module should be imported and used with Genesis scenes.")
    print("\nExample usage:")
    print("  from symbolic_abstraction import abstract_state, visualize_predicates")
    print("  predicates = abstract_state(scene, robot, blocks_state)")
    print("  visualize_predicates(predicates)")
