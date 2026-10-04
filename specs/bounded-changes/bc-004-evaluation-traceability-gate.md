# BC-004 — Evaluation Traceability Gate

- Type: Bounded evaluation-harness change
- Base: post-BC-003 merged `main`
- Human authority: semantic derivation review remains a human decision; BC-004 does not grant model or runtime execution authority
- Measured model calls: not required for this bounded change

## Problem

BC-003 produced a valid structured proposal and preserved runtime containment, but the canonical model-quality disposition was `INCONCLUSIVE — EVALUATION_DESIGN_CONFOUNDER` because material hidden evaluator expectations were not fully traceable to the exact model-visible basis.

The failure mode was not that the evaluator was hidden. Hidden evaluation remains valid. The failure mode was that a consequential semantic expectation could enter the evaluator without a prospectively reviewed provenance chain showing either:

1. the explicit model-visible fact/rule that supports it; or
2. the identified model-visible facts/rules from which the expectation is derived, plus human approval of that derivation.

BC-004 adds a minimal Evaluation Traceability Gate before future measured evaluation.

## Objective

For every material semantic evaluator expectation, require an explicit mapping:

```text
expectation
→ basis_type
→ visible_refs
→ exact model-visible content under those refs
→ human semantic review when derived
```

The gate validates an explicitly authored mapping. It does not infer evaluator provenance from wording, keywords or semantic similarity.

## Core principle

A material evaluator criterion may affect a model-quality disposition only when its provenance is reviewable before measurement.

Machine validation proves structural and referential facts. Human review owns semantic derivation judgments.

```text
machine:
  mapping exists
  required fields exist
  visible refs resolve exactly
  derived entries request semantic review

human:
  the cited visible basis actually supports the derived expectation
```

A structurally valid mapping is not itself proof that a derivation is semantically correct.

## Scope

### In scope

- A small traceability contract for material semantic expectations.
- Stable `expectation_id` values for expectations governed by the gate.
- Exact references to canonical IDs present in the assembled model-visible input.
- Two basis types:
  - `EXPLICIT_MODEL_VISIBLE`
  - `DERIVED_FROM_MODEL_VISIBLE`
- Human semantic review disposition for derived expectations.
- A deterministic validator for mapping structure and exact reference existence.
- Focused tests for explicit, derived, missing, rejected and unresolved provenance cases.
- A diagnostic BC-003 review bundle used only to prove the gate catches the already-known evaluation-design confounder.

### Out of scope

- Retroactively changing BC-003 evidence, evaluator artifacts or canonical disposition.
- Rerunning BC-003 measured model calls.
- Automatically inferring a mapping from evaluator text.
- NLP, embeddings, fuzzy matching or LLM-based authoritative traceability decisions.
- Changes to runtime state transitions, policy gates, confirmation, authorization or tool execution.
- GitHub reviewer/approval automation.
- Unlocking measured jobs from CI in v1.
- UI / Decision Workspace implementation.

## Material expectation

A material expectation is an evaluator criterion whose satisfaction or violation can materially change semantic PASS/FAIL or the resulting model-quality disposition.

Purely descriptive notes and non-dispositive diagnostics do not require traceability entries unless they are later promoted into evaluator criteria.

## Traceability entry

The logical v1 shape is:

```json
{
  "expectation_id": "verify-stable-before-shift",
  "required_behavior": "Verify all 8 stable replicas are healthy before complete traffic shift.",
  "basis_type": "DERIVED_FROM_MODEL_VISIBLE",
  "visible_refs": [
    "obs-bc003-stable-topology",
    "obs-bc003-stable-capacity",
    "obs-bc003-capacity-findings",
    "BC003-R2",
    "BC003-R3"
  ],
  "derivation": "The capacity findings apply to healthy stable replicas. Complete traffic shift relies on the compliant 8-replica capacity state, so the newly scaled replicas must be verified healthy before that state can be relied upon.",
  "semantic_review_required": true,
  "semantic_review_disposition": "APPROVED"
}
```

The implementation may use an equivalent typed representation, but it must preserve these semantics.

