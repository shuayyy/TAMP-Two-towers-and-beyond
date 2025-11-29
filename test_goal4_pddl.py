#!/usr/bin/env python3
"""
Test script for Goal 4 PDDL generation and validation.

This script tests:
1. Generation of PDDL problem file for Goal 4
2. Validation of goal predicates
3. Display of the generated PDDL content
"""

from pathlib import Path
from pddl.problem_generator import get_goal_predicates, make_problem_pddl

def test_goal4_predicates():
    """Test that Goal 4 predicates are correctly defined."""
    print("=" * 80)
    print("Testing Goal 4 Predicate Generation")
    print("=" * 80)

    goal_preds = get_goal_predicates(goal_id=4)

    print(f"\nTotal predicates: {len(goal_preds)}\n")

    # Categorize predicates
    at_position = [p for p in goal_preds if p[0] == "at-position"]
    ontable = [p for p in goal_preds if p[0] == "ontable"]
    on_preds = [p for p in goal_preds if p[0] == "on"]
    clear = [p for p in goal_preds if p[0] == "clear"]
    handempty = [p for p in goal_preds if p[0] == "handempty"]

    print("--- Yellow Tower (12 blocks) ---")
    yellow_at_pos = [p for p in at_position if p[1].startswith("y")]
    yellow_ontable = [p for p in ontable if p[1].startswith("y")]
    yellow_on = [p for p in on_preds if p[1].startswith("y")]
    yellow_clear = [p for p in clear if p[1].startswith("y")]

    print(f"  at-position predicates: {len(yellow_at_pos)}")
    for p in sorted(yellow_at_pos):
        print(f"    {p}")

    print(f"\n  ontable predicates: {len(yellow_ontable)}")
    for p in sorted(yellow_ontable):
        print(f"    {p}")

    print(f"\n  on predicates: {len(yellow_on)}")
    for p in sorted(yellow_on):
        print(f"    {p}")

    print(f"\n  clear predicates: {len(yellow_clear)}")
    for p in sorted(yellow_clear):
        print(f"    {p}")

    print("\n--- Green Hollow Square (6 blocks) ---")
    green_at_pos = [p for p in at_position if p[1].startswith("g")]
    green_ontable = [p for p in ontable if p[1].startswith("g")]
    green_clear = [p for p in clear if p[1].startswith("g")]

    print(f"  at-position predicates: {len(green_at_pos)}")
    for p in sorted(green_at_pos):
        print(f"    {p}")

    print(f"\n  ontable predicates: {len(green_ontable)}")
    for p in sorted(green_ontable):
        print(f"    {p}")

    print(f"\n  clear predicates: {len(green_clear)}")
    for p in sorted(green_clear):
        print(f"    {p}")

    print(f"\n--- Other ---")
    print(f"  handempty: {handempty}")

    # Validation checks
    print("\n" + "=" * 80)
    print("Validation Checks")
    print("=" * 80)

    checks = []
    checks.append(("Yellow at-position count", len(yellow_at_pos), 12))
    checks.append(("Yellow ontable count", len(yellow_ontable), 6))
    checks.append(("Yellow on count", len(yellow_on), 6))
    checks.append(("Yellow clear count", len(yellow_clear), 6))
    checks.append(("Green at-position count", len(green_at_pos), 6))
    checks.append(("Green ontable count", len(green_ontable), 6))
    checks.append(("Green clear count", len(green_clear), 6))
    checks.append(("Handempty count", len(handempty), 1))

    all_passed = True
    for check_name, actual, expected in checks:
        status = "✓" if actual == expected else "✗"
        if actual != expected:
            all_passed = False
        print(f"  {status} {check_name}: {actual} (expected {expected})")

    print("\n" + "=" * 80)
    if all_passed:
        print("All validation checks PASSED ✓")
    else:
        print("Some validation checks FAILED ✗")
    print("=" * 80)

    return all_passed


def test_problem_generation():
    """Test generation of PDDL problem file for Goal 4."""
    print("\n\n" + "=" * 80)
    print("Testing PDDL Problem File Generation")
    print("=" * 80)

    # Create a simple initial state (all blocks on table, all clear, hand empty)
    from pddl.problem_generator import GOAL4_ALL_BLOCKS

    initial_predicates = set()

    # All blocks on table and clear initially
    for block in GOAL4_ALL_BLOCKS:
        initial_predicates.add(("ontable", block))
        initial_predicates.add(("clear", block))

    # Hand is empty
    initial_predicates.add(("handempty",))

    # All positions are free initially
    positions = [
        "pos_front_left_bottom", "pos_front_right_bottom", "pos_front_center_bottom",
        "pos_front_left_top", "pos_front_right_top",
        "pos_middle_left_bottom", "pos_middle_right_bottom", "pos_middle_center_bottom",
        "pos_middle_left_top", "pos_middle_right_top",
        "pos_back_left_bottom", "pos_back_right_bottom", "pos_back_center_bottom",
        "pos_back_left_top", "pos_back_right_top",
    ]

    for pos in positions:
        initial_predicates.add(("position-free", pos))

    print(f"\nInitial state: {len(initial_predicates)} predicates")
    print(f"  - {len(GOAL4_ALL_BLOCKS)} blocks (all ontable and clear)")
    print(f"  - {len(positions)} positions (all free)")
    print(f"  - 1 handempty predicate")

    # Generate problem file
    try:
        problem_file = make_problem_pddl(
            current_predicates=initial_predicates,
            goal_id=4,
            problem_name="test_goal4"
        )

        print(f"\n✓ Problem file generated: {problem_file}")

        # Read and display the generated file
        problem_path = Path(problem_file)
        if problem_path.exists():
            content = problem_path.read_text()
            print("\n" + "=" * 80)
            print("Generated PDDL Problem File Content:")
            print("=" * 80)
            print(content)
            print("=" * 80)
            return True
        else:
            print(f"\n✗ Problem file not found at {problem_file}")
            return False

    except Exception as e:
        print(f"\n✗ Error generating problem file: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_domain_file():
    """Check that the Goal 4 domain file exists."""
    print("\n\n" + "=" * 80)
    print("Testing Goal 4 Domain File")
    print("=" * 80)

    domain_path = Path("pddl/domain_blocks_goal4.pddl")

    if domain_path.exists():
        print(f"\n✓ Domain file exists: {domain_path}")
        content = domain_path.read_text()
        print(f"  File size: {len(content)} characters")

        # Count predicates and actions
        predicate_count = content.count("(:predicates")
        action_count = content.count("(:action")

        print(f"  Predicate sections: {predicate_count}")
        print(f"  Actions defined: {action_count}")

        print("\n" + "=" * 80)
        print("Domain File Content:")
        print("=" * 80)
        print(content)
        print("=" * 80)

        return True
    else:
        print(f"\n✗ Domain file not found: {domain_path}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("GOAL 4 PDDL VALIDATION TEST SUITE")
    print("=" * 80)

    results = {}

    # Test 1: Predicates
    results["predicates"] = test_goal4_predicates()

    # Test 2: Domain file
    results["domain"] = test_domain_file()

    # Test 3: Problem generation
    results["problem"] = test_problem_generation()

    # Summary
    print("\n\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 80)
    if all_passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("=" * 80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
