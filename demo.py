#!/usr/bin/env python3

import numpy as np
import time
import genesis as gs

from scenes import create_scene_6blocks
from robot_adapter import RobotAdapter
from symbolic_abstraction import abstract_state, visualize_predicates
from task_planner import plan_symbolic

BLOCK_SIZE = 0.04

def print_block_positions(BlocksState, label="[BLOCK POS]"):
    import numpy as np
    print(f"\n{label}")
    for name in ["b", "c", "g", "m", "r", "y"]:
        obj = BlocksState[name]
        pos = obj.get_pos()
        try:
            pos = pos.cpu().numpy()
        except:
            pos = np.array(pos, dtype=float)
        print(f"  {name.upper()} @ {pos}")
    print()


def execute_action(franka, scene, BlocksState, action):
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
        bottom_pos  = bottom_geom.get_pos().cpu().numpy()

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

    print(f"[EXEC]  Unknown action {action}")
    return False


if __name__ == "__main__":

    gs.init(backend=gs.gpu, logging_level='Warning', logger_verbose_time=False)
    print("[INFO] Genesis initialized\n")

    scene, franka_raw, BlocksState = create_scene_6blocks()
    franka = RobotAdapter(franka_raw, scene)

    franka.set_dofs_kp(np.array([4500,4500,3500,3500,2000,2000,2000,100,100]))
    franka.set_dofs_kv(np.array([450,450,350,350,200,200,200,10,10]))
    franka.set_dofs_force_range(
        np.array([-87,-87,-87,-87,-12,-12,-12,-100,-100]),
        np.array([ 87, 87, 87, 87, 12, 12, 12, 100, 100])
    )

    print("[INFO] Scene + robot ready.\n")

    for step_idx in range(20):  
        preds = abstract_state(scene, franka, BlocksState)
        visualize_predicates(preds)
        print_block_positions(BlocksState, label=f"[BLOCK POS AFTER STEP {step_idx}]")

        try:
            plan = plan_symbolic(preds, goal_id=1)
        except RuntimeError as e:
            print(f"[task_planner] ERROR during planning: {e}")
            break

        if not plan:
            print("[INFO] Planner returned empty plan — assuming goal reached or unsolvable.")
            break

        print("\n[TASK PLAN]")
        for i, step in enumerate(plan):
            print(f"  {i}: {step}")

        # 3) Execute ONLY the first action of the new plan
        action = plan[0]
        print(f"\n[EXEC-STEP {step_idx}.0] ▶ {action}")
        ok = execute_action(franka, scene, BlocksState, action)
        if not ok:
            print(f"[EXEC] Action failed: {action}. Stopping execution loop.")
            break

        for _ in range(80):
            scene.step()
