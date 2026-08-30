export const meta = {
  name: 'fix-goal-loop',
  description: 'Attack one stubborn TAMP goal failure: multi-lens root-cause analysis, competing fix designs, adversarial judging, then a single serial implement-and-verify pass',
  whenToUse: 'Use when /fix-goal has stalled on a specific failure and you want several independent root-cause hypotheses and competing fix designs judged against each other before touching code. Pass args {goal, scene, failure} where failure is the captured failure description or log excerpt.',
  phases: [
    { title: 'Analyze', detail: 'four independent root-cause lenses, read-only' },
    { title: 'Design', detail: 'three competing fix proposals' },
    { title: 'Judge', detail: 'adversarial scoring against the no-jugaad rule' },
    { title: 'Apply', detail: 'single serial implementer' },
    { title: 'Verify', detail: 'headless runs and acceptance check' },
  ],
}

const REPO = '/home/shuaiyyy/github/TAMP-Two-towers-and-beyond'
const GOAL = (args && args.goal) || 1
const SCENE = (args && args.scene) || 1
const FAILURE = (args && args.failure) || '(no failure description supplied — reproduce it first)'

const BASE = `
CONTEXT
Repo: ` + REPO + ` (branch dev). TAMP: Franka Panda in Genesis 0.3.6, OMPL motion planning,
pyperplan PDDL task planning, 4 cm cubes.
Env: ALWAYS run python as: conda run -n rbe550 python ...   (the base env lacks ompl and pyperplan)
Genesis source: ~/miniconda3/envs/rbe550/lib/python3.11/site-packages/genesis
Hardware: RTX 4060 Laptop 8 GB, 16 cores, 23 GB RAM. Only ONE simulation may run at a time.

TARGET: Goal ` + GOAL + `, scene ` + SCENE + `.
OBSERVED FAILURE:
` + FAILURE + `

THE NO-JUGAAD RULE — this is the owner's hard requirement and it governs everything:
Every fix must be a real physics or logic fix. Banned outright: teleporting blocks via set_pos/set_quat;
loosening any tolerance so a check passes; skipping or swallowing a failed action; disabling collision
checking; hardcoding a known-good pose or plan; raising forces or settling steps without a physical
justification; making perception report the intended state rather than the observed one.
The test for any proposed fix: would it still work on a real Franka with real cubes? If not, it is banned.
Read .claude/skills/physics-honest-fix/SKILL.md for the full taxonomy.

LAYER ORDER — a bug in a lower layer masquerades as several bugs above it. Always fix downward-first:
  headless/video -> physics & materials -> grasp geometry -> control -> motion planning ->
  symbolic abstraction -> PDDL domain -> executive loop.

Cite file:line. Never assert a Genesis API from memory — read the installed source.
`

const READONLY = BASE + `
You are READ-ONLY for this phase. Do NOT use Edit or Write. Do NOT run the simulator (it is serialized
to a later phase and would contend for the GPU). Analysis only.
`

