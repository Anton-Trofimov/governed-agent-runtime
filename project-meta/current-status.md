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

## Freshness and update cadence

This file is a milestone checkpoint, not a live development ledger.

It is updated after material stages, such as:

- completion of a hardening or implementation block;
- a new review verdict;
- a baseline freeze or unfreeze decision;
- transition to a new experiment stage;
- a material change in open findings or next steps.

It may not include:

- uncommitted work;
- intermediate RED tests;
- small fixes made inside the current block;
- final adjustments that have not yet reached a milestone checkpoint.

Before relying on this file, coding agents should also inspect:

- `git status`;
- recent Git history;
- the latest normative specifications;
- the current regression result;
- the latest relevant review report.

When this file conflicts with normative specifications, schemas, tests or the
current repository state, those sources take precedence.

## Current checkpoint

- Date: 2026-07-31
- Current checkpoint source commit: `e4d047a`
- Experiment: Exp 18
- Frozen baseline: deterministic S01 vertical
- Active design stage: Exp 18.1A single-step LLM proposal probe
- Regression result: `68 passed`
- Static analysis result: `ruff check .` passed
- Latest completed verification:
  `reports/reviews/exp-18-0-s01-deterministic-codex-verification-04.md`
- Open Critical, High or Medium findings: none
- S01 freeze status: frozen
- Exp 18.1A status: specification drafted, implementation not started
- Deterministic S02-S12 extension: not started

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
    -> source-boundary validation
    -> normalized state
    -> S01 evidence assessment
    -> HYPOTHESIS_READY / DIAGNOSE
    -> model-shaped CREATE_DRAFT proposal
    -> deterministic runtime policy decision
    -> T015
    -> PREPARING / PREPARE
    -> deterministic create_remediation_plan mock
    -> validated Tool Result Envelope
    -> application-boundary revalidation
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
- semantic transition selection when multiple transitions share states;
- explicit clarification and bounded safe-stop lifecycle paths;
- evidence freshness based on `observed_at`;
- timezone-aware normalized timestamp validation;
- rejection of invalid timestamps before normalized observations are returned;
- evidence-owned blocker recomputation during reassessment;
- preservation of blockers owned by other runtime layers;
- transition-specific governed terminal outcomes;
- generic terminal-outcome fallback for unspecialized terminal transitions;
- transition-aware phase permission bound to real lifecycle transitions;
- bounded tool-budget fallback from `HYPOTHESIS_READY`;
- deterministic preparation-tool execution;
- complete Tool Result Envelope validation before execution output is returned;
- complete Tool Result Envelope revalidation before state application;
- complete Tool Result Envelope retention in execution trace;
- immutable trace copying for recorded tool results;
- unit, contract and acceptance coverage for the S01 vertical.

## Review status

The deterministic S01 baseline remains frozen after an independent closure
verification found no Critical, High or Medium correctness findings.

All known findings from reviews 01, 02 and 03 are closed.

The next-stage sequence has been refined:

1. inspect the S02-S12 matrix as an evaluation set;
2. run a limited single-step LLM proposal probe on representative cases;
3. use the probe results to inform deterministic S02-S12 extension;
4. keep broader LLM integration and the bounded agent loop deferred.

The probe does not unfreeze S01 and does not weaken deterministic runtime
control.

## Quality gate

At the current checkpoint:

- `ruff check .` passes;
- `pytest -q` passes with `68 passed`;
- the deterministic S01 baseline remains protected by the freeze tag
  `exp-18-0-s01-deterministic-freeze`.

## Next development block

Prepare Exp 18.1A without starting an autonomous agent loop.

The next block should:

1. define the model-visible context-package contract;
2. keep scenario identifiers and expected outcomes inside the hidden evaluation
   harness;
3. create representative fixtures for S02, S07, S08A, S08B and S12;
4. distinguish normalized intake from raw-request interpretation;
5. verify that resolved and unresolved fields are explicit;
6. verify that the model sees only allowed tools, constraints and proposal
   types;
7. add tests proving that scenario IDs and acceptance expectations are not
   exposed to the model;
8. implement one LLM call that returns exactly one proposal;
9. execute no preparation or operational tools during the probe;
10. start no autonomous loop and perform no model-authorized state mutation.

After the probe, compare model proposal quality and deterministic runtime
containment separately.

Broader LLM integration remains deferred until the deterministic S02-S12
baseline is implemented and reviewed.

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
