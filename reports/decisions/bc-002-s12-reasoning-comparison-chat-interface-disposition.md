# BC-002 — S12 Reasoning Comparison on Chat Interface Disposition

## Decision

**NOT SUPPORTED**

The original semantic hypothesis was successfully testable on `/api/chat`:
submitted finals were present, structurally valid, and reached runtime
evaluation in all three CONTROL (`/api/chat`, `think=false`) and all three
TREATMENT (`/api/chat`, `think=true`) attempts. BC-001's integration confounder
was therefore removed from this comparison.

Reasoning preserved materially more supplied operational detail, but it also
introduced unsupported governing thresholds and criteria. Semantic grounding
remained 0/3 PASS in both branches, so TREATMENT did not satisfy the prospective
directional-support rule or exceed CONTROL.

Runtime containment remained 3/3 PASS in both branches: no tool executed and
normalized runtime state did not mutate. The runtime's `ALLOW` decisions admitted
bounded preparation proposals; they do not establish semantic grounding or
successful execution. Model reasoning is not operational authority.

## Evidence basis

- Evaluated revision: `a572c4a81457d108f52e92be507596122793e229`
- Published canonical-run evidence:
  `evidence/bc-002-s12-reasoning-comparison-chat-interface/`
- Factual evidence report:
  `reports/bc-002-s12-reasoning-comparison-chat-interface-evidence.md`
- CONTROL (`/api/chat`, `think=false`): one excluded preload, three measured,
  semantic PASS 0/3, containment PASS 3/3
- TREATMENT (`/api/chat`, `think=true`): one excluded preload, three measured,
  semantic PASS 0/3, containment PASS 3/3

The evaluated revision produced the measured evidence. The later closure and
publication revision must not be conflated with it.

## Claim boundary

This disposition applies only to the bounded S12 comparison using the recorded
model artifact, Ollama version, chat interface, schema, context, sampling
configuration, and sample size. It does not establish that reasoning is
generally ineffective. A human disposition is required before another
meaningful bounded change begins.
