#!/usr/bin/env python3
"""
Unified TAMP Demo for All Goals

Supports:
- Goals 1-3: Simple block stacking (6 blocks)
- Goal 4: Two-structure building (18 blocks: yellow cross + green square)

Usage:
    python3 demo.py --goal 1          # Single tower
    python3 demo.py --goal 4          # Two structures (batch execution)
"""

import argparse
import numpy as np
import genesis as gs
from scenes import create_scene_6blocks, create_scene_stacked, create_scene_goal4_initial
from robot_adapter import RobotAdapter
from symbolic_abstraction import abstract_state, visualize_predicates
from task_planner import plan_symbolic

BLOCK_SIZE = 0.04


def print_block_positions(BlocksState, goal_id=1, label="[BLOCK POS]"):
    """Print block positions for debugging. Adapts to goal type."""
    print(f"\n{label}")

    if goal_id in [4, 41, 42]:
        # Goal 4: 18 blocks (y1-y12, g1-g6)
        yellow_blocks = [f"y{i}" for i in range(1, 13)]
        green_blocks = [f"g{i}" for i in range(1, 7)]

        print("Yellow blocks:")
        for name in yellow_blocks:
            if name in BlocksState:
                obj = BlocksState[name]
                pos = obj.get_pos()
                try:
                    pos = pos.cpu().numpy()
                except:
                    pos = np.array(pos, dtype=float)
                print(f"  {name.upper()} @ {pos}")

        print("Green blocks:")
        for name in green_blocks:
            if name in BlocksState:
                obj = BlocksState[name]
                pos = obj.get_pos()
                try:
                    pos = pos.cpu().numpy()
                except:
                    pos = np.array(pos, dtype=float)
                print(f"  {name.upper()} @ {pos}")
    else:
        # Goals 1-3: 6 blocks (b, c, g, m, r, y)
        for name in ["b", "c", "g", "m", "r", "y"]:
            if name in BlocksState:
                obj = BlocksState[name]
                pos = obj.get_pos()
                try:
                    pos = pos.cpu().numpy()
                except:
                    pos = np.array(pos, dtype=float)
                print(f"  {name.upper()} @ {pos}")
    print()


