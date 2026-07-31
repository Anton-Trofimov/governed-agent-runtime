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
- Current commit at creation: `f8dbc73`
- Experiment: Exp 18.0
- Baseline: deterministic S01 vertical
- Regression result: `64 passed`
- Static analysis result: `ruff check .` passed
- Latest completed review:
  `reports/reviews/exp-18-0-s01-deterministic-codex-review-02.md`
- Findings from that review: closed
- Fresh independent review: pending
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

The second read-only Codex review found no Critical or High findings.

All findings from the first review were verified as closed.

The targeted hardening cycle requested by the second review is complete.

Closed findings include:

1. policy decisions from `HYPOTHESIS_READY` now have applicable lifecycle
   transitions for clarification and bounded safe stop;
2. Tool Result Envelopes are revalidated at the state-application boundary;
3. terminal transitions preserve specific governed outcomes such as
   `ANSWERED` and `DRAFT_CREATED`;
4. invalid or timezone-naive normalized timestamps are rejected by source
   adapters;
5. evidence-owned readiness blockers are recomputed rather than accumulated
   across reassessments.

No known finding from the second review remains open.

This statement records closure against that review only. A fresh independent
review has not yet been completed.

## Quality gate

At this checkpoint:

- `ruff check .` passes;
- `pytest -q` passes with `64 passed`;
- the working tree was clean before this checkpoint update.

## Next development block

Perform a fresh independent read-only Codex review in a new session.

The review should:

1. inspect the current repository rather than rely only on historical reports;
2. verify closure of the second-review findings;
3. search for new correctness, contract, lifecycle and test-coverage issues;
4. distinguish real runtime risks from speculative framework expansion;
5. avoid requiring production infrastructure claims outside Exp 18.0 scope.

After the review:

- fix only material findings with targeted spec, RED test and implementation
  changes;
- rerun the complete quality gate;
- freeze the deterministic S01 baseline only if no material findings remain;
- do not begin S02-S12 implementation before the freeze decision.

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
