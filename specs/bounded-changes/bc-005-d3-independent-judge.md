# BC-005-D3 — independent Qwen reviewer diagnostic

Status: PREPARED / PENDING HUMAN PRE-RUN REVIEW. No measured calls.

## Bounded question

Can a separate Qwen reviewer distinguish the known D1 ordering failure from the
accepted D2 answer, with evidence-grounded reasons and without author/label hints?
This is a two-example exploratory diagnostic, not a judge reliability benchmark.
BC-006 design remains separate and is not implemented by this work.

## Exact design

Use the same exact D1 scenario input for both cases, including its final self-review
instruction. A is the unchanged Qwen D1 run-1 final; B is the unchanged Codex D2 final.
Both originals were generated from those scenario-input bytes. Each judge request
has the same new system reviewer instruction, user-data structure and judge output
schema. Only candidate_response differs. No prior response or chat history carries
between calls. Labels, author names and human verdicts are absent from model input.

Use D1 model digest and invocation options, explicit think=true, stream=false,
keep_alive=10m and a 300-second request timeout. Pin Ollama version 0.32.14.
Exactly two inference requests maximum, A then B, no preload and no automatic retries.
No sampling/prompt changes after viewing results. Cold/warm latency is not compared.
Full requests and raw responses are preserved before derived output validation.

## Review and disposition

The [pre-run sheet](../../reports/reviews/bc-005-d3-judge-pre-run-review.md) exposes
all system instructions, response schema, exact requests, provenance, commands and
interpretation criteria. Human acceptance of that instruction is required before run.
The runner requires its SHA-256 as an explicit approval argument; this mechanism
records user assertion, not independent proof of who reviewed it.

A positive diagnostic observation requires A FAIL with a supported explanation of
the pre-shift dependency failure, and B PASS without invented violations. Human
review checks reasons, not just verdict strings. Other supported findings require
adjudication. Invalid/truncated output and provider failures are recorded separately.
No outcome authorizes operational execution or establishes general judge accuracy.
No frozen BC-005/D1/D2 artifact is changed.
