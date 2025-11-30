#!/usr/bin/env python3
import numpy as np
import genesis as gs
from scenes import create_scene_6blocks
from robot_adapter import RobotAdapter

gs.init(backend=gs.gpu, logging_level='Warning', logger_verbose_time=False)  # or gs.cpu
np.set_printoptions(suppress=True, precision=4)

BLOCK_SIZE = 0.04  # one block height
quat_down  = np.array([0, 1, 0, 0])

scene, franka_raw, BlocksState = create_scene_6blocks()
franka = RobotAdapter(franka_raw, scene)

# pick 'r' and stack onto 'g'
top_name, base_name = "r", "g"
top  = BlocksState[top_name]
base = BlocksState[base_name]

def np_pos(obj):
    p = obj.get_pos()
    try: return p.cpu().numpy()
    except: return np.array(p, dtype=float)

pick_pos  = np_pos(top)
base_pos  = np_pos(base)
place_pos = base_pos.copy(); place_pos[2] += BLOCK_SIZE  # stack height

print("=== DEBUG: PICK and PLACE ===")
print("PICK POS:", pick_pos)
print("PLACE POS:", place_pos)
print("=== DEBUG: PICK and PLACE ===")

print(f"Pick {top_name} at {pick_pos}")
franka.pick(pick_pos, quat_down, obj=top)
for _ in range(120): scene.step()

print(f"Place {top_name} on {base_name} at {place_pos} (base_z={base_pos[2]:.4f} → target_z={place_pos[2]:.4f})")
franka.place(place_pos, quat_down, obj=top)
for _ in range(300): scene.step()
