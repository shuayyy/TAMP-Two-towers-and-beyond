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

    preds = abstract_state(scene, franka, BlocksState)
    visualize_predicates(preds)

    plan = plan_symbolic(preds, goal_id=2)

    print("\n[TASK PLAN]")
    for i, step in enumerate(plan):
        print(f"  {i}: {step}")

    print_block_positions(BlocksState, label="[INIT BLOCK POS]")

    for action in plan:
        print(f"\n[EXEC] ▶ {action}")
        execute_action(franka, scene, BlocksState, action)

        for _ in range(80):
            scene.step()

    print("\n[INFO] Execution complete. Observing for 30 seconds...")
    t_end = time.time() + 30.0
    while time.time() < t_end:
        scene.step()
