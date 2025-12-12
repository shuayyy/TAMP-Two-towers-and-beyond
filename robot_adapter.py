"""
RobotAdapter: a thin adapter around a Genesis robot entity.

Features:
  • Transparent pass-through to underlying robot
  • OMPL motion planning bridge via PlannerInterface
  • move_to_pose(..., ignore_collisions=False)
  • Kinematic gripping (block welded to hand while attached)
  • Logical attached_object for symbolic is_holding(...)
  • "Locked" fingers after closing (continuous grip in position mode)
  • Slower, smoother motions while grasping to reduce slip
  • Neighbor-aware place():
        For placing block at (x, y) and any neighbor at (a, b),
        if |y - b| < 0.044 AND |x - a| < 0.010, rotate gripper by +90° about WORLD Z.
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
        # plus kinematic weld data (pos/quat offsets)
        # ------------------------------------------------------------------
        self.attached_object: Optional[Any] = None
        self._attach_offset_pos: Optional[np.ndarray] = None  # block in HAND frame
        self._attach_offset_quat: Optional[np.ndarray] = None  # q_rel = q_h*conj(q_o)

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
    # Blocks registration + neighbor-orientation logic
    # ------------------------------------------------------------------
    def register_blocks(self, blocks: List[Any]):
        """
        Register all block entities so we can search for neighbors
        using only geometry (no TAMP).
        """
        self.blocks = list(blocks)
        print(f"[ROBOT][BLOCKS] Registered {len(self.blocks)} blocks.")

    def _choose_place_quat_from_neighbor(
        self,
        base_quat: np.ndarray,
        target_pos: np.ndarray,
        ignore_obj: Optional[Any] = None,
        extra_deg: float = 90.0,
    ) -> np.ndarray:
        """
        Refined rule with both X and Y:

          placing block at (x, y) and some neighbor at (a, b):

            if there exists ANY neighbor with
                |y - b| < 0.044   (4.4 cm in Y)
            AND |x - a| < 0.010   (~1 cm in X, same column)
            ⇒ rotate gripper by +extra_deg about WORLD Z.

        We pick the neighbor with the smallest |y - b| under those thresholds.
        If none satisfy the condition, keep base_quat.
        """
        base_quat = np.asarray(base_quat, dtype=float)
        target_pos = _to_np(target_pos)

        if not self.blocks:
            print("[PLACE-ORIENT] No blocks registered ⇒ keep base orientation.")
            return base_quat

        x, y = float(target_pos[0]), float(target_pos[1])

        dy_thresh = 0.044   # 4.4 cm in Y
        dx_thresh = 0.010   # 1 cm in X (same column)

        best_block = None
        best_abs_dy = float("inf")
        best_a = 0.0
        best_b = 0.0
        best_abs_dx = 0.0

        print(f"[PLACE-ORIENT] Checking neighbors for target (x,y)=({x:.4f},{y:.4f})")

        for blk in self.blocks:
            if ignore_obj is not None and blk is ignore_obj:
                # skip the block we're currently placing
                continue

            try:
                p = _to_np(blk.get_pos())
            except Exception:
                continue

            a, b = float(p[0]), float(p[1])
            abs_dy = abs(y - b)
            abs_dx = abs(x - a)

            print(
                f"[PLACE-ORIENT] candidate neighbor (a,b)=({a:.4f},{b:.4f}), "
                f"|x-a|={abs_dx:.4f}, |y-b|={abs_dy:.4f}"
            )

            # must satisfy BOTH thresholds to be considered
            if abs_dy < dy_thresh and abs_dx < dx_thresh and abs_dy < best_abs_dy:
                best_abs_dy = abs_dy
                best_abs_dx = abs_dx
                best_block = blk
                best_a = a
                best_b = b

        if best_block is None:
            print(
                "[PLACE-ORIENT] No neighbor with "
                f"|y-b| < {dy_thresh:.3f} AND |x-a| < {dx_thresh:.3f} "
                "⇒ keep base orientation."
            )
            return base_quat

        print(
            f"[PLACE-ORIENT] Chosen neighbor (a,b)=({best_a:.4f},{best_b:.4f}), "
            f"|x-a|={best_abs_dx:.4f}, |y-b|={best_abs_dy:.4f} "
            f"⇒ rotate +{extra_deg}° about WORLD Z."
        )

        quat_rot = rotate_quat_world_z_deg(base_quat, extra_deg)
        print("[PLACE-ORIENT] base_quat:", base_quat, "→ quat_rot:", quat_rot)
        return quat_rot

    # ------------------------------------------------------------------
    # Logical + kinematic attach / detach
    # ------------------------------------------------------------------
    def attach_object(self, obj: Any):
        """
        Logically and kinematically mark that the robot is holding `obj`.
        We compute:
          - _attach_offset_pos: block center in HAND frame
          - _attach_offset_quat: relative orientation (q_h*conj(q_o))
        Then _sync_attached_object() welds the block to the hand each step.
        """
        self.attached_object = obj

        hand = self.get_link("hand")
        p_h = _to_np(hand.get_pos())
        q_h = _to_np(hand.get_quat())
        p_o = _to_np(obj.get_pos())
        q_o = _to_np(obj.get_quat())

        R_h = quat_to_rot_wxyz(q_h)

        # block center in hand frame
        self._attach_offset_pos = R_h.T @ (p_o - p_h)
        # relative orientation: q_rel = conj(q_h) ⊗ q_o
        self._attach_offset_quat = quat_mul_wxyz(
            quat_conj_wxyz(q_h), q_o
        )

        # snap once immediately
        self._sync_attached_object()

        print(
            "[ROBOT][ATTACH-LOGIC] attached_object set to",
            obj,
            "offset_pos (hand frame)=",
            np.round(self._attach_offset_pos, 4),
        )

    def detach_object(self):
        """
        Logically mark that the robot is not holding anything
        and disable kinematic weld.
        """
        print(
            "[ROBOT][DETACH-LOGIC] clearing attached_object (was",
            self.attached_object,
            ")",
        )
        self.attached_object = None
        self._attach_offset_pos = None
        self._attach_offset_quat = None

    def _sync_attached_object(self):
        """
        Kinematic weld: place object at hand pose + stored offset.
        Called after each physics step while attached_object is valid.
        """
        if (
            self.attached_object is None
            or self._attach_offset_pos is None
            or self._attach_offset_quat is None
        ):
            return

        hand = self.get_link("hand")
        p_h = _to_np(hand.get_pos())
        q_h = _to_np(hand.get_quat())
        R_h = quat_to_rot_wxyz(q_h)

        # world pose of block
        p_o = p_h + R_h @ self._attach_offset_pos
        q_o = quat_mul_wxyz(q_h, self._attach_offset_quat)

        try:
            self.attached_object.set_pos(p_o)
            self.attached_object.set_quat(q_o)
        except Exception as e:
            print("[ROBOT][SYNC] Could not kinematically sync attached object:", e)

    # ------------------------------------------------------------------
    # Helpers: stepping + "lock fingers"
    # ------------------------------------------------------------------
    def _step_scene(self, steps: int = 1):
        """Step the simulator and enforce kinematic weld if attached."""
        if self.scene is None:
            return
        for _ in range(steps):
            self.scene.step()
            self._sync_attached_object()

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

        self._step_scene(steps)
        self.print_ee_pose("After open_gripper()")

    def close_gripper(
        self,
        close_pos: float = 0.0,
        steps: int = 10,
        squeeze_force: float = 200.0,  # tune up if needed
        squeeze_steps: int = 120,
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

        self._step_scene(steps)

        print(
            f"[GRIP] Squeezing fingers with ramp 0 → {squeeze_force} "
            f"then hold for 20 steps (or less if needed), total {squeeze_steps} steps"
        )

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
            finger_force = np.array([-squeeze_force, -squeeze_force], dtype=float)
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
        print(
            f"[DEBUG] move_to_pose(): ignore_collisions={ignore_collisions}, "
            f"num_waypoints={steps}"
        )

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
          6) Small test-lift; ONLY IF block lifts, attach_object(obj)
          7) Retreat upward

        `pos` is the desired *block center* world position (4 cm cube).
        """
        block_center = _to_np(pos).copy()
        target_grasp_z = block_center[2] + self.hand_to_block_center_z

        # Hand at block center XY, right Z for grasp
        hand_at_center = block_center.copy()
        hand_at_center[2] = target_grasp_z

        hand_link = self.get_link("hand")

        # For grasp success check, cache pre-grasp block pose
        obj_pos_before = None
        if obj is not None:
            try:
                obj_pos_before = _to_np(obj.get_pos())
            except Exception as e:
                print("[PICK] Could not read obj_pos_before:", e)

        self.print_ee_pose("Before pick()")

        # 1) Pre-grasp above centered hand pose (local, no OMPL)
        pregrasp_target = hand_at_center.copy()
        pregrasp_target[2] = target_grasp_z + 1.5 * self.block_size  # ~6 cm above
        print(f"[DEBUG] Pre-grasp hand target: {pregrasp_target}")

        qpos_pregrasp = self.inverse_kinematics(
            link=hand_link,
            pos=pregrasp_target,
            quat=quat,
        )
        self._servo_to_q(qpos_pregrasp, steps=100)

        # 2) Open gripper (fully open before going down) and unlock fingers
        self.open_gripper()

        # 3) SLOW VERTICAL DESCENT from pre-grasp to grasp height
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
            self._step_scene(1)

        # 4) Let contacts settle at final grasp pose
        self._step_scene(30)  # ~0.5s depending on dt

        # 5) Close gripper (now we are at grasp height) and LOCK fingers
        self.close_gripper()

        # 6) Small test-lift: attach ONLY IF block actually comes up
        grasp_succeeded = False
        if obj is not None and obj_pos_before is not None:
            # target: small lift of the hand (e.g., +1.5 cm)
            test_lift_target = hand_at_center.copy()
            test_lift_target[2] += 0.015  # 1.5 cm up from grasp height
            print(f"[PICK] Test-lift target hand pos: {test_lift_target}")

            q_test_lift = self.inverse_kinematics(
                link=hand_link,
                pos=test_lift_target,
                quat=quat,
            )
            self._servo_to_q(q_test_lift, steps=40)
            self._step_scene(20)

            try:
                obj_pos_after = _to_np(obj.get_pos())
                dz = float(obj_pos_after[2] - obj_pos_before[2])
                print(f"[PICK] Test-lift dz for obj: {dz:.4f} m")

                # threshold: block must move up at least 8 mm to consider grasp success
                if dz > 0.008:
                    print("[PICK] Grasp succeeded ⇒ attaching object.")
                    self.attach_object(obj)
                    grasp_succeeded = True
                else:
                    print("[PICK] Grasp failed (block did not lift) ⇒ NOT attaching.")
            except Exception as e:
                print("[PICK] Could not evaluate grasp success:", e)
        else:
            print("[PICK] Skipping grasp success check (no obj or no pre pose).")

        # 7) Retreat straight up (slow, to reduce slip)
        #    (Even if grasp failed, we still move the hand up to clear the workspace.)
        retreat_target = hand_at_center + np.array(
            [0.0, 0.0, 2.0 * self.block_size]
        )
        qpos_retreat = self.inverse_kinematics(
            link=hand_link,
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
        release_clearance: float = 0.0,  # no free drop; drive to final Z
    ):
        """
        PLACE SEQUENCE (kinematically attached block + neighbor-aware orientation)

        `pos` is the desired object center at the final stack position.

        Steps:
          1) Decide orientation using neighbors and |y - b| / |x - a| rule
          2) Move hand to hover above target (via OMPL, smoothed if grasping)
          3) Iterative XY correction using object pose (if given)
          4) Descend to final placement height (no free drop)
          5) Open gripper (unlock fingers) + logically detach + settling time
          6) Retreat upward
        """
        self.print_ee_pose("Before place()")
        pos = _to_np(pos).copy()

        base_quat = np.asarray(quat, dtype=float)
        print("[DEBUG] Incoming base quat (w,x,y,z):", base_quat)

        # Decide whether to keep base_quat or rotate by +90° about WORLD Z
        quat_place = self._choose_place_quat_from_neighbor(
            base_quat=base_quat,
            target_pos=pos,
            ignore_obj=obj,
            extra_deg=90.0,
        )

        print("[DEBUG] Final quat_place passed to IK:", quat_place)

        # === 1) target object center hover above final stack position ===
        pos_above_obj = pos.copy()
        pos_above_obj[2] += hover_height

        # Default approximate hand↔block offset (if no attach info)
        off = np.array([0.0, 0.0, -self.hand_to_block_center_z], dtype=float)

        # If we have a real measured attach offset, use that instead (world frame)
        if (
            obj is not None
            and obj is self.attached_object
            and self._attach_offset_pos is not None
        ):
            R_place = quat_to_rot_wxyz(quat_place)
            off = R_place @ self._attach_offset_pos

        print("[DEBUG] used hand↔block offset (world):", np.round(off, 4))
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

        # === 3) Iterative XY correction (adaptive step_max) ===
        tol_xy = 1e-3      # 1 mm target
        max_iters = 20
        stall_eps = 1e-6
        k_p = 1.3
        k_d = 0.18

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
                obj_pos = ee_pos - off  # approximate block center

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

            # adaptive step_max: big steps when far, tiny when close
            adaptive = 0.3 * err_norm
            step_max = min(0.02, max(0.001, adaptive))  # [1mm, 2cm]

            u_xy = k_p * err_xy + k_d * derr_xy
            dx = float(np.clip(u_xy[0], -step_max, step_max))
            dy = float(np.clip(u_xy[1], -step_max, step_max))

            print(
                f"[CORRECTION {it}] step_max={step_max:.4f} "
                f"Δhand=({dx:+.6f}, {dy:+.6f})"
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

        # === 4) Descend to *final* placement height (no free drop) ===
        final_obj_pos = pos.copy()
        final_obj_pos[2] += release_clearance  # 0.0 by default
        final_hand_pos = final_obj_pos - off

        q_final = self.inverse_kinematics(
            link=self.get_link("hand"),
            pos=final_hand_pos,
            quat=quat_place,
        )
        print("[DEBUG] Descend to final pose qpos:", q_final)
        self._servo_to_q(q_final, steps=80)
        self.print_ee_pose("[DEBUG] At final pose (block kinematically attached)")

        # 5) Open gripper to release (unlock fingers) and logically detach
        self.open_gripper()
        if obj is not None and obj is self.attached_object:
            self.detach_object()
        elif obj is None and self.attached_object is not None:
            self.detach_object()

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

        # === 6) Retreat upward so we don't collide with the stack ===
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
