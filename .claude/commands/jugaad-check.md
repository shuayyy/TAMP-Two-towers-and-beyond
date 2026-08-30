---
description: Audit the working diff for workarounds, fake physics, and loosened thresholds
argument-hint: [git ref to diff against, default HEAD]
---

Audit every change in the diff against `${1:-HEAD}` for jugaad. This is the guard that keeps the "no
workarounds" rule real rather than aspirational — run it before every commit and before reporting any
goal as working.

Load the `physics-honest-fix` skill for the full banned/legitimate taxonomy, then check the diff for:

- Direct object pose manipulation: `set_pos` / `set_quat` on any block entity, or any new kinematic
  weld or sync-to-hand mechanism.
- Any threshold that got looser: `XY_ALIGNMENT_THRESHOLD`, `Z_STACK_THRESHOLD`, `HOLDING_THRESHOLD`,
  `POSITION_XY_THRESHOLD`, `POSITION_Z_THRESHOLD`, `tol_xy`, the grasp-success `dz` test, the
  displacement sanity check. Compare old vs new numerically and flag every increase.
- Silently swallowed failures: new bare `except`, `except: pass`, `return True` on an error path, or a
  failed action that no longer stops the loop.
- Collision checking weakened: `ignore_collisions=True` added, a validity checker that returns True
  more often, or a new fallback that drives to a goal without a planned path.
- Constants changed with no physical justification in the comment or commit message.
- Anything keyed to a specific goal id, block name, scene, or iteration index that encodes a known
  answer rather than a general rule.
- Increased settling steps or retry counts used to paper over instability.

For each hit, report: file:line, what changed, why it is or is not legitimate, and what the honest fix
would be instead. Be willing to conclude the diff is clean — do not manufacture findings.
