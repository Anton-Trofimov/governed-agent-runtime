# Runtime Architecture

- Spec version: 0.1.0
- Status: draft
- Specification family: governed-runtime-core

## Purpose

Define the framework-independent architecture of a governed agent runtime for
operational incident diagnosis.

The same runtime contracts must support:

- deterministic proposals in Exp 18.0;
- LLM-generated proposals in later experiments;
- fixed-workflow comparison;
- bounded agent loops;
- future LangGraph and Langfuse integration.

## Core principle

The model proposes a next step.

The deterministic runtime remains responsible for:

- context assembly;
- schema validation;
- target resolution;
- permissions;
- policy gates;
- technical preconditions;
- confirmation;
- tool execution;
- state transitions;
- budget enforcement;
- audit and evaluation data collection.

The model is not the control plane.

## Main components

### 1. User interface

Receives the operational request and displays:

- answers;
- clarification questions;
- diagnostic summaries;
- prepared artifacts;
- confirmation requests;
- execution and escalation results.

### 2. Context assembler

Builds a step-specific context package from:

- agent charter;
- service catalog and topology;
- current session state;
- normalized operational state;
- relevant runbooks;
- allowed tool capability summaries;
- relevant policy summaries.

The model does not read repository directories directly.

### 3. Proposal producer

Produces one structured next-step proposal.

In Exp 18.0 this component is deterministic.

Later implementations may use an LLM.

Supported proposal types:

- `CALL_TOOL`
- `PROVIDE_ANSWER`
- `PROVIDE_BOUNDED_HYPOTHESIS`
- `CREATE_DRAFT`
- `ASK_CLARIFICATION`
- `REQUEST_CONFIRMATION`
- `STOP_OR_ESCALATE`

### 4. Runtime policy engine

Evaluates proposals through ordered gates:

1. schema validity;
2. target resolution;
3. phase permission;
4. role authorization;
5. evidence sufficiency;
6. freshness and consistency;
7. technical preconditions;
8. confirmation;
9. budget and repetition limits;
10. audit readiness.

### 5. Tool registry and adapters

The registry stores capability contracts.

Adapters:

- validate tool arguments;
- call deterministic fixtures or future external systems;
- retain raw results in the trace;
- normalize results into runtime state;
- return only relevant summaries to the model.

### 6. State manager

Maintains separate state layers:

- session and workflow state;
- observed state;
- evidence state;
- diagnostic assessment;
- action readiness;
- confirmation state;
- execution state.

### 7. Confirmation manager

Creates a confirmation request only after all earlier gates pass.

Confirmation is bound to:

- action and tool;
- target and environment;
- exact parameters;
- plan or draft version;
- relevant state snapshot;
- user identity;
- timestamp and expiration.

### 8. Trace store

Records the full execution history:

- input context references;
- proposals;
- policy-gate results;
- tool arguments;
- raw tool results;
- normalized state changes;
- confirmations;
- errors;
- latency;
- token and cost data where applicable.

### 9. Evaluation harness

Evaluates runtime and model behavior against hidden acceptance data.

It does not participate in the operational decision path.

## Data visibility

### Model visibility

The model receives:

- the current context package;
- relevant normalized state;
- relevant tool-result summaries;
- allowed capability summaries;
- relevant policy constraints;
- compact session history.

### Runtime visibility

The runtime receives:

- full active state;
- full tool contracts;
- full policy rules;
- raw tool outputs;
- confirmation metadata;
- execution budgets;
- trace metadata.

The runtime does not receive hidden evaluation truth during execution.

### Evaluation visibility

The evaluation harness may receive:

- all model proposals;
- all runtime decisions;
- full traces;
- hidden root cause;
- acceptable paths;
- prohibited actions;
- expected outcomes.

## Raw full trace

The raw full trace is not returned to the model automatically because it may:

- unnecessarily expand context;
- repeat obsolete observations;
- expose internal policy details;
- contain instruction-like tool output;
- reinforce earlier model errors;
- distract from the current state.

The model receives a controlled session summary and relevant normalized state.

## Execution flow

1. Receive request.
2. Assemble initial context.
3. Resolve goal, service, environment and scope.
4. Produce one structured proposal.
5. Validate proposal schema.
6. Apply runtime policy gates.
7. Return a runtime decision.
8. Execute an allowed tool when applicable.
9. Normalize the tool result.
10. Update evidence and workflow state.
11. Continue within budget or stop.
12. Record terminal outcome and evaluation data.

## Runtime decisions

Supported decisions:

- `ALLOW`
- `PROVIDE_ANSWER`
- `ASK_CLARIFICATION`
- `REQUIRE_CONFIRMATION`
- `REPLACE_WITH_SAFER_PATH`
- `BLOCK`
- `SAFE_FALLBACK`
- `ESCALATE`

A safer-path decision should preserve useful progress where possible.

## Runtime phases

### DIAGNOSE

Allowed:

- read-only tools;
- clarification;
- evidence assessment;
- bounded hypotheses;
- fallback and escalation.

### PREPARE

Allowed:

- incident draft;
- notification draft;
- remediation plan.

### EXECUTE

Allowed only after target, authorization, evidence, preconditions and
confirmation are valid.

## Task lifecycle

Primary lifecycle:

`RECEIVED`
→ `CONTEXT_ASSEMBLED`
→ `TARGET_RESOLVED`
→ `DIAGNOSING`
→ `EVIDENCE_EVALUATED`
→ `HYPOTHESIS_READY`
→ `PREPARING`
→ `ACTION_CANDIDATE`
→ `PRECONDITIONS_CHECKED`
→ `AWAITING_CONFIRMATION`
→ `EXECUTING`
→ `VERIFYING`
→ `COMPLETED`

Optional states:

- `NEEDS_CLARIFICATION`
- `SAFE_FALLBACK`
- `ESCALATED`
- `BLOCKED`
- `FAILED`

Not every request traverses every state.

## Comparison architecture

Fixed workflow and bounded agent experiments must use the same:

- source fixtures;
- tool contracts;
- normalized state;
- runtime policy;
- evaluation definitions;
- product metrics.

This allows the project to compare decision strategy rather than different
infrastructure.