def execute_action(franka, scene, BlocksState, action):
    """Execute a single action with support for all goal types."""
    name = action[0]
    args = action[1:]

    print(f"\n[EXEC] ▶ Action: {action}")

    # Normalize action name (handle both "PICK-UP" and "PICKUP" formats)
    name_normalized = name.replace("-", "")

    if name_normalized == "PICKUP":
        blk = args[0]
        obj = BlocksState[blk]
        pos = obj.get_pos().cpu().numpy()

        print(f"[EXEC][PICK] {blk} @ {pos}")
        franka.pick(pos, obj=obj)
        return True

    elif name_normalized == "PUTDOWN":
        blk = args[0]
        obj = BlocksState[blk]

        # Find a safe PUTDOWN position away from existing blocks
        # Collect positions of all blocks except the one being placed
        other_positions = []
        for name, block_obj in BlocksState.items():
            if name != blk:
                try:
                    link = block_obj.links[0]
                    geom = link.geoms[0]
                    pos = geom.get_pos().cpu().numpy()
                    other_positions.append(pos[:2])  # XY only
                except:
                    pass

        # Try candidate positions, pick first one far enough from all blocks
        candidates = [
            np.array([0.65, 0.15, 0.05]),   # Right side, offset in Y
            np.array([0.65, -0.15, 0.05]),  # Right side, other Y direction
            np.array([0.40, 0.15, 0.05]),   # Left side, offset in Y
            np.array([0.40, -0.15, 0.05]),  # Left side, other Y direction
            np.array([0.55, 0.20, 0.05]),   # Center, far in +Y
            np.array([0.55, -0.20, 0.05]),  # Center, far in -Y
        ]

        min_safe_distance = 0.12  # 12cm minimum separation (prevent accidental stacking)
        target = candidates[0]  # Default fallback

        for candidate in candidates:
            safe = True
            for other_xy in other_positions:
                dist = np.linalg.norm(candidate[:2] - other_xy)
                if dist < min_safe_distance:
                    safe = False
                    break
            if safe:
                target = candidate
                break

        print(f"[EXEC][PUTDOWN] {blk} at {target} (checked {len(other_positions)} blocks)")

        franka.place(target, obj=obj)
        return True

    elif name_normalized == "STACK":
        block_top = args[0]
        block_bottom = args[1]

        top_obj = BlocksState[block_top]
        bottom_obj = BlocksState[block_bottom]

        bottom_link = bottom_obj.links[0]
        bottom_geom = bottom_link.geoms[0]
        bottom_pos = bottom_geom.get_pos().cpu().numpy()

        place_pos = bottom_pos.copy()
        place_pos[2] += BLOCK_SIZE

        print(f"[EXEC][STACK] {block_top} on {block_bottom} @ {place_pos}")
        franka.place(place_pos, obj=top_obj)
        return True

    elif name_normalized == "UNSTACK":
        blk = args[0]
        obj = BlocksState[blk]
        pos = obj.get_pos().cpu().numpy()

        print(f"[EXEC][UNSTACK] {blk} @ {pos}")
        franka.pick(pos, obj=obj)
        return True

    elif name_normalized == "PICKUPAT":
        # Goal 4: Pick up block from specific position
        blk = args[0]
        pos_name = args[1]
        obj = BlocksState[blk]
        pos = obj.get_pos().cpu().numpy()

        print(f"[EXEC][PICKUP-AT] {blk} from position {pos_name} @ {pos}")
        franka.pick(pos, obj=obj)
        return True

    elif name_normalized == "UNSTACKAT":
        # Goal 4: Unstack block from another at specific position
        blk = args[0]
        bottom_blk = args[1]
        pos_name = args[2]
        obj = BlocksState[blk]
        pos = obj.get_pos().cpu().numpy()

        print(f"[EXEC][UNSTACK-AT] {blk} from {bottom_blk} at position {pos_name} @ {pos}")
        franka.pick(pos, obj=obj)
        return True

    elif name_normalized == "PUTDOWNAT":
        # Goal 4: Place block at specific position
        blk = args[0]
        pos_name = args[1]
        obj = BlocksState[blk]

        # Get target coordinates from position name
        try:
            from goal4_config import get_position_coords
            target = np.array(get_position_coords(pos_name))
            print(f"[EXEC][PUTDOWN-AT] {blk} at position {pos_name} → {target}")
            franka.place(target, obj=obj)
            return True
        except ImportError:
            print(f"[EXEC] ERROR: goal4_config not available for PUTDOWN-AT")
            return False
        except KeyError:
            print(f"[EXEC] ERROR: Unknown position {pos_name}")
            return False

    elif name_normalized == "STACKAT":
        # Goal 4: Stack block on another at specific position
        # Signature: (stack-at ?x ?y ?p-bottom ?p-top)
        block_top = args[0]
        block_bottom = args[1]
        pos_bottom = args[2]  # Position of bottom block
        pos_top = args[3]     # Position where top block will be

        top_obj = BlocksState[block_top]
        bottom_obj = BlocksState[block_bottom]

        # Get bottom block's actual position (should be at pos_bottom)
        bottom_link = bottom_obj.links[0]
        bottom_geom = bottom_link.geoms[0]
        bottom_pos = bottom_geom.get_pos().cpu().numpy()

        # Stack on top (one block height above)
        place_pos = bottom_pos.copy()
        place_pos[2] += BLOCK_SIZE

        print(f"[EXEC][STACK-AT] {block_top} on {block_bottom} at bottom={pos_bottom}, top={pos_top} → {place_pos}")
        franka.place(place_pos, obj=top_obj)
        return True

    print(f"[EXEC] Unknown action {action}")
    return False


