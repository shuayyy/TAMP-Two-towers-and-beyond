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


Action = Tuple[str, ...]  # e.g. ("STACK", "r", "g")


def run_pyperplan(domain_file: str, problem_file: str) -> str:
    """
    Call pyperplan using its Python API directly.

    Returns:
        plan_text: the plan actions (one action per line).
    """
    try:
        # Import pyperplan modules
        from pyperplan import planner
        from pyperplan.search import breadth_first_search
        
        print("[task_planner] Running pyperplan via Python API...")
        
        # Use pyperplan's search_plan function which returns a list of operators
        plan = planner.search_plan(domain_file, problem_file, breadth_first_search, None)
        
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
        ...

    We:
      - ignore empty lines and comment lines starting with ';'
      - expect each non-empty line to contain exactly one '(action ...)' term
      - action name -> upper-case, args -> lower-case
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

    print(f"[task_planner] Using DOMAIN:  {DOMAIN_FILE}")
    print(f"[task_planner] Using PROBLEM: {problem_file}")

    # 2) Run pyperplan (extracts plan from stdout or .soln) and read plan text
    plan_text = run_pyperplan(DOMAIN_FILE, problem_file)

    # 3) Parse the plan text
    plan = parse_plan(plan_text)

    if not plan:
        print("[task_planner] WARNING: Plan file parsed but no actions found.")
        print("[task_planner] Raw plan content:")
        print(plan_text)
        raise RuntimeError("No actions parsed from plan output.")

    print("[task_planner] Parsed plan:")
    for i, act in enumerate(plan):
        print(f"  {i}: {act}")

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