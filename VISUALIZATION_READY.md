# Goal 4 Visualization Ready! 🎉

## What's New

I've created a complete visualization system for Goal 4 that lets you see the final structure **without running task planning**.

## Files Added

### 1. Scene Creator
**File**: [scenes.py](scenes.py) - Added `create_scene_goal4_final()`

Creates a Genesis scene with:
- 12 yellow blocks in tower formation (y1-y12)
- 6 green blocks in hollow square (g1-g6)
- Blocks positioned at final Goal 4 configuration
- Robot placed out of the way

### 2. Visualization Script
**File**: [visualize_goal4.py](visualize_goal4.py)

Features:
- No task planning required
- Shows structure in final position
- Prints block positions
- Interactive camera controls
- Physics simulation to verify stability

### 3. Usage Guide
**File**: [goal4/HOW_TO_VISUALIZE.md](goal4/HOW_TO_VISUALIZE.md)

Complete instructions for visualization and verification.

## How to Use

### Quick Test
```bash
python3 visualize_goal4.py
```

This will:
1. Launch Genesis viewer
2. Show 18 blocks in Goal 4 configuration
3. Let physics settle (200 steps)
4. Print final positions
5. Wait for you to inspect

### What to Check

**Yellow Tower** should show:
- 12 yellow cubes
- 3 depth slices (front, middle, back)
- 2 width columns (left, right)
- 2 height layers (bottom, top)
- **Hollow middle** - no blocks at center of middle slice

**Green Square** should show:
- 6 green cubes
- Ring pattern on ground
- Empty center (hollow square)
- No stacking (single layer)

## Structure Layout

```
Yellow Tower (side view):
  TOP:    ██  ██    ██  ██    ██  ██
  BOTTOM: ██  ██    ██  ██    ██  ██
          FRONT     MIDDLE    BACK
                    (hollow)

Green Square (top view):
          LEFT  CENTER  RIGHT
  FRONT    ·     ██      ██
  MIDDLE   ██     ·      ██
  BACK     ██    ██       ·
```

## Position Mapping

The scene uses these coordinates:

**Yellow Tower** (centered at x=0.5, y=0.0):
- Block spacing: 5cm between centers
- Bottom layer: z = 0.02m (on table)
- Top layer: z = 0.06m (stacked)

**Green Square** (offset at x=0.7, y=0.25):
- Block spacing: 5cm between centers
- All blocks: z = 0.02m (on table)
- Spatially separated from yellow tower

## Expected Output

When you run `visualize_goal4.py`, you should see:

```
================================================================================
GOAL 4 FINAL STRUCTURE VISUALIZATION
================================================================================

Initializing Genesis...
Creating Goal 4 scene with 18 blocks...

Scene created successfully!
  Total blocks: 18
  Yellow blocks (tower): 12
  Green blocks (square): 6

================================================================================
STRUCTURE DETAILS
================================================================================

Yellow Tower (12 blocks):
  Front slice:  y1, y2 (bottom)  |  y3, y4 (top)
  Middle slice: y5, y6 (bottom)  |  y7, y8 (top)  [center hollow]
  Back slice:   y9, y10 (bottom) |  y11, y12 (top)

Green Hollow Square (6 blocks):
  Layout (3×3 grid with center empty):
    ·  g1  g2
    g3  ·  g4
    g5 g6  ·

... [settling steps] ...

--- Final Block Positions ---
[x, y, z coordinates for all blocks]
```

## Verification Steps

1. **Run visualization**:
   ```bash
   python3 visualize_goal4.py
   ```

2. **Check console output**:
   - Verify 18 blocks created
   - Check final positions are stable
   - No errors or warnings

3. **Inspect viewer**:
   - Rotate camera to see all angles
   - Verify yellow tower structure
   - Verify green square pattern
   - Check hollow center in both structures

4. **Compare with reference**:
   - Yellow tower matches [goal4/122.png](goal4/122.png)
   - Green square matches [goal4/adjacent/167.png](goal4/adjacent/167.png)

5. **Test stability**:
   - Let simulation run for 500+ steps
   - Blocks should remain stable
   - No tipping or collapsing

## Troubleshooting

### Blocks Fall Over
**Problem**: Structure collapses during physics simulation

**Solutions**:
- Increase `SPACING` in `scenes.py` (line ~184)
- Change from 0.05 to 0.06 or 0.07
- Blocks may be too close together

### Wrong Number of Blocks
**Problem**: Not seeing 18 blocks (12 yellow + 6 green)

**Solutions**:
- Check Genesis installation
- Verify no errors in console
- Try restarting Genesis viewer

### Can't See Structure
**Problem**: Viewer shows empty scene or blocks not visible

**Solutions**:
- Check camera position
- Rotate view with left mouse
- Zoom out with scroll wheel
- Verify blocks are not all in same location

## Next Steps After Visualization

Once the structure looks correct:

### 1. Validate PDDL
```bash
python3 test_goal4_pddl.py
```
Should show all tests passing.

### 2. Generate Example Problem
```python
from pddl.problem_generator import make_problem_pddl

# Create initial state (all blocks on table)
initial = set()
for block in ['y1', 'y2', ..., 'g6']:
    initial.add(('ontable', block))
    initial.add(('clear', block))
initial.add(('handempty',))

# Generate problem file
problem_file = make_problem_pddl(initial, goal_id=4, problem_name="goal4_test")
print(f"Problem file: {problem_file}")
```

### 3. Implement Execution (TODO)
You'll still need to:
- Create scene with scattered blocks (not final positions)
- Extend symbolic abstraction to detect positions
- Add motion primitives for positional placement
- Update demo.py to handle Goal 4 actions

## Summary

You now have:
- ✅ PDDL domain and predicates for Goal 4
- ✅ Scene creation with 18 blocks
- ✅ Visualization of final structure
- ✅ Position mapping defined
- ✅ Testing and validation tools

**Ready to visualize?**
```bash
python3 visualize_goal4.py
```

🎯 **Goal**: Verify the structure matches your target images before implementing the full TAMP pipeline!
