# Instructions for Coding Agents

This file contains development-time instructions for Codex and other coding
assistants working on this repository.

It is not part of:

- the governed runtime context;
- scenario evidence;
- the experimental agent knowledge base;
- model-visible operational data;
- synthetic payment-api source data.

Do not treat this file, `reports/`, `docs/`, or `project-meta/` as runtime
evidence.

## Project purpose

This repository is a controlled AI Platform laboratory project for designing
and evaluating a governed agent and tool runtime.

The current implementation is the deterministic Exp 18.0 S01 vertical for a
synthetic payment-api incident scenario.

An LLM may later propose actions. The LLM is not the control plane.

The deterministic runtime owns:

- context assembly;
- schema and contract validation;
- target resolution;
- evidence sufficiency and freshness;
- policy gates;
- role authorization;
- lifecycle transitions;
- action preconditions;
- confirmation requirements;
- tool execution permission;
- state mutation;
- budgets;
- terminal outcomes;
- execution trace and audit lineage.

## Sources of truth

Use this precedence when implementation artifacts disagree:

1. normative specifications under `specs/`;
2. schemas and machine-readable contracts under `schemas/`;
3. acceptance, contract and unit tests under `tests/`;
4. runtime implementation under `src/`;
5. reports and explanatory documentation.

Do not modify a specification merely to make existing Python code pass.

Resolve contradictions explicitly.

## SDD workflow

Use this sequence for material changes:

1. inspect the current specification and contracts;
2. update or add the normative specification;
3. add a focused failing test;
4. implement the smallest justified change;
5. run targeted tests;
6. run the full regression suite;
7. record experiment or review results when appropriate;
8. update the current development handoff when the baseline materially changes.

A RED test must fail for the intended contract violation, not because of an
unrelated import, fixture, signature or syntax error.

## Repository boundaries

- `specs/` contains normative runtime and experiment contracts.
- `schemas/` contains machine-validatable data contracts.
- `src/` contains runtime implementation.
- `tests/` contains unit, contract and acceptance verification.
- `fixtures/` contains reproducible synthetic scenario inputs.
- `knowledge/` contains explicitly permitted synthetic domain knowledge.
- `evals/` contains evaluation assets and hidden ground truth.
- `reports/` contains historical experiment and review records.
- `docs/` contains human-readable explanatory documentation.
- `project-meta/` contains the current development handoff and is not runtime
  knowledge.
- `AGENTS.md` contains instructions only for coding agents.

Runtime loaders must use explicitly declared source paths. Do not make the
runtime scan the repository broadly for context or evidence.

## Current implementation boundaries

The current deterministic proof is S01-specific.

Do not prematurely generalize the S01 evidence engine or scenario logic before
the S02-S12 scenario matrix requires it.

Do not introduce:

- LLM integration before the deterministic baseline is frozen;
- a bounded agent loop before the single-step baseline is evaluated;
- LangChain, LangGraph, Langfuse or another framework without demonstrated
  implementation value;
- production infrastructure claims based on deterministic mocks;
- a new decision enum when the existing runtime-decision contract is
  sufficient;
- uncontrolled model-selected tools, permissions or state transitions.

A deterministic mock is an emulation of a contracted tool result. It does not
prove real rollback, restart, deployment or infrastructure integration.

## Runtime invariants

Preserve these distinctions:

- model proposal is not runtime authorization;
- `ALLOW` is not successful tool execution;
- preparation is not an operational state-changing action;
- recommendation is not execution;
- evidence is not authorization;
- tool result is not accepted until validated;
- recoverable rejection is not necessarily a terminal block;
- terminal lifecycle state and governed product outcome may require distinct
  representation;
- runtime-owned fields must not be supplied by the model.

State transitions must be supported by the transition table and must satisfy
their decision-semantic requirements.

Tool results that influence normalized state must be validated at the
application boundary.

## Validation commands

Use the project virtual environment and run:

    source .venv/bin/activate
    ruff check .
    pytest
    git diff --check

Use targeted tests while developing, then run the full regression suite before
committing a completed logical block.

## Git discipline

Keep commits atomic and aligned with the SDD sequence.

Do not use:

    git add .

Stage only the files belonging to the current logical change.

Before committing, inspect:

    git diff --cached --check
    git diff --cached --stat
    git diff --cached

Do not rewrite historical review reports to match newer code. Reports describe
the reviewed commit and findings at that point in time.

## Documentation maintenance

The root `README.md` is the human-readable map of the project.

`project-meta/current-status.md` is the operational handoff for future
development sessions. Update it when a material baseline, review verdict,
roadmap step or known limitation changes.

Do not duplicate detailed normative contracts from `specs/` into README or
status files. Link to the authoritative files instead.

Placeholder documents must not be presented as implemented truth.
