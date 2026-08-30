---
name: goal-verify
description: Use to decide whether a TAMP goal (1, 2, 3, 4) has ACTUALLY been achieved, rather than trusting the demo's own "GOAL REACHED" print. Defines the acceptance criteria — settled physics, released gripper, observed predicates matching the goal spec, stable tower, and a real video file — plus the repeat-runs requirement and the exact evidence to report. Load this after any headless run, and before telling the user a goal works.
---

# Goal Verification

`demo.py` prints `GOAL REACHED!` whenever pyperplan returns an empty plan. That is a claim by the
planner about the *abstracted* state, not proof that the world is in the goal configuration. It can
fire on a state that is physically wrong if the abstraction is wrong. Never quote it as evidence.

A goal is verified only against the criteria below.

## Acceptance criteria — all must hold

1. **Physics is settled and the hand is clear.**
   After the last action: gripper open, `robot.attached_object is None`, and the scene stepped at
   least 300 more times with **no block moving more than 1 mm** over the final 100 steps. A tower
   that is still settling is a tower that may still topple.

2. **The observed state matches the goal spec.**
   Recompute `abstract_state(...)` fresh at the end and compare against
   `get_goal_predicates(goal_id)`. Every goal predicate must be present. Report any missing ones
   explicitly. Do not accept "close enough".

3. **Independent geometric check — do not trust the abstraction alone.**
   The abstraction is itself suspect code. Verify the structure directly from raw block poses:
   - Goal 1: two disjoint stacks, each 3 tall, correct colour order bottom→top (B-G-R and C-M-Y),
     each neighbouring pair within 1.5 cm in XY and 4 cm ± 5 mm in Z.
   - Goal 2: one stack, 6 tall, order C-G-R-B-Y-M bottom→top.
   - Goal 3: one stack, 8 tall, order C-G-R-B-Y-M-O-P bottom→top; top block centre near z = 0.30.
   - Goal 4: 12 yellow blocks forming the 2-layer cross at the `goal4_config` coordinates, and
     6 green blocks forming the hollow square with the centre cell empty.

4. **The tower is stable, not balanced.**
   Step 500 additional frames after the structure is complete. It must still satisfy criterion 3.
   Falling over after the demo prints success is a failure.

5. **A real video exists.**
   The file must exist, be non-zero, and be readable by ffprobe with a sane duration and frame count:
   `ffprobe -v error -show_entries format=duration:stream=nb_frames,width,height -of default=nw=1 <file>`
   A 0-byte or 0-frame file means the render path silently failed — treat as a failed run.

6. **Reproducible across seeds.**
   `scenes.py` calls `random.seed(time.time())` and jitters block XY by up to 5 cm, so every run is a
   different problem instance. **3 consecutive passes minimum** before reporting a goal as working.
   One pass is an anecdote.

## Reporting

Report exactly this, per goal:

    Goal N (scene S): PASS 3/3   video: runs/<...>.mp4  (Xs, N frames)
      final predicates: all M goal predicates satisfied
      geometric check:  stack order verified, max XY dev 4.2 mm, max Z dev 1.1 mm
      stability:        +500 steps, max block drift 0.3 mm

or, on failure:

    Goal N (scene S): FAIL 1/3
      run 2: planner looped — (at-position y7 pos_r2_c1_top) never observed;
             y7 settled 3.4 mm from target, threshold is 2 mm
      run 3: block m toppled at iteration 9, drift 0.21 m

Never round a failure up. If 2 of 3 runs pass, the goal does not work yet — say so and say why the
third failed.

## Common false positives to watch for

- **Empty plan because the problem was unsolvable**, not because the goal was met. `plan_symbolic`
  raises on no-plan, but check the distinction: an empty parsed plan and a planning failure are
  different states and the demo's loop treats "no plan" as success.
- **Goal predicates satisfied while a block is still welded to the hand.** If `attached_object` is
  non-None, `handempty` is false, but a stale weld can still hold the block in a passing pose.
  Always confirm detachment.
- **`at-position` true for the wrong block.** Goal 4's yellow blocks are interchangeable in
  appearance but not in the goal spec; verify by name, not by colour.
- **Video that is all one frame**, produced when the camera rendered before `scene.build()` or when
  frames were captured but never encoded.
