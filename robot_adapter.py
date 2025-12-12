"""
RobotAdapter: a thin adapter around a Genesis robot entity.

Features:
  • Transparent pass-through to underlying robot
  • OMPL motion planning bridge via PlannerInterface
  • move_to_pose(..., ignore_collisions=False)
  • Physics-based gripping (no kinematic attach/detach)
  • Logical attached_object for symbolic is_holding(...)
  • "Locked" fingers after closing (continuous grip in position mode)
  • Slower, smoother motions while grasping to reduce slip
  • Neighbor-aware place(): auto-rotates gripper by 90° about world Z
    depending on nearby blocks
  • pick(pos, quat, obj=None) / place(pos, quat, obj=None)
"""

from typing import Any, Optional, List
import numpy as np

from genesis.utils.misc import tensor_to_array  # robust tensor → np converter


def _to_np(x) -> np.ndarray:
    """Safely convert Genesis / torch tensors or arrays to np.ndarray."""
    try:
        return tensor_to_array(x)
    except Exception:
        return np.asarray(x, dtype=float)


# ======================================================================
# Quaternion / rotation helpers (W, X, Y, Z convention)
# ======================================================================

def quat_mul_wxyz(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Hamilton product of two quaternions in [w, x, y, z] format."""
    q1 = np.asarray(q1, dtype=float)
    q2 = np.asarray(q2, dtype=float)
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2

    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    return np.array([w, x, y, z], dtype=float)


def quat_conj_wxyz(q: np.ndarray) -> np.ndarray:
    """Quaternion conjugate for [w, x, y, z]."""
    q = np.asarray(q, dtype=float)
    w, x, y, z = q
    return np.array([w, -x, -y, -z], dtype=float)


def quat_to_rot_wxyz(q: np.ndarray) -> np.ndarray:
    """Convert [w, x, y, z] quaternion to 3×3 rotation matrix."""
    q = np.asarray(q, dtype=float)
    w, x, y, z = q
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z

    return np.array(
        [
            [1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy)],
            [2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx)],
            [2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy)],
        ],
        dtype=float,
    )


def rotate_quat_world_z_deg(quat_in: np.ndarray, angle_deg: float) -> np.ndarray:
    """
    Rotate `quat_in` by `angle_deg` about WORLD Z axis.
    All quats are [w, x, y, z].

    q_total = qz ⊗ quat_in
    """
    quat_in = np.asarray(quat_in, dtype=float)
    angle = np.deg2rad(angle_deg)
    half = 0.5 * angle
    sin_half = np.sin(half)
    cos_half = np.cos(half)

    # rotation about WORLD Z: axis (0,0,1) → [w, x, y, z]
    qz = np.array([cos_half, 0.0, 0.0, sin_half], dtype=float)

    return quat_mul_wxyz(qz, quat_in)


class RobotAdapter:
    def __init__(self, robot: Any, scene: Any = None):
        """Wrap a genesis robot entity.

        Args:
            robot: the raw genesis robot entity (e.g., returned from scene.add_entity)
            scene: optional scene reference (some callers use scene alongside robot)
        """
        self.robot = robot
        self.scene = scene

        # --- DOF index groups for arm vs fingers (Franka) ---
        jnt_names = [
            "joint1",
            "joint2",
            "joint3",
            "joint4",
            "joint5",
            "joint6",
            "joint7",
            "finger_joint1",
            "finger_joint2",
        ]
        dofs_idx = [self.robot.get_joint(name).dof_idx_local for name in jnt_names]

        self._arm_dofs = np.array(dofs_idx[:7], dtype=int)
        self._finger_dofs = np.array(dofs_idx[7:], dtype=int)

        print("[DEBUG] arm dofs   :", self._arm_dofs)
        print("[DEBUG] finger dofs:", self._finger_dofs)

        # ------------------------------------------------------------------
        # Block geometry: 4 cm cube
        # ------------------------------------------------------------------
        self.block_size = 0.04  # meters
        self.block_half = 0.5 * self.block_size

        # ------------------------------------------------------------------
        # Vertical offsets:
        #  - hand_to_finger_tip_z: measured (12 cm)
        #  - hand_to_block_center_z: where block center should be when fingers
        #    are gripping at mid-height
        # ------------------------------------------------------------------
        self.hand_to_finger_tip_z = 0.12
        self.hand_to_block_center_z = self.hand_to_finger_tip_z - self.block_half
        # = 0.12 - 0.02 = 0.10 m

        # ------------------------------------------------------------------
        # "Locked fingers" state: keep fingers closed after grasp
        # ------------------------------------------------------------------
        self._fingers_locked: bool = False
        self._finger_lock_value: Optional[float] = None  # scalar for last 2 DOFs

        # ------------------------------------------------------------------
        # Blocks list for neighbor search (purely geometric, no TAMP)
        # ------------------------------------------------------------------
        self.blocks: List[Any] = []

        # ------------------------------------------------------------------
        # Logical attachment state for symbolic is_holding(...)
        # (NO kinematic weld; just a flag)
        # ------------------------------------------------------------------
        self.attached_object: Optional[Any] = None

    # ------------------------------------------------------------------
    # Transparent forwarding
    # ------------------------------------------------------------------
    def __getattr__(self, name: str) -> Any:
        """Forward unknown attribute access to the underlying robot."""
        return getattr(self.robot, name)

    # Convenience wrappers (stable names)
    def get_pos(self):
        return self.robot.get_pos()

    def set_pos(self, pos):
        return self.robot.set_pos(pos)

    def get_qpos(self):
        return self.robot.get_qpos()

    def set_qpos(self, qpos):
        return self.robot.set_qpos(qpos)

    def control_dofs_position(self, *a, **kw):
        return self.robot.control_dofs_position(*a, **kw)

    def control_dofs_force(self, *a, **kw):
        # Used for squeezing fingers in close_gripper
        return self.robot.control_dofs_force(*a, **kw)

    def get_link(self, *a, **kw):
        return self.robot.get_link(*a, **kw)

    def inverse_kinematics(self, *a, **kw):
        return self.robot.inverse_kinematics(*a, **kw)

    def detect_collision(self, *a, **kw):
        return self.robot.detect_collision(*a, **kw)

    # ------------------------------------------------------------------
    # Blocks registration + neighbor logic
    # ------------------------------------------------------------------
    def register_blocks(self, blocks: List[Any]):
        """
        Register all block entities so we can search for neighbors
        using only geometry (no TAMP).
        """
        self.blocks = list(blocks)
        print(f"[ROBOT][BLOCKS] Registered {len(self.blocks)} blocks.")

    def _find_neighbor_block(
        self,
        target_pos,
        radius: float = 0.06,   # ≈ 6 cm, a bit larger than one block
        ignore_obj: Optional[Any] = None,
    ) -> Optional[Any]:
        """
        Find the nearest *other* block around target_pos in XY within `radius`.

        Returns:
            Genesis entity for neighbor block, or None if none found.
        """
        if not self.blocks:
            return None

        target_pos = _to_np(target_pos)
        best_block = None
        best_dist = float("inf")

        for b in self.blocks:
            if ignore_obj is not None and b is ignore_obj:
                continue

            try:
                p = _to_np(b.get_pos())
            except Exception:
                continue

            d_xy = np.linalg.norm(p[:2] - target_pos[:2])
            if d_xy < best_dist and d_xy < radius:
                best_dist = d_xy
                best_block = b

        if best_block is not None:
            print(
                f"[NEIGHBOR] Found neighbor at d_xy={best_dist:.4f} m "
                f"within radius={radius:.3f} m"
            )
        else:
            print("[NEIGHBOR] No neighbor found within radius.")

        return best_block

    def _choose_place_quat_from_neighbor(
        self,
        base_quat: np.ndarray,
        target_pos: np.ndarray,
        neighbor_obj: Optional[Any] = None,
        extra_deg: float = 90.0,
    ) -> np.ndarray:
        """
        Decide whether to keep `base_quat` as-is or rotate it by `extra_deg`
        about WORLD Z, based purely on neighboring block pose.

        Heuristic:
          - Compute the XY direction from target → neighbor
          - Approximate the finger-closing axis in world (assume local +Y)
          - Pick the orientation where that finger axis is MORE PERPENDICULAR
            to the neighbor direction (smaller |dot|).
        """
        base_quat = np.asarray(base_quat, dtype=float)
        target_pos = _to_np(target_pos)

        if neighbor_obj is None:
            # No neighbor: keep base orientation
            return base_quat

        try:
            neighbor_pos = _to_np(neighbor_obj.get_pos())
        except Exception:
            return base_quat

        diff_xy = neighbor_pos[:2] - target_pos[:2]
        norm_xy = float(np.linalg.norm(diff_xy))
        if norm_xy < 1e-4:
            # On top of each other; no real directional info
            return base_quat
        neighbor_dir = diff_xy / norm_xy

        # Finger-closing axis in hand frame (assume +Y)
        f_local = np.array([0.0, 1.0, 0.0], dtype=float)

        # --- Candidate 1: base_quat as-is ---
        R_base = quat_to_rot_wxyz(base_quat)
        f_base_world = R_base @ f_local
        f_base_xy = f_base_world[:2]
        if np.linalg.norm(f_base_xy) < 1e-6:
            score_base = 1.0
        else:
            f_base_xy /= np.linalg.norm(f_base_xy)
            score_base = abs(float(np.dot(f_base_xy, neighbor_dir)))

        # --- Candidate 2: base_quat rotated by +extra_deg about WORLD Z ---
        quat_rot = rotate_quat_world_z_deg(base_quat, extra_deg)
        R_rot = quat_to_rot_wxyz(quat_rot)
        f_rot_world = R_rot @ f_local
        f_rot_xy = f_rot_world[:2]
        if np.linalg.norm(f_rot_xy) < 1e-6:
            score_rot = 1.0
        else:
            f_rot_xy /= np.linalg.norm(f_rot_xy)
            score_rot = abs(float(np.dot(f_rot_xy, neighbor_dir)))

        # Smaller score = more perpendicular to neighbor direction
        if score_rot < score_base:
            print(
                f"[PLACE-ORIENT] Using rotated gripper (+{extra_deg}°); "
                f"score_base={score_base:.3f}, score_rot={score_rot:.3f}"
            )
            return quat_rot
        else:
            print(
                f"[PLACE-ORIENT] Keeping base orientation; "
                f"score_base={score_base:.3f}, score_rot={score_rot:.3f}"
            )
            return base_quat

    # ------------------------------------------------------------------
    # Logical attach / detach (for symbolic is_holding, NO kinematic weld)
    # ------------------------------------------------------------------
    def attach_object(self, obj: Any):
        """
        Logically mark that the robot is holding `obj`.
        No kinematic constraints are applied; used only by symbolic layer.
        """
        self.attached_object = obj
        print(f"[ROBOT][ATTACH-LOGIC] attached_object set to {obj}")

    def detach_object(self):
        """
        Logically mark that the robot is not holding anything.
        """
        print(f"[ROBOT][DETACH-LOGIC] clearing attached_object (was {self.attached_object})")
        self.attached_object = None

    # ------------------------------------------------------------------
    # Helpers: stepping + "lock fingers"
    # ------------------------------------------------------------------
    def _step_scene(self, steps: int = 1):
        """Step the simulator."""
        if self.scene is None:
            return
        for _ in range(steps):
            self.scene.step()

    def _maybe_lock_fingers(self, q) -> np.ndarray:
        """
        Ensure that if fingers are locked, the last 2 DOFs are held at the
        closed value, regardless of what IK/path planner produced.
        """
        q_np = _to_np(q).copy()
        if (
            self._fingers_locked
            and q_np.shape[0] >= 2
            and self._finger_lock_value is not None
        ):
            q_np[-2:] = self._finger_lock_value
        return q_np

    # ------------------------------------------------------------------
    # Debug utils
    # ------------------------------------------------------------------
    def print_ee_pose(self, string_label: str = ""):
        """Print current end-effector (EE) position and orientation."""
        ee_link = self.get_link("hand")
        ee_pos = _to_np(ee_link.get_pos())
        ee_quat = _to_np(ee_link.get_quat())
        print(f"\n[POSE] {string_label}")
        print(f"  Position : {np.round(ee_pos, 4)}")
        print(f"  Quaternion: {np.round(ee_quat, 4)}")

    # ------------------------------------------------------------------
    # Gripper
    # ------------------------------------------------------------------
    def open_gripper(self, open_pos: float = 0.04, steps: int = 10):
        """
        Open parallel gripper (assumes last 2 DOFs).
        Also UNLOCK fingers so they can move normally.
        """
        self.print_ee_pose("Before open_gripper()")
        qpos = _to_np(self.get_qpos())
        qpos[-2:] = open_pos
        self.control_dofs_position(qpos)

        # Opening: stop locking
        self._fingers_locked = False
        self._finger_lock_value = None

        if self.scene is not None:
            self._step_scene(steps)
        self.print_ee_pose("After open_gripper()")

    def close_gripper(
        self,
        close_pos: float = 0.0,
        steps: int = 10,
        squeeze_force: float = 150.0,  # tune up if needed
        squeeze_steps: int = 100,
    ):
        """
        Close parallel gripper with extra squeeze force on the 2 finger DOFs,
        while keeping the arm joints in position control.
        """
        self.print_ee_pose("Before close_gripper()")

        q_current = _to_np(self.get_qpos())
        q_target = q_current.copy()
        q_target[-2:] = close_pos

        # Hold arm joints at this pose
        self.robot.control_dofs_position(q_target[:-2], self._arm_dofs)
        # Put fingers at close_pos under PD as a base command
        self.robot.control_dofs_position(
            np.array([close_pos, close_pos], dtype=float),
            self._finger_dofs,
        )

        if self.scene is not None:
            self._step_scene(steps)

        print(
            f"[GRIP] Squeezing fingers with ramp 0 → {squeeze_force} "
            f"then hold for 20 steps (or less if needed), total {squeeze_steps} steps"
        )

        if self.scene is not None:
            # how many steps to ramp vs hold
            hold_steps = min(20, squeeze_steps)
            ramp_steps = max(squeeze_steps - hold_steps, 1)

            # 1) ramp 0 → squeeze_force over ramp_steps
            for i in range(ramp_steps):
                alpha = (i + 1) / ramp_steps  # 0 → 1
                f = alpha * squeeze_force
                finger_force = np.array([-f, -f], dtype=float)
                self.robot.control_dofs_force(finger_force, self._finger_dofs)
                self._step_scene(1)

            # 2) hold full squeeze_force for the last hold_steps
            for _ in range(hold_steps):
                finger_force = np.array(
                    [-squeeze_force, -squeeze_force], dtype=float
                )
                self.robot.control_dofs_force(finger_force, self._finger_dofs)
                self._step_scene(1)

        # After close, lock fingers in position space
        self._fingers_locked = True
        self._finger_lock_value = float(close_pos)

        self.print_ee_pose("After close_gripper()")

    # ------------------------------------------------------------------
    # Motion
    # ------------------------------------------------------------------
    def move_to_pose(
        self,
        qpos_goal,
        steps: int = 30,
        ignore_collisions: bool = False,
    ):
        """
        Plan and execute path using OMPL planner.

        If we are holding an object (fingers locked), use
        more waypoints (slower, smoother) to reduce slip.
        """
        self.print_ee_pose("Before move_to_pose()")

        # If grasping, increase resolution of motion
        if self._fingers_locked:
            steps = max(steps, 60)

        qpos_start = _to_np(self.get_qpos())
        print(f"[DEBUG] move_to_pose(): ignore_collisions={ignore_collisions}, "
              f"num_waypoints={steps}")

        if ignore_collisions:
            print(
                "[DEBUG] Ignoring collisions during motion planning (explicit flag)."
            )
            from planning import PlannerInterface

            planner_interface = PlannerInterface(self.robot, self.scene)
            path = planner_interface.plan_path(
                qpos_goal=qpos_goal,
                qpos_start=qpos_start,
                num_waypoints=steps,
            )
        else:
            # Assumes underlying robot or wrapper has plan_path(...)
            path = self.plan_path(
                qpos_goal=qpos_goal,
                num_waypoints=steps,
            )

        if len(path) == 0:
            print(
                "[WARN] OMPL returned empty path; executing direct control to goal."
            )
            q_goal = self._maybe_lock_fingers(qpos_goal)
            self.control_dofs_position(q_goal)
            if self.scene is not None:
                self._step_scene(100)
            return

        # OPTIONAL: subdivide between waypoints when grasping
        if self._fingers_locked and len(path) >= 2:
            dense_path = []
            for i in range(len(path) - 1):
                q0 = _to_np(path[i])
                q1 = _to_np(path[i + 1])
                # 3 sub-steps between waypoints → smoother
                for alpha in np.linspace(0.0, 1.0, 4, endpoint=False):
                    dense_path.append((1 - alpha) * q0 + alpha * q1)
            dense_path.append(_to_np(path[-1]))
            path = dense_path

        for waypoint in path:
            q = self._maybe_lock_fingers(waypoint)
            self.control_dofs_position(q)
            if self.scene is not None:
                self._step_scene(1)

        self.print_ee_pose("After move_to_pose()")

    def _servo_to_q(self, q_goal, steps: int = 80):
        """
        Simple joint-space interpolation from current q to q_goal.

        When fingers are locked (grasping), we automatically increase
        the number of interpolation steps to reduce accelerations and slip.
        """
        # Slow down if grasping
        if self._fingers_locked:
            steps = int(steps * 2.0)  # 2× slower when holding a block

        q_start = _to_np(self.get_qpos())
        q_goal = _to_np(q_goal)

        for alpha in np.linspace(0.0, 1.0, steps):
            q = (1.0 - alpha) * q_start + alpha * q_goal
            q = self._maybe_lock_fingers(q)
            self.control_dofs_position(q)
            if self.scene is not None:
                self._step_scene(1)

    def pre_grasp_pose(
        self,
        pos,
        quat,
        approach_dir: np.ndarray = np.array([0.0, 0.0, 1.0]),
        offset: float = 0.10,
        steps: int = 30,
    ):
        """
        Move the end-effector to a pre-grasp position offset from the given pos
        along the specified approach direction.

        NOTE: Here `pos` is interpreted as a target hand position (not block center).
        Uses local joint-space servo (no OMPL) for this short motion.
        """
        pos = _to_np(pos)
        approach_dir = _to_np(approach_dir)
        self.print_ee_pose("Before pre_grasp_pose()")

        pregrasp_pos = pos + approach_dir * offset
        print(f"[DEBUG] Pre-grasp hand position: {pregrasp_pos}")

        qpos_pregrasp = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=pregrasp_pos,
            quat=quat,
        )
        self._servo_to_q(qpos_pregrasp, steps=steps)

        self.print_ee_pose("After pre_grasp_pose()")

    def post_grasp_pose(
        self,
        pos,
        quat,
        approach_dir: np.ndarray = np.array([0.0, 0.0, -1.0]),
        offset: float = 0.10,
        steps: int = 30,
    ):
        """
        Move the end-effector away from a grasped pose (opposite of approach_dir).

        NOTE: Here `pos` is interpreted as a target hand position (not block center).
        Uses local joint-space servo (no OMPL).
        """
        pos = _to_np(pos)
        approach_dir = _to_np(approach_dir)
        self.print_ee_pose("Before post_grasp_pose()")

        retreat_pos = pos - approach_dir * offset
        print(f"[DEBUG] Post-grasp hand position: {retreat_pos}")

        qpos_postgrasp = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=retreat_pos,
            quat=quat,
        )
        self._servo_to_q(qpos_postgrasp, steps=steps)

        self.print_ee_pose("After post_grasp_pose()")

    # ------------------------------------------------------------------
    # High-level actions (obj is optional for logging / logic)
    # ------------------------------------------------------------------
    def pick(
        self,
        pos,
        quat: np.ndarray = np.array([0.0, 1.0, 0.0, 0.0]),
        obj: Optional[Any] = None,
    ):
        """
        PICK SEQUENCE (NO OMPL BETWEEN PRE-GRASP / GRASP / RETREAT)

        Steps:
          1) Pre-grasp above block center
          2) Open gripper
          3) Slow vertical descent to grasp height
          4) Let contacts settle
          5) Close gripper (lock fingers closed)
          6) Logically attach obj (for symbolic is_holding)
          7) Slow retreat upward

        `pos` is the desired *block center* world position (4 cm cube).
        """
        block_center = _to_np(pos).copy()
        target_grasp_z = block_center[2] + self.hand_to_block_center_z

        # Hand at block center XY, right Z for grasp
        hand_at_center = block_center.copy()
        hand_at_center[2] = target_grasp_z

        hand_link = self.get_link("hand")
        cur = _to_np(hand_link.get_pos())
        hand_at_center[0] = block_center[0]
        hand_at_center[1] = block_center[1]

        self.print_ee_pose("Before pick()")

        # 1) Pre-grasp above centered hand pose (local, no OMPL)
        pregrasp_target = hand_at_center.copy()
        pregrasp_target[2] = target_grasp_z + 1.5 * self.block_size  # ~6 cm above
        print(f"[DEBUG] Pre-grasp hand target: {pregrasp_target}")

        qpos_pregrasp = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=pregrasp_target,
            quat=quat,
        )
        self._servo_to_q(qpos_pregrasp, steps=100)

        # 2) Open gripper (fully open before going down) and unlock fingers
        self.open_gripper()

        # 3) SLOW VERTICAL DESCENT from pre-grasp to grasp height
        hand_link = self.get_link("hand")
        current_hand_pos = _to_np(hand_link.get_pos())
        z_start = current_hand_pos[2]
        z_goal = hand_at_center[2] - 0.001

        descent_steps = 30  # slow descent
        print(
            f"[DEBUG] Slow vertical descent from z={z_start:.4f} "
            f"→ z={z_goal:.4f} in {descent_steps} steps"
        )

        for i in range(descent_steps):
            alpha = (i + 1) / descent_steps
            z = z_start + alpha * (z_goal - z_start)

            target_pos = hand_at_center.copy()
            target_pos[2] = z

            q_step = self.inverse_kinematics(
                link=hand_link,
                pos=target_pos,
                quat=quat,
            )
            q_step = self._maybe_lock_fingers(q_step)
            self.control_dofs_position(q_step)

            if self.scene is not None:
                self._step_scene(1)

        # 4) Let contacts settle at final grasp pose
        if self.scene is not None:
            self._step_scene(30)  # ~0.5s depending on dt

        # 5) Close gripper (now we are at grasp height) and LOCK fingers
        self.close_gripper()

        # 6) Logically attach if provided (for symbolic is_holding)
        if obj is not None:
            self.attach_object(obj)

        # 7) Retreat straight up (slow, to reduce slip)
        retreat_target = hand_at_center + np.array(
            [0.0, 0.0, 2.0 * self.block_size]
        )
        qpos_retreat = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=retreat_target,
            quat=quat,
        )
        print("[DEBUG] Retreat target (from centered grasp):", retreat_target)
        # extra steps; _servo_to_q will 2× it again because fingers_locked
        self._servo_to_q(qpos_retreat, steps=80)

        self.print_ee_pose("After pick()")

    def place(
        self,
        pos,
        quat: np.ndarray = np.array([0.0, 1.0, 0.0, 0.0]),  # [w,x,y,z]
        obj: Optional[Any] = None,
        hover_height: float = 0.08,
        release_clearance: float = 0.015,  # release a few mm above target
    ):
        """
        PLACE SEQUENCE (physics-based grip; neighbor-aware orientation)

        `pos` is the desired object center at the final stack position.

        Steps:
          1) Find neighbor based on geometry
          2) Decide whether to rotate gripper by +90° about world Z
          3) Move hand to hover above target (via OMPL, smoothed if grasping)
          4) Iterative XY correction using object pose (if given)
          5) Descend to a release height slightly above final Z
          6) Open gripper (unlock fingers) + logically detach + settling time
          7) Retreat upward
        """
        self.print_ee_pose("Before place()")
        pos = _to_np(pos).copy()

        base_quat = np.asarray(quat, dtype=float)

        # --- purely geometric neighbor lookup (no TAMP) ---
        neighbor = self._find_neighbor_block(target_pos=pos, ignore_obj=obj)

        # Decide whether to keep base_quat or rotate by +90° about WORLD Z
        quat_place = self._choose_place_quat_from_neighbor(
            base_quat=base_quat,
            target_pos=pos,
            neighbor_obj=neighbor,
            extra_deg=90.0,
        )

        print("[DEBUG] Original quat [w,x,y,z]:", quat)
        print("[DEBUG] Chosen place quat (maybe +90°):", quat_place)

        # === 1) target object center hover above final stack position ===
        pos_above_obj = pos.copy()
        pos_above_obj[2] += hover_height

        # Approximate hand↔block offset (same geometry as in pick())
        off = np.array([0.0, 0.0, -self.hand_to_block_center_z], dtype=float)

        print("[DEBUG] assumed hand↔block offset:", np.round(off, 4))
        print("[DEBUG] desired object pos:", np.round(pos, 4))
        print("[DEBUG] desired object pos above:", np.round(pos_above_obj, 4))

        target_hand_pos_above = pos_above_obj - off

        # === 2) Move to hover pose via OMPL (coarse motion) ===
        q_above = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=target_hand_pos_above,
            quat=quat_place,
        )
        print("[DEBUG] Initial hover qpos:", q_above)
        self.move_to_pose(q_above, steps=40)
        self.print_ee_pose("[DEBUG] After initial hover move")

        # === 3) Iterative XY correction (if obj is available) ===
        tol_xy = 2e-3  # 2 mm target
        max_iters = 4
        stall_eps = 1e-6
        k_p = 1.1
        k_d = 0.0
        step_max = 7e-1  # up to 7 mm per correction

        prev_err_xy = None
        prev_err_norm = None

        for it in range(max_iters):
            hand = self.get_link("hand")
            ee_pos = _to_np(hand.get_pos())

            if obj is not None:
                try:
                    obj_pos = _to_np(obj.get_pos())
                except Exception:
                    obj_pos = ee_pos - off  # fallback guess
            else:
                # if we don't have an object reference, approximate block center
                obj_pos = ee_pos - off

            target_xy = pos[:2]
            err_xy = target_xy - obj_pos[:2]
            err_norm = float(np.linalg.norm(err_xy))

            print(
                f"[CORRECTION {it}] XY error = "
                f"({err_xy[0]:+.6f}, {err_xy[1]:+.6f}), "
                f"‖err‖ = {err_norm:.6f} m"
            )

            if err_norm < tol_xy:
                print(f"[CORRECTION] Reached tolerance {tol_xy} m, stopping.")
                break

            if prev_err_norm is not None and abs(prev_err_norm - err_norm) < stall_eps:
                print(
                    f"[CORRECTION] Stalled at ~{err_norm:.6f} m "
                    f"(Δ‖err‖ < {stall_eps}), breaking."
                )
                break

            if prev_err_xy is None:
                derr_xy = np.zeros_like(err_xy)
            else:
                derr_xy = err_xy - prev_err_xy

            prev_err_xy = err_xy.copy()
            prev_err_norm = err_norm

            u_xy = k_p * err_xy + k_d * derr_xy
            dx = float(np.clip(u_xy[0], -step_max, step_max))
            dy = float(np.clip(u_xy[1], -step_max, step_max))

            print(
                f"[CORRECTION {it}] Applying Δhand = "
                f"({dx:+.6f}, {dy:+.6f})"
            )

            new_hand_pos = ee_pos.copy()
            new_hand_pos[0] += dx
            new_hand_pos[1] += dy
            new_hand_pos[2] = target_hand_pos_above[2]

            q_fix = self.inverse_kinematics(
                link=hand,
                pos=new_hand_pos,
                quat=quat_place,
            )
            self._servo_to_q(q_fix, steps=40)

        # === 4) Descend to *release* height while still gripping ===
        final_obj_pos = pos.copy()
        final_obj_pos[0] += 0.0085   # your tuned XY bias
        final_obj_pos[1] += 0.002
        final_obj_pos[2] += release_clearance
        final_hand_pos = final_obj_pos - off

        q_final = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=final_hand_pos,
            quat=quat_place,
        )
        print("[DEBUG] Descend to release pose qpos:", q_final)
        self._servo_to_q(q_final, steps=80)
        self.print_ee_pose("[DEBUG] At release pose (physics holding block)")

        # 6) Open gripper to release (unlock fingers) and logically detach
        self.open_gripper()
        if obj is not None and obj is self.attached_object:
            self.detach_object()
        elif obj is None and self.attached_object is not None:
            # if we had something logically attached but caller omitted obj,
            # still clear it so is_holding doesn't get stuck
            self.detach_object()

        if self.scene is not None:
            self._step_scene(30)

        try:
            if obj is not None:
                final_obj_pos_meas = _to_np(obj.get_pos())
                xy_err_vec = pos[:2] - final_obj_pos_meas[:2]
                xy_err_norm = float(np.linalg.norm(xy_err_vec))
                print(
                    "[DEBUG] Final placed object center:",
                    np.round(final_obj_pos_meas, 4),
                    "‖XY err‖ =",
                    f"{xy_err_norm:.6f} m",
                )
        except Exception as e:
            print("[DEBUG] Could not read final object pose:", e)

        # === 7) Retreat upward so we don't collide with the stack ===
        pos_retreat = pos.copy()
        pos_retreat[2] += 0.30

        q_retreat = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=pos_retreat,
            quat=quat_place,
        )
        print("[DEBUG] move_to_pose retreat called, pos_retreat:", pos_retreat)
        self._servo_to_q(q_retreat, steps=40)
        self.print_ee_pose("After place()")

    # ------------------------------------------------------------------
    # Raw object access
    # ------------------------------------------------------------------
    @property
    def raw(self):
        """Direct access to underlying Genesis robot entity."""
        return self.robot