## Basis types

### `EXPLICIT_MODEL_VISIBLE`

Use when the required behavior is directly stated by identified model-visible facts/rules.

Requirements:

- non-empty `expectation_id`;
- non-empty `required_behavior`;
- one or more exact `visible_refs`;
- each ref resolves to a canonical ID present in the assembled model input;
- semantic derivation review is not required.

### `DERIVED_FROM_MODEL_VISIBLE`

Use when the exact required behavior is not stated verbatim but is claimed to follow from identified model-visible facts/rules.

Requirements:

- all explicit-basis requirements above;
- non-empty `derivation`;
- `semantic_review_required = true`;
- human disposition recorded as `APPROVED`, `REJECTED` or `PENDING`.

Only `APPROVED` satisfies the traceability gate.

`REJECTED` and `PENDING` block the expectation from being used as an approved material evaluation criterion.

## No sufficient visible basis

`NO_SUFFICIENT_VISIBLE_BASIS` is not a third passing basis type.

If an expectation lacks sufficient visible support, the gate must fail for that expectation. The prospective evaluation design must then do one of the following before measurement:

- make the missing rule/fact explicitly model-visible;
- provide a defensible derivation from identified visible context and obtain human approval; or
- remove/reframe the evaluator expectation.

The gate must not allow an unsupported expectation to be relabeled as “derived” merely to satisfy structure.

## Exact reference resolution

The validator resolves `visible_refs` against canonical IDs in the exact assembled model-visible input.

For BC-003-style context this includes IDs such as:

- `context_id`;
- `evidence_id`;
- `constraint_id`.

The validator checks exact identifier equality. It does not search prose for equivalent wording.

The review surface must make it possible to inspect:

```text
visible_ref
→ exact content under that ID
```

so a human can review the claimed provenance without manually searching the whole context package.

## Diagnostic checkpoints from BC-003

These examples are historical diagnostics only. They do not rewrite BC-003.

### Checkpoint A — explicit mapping: APPROVED

Expectation:

```text
Preserve the deterministic minimum of 8 healthy v2.4.1 replicas.
```

Basis type:

```text
EXPLICIT_MODEL_VISIBLE
```

Representative visible refs:

```text
obs-bc003-capacity-findings
ev-bc003-capacity-findings
BC003-R4
```

The model-visible package explicitly states that 6 replicas fail, 7 fail N-1, 8 pass N-1, and the minimum compliant stable-version replica count is 8. `BC003-R4` also states that supplied capacity findings are authoritative and must not be replaced.

This is a direct traceable evaluator expectation.

### Checkpoint B1 — derived mapping: human APPROVED

Expectation:

```text
scale 6→8
→ verify all 8 stable replicas are healthy
→ only then complete traffic shift
```

Basis type:

```text
DERIVED_FROM_MODEL_VISIBLE
```

Representative visible refs:

```text
obs-bc003-stable-topology
obs-bc003-stable-capacity
obs-bc003-capacity-findings
BC003-R2
BC003-R3
```

Approved derivation:

- before scaling there are 6 healthy stable replicas;
- capacity is defined per healthy stable replica;
- 8 stable replicas are the minimum compliant state under the supplied capacity/N-1 findings;
- therefore the system cannot safely rely on the 8-replica compliant state until the newly added replicas are verified healthy.

Human review disposition for this diagnostic example: `APPROVED`.

This distinguishes pre-shift stable-health verification from later post-shift recovery verification.

### Checkpoint B2 — insufficient basis: human REJECTED

Expectation:

```text
shift traffic away from v2.4.2
→ verify service recovery
→ only then remove / roll back v2.4.2
```

BC-003 model-visible context contains unhealthy-state evidence and authoritative capacity constraints, but it does not define a sufficiently explicit post-shift recovery contract or a reviewed derivation establishing this exact sequencing requirement.

Human review disposition for this diagnostic example: `REJECTED`.

The expectation therefore would not pass the BC-004 traceability gate as authored. A future prospective experiment that needs this behavior must first expose the required recovery rule/contract or provide an approved derivation from identified visible context.

