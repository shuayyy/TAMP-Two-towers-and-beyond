export const meta = {
  name: 'diagnose-tamp',
  description: 'Read-only multi-lens diagnosis of the TAMP repo: headless/video path, physics cheats, git regressions, per-goal logic bugs',
  whenToUse: 'Run when you need a fresh, grounded picture of what is broken across the whole repo — after a big merge, when many things fail at once, or to refresh the known-breakage list in CLAUDE.md. Read-only: never edits code.',
  phases: [
    { title: 'Diagnose', detail: 'six parallel read-only investigators, one per layer' },
    { title: 'Verify', detail: 'adversarial refutation of every blocker/major finding' },
  ],
}

const REPO = '/home/shuaiyyy/github/TAMP-Two-towers-and-beyond'
const GENESIS = '~/miniconda3/envs/rbe550/lib/python3.11/site-packages/genesis'

const RULES = `
ABSOLUTE CONSTRAINT — YOU ARE READ-ONLY.
Do NOT use Edit, Write, or NotebookEdit. Do NOT modify, create, or delete any file in ` + REPO + `.
Do NOT run the simulator or demo.py. Do NOT run mutating git commands (checkout, stash, reset, restore,
clean). Read-only git (log, show, diff, blame) is encouraged. You MAY read files outside the repo,
especially the installed Genesis source. You MAY run short read-only python one-liners that only
import and introspect libraries.

CONTEXT
Repo: ` + REPO + ` (branch dev). Robotics TAMP course project: Franka Panda in Genesis sim,
OMPL motion planning, pyperplan PDDL task planning, stacking 4 cm cubes.
Env: conda env rbe550 — python 3.11, genesis 0.3.6, torch 2.5.1+cu121, ompl, pyperplan, numpy 2.3.3.
The base env has NONE of these. Always: conda run -n rbe550 python -c "..."
Genesis source: ` + GENESIS + `
Hardware: RTX 4060 Laptop 8GB, 16 cores, 23 GB RAM, DISPLAY=:0, NO Xvfb, ffmpeg present.

SITUATION: this code used to work, then many people edited it and broke it. The owner needs Goals 1
and 2 working first, then 3 and 4, each verified by HEADLESS runs that produce VIDEO files. Workarounds
are forbidden — every fix must be real physics, never teleporting objects or faking state.

GOALS (pddl/problem_generator.py get_goal_predicates):
 1: two 3-block towers (R-G-B, Y-M-C), 6 blocks, scenes scattered or pre-stacked
 2: one 6-block tower
 3: 8-block tallest tower
 4: 18 blocks -> yellow cross (12, goal_id 41) + green hollow square (6, goal_id 42)

Cite file:line for every claim. Never assert a library API from memory — read the installed source.
Mark confidence honestly.
`

