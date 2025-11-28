from typing import Set, Tuple
from pathlib import Path

# Must match your block names in blocks_state / abstract_state
BLOCK_NAMES = ["r", "g", "b", "y", "m", "c"]

DOMAIN_FILE = str(Path("pddl") / "domain_blocks.pddl")


# ----- 1. Hard-code goal predicates per goal_id -----

def get_goal_predicates(goal_id: int) -> Set[Tuple]:
    """
    Return the goal predicates as a set of tuples, SAME FORMAT
    as abstract_state() output.
    """
    if goal_id == 1:
        # Goal 1: two towers
        # Tower 1: r-g-b (top to bottom)
        # Tower 2: y-m-c (top to bottom)
        return {
            ("ontable", "b"),
            ("on", "g", "b"),
            ("on", "r", "g"),
            ("clear", "r"),

            ("ontable", "c"),
            ("on", "m", "c"),
            ("on", "y", "m"),
            ("clear", "y"),
            ("handempty",),
        }

    elif goal_id == 2:
        # Goal 2: 6-block tower (top→bottom: M-Y-B-R-G-C)
        return {
            ("ontable", "g"),
            ("on", "r", "g"),
            ("on", "b", "r"),
            ("on", "y", "b"),
            ("on", "m", "y"),
            ("clear", "m"),
            ("handempty",),
        }
    elif goal_id == 3:
        # Goal 3: (BONUS) 6-block tower (top→bottom: M-Y-B-R-G-C)
        return {
            ("ontable", "c"),
            ("on", "g", "c"),
            ("on", "r", "g"),
            ("on", "b", "r"),
            ("on", "y", "b"),
            ("on", "m", "y"),
            ("clear", "m"),
            ("handempty",),
        }
    elif goal_id == 4:
        # Goal 4: Special Structure (not specified yet)
        raise NotImplementedError("Goal 4 predicates are not defined.")
    else:
        raise ValueError(f"Unknown goal_id: {goal_id}")


# ----- 2. Helper: convert predicates to PDDL strings -----

def predicate_to_pddl_line(pred: Tuple) -> str:
    """
    ('ontable', 'b')   -> '(ontable b)'
    ('on', 'g', 'b')   -> '(on g b)'
    ('handempty',)     -> '(handempty)'
    """
    name = pred[0]
    args = pred[1:]
    if len(args) == 0:
        return f"({name})"
    return f"({name} {' '.join(args)})"


# ----- 3. Main function: write a PDDL problem file -----

def make_problem_pddl(current_predicates: Set[Tuple],
                      goal_id: int,
                      problem_name: str = "blocks-problem") -> str:
    """
    Create a PDDL problem file from current_predicates + chosen goal.

    Returns:
        Path to the written .pddl file as string.
    """
    goal_predicates = get_goal_predicates(goal_id)

    # (a) Objects: just use the known block names
    objects_str = " ".join(BLOCK_NAMES) + " - block"

    # (b) Init: build from current_predicates
    init_lines = [predicate_to_pddl_line(p) for p in sorted(current_predicates)]
    init_str = "\n    ".join(init_lines)

    # (c) Goal: build from goal_predicates
    goal_lines = [predicate_to_pddl_line(p) for p in sorted(goal_predicates)]
    goal_str = "\n      ".join(goal_lines)

    problem_text = f"""(define (problem {problem_name})
  (:domain blocks)
  (:objects
    {objects_str}
  )
  (:init
    {init_str}
  )
  (:goal
    (and
      {goal_str}
    )
  )
)
"""

    # Decide output path
    problem_path = Path("pddl") / f"{problem_name}_goal{goal_id}.pddl"
    problem_path.write_text(problem_text)

    return str(problem_path)
