# Session state — resume point

**Last updated: 2026-08-29 ~23:55.**

Read this together with `CLAUDE.md` (rules, environment) before doing anything.

---

## Where things stand — ALL FOUR GOALS WORK

| Goal | Scene | Status | Evidence |
|---|---|---|---|
| **1** — two towers (B-G-R, C-M-Y) | 1 scattered | **PASS 3/3+** | XY dev 0.35–0.63 mm |
| **1** | 2 pre-stacked | **PASS 3/3** | XY dev 1.07–1.48 mm |
| **2** — 5-block tower (G-R-B-Y-M) | 1 scattered | **PASS 3/3+** | XY dev 0.30–0.47 mm |
| **2** | 2 pre-stacked | **PASS 3/3** | XY dev 0.51–0.95 mm (one run leaned 14 mm — see "open") |
| **3** — tallest tower (bonus) | 1 | **CLOSED at 6 blocks** per owner's decision (2 pts/block over 5 = partial credit banked). Do not spend more time here. |
| **4** — yellow cross + green square | 1 | **GOAL 4 FULLY COMPLETED** — first full run 23:53, 9.5 min, all 18 blocks within the 2 mm threshold, video. Second reproducibility run in flight at time of writing (`runs/verify/b8_goal4_2`). |

Goal 2 is a **5-block** tower (M-Y-B-R-G top-down) per the assignment PDF — the README used to
claim 6 blocks; the predicates were always right, the docs were wrong (fixed).

## Commits (chronological)

| SHA | What |
|---|---|
| `a9c7b9b` | Core physics: gravity compensation, weld removal, gripper, descent, IK checks, empty-plan bug, headless video |
| `2903759` | Wrist-tilt ladder for edge-of-workspace blocks |
| `05615e5` | PUTDOWN picks a clear reachable table spot |
| `9648a9a` | STATE.md checkpoint |
| `0011ca8` | Spurious 90° stack rotation · safe transit height · no-sweep pick approach · `--video-every` RAM cap |
| `c371b08` | **Goal 4**: plain `putdown` in domain (deadlock fix) · closed-loop executive · reorder removed · Cartesian carry · loop detection |

Working tree at time of writing: clean except runs/ artifacts.

---

## The 16 defects fixed this session (all measured, none papered over)

1. **No gravity compensation** — joint 2 sagged 0.0158 rad, 82 % torque-saturated. THE keystone: placement 15 mm → 0.4 mm.
2. **Kinematic weld faked the grasp** — correction loop diverged 3.2 → 8.5 mm; real friction grasp proven (150 mm lift at default friction).
3. **200 N squeeze crushed the cube** — 20 N force-close ends at width −0.0006, DROPPED. Position-close seats at 0.0396.
4. **Descent overshoot** — 30-step descent drove fingertips to z = 0 (into the table). Now 150 steps + verified height.
5. **IK never checked** — `return_error=True` now used everywhere (`_ik()`).
6. **Empty plan raised** — success was reported as planning failure.
7. **No headless/video; demo never exited** — `recording.py`, `--headless/--video[-every]`, clean exit.
8. **PUTDOWN used one fixed target** — accidental stacks → infinite loop. Now `find_free_table_spot()`.
9. **Spurious 90° wrist rotation on every stack** — the support block matched as a "neighbour" at distance 0. Height filter added; goal-4's needed same-layer rotation preserved.
10. **Carried block invisible to OMPL collision checking (transit)** — block thrown 2.1 m through scene-2's tower. `_safe_transit_hand_z()`.
11. **Video frames buffered in RAM** — goal 4 OOM-killed at ~12 GB. `--video-every`.
12. **Pick approach swept blocks** — blind joint-space interpolation shoved R 0.398 → 0.262 m over 4 attempts. Three-stage lift-translate-descend.
13. **Goal-4 domain deadlock** — no plain `putdown`; a lifted mis-placed block could never be released. Proven unsolvable (EHC *and* A*) → 12-action recovery plan after fix.
14. **Goal-4 open-loop batching** — 16 actions on stale perception; flings of 2.2 / 2.6 m. Now closed-loop (1 action/cycle), as the assignment specifies.
15. **`reorder_plan_by_layers` invalidated valid plans** — buried the mandatory in-progress `putdown-at`, causing PICKUP-with-full-hand alternation (16 grasps, 0 placements). Removed; the domain's `stack-at` preconditions already guarantee bottom-first.
16. **OMPL carry lost the held block** — g3 found 2.88 m away after its own transit. Cartesian straight-line carry at safe height, 2 cm steps. Yellow cross: 84 actions with rework → 24 actions, zero rework.

### Hypotheses tested and DISCARDED (do not revisit)

- `hand_to_finger_tip_z = 0.12` suspected wrong → calibration shows 0.12 is optimal. True fingertip offset 0.1124 m (used in diagnostics only).
- IK suspected failing → residual 0.03 mm; the arm was gravity-drooping instead.
- **Friction suspected for post-release tower lean → drift experiment exonerates it**: 1 mm-offset towers drift 0.3 mm in 20 s at ALL frictions incl. default; 5 mm-offset towers collapse at ALL frictions identically. The lean is robot contact, not sliding. Friction stays default.

## Open (quality items, not blockers)

- **Goal 2 scene 2 occasionally leans** (worst 14.45 mm; the abstraction's criterion is 15 mm, my verifier's stricter bar is 10 mm). Candidate root cause: `place()` presses the held block to exact Z (`release_clearance = 0.0`) before opening — if the tower sits fractionally tall the arm loads the stack. Honest fix candidate: release with ~1 mm clearance. **Not tolerance-widening.**
- **Goal-4 verifier**: `verify_goal.py` covers goals 1–3 geometrically; goal 4's completion is currently certified by the perception layer's own 2 mm `at-position` check (strict, but not independent). An independent check would parse final poses against `GOAL4_POSITION_COORDS`.
- `run_goal4` doesn't print final block positions — add `print_block_positions` at phase ends if the independent verifier is built.

## Measured constants (trust these over comments)

Fingertip 0.1124 m below hand frame · seated 4 cm cube reads width 0.0396 · cube mass 12.8 g = 0.126 N · top-down grasp limit **r ≈ 0.79 m** (not 0.855) · 25° wrist tilt reaches r ≈ 0.832 · goal-4 positions max r = 0.7754 (all reachable straight-down) · Genesis buffers ~0.65 MB/frame at 640×360 (18 000 frames ≈ 12 GB → OOM).

## How to run

```bash
# any goal, headless + video (always via xvfb-run)
xvfb-run -a -s "-screen 0 1280x720x24" conda run -n rbe550 python demo.py \
    --goal 4 --headless --video runs/x/run.mp4 --video-res 480x270 --video-every 40 \
    --max-iterations 80

# verification (goals 1–3; derives expected stacks from the goal spec)
conda run -n rbe550 python verify_goal.py --goal 1 runs/*/run.log
```

Goal-4 runs: ~10 min at `--video-every 40`, 480×270. One sim at a time. Background always;
poll `runs/STATUS.txt`, never the logs.
