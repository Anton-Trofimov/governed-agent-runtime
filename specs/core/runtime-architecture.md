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

#### Deterministic decision-application trace contract

For the current Exp 18.0 runtime slice, a successfully evaluated proposal and
applied runtime decision must produce append-only trace events in this order:

1. `PROPOSAL_CREATED`;
2. one `GATE_EVALUATED` event for each recorded gate result, preserving policy
   order;
3. `RUNTIME_DECISION`;
4. `STATE_UPDATED` after successful decision application.

`RUNTIME_DECISION` records the authoritative runtime decision, including the
proposal reference, decision type, reason codes, declared next state, tool
execution permission and confirmation requirement.

`STATE_UPDATED` records:

- the runtime decision and proposal references;
- the applied rule type and rule identifier;
- previous and new state versions;
- previous and new task states;
- previous and new phases;
- previous and new action-readiness values;
- previous and new terminal outcomes.

Normal lifecycle transitions use:

- `application_rule_type: STATE_TRANSITION`;
- a transition identifier such as `T015` or `T033`.

Recoverable decision application uses:

- `application_rule_type: DECISION_APPLICATION_RULE`;
- `application_rule_id: DA001`;
- the matched lifecycle disposition.

A `STATE_UPDATED` event may be emitted only after the runtime has validated and
successfully applied the decision. An unsupported or ambiguous transition must
not be represented as a successful state update.

Decision application and trace recording do not execute tools. The absence of
`TOOL_CALL_STARTED`, `TOOL_RESULT_RECEIVED`, `EXECUTION_STARTED` and
`EXECUTION_COMPLETED` events means that no tool execution occurred in this
runtime step.

#### Deterministic preparation-tool execution contract

In the current S01 vertical, `create_remediation_plan` may be invoked only when:

- the proposal is schema-valid;
- the runtime decision is `ALLOW`;
- `tool_execution_allowed` is `true`;
- the current runtime phase is `PREPARE`;
- the tool arguments satisfy the registered input contract.

A successful deterministic mock invocation:

1. derives the idempotency key from the session identifier and canonical tool
   arguments;
2. creates a stable tool-call identifier and remediation-plan identifier;
3. returns a schema-valid `Tool Result Envelope`;
4. records `TOOL_CALL_STARTED`;
5. records `TOOL_RESULT_RECEIVED`;
6. normalizes a compact remediation-plan reference into the candidate action;
7. increments the tool-call counter exactly once;
8. applies transition `T019` from `PREPARING` to `ACTION_CANDIDATE`;
9. records the resulting `STATE_UPDATED` event.

The plan result distinguishes artifact creation from action readiness:

- `PRECONDITIONS_PENDING` means that the plan exists but one or more required
  action preconditions remain unresolved;
- `READY_FOR_PRECONDITION_EVALUATION` means that the plan may proceed to the
  deterministic precondition-evaluation stage.

Preparation-tool invocation does not perform the candidate operational action.
It must not create `EXECUTION_STARTED` or `EXECUTION_COMPLETED` events, modify
the operational execution state, set `action_ready` to true, or set a terminal
outcome.

For S01, successful remediation-plan creation may be evaluated as the governed
outcome `DRAFT_CREATED`, while the active task continues through
`ACTION_CANDIDATE`.

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

### Transition-aware phase permission

G03 evaluates proposals against the current runtime phase by default.

An exception is allowed only when an explicit
`transition_aware_phase_rules` entry binds all of the following:

- current phase;
- current task state;
- proposal type;
- tool category;
- decision next state;
- lifecycle transition;
- resulting permission phase.

For `PH001`, a `CREATE_DRAFT` proposal using a preparation tool may be
authorized while the task is in `HYPOTHESIS_READY` and phase `DIAGNOSE`.

The governed path is:

- before decision application: `HYPOTHESIS_READY / DIAGNOSE`;
- decision application uses `T015`;
- after decision application: `PREPARING / PREPARE`.

The runtime must not mutate phase before policy evaluation.

An `ALLOW` decision under a transition-aware phase rule does not permit the
tool adapter to run immediately. Tool execution may start only after the
decision has been applied and the current state satisfies:

- `task_state = PREPARING`;
- `phase = PREPARE`.

The tool adapter must revalidate these conditions before execution.

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

## Explicit BC-006 execution profile

BC-006 selects `bounded-remediation.yaml` as the normative synthetic S12 profile.
Its concrete registry, schemas, preconditions, confirmation and transition table
specialize the legacy single-step path only when the BC-006 runner is invoked.
The shared `runtime_policy` and `state_transition` modules own its admission and
lifecycle; `bc006_runtime` assembles context and dispatches only admitted adapters.
The provider receives no adapter or mutation handle. Deterministic scripted controls,
Ollama and manual proposal transport all use this same profile/runtime/environment.
Preparation creates one immutable candidate per write proposal without a second
inference. Legacy `create_remediation_plan`, T023 and T029 remain unchanged for
historical paths. This does not introduce a general framework or production adapter.
