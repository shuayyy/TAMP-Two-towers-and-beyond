#!/usr/bin/env python3
"""
Visualize Goal 4 Final Structure

This script creates a Genesis scene with all 18 blocks positioned
in their final Goal 4 configuration for visual validation.

NO TASK PLANNING - just shows the target structure.

Controls:
- Press 'Q' to quit
- Use mouse to rotate camera
"""

import genesis as gs
import numpy as np
from scenes import create_scene_goal4_final

def main():
    print("=" * 80)
    print("GOAL 4 FINAL STRUCTURE VISUALIZATION")
    print("=" * 80)
    print("\nInitializing Genesis...")

    # Initialize Genesis
    gs.init(backend=gs.cpu, logging_level="Warning", logger_verbose_time=False)

    # Create scene with Goal 4 final positions
    print("Creating Goal 4 scene with 18 blocks...")
    scene, robot, blocks_state = create_scene_goal4_final()

    print(f"\nScene created successfully!")
    print(f"  Total blocks: {len(blocks_state)}")

    # Count yellow and green blocks
    yellow_blocks = [name for name in blocks_state.keys() if name.startswith('y')]
    green_blocks = [name for name in blocks_state.keys() if name.startswith('g')]

    print(f"  Yellow blocks (tower): {len(yellow_blocks)}")
    print(f"  Green blocks (square): {len(green_blocks)}")

    # Set robot control gains
    robot.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    robot.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))

    print("\n" + "=" * 80)
    print("STRUCTURE DETAILS")
    print("=" * 80)

    print("\nYellow Tower (12 blocks):")
    print("  Front slice:  y1, y2 (bottom)  |  y3, y4 (top)")
    print("  Middle slice: y5, y6 (bottom)  |  y7, y8 (top)  [center hollow]")
    print("  Back slice:   y9, y10 (bottom) |  y11, y12 (top)")

    print("\nGreen Hollow Square (6 blocks):")
    print("  Layout (3×3 grid with center empty):")
    print("    ·  g1  g2")
    print("    g3  ·  g4")
    print("    g5 g6  ·")

    print("\n" + "=" * 80)
    print("SIMULATION RUNNING")
    print("=" * 80)
    print("Camera controls:")
    print("  - Left mouse: Rotate view")
    print("  - Right mouse: Pan")
    print("  - Scroll: Zoom")
    print("  - Press 'Q': Quit")
    print("\nLet physics settle for a moment...")
    print("=" * 80)

    # Run simulation to let blocks settle
    for i in range(200):
        scene.step()

        if i == 50:
            print("\n[Step 50] Blocks settling...")
        elif i == 100:
            print("[Step 100] Structure stabilizing...")
        elif i == 150:
            print("[Step 150] Almost ready...")
        elif i == 199:
            print("[Step 200] ✓ Structure stable!")
            print("\n" + "=" * 80)
            print("STRUCTURE READY - Rotate camera to inspect")
            print("=" * 80)

    # Get final positions for verification
    print("\n--- Final Block Positions ---")
    print("\nYellow blocks:")
    for name in sorted(yellow_blocks):
        pos = blocks_state[name].get_pos()
        if hasattr(pos, 'cpu'):
            pos = pos.cpu().numpy()
        else:
            pos = np.array(pos)
        print(f"  {name}: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")

    print("\nGreen blocks:")
    for name in sorted(green_blocks):
        pos = blocks_state[name].get_pos()
        if hasattr(pos, 'cpu'):
            pos = pos.cpu().numpy()
        else:
            pos = np.array(pos)
        print(f"  {name}: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")

    print("\n" + "=" * 80)
    print("Press Ctrl+C or close window to exit")
    print("=" * 80)

    # Keep simulation running for visualization
    try:
        while True:
            scene.step()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        print("Visualization complete!")
        print("=" * 80)

if __name__ == "__main__":
    main()
