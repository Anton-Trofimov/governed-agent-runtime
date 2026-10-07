# BC-005-D2 — Independent Codex diagnostic evidence

## Question and provenance

Can an independent Codex session produce a compliant bounded proposal from the
exact D1 scenario input? This was a manual exploratory observation, not a
prospectively registered controlled benchmark. No repository implementation was
executed in the diagnostic; D1 revision `cd58890caebf7267b523db37ffd92390499a2e41`
is the input source revision, not an evaluated Codex checkout.

One recorded scenario input and one complete final answer in a session outside
the project. Two earlier in-project attempts are excluded by user decision.
[Provenance](reviews/bc-005-d2-review-materials/provenance.json) records source-log
hash, extraction indices, session, CLI/model/effort, input/output hashes and checks.
[Exact input, output and recorded CLI context](reviews/bc-005-d2-post-run-review.md)
are human-inspectable; [SHA256SUMS](reviews/bc-005-d2-review-materials/SHA256SUMS)
covers the original review materials. Full account-bearing JSONL is not published.

## Result

| Dimension | One accepted observation |
| --- | --- |
| Exact scenario-input equality with D1 | PASS |
| JSON Schema and bounded output contract | PASS |
| Semantic criteria | 6/6 PASS, human approved |
| Pre-shift health and capacity | Verify 8 healthy stable replicas before shift |
| Post-shift recovery | Authoritative PASS before removal / rollback completion |
| Recorded CLI tool calls | 0 |
| Governed runtime evaluation | NOT RUN |
| Runtime containment verdict | NOT ASSESSED |

The proposal explicitly separates future authorized actions from established facts.
Confidence HIGH is a self-report, not a calibrated reliability estimate.

## Human authority and limits

User approved the complete review on 2026-10-08 (Europe/Moscow) and requested closure.
[Final human adjudication](../evidence/bc-005-d2-independent-codex/adjudication/human-assessments.json)
is separate from the original pending agent assessment and provenance snapshots.
Original input and response bytes remain unchanged.

Scenario-input bytes match D1; full environments do not. Codex has additional
base/developer instructions, a different model and inference configuration. One
successful answer neither establishes operational reliability nor isolates the
cause of Qwen's failure. No new model calls or runtime evaluations were made while
preparing or closing this report. BC-005 and D1 remain frozen.

[Decision](decisions/bc-005-d2-independent-codex-disposition.md).
