#!/usr/bin/env python3
"""
Goal 4 Demo - TAMP for Two Structures

Demonstrates complete Task and Motion Planning for Goal 4:
- Yellow cross/plus tower (12 blocks)
- Green hollow square (6 blocks)

Uses:
- Scattered initial scene
- Position-aware symbolic abstraction
- PDDL planning with positions
- Position-aware motion execution
"""

import numpy as np
import genesis as gs
from scenes import create_scene_goal4_initial
from robot_adapter import RobotAdapter
from symbolic_abstraction import abstract_state, visualize_predicates
from task_planner import plan_symbolic

BLOCK_SIZE = 0.04

def print_block_positions(BlocksState, label="[BLOCK POS]"):
    """Debug utility to print all block positions."""
    print(f"\n{label}")
    # Goal 4 has 18 blocks: y1-y12, g1-g6
    yellow_blocks = [f"y{i}" for i in range(1, 13)]
    green_blocks = [f"g{i}" for i in range(1, 7)]

    print("Yellow blocks:")
    for name in yellow_blocks:
        obj = BlocksState[name]
        pos = obj.get_pos()
        try:
            pos = pos.cpu().numpy()
        except:
            pos = np.array(pos, dtype=float)
        print(f"  {name.upper()} @ {pos}")

    print("Green blocks:")
    for name in green_blocks:
        obj = BlocksState[name]
        pos = obj.get_pos()
        try:
            pos = pos.cpu().numpy()
        except:
            pos = np.array(pos, dtype=float)
        print(f"  {name.upper()} @ {pos}")
    print()


def execute_action(franka, scene, BlocksState, action):
    """Execute a single action with Goal 4 support."""
    name = action[0]
    args = action[1:]

    print(f"\n[EXEC] ▶ Action: {action}")

    if name == "PICKUP":
        blk = args[0]
        obj = BlocksState[blk]
        pos = obj.get_pos().cpu().numpy()

        print(f"[EXEC][PICK] {blk} @ {pos}")
        franka.pick(pos, obj=obj)
        return True

    elif name == "PUTDOWN":
        blk = args[0]
        obj = BlocksState[blk]

        target = np.array([0.55, 0.0, 0.05])
        print(f"[EXEC][PUTDOWN] {blk} at {target}")

        franka.place(target, obj=obj)
        return True

    elif name == "STACK":
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

    elif name == "UNSTACK":
        blk = args[0]
        obj = BlocksState[blk]
        pos = obj.get_pos().cpu().numpy()

        print(f"[EXEC][UNSTACK] {blk} @ {pos}")
        franka.pick(pos, obj=obj)
        return True

    elif name == "PICKUP-AT":
        # Goal 4: Pick up block from specific position
        blk = args[0]
        pos_name = args[1]
        obj = BlocksState[blk]
        pos = obj.get_pos().cpu().numpy()

        print(f"[EXEC][PICKUP-AT] {blk} from position {pos_name} @ {pos}")
        franka.pick(pos, obj=obj)
        return True

    elif name == "UNSTACK-AT":
        # Goal 4: Unstack block from another at specific position
        blk = args[0]
        bottom_blk = args[1]
        pos_name = args[2]
        obj = BlocksState[blk]
        pos = obj.get_pos().cpu().numpy()

        print(f"[EXEC][UNSTACK-AT] {blk} from {bottom_blk} at position {pos_name} @ {pos}")
        franka.pick(pos, obj=obj)
        return True

    elif name == "PUTDOWN-AT":
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

    elif name == "STACK-AT":
        # Goal 4: Stack block on another at specific position
        block_top = args[0]
        block_bottom = args[1]
        pos_name = args[2]

        top_obj = BlocksState[block_top]
        bottom_obj = BlocksState[block_bottom]

        # Get bottom block's actual position (should be at pos_name)
        bottom_link = bottom_obj.links[0]
        bottom_geom = bottom_link.geoms[0]
        bottom_pos = bottom_geom.get_pos().cpu().numpy()

        # Stack on top (one block height above)
        place_pos = bottom_pos.copy()
        place_pos[2] += BLOCK_SIZE

        print(f"[EXEC][STACK-AT] {block_top} on {block_bottom} at {pos_name} → {place_pos}")
        franka.place(place_pos, obj=top_obj)
        return True

    print(f"[EXEC] Unknown action {action}")
    return False


