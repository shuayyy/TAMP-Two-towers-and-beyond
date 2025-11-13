"""Example Usage: Symbolic Abstraction Module

This file shows practical examples of how to use the symbolic abstraction
module in different scenarios.

Author: Person 2
"""

import numpy as np
import genesis as gs
from scenes import create_scene_6blocks, create_scene_stacked
from symbolic_abstraction import (
    abstract_state,
    visualize_predicates,
    visualize_ascii_blocks,
    log_predicate_changes,
    debug_spatial_relationships
)


def example_1_basic_usage():
    """Example 1: Basic usage - abstracting state from a scene."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Usage")
    print("="*60)

    # Initialize Genesis
    gs.init(backend=gs.cpu, logging_level='Warning', logger_verbose_time=False)

    # Create scene
    scene, robot, blocks_state = create_scene_6blocks()

    # Set control gains (standard for Franka)
    robot.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    robot.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))

    # Let physics settle
    for _ in range(100):
        scene.step()

    # Abstract the state - THIS IS THE MAIN FUNCTION YOU'LL USE
    predicates = abstract_state(scene, robot, blocks_state)

    # Visualize the predicates
    visualize_predicates(predicates, "Example 1: Current State")

    # Access specific predicates
    print("\nQuerying specific information:")

    # Which blocks are on the table?
    blocks_on_table = [p[1] for p in predicates if p[0] == "ontable"]
    print(f"Blocks on table: {sorted(blocks_on_table)}")

    # Which blocks are clear?
    clear_blocks = [p[1] for p in predicates if p[0] == "clear"]
    print(f"Clear blocks: {sorted(clear_blocks)}")

    # Is hand empty?
    hand_empty = ("handempty",) in predicates
    print(f"Hand empty: {hand_empty}")

    # Any stacking relationships?
    on_relations = [(p[1], p[2]) for p in predicates if p[0] == "on"]
    print(f"Stacking relationships: {on_relations}")


def example_2_tracking_changes():
    """Example 2: Track how predicates change over time."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Tracking Changes")
    print("="*60)

    # Initialize
    gs.init(backend=gs.cpu, logging_level='Warning', logger_verbose_time=False)
    scene, robot, blocks_state = create_scene_6blocks()
    robot.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    robot.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))

    # Settle physics
    for _ in range(100):
        scene.step()

    # Get initial state
    print("\nState BEFORE manual change:")
    old_predicates = abstract_state(scene, robot, blocks_state)
    visualize_predicates(old_predicates, "Before")

    # Make a manual change (simulate an action)
    print("\nManually stacking GREEN on RED...")
    red_pos = blocks_state["r"].get_pos()
    blocks_state["g"].set_pos([red_pos[0], red_pos[1], red_pos[2] + 0.04])

    # Settle physics
    for _ in range(100):
        scene.step()

    # Get new state
    print("\nState AFTER manual change:")
    new_predicates = abstract_state(scene, robot, blocks_state)
    visualize_predicates(new_predicates, "After")

    # Show what changed
    log_predicate_changes(old_predicates, new_predicates)


