# BC-004 — Evaluation Traceability Gate Disposition

## Decision

BC-004 disposition:

`ACCEPTED — TRACEABILITY GATE DEMONSTRATED`

The implemented v1 gate is accepted as a useful evaluation-governance control.
It closes the specific design gap exposed by BC-003 without expanding runtime or
model authority.

## Basis

BC-004 added an explicit expectation-to-visible-basis contract with two allowed
provenance types:

- `EXPLICIT_MODEL_VISIBLE`;
- `DERIVED_FROM_MODEL_VISIBLE`.

For derived expectations, deterministic structure/reference validation is kept
separate from human semantic approval.

The diagnostic run at revision
`db34c992d12afbe838431efde7428e89912941b4` produced:

```text
minimum-8-stable-replicas:      PASS
verify-stable-before-shift:     PASS
verify-recovery-before-remove:  FAIL — HUMAN_REVIEW_REJECTED
aggregate gate:                 FAIL
undeclared mappings:            []
```

The aggregate `FAIL` is the intended result for the historical BC-003 diagnostic
bundle. The gate correctly blocks a material evaluator expectation whose claimed
derivation was rejected by human semantic review.

## Human semantic decisions preserved

### Verify 8 stable replicas before complete shift

Disposition:

`APPROVED`

The model-visible basis established that capacity was defined for healthy stable
replicas and that 8 stable replicas were the minimum compliant capacity/N-1
state. The derived requirement to verify the newly scaled replicas healthy
before relying on that 8-replica state was accepted as a defensible derivation.

### Verify service recovery before candidate removal / rollback

Disposition:

`REJECTED`

The historical BC-003 visible context did not establish a sufficiently explicit
post-shift recovery contract or a reviewed derivation supporting the exact
sequence:

```text
traffic shift
→ verify service recovery
→ only then remove / roll back the degraded candidate
```

The expectation therefore must not be treated as authoritative evaluation truth
for BC-003 merely because it appeared in the hidden evaluator.

## Why BC-004 is considered successful

BC-004 is not a test whose success requires the historical diagnostic bundle to
produce aggregate `PASS`.

Its purpose is to distinguish traceable criteria from unsupported or unresolved
criteria before they affect a measured semantic disposition.

The diagnostic aggregate `FAIL` demonstrates the desired fail-closed behavior:

```text
structurally valid refs
+ rejected semantic derivation
≠ approved evaluator criterion
```

That is the control BC-003 lacked prospectively.

## Preserved boundaries

BC-004 does not:

- reinterpret BC-003 as a clean PASS or FAIL;
- modify BC-003 model-visible fixture, hidden evaluator, evidence or measured
  outputs;
- perform or authorize operational actions;
- add model authority;
- automate semantic correctness judgments;
- implement GitHub reviewer enforcement or CI unlocking for measured jobs.

BC-003 therefore remains an immutable historical experiment with canonical
model-quality disposition:

`INCONCLUSIVE — EVALUATION_DESIGN_CONFOUNDER`

## Verification

Before the diagnostic run, local AI Station verification at the evaluated
revision reported:

- `ruff check .` — PASS;
- `pytest` — `189 passed in 6.82s`;
- `git diff --check main...HEAD --` — PASS;
- clean working tree before the diagnostic run.

A final repository verification is still required after closure documentation is
integrated into the feature branch and before pull-request integration.

## Project decision

Use the Evaluation Traceability Gate as the required design boundary for future
measured semantic evaluations where material evaluator expectations can affect
model-quality disposition.

A material expectation may be admitted only when:

1. its mapping exists;
2. its declared model-visible references resolve exactly;
3. its structural contract is valid; and
4. if derived, human semantic review is explicitly `APPROVED`.

`PENDING`, `REJECTED`, missing, unknown or ambiguous provenance must block the
criterion from being treated as approved measurement truth.

## Deferred follow-up

Do not add GitHub approval automation or measured-job unlocking inside BC-004.
Those mechanisms may be considered in a later bounded change if the manual gate
proves cumbersome or insufficient.

The next product/runtime validation block should now be selected separately; it
should not be coupled to closure of this evaluation-governance change.

## Supporting artifacts

Factual diagnostic evidence:

`reports/bc-004-evaluation-traceability-gate-evidence.md`

Normative specification:

`specs/bounded-changes/bc-004-evaluation-traceability-gate.md`

Traceability contract:

`schemas/evaluation-traceability.schema.json`

Diagnostic mapping bundle:

`evals/traceability/bc-003/s12/traceability.json`
