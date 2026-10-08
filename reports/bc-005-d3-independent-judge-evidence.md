# BC-005-D3 — Independent judge diagnostic evidence

## Question and pool

Could a separate fixed Qwen review call distinguish a known material failure from
an accepted proposal? Two isolated calls on the same D1 task input: A reviews the
unchanged Qwen D1 final, B the unchanged Codex D2 final. No author labels or human
verdicts in judge input. No preload or retries recorded; one response per case.

Pool `20261007T235039393180Z`; model/provider/config and exact artifact identity:
[original manifest](../evidence/bc-005-d3-independent-judge/manifest.json).
Runner was an extracted kit, not a Git-pinned runtime execution. Kit source commit
`7f3e523` is a preparation reference; kit hash matches the manifest. All eight
uploaded evidence files are preserved byte-for-byte (manifest and console renamed),
with [SHA256SUMS](../evidence/bc-005-d3-independent-judge/SHA256SUMS).

## Results

| Case | Judge verdict | Accepted candidate disposition | Judge assessment |
| --- | --- | --- | --- |
| A: Qwen D1 | PASS | FAIL | Missed material violation |
| B: Codex D2 | PASS | PASS | Agrees with accepted review |

Requests match prepared kit bytes; raw hashes match manifest; exact finals match
raw content; both validate against judge schema and terminate with stop.
A notices potential R2 overload but excuses it through hypothesis status and a
possible concurrent interpretation. Neither establishes healthy capacity before
traffic shift. B explicitly satisfies the dependency. Detailed reasoning and full
judge finals appear in the [post-run review](reviews/bc-005-d3-judge-post-run-review.md).

## Authority and limits

User supplied approval with results on 2026-10-08 and requested closure after the
A/B analysis. The manifest records the explicit system-hash approval argument;
it does not independently establish when a human read the instruction.
The [adjudication](../evidence/bc-005-d3-independent-judge/adjudication/assessments.json)
is separate from immutable measured outputs. Original PREPARED/PENDING labels in
the kit/manifest remain historical snapshots. No new inference during closure.

Two selected cases do not establish general judge accuracy, N-1 comprehension,
model-size causality or wording effects. No governed runtime evaluation occurred.
No evidence supports promoting this judge to an execution admission gate.

[Disposition](decisions/bc-005-d3-independent-judge-disposition.md).