const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['area', 'findings', 'notes'],
  properties: {
    area: { type: 'string' },
    notes: { type: 'string', description: 'key context and caveats, <=1200 chars' },
    findings: {
      type: 'array',
      maxItems: 12,
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'file', 'line', 'severity', 'detail', 'evidence', 'blocks_goal', 'confidence', 'is_physics_cheat'],
        properties: {
          title: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'integer' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'info'] },
          detail: { type: 'string' },
          evidence: { type: 'string' },
          blocks_goal: { type: 'string' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          is_physics_cheat: { type: 'boolean' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['verdict', 'reasoning', 'corrected_detail'],
  properties: {
    verdict: { type: 'string', enum: ['CONFIRMED', 'REFUTED', 'PARTIAL'] },
    reasoning: { type: 'string' },
    corrected_detail: { type: 'string' },
  },
}

const AREAS = [
  {
    key: 'headless-video',
    label: 'headless-video-api',
    prompt: `YOUR AREA: how to run headless and produce a video, with genesis 0.3.6 SPECIFICALLY.
Read the installed Genesis source; do not rely on knowledge of newer versions.
Determine: exact Scene.add_camera signature; exact camera recording methods and how a file is encoded;
which renderer backends work offscreen with show_viewer=False; whether EGL/OSMesa is used and whether a
display is required given DISPLAY=:0 with no Xvfb; any gs.init or env-var control over headless mode;
whether backend (cpu/gpu) is independent of the renderer, and the perf implication for multi-hour runs.
Confirm that scenes.py hardcodes show_viewer=True and adds no camera. Verify every API claim by
introspection (inspect.signature) and report the exact output.
Deliver the verified minimal recipe as a DESCRIPTION, not an edit, plus every gotcha.`,
  },
  {
    key: 'physics-cheats',
    label: 'physics-cheat-audit',
    prompt: `YOUR AREA: find every place the code fakes physics instead of simulating it.
Read robot_adapter.py fully, plus demo.py, planning.py, scenes.py.
Judge specifically: the attach_object/_sync_attached_object kinematic weld; whether
control_dofs_position and control_dofs_force issued to the same finger DOFs conflict (read the Genesis
source to determine which wins); the _fingers_locked override; whether place() ever lets the block
experience contact physics or simply teleports it to the target; _elevate_robot_base; whether ANY
friction or material properties are set on cubes or fingers and what the Genesis 0.3.6 defaults are;
and the hardcoded PUTDOWN target in demo.py.
For each, set is_physics_cheat and state what a physically honest implementation requires.`,
  },
  {
    key: 'git-archaeology',
    label: 'git-regression-archaeology',
    prompt: `YOUR AREA: git forensics. The code used to work; find what regressed.
Map the full history. Diff successive commits on robot_adapter.py, planning.py, demo.py,
symbolic_abstraction.py, scenes.py looking for changed constants (gains, thresholds, offsets, timings,
forces), changed pick/place geometry, and the commit that INTRODUCED the kinematic weld — establish what
the grasp looked like before it, and whether a real-physics grasp ever existed. Inspect merge commits for
clobbered fixes. Use git log -S for add_camera / start_recording / show_viewer / headless / render to see
whether a video capability was ever present and removed. Check any uncommitted working-tree changes.
Name the most likely last-known-good commit for goals 1 and 2, with evidence. Cite SHAs and before/after values.`,
  },
  {
    key: 'goal12',
    label: 'goal-1-2-pipeline',
    prompt: `YOUR AREA: trace Goals 1 and 2 end to end for logic bugs. Highest priority.
Read demo.py (run_simple_goals, execute_action), symbolic_abstraction.py, pddl/problem_generator.py,
task_planner.py, pddl/domain_blocks.pddl, scenes.py.
Investigate: whether the domain actions match the predicates abstract_state actually emits; whether the
predicate set is self-consistent while a block is held (holding vs ontable vs clear vs handempty) or
contradictory enough to make the PDDL init invalid; dead/broken code in symbolic_abstraction; whether
geom.get_pos() equals entity.get_pos() in Genesis and whether the STACK branch introduces an offset;
loop-detection correctness; completeness of get_goal_predicates(1) and (2); and whether repeated PUTDOWN
to one hardcoded target makes blocks collide, especially from the pre-stacked scene which requires UNSTACK.`,
  },
  {
    key: 'goal34',
    label: 'goal-3-4-pipeline',
    prompt: `YOUR AREA: trace Goals 3 and 4 for logic bugs.
Read goal4_config.py fully, pddl/domain_blocks_goal4.pddl fully, pddl/problem_generator.py,
task_planner.py reorder_plan_by_layers, demo.py run_goal4 and the *-AT action branches, scenes.py,
and the goal-4 branch of symbolic_abstraction.py.
Compute the actual numbers: do the yellow-cross and green-square coordinates overlap given SPACING and
the base offsets; is the 2 mm at-position tolerance physically achievable given place() servos XY to
1 mm and physics then settles, or does it guarantee an infinite replanning loop; are all positions within
the Franka's reach; is an 8-tall tower reachable. Check the goal-4 domain's predicates against what
problem_generator actually emits for undeclared or never-produced predicates. Verify the nested-tuple
construction of the position-free predicates round-trips correctly. Find a counterexample where
reorder_plan_by_layers produces an invalid plan. Assess open-loop batch execution of 16 actions.`,
  },
  {
    key: 'control-ik',
    label: 'control-ik-ompl',
    prompt: `YOUR AREA: control, IK and OMPL correctness. Read robot_adapter.py and planning.py fully plus
the Genesis source for every API they use.
Investigate: whether the kp/kv/force_range in demo.py match the reference Franka gains Genesis itself
ships; what inverse_kinematics returns in 0.3.6, whether it signals failure, and the risk of the code
never checking; whether planning over all 9 DOFs including fingers is correct and whether the
_maybe_lock_fingers override invalidates the collision-checked path; whether calling set_qpos inside the
OMPL validity checker corrupts sim state and whether detect_collision is meaningful without a step;
whether comparing a geom index against entity.idx in collision_with_attached_object is an index-space
mismatch; what happens on the no-collision-check fallback when OMPL returns empty; whether the carried
block is in the collision model at all; and whether one sim step per waypoint is enough for the PD
controller to track at dt=0.01.`,
  },
]

phase('Diagnose')

const results = await pipeline(
  AREAS,
  (a) => agent(RULES + '\n\n' + a.prompt, { label: a.label, phase: 'Diagnose', schema: FINDINGS_SCHEMA }),
  (res, area) => {
    if (!res || !res.findings) return { area: area.key, notes: (res && res.notes) || '', findings: [] }
    const worth = res.findings.filter((f) => f.severity === 'blocker' || f.severity === 'major').slice(0, 5)
    if (!worth.length) return { area: area.key, notes: res.notes, findings: res.findings }
    return parallel(
      worth.map((f) => () =>
        agent(
          RULES +
            '\n\nADVERSARIAL VERIFICATION. Another agent made the claim below. Your job is to REFUTE it.' +
            '\nRead the actual code and the actual Genesis source. Default to REFUTED if the claim does not' +
            '\nhold exactly as stated. Mark PARTIAL if the problem is real but described inaccurately.' +
            '\n\nCLAIM: ' + f.title +
            '\nFILE: ' + f.file + ':' + f.line +
            '\nDETAIL: ' + f.detail +
            '\nEVIDENCE OFFERED: ' + f.evidence +
            '\nCLAIMED TO BLOCK: ' + f.blocks_goal,
          { label: 'verify:' + f.title.slice(0, 40), phase: 'Verify', schema: VERDICT_SCHEMA, effort: 'high' },
        ).then((v) => Object.assign({}, f, { verification: v })),
      ),
    ).then((verified) => ({
      area: area.key,
      notes: res.notes,
      findings: verified.filter(Boolean).concat(res.findings.filter((f) => worth.indexOf(f) === -1)),
    }))
  },
)

const clean = results.filter(Boolean)
log('Diagnosis complete across ' + clean.length + ' areas')
return { areas: clean }
