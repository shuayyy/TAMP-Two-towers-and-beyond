# TAMP — Two Towers and Beyond

Task and Motion Planning for a Franka Panda stacking 4 cm cubes. Genesis simulator, OMPL for motion
planning, pyperplan (PDDL) for task planning.

**Current mission: this code used to work, then it was broken by many hands. Get all four goals working
again, verified by headless runs that produce video. Goals 1 and 2 first, then 3 and 4.**

---

## Environment — read this first

Always run Python through the project env. **The `base` env has no OMPL and no pyperplan and will fail
immediately.**

```bash
conda run -n rbe550 python demo.py --goal 1
```

| | |
|---|---|
| env | `rbe550` — python 3.11.14, genesis **0.3.6**, torch 2.5.1+cu121, numpy 2.3.3, ompl, pyperplan |
| genesis source | `~/miniconda3/envs/rbe550/lib/python3.11/site-packages/genesis` |
| GPU | RTX 4060 Laptop, 8 GB |
| CPU / RAM | 16 cores / 23 GB |
| display | `DISPLAY=:0` present, **Xvfb NOT installed**, ffmpeg present |

Genesis 0.3.6 is old. **Never assert a Genesis API from memory — read the installed source.** Newer
Genesis versions changed the camera and renderer APIs substantially, and guessing here wastes hours.

Only **one simulation at a time** — the GPU cannot host concurrent runs. Never fan out parallel agents
that each start a sim.

---

## The rule that governs everything: no jugaad

Every fix must be a real physics or logic fix. A goal that passes because a tolerance was widened, a
block was teleported, or a failure was swallowed **does not count as passing** — it produces a video
that looks right and a system that is wrong, which is the worst possible outcome for work going on a
portfolio site.

The test for any change: *would this still work on a real Franka with real cubes?*

Load `.claude/skills/physics-honest-fix/SKILL.md` before editing `robot_adapter.py`, `planning.py`,
`scenes.py`, or any threshold in `symbolic_abstraction.py` / `goal4_config.py`. It has the full
banned/legitimate taxonomy and the diagnostic ladder.

Every numeric constant you change needs a one-line physical justification, inline and in the commit
message. If you cannot write that sentence, you have not found the root cause yet.

---

## What counts as "working"

Not the demo printing `GOAL REACHED` — that only means pyperplan returned an empty plan for a possibly
wrong abstraction. Load `.claude/skills/goal-verify/SKILL.md`. In short:

1. Physics settled, gripper open, `attached_object is None`, no block drifting.
2. Fresh `abstract_state` matches `get_goal_predicates(goal_id)` completely.
3. Independent geometric check straight from raw block poses — do not trust the abstraction alone.
4. Structure still standing after 500 extra steps.
5. Video file exists and `ffprobe` reports sane duration and frame count.
6. **3 consecutive passes.** `scenes.py` re-seeds from wall clock and jitters block XY by up to 5 cm,
   so one pass proves nothing.

---

## Long runs

Verification runs take minutes to hours, and multi-hour sessions are expected and budgeted.

- Launch every run with `run_in_background: true`. Never block the foreground.
- Never poll with `sleep`. Use `Monitor` with an until-condition on the log file, or wait for the
  completion notification.
- Write output under `runs/goal<N>_scene<S>/<run-index>/` — log, video, JSON summary. `runs/` is
  gitignored.

---

## Priority order

Do not move on until the current item passes 3/3.

1. Goal 1, scene 1 (scattered)
2. Goal 1, scene 2 (pre-stacked — forces UNSTACK)
3. Goal 2
4. Goal 3
5. Goal 4.1 (yellow cross), then 4.2 (green square)

---

## Fix downward, never upward

A defect in a low layer shows up as several apparent defects in the layers above it. Always fix in
this order:

```
headless / video  →  physics & materials  →  grasp geometry  →  control  →
motion planning  →  symbolic abstraction  →  PDDL domain  →  executive loop
```

---

## Architecture

The TAMP loop in `demo.py`:

```
scene → abstract_state() → PDDL problem → pyperplan → plan → execute → re-perceive → repeat
```