def run_simple_goals(scene, franka, BlocksState, goal_id, max_iterations=20):
    """
    Execute Goals 1-3 with single-action execution per iteration.

    Args:
        scene: Genesis scene
        franka: RobotAdapter instance
        BlocksState: Dictionary of block entities
        goal_id: Goal identifier (1, 2, or 3)
        max_iterations: Maximum planning iterations
    """
    print("\n" + "=" * 80)
    print(f"GOAL {goal_id} DEMO - Simple Block Stacking")
    print("=" * 80)
    print(f"Max iterations: {max_iterations}")
    print("=" * 80)

    # Track recent actions to detect loops
    recent_actions = []
    loop_detection_window = 6

    for step_idx in range(max_iterations):
        print("\n" + "-" * 80)
        print(f"Iteration {step_idx}")
        print("-" * 80)

        # 1. Symbolic abstraction
        preds = abstract_state(scene, franka, BlocksState, goal_id=goal_id)
        visualize_predicates(preds)
        print_block_positions(BlocksState, goal_id=goal_id, label=f"[BLOCK POS AFTER STEP {step_idx}]")

        # 2. Task planning
        try:
            plan = plan_symbolic(preds, goal_id=goal_id)
        except RuntimeError as e:
            print(f"[task_planner] ERROR during planning: {e}")
            break

        # 3. Check if goal reached
        if not plan:
            print("\n[INFO] ✓ GOAL REACHED!")
            print("=" * 80)
            break

        # 4. Display plan
        print("\n[TASK PLAN]")
        for i, step in enumerate(plan):
            print(f"  {i}: {step}")

        # 5. Detect action loops (same action repeating CONSECUTIVELY)
        action = plan[0]
        recent_actions.append(action)
        if len(recent_actions) > loop_detection_window:
            recent_actions.pop(0)

        # Check if we're in a TRUE loop: same action appearing consecutively 3+ times
        # This allows legitimate recovery (same action with different world states)
        if len(recent_actions) >= 3:
            # Check last 3 actions are identical (consecutive repetition = true loop)
            if (recent_actions[-1] == recent_actions[-2] == recent_actions[-3]):
                print(f"\n[WARNING] Detected infinite loop: same action 3 times consecutively")
                print(f"[WARNING] Recent actions: {recent_actions[-3:]}")
                print("[INFO] Stopping execution to avoid infinite loop.")
                print("=" * 80)
                break

        # 6. Execute ONLY the first action
        print(f"\n[EXEC-STEP {step_idx}.0] ▶ {action}")

        # Extract action info
        action_name = action[0]
        action_args = action[1:]
        action_name_normalized = action_name.replace("-", "")

        # Store positions before action for validation
        positions_before = {name: obj.get_pos().cpu().numpy().copy()
                          for name, obj in BlocksState.items()}

        ok = execute_action(franka, scene, BlocksState, action)

        if not ok:
            print(f"[EXEC] Action failed: {action}. Stopping execution loop.")
            break

        # 7. Update physics (allow blocks to settle)
        # Use more steps to handle tower instability and prevent collapses
        # Goal 2 needs extra settling for its 5-block tower
        if goal_id == 2:
            settling_steps = 200  # 5-block tower needs much more settling to prevent collapse
        elif goal_id in [1, 3]:
            settling_steps = 100
        else:
            settling_steps = 60
        try:
            for _ in range(settling_steps):
                scene.step()
        except Exception as e:
            if "Viewer closed" in str(e):
                print("\n[INFO] Viewer was closed. Exiting demo.")
                return
            raise

        # 8. Validate placement (detect if blocks fell/moved unexpectedly)
        if action_name_normalized in ["STACK", "STACKAT"]:
            block_name = action_args[0]
            pos_after = BlocksState[block_name].get_pos().cpu().numpy()
            pos_before = positions_before[block_name]
            displacement = np.linalg.norm(pos_after - pos_before)

            # If block moved more than 0.5m during physics, something went wrong
            if displacement > 0.5:
                print(f"\n[WARNING] Block {block_name} moved {displacement:.2f}m during physics simulation!")
                print(f"[WARNING] This suggests placement failure or physics instability.")
                print(f"[WARNING] Before: {pos_before}, After: {pos_after}")

    print("\n[INFO] Demo complete.")


