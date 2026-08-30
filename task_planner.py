"""
Task Planner Integration (Phase 3)

This module connects:
  - Phase 1: symbolic_abstraction.abstract_state(...)
  - Phase 2: pddl.problem_generator.make_problem_pddl(...)
  - pyperplan: external planner

Goal:
  plan_symbolic(predicates, goal_id) -> list of high-level actions

Each action is a tuple, e.g.:
  ("PICKUP", "r")
  ("STACK", "r", "g")
  ("UNSTACK", "r", "g")
  ("PUTDOWN", "r")

Author: Ajay (Phase 3)
"""

from typing import List, Tuple, Set
import subprocess
from pathlib import Path

from pddl.problem_generator import make_problem_pddl, DOMAIN_FILE

# Domain file mapping for different goals
def get_domain_file(goal_id: int) -> str:
    """Return the appropriate domain file for the given goal_id."""
    if goal_id in [4, 41, 42]:
        return str(Path("pddl") / "domain_blocks_goal4.pddl")
    else:
        return DOMAIN_FILE


Action = Tuple[str, ...]  # e.g. ("STACK", "r", "g")


def run_pyperplan(domain_file: str, problem_file: str, goal_id: int = 1) -> str:
    """
    Call pyperplan using its Python API directly.

    Args:
        domain_file: Path to PDDL domain file
        problem_file: Path to PDDL problem file
        goal_id: Goal identifier (used to select appropriate planner)

    Returns:
        plan_text: the plan actions (one action per line).
    """
    try:
        # Import pyperplan modules
        from pyperplan import planner
        from pyperplan.heuristics.relaxation import hFFHeuristic

        # Use A* for optimal plans on small problems (Goals 1-3)
        # Use Enforced Hill-Climbing for faster planning on large problems (Goal 4)
        if goal_id in [4, 41, 42]:
            from pyperplan.search import enforced_hillclimbing_search
            print("[task_planner] Running pyperplan with Enforced Hill-Climbing (fast for Goal 4)...")
            plan = planner.search_plan(domain_file, problem_file, enforced_hillclimbing_search, hFFHeuristic)
        else:
            from pyperplan.search import astar_search
            print("[task_planner] Running pyperplan with A* (optimal for Goals 1-3)...")
            plan = planner.search_plan(domain_file, problem_file, astar_search, hFFHeuristic)
        
        if plan is None:
            raise RuntimeError("Pyperplan returned no plan (unsolvable problem?)")
        
        # Convert plan operators to string format
        # Each operator in plan is an Op object with a .name attribute like "(pickup r)"
        plan_actions = [str(op.name) for op in plan]
        
        # Write the plan to .soln file
        problem_path = Path(problem_file)
        soln_path = problem_path.with_suffix(".soln")
        plan_text = '\n'.join(plan_actions)
        soln_path.write_text(plan_text)
        
        print(f"[task_planner] Plan found with {len(plan_actions)} actions")
        print(f"[task_planner] Plan saved to {soln_path}")
        
        return plan_text
        
    except ImportError:
        # Fallback to subprocess if pyperplan not importable
        print("[task_planner] Could not import pyperplan, falling back to subprocess...")
        return _run_pyperplan_subprocess(domain_file, problem_file)
    except Exception as e:
        print(f"[task_planner] Error running pyperplan: {e}")
        raise


