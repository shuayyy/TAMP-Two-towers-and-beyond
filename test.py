import genesis as gs
import numpy as np
from scenes import create_scene_6blocks
from robot_adapter import RobotAdapter

gs.init(backend=gs.gpu, logging_level='Warning', logger_verbose_time=False)
np.set_printoptions(suppress=True, precision=4)

scene, franka_raw, BlocksState = create_scene_6blocks()
franka = RobotAdapter(franka_raw, scene)

cube_r = BlocksState["r"]
cube_r_pos = cube_r.get_pos().cpu().numpy()

pick_pos = cube_r_pos
print("Pick position:", pick_pos)

place_pos = np.array([0.45, 0.1, 0.3])
quat = np.array([0, 1, 0, 0])

print("\n Starting PICK\n")
franka.pick(pick_pos, quat)

for _ in range(100):
    scene.step()

print("\n Starting PLACE\n")
franka.place(place_pos, quat)
