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
- Reviewed baseline commit: `de02251`
- Experiment: Exp 18.0
- Baseline: deterministic S01 vertical
- Regression result: `64 passed`
- Static analysis result: `ruff check .` passed
- Latest completed review:
  `reports/reviews/exp-18-0-s01-deterministic-codex-review-03.md`
- Review findings: one High and one Medium open
- Fresh independent review: completed
- Freeze status: blocked by review-03 findings

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

The fresh independent read-only Codex review inspected the current repository
at the reviewed baseline commit.

It verified closure of:

- clarification and bounded safe-stop transitions;
- transition-specific terminal outcomes;
- evidence blocker recomputation.

It identified two material findings:

1. High: malformed metric-point timestamps can enter normalized observations
   and affect latest-metric selection and the S01 diagnosis.
2. Medium: Tool Result Envelope timestamps are not explicitly validated as
   timezone-aware values at the state-application boundary.

The deterministic S01 baseline is not ready to freeze until both findings are
closed.

## Quality gate

At this checkpoint:

- `ruff check .` passes;
- `pytest -q` passes with `64 passed`;
- the working tree was clean before this checkpoint update.

## Next development block

Close the review-03 findings in this order:

1. validate decision-relevant metric-point timestamps during source
   normalization and parse timestamps for latest-point selection;
2. explicitly validate Tool Result Envelope timestamps before state
   application;
3. run `ruff check .` and the full regression suite;
4. update this checkpoint;
5. perform a fresh read-only verification before freezing S01.

Do not begin S02-S12 implementation before the freeze decision.

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