| File | Layer | Role |
|---|---|---|
| `scenes.py` | world | Scene factories: 6 scattered / 6 pre-stacked / 8 / 18 blocks. Randomizes block XY. |
| `symbolic_abstraction.py` | lifting | Continuous poses → PDDL predicates (`ontable`, `on`, `clear`, `holding`, `handempty`; plus `at-position`, `position-free` for goal 4). |
| `pddl/problem_generator.py` | lifting | Writes the problem file. Goal specs are hardcoded per `goal_id` in `get_goal_predicates`. |
| `task_planner.py` | task | Runs pyperplan (A* + hFF for goals 1–3, EHC for goal 4), parses the plan. |
| `planning.py` | motion | OMPL joint-space planner (ABITstar) with collision checking. |
| `robot_adapter.py` | grounding | IK, pick/place, gripper control, and the object-attachment mechanism. |
| `goal4_config.py` | world | Named position → (x,y,z) map for goal 4 structures. |

Goal ids: `1`, `2`, `3`, `4`; goal 4 runs as sub-goals `41` (yellow cross) then `42` (green square).

---

## Commands

| Command | Use |
|---|---|
| `/run-goal <N> [scene] [runs]` | Headless run + video + verification. Reports PASS n/N with evidence. |
| `/fix-goal <N> [scene]` | The main working command: diagnose and fix until 3/3, no workarounds. |
| `/jugaad-check [ref]` | Audit the diff for workarounds. **Run before every commit.** |
| `/tamp-status` | Evidence-based status of all four goals and the next action. |

Workflows (multi-agent, for heavier attacks — invoke by name):

| Workflow | Use |
|---|---|
| `diagnose-tamp` | Read-only six-lens sweep of the whole repo. Refreshes the breakage list below. |
| `fix-goal-loop` | Competing root-cause analyses and fix designs, judged, then serial implement + verify. Args `{goal, scene, failure}`. |

---

## Repo hygiene

- Generated PDDL problems and `.soln` files are build output and are gitignored. 22 of them are still
  tracked from before; untrack with `git rm -r --cached pddl/*_goal*.pddl pddl/*.soln` when convenient.
- `docs/` holds development-session logs from the original team (`ALL_FIXES_SUMMARY.md`,
  `PLANNER_FIX.md`, …). Treat them as historical notes, not as current truth — several describe fixes
  that were later reverted or clobbered by merges.
- No tests and no dependency manifest exist. The pure functions (`is_on`, `is_clear`, `parse_plan`,
  `get_goal_predicates`, the goal-4 constraint generation) are all testable without the simulator.

---

## Current state — read `STATE.md` first

`STATE.md` is the live resume point: what passes, what is committed, the nine defects already
fixed with their measured evidence, hypotheses already tested and discarded, and the ordered
next actions. **Read it before starting work** so you do not re-investigate settled ground.

Summary as of 2026-08-29: goals 1 and 2 pass 3/3 from **both** scenes. Goal 3 (bonus) reaches
6 blocks then gets knocked over. Goal 4 is untouched and is the remaining required deliverable.

<!-- BREAKAGE-LIST -->
### Fixed (do not re-investigate — see STATE.md for evidence)

Gravity compensation missing · kinematic weld faking the grasp · 200 N squeeze crushing the
cube · descent overshoot into the table · IK convergence never checked · empty plan raising
instead of signalling success · no headless/video path and no clean exit · PUTDOWN using one
fixed target for every block.

### Open

- **Spurious 90° wrist rotation on every stack** — fix written in `robot_adapter.py`,
  syntax-checked, **not yet verified by a run**. Verify before committing.
- **Goal 3** — tower reaches 6 blocks then is knocked over on release. Bonus task, partial
  credit by design.
- **Goal 4** — not started. Suspects listed in `STATE.md`; the 2 mm `POSITION_XY_THRESHOLD`
  is the one to measure against, never to loosen.

### Measured constants (trust these over the code's comments)

Fingertip sits 0.1124 m below the hand frame · a seated 4 cm cube reads finger width 0.0396 ·
cube mass 12.8 g = 0.126 N · **top-down grasp reaches only r ≈ 0.79 m, not the quoted 0.855** ·
a 25° wrist tilt extends that to r ≈ 0.832, which is what `scenes.py` can spawn.
<!-- /BREAKAGE-LIST -->
