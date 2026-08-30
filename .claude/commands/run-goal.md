---
description: Run one TAMP goal headless, record video, and verify it against the acceptance criteria
argument-hint: <goal 1-4> [scene 1|2] [runs, default 3]
---

Run goal `$1` headless and verify it. Scene = `$2` (default 1). Repeat runs = `$3` (default 3).

Procedure:

1. Read `CLAUDE.md` for the current known-breakage list and the verified headless-video recipe. Do not
   re-derive the Genesis API from memory — use what is recorded there.

2. Ensure the run is genuinely headless and recording. If the repo cannot yet do this, say so and stop —
   do not fake a video, and do not fall back to an on-screen run and call it headless.

3. Launch with `run_in_background: true`. These runs take minutes to hours; never block the foreground,
   and never poll with `sleep`. Use Monitor with an until-condition on the log, or wait for the
   completion notification.

   Always: `conda run -n rbe550 python demo.py --goal $1 ...`. The `base` env has no ompl/pyperplan and
   will fail immediately.

4. Write all output under `runs/goal$1_scene$2/<run-index>/` — stdout log, video, and a JSON summary.

5. When each run finishes, load the `goal-verify` skill and apply every acceptance criterion. Check the
   video with ffprobe. Do not trust the demo's own `GOAL REACHED` print.

6. Report per the `goal-verify` reporting format: PASS n/N with evidence, or FAIL with the specific
   reason each failing run failed and which layer it failed in.

If a run fails, do not attempt a quick patch inside this command — report the failure and its root-cause
layer. Fixing is `/fix-goal`, which enforces the no-jugaad rules.
