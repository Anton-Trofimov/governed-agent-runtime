# Governed Agent Runtime

Controlled AI Platform laboratory project for designing and evaluating a
governed runtime for bounded agent behavior.

The project uses a synthetic payment-api incident-response environment to
explore how an AI system can investigate operational problems, prepare
artifacts and propose next steps while deterministic platform logic retains
control over permissions, evidence, lifecycle transitions, tool execution and
auditability.

## Core principle

An LLM may propose a next step. The LLM is not the control plane.

The runtime remains responsible for:

- assembling permitted context;
- validating schemas and contracts;
- resolving targets;
- checking evidence sufficiency and freshness;
- applying policy gates;
- enforcing role permissions;
- checking technical preconditions;
- requesting confirmation when required;
- controlling tool execution;
- validating lifecycle transitions;
- applying state changes;
- enforcing budgets;
- recording terminal outcomes;
- preserving execution trace and audit lineage.

A model proposal is not authorization. An `ALLOW` decision is not proof of
successful execution. A preparation tool is not an operational action.

## Experimental scenario

The experimental user is an on-call or operations specialist investigating
incidents around a synthetic `payment-api` service.

The initial S01 scenario represents a regression during a partial rollout. The
available evidence localizes elevated 5xx errors to one deployed version while
also showing that an immediate full rollback may be unsafe because of capacity
and unresolved preconditions.

The deterministic S01 vertical demonstrates how the runtime can:

1. normalize source observations;
2. assess evidence;
3. establish a bounded diagnostic hypothesis;
4. evaluate a model-shaped proposal through policy gates;
5. enter a preparation phase through a validated lifecycle transition;
6. invoke a deterministic preparation-tool mock;
7. produce a versioned remediation-plan artifact;
8. apply the validated tool result to normalized state;
9. retain the complete decision and artifact lineage in execution trace.

The current vertical prepares an action candidate. It does not execute a real
rollback, restart, deployment or other production action.

## Current implementation stage

Development is currently centered on the deterministic Exp 18.0 baseline.

The implemented S01 path is:

    synthetic source observations
    -> normalized state
    -> evidence assessment
    -> HYPOTHESIS_READY / DIAGNOSE
    -> model-shaped proposal
    -> deterministic runtime decision
    -> PREPARING / PREPARE
    -> create_remediation_plan mock
    -> validated Tool Result Envelope
    -> ACTION_CANDIDATE / PREPARE
    -> governed remediation-plan result and execution trace

The detailed current checkpoint, open findings, latest review and next
development block are maintained in:

    project-meta/current-status.md

That file is a milestone handoff rather than a live log. It may not include
small changes made inside an unfinished work block. Before relying on it,
inspect the current Git state, recent commits, tests and normative
specifications.

The root README is intentionally more stable. It will be revised again when a
major Exp 18 stage is completed and the implemented scope or project-level
conclusions materially change.

## Repository map

The repository is organized by responsibility rather than by experiment diary.

    governed-agent-runtime/
    |
    |-- README.md
    |   Human-readable entry point and high-level project map.
    |
    |-- AGENTS.md
    |   Development instructions for Codex and other coding agents.
    |   It is not runtime context or scenario evidence.
    |
    |-- project-meta/
    |   Current development handoff and milestone status.
    |   It is not part of the experimental knowledge base.
    |
    |-- specs/
    |   Normative design contracts describing how the governed runtime
    |   should behave.
    |   `core/` contains runtime contracts.
    |   `experiments/` contains experiment-specific scope, plans and
    |   acceptance cases.
    |
    |-- schemas/
    |   Machine-validatable contracts for proposals, decisions, normalized
    |   state, confirmations, tool results and execution traces.
    |
    |-- src/
    |   Python implementation of the deterministic runtime baseline:
    |   source adapters, evidence assessment, policy gates, state
    |   transitions, preparation tools, trace construction and scenario
    |   orchestration.
    |
    |-- fixtures/scenarios/
    |   Reproducible synthetic user requests and raw scenario-specific
    |   source responses.
    |
    |-- knowledge/
    |   Controlled synthetic domain knowledge such as service topology,
    |   ownership, capacity profiles and runbooks.
    |   Files are usable only through explicitly declared runtime paths and
    |   contracts.
    |
    |-- evals/
    |   Evaluation assets and hidden ground truth that must remain separate
    |   from model-visible and runtime-visible scenario inputs.
    |
    |-- tests/
    |   Unit, contract and acceptance verification of runtime behavior and
    |   scenario contracts.
    |
    |-- reports/
    |   Historical experiment and review records tied to particular
    |   checkpoints. Reports may describe older repository states.
    |
    |-- docs/
    |   Human-readable product, architecture, environment, operations and
    |   limitations documentation. Some documents remain placeholders until
    |   the corresponding implementation stage is mature.
    |
    |-- scripts/
        Supporting development and experiment commands.

## Context and evidence boundaries

Repository location does not automatically make information available to the
experimental agent.

Potential runtime inputs are limited to explicitly declared scenario sources
and permitted knowledge paths. Source adapters, tool contracts and
context-assembly rules determine what becomes:

- model-visible context;
- runtime-only state;
- audit-only data;
- evaluator-only hidden ground truth.

The runtime must not broadly scan the repository for context.

The following development materials are not runtime evidence:

- `AGENTS.md`;
- `project-meta/`;
- `reports/`;
- `docs/`;
- the root `README.md`;
- Git history and development notes.

Files under `knowledge/` are also not automatically model-visible merely
because they exist. Access must be explicitly provided through the experimental
contracts.

## Sources of truth

When project artifacts disagree, use this precedence:

1. normative specifications under `specs/`;
2. machine-readable schemas under `schemas/`;
3. acceptance, contract and unit tests under `tests/`;
4. runtime implementation under `src/`;
5. historical reports and explanatory documentation.

A specification should not be rewritten merely to match existing Python code.
Contradictions must be resolved explicitly.

## Local setup

Create a virtual environment, install the project and run the regression suite:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"
    pytest

Run the deterministic S01 acceptance path:

    pytest tests/acceptance/test_s01_preparation_path.py -q

Standard repository checks:

    ruff check .
    pytest
    git diff --check

## Development method

The project follows a specification-driven sequence:

    normative specification
    -> schemas and contracts
    -> focused failing test
    -> smallest justified implementation
    -> targeted verification
    -> full regression
    -> experiment or review result
    -> decision and milestone handoff

Material changes are kept in atomic commits. Historical review reports are not
rewritten to match later code.

## Current limitations

This repository is a controlled laboratory proof, not a production runtime.

Current limitations include:

- the implemented evidence engine and deterministic path are S01-specific;
- deterministic tool mocks do not prove real infrastructure integration;
- no production rollback, restart or deployment is performed;
- LLM integration is intentionally deferred until the deterministic baseline
  is frozen;
- the bounded governed loop has not yet been implemented;
- S02-S12 are not yet implemented as deterministic runtime paths;
- security and safety controls are supporting design dimensions, not a claim
  of certification;
- no universal agent-framework or production-readiness claim is made.

For the latest verified baseline and remaining hardening work, read
`project-meta/current-status.md`.
