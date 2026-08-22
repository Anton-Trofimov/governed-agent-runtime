# BC-001 — S12 Reasoning Mode Comparison Disposition

## Decision

**INCONCLUSIVE DUE TO INTEGRATION CONFOUNDER**

In the canonical BC-001 configuration, all three measured `/api/generate` calls
with `think=true` and JSON-schema structured output returned populated reasoning
content but an empty submitted-final response. No submitted Model Proposal
was successfully parsed or reached runtime evaluation; runtime decision is
therefore `NOT_REACHED`.

Runtime containment is three of three PASS only because no unauthorized tool
execution or normalized-state mutation occurred. It does not imply that runtime
policy gates evaluated or admitted a proposal. Semantic grounding could not be
fairly adjudicated from submitted proposals.

## Limitation and bounded diagnosis

Separate non-canonical diagnostics identify the strongest bounded explanation as
an interaction involving `/api/generate`, reasoning mode, and structured
JSON-schema output. Those diagnostics explain the confounder but are not BC-001
decision evidence. Their separately published `NON_CANONICAL_DIAGNOSTIC` bundle
is available at
`evidence/bc-001-s12-reasoning-mode-comparison-diagnostics/`.

BC-001 therefore does not support a conclusion about whether `think=true`
improves semantic grounding. It also does not establish that Qwen reasoning,
Ollama generally, or structured output generally is broken.

## Evidence basis

- Evaluated revision: `e4aab95ea78295d0d90cb877832057c85c2f5fe6`
- Canonical source evidence:
  `evidence/bc-001-s12-reasoning-mode-comparison/`
- Factual evidence report:
  `reports/bc-001-s12-reasoning-mode-comparison-evidence.md`
- Non-canonical diagnostic evidence:
  `evidence/bc-001-s12-reasoning-mode-comparison-diagnostics/`
- Measured calls: three
- Structured submission: zero of three successful
- Runtime decision reached: zero of three
- Unauthorized tool executions: zero
- Normalized-state mutations: zero

The evaluated revision is the revision that produced the measured evidence. A
later closure or promotion revision is separate publication provenance.

## Next bounded change

BC-002 establishes a new `/api/chat` control and treatment comparison so the
semantic question can be evaluated on an interface that exposes a submitted
final response. BC-002 is prospective and must not reinterpret, replace, or add
decision evidence to BC-001.
