from typing import Set, Tuple
from pathlib import Path

# Must match your block names in blocks_state / abstract_state
BLOCK_NAMES = ["r", "g", "b", "y", "m", "c"]

DOMAIN_FILE = str(Path("pddl") / "domain_blocks.pddl")

# For Goal 4, we need 12 yellow blocks + 6 green blocks = 18 blocks total
# Yellow blocks: y1-y12 for the tower structure
# Green blocks: g1-g6 for the hollow square
GOAL4_YELLOW_BLOCKS = [f"y{i}" for i in range(1, 13)]  # y1, y2, ..., y12
GOAL4_GREEN_BLOCKS = [f"g{i}" for i in range(1, 7)]    # g1, g2, ..., g6
GOAL4_ALL_BLOCKS = GOAL4_YELLOW_BLOCKS + GOAL4_GREEN_BLOCKS

# Position naming convention for Goal 4:
# Yellow cross/plus: pos_<row>_<col>_<layer>
#   row: r1 (front), r2 (middle), r3 (back)
#   col: c1 (far left), c2 (left-center), c3 (right-center), c4 (far right)
#   layer: bottom, top
# Green square: pos_<x>_<y>_<z>
#   x: front, middle, back
#   y: left, center, right
#   z: bottom


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
        # Goal 4: Two structures
        # Structure 1: Yellow cross/plus (12 blocks) - 3D cross shape with 2 layers
        # Structure 2: Green hollow square (6 blocks) - all at z=bottom

        goal_preds = set()

        # ===== YELLOW CROSS/PLUS TOWER (12 blocks) =====
        # 3D cross shape: 3 rows × 4 columns × 2 layers
        # Pattern per layer (6 cubes):
        #   r1:      [c2][c3]
        #   r2: [c1]        [c4]
        #   r3:      [c2][c3]

        # Row 1 (front): 2 blocks at center columns [c2][c3]
        goal_preds.add(("at-position", "y1", "pos_r1_c2_bottom"))
        goal_preds.add(("ontable", "y1"))
        goal_preds.add(("at-position", "y2", "pos_r1_c3_bottom"))
        goal_preds.add(("ontable", "y2"))
        goal_preds.add(("at-position", "y3", "pos_r1_c2_top"))
        goal_preds.add(("on", "y3", "y1"))
        goal_preds.add(("at-position", "y4", "pos_r1_c3_top"))
        goal_preds.add(("on", "y4", "y2"))

        # Row 2 (middle): 2 blocks at far edges [c1] and [c4]
        goal_preds.add(("at-position", "y5", "pos_r2_c1_bottom"))
        goal_preds.add(("ontable", "y5"))
        goal_preds.add(("at-position", "y6", "pos_r2_c4_bottom"))
        goal_preds.add(("ontable", "y6"))
        goal_preds.add(("at-position", "y7", "pos_r2_c1_top"))
        goal_preds.add(("on", "y7", "y5"))
        goal_preds.add(("at-position", "y8", "pos_r2_c4_top"))
        goal_preds.add(("on", "y8", "y6"))

        # Row 3 (back): 2 blocks at center columns [c2][c3]
        goal_preds.add(("at-position", "y9", "pos_r3_c2_bottom"))
        goal_preds.add(("ontable", "y9"))
        goal_preds.add(("at-position", "y10", "pos_r3_c3_bottom"))
        goal_preds.add(("ontable", "y10"))
        goal_preds.add(("at-position", "y11", "pos_r3_c2_top"))
        goal_preds.add(("on", "y11", "y9"))
        goal_preds.add(("at-position", "y12", "pos_r3_c3_top"))
        goal_preds.add(("on", "y12", "y10"))

        # All yellow top blocks are clear
        for block in ["y3", "y4", "y7", "y8", "y11", "y12"]:
            goal_preds.add(("clear", block))

        # ===== GREEN HOLLOW SQUARE (6 blocks) =====
        # All at z=bottom, forming a ring with center empty
        # Positions: (front, center), (front, right), (middle, left),
        #            (middle, right), (back, left), (back, center)

        goal_preds.add(("at-position", "g1", "pos_front_center_bottom"))
        goal_preds.add(("ontable", "g1"))
        goal_preds.add(("clear", "g1"))

        goal_preds.add(("at-position", "g2", "pos_front_right_bottom"))
        goal_preds.add(("ontable", "g2"))
        goal_preds.add(("clear", "g2"))

        goal_preds.add(("at-position", "g3", "pos_middle_left_bottom"))
        goal_preds.add(("ontable", "g3"))
        goal_preds.add(("clear", "g3"))

        goal_preds.add(("at-position", "g4", "pos_middle_right_bottom"))
        goal_preds.add(("ontable", "g4"))
        goal_preds.add(("clear", "g4"))

        goal_preds.add(("at-position", "g5", "pos_back_left_bottom"))
        goal_preds.add(("ontable", "g5"))
        goal_preds.add(("clear", "g5"))

        goal_preds.add(("at-position", "g6", "pos_back_center_bottom"))
        goal_preds.add(("ontable", "g6"))
        goal_preds.add(("clear", "g6"))

        # Hand must be empty
        goal_preds.add(("handempty",))

        return goal_preds
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

    # Determine domain and objects based on goal_id
    if goal_id == 4:
        domain_name = "blocks-goal4"
        domain_file_name = "domain_blocks_goal4.pddl"

        # For Goal 4, use the 18 blocks (12 yellow + 6 green)
        blocks_str = " ".join(GOAL4_ALL_BLOCKS) + " - block"

        # Define all positions for Goal 4
        positions = [
            # Yellow cross/plus positions (3 rows × 4 columns × 2 layers)
            # Row 1 (front)
            "pos_r1_c2_bottom", "pos_r1_c3_bottom",
            "pos_r1_c2_top", "pos_r1_c3_top",
            # Row 2 (middle)
            "pos_r2_c1_bottom", "pos_r2_c4_bottom",
            "pos_r2_c1_top", "pos_r2_c4_top",
            # Row 3 (back)
            "pos_r3_c2_bottom", "pos_r3_c3_bottom",
            "pos_r3_c2_top", "pos_r3_c3_top",

            # Green hollow square positions (3×3 grid with center empty, z=bottom only)
            "pos_front_center_bottom",
            "pos_front_right_bottom",
            "pos_middle_left_bottom",
            "pos_middle_right_bottom",
            "pos_back_left_bottom",
            "pos_back_center_bottom",
            "pos_middle_center_bottom",  # center (empty in goal)
        ]
        positions_str = " ".join(positions) + " - position"

        objects_str = f"{blocks_str}\n    {positions_str}"

        # Add position-free predicates to init for all goal positions
        position_free_preds = [(("position-free", p),) for p in positions]

        # Update positions string
        positions_str = " ".join(positions) + " - position"
        objects_str = f"{blocks_str}\n    {positions_str}"

        init_predicates = current_predicates.union(
            set(p[0] for p in position_free_preds)
        )

    else:
        domain_name = "blocks"
        domain_file_name = "domain_blocks.pddl"
        objects_str = " ".join(BLOCK_NAMES) + " - block"
        init_predicates = current_predicates

    # (b) Init: build from current_predicates
    init_lines = [predicate_to_pddl_line(p) for p in sorted(init_predicates)]
    init_str = "\n    ".join(init_lines)

    # (c) Goal: build from goal_predicates
    goal_lines = [predicate_to_pddl_line(p) for p in sorted(goal_predicates)]
    goal_str = "\n      ".join(goal_lines)

    problem_text = f"""(define (problem {problem_name})
  (:domain {domain_name})
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
