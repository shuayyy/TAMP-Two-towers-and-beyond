# Quick Start Guide - Unified TAMP Codebase

## ✅ Merge Complete!

This codebase now supports **all goals (1-4)** in a single unified system.

---

## 🚀 Running the Demo

### Goals 1-3 (6 blocks)

```bash
# Goal 1: Build two towers (r-g-b, y-m-c)
python3 demo.py --goal 1

# Goal 2: Build single 6-block tower
python3 demo.py --goal 2

# Goal 3: Build alternative 6-block tower
python3 demo.py --goal 3
```

### Goal 4 (18 blocks)

```bash
# Goal 4: Build yellow cross + green hollow square
python3 demo.py --goal 4
```

---

## 🧪 Testing

```bash
# Quick test (verifies Goals 1-3)
python3 test_goals_simple.py

# Expected output:
# ✓ All tests passed!
# 🎉 Goals 1-3 are fully functional in the merged codebase!
```

---

## 📖 What Changed?

The two codebases (`Two-towers-and-beyond` and `Two-towers-and-beyond_goal4`) have been **merged into one**. Key changes:

1. **`symbolic_abstraction.py`** - Now accepts `goal_id` parameter
2. **`task_planner.py`** - Automatically selects correct domain file
3. **`pddl/problem_generator.py`** - Supports all goals (1, 2, 3, 4, 41, 42)
4. **`pddl/domain_blocks.pddl`** - Copied from original for Goals 1-3

---

## 📁 File Structure

```
Two-towers-and-beyond_goal4/  ← UNIFIED CODEBASE (use this!)
├── demo.py                    ← Run this (supports --goal 1-4)
├── test_goals_simple.py       ← Test this
└── MERGE_COMPLETE.md          ← Read this for details

Two-towers-and-beyond/         ← OLD (can be archived)
```

---

## ⚙️ Optional Arguments

```bash
# Use CPU instead of GPU
python3 demo.py --goal 1 --backend cpu

# Limit iterations (prevent infinite loops)
python3 demo.py --goal 1 --max-iterations 15
```

---

## �� Full Documentation

For complete details, see **[MERGE_COMPLETE.md](MERGE_COMPLETE.md)**

---

## ✨ Quick Verification

Run this to confirm everything works:

```bash
cd Two-towers-and-beyond_goal4
python3 test_goals_simple.py
```

You should see:
```
[task_planner] Running pyperplan with A* (optimal for Goals 1-3)...
✓ Plan generated: 8 actions
✓ All tests passed!
🎉 Goals 1-3 are fully functional in the merged codebase!
```

---

## 🔧 Recent Fix (Dec 7, 2024)

**Issue**: Plans were suboptimal (16 actions instead of 8)
**Fix**: Now uses A* planner for Goals 1-3 (optimal) and Enforced Hill-Climbing for Goal 4 (fast)
**Result**: 50% reduction in plan length, more stable execution

See [PLANNER_FIX.md](PLANNER_FIX.md) for details.

---

**Status**: ✅ Ready to use!
**Last Updated**: December 7, 2024
