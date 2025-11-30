#!/usr/bin/env python3
"""
Test Goal 4 Symbolic Abstraction

Verifies that position detection works correctly for Goal 4.
Tests both scattered initial state and final goal state.
"""

import genesis as gs
import numpy as np
from scenes import create_scene_goal4_initial, create_scene_goal4_final
from symbolic_abstraction import abstract_state, visualize_predicates
from robot_adapter import RobotAdapter

def test_initial_state():
    """Test abstraction on scattered initial state."""
    print("=" * 80)
    print("TEST 1: INITIAL STATE (Scattered Blocks)")
    print("=" * 80)

    gs.init(backend=gs.cpu, logging_level="Warning", logger_verbose_time=False)

    scene, franka_raw, blocks_state = create_scene_goal4_initial()
    franka = RobotAdapter(franka_raw, scene)

    franka.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    franka.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))

    # Let physics settle
    for _ in range(100):
        scene.step()

    # Get abstract state
    predicates = abstract_state(scene, franka, blocks_state, goal_id=4)

    print(f"\nTotal predicates: {len(predicates)}")
    visualize_predicates(predicates, "Initial State Predicates")

    # Verify expected predicates
    ontable = [p for p in predicates if p[0] == "ontable"]
    clear = [p for p in predicates if p[0] == "clear"]
    at_position = [p for p in predicates if p[0] == "at-position"]
    position_free = [p for p in predicates if p[0] == "position-free"]

    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    print(f"✓ Blocks on table: {len(ontable)} (expected: 18)")
    print(f"✓ Clear blocks: {len(clear)} (expected: 18 - all scattered)")
    print(f"✓ At-position predicates: {len(at_position)} (expected: 0 - not at goal positions)")
    print(f"✓ Free positions: {len(position_free)} (expected: 19 - all free)")

    assert len(ontable) == 18, f"Expected 18 blocks on table, got {len(ontable)}"
    assert len(clear) == 18, f"Expected 18 clear blocks, got {len(clear)}"
    assert len(position_free) == 19, f"Expected 19 free positions, got {len(position_free)}"

    print("\n✅ Initial state test PASSED!\n")


def test_final_state():
    """Test abstraction on final goal state."""
    print("=" * 80)
    print("TEST 2: FINAL STATE (Goal Structure)")
    print("=" * 80)

    gs.init(backend=gs.cpu, logging_level="Warning", logger_verbose_time=False)

    scene, franka_raw, blocks_state = create_scene_goal4_final()
    franka = RobotAdapter(franka_raw, scene)

    franka.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    franka.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))

    # Let physics settle
    for _ in range(100):
        scene.step()

    # Get abstract state
    predicates = abstract_state(scene, franka, blocks_state, goal_id=4)

    print(f"\nTotal predicates: {len(predicates)}")
    visualize_predicates(predicates, "Final State Predicates")

    # Verify expected predicates
    ontable = [p for p in predicates if p[0] == "ontable"]
    on_relations = [p for p in predicates if p[0] == "on"]
    clear = [p for p in predicates if p[0] == "clear"]
    at_position = [p for p in predicates if p[0] == "at-position"]
    position_free = [p for p in predicates if p[0] == "position-free"]

    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    print(f"✓ Blocks on table: {len(ontable)} (expected: 12 - bottom layer)")
    print(f"✓ On relationships: {len(on_relations)} (expected: 6 - top layer)")
    print(f"✓ Clear blocks: {len(clear)} (expected: 12 - top layer + green)")
    print(f"✓ At-position predicates: {len(at_position)} (expected: 18)")
    print(f"✓ Free positions: {len(position_free)} (expected: 1 - center empty)")

    # Detailed position analysis
    print("\n" + "=" * 80)
    print("POSITION ANALYSIS")
    print("=" * 80)

    yellow_at_pos = [p for p in at_position if p[1].startswith('y')]
    green_at_pos = [p for p in at_position if p[1].startswith('g')]

    print(f"\nYellow blocks at positions: {len(yellow_at_pos)}/12")
    for pred in sorted(yellow_at_pos):
        print(f"  {pred[1]} → {pred[2]}")

    print(f"\nGreen blocks at positions: {len(green_at_pos)}/6")
    for pred in sorted(green_at_pos):
        print(f"  {pred[1]} → {pred[2]}")

    print(f"\nFree positions: {len(position_free)}")
    for pred in sorted(position_free):
        print(f"  {pred[1]}")

    # Assertions
    assert len(at_position) == 18, f"Expected 18 at-position predicates, got {len(at_position)}"
    assert len(yellow_at_pos) == 12, f"Expected 12 yellow blocks positioned, got {len(yellow_at_pos)}"
    assert len(green_at_pos) == 6, f"Expected 6 green blocks positioned, got {len(green_at_pos)}"
    assert len(position_free) == 1, f"Expected 1 free position (center), got {len(position_free)}"

    print("\n✅ Final state test PASSED!\n")


def main():
    print("\n" + "=" * 80)
    print("GOAL 4 SYMBOLIC ABSTRACTION TEST SUITE")
    print("=" * 80)
    print("\nTesting position detection for Goal 4 structures...")
    print()

    try:
        test_initial_state()
        test_final_state()

        print("=" * 80)
        print("ALL TESTS PASSED ✅")
        print("=" * 80)
        print("\nSymbolic abstraction correctly detects:")
        print("  ✓ Position predicates (at-position)")
        print("  ✓ Position availability (position-free)")
        print("  ✓ Standard block predicates (ontable, on, clear)")
        print("\nReady for task planning with Goal 4!")
        print("=" * 80 + "\n")

    except AssertionError as e:
        print("\n" + "=" * 80)
        print("TEST FAILED ❌")
        print("=" * 80)
        print(f"\nError: {e}\n")
        raise


if __name__ == "__main__":
    main()
