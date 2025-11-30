# How to Visualize Goal 4 Structure

## Quick Start

To see the final Goal 4 structure without running task planning:

```bash
python3 visualize_goal4.py
```

This will:
1. Create a Genesis scene with 18 blocks
2. Position them in their final Goal 4 configuration
3. Let physics settle (200 steps)
4. Display block positions
5. Keep the viewer open for inspection

## What You'll See

### Yellow Tower (12 blocks)
- 2×3×2 formation (width × depth × height)
- Front, middle, and back slices
- Middle slice has hollow center
- Blocks named: y1-y12

### Green Hollow Square (6 blocks)
- 3×3 grid pattern with center empty
- All blocks on ground level
- Forms a square ring
- Blocks named: g1-g6

## Scene Layout

The structures are spatially separated:
- **Yellow Tower**: Centered around (0.5, 0.0)
- **Green Square**: Offset to (0.7, 0.25)

This prevents interference during construction.

## Controls

- **Left mouse**: Rotate camera
- **Right mouse**: Pan view
- **Scroll wheel**: Zoom in/out
- **Q key**: Quit (or Ctrl+C in terminal)

## Output

The script will print:
- Block count (18 total)
- Structure layout description
- Final (x, y, z) positions for all blocks
- Progress messages as physics settles

## Verify Structure

After running, check:

### Yellow Tower Checklist
- [ ] 12 yellow blocks visible
- [ ] 3 slices (front, middle, back) in depth
- [ ] Each slice has 2 columns (left, right)
- [ ] Middle slice center is empty (hollow)
- [ ] 2 layers in height (bottom, top)
- [ ] Bottom blocks on table (z ≈ 0.02)
- [ ] Top blocks stacked (z ≈ 0.06)

### Green Square Checklist
- [ ] 6 green blocks visible
- [ ] Forms a square/ring pattern
- [ ] Center position is empty (hole visible)
- [ ] All blocks on ground level
- [ ] No stacking (single layer)

## Troubleshooting

**Blocks fall over or collapse:**
- The spacing might be too tight
- Try adjusting `SPACING` in `scenes.py` (currently 0.05m)
- Increase to 0.06m or 0.07m if unstable

**Blocks don't look right:**
- Check the console output for final positions
- Compare with expected positions in GOAL4_README.md
- Verify block naming (y1-y12, g1-g6)

**Genesis window doesn't open:**
- Check Genesis installation
- Try: `python3 -c "import genesis as gs; gs.init()"`

## Compare with Target Images

After visualization, compare with reference images:
- Yellow tower: [122.png](122.png)
- Green square: [adjacent/167.png](adjacent/167.png)

The structures should match the reference images in configuration, but may differ in:
- Absolute positioning (your scene is in different location)
- Colors (your yellow/green are pure RGB)
- Camera angle (rotate to match reference view)

## Next Steps

Once the visualization looks correct:

1. **Verify PDDL**: Run `python3 test_goal4_pddl.py`
2. **Test Planning**: Generate a plan for Goal 4 using task planner
3. **Implement Execution**: Add motion primitives to build this structure from scratch

## Code References

- Scene creation: [scenes.py](../scenes.py) - `create_scene_goal4_final()`
- Visualization script: [visualize_goal4.py](../visualize_goal4.py)
- PDDL definition: [../pddl/domain_blocks_goal4.pddl](../pddl/domain_blocks_goal4.pddl)
- Goal predicates: [../pddl/problem_generator.py](../pddl/problem_generator.py) - `get_goal_predicates(4)`