def example_3_goal_checking():
    """Example 3: Check if a goal state is achieved."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Goal Checking")
    print("="*60)

    # Initialize
    gs.init(backend=gs.cpu, logging_level='Warning', logger_verbose_time=False)
    scene, robot, blocks_state = create_scene_6blocks()
    robot.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    robot.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))

    for _ in range(100):
        scene.step()

    # Define Goal 1: Two towers
    # Tower 1: RED on GREEN on BLUE (top to bottom)
    # Tower 2: YELLOW on MAGENTA on CYAN (top to bottom)
    goal_predicates = {
        # Tower 1
        ("ontable", "b"),
        ("on", "g", "b"),
        ("on", "r", "g"),
        ("clear", "r"),

        # Tower 2
        ("ontable", "c"),
        ("on", "m", "c"),
        ("on", "y", "m"),
        ("clear", "y"),

        # Robot
        ("handempty",)
    }

    # Get current state
    current_predicates = abstract_state(scene, robot, blocks_state)

    # Check if goal is achieved
    def goal_achieved(current, goal):
        """Check if all goal predicates are present in current state."""
        return goal.issubset(current)

    achieved = goal_achieved(current_predicates, goal_predicates)
    print(f"\nGoal achieved: {achieved}")

    if not achieved:
        missing = goal_predicates - current_predicates
        print(f"\nMissing predicates ({len(missing)}):")
        for pred in sorted(missing):
            print(f"  - {pred}")

    # Show current state
    visualize_predicates(current_predicates, "Current State")
    visualize_ascii_blocks(current_predicates)


def example_4_integration_loop():
    """Example 4: How to use in TAMP execution loop (Person 4 integration)."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Integration Loop Pattern")
    print("="*60)

    # Initialize
    gs.init(backend=gs.cpu, logging_level='Warning', logger_verbose_time=False)
    scene, robot, blocks_state = create_scene_6blocks()
    robot.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    robot.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))

    # Define goal
    goal_predicates = {
        ("ontable", "b"),
        ("on", "g", "b"),
        ("on", "r", "g"),
        ("clear", "r"),
        ("ontable", "c"),
        ("on", "m", "c"),
        ("on", "y", "m"),
        ("clear", "y"),
        ("handempty",)
    }

    # TAMP execution loop pattern
    max_iterations = 5  # Just a few iterations for demo
    previous_predicates = None

    print("\nSimulating TAMP execution loop...\n")

    for iteration in range(max_iterations):
        print(f"\n{'='*60}")
        print(f"Iteration {iteration}")
        print(f"{'='*60}")

        # STEP 1: Abstract current state (YOUR MODULE!)
        current_predicates = abstract_state(scene, robot, blocks_state)
        visualize_predicates(current_predicates, f"Iteration {iteration}")

        # Log changes if not first iteration
        if previous_predicates is not None:
            log_predicate_changes(previous_predicates, current_predicates)

        # STEP 2: Check goal
        if goal_predicates.issubset(current_predicates):
            print("\n🎉 GOAL ACHIEVED!")
            break

        # STEP 3: Get task plan (Person 1's job)
        print("\n[Would call Person 1's task planner here...]")
        print("  get_task_plan(current_predicates, goal_predicates)")

        # STEP 4: Execute action (Person 3 & 4's job)
        print("\n[Would execute motion primitive here...]")
        print("  execute_action(robot, scene, blocks_state, action)")

        # STEP 5: Wait for physics
        for _ in range(50):
            scene.step()

        # Save for next iteration
        previous_predicates = current_predicates

    print("\n" + "="*60)
    print("Loop complete (demo)")
    print("="*60)


def example_5_debugging():
    """Example 5: Debugging tools when predicates seem wrong."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Debugging Tools")
    print("="*60)

    # Initialize
    gs.init(backend=gs.cpu, logging_level='Warning', logger_verbose_time=False)
    scene, robot, blocks_state = create_scene_6blocks()
    robot.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    robot.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))

    for _ in range(100):
        scene.step()

    print("\n1. Show detailed spatial relationships:")
    debug_spatial_relationships(blocks_state, robot)

    print("\n2. Show predicates:")
    predicates = abstract_state(scene, robot, blocks_state)
    visualize_predicates(predicates)

    print("\n3. Show ASCII visualization:")
    visualize_ascii_blocks(predicates)

    print("\n4. Manual predicate checks:")
    from symbolic_abstraction import get_block_positions, is_on, is_on_table, is_clear

    positions = get_block_positions(blocks_state)

    print(f"\nIs RED on table? {is_on_table(positions['r'])}")
    print(f"Is GREEN on RED? {is_on(positions['g'], positions['r'])}")
    print(f"Is RED clear? {is_clear('r', positions)}")


def main():
    """Run all examples."""
    examples = [
        ("Basic Usage", example_1_basic_usage),
        ("Tracking Changes", example_2_tracking_changes),
        ("Goal Checking", example_3_goal_checking),
        ("Integration Loop", example_4_integration_loop),
        ("Debugging", example_5_debugging),
    ]

    print("\n" + "="*60)
    print("SYMBOLIC ABSTRACTION - EXAMPLE USAGE")
    print("="*60)
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print("\nRunning all examples...\n")

    for name, example_func in examples:
        try:
            example_func()
            print(f"\n✓ {name} complete\n")
        except Exception as e:
            print(f"\n✗ {name} failed: {e}\n")

    print("\n" + "="*60)
    print("ALL EXAMPLES COMPLETE")
    print("="*60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Run specific example
        example_num = int(sys.argv[1])
        examples = {
            1: example_1_basic_usage,
            2: example_2_tracking_changes,
            3: example_3_goal_checking,
            4: example_4_integration_loop,
            5: example_5_debugging,
        }

        if example_num in examples:
            examples[example_num]()
        else:
            print(f"Invalid example number: {example_num}")
            print("Usage: python example_usage.py [1-5]")
    else:
        # Run all examples
        main()
