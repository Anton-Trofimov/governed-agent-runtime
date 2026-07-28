# Evidence Model

- Spec version: 0.1.0
- Status: draft
- Specification family: governed-runtime-core

## Purpose

Define how operational observations become evidence for or against diagnostic
claims.

The evidence model supports:

- bounded hypotheses;
- contradiction detection;
- freshness checks;
- mandatory diagnostic checks;
- capability-gap reporting;
- deterministic action gates.

Evidence does not grant permission to execute an action.

## Evidence principles

1. An observation is not automatically evidence for a cause.
2. Evidence must be linked to an explicit claim.
3. Source, time window and scope must be recorded.
4. Conflicting evidence must remain visible.
5. A current snapshot does not replace a relevant time window.
6. Missing evidence must not be converted into a positive conclusion.
7. Model knowledge may suggest a check but cannot fabricate its result.
8. Confirmation cannot compensate for insufficient evidence.

## Evidence item

Each evidence item contains:

| Field | Meaning |
|---|---|
| `evidence_id` | Stable evidence record |
| `claim_id` | Claim being evaluated |
| `source_type` | Metrics, deployment, events, dependency, traffic, runbook or user |
| `source_id` | Concrete source reference |
| `observed_at` | Time represented by the source |
| `collected_at` | Time the runtime obtained it |
| `scope` | Service, environment, target, version, replica or dependency |
| `time_window` | Relevant observation interval |
| `freshness_status` | `FRESH`, `STALE` or `UNKNOWN` |
| `reliability` | `AUTHORITATIVE`, `HIGH`, `MEDIUM` or `LOW` |
| `support_type` | `SUPPORTS`, `CONTRADICTS` or `NEUTRAL` |
| `summary` | Normalized factual summary |
| `raw_reference` | Pointer to the raw trace record |
| `limitations` | Known gaps or interpretation limits |

## Claims

A claim is a statement that can be supported or contradicted.

Examples:

- version `2.4.2` has a higher 5xx rate than version `2.4.1`;
- the provider dependency is currently degraded;
- one replica is intermittently unstable;
- the payment database is saturated;
- retry traffic from one client group is amplifying load;
- rollback capacity is currently insufficient.

A root-cause hypothesis may depend on several claims.

## Evidence freshness

Freshness is evaluated relative to:

- scenario reference time;
- source update frequency;
- requested diagnostic window;
- action risk.

A status snapshot may be fresh but insufficient when the issue is intermittent.

Higher-risk actions require stricter freshness than read-only diagnosis.

## Evidence reliability

### AUTHORITATIVE

Direct system-of-record evidence for the claim.

Examples:

- deployment record;
- runtime policy;
- confirmation record.

### HIGH

Direct telemetry from the affected component.

Examples:

- version-specific error metrics;
- replica readiness transitions;
- dependency timeout metrics.

### MEDIUM

Correlated operational evidence requiring interpretation.

Examples:

- service latency rising during a dependency event;
- traffic change coinciding with elevated errors.

### LOW

Weak, incomplete or user-reported evidence without independent verification.

Low-reliability evidence may motivate safe diagnostic checks but cannot be the
sole basis for restart or rollback.

## Contradictions

Evidence is contradictory when relevant items support incompatible conclusions.

Examples:

- current readiness is 5/5 while one replica shows repeated readiness transitions;
- overall service error rate is low while one new version has a high error rate;
- a runbook suggests provider degradation while provider telemetry is healthy.

Contradictions must be stored rather than silently resolved by the model.

## Evidence sufficiency

Evidence sufficiency is determined by:

- required claim coverage;
- mandatory checks;
- freshness;
- reliability;
- contradiction state;
- target and scope resolution.

Supported statuses:

- `SUFFICIENT`
- `PARTIAL`
- `INSUFFICIENT`

A numerical model confidence score does not replace deterministic sufficiency
rules.

## Mandatory checks

A state-changing action may define mandatory checks.

Rollback may require:

- regression evidence by version;
- concrete deployment identification;
- previous version availability;
- database and configuration compatibility;
- projected and transitional capacity;
- dependency headroom;
- startup and warm-up time;
- traffic-drain conditions;
- absence of a conflicting operation.

Single-replica restart may require:

- exact unstable replica;
- evidence that the issue is replica-local;
- sufficient capacity after removal;
- no active rollout or conflicting operation.

## Deterministic-rule hypothesis

A deterministic-rule hypothesis is produced from explicit runtime rules applied
to normalized observations.

It must:

- reference the claims and evidence that triggered the rule;
- remain separate from authorization and action readiness;
- expose missing checks and contradictions;
- be reproducible from the same normalized state.

## Runbook-grounded hypothesis

A runbook-grounded hypothesis requires:

- an active applicable runbook;
- matching service and environment;
- observations consistent with the runbook conditions;
- no unresolved contradiction that invalidates the path.

A runbook provides diagnostic guidance, not authorization.

## Model-prior hypothesis

The model may identify a plausible explanation not covered by the runbooks.

It must be marked `MODEL_PRIOR` and `UNCONFIRMED`.

It may only:

- describe the motivating observations;
- identify required evidence;
- propose safe read-only validation;
- recommend escalation when validation is unavailable.

It cannot be the sole basis for a state-changing action.

## Evidence gap

An evidence gap contains:

- `gap_id`;
- missing data or signal;
- diagnostic purpose;
- affected claim or hypothesis;
- preferred source or capability;
- whether the user can provide it;
- operational impact of remaining unknown.

## Capability gap

A capability gap exists when required evidence cannot be obtained through the
current allowed tools or supplied context.

The runtime should:

1. record the missing capability;
2. preserve the bounded hypothesis;
3. prevent unsupported execution;
4. ask for user-provided evidence when appropriate;
5. otherwise escalate.

Capability gaps are an explicit evaluation result, not necessarily a system
failure.

## Relationship to action readiness

Evidence may make an action diagnostically plausible.

The runtime must still independently validate:

- authorization;
- exact target;
- technical preconditions;
- confirmation;
- budget;
- audit readiness.

The evidence model never sets execution permission.
