# BC-004 — Evaluation Traceability Gate Evidence

## Scope

BC-004 implements a bounded evaluation/development-harness gate that requires
material semantic evaluator expectations to be traceable to the exact
model-visible basis used for measurement.

The gate does not infer semantic provenance. It validates an explicitly authored
mapping and preserves a human review boundary for derived semantic expectations.

BC-004 does not change runtime authorization, state transitions, tool execution,
confirmation, or model authority. It also does not rewrite or rerun BC-003.

## Evaluated revision

The diagnostic run was executed on AI Station from exact revision:

`db34c992d12afbe838431efde7428e89912941b4`

Branch:

`bc-004-evaluation-traceability-gate`

The branch was synchronized with `origin/bc-004-evaluation-traceability-gate`
and the working tree was clean before the diagnostic run.

## Pre-diagnostic verification

Local verification at the evaluated revision reported:

- `ruff check .` — PASS
- `pytest` — PASS
- pytest result — `189 passed in 6.82s`
- `git diff --check main...HEAD --` — PASS
- working tree — clean before the diagnostic run

The 189-test regression suite includes the 10 focused BC-004 traceability tests.
No measured model calls were required or performed for BC-004.

## Diagnostic inputs

Traceability bundle:

`evals/traceability/bc-003/s12/traceability.json`

Historical model-visible context:

`fixtures/model-context/bc-003/s12/context-package.json`

The BC-003 artifacts are referenced read-only as a diagnostic case. Their
historical measured evidence, evaluator truth and canonical disposition remain
unchanged.

## Diagnostic result

The deterministic traceability gate returned:

```text
BC-004 Evaluation Traceability Gate — diagnostic run
revision: db34c992d12afbe838431efde7428e89912941b4
case: bc-003-s12-first-step

minimum-8-stable-replicas: PASS
  resolved refs: 3
verify-stable-before-shift: PASS
  resolved refs: 5
verify-recovery-before-remove: FAIL
  resolved refs: 3
  reasons: HUMAN_REVIEW_REJECTED

aggregate gate: FAIL
undeclared mappings: []
```

## Interpretation

The aggregate `FAIL` is the expected successful diagnostic outcome for this
historical bundle.

The gate is intentionally fail-closed: one material expectation is blocked
because the recorded human semantic review rejected the claimed derivation from
the BC-003 visible basis.

The three diagnostic expectations demonstrate distinct provenance outcomes:

1. `minimum-8-stable-replicas` — direct explicit visible basis; exact refs
   resolve and the expectation passes.
2. `verify-stable-before-shift` — derived visible basis; exact refs resolve and
   the recorded human disposition is `APPROVED`, so the expectation passes.
3. `verify-recovery-before-remove` — exact refs resolve, but the recorded human
   disposition is `REJECTED`, so the expectation fails and blocks the aggregate
   gate.

This result is evidence that structural/reference validity does not silently
become semantic approval.

## What the result demonstrates

BC-004 demonstrates, for the implemented v1 boundary, that the harness can:

- require a mapping for material evaluator expectations;
- resolve declared model-visible references by exact canonical ID;
- expose the exact referenced records for review;
- reject missing or ambiguous references;
- require non-empty derivation metadata for derived expectations;
- require an explicit human review disposition for derived expectations;
- block `PENDING` and `REJECTED` derived expectations;
- keep semantic approval outside deterministic inference;
- reproduce the known BC-003 evaluation-design problem without altering BC-003.

## Post-documentation closure verification

After the evidence and disposition documents were added to the feature branch,
AI Station repeated repository verification on the synchronized branch:

- `ruff check .` — PASS;
- `pytest` — PASS;
- pytest result — `189 passed in 6.91s`;
- `git diff --check main...HEAD --` — PASS;
- `git status` — branch up to date with origin, nothing to commit, working tree clean.

This is the final local closure verification for the documented BC-004 branch
before pull-request integration. GitHub pull-request CI remains an independent
integration check and is not part of the diagnostic result above.

## Claims boundary

The result does not establish that the harness can automatically determine
whether a semantic derivation is correct.

It does not use keyword matching, embeddings, fuzzy matching, an LLM judge, or
another semantic inference mechanism as authoritative provenance validation.

It also does not establish GitHub reviewer enforcement or CI-based measured-job
unlocking. Those mechanisms remain outside BC-004 v1.

## Supporting artifacts

Normative bounded-change specification:

`specs/bounded-changes/bc-004-evaluation-traceability-gate.md`

Machine-readable contract:

`schemas/evaluation-traceability.schema.json`

Implementation:

`src/governed_agent_runtime/evaluation_traceability.py`

Focused tests:

`tests/unit/test_evaluation_traceability.py`

Historical diagnostic mapping bundle:

`evals/traceability/bc-003/s12/traceability.json`