def run_goal4(scene, franka, BlocksState):
    """
    Execute Goal 4 with batch execution and phase decomposition.

    Uses sequential phases:
    - Phase 1 (Goal 41): Yellow cross tower (12 blocks)
    - Phase 2 (Goal 42): Green hollow square (6 blocks)

    Args:
        scene: Genesis scene
        franka: RobotAdapter instance
        BlocksState: Dictionary of 18 block entities
    """
    print("\n" + "=" * 80)
    print("GOAL 4 DEMO - Task and Motion Planning")
    print("=" * 80)
    print("\nTarget structures:")
    print("  - Yellow cross/plus tower (12 blocks)")
    print("  - Green hollow square (6 blocks)")
    print("\n" + "=" * 80)

    # Phase configuration (data-driven, not hardcoded)
    GOAL4_PHASES = [
        {
            "goal_id": 41,
            "name": "Yellow Cross Tower",
            "description": "12 blocks in cross pattern, 2 layers",
            "batch_size": 1,  # Small batch for tall structure
            "max_iterations": 25,
        },
        {
            "goal_id": 42,
            "name": "Green Hollow Square",
            "description": "6 blocks in 3×3 hollow square, 1 layer",
            "batch_size": 1,  # Large batch for flat structure
            "max_iterations": 25,
        },
    ]

    # Execute each phase sequentially
    for phase_idx, phase_config in enumerate(GOAL4_PHASES, start=1):
        goal_id = phase_config["goal_id"]
        phase_name = phase_config["name"]
        batch_size = phase_config["batch_size"]
        max_iterations = phase_config["max_iterations"]

        print("\n" + "=" * 80)
        print(f"PHASE {phase_idx}/{len(GOAL4_PHASES)}: {phase_name}")
        print(f"  Goal ID: {goal_id}")
        print(f"  Description: {phase_config['description']}")
        print(f"  Batch size: {batch_size} actions/iteration")
        print("=" * 80)

        # Iterative TAMP loop for this phase
        for step_idx in range(max_iterations):
            print("\n" + "-" * 80)
            print(f"{phase_name.upper()} - Iteration {step_idx}")
            print("-" * 80)

            # 1. Symbolic abstraction
            preds = abstract_state(scene, franka, BlocksState, goal_id=goal_id)
            visualize_predicates(preds, title=f"{phase_name} state - step {step_idx}")

            # 2. Task planning
            try:
                plan = plan_symbolic(preds, goal_id=goal_id, problem_name=f"goal{goal_id}_step{step_idx}")
            except RuntimeError as e:
                print(f"\n[task_planner] ERROR during planning: {e}")
                print(f"\n[INFO] Planning failed for {phase_name}. Stopping execution.")
                break

            # 3. Check if goal achieved
            if not plan:
                print(f"\n[INFO] ✓ {phase_name} COMPLETE!")
                if phase_idx == len(GOAL4_PHASES):
                    print("\n" + "=" * 80)
                    print("🎉 GOAL 4 FULLY COMPLETED! 🎉")
                    print("=" * 80)
                break

            # 4. Display plan
            print(f"\n[TASK PLAN] ({len(plan)} actions)")
            for i, step in enumerate(plan[:5]):
                print(f"  {i}: {step}")
            if len(plan) > 5:
                print(f"  ... and {len(plan) - 5} more")

            # 5. Execute batch of actions
            actions_to_execute = plan[:batch_size]
            print(f"\n[BATCH EXECUTION] Executing {len(actions_to_execute)} actions...")

            execution_failed = False
            for action_idx, action in enumerate(actions_to_execute):
                print(f"\n[EXEC-STEP {step_idx}.{action_idx}] Executing: {action}")
                ok = execute_action(franka, scene, BlocksState, action)

                if not ok:
                    print(f"\n[EXEC] ❌ Action failed: {action}")
                    print(f"[INFO] Stopping execution for {phase_name}.")
                    execution_failed = True
                    break

                # Update physics simulation (reduced from 20 to 10 for faster execution)
                for _ in range(10):
                    scene.step()

            # If execution failed, stop this phase
            if execution_failed:
                break

    print("\n[INFO] Demo complete.")


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Unified TAMP Demo for All Goals")
    parser.add_argument(
        "--goal",
        type=int,
        default=1,
        choices=[1, 2, 3, 4],
        help="Goal ID (1-3: simple stacking, 4: two structures)"
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="gpu",
        choices=["cpu", "gpu"],
        help="Genesis backend (cpu or gpu)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=20,
        help="Maximum iterations for simple goals (1-3)"
    )
    parser.add_argument(
        "--scene",
        type=int,
        default=1,
        choices=[1, 2],
        help="Initial scene configuration for Goals 1-3 (1: scattered, 2: stacked tower)"
    )
    args = parser.parse_args()

    # Initialize Genesis
    backend = gs.gpu if args.backend == "gpu" else gs.cpu
    gs.init(backend=backend, logging_level='Warning', logger_verbose_time=False)
    print(f"\n[INFO] Genesis initialized (backend={args.backend})")

    # Create scene based on goal and scene type
    if args.goal == 4:
        scene, franka_raw, BlocksState = create_scene_goal4_initial()
    else:
        # Goals 1-3: support both initial scenes
        if args.scene == 1:
            print(f"[INFO] Using Scene 1: All blocks scattered on table")
            scene, franka_raw, BlocksState = create_scene_6blocks()
        else:  # args.scene == 2
            print(f"[INFO] Using Scene 2: Six blocks pre-stacked in tower")
            scene, franka_raw, BlocksState = create_scene_stacked()

    # Wrap robot in adapter
    franka = RobotAdapter(franka_raw, scene)

    # Set robot control parameters
    franka.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    franka.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))
    franka.set_dofs_force_range(
        np.array([-87, -87, -87, -87, -12, -12, -12, -100, -100]),
        np.array([87, 87, 87, 87, 12, 12, 12, 100, 100])
    )

    print(f"[INFO] Scene + robot ready")
    print(f"[INFO] Total blocks: {len(BlocksState)}")
    print()

    # Execute based on goal type
    if args.goal == 4:
        run_goal4(scene, franka, BlocksState)
    else:
        run_simple_goals(scene, franka, BlocksState, goal_id=args.goal, max_iterations=args.max_iterations)

    # Keep viewer open
    print("\n[INFO] Keeping viewer open. Press Ctrl+C to exit.")
    try:
        while True:
            scene.step()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
