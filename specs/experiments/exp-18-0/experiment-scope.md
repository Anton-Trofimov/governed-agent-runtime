# Scope

- Spec version: 0.1.0
- Status: draft
- Specification family: governed-runtime-core

## Objective

Build and validate the deterministic specification baseline for a governed
agent/tool runtime before connecting an LLM or orchestration framework.

## In scope

### Synthetic product environment

- one logical service: `payment-api`;
- `production` and `staging` environments;
- deployment targets and version groups;
- provider adapter;
- payment database;
- payment events queue;
- selected downstream consumers;
- ownership and capacity metadata;
- operational runbooks.

### Operational sources

- service status;
- time-series metrics;
- deployment history;
- runtime events;
- dependency state;
- traffic breakdown;
- incident drafts;
- approvals;
- trace and evaluation records.

### Governed runtime

- agent charter;
- context assembly;
- normalized state;
- evidence state;
- diagnostic assessment;
- action readiness;
- tool capability contracts;
- runtime policy gates;
- action preconditions;
- confirmation binding and invalidation;
- task-state transitions;
- fallback and escalation;
- audit trace.

### Tools

Read-only tools:

- service status;
- service metrics;
- runtime events;
- dependency status;
- traffic breakdown;
- runbook search.

Preparation tools:

- incident draft;
- notification draft;
- remediation plan.

Mock state-changing tools:

- notification sending;
- single-replica restart;
- deployment rollback.

### Baseline scenarios

S01-S12 cover:

- partial rollout regression;
- provider degradation;
- retry amplification;
- downstream failure;
- replica or infrastructure instability;
- payment database degradation;
- no-tool answer;
- clarification;
- incident draft;
- confirmation-bound notification;
- controlled restart;
- validated rollback.

### Product evaluation

The experiment must include:

- one short end-to-end demonstration;
- fixed workflow versus bounded agent comparison;
- time-to-outcome measurement;
- tool-call and unnecessary-call accounting;
- policy-containment measurement;
- latency, token and cost accounting;
- product decision by scenario class.

## Out of scope for Exp 18.0

- LLM integration;
- LangChain or LangGraph;
- Langfuse;
- PostgreSQL implementation;
- vector storage;
- real monitoring and infrastructure APIs;
- real restart, rollback or notification;
- multi-agent orchestration;
- long-term memory;
- arbitrary shell, SQL or code execution;
- packet-level network diagnosis;
- automatic scaling execution;
- n8n workflows;
- full security benchmarking;
- production deployment and load testing.

## Required deliverables

- approved specification baseline;
- canonical identifiers and state dictionary;
- tool and policy contracts;
- formal schemas;
- deterministic source fixtures;
- hidden evaluation truth;
- contract and acceptance tests;
- deterministic runtime;
- complete execution traces;
- end-to-end demo;
- fixed-workflow comparison;
- Exp 18.0 result and decision report.

## Ready-for-implementation gate

Implementation begins only after:

- domain entities and relationships are consistent;
- proposal and runtime-decision taxonomies are defined;
- mandatory action preconditions are explicit;
- S01-S12 expectations are recorded;
- model-visible and hidden data are separated;
- schemas and source contracts are agreed;
- product metrics and comparison method are fixed.

## Change control

A behavioral change requires:

1. specification update;
2. acceptance-case update;
3. ADR when the architectural decision is meaningful;
4. implementation change;
5. reproducible test result.

Implementation must not silently diverge from the approved specification.
