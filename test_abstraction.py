"""Test script for Symbolic Abstraction Module (Person 2)

This script tests the predicate detection functions with both starting scenes:
  - Scene 1: All 6 blocks on floor
  - Scene 2: All 6 blocks stacked in single tower

Usage:
    python test_abstraction.py          # Test scene 1 (blocks on floor)
    python test_abstraction.py stacked  # Test scene 2 (stacked tower)
    python test_abstraction.py debug    # Debug mode with spatial info

Author: Person 2
"""

import sys
import numpy as np
import genesis as gs
from scenes import create_scene_6blocks, create_scene_stacked
from symbolic_abstraction import (
    abstract_state,
    visualize_predicates,
    visualize_ascii_blocks,
    debug_spatial_relationships,
    get_block_positions,
    get_gripper_state
)


def test_scene_1():
    """Test abstraction on Scene 1 (blocks on floor)."""
    print("\n" + "="*60)
    print("TESTING SCENE 1: All blocks on floor")
    print("="*60)

    # Initialize Genesis
    gs.init(backend=gs.cpu, logging_level='Warning', logger_verbose_time=False)

    # Create scene
    scene, franka, blocks_state = create_scene_6blocks()

    # Set control gains
    franka.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    franka.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))
    franka.set_dofs_force_range(
        np.array([-87, -87, -87, -87, -12, -12, -12, -100, -100]),
        np.array([87, 87, 87, 87, 12, 12, 12, 100, 100])
    )

    # Step scene to let physics settle
    print("\nLetting physics settle...")
    for _ in range(100):
        scene.step()

    # Abstract the state
    print("\nAbstracting state...")
    predicates = abstract_state(scene, franka, blocks_state)

    # Visualize
    visualize_predicates(predicates, "Scene 1: Initial State")
    visualize_ascii_blocks(predicates)

    # Validate expected predicates for Scene 1
    print("\nValidation for Scene 1:")
    expected_ontable = {"r", "g", "b", "y", "m", "c"}
    expected_clear = {"r", "g", "b", "y", "m", "c"}

    actual_ontable = {p[1] for p in predicates if p[0] == "ontable"}
    actual_clear = {p[1] for p in predicates if p[0] == "clear"}
    actual_on = [p for p in predicates if p[0] == "on"]
    has_handempty = ("handempty",) in predicates

    print(f"✓ Expected all 6 blocks on table: {expected_ontable == actual_ontable}")
    print(f"  Expected: {sorted(expected_ontable)}")
    print(f"  Actual: {sorted(actual_ontable)}")

    print(f"✓ Expected all 6 blocks clear: {expected_clear == actual_clear}")
    print(f"  Expected: {sorted(expected_clear)}")
    print(f"  Actual: {sorted(actual_clear)}")

    print(f"✓ Expected no 'on' relationships: {len(actual_on) == 0}")
    print(f"  Actual: {actual_on}")

    print(f"✓ Expected hand empty: {has_handempty}")

    return scene, franka, blocks_state, predicates


def test_scene_2():
    """Test abstraction on Scene 2 (stacked tower)."""
    print("\n" + "="*60)
    print("TESTING SCENE 2: All blocks stacked")
    print("="*60)

    # Initialize Genesis
    gs.init(backend=gs.cpu, logging_level='Warning', logger_verbose_time=False)

    # Create scene
    scene, franka, blocks_state = create_scene_stacked()

    # Set control gains
    franka.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    franka.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))
    franka.set_dofs_force_range(
        np.array([-87, -87, -87, -87, -12, -12, -12, -100, -100]),
        np.array([87, 87, 87, 87, 12, 12, 12, 100, 100])
    )

    # Step scene to let physics settle
    print("\nLetting physics settle...")
    for _ in range(100):
        scene.step()

    # Abstract the state
    print("\nAbstracting state...")
    predicates = abstract_state(scene, franka, blocks_state)

    # Visualize
    visualize_predicates(predicates, "Scene 2: Stacked Tower")
    visualize_ascii_blocks(predicates)

    # Validate expected predicates for Scene 2
    print("\nValidation for Scene 2:")
    # Expected: r on table, g on r, b on g, y on b, m on y, c on m
    # Only r should be on table, only c should be clear

    actual_ontable = {p[1] for p in predicates if p[0] == "ontable"}
    actual_clear = {p[1] for p in predicates if p[0] == "clear"}
    actual_on = {(p[1], p[2]) for p in predicates if p[0] == "on"}
    has_handempty = ("handempty",) in predicates

    print(f"✓ Expected only RED on table: {actual_ontable == {'r'}}")
    print(f"  Actual: {sorted(actual_ontable)}")

    print(f"✓ Expected only CYAN clear: {actual_clear == {'c'}}")
    print(f"  Actual: {sorted(actual_clear)}")

    print(f"✓ Expected 5 'on' relationships:")
    print(f"  Actual count: {len(actual_on)}")
    for top, bottom in sorted(actual_on):
        print(f"    - {top.upper()} on {bottom.upper()}")

    print(f"✓ Expected hand empty: {has_handempty}")

    # Check specific stacking order from scenes.py
    # Scene 2 creates: r(z=0.02), g(0.06), b(0.10), y(0.14), m(0.18), c(0.22)
    expected_on = {("g", "r"), ("b", "g"), ("y", "b"), ("m", "y"), ("c", "m")}
    print(f"\n✓ Expected stacking order matches: {expected_on == actual_on}")
    if expected_on != actual_on:
        print(f"  Expected: {sorted(expected_on)}")
        print(f"  Actual: {sorted(actual_on)}")

    return scene, franka, blocks_state, predicates


