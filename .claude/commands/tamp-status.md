---
description: Report which goals currently pass, which fail and why, and what the next action is
---

Give a current, evidence-based status of all four goals. No optimism, no guessing.

1. Read `CLAUDE.md` for the recorded state and the known-breakage list.

2. Read whatever run evidence exists under `runs/` — logs, videos, JSON summaries. Check video files
   with ffprobe rather than assuming a file on disk means a successful run.

3. Report a table: goal, scene, last result (PASS n/N or FAIL), date, video path, and — for failures —
   the specific failing layer and predicate.

4. Distinguish clearly between:
   - verified passing (3 consecutive clean headless runs, video confirmed)
   - passing once (not yet trustworthy)
   - failing with known root cause
   - failing with unknown root cause
   - not yet attempted

5. State the single next action, in the project's priority order: Goal 1 scene 1 → Goal 1 scene 2 →
   Goal 2 → Goal 3 → Goal 4.1 → Goal 4.2.

If there is no run evidence at all, say that plainly rather than inferring status from the code.
