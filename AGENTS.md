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

This repository develops and evaluates a governed runtime for bounded agent
behavior in a synthetic payment-api incident-response environment.

The current baselines are the deterministic Exp 18.0 S01 vertical and the
frozen Exp 18.1A single-step Qwen proposal evaluation for a synthetic
payment-api incident environment.

An LLM may interpret controlled context and produce bounded proposals. The LLM
is not the control plane.

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

## Progressive context loading

Load the minimum authoritative context needed for the bounded concern. A fresh
session should normally follow:

    AGENTS.md
    -> current Git state and accepted baseline
    -> bounded concern
    -> specs/README.md concern router
    -> applicable authoritative specifications
    -> affected formal contracts
    -> affected implementation
    -> relevant tests or evaluations
    -> verification
    -> evidence and decision handoff when applicable

Formal contracts include JSON Schemas, state-transition tables, tool and
source-adapter contracts, proposal and runtime-decision interfaces, and other
machine-readable or formal behavioral boundaries.

Do not load the whole repository by default. Do not require the external
reusable SDD Operating Model for routine project work.

## Human intent authority

Human intent is authoritative. A narrow task is not permission to broaden,
weaken or replace product intent, requirements, acceptance criteria, policy,
architecture or shared contracts.

When a narrow task conflicts with higher-level authority:

    detect conflict
    -> stop the affected path
    -> surface the conflict
    -> human decides
    -> update the durable authoritative artifact if intent changes
    -> continue only after that update

Passing tests does not demonstrate preservation of intent when requirements,
contracts or tests were weakened or redefined at the same time.

## Bounded-change workflow

Use this sequence for material changes:

1. identify the bounded concern and applicable authority;
2. update the normative specification when behavior or intent changes;
3. add a focused failing test when an executable contract is required;
4. implement the smallest justified change;
5. run targeted and required regression checks;
6. record evidence, review or decision results when applicable;
7. obtain an explicit human disposition before starting the next meaningful
   bounded change;
8. update the current handoff when the baseline materially changes.

A RED test must fail for the intended contract violation, not because of an
unrelated import, fixture, signature or syntax error.

A freeze or tag is optional. Create one only when a human intentionally selects
a durable reference baseline.

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

The deterministic Exp 18.0 proof remains S01-specific. Exp 18.1A is a frozen
single-step evaluation boundary, not a bounded agent loop.

Do not prematurely generalize the S01 evidence engine or scenario logic before
the S02-S12 scenario matrix requires it.

Do not introduce:

- retrospective changes to the frozen Exp 18.1A evidence or adjudication to
  match later experiments;
- uncontrolled tool execution, autonomous looping or model-authorized state
  mutation;
- a bounded agent loop without a separately specified and verified change;
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

Required verification gates are blocking. A failed required check stops the
dependent next step until the failure is resolved or the gate is intentionally
changed through its proper authority and review path. Use fail-fast command
sequencing for dependent checks where appropriate; no single shell syntax is
required for every environment.

## Evaluation evidence

Decision-relevant measured evidence must identify the evaluated Git revision
and material execution, model and runtime configuration where applicable.
Development output, calibration smokes and ad hoc runs are not accepted
evidence automatically.

Accepted or promoted decision-relevant evidence must not be changed merely to
satisfy formatting, lint or style preferences. Evidence integrity and
provenance take precedence over cosmetic cleanup. Ordinary mutable
documentation remains subject to normal formatting and quality rules.

For decision-relevant AI evaluations, preserve or expose human-inspectable
representative model-visible inputs and relevant outputs or traces. Include
anomalous, failing or high-risk outputs where applicable. Exhaustive manual
inspection of every run is not required unless the active evaluation contract
requires it.

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

## Methodology boundary

The reusable SDD Operating Model is not a runtime dependency or mandatory
context for routine coding sessions. This file, the specification router, the
applicable project-local specifications and contracts, relevant tests or
evaluations, and the active bounded task should provide the minimum correct
working context.
