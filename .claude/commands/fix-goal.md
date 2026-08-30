---
description: Autonomously diagnose and fix one TAMP goal until it passes 3 headless runs, with no workarounds
argument-hint: <goal 1-4> [scene 1|2]
---

Get goal `$1` (scene `$2`, default 1) actually working. This is the main working command.

Non-negotiable: load the `physics-honest-fix` skill first and obey it. Every fix must be a real physics
or logic fix. No teleporting objects, no loosened tolerances, no skipped failures, no hardcoded answers.
A goal that "passes" via a workaround is worse than a goal that fails, because it hides the defect.

Procedure:

1. Load `physics-honest-fix` and read the known-breakage list in `CLAUDE.md`.

2. Establish the current failure. Run once headless and capture exactly where and how it fails —
   which iteration, which action, which layer. Use the diagnostic ladder from the skill; do not guess.

3. Fix the root cause, lowest layer first. The dependency order for this repo is:
   headless/video path → physics & materials → grasp geometry → control → motion planning →
   symbolic abstraction → PDDL domain → executive loop. A bug in a lower layer will masquerade as
   several bugs in the layers above it, so never fix upward first.

4. After each fix, re-run headless and re-verify with the `goal-verify` skill.

5. Repeat until 3 consecutive runs pass with different random seeds. `scenes.py` re-seeds from wall
   clock on every run, so this genuinely tests robustness.

6. Commit each verified fix separately, with the physical justification in the message. Do not batch
   unrelated fixes into one commit.

Report: root cause per fix, the layer it lived in, the physical justification for any constant changed,
and the final 3/3 evidence with video paths. If you could not get it passing, say exactly where it
stands and what the remaining blocker is — do not report partial success as success.

For a heavier multi-agent attack on a stubborn failure, run the `fix-goal-loop` workflow instead.