if __name__ == "__main__":
    print("=" * 80)
    print("GOAL 4 DEMO - Task and Motion Planning")
    print("=" * 80)
    print("\nTarget structures:")
    print("  - Yellow cross/plus tower (12 blocks)")
    print("  - Green hollow square (6 blocks)")
    print("\n" + "=" * 80)

    # Initialize Genesis
    gs.init(backend=gs.cpu, logging_level='Warning', logger_verbose_time=False)
    print("\n[INFO] Genesis initialized")

    # Create scattered initial scene
    scene, franka_raw, BlocksState = create_scene_goal4_initial()
    franka = RobotAdapter(franka_raw, scene)

    # Set robot control parameters
    franka.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    franka.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))
    franka.set_dofs_force_range(
        np.array([-87, -87, -87, -87, -12, -12, -12, -100, -100]),
        np.array([87, 87, 87, 87, 12, 12, 12, 100, 100])
    )

    print("[INFO] Scene + robot ready")
    print(f"[INFO] Total blocks: {len(BlocksState)}")
    print()

    # TAMP loop
    MAX_STEPS = 50  # Limit iterations for Goal 4 (many blocks)

    for step_idx in range(MAX_STEPS):
        print("\n" + "=" * 80)
        print(f"TAMP ITERATION {step_idx}")
        print("=" * 80)

        # 1. Symbolic abstraction with Goal 4 position detection
        preds = abstract_state(scene, franka, BlocksState, goal_id=4)
        visualize_predicates(preds, title=f"State after step {step_idx}")

        # Uncomment to see detailed positions
        # print_block_positions(BlocksState, label=f"[BLOCK POS AFTER STEP {step_idx}]")

        # 2. Task planning for Goal 4
        try:
            plan = plan_symbolic(preds, goal_id=4, problem_name=f"goal4_step{step_idx}")
        except RuntimeError as e:
            print(f"\n[task_planner] ERROR during planning: {e}")
            print("\n[INFO] Planning failed. Stopping execution.")
            break

        if not plan:
            print("\n[INFO] ✓ Planner returned empty plan — GOAL REACHED!")
            print("\n" + "=" * 80)
            print("GOAL 4 COMPLETED!")
            print("=" * 80)
            visualize_predicates(preds, title="FINAL STATE")
            break

        print(f"\n[TASK PLAN] ({len(plan)} actions)")
        for i, step in enumerate(plan[:5]):  # Show first 5
            print(f"  {i}: {step}")
        if len(plan) > 5:
            print(f"  ... and {len(plan) - 5} more")

        # 3. Execute batch of actions (up to 10) before replanning
        ACTIONS_PER_BATCH = 10
        actions_to_execute = plan[:ACTIONS_PER_BATCH]

        print(f"\n[BATCH EXECUTION] Executing {len(actions_to_execute)} actions before replanning...")

        for action_idx, action in enumerate(actions_to_execute):
            print(f"\n[EXEC-STEP {step_idx}.{action_idx}] Executing: {action}")
            ok = execute_action(franka, scene, BlocksState, action)

            if not ok:
                print(f"\n[EXEC] ❌ Action failed: {action}")
                print("[INFO] Stopping execution loop.")
                break

            # Let physics settle (reduced for speed)
            for _ in range(20):
                scene.step()
        else:
            # All actions in batch succeeded, continue to next iteration
            continue

        # If we broke out of action loop (failure), break outer loop too
        break

    else:
        # Reached MAX_STEPS
        print("\n" + "=" * 80)
        print(f"WARNING: Reached maximum iterations ({MAX_STEPS})")
        print("=" * 80)
        print("\nFinal state:")
        preds = abstract_state(scene, franka, BlocksState, goal_id=4)
        visualize_predicates(preds, title="STATE AT ITERATION LIMIT")

    print("\n[INFO] Demo complete. Close viewer to exit.")

    # Keep viewer open
    try:
        while True:
            scene.step()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
