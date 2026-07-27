# Governed Agent Runtime

Controlled AI Platform laboratory project for designing and evaluating a governed agent and tool runtime.

## Current stage

Exp 18.0 — specification and deterministic runtime baseline.

The project starts with:

- a synthetic payment-api operating environment;
- explicit state and evidence models;
- tool capability contracts;
- runtime policy gates;
- action preconditions;
- deterministic fixtures;
- acceptance tests before LLM integration.

An LLM may propose the next step. The runtime remains responsible for validation, permissions, confirmation, execution control and audit.

## Status

Initial repository structure.

Specifications and scenario data are drafts. No production-readiness claim is made.

## Local setup

Create and activate a virtual environment, install the project and run tests:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"
    pytest
