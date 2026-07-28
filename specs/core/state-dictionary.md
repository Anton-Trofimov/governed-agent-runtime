# State Dictionary

- Spec version: 0.1.0
- Status: draft
- Specification family: governed-runtime-core

## Purpose

Define the canonical runtime state and ownership of each state layer.

Facts, interpretations, recommendations, authorization and execution must remain
separate.

No model-generated field can authorize a state-changing action by itself.

## Canonical identifiers

| Field | Meaning |
|---|---|
| `service_id` | Stable logical service identifier |
| `environment_id` | Environment such as production or staging |
| `deployment_target_id` | Region, cluster or namespace deployment target |
| `deployment_id` | One concrete deployment event |
| `version_id` | Software version |
| `replica_id` | One running service instance |
| `dependency_id` | External or internal dependency |
| `runbook_id` | Operational guidance document |
| `incident_id` | Incident or incident draft |
| `event_id` | Runtime or infrastructure event |
| `trace_id` | Full execution trace |
| `tool_call_id` | One tool invocation |
| `confirmation_id` | One confirmation record |

## State ownership rules

- Source adapters own observed facts.
- Evidence logic owns evidence classification.
- The model may propose diagnostic interpretations.
- The runtime owns action readiness and authorization state.
- Tool adapters own execution results.
- The evaluation harness owns hidden expected outcomes.

## Session state

| Field | Type | Source | Meaning |
|---|---|---|---|
| `session_id` | string | runtime | Active interaction identifier |
| `current_goal` | string | user/runtime | Current operational objective |
| `phase` | enum | runtime | `DIAGNOSE`, `PREPARE` or `EXECUTE` |
| `task_state` | enum | runtime | Current lifecycle state |
| `resolved_service_id` | string/null | runtime | Resolved logical service |
| `resolved_environment_id` | string/null | runtime | Resolved environment |
| `resolved_scope` | object/null | runtime | Target, replica or deployment scope |
| `tool_call_count` | integer | runtime | Calls already made |
| `tool_call_budget` | integer | runtime policy | Maximum allowed calls |
| `repeated_call_count` | integer | runtime | Repeated equivalent calls |
| `capability_gaps` | array | runtime/model proposal | Required evidence unavailable through current capabilities |

## Observed state

Observed state contains source-derived facts only.

| Field | Type | Source | Meaning |
|---|---|---|---|
| `observations` | array | adapters | Normalized factual observations |
| `reference_time` | datetime | scenario/runtime | Time against which freshness is evaluated |
| `current_deployment` | object/null | deployment source | Active deployment facts |
| `service_status` | object/null | status source | Current service and replica status |
| `metric_windows` | array | metrics source | Time-window metric observations |
| `runtime_events` | array | event source | Deployments, restarts, readiness or config events |
| `dependency_states` | array | dependency source | Dependency availability and performance |
| `traffic_breakdowns` | array | traffic source | Requests grouped by version, client or attempt type |

Observed facts do not contain inferred root causes.

## Evidence state

| Field | Type | Source | Meaning |
|---|---|---|---|
| `evidence_items` | array | evidence engine | Evidence linked to claims |
| `mandatory_checks_completed` | array | runtime | Required checks that passed |
| `mandatory_checks_missing` | array | runtime | Required checks not yet completed |
| `freshness_status` | enum | evidence engine | `FRESH`, `STALE`, `MIXED` or `UNKNOWN` |
| `contradictions` | array | evidence engine | Conflicting evidence relationships |
| `evidence_sufficiency` | enum | runtime | `SUFFICIENT`, `PARTIAL`, `INSUFFICIENT` |
| `evidence_gaps` | array | runtime/model proposal | Missing information and its diagnostic purpose |

Evidence sufficiency does not authorize execution.

## Diagnostic assessment

| Field | Type | Source | Meaning |
|---|---|---|---|
| `hypotheses` | array | model or deterministic logic | Candidate explanations |
| `hypothesis_source` | enum | proposal/runtime | `DETERMINISTIC_RULE`, `RUNBOOK_GROUNDED` or `MODEL_PRIOR` |
| `supported_claim_ids` | array | evidence engine | Claims supported by evidence |
| `contradicted_claim_ids` | array | evidence engine | Claims contradicted by evidence |
| `cause_status` | enum | runtime/evaluation | `SUPPORTED`, `PLAUSIBLE`, `UNCONFIRMED`, `CONTRADICTED` or `UNKNOWN` |
| `recommended_next_step` | object/null | proposal | One proposed useful step |
| `uncertainty_notes` | array | proposal/runtime | Explicit uncertainty |

Diagnostic assessment cannot authorize an action.

## Action readiness

| Field | Type | Source | Meaning |
|---|---|---|---|
| `candidate_action` | object/null | proposal | Proposed action and parameters |
| `target_resolved` | boolean | runtime | Exact target is known |
| `role_authorized` | boolean | runtime policy | User role may request the action |
| `evidence_gate_passed` | boolean | runtime | Required evidence is sufficient |
| `freshness_gate_passed` | boolean | runtime | Evidence is current enough |
| `preconditions_passed` | boolean | runtime | Technical conditions passed |
| `conflicting_operation_present` | boolean | runtime | Another operation blocks execution |
| `confirmation_required` | boolean | runtime policy | Human confirmation is required |
| `action_ready` | boolean | runtime | All pre-confirmation gates passed |
| `blocking_reason_codes` | array | runtime | Deterministic reasons for non-readiness |

Only the runtime may set `action_ready`.

## Confirmation state

| Field | Type | Source | Meaning |
|---|---|---|---|
| `confirmation_id` | string | runtime | Confirmation record |
| `bound_action` | object | runtime | Exact action and parameters |
| `bound_target` | object | runtime | Exact service, environment and scope |
| `bound_state_hash` | string | runtime | Relevant state snapshot |
| `bound_artifact_version` | string/null | runtime | Plan or draft version |
| `confirmed_by` | string/null | user identity | Confirming user |
| `confirmed_at` | datetime/null | runtime | Confirmation timestamp |
| `expires_at` | datetime/null | runtime policy | Expiration |
| `confirmation_status` | enum | runtime | `PENDING`, `VALID`, `EXPIRED`, `INVALIDATED`, `REJECTED` |

Confirmation is invalidated when relevant target, parameters, state or artifact
version changes.

## Execution state

| Field | Type | Source | Meaning |
|---|---|---|---|
| `execution_status` | enum | tool/runtime | `NOT_STARTED`, `RUNNING`, `SUCCEEDED`, `FAILED` or `PARTIAL` |
| `executed_tool_call_id` | string/null | runtime | Executed tool call |
| `side_effect_summary` | object/null | tool adapter | Mock side-effect result |
| `verification_status` | enum | runtime | `NOT_REQUIRED`, `PENDING`, `PASSED` or `FAILED` |
| `execution_error` | object/null | tool adapter | Structured failure |
| `terminal_outcome` | enum/null | runtime | Final governed outcome |

## Terminal outcomes

- `COMPLETED`
- `ANSWERED`
- `CLARIFICATION_REQUESTED`
- `DRAFT_CREATED`
- `CONFIRMATION_REQUIRED`
- `MOCK_ACTION_EXECUTED`
- `SAFE_FALLBACK`
- `ESCALATED`
- `BLOCKED`
- `FAILED`

## Required invariant

The following sequence must remain explicit:

observed fact
→ evidence classification
→ diagnostic assessment
→ candidate action
→ runtime preconditions
→ confirmation
→ execution
→ verification

No earlier state may silently imply a later state.
