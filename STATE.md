# Session state — resume point

**Last updated: 2026-08-29 ~03:20. Written as a stopping point before shutdown.**

Read this together with `CLAUDE.md` (rules, environment) before doing anything.

---

## Where things stand

| Goal | Scene | Status | Evidence |
|---|---|---|---|
| **1** — two towers (B-G-R, C-M-Y) | 1 scattered | **PASS 3/3** | XY dev 0.61 / 0.48 / 0.43 mm |
| **1** | 2 pre-stacked | **PASS 3/3** | XY dev 1.10 / 0.65 / 0.92 mm |
| **2** — 5-block tower (G-R-B-Y-M) | 1 scattered | **PASS** (4/4 structurally; one lost its video to a shutdown mid-encode) | XY dev 0.39–0.67 mm |
| **2** | 2 pre-stacked | **PASS 3/3** | XY dev 1.18 / 0.88 / 0.89 mm |
| **3** — tallest tower (bonus) | 1 | **FAILING** — reached 6 blocks before the stack was knocked over | see "next actions" |
| **4** — yellow cross + green square | — | **NOT STARTED** | — |

**Goals 1 and 2 work from both starting scenes.** That is the core assignment requirement.

Per the assignment PDF, goal 3 is explicitly *bonus* and scores partial credit — "for each
additional block over 5 you successfully add before the structure collapses, you will receive
2 bonus points". Goal 4 is a required deliverable, so **goal 4 outranks goal 3**.

---

## Commits

| SHA | What |
|---|---|
| `a9c7b9b` | Core physics fixes: gravity compensation, weld removal, gripper, descent, IK checks, empty-plan bug, headless video |
| `2903759` | Wrist-tilt ladder for edge-of-workspace blocks; IK convergence reporting |
| `05615e5` | PUTDOWN picks a clear reachable table spot instead of one fixed point |

**Uncommitted: `robot_adapter.py`** — the fix for bug #9 below. Written and syntax-checked
but **not yet verified by a run**. Commit only after it passes.

---

## The nine defects found and fixed

Each was measured, not guessed. Numbers are from actual runs.

1. **No gravity compensation** (`scenes.py`) — *the keystone*. Joint 2 (shoulder pitch) settled
   0.0158 rad below every command: kp·err = 4500 × 0.0158 = 71 N·m against an 87 N·m limit,
   82% saturated just holding station. That 16 mrad droop swamped the millimetre corrections
   `place()` issues, so the hand moved ~0.3% of what it was commanded. Fixing it took descent
   error −6.8 mm → 0.0 mm and placement error ~15 mm → 0.4 mm.

2. **Kinematic weld faked the grasp** (`robot_adapter._sync_attached_object`) — wrote the
   block's pose every step, so every grasp "succeeded" regardless of finger purchase, and
   `place()` could not steer a block rigidly pinned to the hand; its correction loop
   *diverged* 3.2 → 8.5 mm. Proven unnecessary: a real friction grasp lifts the 12.8 g cube
   150 mm at Genesis' default friction. Now observes the measured offset instead.

3. **200 N finger squeeze** fought the position controller on the same DOFs and drove through
   the cube — force-closing at only 20 N ends at finger width −0.0006 m with the cube dropped.
   Position-closing seats them at 0.0396 m on a 0.040 m cube.

4. **Descent overshoot** — 90 mm in 30 steps (~0.3 m/s) overshot 6.6 mm, putting the
   fingertips (measured 0.1124 m below the hand frame) at exactly z = 0, jammed into the
   table. Now 150 steps with the achieved height verified before closing.

5. **IK never checked** — Genesis returns a best-effort qpos and reports non-convergence only
   via `return_error=True`. Added `_ik()` plus joint-tracking diagnostics in `_servo_to_q`,
   which is how the gravity droop was found.

6. **Empty plan treated as failure** (`task_planner`) — an empty plan means the goal already
   holds, but it raised, making demo.py's `GOAL REACHED` branch unreachable. Every success was
   reported as a planning error.

7. **No headless/video path** — `show_viewer=True` hardcoded, no camera, and demo.py ended in
   `while True: scene.step()` so runs never terminated. Added `recording.py` and
   `--headless/--video`; runs now exit with a meaningful code.

8. **PUTDOWN used one fixed target** `[0.55, 0, 0.05]` for every block. Each putdown landed on
   the previous one; the planner saw the accidental stack, unstacked it, and put it back in
   the same place — an infinite loop, observed verbatim. One collision threw a block 0.84 m.
   Also z = 0.05 dropped blocks from 3 cm up (resting centre is 0.02). Scene 2 went 1/3 → 3/3.

