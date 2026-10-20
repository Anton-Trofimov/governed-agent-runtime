# BC-009 — evidence-derived operator outcome view

Authorized 2026-10-14: implement a small result-presentation boundary before UI.
Baseline: BC-008 merged PR #9, main a0d09693cc14cc907c57f69e8b93fcd941d77c6e.

## Question and scope

Can an operator distinguish confirmed effects, last observed environment facts,
termination cause and remaining work without reconstructing a trace? Build a
read-only projection and text renderer for recorded BC-006/007/008 run directories.
One explicit offline CLI produces text or JSON for future UI reuse. No UI,
new model calls, model-visible hints, execution changes or automatic remediation.
Live runner integration remains separate so evaluated runners/packets stay intact.

## Contract

`build_view(run_directory)` reads only manifest.json and trace.jsonl, returns a
versioned JSON-serializable derived view. It never writes evidence. Source SHA-256
and trace event IDs accompany fields. Renderer is deterministic Russian text.
Original model rationale is separately labeled, quoted without correction and
never used to establish facts or authority. Do not show internal thinking.

Use observation_applied, never unvalidated tool_result_raw, as last recorded
observation. State explicitly that this is historical evidence, not a current
live health check. Show its time and identity. Missing observation is unknown.
Show recovery status and shift binding separately from rollback completion.
Completion requires agreement of terminal runtime state and task_completed;
contradictory or incomplete traces must not produce a successful view.

Track started tool calls as attempts. An applied observation after a matching
raw tool result establishes observed effect; without it, effect is unknown.
Pending confirmation is not execution, and must not become an unknown executed
write. Show pending action separately; never suggest replaying an old CONFIRM ID.
Unknown write effects suppress reassuring conclusions from older observations.

Runtime end reason comes from recorded terminal/transition and manifest agreement.
KeyboardInterrupt is a runner interruption, not model STOP, timeout or refusal.
For model STOP, distinguish model explanation from recorded runtime reason.
Remaining candidate count/full-traffic/recovery facts must not redefine the user's
goal as mandatory rollback. Human follow-up is a presentation recommendation,
not a policy authorization or an executed escalation.

## Material dependency: runner outputs

The presentation layer depends on the recorded `manifest.json` / `trace.jsonl`
output contract and semantics of the BC-006/007/008 runners. Its current compatibility
basis is the saved runs named in Acceptance and their read-only replay tests.
In particular, it consumes manifest outcome/completion fields and trace event IDs,
terminal transitions/reasons, applied observations, tool attempts/results,
confirmation events, runner failures and model proposals. Applied observations
establish recorded facts; raw results and model rationale do not.
Changes to these structures or meanings require assessing presentation compatibility
and its existing contract tests. This documents an existing consumer dependency;
it does not change runner behavior or introduce a new output schema or dependency
validation mechanism.

## Acceptance

- BC-006 nominal and BC-008 completed run: verified rollback and separate recovery
  evidence; no unsupported claim that every health field is healthy.
- BC-007 STOP: SAFE_FALLBACK/MODEL_REQUESTED_STOP, recovery FAIL, candidate retained,
  exact STOP rationale separately available, human review recommendation.
- BC-008 interrupted A-20: one observed scale, pending shift not executed,
  KeyboardInterrupt; no fabricated recovery/removal or automatic retry advice.
- Adversarial recorded variants: raw PASS without applied observation cannot
  establish PASS; started write without validated result is unknown; fabricated
  model success cannot establish completion; missing/contradictory terminal
  evidence fails closed. Historical freshness must not be presented as live.
- Every displayed operational fact refers to its source event; rendering must
  not mutate source bytes. Verify all seven BC-008 attempts plus BC-006/007.

Development tests and replay checks are not new measured model evidence.
Deliver three concrete human-review examples with links to full view JSON and
source evidence. Human disposition of readability remains pending after tests.
No benchmark, reliability or usability claim without its corresponding evidence.

## Human-review refinement — 2026-10-14

Use the same order for success/STOP/interruption: plain-language outcome, recorded
system state, then technical details and model explanation. Time refers to the
last applied observation available at termination, not a new live check. Do not
require an operator to repeat a successful final check without another reason.
Explain shift as traffic transfer. Never use a blanket runtime PASS label.
Preserve original rationale in JSON/evidence, but the text presentation may omit
sentences/clauses about the internal write budget. Label this as an excerpt with
service-budget wording omitted; no silent correction, translation or new inference.
Label rationale as explanation before the proposed action (or explanation of STOP),
not a final model answer: final runtime verification has no subsequent model call.

## Accepted presentation refinement — 2026-10-15

Human accepted the r4 content concept and authorized implementation closure.
Text order: «Статус» → «Подтверждённое состояние» → «Отчёт / Подробнее».
These correspond to operator communication and a separate state panel in a future
UI, both derived from the same evidence, not separate authorities. Preserve actual
observation timestamps and saved-run scope. Use «Реплик версии», not «новой версии».
Success explicitly states removal; STOP describes the reached state and remaining
work, not one fixed recovery-FAIL template. Interruption remains a recorded
KeyboardInterrupt example, never relabeled refusal or timeout. Unknown write
outcomes must suppress claims about unchanged traffic or confirmed recovery.
Show concrete confirmed scale/traffic effects. Keep model rationale in details.
Future UI refusal/expiry examples in r4 are design examples, not measured runs.
Resume, live integration, buttons and UI implementation remain out of scope.