const CAUSE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['lens', 'hypotheses'],
  properties: {
    lens: { type: 'string' },
    hypotheses: {
      type: 'array',
      maxItems: 4,
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['cause', 'layer', 'file', 'line', 'mechanism', 'evidence', 'confidence'],
        properties: {
          cause: { type: 'string' },
          layer: { type: 'string', enum: ['headless', 'physics', 'grasp', 'control', 'motion', 'abstraction', 'domain', 'executive'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          mechanism: { type: 'string', description: 'the causal chain from this defect to the observed failure' },
          evidence: { type: 'string' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
      },
    },
  },
}

const LENSES = [
  { key: 'physics', prompt: 'LENS: physics and contact. Is the failure caused by materials, friction, mass, contact parameters, solver substeps, or the kinematic weld standing in for a real grasp? Read the Genesis defaults rather than assuming them. Compute force balances where relevant.' },
  { key: 'control', prompt: 'LENS: control and IK. Is the failure caused by PD gains, force limits, unchecked IK convergence, trajectory timing, too few sim steps per waypoint, or conflicting control modes on the same DOF? Compare against the reference Franka setup Genesis itself ships.' },
  { key: 'symbolic', prompt: 'LENS: perception and symbolic reasoning. Is the failure caused by abstract_state producing a wrong or self-contradictory predicate set, thresholds that cannot be met by achievable placement accuracy, a PDDL domain that does not match the emitted predicates, or an executive loop that mis-handles replanning? Trace the exact predicate set at the failing step.' },
  { key: 'motion', prompt: 'LENS: motion planning. Is the failure caused by the OMPL setup — planning over finger DOFs, validity checking that mutates sim state, the carried block being absent from the collision model, index-space mismatches in collision filtering, or the unchecked fallback when planning returns an empty path?' },
]

phase('Analyze')
const analyses = (await parallel(
  LENSES.map((l) => () => agent(READONLY + '\n\n' + l.prompt, { label: 'analyze:' + l.key, phase: 'Analyze', schema: CAUSE_SCHEMA })),
)).filter(Boolean)

const allHyps = analyses.flatMap((a) => (a.hypotheses || []).map((h) => Object.assign({ lens: a.lens }, h)))
log('Collected ' + allHyps.length + ' root-cause hypotheses across ' + analyses.length + ' lenses')

const hypText = allHyps
  .map((h, i) => i + '. [' + h.layer + '/' + h.confidence + '] ' + h.cause + ' (' + h.file + ':' + h.line + ') — ' + h.mechanism)
  .join('\n')

const DESIGN_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['approach', 'root_cause', 'layer', 'changes', 'physical_justification', 'risks', 'verification'],
  properties: {
    approach: { type: 'string' },
    root_cause: { type: 'string' },
    layer: { type: 'string' },
    changes: {
      type: 'array',
      maxItems: 10,
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['file', 'what', 'why'],
        properties: { file: { type: 'string' }, what: { type: 'string' }, why: { type: 'string' } },
      },
    },
    physical_justification: { type: 'string', description: 'the physics argument, with numbers, for every constant introduced or changed' },
    risks: { type: 'string' },
    verification: { type: 'string', description: 'how to prove it worked without relying on the demo self-report' },
  },
}

phase('Design')
const STANCES = [
  { key: 'minimal', prompt: 'STANCE: minimal correct fix. Find the single deepest root cause and fix only that. Prefer the smallest change that is physically honest. Resist scope creep.' },
  { key: 'physics-first', prompt: 'STANCE: physics-first. Assume the grasp and contact model are the root problem. Design the fix that replaces faked mechanics with genuinely simulated ones — real friction grasping, correct materials, correct force control — even if it is a larger change.' },
  { key: 'systemic', prompt: 'STANCE: systemic. Assume several defects compound. Design an ordered sequence of fixes, lowest layer first, that makes the whole pipeline sound rather than patching the visible symptom. Say explicitly which fix must land first and why.' },
]

const designs = (await parallel(
  STANCES.map((s) => () =>
    agent(
      READONLY + '\n\nROOT-CAUSE HYPOTHESES gathered by four independent analysts:\n' + hypText +
        '\n\n' + s.prompt +
        '\n\nProduce a concrete fix design. Every constant you introduce or change needs a numeric physical' +
        '\njustification. Do not propose anything on the banned list. Do not write code yet — design only.',
      { label: 'design:' + s.key, phase: 'Design', schema: DESIGN_SCHEMA },
    ),
  ),
)).filter(Boolean)

const JUDGE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['winner_index', 'rationale', 'jugaad_violations', 'merged_plan', 'ordered_steps'],
  properties: {
    winner_index: { type: 'integer' },
    rationale: { type: 'string' },
    jugaad_violations: { type: 'string', description: 'any banned pattern found in ANY proposal, named explicitly; "none" if clean' },
    merged_plan: { type: 'string', description: 'the winning design plus any strictly better ideas grafted from the others' },
    ordered_steps: {
      type: 'array',
      maxItems: 12,
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['step', 'file', 'change', 'justification'],
        properties: { step: { type: 'integer' }, file: { type: 'string' }, change: { type: 'string' }, justification: { type: 'string' } },
      },
    },
  },
}

