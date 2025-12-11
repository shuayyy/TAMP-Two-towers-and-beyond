# Goal 3: 8-Block Tower (Tallest Possible)

## Overview
Goal 3 builds the **tallest possible tower** using all 8 blocks available in the scene.

## Tower Configuration

**Tower Structure (top → bottom):**
```
     [P]  ← Purple (top)
      |
     [O]  ← Orange
      |
     [M]  ← Magenta
      |
     [Y]  ← Yellow
      |
     [B]  ← Blue
      |
     [R]  ← Red
      |
     [G]  ← Green
      |
     [C]  ← Cyan (bottom, on table)
```

## Block Details

| Block | Color | Letter | RGB Color |
|-------|-------|--------|-----------|
| C | Cyan | c | (0.0, 1.0, 1.0) |
| G | Green | g | (0.0, 1.0, 0.0) |
| R | Red | r | (1.0, 0.0, 0.0) |
| B | Blue | b | (0.0, 0.0, 1.0) |
| Y | Yellow | y | (1.0, 1.0, 0.0) |
| M | Magenta | m | (1.0, 0.0, 1.0) |
| O | **Orange** | o | (1.0, 0.5, 0.0) |
| P | **Purple** | p | (0.5, 0.0, 0.5) |

**Note:** Orange (O) and Purple (P) are the two new blocks added for Goal 3.

## Goal Predicates (PDDL)

```lisp
(:goal
  (and
    (ontable c)          ; Cyan is on the table
    (on g c)             ; Green is on Cyan
    (on r g)             ; Red is on Green
    (on b r)             ; Blue is on Red
    (on y b)             ; Yellow is on Blue
    (on m y)             ; Magenta is on Yellow
    (on o m)             ; Orange is on Magenta
    (on p o)             ; Purple is on Orange
    (clear p)            ; Purple is clear (top of tower)
    (handempty)          ; Robot gripper is empty
  )
)
```

## Initial Scene

The scene starts with all 8 blocks **scattered on the table** at random positions:
- Original 6 blocks: R, G, B, Y, M, C (in two rows)
- 2 new blocks: O (Orange), P (Purple) (positioned on the sides)

## Running Goal 3

```bash
# Run Goal 3 with 8-block tower
python3 demo.py --goal 3

# Run with CPU backend
python3 demo.py --goal 3 --backend cpu

# Run with custom iteration limit
python3 demo.py --goal 3 --max-iterations 30
```

## Expected Behavior

1. **Initial State:** All 8 blocks scattered on table
2. **Planning:** System generates optimal plan using A* search
3. **Execution:** Robot picks and stacks blocks one by one
4. **Final State:** Single tower of 8 blocks (height = 32cm)

## Tower Height

- Each block: 4cm (0.04m)
- Total tower height: **8 × 4cm = 32cm** (0.32m)
- This is the tallest possible single tower with the available blocks

## Technical Details

- **Scene Function:** `create_scene_8blocks()` in [scenes.py](scenes.py)
- **Goal Definition:** `goal_id == 3` in [pddl/problem_generator.py](pddl/problem_generator.py)
- **Planner:** A* search (optimal planning)
- **Physics Settling:** 100 simulation steps per action

## Differences from Other Goals

| Aspect | Goal 1 | Goal 2 | Goal 3 | Goal 4 |
|--------|--------|--------|--------|--------|
| Blocks | 6 | 6 | **8** | 18 |
| Towers | 2 | 1 | 1 | 2 structures |
| Max height | 3 blocks | 5 blocks | **8 blocks** | 2 blocks |
| New blocks | - | - | **O, P** | y1-y12, g1-g6 |

## Example Plan

Assuming all blocks start on the table, a typical plan would be:

```
1. (pickup c)
2. (putdown c)         ; Position cyan at desired location
3. (pickup g)
4. (stack g c)
5. (pickup r)
6. (stack r g)
7. (pickup b)
8. (stack b r)
9. (pickup y)
10. (stack y b)
11. (pickup m)
12. (stack m y)
13. (pickup o)
14. (stack o m)
15. (pickup p)
16. (stack p o)
```

Total: **16 actions** (may vary based on initial positions)

## Notes

- The tower is **tall and potentially unstable** - physics simulation uses careful settling
- Orange and Purple blocks are positioned to avoid collision with the original 6 blocks
- The planner automatically determines the optimal stacking order
- Scene uses random noise (±5cm) in initial block positions for variability
