# Unified TAMP Demo

The demo files have been merged into a single unified interface that supports all goals (1-4).

## Quick Start

### Goals 1-3: Simple Block Stacking

```bash
# Goal 1: Single tower
python3 demo.py --goal 1

# Goal 2: Multiple towers
python3 demo.py --goal 2

# Goal 3: Complex stacking
python3 demo.py --goal 3

# Custom max iterations
python3 demo.py --goal 1 --max-iterations 30
```

### Goal 4: Two-Structure Building

```bash
# Goal 4: Yellow cross + Green square
python3 demo.py --goal 4

# Use CPU backend (if GPU unavailable)
python3 demo.py --goal 4 --backend cpu
```

## Backwards Compatibility

For backwards compatibility, `demo_goal4.py` still exists but now wraps the unified demo:

```bash
# These are equivalent:
python3 demo_goal4.py
python3 demo.py --goal 4
```

## Architecture

### File Structure

```
demo.py                  # Unified demo (all goals)
demo_goal4.py            # Wrapper pointing to demo.py --goal 4
demo_goal4_old.py        # Original Goal 4 implementation (backup)
```

### Key Features

1. **Unified Action Execution**: Single `execute_action()` function handles all action types:
   - Simple: PICKUP, PUTDOWN, STACK, UNSTACK
   - Goal 4: PICKUP-AT, PUTDOWN-AT, STACK-AT, UNSTACK-AT

2. **Adaptive Block Printing**: `print_block_positions()` automatically detects goal type:
   - Goals 1-3: 6 blocks (b, c, g, m, r, y)
   - Goal 4: 18 blocks (y1-y12, g1-g6)

3. **Scene Routing**: Automatically selects correct scene:
   - Goals 1-3: `create_scene_6blocks()`
   - Goal 4: `create_scene_goal4_initial()`

4. **Execution Strategies**:
   - Goals 1-3: Single-action execution (replan after each action)
   - Goal 4: Batch execution with phase decomposition

### Execution Flow

#### Goals 1-3 (Simple)
```
Loop (max iterations):
  1. Abstract state → predicates
  2. Plan symbolic actions
  3. Execute FIRST action only
  4. Update physics (80 steps)
  5. Repeat until goal reached
```

#### Goal 4 (Complex)
```
Phase 1: Yellow Cross Tower (Goal 41)
  Loop:
    1. Abstract state → predicates
    2. Plan symbolic actions
    3. Execute BATCH of 2 actions
    4. Update physics (20 steps per action)
    5. Repeat until phase complete

Phase 2: Green Hollow Square (Goal 42)
  Loop:
    1. Abstract state → predicates
    2. Plan symbolic actions
    3. Execute BATCH of 10 actions
    4. Update physics (20 steps per action)
    5. Repeat until phase complete
```

## Command-Line Options

```
--goal {1,2,3,4}         Goal ID to execute (default: 1)
--backend {cpu,gpu}      Genesis physics backend (default: gpu)
--max-iterations N       Max iterations for goals 1-3 (default: 20)
```

## Differences from Original Files

### Merged Improvements

1. **Code Deduplication**:
   - Single `execute_action()` instead of duplicated code
   - Shared robot initialization and parameter setting
   - Unified predicate visualization

2. **Better Modularity**:
   - `run_simple_goals()`: Handles goals 1-3
   - `run_goal4()`: Handles goal 4 with phases
   - Clean separation of concerns

3. **Enhanced Configuration**:
   - Command-line argument parsing
   - Configurable backend selection
   - Adjustable iteration limits

### What Was Preserved

- **All action types**: Both simple and position-aware actions
- **Batch execution**: Goal 4 batch sizes (2 for yellow, 10 for green)
- **Phase decomposition**: Sequential goal 41 → goal 42 execution
- **Error handling**: Try-catch blocks and failure detection
- **Physics updates**: Different step counts (80 for simple, 20 for Goal 4)

## Migration Guide

If you have scripts calling the old demos:

### Old Way
```bash
python3 demo.py              # Was hardcoded to goal 1
python3 demo_goal4.py        # Goal 4 only
```

### New Way
```bash
python3 demo.py --goal 1     # Explicit goal selection
python3 demo.py --goal 4     # Or use demo_goal4.py wrapper
```

## Development Notes

### Adding New Goals

To add a new goal (e.g., Goal 5):

1. Update `--goal` choices in argument parser
2. Add goal-specific scene creation if needed
3. Route to appropriate execution function:
   - Simple goals → `run_simple_goals()`
   - Complex goals → create new function like `run_goal5()`

### Debugging

Enable verbose output by printing predicates and block positions:

```python
# Already included in both execution functions:
visualize_predicates(preds)
print_block_positions(BlocksState, goal_id=goal_id)
```

## Performance Characteristics

| Goal | Blocks | Actions/Iteration | Physics Steps/Action | Typical Iterations |
|------|--------|-------------------|----------------------|-------------------|
| 1    | 6      | 1                 | 80                   | 5-15              |
| 2    | 6      | 1                 | 80                   | 10-20             |
| 3    | 6      | 1                 | 80                   | 10-20             |
| 4.1  | 12     | 2 (batch)         | 20                   | 10-25             |
| 4.2  | 6      | 10 (batch)        | 20                   | 2-5               |

## Troubleshooting

### "No such file or directory: 'pddl/domain_blocks.pddl'"
**Solution**: The domain file for simple goals (1-3) is missing. Copy it:
```bash
cp domain.pddl pddl/domain_blocks.pddl
```

Then update it to use typing:
- Change `(define (domain blocksworld)` to `(define (domain blocks)`
- Add `:typing` requirement and `(:types block)`
- Add type annotations to all predicates and action parameters

This file should already exist after setup. If it's missing, it was likely moved accidentally.

### "Error: unknown type block used in object definition!"
**Solution**: The domain file needs typing support. The [pddl/domain_blocks.pddl](pddl/domain_blocks.pddl) file should include:
- `:requirements :strips :typing`
- `(:types block)`
- Type annotations on all predicates (e.g., `?x - block`)
- Type annotations on all action parameters

### "goal4_config not available"
- Make sure `goal4_config.py` exists in the same directory
- Only needed for Goal 4

### "Unknown position {pos_name}"
- Position not defined in `GOAL4_POSITION_COORDS`
- Check `goal4_config.py` for valid position names

### GPU out of memory
- Use `--backend cpu` flag
- Close other GPU-intensive applications

## Testing

Test all goals to ensure proper functionality:

```bash
# Quick validation (won't complete, just tests initialization)
python3 demo.py --goal 1 --max-iterations 1
python3 demo.py --goal 2 --max-iterations 1
python3 demo.py --goal 3 --max-iterations 1
python3 demo.py --goal 4  # Will execute until first phase breakpoint
```

## Future Enhancements

Potential improvements:
- [ ] Support for custom goal specifications via config files
- [ ] Parallel execution of independent actions
- [ ] Real-time replanning based on execution failures
- [ ] Visualization of planned trajectories
- [ ] Logging to file for post-execution analysis