phase('Judge')
const judgment = await agent(
  READONLY +
    '\n\nThree fix designs were produced independently. Judge them adversarially.\n\n' +
    designs.map((d, i) => 'DESIGN ' + i + ' [' + d.approach + ']\nroot cause: ' + d.root_cause + ' (layer ' + d.layer + ')\nchanges: ' + JSON.stringify(d.changes) + '\njustification: ' + d.physical_justification + '\nrisks: ' + d.risks + '\nverification: ' + d.verification).join('\n\n---\n\n') +
    '\n\nFirst, hunt for jugaad in EVERY proposal — a loosened tolerance, a teleport, a swallowed failure,' +
    '\nan unjustified constant. Name every violation you find; reject any design that depends on one.' +
    '\nThen pick the design most likely to make the goal genuinely work, graft in strictly better ideas' +
    '\nfrom the others, and emit an ordered, minimal implementation plan, lowest layer first.',
  { label: 'judge', phase: 'Judge', schema: JUDGE_SCHEMA, effort: 'high' },
)

if (!judgment) {
  log('Judging failed — returning analyses and designs for manual review')
  return { goal: GOAL, scene: SCENE, analyses, designs, judgment: null }
}

log('Selected design ' + judgment.winner_index + ' with ' + judgment.ordered_steps.length + ' steps')

phase('Apply')
const applied = await agent(
  BASE +
    '\n\nYou are the IMPLEMENTER. You may edit code. Apply exactly this plan, in order:\n\n' +
    judgment.merged_plan +
    '\n\nORDERED STEPS:\n' +
    judgment.ordered_steps.map((s) => s.step + '. ' + s.file + ' — ' + s.change + '  [' + s.justification + ']').join('\n') +
    '\n\nRules: implement only what the plan specifies. Every changed constant gets an inline comment with' +
    '\nits physical justification. Do NOT run the simulator — verification is a separate serialized phase.' +
    '\nDo NOT commit. If a step turns out to be wrong once you see the real code, stop and report why' +
    '\nrather than improvising a workaround.' +
    '\n\nReturn a precise summary of every edit you made, file:line, and anything in the plan you did not do.',
  { label: 'apply', phase: 'Apply' },
)

phase('Verify')
const VERIFY_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['passed', 'runs_attempted', 'runs_passed', 'evidence', 'remaining_blocker'],
  properties: {
    passed: { type: 'boolean' },
    runs_attempted: { type: 'integer' },
    runs_passed: { type: 'integer' },
    evidence: { type: 'string', description: 'video paths with ffprobe results, final predicate comparison, geometric check numbers' },
    remaining_blocker: { type: 'string', description: 'if not passing, the specific failing layer and symptom; "none" if passing' },
  },
}

const verified = await agent(
  BASE +
    '\n\nYou are the VERIFIER. The following changes were just applied:\n\n' + applied +
    '\n\nRun goal ' + GOAL + ' scene ' + SCENE + ' HEADLESS and verify honestly.' +
    '\n- You are the only agent permitted to run the simulator. Launch runs in the BACKGROUND' +
    '\n  (run_in_background: true) and wait on them; never poll with sleep, never block the foreground.' +
    '\n- Runs may take hours. That is expected and budgeted.' +
    '\n- Apply every acceptance criterion in .claude/skills/goal-verify/SKILL.md. Do NOT trust the demo' +
    '\n  printing GOAL REACHED. Verify the video with ffprobe. Verify the structure geometrically from raw' +
    '\n  block poses, not only from the abstraction.' +
    '\n- Three consecutive passes with different seeds are required to call it working.' +
    '\n- Report failures faithfully, with the output. Never round a failure up. If it fails, say which' +
    '\n  layer failed and why — do not patch it here.',
  { label: 'verify:goal' + GOAL, phase: 'Verify', schema: VERIFY_SCHEMA },
)

return {
  goal: GOAL,
  scene: SCENE,
  root_cause: judgment.merged_plan,
  jugaad_violations_found: judgment.jugaad_violations,
  steps: judgment.ordered_steps,
  applied: applied,
  verification: verified,
}