9. **Spurious 90° wrist rotation on every stack** — *fix written, NOT yet verified*.
   `_choose_place_quat_from_neighbor` compared only XY, so the support block directly
   underneath matched at `|dx|=|dy|=0.0000` and triggered the rotation on **every** stack.
   Short towers tolerate it; on a 6-tall tower the rotated fingers catch the stack on release.
   Fix: only blocks within half a block height of the target count as neighbours.

### Two hypotheses tested and discarded

Recorded so they are not re-explored:

- `hand_to_finger_tip_z = 0.12` was suspected wrong. Calibration showed 0.12 produces the
  **best** grasp of the heights tried (finger width 0.0396, lift +152.7 mm). Left alone.
  The true fingertip offset is 0.1124 m, used only for reporting.
- IK was suspected of failing. Its residual is 0.03 mm and zero solves were unconverged.
  The arm was drooping under gravity instead (defect 1).

---

## Measured constants worth keeping

| Quantity | Value | How measured |
|---|---|---|
| Fingertip below hand frame | 0.1124 m | lowest finger geom, consistent across all trials |
| Hand → grasped cube centre | ~0.093 m | post-grasp pose difference |
| Seated finger width on a 4 cm cube | 0.0396 m | every successful grasp |
| Cube mass | 12.8 g (0.126 N) | 0.04³ m³ at Genesis default rho = 200 |
| Top-down grasp reach limit | **r ≈ 0.79 m** | sweep; NOT the quoted 0.855 m |
| Reach with 25° wrist tilt | r ≈ 0.832 m works | cube lifted +155.7 mm |
| `scenes.py` worst-case B spawn | r = 0.832 m | (0.65, 0.40) ± 0.05 — outside straight-down reach |

---

## Next actions, in order

1. **Verify defect 9.** Run goal 3 and confirm `[PLACE-ORIENT]` no longer rotates on every
   stack, and check goals 1/2 for regression. Commit `robot_adapter.py` only if clean.

   ```bash
   conda run -n rbe550 python demo.py --goal 3 --headless \
       --video runs/x/g3.mp4 --max-iterations 30
   conda run -n rbe550 python verify_goal.py --goal 3 runs/x/run.log
   ```

2. **Start goal 4** — the remaining required deliverable. It is untouched and expected to be
   the hardest. Known suspects, from a read of the code (not yet confirmed by a run):
   - `goal4_config.POSITION_XY_THRESHOLD = 0.002` (2 mm). Placement now achieves ~0.4–1.2 mm,
     so this may be attainable — but it is tight, and if a block settles 3 mm off the planner
     will loop forever. **Do not loosen it without first measuring what placement achieves at
     those positions.**
   - `run_goal4` executes `plan[:16]` open-loop without re-perceiving between actions, unlike
     goals 1–3 which execute one action then replan. That is fragile.
   - `reorder_plan_by_layers` sorts by position *name string*, which may not be a valid
     execution order.
   - Goal-4 positions are at x ≈ 0.65 with y offsets; check them against the measured
     r ≈ 0.79 m reach limit before assuming they are all reachable.

3. **Goal 3 (bonus, lowest priority).** Partial credit applies. If the tower still topples
   above 6 blocks, that may be genuine physics rather than a bug — but check for gripper
   contact on release before concluding that.

4. Re-run goal 2 scene 1 once to replace the run whose video was lost.

---

## How to run things

```bash
# single verified run
conda run -n rbe550 python demo.py --goal 1 --scene 1 --headless \
    --video runs/foo/run.mp4 --video-res 640x360 --max-iterations 25

# always under xvfb-run when headless
xvfb-run -a -s "-screen 0 1280x720x24" conda run -n rbe550 python demo.py ...

# verify — derives expected stacks from get_goal_predicates, checks geometry + video
conda run -n rbe550 python verify_goal.py --goal 1 runs/*/run.log
```

Batch scripts used in this session are in the session scratchpad, not the repo. They append
one line per run to `runs/STATUS.txt`, which is the cheap way to poll progress.

Runs take 4–10 minutes each. Only one simulation at a time — the GPU cannot host concurrent
runs. Always launch in the background; never poll with `sleep`.

---

## Standing rule

No jugaad. Not one tolerance was loosened in any of the above: `XY_ALIGNMENT_THRESHOLD` is
still 15 mm, and placement was fixed to 0.4 mm rather than the check widened to accept 15 mm.
Every constant changed carries a numeric physical justification inline. Run `/jugaad-check`
before each commit. See `.claude/skills/physics-honest-fix/SKILL.md`.
