# BC-005-D1 — Prospective pre-run review

Status: READY FOR EXACT-REVISION HUMAN PRE-RUN CHECKPOINT; zero real D1 calls.
The source revision is the implementation commit containing this document, as shown
by Git history and the draft PR. No self-referential commit hash is embedded.

## Closed comparator

BC-005 is merged through PR #3 at bc91ed5df96b3952cc7a2ee4e2f0f928eeb5e4e2.
Its evaluated revision remains f033f04820e1d044c72da0d2682cc62e99b73936; disposition
NOT SUPPORTED, semantic 0/3, runtime containment 3/3. Its evidence is immutable.

## Exact treatment delta

The new field is appended as the last top-level field of the existing JSON envelope.
No old field is changed. The context, schema, available tools ([]), operational
rules, evidence, hidden evaluator and traceability are reused unchanged.

```json
{
  "final_review_instruction": "Before returning your final proposal, review the entire plan against all supplied facts, constraints, and dependencies. Verify that each action's preconditions are satisfied when that action would be performed and that the action order does not violate any constraint. Do not treat a planned action as already completed or its outcome as confirmed. Correct any contradictions before answering."
}
```

This is one internal self-review instruction before the submitted final, not an
additional LLM call or a response to the previous failed answer. The instruction
contains no specific replica count or correct remediation sequence.

Baseline full input is inspectable in the canonical BC-005 RAW evidence and prior
pre-run packet. The D1 full input is reproducible without inference:

```python
from pathlib import Path
from governed_agent_runtime.bc005_d1_self_review import assemble_diagnostic_input
print(assemble_diagnostic_input(Path.cwd()))
```

Baseline input SHA-256: `d4b67d3f282281f6fb4a3789b0adfea8b677bc04ab5d00712982e015e47f3e38`.
Diagnostic input SHA-256: `c034ecab199767da49fd71e0609c0bdabc76c73cc3956c3b4f5d8604e06114b7`.

## Frozen settings and checks

Same qwen3.8:27b digest and Ollama 0.32.14; unchanged /api/chat parameters, seed,
context/generation budgets, 300s timeout and proposal format from the baseline
manifest. The runner checks baseline artifact hashes/input hash, traceability,
clean exact approved HEAD and full verification before provider construction.
Provider version and model digest must match before preload. One excluded preload,
then exactly three measured calls; no tools or normalized-state mutation.

## Evaluation and stop

Same six semantic criteria and automatic output checks as BC-005. Human evaluates
submitted finals; no judge model. Inspect budget/integration before counting quality.
Report D1 separately against the fixed BC-005 comparator. Never replace BC-005 results.
3/3 PASS supports this instruction on this fixture/configuration; 2/3 is mixed;
0–1/3 does not support reliable correction in this pool. No general reliability
or isolated causal effect is claimed (added text also changes length/position).
Stop after this pool; no iterative prompt edits.

## Evidence and execution handoff

Station root: `/home/anton/projects/evidence/governed-agent-runtime/bc-005-d1/`;
create one new timestamped child per pool, never overwrite existing evidence.
Every record has experiment_id=BC-005-D1, DIAGNOSTIC scope and
 decision_evidence_eligible=false. The shared bounded_change_id=BC-005 exists only
for frozen offline-evaluator compatibility. RAW precedes evaluation. Manifest
records actual observed attempts and failure if evaluation aborts; no auto retry.

Call `run_diagnostic(root, evidence_directory=..., approved_revision=<exact SHA>,
human_pre_run_approved=True)` only after the exact published revision is approved.
The user authorized preparation of this diagnostic; this packet does not assert
that an as-yet-unidentified run revision has received pre-run approval.

## Verification coverage

Focused tests: unchanged baseline after removing the new field; last-field placement;
1+3 fixed calls with identical input; diagnostic scope and frozen offline evaluator
compatibility; approval/revision and baseline-drift gates; RAW persistence before
injected runtime failure. Stub providers only. Full repository regression is a
blocking publication/pre-run gate, with its exact result recorded in the PR/CI.
