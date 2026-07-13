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


def reorder_plan_by_layers(plan: List[Action]) -> List[Action]:
    """
    Reorder a plan to ensure bottom-layer blocks are placed before top-layer blocks.

    For Goal 4 yellow cross structure:
    - Bottom layer positions end with '_bottom'
    - Top layer positions end with '_top'

    Strategy: Group PICKUP + PUTDOWN/STACK pairs, then separate by layer.
    """
    bottom_layer_pairs = []  # [(PICKUP, PUTDOWN-AT/STACK-AT), ...]
    top_layer_pairs = []
    other_actions = []

    i = 0
    while i < len(plan):
        action = plan[i]
        action_name = action[0]

        # Look for PICKUP followed by PUTDOWN-AT or STACK-AT
        if action_name in ['PICKUP', 'PICKUP-AT']:
            if i + 1 < len(plan):
                next_action = plan[i + 1]
                next_name = next_action[0]

                if next_name == 'PUTDOWN-AT' and len(next_action) >= 3:
                    position = next_action[2]
                    pair = [action, next_action]
                    if position.endswith('_bottom'):
                        bottom_layer_pairs.append(pair)
                    elif position.endswith('_top'):
                        top_layer_pairs.append(pair)
                    else:
                        other_actions.extend(pair)
                    i += 2  # Skip both actions
                    continue

                elif next_name == 'STACK-AT' and len(next_action) >= 5:
                    top_position = next_action[4]
                    pair = [action, next_action]
                    if top_position.endswith('_top'):
                        top_layer_pairs.append(pair)
                    elif top_position.endswith('_bottom'):
                        bottom_layer_pairs.append(pair)
                    else:
                        other_actions.extend(pair)
                    i += 2  # Skip both actions
                    continue

        # If not part of a PICKUP+PLACE pair, add to others
        other_actions.append(action)
        i += 1

    # Sort pairs by position for efficient execution
    def get_position_key(pair):
        """Extract position name from action pair for sorting."""
        # pair is [PICKUP/PICKUP-AT, PUTDOWN-AT/STACK-AT]
        place_action = pair[1]

        if place_action[0] == 'PUTDOWN-AT' and len(place_action) >= 3:
            return place_action[2]  # position name
        elif place_action[0] == 'STACK-AT' and len(place_action) >= 5:
            return place_action[4]  # top position name
        return ""

    # Sort bottom and top layer pairs by position name
    # This groups adjacent positions together (e.g., r1_c2, r1_c3, then r2_c1, r2_c4, etc.)
    bottom_layer_pairs.sort(key=get_position_key)
    top_layer_pairs.sort(key=get_position_key)

    # Flatten pairs back to action list
    bottom_actions = [act for pair in bottom_layer_pairs for act in pair]
    top_actions = [act for pair in top_layer_pairs for act in pair]

    # Reconstruct: bottom layer first, then top layer, then others
    reordered = bottom_actions + top_actions + other_actions

    if len(bottom_layer_pairs) > 0 or len(top_layer_pairs) > 0:
        print(f"[PLAN REORDER] Bottom layer action pairs: {len(bottom_layer_pairs)}")
        print(f"[PLAN REORDER] Top layer action pairs: {len(top_layer_pairs)}")
        print(f"[PLAN REORDER] Other actions: {len(other_actions)}")
        if bottom_layer_pairs:
            print(f"[PLAN REORDER] Bottom layer order: {[get_position_key(p) for p in bottom_layer_pairs]}")
        if top_layer_pairs:
            print(f"[PLAN REORDER] Top layer order: {[get_position_key(p) for p in top_layer_pairs]}")

    return reordered


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
        print("[task_planner] WARNING: Plan file parsed but no actions found.")
        print("[task_planner] Raw plan content:")
        print(plan_text)
        raise RuntimeError("No actions parsed from plan output.")

    print("[task_planner] Parsed plan:")
    for i, act in enumerate(plan):
        print(f"  {i}: {act}")

    # 5) Reorder plan to ensure bottom-layer-first execution (Goal 4 only)
    if goal_id in [4, 41, 42]:
        plan = reorder_plan_by_layers(plan)
        print("\n[task_planner] Reordered plan (bottom-layer first):")
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