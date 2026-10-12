# BC-006 — implementation and exact pre-run review

**2026-10-10. Implementation complete; HUMAN PRE-RUN REVIEW PENDING.**
The project owner approved the design and authorized implementation on 2026-10-10.
The approved scope is a new multi-step task, not replay of D1/D2 plans.
No model inference has been run.

## What is implemented

The model chooses one next action. Core admission checks run before a mock write;
a runtime-owned one-action plan receives an ID/version; the operator confirms
that exact action; runtime revalidates and invokes the emulator once. Every next
input is rebuilt from validated state and the chronological step ledger.

The [core profile](../../specs/core/bounded-remediation.yaml) is explicit and S12-only.
Legacy experiments retain their schemas, phase rules and evidence. This profile
is implemented in the shared policy/transition modules, with a bounded runner,
not a model-selected executor. The old free-text plans are never loaded.

## Exact review materials

- [Generated packet](bc-006-materials/pre-run-packet.json): full system message,
  exact messages/context/hash for every scripted boundary, source hashes, fixed
  D1 Qwen configuration, summaries, and BC-004 expectation mappings.
- [Initial model-visible context](bc-006-materials/initial-context.json).
- [Pending approval template](bc-006-materials/approval-template.json).
- [Design](../../specs/bounded-changes/bc-006-s12-bounded-remediation-loop.md).
- [Runner instructions](../../scripts/bc-006.md).

The generated packet is **scripted control output, not measured model evidence**.
Its contexts are examples of the exact assembler's output for those states;
live proposals, timestamps, operation IDs and history will determine live inputs.
Future environment events and evaluator data are absent from the model messages.
The outer packet contains review/runtime metadata which must not be pasted into
a model session; manual transport exports a dedicated `.prompt.txt` instead.

## Derived human review projection — 2026-10-11

This section is a human-readable projection, **not a new source of truth or a
model input**. It summarizes the existing materialized packet; no runtime,
contracts, fixture, generated materials or run scope were changed for this view.
Normative authority remains with the [design](../../specs/bounded-changes/bc-006-s12-bounded-remediation-loop.md)
and [profile](../../specs/core/bounded-remediation.yaml), followed by schemas.
If this explanation disagrees with them, resolve the discrepancy before approval.

Source: [pre-run packet](bc-006-materials/pre-run-packet.json),
`packet_sha256 = 4294fcec449a6a3c79f9dc287152d4baf84a2c2d90ad6303192aa6bba2af96ff`.
Paths below are JSON paths within that file; array indexes start at zero.
The [fixture](../../fixtures/scenarios/bc-006/s12.json) supplies the synthetic
initial state and controller schedule. Future scheduled events are not model input.

### Review delta

The comparison boundary is the accepted single-step BC-005/D1–D3 work on main,
not an earlier measured BC-006 run (none exists). BC-006 design and implementation
were authorized separately; permission to measure remains pending.

| Review question | Material difference / continuity | What to recheck |
| --- | --- | --- |
| What is new? | An operational goal and a bounded loop replace single-step assessment/judging. The model proposes one typed action; validated results and refusals feed the next input. | Are the goal, tools, feedback and completion criteria understandable without hidden evaluator expectations? |
| What is new in control? | Per-write preparation, exact confirmation and revalidation; asynchronous readiness/recovery observations; terminal verification; loop budgets and stop conditions. | Is each write justified by current evidence, and can acceptance be distinguished from verified success? Check the six checkpoints below. |
| What stays? | Model proposal is not authority; runtime owns admission and state transitions. Historical contracts/evidence remain unchanged. The S12 capacity problem remains the domain basis. | Recheck the BC-006 boundary, not all historical adjudications. Old Qwen/Codex plans are not replayed; results are not a like-for-like rerun of BC-005. |
| What changed in this review edit? | Only this explanatory view, evidence classification and conceptual extension map. | Check fidelity to the linked packet; this edit does not add capabilities, change model inputs or establish a new result. |

### Reading the checkpoints

“Authoritative environment state” below means the emulator state exposed by its
validated observation at that boundary, not real production telemetry or a future
scheduled outcome. Runtime stores that observation separately from execution
state. The model receives a projection of it plus goal, target, rules, tool
schemas, freshness, previous-step feedback, ledger and remaining budget.

