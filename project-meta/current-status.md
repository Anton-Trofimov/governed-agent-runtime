# Current Development Status

## Purpose

This file is the operational handoff for future development sessions and
coding agents.

It is not part of:

- runtime context;
- scenario evidence;
- the experimental agent knowledge base;
- model-visible operational data;
- synthetic payment-api source data.

Historical reviews remain under `reports/`. Normative requirements remain under
`specs/`.

## Current checkpoint

- Date: 2026-07-30
- Current commit at creation: `83a28b3`
- Experiment: Exp 18.0
- Baseline: deterministic S01 vertical
- Regression result: `53 passed`
- Latest review:
  `reports/reviews/exp-18-0-s01-deterministic-codex-review-02.md`
- Freeze status: not yet frozen for S02-S12 extension

## Project objective

Build and evaluate a bounded governed runtime for a synthetic payment-api
incident-response scenario.

The LLM may later propose a next step. The LLM is not the control plane.

The runtime owns:

- context and evidence handling;
- schema and contract validation;
- target resolution;
- policy gates;
- permissions and role checks;
- lifecycle transitions;
- technical preconditions;
- confirmation;
- tool execution control;
- budgets;
- state mutation;
- terminal outcomes;
- trace and audit lineage.

## Implemented deterministic S01 path

The currently validated path is:

    deterministic source observations
    -> normalized state
    -> S01 evidence assessment
    -> HYPOTHESIS_READY / DIAGNOSE
    -> model-shaped CREATE_DRAFT proposal
    -> deterministic runtime policy decision
    -> T015
    -> PREPARING / PREPARE
    -> deterministic create_remediation_plan mock
    -> validated Tool Result Envelope
    -> T019
    -> ACTION_CANDIDATE / PREPARE
    -> governed outcome DRAFT_CREATED

The resulting operational action remains not ready for execution.

No production action is executed.

## Confirmed implementation properties

The current baseline includes:

- recursive and non-mutating JSON Schema alias normalization;
- closed candidate-action input contracts;
- runtime-decision semantic checks on implemented transitions;
- evidence freshness based on `observed_at`;
- terminal-outcome recording on terminal transitions;
- transition-aware phase permission bound to real lifecycle transitions;
- bounded tool-budget fallback from `HYPOTHESIS_READY`;
- deterministic preparation-tool execution;
- complete Tool Result Envelope retention in execution trace;
- immutable trace copying for recorded tool results;
- unit, contract and acceptance coverage for the S01 vertical.

## Review status

The second read-only Codex review found no Critical or High findings.

All findings from the first review were verified as closed.

The second review identified three Medium and two Low findings.

### Remaining Medium findings

1. Some policy decisions allowed from `HYPOTHESIS_READY` cannot yet be applied
   by the lifecycle state machine:
   - `ASK_CLARIFICATION -> NEEDS_CLARIFICATION`;
   - non-budget `STOP_OR_ESCALATE -> SAFE_FALLBACK`.

2. `apply_preparation_tool_result()` does not yet revalidate the complete Tool
   Result Envelope at the state-application boundary.

3. Generic state-based terminal-outcome mapping cannot distinguish:
   - `DRAFT_CREATED`;
   - `ANSWERED`;
   - generic `COMPLETED`.

### Remaining Low findings

1. Invalid source timestamps are not rejected immediately during source
   normalization.

2. `blocking_reason_codes` may remain stale after evidence reassessment.

## Next development block

Complete one final targeted S01 hardening cycle in this order:

1. align allowed policy decisions with supported lifecycle transitions;
2. validate Tool Result Envelopes at the application boundary;
3. preserve specific governed terminal outcomes;
4. reject invalid timestamps during normalization;
5. recompute readiness blocking reasons during reassessment;
6. run the full regression suite;
7. perform a fresh independent Codex review in a new session;
8. freeze the deterministic S01 baseline only if no material findings remain.

Do not start S02-S12 implementation before this block is complete.

## Sources of truth

Use the following precedence:

1. `specs/` — normative runtime and experiment requirements;
2. `schemas/` — machine-validatable contracts;
3. `tests/` — acceptance, contract and unit verification;
4. `src/` — implementation;
5. `reports/` — historical findings and experiment results;
6. `docs/` — human-readable explanatory material.

When Python and a normative specification conflict, resolve the contradiction
explicitly. Do not silently rewrite the specification to fit existing code.

## Repository-context boundaries

The following are development-time materials and must not be treated as
runtime evidence:

- `AGENTS.md`;
- `project-meta/`;
- `reports/`;
- `docs/`;
- root `README.md`.

Potential runtime inputs are limited to explicitly declared paths under:

- `fixtures/`;
- `knowledge/`;
- scenario-specific source mappings and contracts.

Runtime loaders must not broadly scan the repository for context.

## Maintenance rule

Update this file when any of the following materially changes:

- deterministic baseline or validated lifecycle path;
- regression result;
- review verdict;
- open findings;
- experiment stage;
- next implementation block;
- freeze decision.

Do not rewrite historical review reports when updating this handoff.
