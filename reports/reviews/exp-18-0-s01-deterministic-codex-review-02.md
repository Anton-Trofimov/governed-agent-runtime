# Exp 18.0 Deterministic S01 — Codex Review 02

## Review metadata

- Review date: 2026-07-30
- Reviewed commit: `22944c0`
- Review mode: read-only
- Approval mode: never
- Codex version: 0.141.0
- Model: GPT-5.5
- Session: `019fabfd-8da6-7d50-92b4-a30fd4d1bbd6`
- Regression result: `53 passed in 1.71s`

## Scope

Second read-only review of the deterministic Exp 18.0 S01 baseline.

The review verified the findings from the first review and performed a fresh
correctness pass over:

- runtime policy;
- lifecycle transitions;
- evidence handling;
- preparation-tool execution;
- normalized-state application;
- terminal outcomes;
- execution trace;
- unit, contract and acceptance coverage.

The review did not request:

- implementation of S02-S12;
- LLM integration;
- a bounded agent loop;
- production infrastructure execution;
- universal framework or security-certification claims.

## A. Previous findings verification

### 1. JSON Schema alias normalization — CLOSED

The shared normalization helper is recursive and non-mutating and is used by
runtime policy and preparation-tool validation.

Evidence:

- `src/governed_agent_runtime/contract_schema.py`
- `src/governed_agent_runtime/runtime_policy.py`
- `src/governed_agent_runtime/preparation_tools.py`
- `tests/unit/test_contract_schema.py`
- `tests/unit/test_runtime_policy.py`

### 2. Governed candidate action contract — CLOSED

`create_remediation_plan` constrains the candidate action type and rejects
unknown or runtime-owned fields.

Evidence:

- `specs/core/tool-contracts.yaml`
- `tests/unit/test_runtime_policy.py`

### 3. Runtime-decision transition semantics — CLOSED for implemented S01 paths

T015, T033 and T034 contain decision requirements, and transition application
validates those requirements.

Evidence:

- `specs/core/state-transition-table.yaml`
- `src/governed_agent_runtime/state_transition.py`
- `tests/unit/test_state_transition.py`

### 4. Observation-time freshness — CLOSED

Evidence freshness is based on `observed_at`. `collected_at` remains provenance
and audit metadata.

Evidence:

- `src/governed_agent_runtime/evidence_engine.py`
- `tests/unit/test_evidence_engine.py`

### 5. Terminal-outcome recording — CLOSED mechanically

Terminal transitions now record `terminal_outcome`.

A remaining semantic-specificity finding is documented below.

Evidence:

- `src/governed_agent_runtime/state_transition.py`
- `tests/unit/test_state_transition.py`

### 6. Transition-aware phase permission — CLOSED

PH001 resolves its referenced transition and verifies:

- source task state;
- decision next state;
- resulting phase.

Evidence:

- `src/governed_agent_runtime/runtime_policy.py`
- `tests/unit/test_runtime_policy.py`

### 7. Bounded tool-budget fallback — CLOSED

Tool-budget exhaustion from `HYPOTHESIS_READY` can reach the supported T034
`SAFE_FALLBACK` transition without executing another tool.

Evidence:

- `specs/core/state-transition-table.yaml`
- `specs/core/policy-spec.yaml`
- `tests/unit/test_state_transition.py`

### 8. Complete Tool Result Envelope in trace — CLOSED

`TOOL_RESULT_RECEIVED` retains a deep-copied complete Tool Result Envelope.

Evidence:

- `src/governed_agent_runtime/execution_trace.py`
- `schemas/execution-trace.schema.json`
- `tests/unit/test_execution_trace.py`

## B. Remaining or new findings

No Critical or High findings were identified.

### Medium — Some policy decisions cannot be applied from HYPOTHESIS_READY

A valid `ASK_CLARIFICATION` proposal can produce:

    HYPOTHESIS_READY -> NEEDS_CLARIFICATION

No corresponding lifecycle transition currently exists.

A valid non-budget `STOP_OR_ESCALATE` proposal can produce:

    HYPOTHESIS_READY -> SAFE_FALLBACK

T034 cannot apply this decision because it specifically requires the
`EXECUTION_BUDGET_EXCEEDED` reason code.

Violated invariant:

A policy decision must select a state-machine-supported transition with
matching decision semantics.

Missing coverage:

Current tests cover budget fallback and PH001 but not every proposal type
allowed from `HYPOTHESIS_READY / DIAGNOSE`.

Smallest fix direction:

Define explicit lifecycle transitions and semantic requirements for
clarification and non-budget safe fallback, or make policy select another
supported disposition.

### Medium — Tool Result Envelope is not revalidated at application boundary

`apply_preparation_tool_result()` checks status, tool name and selected result
fields but does not revalidate the complete envelope before mutating state.

A malformed externally supplied execution record could therefore pass selected
checks and influence normalized state.

Violated invariant:

T019 requires a schema-valid remediation-plan result, and the execution-trace
contract states that runtime uses a validated Tool Result Envelope.

Missing coverage:

Current tests validate generated tool results during deterministic generation
but do not prove that application rejects malformed envelopes.

Smallest fix direction:

Validate the Tool Result Envelope at the application boundary, or introduce a
strict typed and validated execution-record boundary.

### Medium — Terminal outcome mapping loses governed outcome specificity

Terminal state `COMPLETED` currently maps only to terminal outcome `COMPLETED`.

This does not distinguish:

- `DRAFT_CREATED`;
- `ANSWERED`;
- generic completion.

T018 describes a terminal requested draft outcome, but state-based mapping
cannot record `DRAFT_CREATED`.

Violated invariant:

Governed product outcomes are more specific than generic lifecycle terminal
states.

Missing coverage:

The current terminal test asserts `COMPLETED`, locking in the lossy behavior.

Smallest fix direction:

Resolve terminal outcome using transition ID, decision semantics or proposal
type rather than target state alone.

### Low — Invalid source timestamps are not rejected during normalization

Invalid source, event, deployment or metric timestamps can enter normalized
observations and fail later during freshness evaluation.

The normalization boundary should reject them immediately.

Missing negative coverage includes:

- source `source_timestamp`;
- event `occurred_at`;
- deployment `started_at`;
- metric-point timestamps.

### Low — Readiness blocking reasons can remain stale after reassessment

`blocking_reason_codes` may be set during an insufficient assessment and remain
present after a later sufficient assessment.

Readiness booleans and blocking reasons should be recomputed together on every
assessment application.

A reassessment test is missing.

## C. Material test coverage gaps

The review recommends tests for:

1. Policy-then-apply behavior for every proposal type permitted from
   `HYPOTHESIS_READY / DIAGNOSE`.
2. Malformed Tool Result Envelopes at the application boundary.
3. T018 terminal outcome `DRAFT_CREATED`.
4. Answer terminal outcome `ANSWERED`.
5. Invalid timestamps at source-normalization boundaries.
6. Readiness reason recomputation during reassessment.

## D. Verdict

The deterministic S01 happy path is substantially stronger, and all findings
from the first review are closed.

The baseline should not yet be frozen for extension to S02-S12.

One targeted hardening block remains:

1. Align allowed policy decisions with supported lifecycle transitions.
2. Validate tool results at the application boundary.
3. Preserve specific governed terminal outcomes.
4. Reject invalid timestamps during normalization.
5. Recompute readiness blocking reasons during reassessment.

After this block and a fresh independent review, the deterministic S01 baseline
should be a strong candidate for freeze and extension to S02-S12.
