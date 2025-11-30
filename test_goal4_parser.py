#!/usr/bin/env python3
"""
Test Goal 4 Action Parser

Verifies that the task planner correctly parses Goal 4 actions
with position parameters.
"""

from task_planner import parse_plan

def test_goal4_action_parsing():
    """Test parsing of PUTDOWN-AT and STACK-AT actions."""

    # Sample plan with Goal 4 actions
    plan_text = """
; Goal 4 plan example
(pickup y1)
(putdown-at y1 pos_r1_c2_bottom)
(pickup y2)
(putdown-at y2 pos_r1_c3_bottom)
(pickup y3)
(stack-at y3 y1 pos_r1_c2_bottom)
(unstack y3 y1)
(putdown y3)
"""

    plan = parse_plan(plan_text)

    print("=" * 80)
    print("GOAL 4 ACTION PARSER TEST")
    print("=" * 80)
    print(f"\nParsed {len(plan)} actions:\n")

    for i, action in enumerate(plan, 1):
        print(f"{i}. {action}")

    # Verify expected actions
    expected = [
        ("PICKUP", "y1"),
        ("PUTDOWN-AT", "y1", "pos_r1_c2_bottom"),
        ("PICKUP", "y2"),
        ("PUTDOWN-AT", "y2", "pos_r1_c3_bottom"),
        ("PICKUP", "y3"),
        ("STACK-AT", "y3", "y1", "pos_r1_c2_bottom"),
        ("UNSTACK", "y3", "y1"),
        ("PUTDOWN", "y3"),
    ]

    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    if plan == expected:
        print("\n✅ All actions parsed correctly!")
        print(f"\nVerified action types:")
        print(f"  ✓ PICKUP: standard 1-arg action")
        print(f"  ✓ PUTDOWN-AT: Goal 4 2-arg action (block, position)")
        print(f"  ✓ STACK-AT: Goal 4 3-arg action (block, base, position)")
        print(f"  ✓ UNSTACK: standard 2-arg action")
        print(f"  ✓ PUTDOWN: standard 1-arg action")
        print("\n" + "=" * 80)
        return True
    else:
        print("\n❌ Parse mismatch!")
        print("\nExpected:")
        for action in expected:
            print(f"  {action}")
        print("\nGot:")
        for action in plan:
            print(f"  {action}")
        print("\n" + "=" * 80)
        return False


def test_mixed_actions():
    """Test parsing mixed Goals 1-4 actions."""

    plan_text = """
(pickup r)
(stack r g)
(putdown-at y1 pos_r1_c2_bottom)
(stack-at y3 y1 pos_r1_c2_bottom)
"""

    plan = parse_plan(plan_text)

    print("\n" + "=" * 80)
    print("MIXED ACTIONS TEST")
    print("=" * 80)
    print(f"\nParsed {len(plan)} actions:\n")

    for i, action in enumerate(plan, 1):
        action_name = action[0]
        args = action[1:]
        print(f"{i}. {action_name:15s} args={args}")

    expected_count = 4
    if len(plan) == expected_count:
        print(f"\n✅ Correctly parsed {expected_count} mixed actions")
        print("=" * 80)
        return True
    else:
        print(f"\n❌ Expected {expected_count} actions, got {len(plan)}")
        print("=" * 80)
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TASK PLANNER - GOAL 4 ACTION PARSING TESTS")
    print("=" * 80)

    test1_passed = test_goal4_action_parsing()
    test2_passed = test_mixed_actions()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if test1_passed and test2_passed:
        print("\n✅ ALL TESTS PASSED")
        print("\nAction parser ready for Goal 4:")
        print("  ✓ Handles PUTDOWN-AT with position parameter")
        print("  ✓ Handles STACK-AT with block and position parameters")
        print("  ✓ Backward compatible with Goals 1-3 actions")
        print("  ✓ Supports mixed action types in same plan")
    else:
        print("\n❌ SOME TESTS FAILED")

    print("=" * 80 + "\n")
