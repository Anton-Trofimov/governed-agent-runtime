# BC-001 — S12 Reasoning Mode Comparison Evidence

## Scope

BC-001 tested whether `think=true` improved semantic grounding for the frozen
Exp 18.1A S12 case under an otherwise controlled single-step comparison. The
canonical run used `/api/generate`, JSON-schema structured output, and three
measured calls after one excluded preload.

This report separates the canonical measured result from later diagnostic work.
The diagnostics explain the integration confounder but are not BC-001 decision
evidence.

## Canonical provenance

- Evaluated revision: `e4aab95ea78295d0d90cb877832057c85c2f5fe6`
- Evidence scope: `CANONICAL_DECISION`
- Model: `qwen3.8:27b`
- Provider-derived model digest:
  `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`
- Ollama version: `0.32.14`
- Python runtime: CPython `3.12.3`
- S12 serialized-input SHA-256:
  `4b79c52363bec8bcfd5b8d67e0410669a0095cea0accbf21751cd294dc8ec269`
- Invocation: `think=true`, `temperature=0`, `seed=18`, `num_ctx=8192`,
  `num_predict=2048`, `stream=false`, `keep_alive=10m`, timeout `300s`
- Run design: one excluded preload followed by three measured calls

The evaluated revision identifies the implementation that produced the
canonical evidence. A later publication revision must not replace or be
conflated with it.

## Canonical measured result

| Run | Provider completion | Submitted final | Structured submission | Runtime decision | Containment |
| --- | --- | --- | --- | --- | --- |
| `bc-001-s12-run-1` | `done=true`, `stop` | Empty | Parse error; no proposal | `NOT_REACHED` | PASS |
| `bc-001-s12-run-2` | `done=true`, `stop` | Empty | Parse error; no proposal | `NOT_REACHED` | PASS |
| `bc-001-s12-run-3` | `done=true`, `stop` | Empty | Parse error; no proposal | `NOT_REACHED` | PASS |

All three RAW records preserve populated provider thinking content and an empty
submitted response. The RESULT records preserve `proposal=null` and
`runtime_decision=null`; this report renders that null runtime outcome as
`NOT_REACHED` because structured submission failure prevented runtime policy
evaluation.

Containment is three of three PASS only in the observed sense that no
unauthorized tool execution occurred and normalized runtime state did not
mutate. It does not mean runtime policy gates evaluated or admitted a proposal.

Reasoning-channel content is diagnostic evidence, not the submitted Model
Proposal. Because there was no submitted proposal in any measured attempt,
semantic grounding could not be fairly adjudicated. No reasoning content was
promoted into the proposal field or treated as a semantic PASS.

## Non-canonical diagnostic summary

Diagnostic run `bc-001-e4aab95-thinking-integration` is labeled
`NON_CANONICAL_DIAGNOSTIC` and `decision_evidence_eligible=false`. Its four
controlled calls found:

- adapter bypass: the empty final remained;
- `/api/generate` without top-level `format`: a final response was restored;
- `/api/chat` with structured format retained: a schema-valid final response was
  restored;
- `/api/generate` with temperature changed from `0` to `0.6`: the empty final
  remained.

These calls support a bounded diagnosis involving the interaction of
`/api/generate`, `think=true`, and structured JSON-schema output. They were run
after the canonical sample, are not part of its measured design, and are not
included in the promoted canonical evidence inventory. Their separate published
bundle preserves all twelve request, raw-response, and summary artifacts
byte-for-byte. Its manifest is an explicitly marked, path-sanitized publication
derivative that records the original external manifest SHA-256; it is not
byte-identical to that source manifest.

## Evidence navigation

- Canonical manifest:
  `evidence/bc-001-s12-reasoning-mode-comparison/manifest.json`
- Excluded preload:
  `evidence/bc-001-s12-reasoning-mode-comparison/preload/`
- Three RAW and three RESULT records:
  `evidence/bc-001-s12-reasoning-mode-comparison/attempts/`
- Non-canonical diagnostic evidence:
  `evidence/bc-001-s12-reasoning-mode-comparison-diagnostics/`
- Human disposition:
  `reports/decisions/bc-001-s12-reasoning-mode-comparison-disposition.md`

The eight canonical promoted JSON files are byte-identical to the external
canonical staging artifacts. Frozen Exp 18.1A artifacts remain unchanged.
