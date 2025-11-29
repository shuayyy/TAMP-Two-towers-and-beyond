#!/usr/bin/env python3
"""
Test Goal 4 Initial Scene (Scattered Blocks)

This script creates a Genesis scene with 18 blocks scattered on the table
to verify the initial state before task planning.

Controls:
- Press 'Q' to quit
- Use mouse to rotate camera
"""

import genesis as gs
import numpy as np
from scenes import create_scene_goal4_initial

def main():
    print("=" * 80)
    print("GOAL 4 INITIAL SCENE - SCATTERED BLOCKS")
    print("=" * 80)
    print("\nInitializing Genesis...")

    # Initialize Genesis
    gs.init(backend=gs.cpu, logging_level="Warning", logger_verbose_time=False)

    # Create scene with scattered blocks
    print("Creating Goal 4 initial scene with 18 scattered blocks...")
    scene, robot, blocks_state = create_scene_goal4_initial()

    print(f"\nScene created successfully!")
    print(f"  Total blocks: {len(blocks_state)}")

    # Count yellow and green blocks
    yellow_blocks = [name for name in blocks_state.keys() if name.startswith('y')]
    green_blocks = [name for name in blocks_state.keys() if name.startswith('g')]

    print(f"  Yellow blocks: {len(yellow_blocks)} (y1-y12)")
    print(f"  Green blocks: {len(green_blocks)} (g1-g6)")

    # Set robot control gains
    robot.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    robot.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))

    print("\n" + "=" * 80)
    print("INITIAL STATE - All blocks on table (scattered)")
    print("=" * 80)
    print("\nThis is the starting configuration for TAMP task planning.")
    print("Blocks are randomly positioned with noise for realistic scenarios.")

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
            print("[Step 100] Blocks stabilizing...")
        elif i == 150:
            print("[Step 150] Almost ready...")
        elif i == 199:
            print("[Step 200] ✓ All blocks settled!")
            print("\n" + "=" * 80)
            print("INITIAL STATE READY")
            print("=" * 80)

    # Get final positions for verification
    print("\n--- Initial Block Positions ---")
    print("\nYellow blocks (should be scattered):")
    for name in sorted(yellow_blocks):
        pos = blocks_state[name].get_pos()
        if hasattr(pos, 'cpu'):
            pos = pos.cpu().numpy()
        else:
            pos = np.array(pos)
        print(f"  {name}: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")

    print("\nGreen blocks (should be scattered):")
    for name in sorted(green_blocks):
        pos = blocks_state[name].get_pos()
        if hasattr(pos, 'cpu'):
            pos = pos.cpu().numpy()
        else:
            pos = np.array(pos)
        print(f"  {name}: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")

    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    print("\nCheck that:")
    print("  ✓ All 18 blocks are visible (12 yellow + 6 green)")
    print("  ✓ All blocks are on the table surface (z ≈ 0.02)")
    print("  ✓ Blocks are scattered (not in final structure)")
    print("  ✓ No blocks are stacked (all should be separate)")

    print("\n" + "=" * 80)
    print("Press Ctrl+C or close window to exit")
    print("=" * 80)

    # Keep simulation running for visualization
    try:
        while True:
            scene.step()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        print("Initial scene verification complete!")
        print("=" * 80)

if __name__ == "__main__":
    main()