def test_debug_mode():
    """Run in debug mode to show detailed spatial information."""
    print("\n" + "="*60)
    print("DEBUG MODE: Detailed spatial information")
    print("="*60)

    # Initialize Genesis
    gs.init(backend=gs.cpu, logging_level='Warning', logger_verbose_time=False)

    # Create scene (use scene 1 for debug)
    scene, franka, blocks_state = create_scene_6blocks()

    # Set control gains
    franka.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    franka.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))
    franka.set_dofs_force_range(
        np.array([-87, -87, -87, -87, -12, -12, -12, -100, -100]),
        np.array([87, 87, 87, 87, 12, 12, 12, 100, 100])
    )

    # Let physics settle
    for _ in range(100):
        scene.step()

    # Show debug info
    debug_spatial_relationships(blocks_state, franka)

    # Show predicates
    predicates = abstract_state(scene, franka, blocks_state)
    visualize_predicates(predicates, "Debug Mode: Current State")

    return scene, franka, blocks_state, predicates


def test_manual_positions():
    """Test predicate detection with manually verified block positions."""
    print("\n" + "="*60)
    print("TESTING: Manual position verification")
    print("="*60)

    # Initialize Genesis
    gs.init(backend=gs.cpu, logging_level='Warning', logger_verbose_time=False)

    # Create scene
    scene, franka, blocks_state = create_scene_6blocks()

    # Set control gains
    franka.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    franka.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))

    # Let physics settle
    for _ in range(100):
        scene.step()

    # Get initial state
    print("\nInitial state (all blocks on floor):")
    predicates1 = abstract_state(scene, franka, blocks_state)
    visualize_predicates(predicates1, "State 1: Initial")

    # Manually move a block to create a simple tower
    print("\n" + "="*60)
    print("Manually creating test configuration...")
    print("Moving GREEN block on top of RED block")
    print("="*60)

    # Get red block position
    red_pos = blocks_state["r"].get_pos()
    # Place green block directly on top of red
    green_new_pos = [red_pos[0], red_pos[1], red_pos[2] + 0.04]  # One block height up
    blocks_state["g"].set_pos(green_new_pos)

    # Let physics settle
    for _ in range(100):
        scene.step()

    # Abstract new state
    predicates2 = abstract_state(scene, franka, blocks_state)
    visualize_predicates(predicates2, "State 2: After manual move")
    visualize_ascii_blocks(predicates2)

    # Verify expected predicates
    print("\nValidation:")
    has_g_on_r = ("on", "g", "r") in predicates2
    has_r_ontable = ("ontable", "r") in predicates2
    r_not_clear = ("clear", "r") not in predicates2
    g_is_clear = ("clear", "g") in predicates2

    print(f"✓ GREEN on RED: {has_g_on_r}")
    print(f"✓ RED on table: {has_r_ontable}")
    print(f"✓ RED not clear: {r_not_clear}")
    print(f"✓ GREEN is clear: {g_is_clear}")

    all_correct = has_g_on_r and has_r_ontable and r_not_clear and g_is_clear
    print(f"\n{'✓ ALL TESTS PASSED!' if all_correct else '✗ SOME TESTS FAILED'}")

    return scene, franka, blocks_state, predicates2


def interactive_mode():
    """Interactive mode - keep scene open for manual inspection."""
    print("\n" + "="*60)
    print("INTERACTIVE MODE")
    print("="*60)
    print("\nThe scene will stay open. You can:")
    print("  - View the visualization")
    print("  - Press Ctrl+C to exit")
    print("="*60)

    # Initialize Genesis with viewer
    gs.init(backend=gs.cpu, logging_level='Warning', logger_verbose_time=False)

    # Create scene
    scene, franka, blocks_state = create_scene_6blocks()

    # Set control gains
    franka.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    franka.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))

    # Main loop
    print("\nRunning scene... (Press Ctrl+C to exit)")
    try:
        for i in range(10000):
            scene.step()

            # Print predicates every 200 steps
            if i % 200 == 0:
                predicates = abstract_state(scene, franka, blocks_state)
                visualize_predicates(predicates, f"Step {i}")
    except KeyboardInterrupt:
        print("\nExiting interactive mode...")


def main():
    """Main test entry point."""
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

        if mode == "stacked":
            test_scene_2()
        elif mode == "debug":
            test_debug_mode()
        elif mode == "manual":
            test_manual_positions()
        elif mode == "interactive":
            interactive_mode()
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python test_abstraction.py [stacked|debug|manual|interactive]")
            sys.exit(1)
    else:
        # Default: test scene 1
        test_scene_1()

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