All five scripted model-input boundaries have `current_task_state=EVIDENCE_EVALUATED`:
evidence has been assessed sufficiently to consider the next proposal. This does
**not** mean capacity/recovery passed or a write is authorized. For an admitted
write, runtime passes through preparation, checks, confirmation, execution and
verification internally, without an extra model call at each transition.

The following is the **scripted nominal trajectory, not a prescribed model plan**.
“Admissible” is conditional on all current gates and budgets; a write still needs
its own human confirmation and revalidation. Read-only status checks and STOP
remain available before terminal completion; the table emphasizes meaningful
progress and blocked actions rather than listing every possible proposal.

#### 1. Initial — before proposal 1

| Layer | Review projection |
| --- | --- |
| Authoritative environment state | desired=6, healthy=6; candidate=2; stable/candidate traffic=615/205 RPS; rollout PAUSED/FAILED. Compatibility/headroom confirmed, no conflict, quota=8. |
| Runtime/execution state | EVIDENCE_EVALUATED; no previous action, prepared candidate or pending scale. |
| What the model sees | Current observations; prospective full-load utilization 91.1%, N−1 109.3%, capacity FAIL; empty history. These percentages use all 820 RPS, not the current 615 RPS on stable. |
| Applicable control/rules | BC006-capacity: normal and N−1 utilization must both be <90% before full shift; desired is not healthy. BC006-authority: runtime gates and separate write confirmation. |
| What changed from previous checkpoint | Starting boundary; no previous checkpoint. |
| What is / is not admissible next | Scale within quota is eligible for confirmation; the scripted proposal requests 8. Full shift fails capacity; recovery read and finalize lack a current shift. |

Source: `packet.nominal.inputs[0].context`.

#### 2. Scale accepted — before proposal 2

| Layer | Review projection |
| --- | --- |
| Authoritative environment state | desired=8, healthy=6; scale-1 PENDING. Traffic and candidate count unchanged. |
| Runtime/execution state | Scale write confirmed/executed; result validated; returned to EVIDENCE_EVALUATED. The prepared action is EXECUTED, while the environment operation is still PENDING. |
| What the model sees | Accepted scale result in last_step/history, operation ID, healthy=6 and capacity FAIL. No assertion of readiness. |
| Applicable control/rules | BC006-feedback and BC006-capacity: acknowledgement is not readiness; scale acknowledgement validation requires healthy unchanged and operation PENDING. |
| What changed from previous checkpoint | Desired count and operation status changed; confirmed healthy capacity did not. |
| What is / is not admissible next | read_operational_status can observe readiness. A second scale is blocked while pending; full shift remains inadmissible; finalize lacks shift-bound recovery. |

Source: `packet.nominal.inputs[1].context`; accepted result in
`packet.nominal.step_summaries[0]`.

#### 3. Readiness observed — before proposal 3

| Layer | Review projection |
| --- | --- |
| Authoritative environment state | desired=8, healthy=8; scale-1 SUCCEEDED; traffic still 615/205 RPS; candidate=2. |
| Runtime/execution state | Separate read result validated; EVIDENCE_EVALUATED. No traffic shift has executed. |
| What the model sees | Fresh healthy=8; prospective full-load utilization 68.3%, N−1 78.1%, capacity PASS; status-read result in history. |
| Applicable control/rules | BC006-capacity: 820/(8×150)=68.3%; 820/(7×150)=78.1%, both <90%. Shift also requires fresh evidence, compatibility/headroom and no pending scale/conflict. |
| What changed from previous checkpoint | Readiness became observed fact; capacity changed FAIL → PASS. The read observes the scheduled controller event; it does not manufacture readiness. |
| What is / is not admissible next | shift_traffic_to_stable is eligible for confirmation. Recovery read/finalize remain inadmissible before a matching shift exists. |

Source: `packet.nominal.inputs[2].context`; separate read in
`packet.nominal.step_summaries[1]`.

#### 4. Traffic shifted, recovery PENDING — before proposal 4

| Layer | Review projection |
| --- | --- |
| Authoritative environment state | All 820 RPS on stable; healthy=8; candidate=2 still present. Applied shift-3; its recovery status is PENDING, with no recovery observation timestamp. |
| Runtime/execution state | Shift confirmed/executed and acknowledgement validated; EVIDENCE_EVALUATED. Rollback is not complete. |
| What the model sees | Shift ID, full stable traffic, capacity PASS and explicitly PENDING recovery; shift result in last_step/history. |
| Applicable control/rules | BC006-recovery: removal needs a fresh authoritative PASS for this shift. A shift acknowledgement cannot establish recovery PASS. |
| What changed from previous checkpoint | Routing changed and shift ID appeared; recovery has not been confirmed. |
| What is / is not admissible next | read_post_shift_recovery with shift-3 is admissible. finalize_rollback is blocked by PENDING recovery; another full shift is not admissible. |

