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

## Context and control boundaries

| Boundary | Current facts at next inference | What is not asserted |
| --- | --- | --- |
| Initial | 6 healthy; 615 RPS stable / 205 candidate; total 820; PAUSED/FAILED; quota 8 | A next action is not prescribed |
| Early shift refused | Exact proposal, capacity failure, execution=false; traffic unchanged | No write occurred |
| Scale accepted | desired=8, healthy=6, pending operation | No readiness or N−1 PASS |
| Status observation | healthy=8; calculated N−1 utilization 78.1%, PASS | No traffic shift yet |
| Shift applied | 820 RPS stable; shift ID; recovery PENDING | No recovery PASS yet |
| Recovery observation | PASS with matching shift/scope/time | Candidate not yet removed |
| Finalize + runtime verification | candidate=0, ROLLED_BACK; status verifies terminal conditions | A model statement cannot complete the task |

A scale acknowledgement that claims immediate readiness fails result validation.
The controller advances by contracted logical ticks; reads observe scheduled
changes rather than deciding to heal the environment. The alternate delayed-ready
and recovery-FAIL controls demonstrate this separation.

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
