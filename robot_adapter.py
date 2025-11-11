"""RobotAdapter: a thin adapter around a Genesis robot entity.

Purpose:
- Normalize and centralize robot API access so higher-level modules can
  call a stable interface. By default the adapter forwards unknown
  attributes to the underlying genesis robot, so existing code that
  expects the raw robot still works when passed an adapter.

Usage:
    adapter = RobotAdapter(raw_robot, scene)
    adapter.get_qpos()  # forwarded
    adapter.set_qpos(q) # forwarded

This is intentionally minimal: it implements __getattr__ forwarding and
adds an explicit .robot property to access the raw object when needed.
"""
from typing import Any
import time
import numpy as np
from genesis.utils.misc import tensor_to_array ## TODO : use this utility for conversions

class RobotAdapter:
    def __init__(self, robot: Any, scene: Any = None):
        """Wrap a genesis robot entity.

        Args:
            robot: the raw genesis robot entity (e.g., returned from scene.add_entity)
            scene: optional scene reference (some callers use scene alongside robot)
        """
        self.robot = robot
        self.scene = scene

    def __getattr__(self, name: str) -> Any:
        """Forward unknown attribute access to the underlying robot.

        This makes the adapter nearly transparent by default so existing
        code can keep using the usual robot API.
        """
        return getattr(self.robot, name)

    # Optional: convenience explicit aliases (delegation examples). Keep these
    # so callers can rely on these names being present even if we later
    # enrich/transform arguments.
    def get_pos(self):
        return self.robot.get_pos()

    def set_pos(self, pos):
        return self.robot.set_pos(pos)

    def get_qpos(self):
        return self.robot.get_qpos()

    def set_qpos(self, qpos):
        return self.robot.set_qpos(qpos)

    def control_dofs_position(self, *args, **kwargs):
        return self.robot.control_dofs_position(*args, **kwargs)

    def control_dofs_force(self, *args, **kwargs):
        return self.robot.control_dofs_force(*args, **kwargs)

    def get_link(self, *args, **kwargs):
        return self.robot.get_link(*args, **kwargs)

    def inverse_kinematics(self, *args, **kwargs):
        return self.robot.inverse_kinematics(*args, **kwargs)

    def detect_collision(self, *args, **kwargs):
        return self.robot.detect_collision(*args, **kwargs)
    

    ###Planning interface 
    def plan_path(self, *args, **kwargs):
        """
        Using PlannerInterface for motion planning (in planning.py)
        """
        from planning import PlannerInterface

        print("[DEBUG][RobotAdapter] plan_path() called")

        planner_interface = PlannerInterface(self.robot, self.scene)
        print("[DEBUG][RobotAdapter] Forwarding to PlannerInterface.plan_path()")
        waypoints = planner_interface.plan_path(*args, **kwargs)
        print(f"[DEBUG][RobotAdapter] OMPL returned {len(waypoints)} waypoints")
        return waypoints
    ###Planning interface 

    ##DEBUG UTILS
    def print_ee_pose(self, string_label=""):
        """Print current end-effector (ee) position and orientation."""
        ee_link = self.get_link("hand")
        ee_pos = ee_link.get_pos().cpu().numpy()
        ee_quat = ee_link.get_quat().cpu().numpy()
        print(f"\n[POSE] {string_label}")
        print(f"  Position : {np.round(ee_pos, 4)}")
        print(f"  Quaternion: {np.round(ee_quat, 4)}")
    ##DEBUG UTILS
    
    ##GRIPPER
    def open_gripper(self, open_pos=0.04, steps=20):
        self.print_ee_pose("Before open_gripper()")
        qpos = self.get_qpos()
        qpos[-2:] = open_pos
        self.control_dofs_position(qpos)
        for _ in range(steps):
            self.scene.step()
        self.print_ee_pose("After open_gripper()")

    def close_gripper(self, close_pos=0.0, steps=20):
        self.print_ee_pose("Before close_gripper()")
        qpos = self.get_qpos()
        qpos[-2:] = close_pos
        self.control_dofs_position(qpos)
        for _ in range(steps):
            self.scene.step()
        self.print_ee_pose("After close_gripper()")
    ##GRIPPER

    """ TODO : TESTED WHILE IGNORING COLLISIONS ,
            NEED TO ADD IMPLEMENT WITH COLLISIONS"""
    
    """ TODO : IMPLEMENT ATTACH / DETACH OBJECT FOR GRASPING  """

    ##PANDA MOTION CONTROL
    def move_to_pose(self,qpos_goal, steps=300): 
        """
        Plan and execute path using OMPL' planner.
        """
        self.print_ee_pose("Before move_to_pose()")
        qpos_start = self.get_qpos()
        path  = self.plan_path(
            qpos_goal=qpos_goal,
            num_waypoints=steps,
        )
        for waypoint in path:
            self.control_dofs_position(waypoint)
            self.scene.step()
        self.print_ee_pose("After move_to_pose()")
        time.sleep(0.1)

    def pre_grasp_pose(self, pos, quat, approach_dir=np.array([0, 0, 1]), offset=0.10, steps=300):
        """
        Move the end-effector to a pre-grasp position offset from the object
        along the specified approach direction.
        """
        self.print_ee_pose("Before pre_grasp_pose()")
        # pre-grasp position
        pregrasp_pos = pos + approach_dir * offset
        print(f"[DEBUG] Pre-grasp position: {pregrasp_pos}")

        # IK for pre-grasp position
        qpos_pregrasp = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=pregrasp_pos,
            quat=quat,
        )

        self.move_to_pose(qpos_pregrasp, steps=steps)
        self.print_ee_pose("After pre_grasp_pose()")

    def post_grasp_pose(self, pos, quat, approach_dir=np.array([0, 0, -1]), offset=0.1, steps=300):
        """
        Move the end-effector away from the grasped object (opposite of approach direction).
        """
        self.print_ee_pose("Before post_grasp_pose()")
        # retreat position (opposite of pre-grasp)
        retreat_pos = pos - approach_dir * offset

        # IK for post-grasp position
        qpos_postgrasp = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=retreat_pos,
            quat=quat,
        )

        self.move_to_pose(qpos_postgrasp, steps=steps)
        self.print_ee_pose("After post_grasp_pose()")

    def pick(self, pos, quat = np.array([0, 1, 0, 0])):
        """
        Perform a pick operation: move to pre-grasp, open gripper, move to grasp,
        close gripper, and retreat to post-grasp position.
        """
        #ADJUST pos Z TO COMPENSATE GRIPPER OFFSET (~11 CM) 
        #TODO: Instead of hardcoding , compute from robot model
        pos[2] += 0.12

        self.print_ee_pose("Before pick()")
        self.pre_grasp_pose(pos, quat)
        self.open_gripper()
        self.move_to_pose(
            self.inverse_kinematics(
                link=self.get_link("hand"),
                pos=pos,
                quat=quat,
            )
        )
        self.close_gripper()
        self.post_grasp_pose(pos, quat)
        self.print_ee_pose("After pick()")

    def place(self, pos, quat = np.array([0, 1, 0, 0])):
        """
        Perform a place operation: move to pre-grasp above place position,
        move to place position, open gripper, and retreat to post-grasp position.
        """
        self.print_ee_pose("Before place()")
        self.move_to_pose(
            self.inverse_kinematics(
                link=self.get_link("hand"),
                pos=pos,
                quat=quat,
            )
        )
        self.open_gripper()
        self.post_grasp_pose(pos, quat)
        self.print_ee_pose("After place()")
    ##PANDA MOTION CONTROL


    # expose the raw object if callers need direct access
    @property
    def raw(self):
        return self.robot