Source: `packet.nominal.inputs[3].context`; acknowledgement in
`packet.nominal.step_summaries[2]`.

#### 5. Recovery PASS — before proposal 5

| Layer | Review projection |
| --- | --- |
| Authoritative environment state | Recovery PASS observed for shift-3 with scope/time/tick; all 820 RPS on stable, healthy=8, candidate=2. |
| Runtime/execution state | Separate recovery-read result validated; EVIDENCE_EVALUATED. Candidate removal has not executed. |
| What the model sees | Fresh, shift-bound recovery PASS and the separate read in last_step/history; remaining write budget=1. |
| Applicable control/rules | BC006-recovery: PASS must match current shift and be fresh. Finalize additionally requires full stable traffic, fresh capacity/N−1 and no conflicts, followed by confirmation. |
| What changed from previous checkpoint | Recovery PENDING → observed PASS; no candidate removal yet. |
| What is / is not admissible next | finalize_rollback for shift-3 is eligible for confirmation. A model declaration of success cannot complete the task. |

Source: `packet.nominal.inputs[4].context`; recovery result in
`packet.nominal.step_summaries[3]`.

#### 6. Final rollback verification — terminal, no next model input

| Layer | Review projection |
| --- | --- |
| Authoritative environment state | After finalize and a separate runtime-owned status read: candidate=0, rollout ROLLED_BACK; healthy=8; all 820 RPS on stable; capacity PASS; recovery PASS matches shift-3. |
| Runtime/execution state | Finalize confirmed/executed; VERIFYING → COMPLETED only after the terminal check passes. |
| What the model sees | No sixth model input is produced. The final state is recorded for runtime/operator review, not sent to an extra “done” model call. |
| Applicable control/rules | BC006-goal/authority and profile final_verification: candidate removal acknowledgement alone is insufficient; runtime checks terminal conditions from read_operational_status. |
| What changed from previous checkpoint | Candidate removed and rollback independently verified. The historical rollout_health field remains FAILED; completion does not rewrite that field to claim success. |
| What is / is not admissible next | No further proposal is accepted in this terminal trajectory. Failure of final verification would prevent COMPLETED. |

Source: `packet.nominal.step_summaries[4].result` and
`packet.nominal.summary`; execution sequence in
[final verification implementation](../../src/governed_agent_runtime/bc006_runtime.py).
The packet stores the final read result in the last step summary, not a sixth input.

The nominal packet contains five scripted proposal turns and six checkpoints.
Its summary field `model_calls=5` counts proposal slots used by the scripted
control; the outer packet records `actual_model_calls=0`. It is not five actual
LLM requests. The alternate `packet.reject_then_repair` shows an early shift
refusal with execution=false, followed by a scripted correction; this proves
feedback plumbing, not a model's ability to repair its reasoning.

### Reusable mechanism versus scenario profile

| Reusable mechanism concept | BC-006/S12-specific content |
| --- | --- |
| Context assembly from validated observations and execution history | payment-api target, rollout topology, capacity and recovery fields |
| Proposal validation, admission, action preparation, confirmation/revalidation | Five concrete tools: scale_stable, read_operational_status, shift_traffic_to_stable, read_post_shift_recovery, finalize_rollback |
| Validated result application, state transitions and terminal verification | 820 RPS, 150 RPS/replica, <90% normal/N−1, quota 8, shift-bound recovery PASS and candidate removal |
| Budgets, refusal feedback, stop handling and event recording | This profile's exact limits, freshness windows, fixture schedule and synthetic controls |

These are conceptual responsibilities already visible in the implementation,
not a claim that a portable core has been extracted or proven on another domain.
The shared policy implementation still contains explicit scenario/tool logic.

### Future extension points — conceptual only

