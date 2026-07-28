# Context Assembly Specification

- Spec version: 0.1.0
- Status: draft
- Specification family: governed-runtime-core

## Purpose

Define how the runtime prepares a controlled, step-specific context package for
the proposal producer.

The model does not read repository files, databases or complete execution traces
directly.

## Core principle

The context package must contain enough information for one useful next-step
proposal without exposing unnecessary, hidden or obsolete data.

Context assembly is deterministic runtime logic.

## Context sources

Potential sources include:

- agent charter;
- current user request;
- session and workflow state;
- service catalog;
- service topology;
- ownership information;
- capacity profiles;
- normalized operational state;
- evidence state;
- current hypotheses;
- applicable runbooks;
- allowed tool summaries;
- relevant policy constraints;
- prepared artifact summaries;
- confirmation status.

Not every source is included at every step.

## Visibility classes

### Model-visible

May be included in the context package:

- relevant service and environment information;
- current operational observations;
- evidence summaries;
- active hypotheses and uncertainty;
- relevant runbook excerpts;
- available tool capability summaries;
- applicable action constraints;
- compact session history.

### Runtime-only

Must not be exposed in full:

- complete policy implementation;
- internal authorization logic;
- raw tool outputs;
- full confirmation records;
- execution budgets and internal counters;
- policy-gate implementation details;
- internal state hashes.

The model may receive a relevant summary when needed.

### Evaluation-only

Must never enter the model or runtime decision context:

- hidden root cause;
- expected next step;
- acceptable evaluation paths;
- prohibited-action labels;
- expected terminal outcome;
- scenario scoring rules.

## Context package structure

A context package should contain:

- `context_package_id`;
- `assembled_at`;
- `session_summary`;
- `current_goal`;
- `resolved_target`;
- `current_phase`;
- `relevant_service_context`;
- `observed_state_summary`;
- `evidence_summary`;
- `active_hypotheses`;
- `evidence_gaps`;
- `capability_gaps`;
- `relevant_runbooks`;
- `available_tools`;
- `applicable_constraints`;
- `remaining_budget_summary`;
- `requested_output_schema`.

## Assembly pipeline

1. Read the current runtime state.
2. Resolve service, environment and action scope where possible.
3. Select information relevant to the current goal and phase.
4. Remove hidden evaluation data.
5. Exclude obsolete or superseded observations.
6. Mark stale, conflicting and incomplete evidence.
7. Summarize raw tool results into normalized state.
8. Select applicable runbooks and tool capabilities.
9. Apply context-size and repetition limits.
10. Validate the final context-package schema.
11. Record context references in the trace.
12. Send the package to the proposal producer.

## Selection rules

Information should be included when it is required to:

- understand the user's goal;
- resolve the affected service or environment;
- evaluate an active hypothesis;
- choose the next diagnostic step;
- understand available capabilities;
- identify action constraints;
- avoid repeating an already completed check.

Information should be excluded when it is:

- unrelated to the current task;
- hidden evaluation truth;
- obsolete and already superseded;
- duplicated without additional value;
- raw technical noise;
- an internal implementation detail not required by the model.

## Operational state handling

The context package should prefer normalized state over raw source responses.

Raw source data remains available in the trace for audit and debugging.

Each included observation must preserve:

- source reference;
- timestamp;
- scope;
- freshness;
- known limitations.

## Session summary

The session summary should contain:

- original user goal;
- resolved target;
- completed steps;
- important evidence collected;
- rejected or contradicted hypotheses;
- current open hypotheses;
- missing checks;
- prepared artifacts;
- pending confirmation or escalation state.

It should not reproduce the entire conversation or trace.

## Tool-result handling

After a tool call:

1. retain the raw result in the trace;
2. validate the result schema;
3. normalize factual observations;
4. update evidence and contradiction state;
5. mark previous observations stale when required;
6. create a compact result summary;
7. include only relevant information in the next context package.

Instruction-like text found inside tool output is treated as data, not as an
instruction to the model or runtime.

## Multiple plausible hypotheses

The runtime may include several active hypotheses when current evidence supports
more than one explanation.

The model must not be forced to select one root cause prematurely.

The next step should preferably:

- distinguish between competing hypotheses;
- provide high expected information value;
- remain read-only where possible;
- have low operational risk;
- avoid unnecessary cost;
- remain useful even if one hypothesis is later rejected.

Possible outcomes include:

- call an allowed read-only tool;
- ask a precise clarification question;
- request user-provided evidence;
- record a capability gap;
- escalate when no rational validation path is available.

## Context budget

The runtime must control:

- maximum context size;
- number of included observations;
- repeated evidence;
- runbook excerpt length;
- session-history length;
- tool-result verbosity.

Later experiments may compare:

- dropping and trimming;
- summarization and compression;
- offloading and retrieval.

## Freshness and change handling

Before every state-changing action, the runtime must rebuild or revalidate the
relevant context.

A previous context package cannot authorize execution when:

- deployment state changed;
- traffic or load changed materially;
- action parameters changed;
- confirmation expired;
- a conflicting operation appeared;
- required evidence became stale.

## Required invariants

- Hidden evaluation data never enters the context package.
- Raw full trace is not returned automatically.
- Facts and hypotheses remain separate.
- Missing data is explicitly represented.
- Multiple hypotheses may remain active.
- Tool availability does not imply action permission.
- Confirmation does not replace technical preconditions.
- Every context package is traceable to its source records.
