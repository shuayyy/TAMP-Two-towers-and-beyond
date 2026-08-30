---
name: physics-honest-fix
description: Use when fixing ANY failing behavior in this TAMP repo — a grasp that slips, a block that lands off-target, a plan that loops, a tower that topples. Enforces the project's no-workaround rule: defines exactly which fixes are legitimate physics fixes and which are banned jugaad, gives the diagnostic ladder to find the true root cause, and requires a physical justification for every constant you change. Load this BEFORE editing robot_adapter.py, planning.py, scenes.py, or any threshold in symbolic_abstraction.py / goal4_config.py.
---

# Physics-Honest Fixing

The owner of this repo has one hard rule: **no jugaad**. A goal counts as "working" only if it works
because the simulated physics made it work. Anything that produces a green checkmark without the
underlying mechanics being right is a failure, not a fix — it will look correct in a video and be
wrong on the website it is being built for.

This skill is the arbiter of that rule.

## The line

The question that separates a fix from a hack:

> If this same code ran on a real Franka with real 4 cm cubes, would it still work?

If the answer is no, it is jugaad. No exceptions for "just to get the video".

## Banned — these are jugaad, never do them

| Banned move | Why it is a lie |
|---|---|
| `obj.set_pos(...)` / `obj.set_quat(...)` to place or hold a block | Teleports mass through space. No contact, no friction, no momentum. This is the single biggest offender in this repo. |
| Widening a tolerance so a check passes (`XY_ALIGNMENT_THRESHOLD`, `POSITION_XY_THRESHOLD`, `Z_STACK_THRESHOLD`, the `dz > 0.008` grasp test) | Changes the definition of success instead of achieving it. A 2 cm "aligned" is not aligned. |
| Skipping, retrying-until-lucky, or `try/except: pass` around a failing action | Hides the failure. The next action then operates on a state that was never reached. |
| Disabling collision checking, or falling through to `control_dofs_position` when OMPL fails | Produces a path that drives the arm through solid objects. |
| Hardcoding a known-good qpos / position / plan for a specific goal | Overfits to one scene. The scenes are randomized (`_rand_xy`) precisely to prevent this. |
| Raising `squeeze_force` until the block stops slipping, with no force-balance argument | Cargo-culting a number. See "Justifying a constant" below. |
| Increasing settling steps until the state happens to read correctly | Masks an unstable placement rather than making the placement stable. |
| Making `abstract_state` read the intended state instead of the observed state | Breaks the whole point of a TAMP perception layer. |
| Reducing gravity, inflating friction to implausible values, freezing a block's DOFs | Changes the world to fit the code. |

## Legitimate — these are real fixes

- **Set physical material properties explicitly** — friction coefficients on cube and finger geoms,
  restitution, density. Not tuning them to absurd values, but setting them to *documented, physically
  plausible* ones (rubber-on-plastic mu is roughly 0.6–1.0; steel-on-plastic roughly 0.3–0.4).
- **Fix the grasp geometry** — finger tip offset, approach height, grasp width relative to the 4 cm cube.
  A grasp that closes on the block's corner rather than its face will always slip.
- **Fix the controller** — PD gains, force limits, trajectory timing, number of sim steps per waypoint.
  A grasp can fail purely because the arm accelerates faster than friction can hold the block.
- **Use force control correctly** — one control mode per DOF per step. Issuing both
  `control_dofs_position` and `control_dofs_force` to the same DOF is a bug, not a technique.
- **Increase simulation fidelity** — `substeps`, solver iterations, contact parameters. Slower is fine;
  the user has explicitly budgeted 3–6 hours per verification run.
- **Fix the IK / motion plan** — check IK convergence instead of assuming it, include the carried
  object in the collision model, plan over the arm DOFs rather than all 9.
- **Fix the symbolic layer to match reality** — if the planner loops because perception genuinely
  cannot observe a state the domain requires, the fix is to make the *placement* accurate enough,
  or to correct the *domain model*. Never to loosen the perception threshold.

## Justifying a constant

Any numeric constant you change must come with a one-line physical justification in the commit
message and, where it is non-obvious, an inline comment. Format:

    squeeze_force = 40.0  # 2 fingers x 40 N x mu=0.5 = 40 N friction >> 0.064 N block weight; 600x margin

If you cannot write that sentence, you do not yet understand the failure. Go back to the ladder.

Worked example for this repo — a 4 cm plastic cube at Genesis default density 1000 kg/m^3 weighs
6.4e-5 m^3 x 1000 = 0.064 kg, i.e. about 0.63 N. Two fingers gripping with normal force N and friction
coefficient mu hold it against gravity when `2 * mu * N > 0.63 N`. With mu = 0.5 that needs N > 0.63 N.
The repo currently uses `squeeze_force = 200.0`, which is ~300x that requirement — a number that large
is itself evidence that something else is wrong (most likely the grasp is not actually load-bearing,
because the kinematic weld is doing the work).

## The diagnostic ladder

Work top-down. Do not touch a constant until you have located the layer that is actually failing.

1. **Is it perception or physics?**
   Print the true pose from the simulator and the predicate set from `abstract_state` side by side.
   If the block is physically where it should be but the predicate is false, the bug is in the
   abstraction. If the block is not where it should be, the bug is below.

2. **Is it the plan or the execution?**
   Dump the PDDL problem and run pyperplan on it standalone. If the plan is wrong, the bug is in
   `problem_generator` / the domain / `abstract_state`. If the plan is right, the bug is in execution.

3. **Is it the motion or the grasp?**
   Log the end-effector pose at each stage against the commanded pose. If the hand never reaches the
   commanded pose, it is IK or control. If it reaches it and the block does not follow, it is the grasp.

4. **Is it the grasp or the release?**
   Log the block pose through close → lift → transport → descend → open. Find the first step where
   block pose stops tracking hand pose. That step is the failure.

5. **Only now touch a number** — and justify it as above.

## Before claiming a fix works

- The fix must survive **at least 3 consecutive runs** with different random seeds. `scenes.py`
  randomizes block XY by up to 5 cm; one lucky run proves nothing.
- The fix must not be conditional on goal id, block name, or iteration index unless the physics
  genuinely differs.
- State plainly in your report which layer the root cause was in, and why the change addresses it.

## Reporting a fix

Never say "fixed" without: the root cause layer, the physical reason, the number of clean runs, and
the video path. If a run failed, say so with the failure output. Reporting an unverified fix as
verified is the same category of error as jugaad.