| Concern | Attachment point and responsibility | Current boundary |
| --- | --- | --- |
| Memory | Context assembly may retrieve scoped, source-labelled memory; accepted execution events may feed persistence. Model-visible search/write tools are optional, with runtime admission. Retrieved memory cannot silently replace current authoritative observations. | Bounded in-process history; no durable memory or restart recovery added. |
| Access | Establish identity/scope at session entry; enforce authorization at admission and again before dispatch; the target service enforces its own credentials/permissions. | Synthetic role flag/local confirmation; no production identity integration. A skill or model proposal cannot grant access. |
| Observability | Runtime event boundaries around context, proposal, gate, confirmation, tool result and terminal verification can feed a trace exporter; evaluations consume recorded evidence separately. | Existing local audit trace; no new backend/exporter. Required logging does not depend on the model choosing a logging tool. |

### Evidence classes and approval meaning

| Evidence class | Available evidence | What it establishes / does not establish |
| --- | --- | --- |
| Development verification | Recorded 259 tests PASS, Ruff PASS and diff check; detailed coverage below. | Checked implementation behavior under tests; does not show a model can complete remediation. |
| Scripted/emulated trajectory verification | Materialized nominal and reject-then-repair inputs/results; 5 and 6 proposal turns respectively, both COMPLETED. | Demonstrates the assembler/control/emulator path with scripted proposals and scripted confirmations. Does not demonstrate human approval quality, model choice, or real infrastructure recovery. |
| Actual measured model evidence | **Absent: actual_model_calls=0.** | No BC-006 Qwen/Codex completion, refusal-repair, latency or cost conclusion is available. |

The [approval template](bc-006-materials/approval-template.json) is a pending
record binding a human pre-run disposition to the exact reviewed revision and
packet. It is not model input, action permission, an authenticated signature or
proof of correctness. Per-write confirmations inside a trajectory are separate.
This documentation edit grants neither pre-run approval nor write confirmation.

## Verification

Focused RED first exposed the absent admission/feedback behavior. A later semantic
RED exposed acceptance of premature readiness in a scale acknowledgement; the
application boundary now rejects that result without updating observed state.

The focused suite covers:

- nominal completion and reject-then-repair through the same runtime;
- 6/7 healthy and desired=8/healthy=6 shift refusal, with no adapter call;
- readiness delay, no logical-time advance on rejection, recovery FAIL;
- stale/foreign/unknown recovery and final verification failure;
- scope/schema faults, unknown write outcome and no retries;
- confirmation rejection/expiry, state/parameter/role changes, single consumption;
- repeated rejection, budgets, context overflow and terminal-state immutability;
- exact replay of context assembly, history/current-state separation, visibility;
- API request equality, raw evidence retention, digest/version/truncation/timeout stops;
- manual exact-text/hash binding and reuse of legacy chat adapter without default changes;
- generated BC-004 reference gate and exact revision/packet approval checks.

Scripted nominal: **5 proposal turns, 9 tools including preparation and final read,
3 writes, 0 rejections, COMPLETED**. Scripted recovery: **6 turns, 1 rejection,
9 tools, 3 writes, COMPLETED**. Actual LLM calls: **0**.

Final local verification: **259 tests PASS**, Ruff PASS, `git diff --check` PASS.
This is development verification, not experiment measurement. Verification was
performed on the BC-006 implementation worktree based on `851c79e`; the live
runner additionally requires a clean exact approved commit and records that SHA.
No remote CI or publication is claimed by this review.

## What the human still reviews before measurement

1. The task and tool preconditions are intelligible without hidden expectations.
2. Each context correctly distinguishes proposal / refusal / acceptance / observation.
3. The supplied action interface is acceptable as a new task (not a repeat of BC-005).
4. Fixed budgets/configuration and one trajectory are acceptable.

All material model expectations currently have explicit visible rule references.
The machine BC-004 gate checks those references in every generated boundary;
its PASS does not replace human assessment of sufficiency or run authorization.
The runner will not launch from the PENDING template.

## Limits and next step

- No Qwen/Codex task-completion result exists yet.
- The emulator, configured role flag and local confirmation are synthetic controls,
  not real infrastructure/authentication integration.
- Nominal readiness/recovery events are fixture-defined; no production timings.
- No automatic recovery after process interruption or ambiguous write result.
- The entire bounded history is retained; overflow stops instead of summarizing.
- No UI, model judge, prompt/seed search, or switching models within a trajectory.
- First exact packet review, then one separately authorized Qwen run. A Codex run
  remains a separate decision after Qwen's recorded outcome.