def _run_pyperplan_subprocess(domain_file: str, problem_file: str) -> str:
    """
    Fallback method: Call pyperplan via subprocess.
    """
    cmd = [
        "python3",
        "-m",
        "pyperplan",
        domain_file,
        problem_file,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    stdout = result.stdout or ""
    stderr = result.stderr or ""

    if result.returncode != 0:
        print("[task_planner] pyperplan subprocess failed.")
        print("[task_planner] STDOUT:\n", stdout)
        print("[task_planner] STDERR:\n", stderr)
        raise RuntimeError("Pyperplan failed; see logs above.")

    # Check if .soln file was created
    problem_path = Path(problem_file)
    soln_path = problem_path.with_suffix(".soln")

    if soln_path.exists():
        plan_text = soln_path.read_text()
        print(f"[task_planner] Plan loaded from {soln_path}")
        return plan_text

    print("[task_planner] ERROR: No .soln file created and no plan in output")
    print("[task_planner] STDOUT:\n", stdout)
    raise RuntimeError("No plan found from pyperplan subprocess.")


def parse_plan(plan_text: str) -> List[Action]:
    """
    Parse a .soln plan file into a list of action tuples.

    Typical .soln format (pyperplan):
        (pickup r)
        (stack r g)
        (pickup y)
        (stack y m)

        Goal 4 actions:
        (putdown-at y1 pos_r1_c2_bottom)
        (stack-at y3 y1 pos_r1_c2_bottom)

    We:
      - ignore empty lines and comment lines starting with ';'
      - expect each non-empty line to contain exactly one '(action ...)' term
      - action name -> upper-case (PUTDOWN-AT), args -> lower-case
      - supports variable-length arguments for Goal 4 position actions
    """
    plan: List[Action] = []

    for line in plan_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(";"):
            continue

        if "(" not in line or ")" not in line:
            continue

        try:
            start = line.index("(")
            end = line.rindex(")")
        except ValueError:
            continue

        inside = line[start + 1:end].strip()
        if not inside:
            continue

        tokens = inside.split()
        if not tokens:
            continue

        action_name = tokens[0].upper()
        args = [t.lower() for t in tokens[1:]]
        plan.append((action_name, *args))

    return plan


def plan_symbolic(current_predicates: Set[Tuple],
                  goal_id: int,
                  problem_name: str = "demo_goal") -> List[Action]:
    """
    Main API for Phase 3.

    Input:
        current_predicates: set of tuples from abstract_state(...)
        goal_id: which goal to plan for (1 = two towers, etc.)
        problem_name: base name for the generated PDDL problem file

    Output:
        plan: list of actions as tuples, e.g.
              [
                ("UNSTACK", "r", "g"),
                ("PUTDOWN", "r"),
                ("PICKUP", "y"),
                ("STACK", "y", "m"),
                ...
              ]

        If no plan is found or parsing fails, we raise RuntimeError.
    """
    # 1) Generate PDDL problem file from current predicates + goal spec
    problem_file = make_problem_pddl(
        current_predicates=current_predicates,
        goal_id=goal_id,
        problem_name=problem_name,
    )

    # 2) Get the appropriate domain file for this goal
    domain_file = get_domain_file(goal_id)

    print(f"[task_planner] Using DOMAIN:  {domain_file}")
    print(f"[task_planner] Using PROBLEM: {problem_file}")

    # 3) Run pyperplan (extracts plan from stdout or .soln) and read plan text
    # Pass goal_id to select appropriate planner (A* for 1-3, EHC for 4)
    plan_text = run_pyperplan(domain_file, problem_file, goal_id=goal_id)

    # 4) Parse the plan text
    plan = parse_plan(plan_text)

    if not plan:
        # An empty plan is SUCCESS, not failure: pyperplan returns a zero-action plan when
        # the goal already holds in the initial state. run_pyperplan() has already raised
        # for the genuinely unsolvable case (search_plan returns None), so reaching here
        # with no actions means there is nothing left to do.
        #
        # This used to raise, which made demo.py's "if not plan: GOAL REACHED" branch
        # unreachable — every successful run was reported as a planning error.
        print("[task_planner] Empty plan: goal already satisfied in the current state.")
        return []

    print("[task_planner] Parsed plan:")
    for i, act in enumerate(plan):
        print(f"  {i}: {act}")

    # NOTE: this used to pass goal-4 plans through reorder_plan_by_layers(). That reorder
    # is both unnecessary and provably harmful:
    #
    #   * unnecessary -- bottom-before-top is already enforced by the DOMAIN: stack-at
    #     requires (at-position ?y ?p-bottom), so no valid plan can place a top block
    #     before its support is in position. The planner's own order is always sound.
    #
    #   * harmful -- it paired PICKUP+PLACE actions and moved unpaired actions to the
    #     end. When execution is closed-loop, a plan computed while the hand is already
    #     holding a block BEGINS with an unpaired putdown-at/stack-at. The reorder
    #     shuffled that mandatory first action to the back, so the executed first action
    #     became a PICKUP with the hand full: pick() opened the gripper, dropped the held
    #     block wherever the arm was, and grabbed the other one -- observed as an endless
    #     PICKUP y1 / PICKUP y2 alternation with every grasp succeeding and nothing ever
    #     placed.
    return plan


# ---- Quick standalone test (optional) ----

if __name__ == "__main__":
    from symbolic_abstraction import abstract_state
    from scenes import create_scene_6blocks
    import genesis as gs
    import numpy as np

    print("\n[task_planner] Standalone test: plan from current 6-block scene\n")

    gs.init(backend=gs.cpu, logging_level="Warning", logger_verbose_time=False)
    scene, robot, blocks_state = create_scene_6blocks()
    robot.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    robot.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))
    for _ in range(100):
        scene.step()

    current_predicates = abstract_state(scene, robot, blocks_state)
    print("[task_planner] Current predicates:", current_predicates)

    plan = plan_symbolic(current_predicates, goal_id=1, problem_name="test_goal1")
    print("\n[task_planner] Final plan returned by plan_symbolic():")
    for step, action in enumerate(plan):
        print(f"  {step}: {action}")