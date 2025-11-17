"""
RobotAdapter: a thin adapter around a Genesis robot entity.

Now with:
  • move_to_pose(..., ignore_collisions=False)
  • attach_object / detach_object + auto hand-follow
  • pick(pos, quat, obj=None) / place(pos, quat, obj=None)
"""

from typing import Any, Optional
import time
import numpy as np
from genesis.utils.misc import tensor_to_array  # TODO: use this utility for conversions


class RobotAdapter:
    def __init__(self, robot: Any, scene: Any = None):
        """Wrap a genesis robot entity.

        Args:
            robot: the raw genesis robot entity (e.g., returned from scene.add_entity)
            scene: optional scene reference (some callers use scene alongside robot)
        """
        self.robot = robot
        self.scene = scene

        # --- grasp/attachment state ---
        self.attached_object = None
        self._attach_offset = None
        self._sync_cb = None

    # ------------------------------------------------------------------
    # Transparent forwarding
    # ------------------------------------------------------------------
    def __getattr__(self, name: str) -> Any:
        """Forward unknown attribute access to the underlying robot.

        This makes the adapter nearly transparent by default so existing
        code can keep using the usual robot API.
        """
        return getattr(self.robot, name)

    # Convenience wrappers (stable names)
    def get_pos(self): return self.robot.get_pos()
    def set_pos(self, pos): return self.robot.set_pos(pos)
    def get_qpos(self): return self.robot.get_qpos()
    def set_qpos(self, qpos): return self.robot.set_qpos(qpos)
    def control_dofs_position(self, *a, **kw): return self.robot.control_dofs_position(*a, **kw)
    def control_dofs_force(self, *a, **kw): return self.robot.control_dofs_force(*a, **kw)
    def get_link(self, *a, **kw): return self.robot.get_link(*a, **kw)
    def inverse_kinematics(self, *a, **kw): return self.robot.inverse_kinematics(*a, **kw)
    def detect_collision(self, *a, **kw): return self.robot.detect_collision(*a, **kw)

    # ------------------------------------------------------------------
    # Planning interface bridge
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Debug utils
    # ------------------------------------------------------------------
    def print_ee_pose(self, string_label=""):
        """Print current end-effector (ee) position and orientation."""
        ee_link = self.get_link("hand")
        ee_pos = ee_link.get_pos().cpu().numpy()
        ee_quat = ee_link.get_quat().cpu().numpy()
        print(f"\n[POSE] {string_label}")
        print(f"  Position : {np.round(ee_pos, 4)}")
        print(f"  Quaternion: {np.round(ee_quat, 4)}")

    # ------------------------------------------------------------------
    # Gripper
    # ------------------------------------------------------------------
    def open_gripper(self, open_pos=0.04, steps=20):
        self.print_ee_pose("Before open_gripper()")
        qpos = self.get_qpos()
        qpos[-2:] = open_pos
        self.control_dofs_position(qpos)
        for _ in range(steps):
            self.scene.step()
        self.print_ee_pose("After open_gripper()")

    def close_gripper(self, close_pos=0.0, steps=100):
        self.print_ee_pose("Before close_gripper()")
        qpos = self.get_qpos()
        qpos[-2:] = close_pos
        self.control_dofs_position(qpos)
        for _ in range(steps):
            self.scene.step()
        self.print_ee_pose("After close_gripper()")

    # ------------------------------------------------------------------
    # ATTACH / DETACH (virtual, version-agnostic)
    # ------------------------------------------------------------------
    def attach_object(self, obj):
        """Save hand→obj offset and start kinematic sync."""
        self.attached_object = obj
        hand = self.get_link("hand")
        hand_pos = hand.get_pos()
        obj_pos = obj.get_pos()
        try: hand_pos = hand_pos.cpu().numpy()
        except: pass
        try: obj_pos = obj_pos.cpu().numpy()
        except: pass
        offset = obj_pos - hand_pos
        offset[0] = 0.0   # lock X to hand
        offset[1] = 0.0   # lock Y to hand
        self._attach_offset = offset

        self._enable_sync()
        print("[ROBOT][ATTACH] attached; offset =", self._attach_offset)

    def detach_object(self):
        """Stop kinematic sync and clear state."""
        self._disable_sync()
        self.attached_object = None
        self._attach_offset = None
        print("[ROBOT][DETACH] detached")


    def _sync_attached_object(self):
        """Keep the attached object rigidly at the hand each sim step."""
        if self.attached_object is None or self._attach_offset is None:
            return
        hand = self.get_link("hand")
        hand_pos = hand.get_pos()
        hand_quat = hand.get_quat()
        try: hand_pos = hand_pos.cpu().numpy()
        except: pass
        try: hand_quat = hand_quat.cpu().numpy()
        except: pass
        target_pos = hand_pos + self._attach_offset
        self.attached_object.set_pos(target_pos)
        self.attached_object.set_quat(hand_quat)

    def _enable_sync(self):
        """Register a post-step callback (idempotent)."""
        if self._sync_cb is not None:
            return
        # Try common Genesis callback names; fall back to a simple wrapper
        if hasattr(self.scene, "add_post_step_callback"):
            self._sync_cb = self.scene.add_post_step_callback(self._sync_attached_object)
        elif hasattr(self.scene, "add_post_step_cb"):
            self._sync_cb = self.scene.add_post_step_cb(self._sync_attached_object)
        else:
            # Fallback: wrap scene.step() to always call sync after step
            orig_step = self.scene.step
            def step_wrapper(*args, **kwargs):
                r = orig_step(*args, **kwargs)
                self._sync_attached_object()
                return r
            self.scene.step = step_wrapper
            self._sync_cb = "wrapped"

    def _disable_sync(self):
        """Unregister post-step callback (idempotent)."""
        if self._sync_cb is None:
            return
        if self._sync_cb != "wrapped":
            if hasattr(self.scene, "remove_post_step_callback"):
                self.scene.remove_post_step_callback(self._sync_cb)
            elif hasattr(self.scene, "remove_post_step_cb"):
                self.scene.remove_post_step_cb(self._sync_cb)
        else:
            # If we wrapped scene.step(), we can’t easily restore the original here.
            # Safe to leave wrapped; sync is a no-op when no object is attached.
            pass
        self._sync_cb = None


    # ------------------------------------------------------------------
    # Motion
    # ------------------------------------------------------------------
    def move_to_pose(self, qpos_goal, steps=300, ignore_collisions=False):
        """Plan and execute path using OMPL planner."""
        self.print_ee_pose("Before move_to_pose()")

        qpos_start = self.get_qpos()

        # --- safety fallback: initialize if missing ---
        if not hasattr(self, "attached_geom_indices"):
            self.attached_geom_indices = []

        # --- auto ignore heuristic ---
        fingers = qpos_start[-2:]
        if hasattr(fingers, "cpu"):  # convert torch.Tensor → numpy
            fingers = fingers.detach().cpu().numpy()
        gripper_closed = np.all(fingers < 0.01)
        print(f"[DEBUG] attached_object: {self.attached_object}")
        # auto_ignore = (getattr(self, "attached_object", None) is not None)  #or gripper_closed
        # use_ignore = ignore_collisions or auto_ignore
        auto_ignore = False
        use_ignore = ignore_collisions
        print(f"[DEBUG] move_to_pose(): ignore_collisions={ignore_collisions}, auto_ignore={auto_ignore} => use_ignore={use_ignore}")

        if use_ignore:
            print("[DEBUG] Ignoring collisions during motion planning (grasp context).")
            from planning import PlannerInterface
            planner_interface = PlannerInterface(self.robot, self.scene)
            # planner_interface._is_ompl_state_valid = lambda s: True
            path = planner_interface.plan_path(
                qpos_goal=qpos_goal,
                qpos_start=qpos_start,
                num_waypoints=steps,
                attached_object=self.attached_object,
            )
        else:
            path = self.plan_path(qpos_goal=qpos_goal, num_waypoints=steps,attached_object=self.attached_object,)

        if len(path) == 0:
            print("[WARN] OMPL returned empty path; executing direct control to goal.")
            self.control_dofs_position(qpos_goal)
            for _ in range(100):
                self.scene.step()
            return

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
        pregrasp_pos = pos + approach_dir * offset
        print(f"[DEBUG] Pre-grasp position: {pregrasp_pos}")
        qpos_pregrasp = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=pregrasp_pos,
            quat=quat,
        )
        self.move_to_pose(qpos_pregrasp, steps=steps)
        self.print_ee_pose("After pre_grasp_pose()")

    def post_grasp_pose(self, pos, quat, approach_dir=np.array([0, 0, -1]), offset=0.10, steps=300):
        """
        Move the end-effector away from the grasped object (opposite of approach direction).
        """
        self.print_ee_pose("Before post_grasp_pose()")
        retreat_pos = pos - approach_dir * offset
        print(f"[DEBUG] Post-grasp position: {retreat_pos}")
        qpos_postgrasp = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=retreat_pos,
            quat=quat,
        )
        # If attached_object exists, collisions are ignored automatically inside move_to_pose
        self.move_to_pose(qpos_postgrasp, steps=steps)
        self.print_ee_pose("After post_grasp_pose()")

    # ------------------------------------------------------------------
    # High-level actions (obj is optional for backward compatibility)
    # ------------------------------------------------------------------
    def pick(self, pos, quat=np.array([0, 1, 0, 0]), obj: Optional[Any] = None):
        """
        Approach → open → descend → close → retreat.
        If obj is provided, it will be attached after closing the gripper.
        """
        # compensate for fingertip-to-EE offset (approx 12 cm)
        pos = np.array(pos, dtype=float)
        pos[2] += 0.12

        self.print_ee_pose("Before pick()")
        self.pre_grasp_pose(pos, quat)
        self.open_gripper()
        
        print("Move to pose called ", pos)  
        qpos_grasp = self.inverse_kinematics(link=self.get_link("hand"), pos=pos, quat=quat)
        self.move_to_pose(qpos_grasp, steps=200)
        self.close_gripper()

        # Attach if provided
        if obj is not None:
            print("[ROBOT][PICK] obj is None?" , obj is None)
            self.attach_object(obj)
            # print("[ROBOT][PICK] attached:", getattr(self, "attached_object", None))

        # Retreat up (auto ignores collisions if attached)
        qpos_retreat = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=pos + np.array([0, 0, 0.15]),
            quat=quat,
        )

        print("move to retreat pose called ", qpos_retreat)
        self.move_to_pose(qpos_retreat, steps=200)
        self.print_ee_pose("After pick()")

    def place(self, pos, quat=np.array([0, 1, 0, 0]), obj: Optional[Any] = None):
        """
        Move above → descend to exact target → detach → open → retreat.
        """
        self.print_ee_pose("Before place()")

        # 1) move 10 cm above target
        pos_above = pos.copy()
        # pos_above[1] += 0.011
        pos_above[2] += 0.075

        # >>> MINIMAL ADD: compensate grasp offset so cube centers correctly
        off = np.zeros(3)
        if self.attached_object is not None and self._attach_offset is not None:
            off = np.array(self._attach_offset, dtype=float)
        # <<<
        print("off :", off)

        print("pos :", pos)
        print("pos above:", pos_above - off)
        self.print_ee_pose("DEBUG CHECK")

        # >>> MINIMAL CHANGE: aim the HAND at (pos_above - off)
        q_above = self.inverse_kinematics(link=self.get_link("hand"),
                                        pos=pos_above - off,  # <— only change
                                        quat=quat)
        # <<<
        print("[DEBUG] GOAL POSITION, QPOS:", q_above)
        print("[DEBUG]")
        # ---- Move once ----
        self.move_to_pose(q_above, steps=200)
        self.print_ee_pose(" DEBUG CHECK")

        # ---- Iterative XY correction loop ----
        # ---- Iterative XY correction loop ----
        max_iters = 3
        for i in range(max_iters):
            hand = self.get_link("hand")
            ee_pos = hand.get_pos().cpu().numpy()
            target_pos = pos_above - off

            # Compute X and Y errors separately
            x_err = abs(ee_pos[0] - target_pos[0])
            y_err = abs(ee_pos[1] - target_pos[1])
            print(f"[DEBUG][CORRECTION {i}] X err: {x_err:.4f} | Y err: {y_err:.4f}")

            # Stop if both errors are within 5 mm
            if x_err <= 0.001 and y_err <= 0.001:
                print("[DEBUG][CORRECTION] Pose aligned within tolerance ✅")
                break

            # Otherwise, correct position
            target_pos[1] += 0.001
            q_fix = self.inverse_kinematics(link=hand, pos=target_pos, quat=quat)
            self.move_to_pose(q_fix, steps=80)

        self.print_ee_pose("[DEBUG] After XY correction")


        # (drop step intentionally skipped per your version)

        # 3) detach first (stop kinematic sync), then open gripper
        if obj is not None and obj is self.attached_object:
            self.detach_object()
        elif obj is None and self.attached_object is not None:
            self.detach_object()
        # print("[ROBOT][PLACE] detached; attached now:", getattr(self, "attached_object", None))

        self.open_gripper()

        # 4) retreat upward to avoid re-contact
        pos_retreat = pos.copy()
        pos_retreat[2] += 0.30
        q_retreat = self.inverse_kinematics(link=self.get_link("hand"), pos=pos_retreat, quat=quat)
        print("move to pose called ", pos_retreat)
        self.move_to_pose(q_retreat, steps=200)

        ##ADDED detach and open here
        

        self.print_ee_pose("After place()")



    # ------------------------------------------------------------------
    # Raw object access
    # ------------------------------------------------------------------
    @property
    def raw(self):
        return self.robot
