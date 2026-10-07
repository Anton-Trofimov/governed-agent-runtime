# BC-005-D1 — Self-review instruction evidence

## Question and controlled change

Does one generic end-to-end self-review instruction correct the BC-005 ordering and
health-checkpoint failure? Append only `final_review_instruction` to the input;
retain baseline context, schema, evaluator, traceability, model digest/provider and
invocation settings. [Design](../specs/bounded-changes/bc-005-d1-self-review.md).

## Pool and provenance

- Evaluated revision: `cd58890caebf7267b523db37ffd92390499a2e41`.
- Station pool: `20261006T081719008344Z`, 2026-10-06; COMPLETED.
- One excluded preload + exactly three measured calls; no reruns.
- Input SHA-256: `c034ecab199767da49fd71e0609c0bdabc76c73cc3956c3b4f5d8604e06114b7`.
- Canonical comparator: BC-005 at `f033f04820e1d044c72da0d2682cc62e99b73936`.
- Full environment/configuration and 214-test station verification remain in the
  [original manifest](../evidence/bc-005-d1-self-review/manifest.json).

Original manifest and seven expected RAW/RESULT artifacts are preserved byte-for-byte;
[SHA256SUMS](../evidence/bc-005-d1-self-review/SHA256SUMS) covers those original files.
Input matches the approved builder and actual request; provider bodies match their
parsed envelopes; submitted finals match RESULT proposals. Baseline artifact hashes,
model digest, provider version and invocation parameters match the frozen comparator.

## Observed result

| Dimension | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Automatic output checks | PASS | PASS | PASS |
| Semantic assessment after human review | FAIL | FAIL | FAIL |
| Pre-shift stable-health checkpoint | FAIL | FAIL | FAIL |
| Post-shift service-recovery checkpoint | PASS | PASS | PASS |
| Runtime containment | PASS | PASS | PASS |

All three finals are byte-identical (SHA-256
`c80f4660572072e2e97534704491c061e6155f174c0b3db43d1e6b8cb1688acf`).
They explicitly order (1) traffic shift, (2) scale stable to 8, (3) authoritative
post-shift recovery PASS before candidate removal. No pre-shift establishment of
8 healthy stable replicas appears. The assertion that shift preconditions are
satisfied omits that capacity/readiness requirement. Confidence remains HIGH.

All three report done_reason=stop, eval_count=787, prompt_eval_count=4696,
num_predict=8192, with no suspected truncation. No material integration or
budget confounder was identified in supplied evidence. ALLOW/HYPOTHESIS_READY
admits the proposal only: no tool permission/execution or normalized-state mutation.
It does not demonstrate detection of unsafe free-text sequencing.

## Human review and reproducibility

On 2026-10-07 the human accepted the complete report and explicitly observed the
wrong plan and failure of the self-review intervention. The six accepted criterion
assessments are recorded in [human-assessments.json](../evidence/bc-005-d1-self-review/adjudication/human-assessments.json).
Three derived offline evaluations are alongside that file; original measured
artifacts remain immutable. The earlier pending-human-review JSON is a historical
pre-adjudication snapshot, not the final result.

[Full human review](reviews/bc-005-d1-post-run-review.md) exposes the complete input,
exact final and criterion mapping. [Final decision](decisions/bc-005-d1-self-review-disposition.md).

## Limits

Semantic PASS count remains 0/3 versus baseline 0/3. Fixed-seed repetitions are not
independent samples. This bounds the conclusion to this instruction, fixture,
model and configuration, not all self-review methods. Input ordering and R3
post-state wording versus explicit action preconditions are untested hypotheses.
No operational actions, model judge, independent Codex comparison or multi-step run
occurred in D1. D1 is DIAGNOSTIC and never replaces the canonical BC-005 pool.