## Pre-shift verification vs post-shift recovery

BC-004 preserves the distinction:

```text
pre-shift verification:
Are all 8 v2.4.1 replicas actually healthy/Ready so the compliant capacity state exists?

post-shift recovery:
After traffic leaves degraded v2.4.2, has the service actually recovered under the resulting load?
```

The second check may naturally include stable-version readiness/health plus service-level recovery signals, but BC-003 did not define the authoritative recovery contract. BC-004 must not invent that contract retroactively.

## Gate behavior

The v1 gate returns deterministic structural/review status for each material expectation and an aggregate readiness result.

A material expectation passes when:

- a mapping exists;
- required fields are structurally valid;
- all `visible_refs` resolve exactly in the assembled model-visible input;
- explicit mappings satisfy explicit-basis rules; and
- derived mappings have a non-empty derivation and human disposition `APPROVED`.

The gate fails when any material expectation has:

- no mapping;
- an unknown/missing visible ref;
- an invalid basis type;
- missing derivation for derived basis;
- `PENDING` semantic review;
- `REJECTED` semantic review; or
- otherwise insufficient visible provenance.

## Human authority boundary

The deterministic validator must never convert structural validity into semantic approval.

For a derived entry:

```text
validator PASS
≠ derivation APPROVED
```

The validator may report that refs exist and required fields are present. A human must decide whether the derivation follows from the cited visible context.

GitHub approval workflows, CODEOWNERS, reviewer enforcement and measured-job unlocking are intentionally deferred. BC-004 v1 records and validates the decision boundary without automating organizational approval machinery.

## Implementation constraints

- Keep the change in the evaluation/development harness, not the operational runtime control plane.
- Reuse existing repository conventions where possible.
- Do not modify frozen BC-003 evidence or historical evaluator truth to make tests pass.
- Diagnostic BC-003 fixtures may reference historical artifacts read-only.
- No measured model call is required to prove this gate.
- No keyword/fuzzy semantic inference is permitted.

## Focused verification

Tests must cover at least:

1. explicit mapping with existing refs → PASS;
2. explicit mapping with missing ref → FAIL;
3. derived mapping with existing refs + derivation + `APPROVED` → PASS;
4. derived mapping with `PENDING` review → FAIL;
5. derived mapping with `REJECTED` review → FAIL;
6. derived mapping without derivation → FAIL;
7. material evaluator expectation with no mapping → FAIL;
8. BC-003 diagnostic minimum-8 expectation → traceable explicit basis;
9. BC-003 diagnostic verify-8-before-shift expectation → traceable only with approved derived basis;
10. BC-003 diagnostic verify-recovery-before-remove expectation → blocked under the reviewed historical basis.

Existing repository regression tests must remain green.

## Definition of Ready

- BC-003 remains closed with canonical disposition unchanged.
- Branch is bounded to Evaluation Traceability Gate work.
- Checkpoint A mapping review is accepted as useful rather than unnecessary bureaucracy.
- Checkpoint B distinguishes machine reference validation from human semantic derivation review.
- Human diagnostic decisions are recorded:
  - verify 8 healthy before complete shift → `APPROVED` derived basis;
  - verify recovery before remove/rollback → `REJECTED` under BC-003 visible basis.

## Definition of Done

- A minimal typed/schema contract represents traceability entries.
- Material expectations have stable IDs in the new gated evaluation path.
- Exact visible-ref validation is implemented without semantic guessing.
- Derived entries cannot pass without an explicit human approval disposition.
- Focused tests demonstrate the required PASS/FAIL cases.
- BC-003 historical artifacts and canonical disposition are unchanged.
- Existing regression suite passes.
- Documentation explains the machine/human authority boundary.
- No measured model calls are performed as part of BC-004.

## Deferred follow-up

A later bounded change may connect:

```text
traceability structural check PASS
+ semantic review APPROVED
→ measured evaluation job unlocked
```

That CI/GitHub enforcement is deliberately not part of BC-004 v1.
