# Goal 4: Special Structure - Two Combined Structures

## Overview
Goal 4 requires building **two separate structures** using 18 blocks total:
1. **Yellow Tower** - 12 yellow blocks (image: 122.png)
2. **Green Hollow Square** - 6 green blocks (image: adjacent/167.png)

## Coordinate System (Right-Handed Frame)
- **x-axis**: depth (front → middle → back)
- **y-axis**: width (left → center → right)
- **z-axis**: height (bottom → top)

---

## Structure 1: Yellow Tower (12 blocks)

### Dimensions
- Footprint: 2 (y) × 3 (x) × 2 (z)
- Total blocks: 12 yellow cubes (y1 through y12)

### Layer-by-Layer Description

#### **Front Slice (x = front)** - 4 blocks
Full 2×2 block in the y-z plane:
- `y1`: (front, left, bottom) - ontable
- `y2`: (front, right, bottom) - ontable
- `y3`: (front, left, top) - on y1
- `y4`: (front, right, top) - on y2

#### **Middle Slice (x = middle)** - 4 blocks
Only side columns present (center is empty - creates the hollow effect):
- `y5`: (middle, left, bottom) - ontable
- `y6`: (middle, right, bottom) - ontable
- `y7`: (middle, left, top) - on y5
- `y8`: (middle, right, top) - on y6

#### **Back Slice (x = back)** - 4 blocks
Full 2×2 block in the y-z plane:
- `y9`: (back, left, bottom) - ontable
- `y10`: (back, right, bottom) - ontable
- `y11`: (back, left, top) - on y9
- `y12`: (back, right, top) - on y10

### Visual Summary
**Top view (x-y plane looking down):**
```
      LEFT  RIGHT
FRONT  ██    ██     (y1-y4)
MIDDLE ██    ██     (y5-y8) - center empty!
BACK   ██    ██     (y9-y12)
```

**Front view (y-z plane from front):**
```
TOP    ██  ██       (any x slice shows 2×2)
BOTTOM ██  ██
```

---

## Structure 2: Green Hollow Square (6 blocks)

### Dimensions
- Footprint: 3 (x) × 3 (y) × 1 (z)
- Total blocks: 6 green cubes (g1 through g6)
- All blocks at z = bottom (single layer)

### Block Positions
Imagine a 3×3 grid with the **center cell empty**:

```
         LEFT   CENTER  RIGHT
FRONT     ·      g1      g2
MIDDLE    g3     ·       g4
BACK      g5     g6      ·
```

**Occupied positions** (all at z=bottom, all ontable):
- `g1`: (front, center, bottom)
- `g2`: (front, right, bottom)
- `g3`: (middle, left, bottom)
- `g4`: (middle, right, bottom)
- `g5`: (back, left, bottom)
- `g6`: (back, center, bottom)

**Empty positions:**
- (front, left, bottom) - no block
- (middle, center, bottom) - **CENTER HOLE**
- (back, right, bottom) - no block

### Visual Summary
Forms a square "ring" missing two opposite corner cubes, with a hollow center.

---

## PDDL Representation

### Block Names
- Yellow blocks: `y1`, `y2`, `y3`, ..., `y12`
- Green blocks: `g1`, `g2`, `g3`, `g4`, `g5`, `g6`

### Position Names
Format: `pos_<x>_<y>_<z>`

**Yellow tower positions:**
- `pos_front_left_bottom`, `pos_front_right_bottom`
- `pos_front_left_top`, `pos_front_right_top`
- `pos_middle_left_bottom`, `pos_middle_right_bottom`
- `pos_middle_left_top`, `pos_middle_right_top`
- `pos_back_left_bottom`, `pos_back_right_bottom`
- `pos_back_left_top`, `pos_back_right_top`

**Green square positions (additional):**
- `pos_front_center_bottom`
- `pos_middle_center_bottom` (empty in goal)
- `pos_back_center_bottom`

### Key Predicates
- `(at-position ?block ?position)` - Block is at specific 3D grid position
- `(ontable ?block)` - Block is on the table surface
- `(on ?top ?bottom)` - Block stacking (vertical only)
- `(clear ?block)` - Nothing on top of block
- `(position-free ?position)` - Position is unoccupied

### Domain File
Goal 4 uses the extended domain: `pddl/domain_blocks_goal4.pddl`

---

## Implementation Notes

### Scene Setup
You will need to create a scene with 18 blocks total:
- 12 yellow blocks (same color, different identifiers)
- 6 green blocks (same color, different identifiers)

### Position Mapping
When executing in Genesis, you'll need to map the symbolic positions to actual (x, y, z) coordinates in the simulation. Suggested spacing:
- Block size: 0.04m (4cm cubes)
- Grid spacing: 0.05m between block centers
- Separate the two structures spatially to avoid interference during construction

### Execution Strategy
1. Build yellow tower first (more complex, requires stacking)
2. Then build green hollow square (simpler, single layer)
3. Or build in parallel if planner supports concurrent actions

---

## Goal Validation

### Yellow Tower Checks
✓ 12 yellow blocks present
✓ 6 blocks on table (bottom layer)
✓ 6 blocks stacked (top layer)
✓ Correct (x,y) positions for each block
✓ Middle slice has empty center (no blocks at middle-center positions)
✓ All top blocks are clear

### Green Hollow Square Checks
✓ 6 green blocks present
✓ All blocks on table (z=bottom)
✓ All blocks are clear
✓ Correct (x,y) positions forming ring pattern
✓ Center position (middle, center) is empty

---

## File References
- PDDL Domain: [pddl/domain_blocks_goal4.pddl](../pddl/domain_blocks_goal4.pddl)
- Problem Generator: [pddl/problem_generator.py](../pddl/problem_generator.py) (goal_id=4)
- Yellow Structure Image: [122.png](122.png)
- Green Structure Image: [adjacent/167.png](adjacent/167.png)
