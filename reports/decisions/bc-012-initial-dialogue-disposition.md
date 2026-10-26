# BC-012 — initial dialogue and goal admission disposition

2026-10-26 (Europe/Moscow). Owner-reviewed implementation:
`8941d67a45d80b193e3ffd92c8b7ad09a62cc206`, profile `BC012-local-ollama-v1`
(pinned Qwen `qwen3.8:27b`, Ollama `0.32.14`).

**Decision: ACCEPTED for bounded local use, with the limitations below.**
The owner reported both final smokes successful and approved concise closure and
PR preparation. Integration into main is tracked by the PR, not implied here.

## Result and verification

- Up to five initial model calls can answer, clarify or explain scope without
  creating a remediation run. A valid goal proposal references original operator
  messages and hands off to the existing executor; writes still require exact-action
  confirmation. Navigation preserves preparation/dialogue and existing deadlines.
- Offline verification: 366 Python tests, 71 UI tests, Ruff, TypeScript/Vite build,
  recorded-data export and diff checks PASS. Fake-provider tests cover invalid
  outputs/references, duplicate commands, ownership, call/time bounds, cancellation,
  late results and preservation of the execution boundary. They do not assess
  natural-language intent understanding.
- Final owner station check: capacity question followed by explicit recovery,
  five action proposals, three confirmations and runtime-verified COMPLETED;
  a second dialogue respected explicit non-execution and a hypothetical shift,
  ending without remediation. Its explanation correctly distinguished 6/7/8
  replicas under the 90% normal/N-1 rule. Navigation retained the owned scenario;
  another browser displayed the exhausted two-preparation package limit.
- Earlier owner smokes on `b3410eb` observed capability answers, concise handoff,
  a hypothetical/non-action dialogue followed by explicit recovery, and five
  unrelated questions ending at DIALOGUE_LIMIT without execution.

Closure verification exposed a timing race in the existing mobile-scroll test.
It now waits for the React effect before asserting one scroll; subsequent polls
must still leave the count unchanged. No UI behavior or assertion was weakened.

These are owner-provided transcripts/screenshots and reported behavior, not a
controlled benchmark or exhaustive review of private station evidence. No aggregate
real-call success rate or complete semantic acceptance matrix is claimed.

## Engineering findings and limits

Provider schema conversion initially rejected an unsupported pattern. Only the
provider-facing projection omits it; authoritative server validation remains.
A later non-start reply with goal references was rejected, not repaired or retried.
Bounded failure diagnostics remain private; uncertain completion retains quarantine.

The dialogue and executor need different context: capability/state explanation
must not masquerade as an executable plan. Contract-derived capabilities and the
capacity rule improved the observed explanation; the small uncontrolled sample
does not isolate causality or establish general reliability. The model still owns
semantic classification, and a wrong start classification remains possible despite
structural validation. Action confirmations are a separate safeguard.

Minor explanatory inaccuracies remain (for example, wording that could imply a
read-only verification needs confirmation). Do not treat prose as runtime authority.
Exhaustive wording refinement, mobile review of the new composer and stronger
status-text emphasis are deferred, not claimed as completed acceptance.

One active local slot, five dialogue calls, 300-second idle and 600-second absolute
dialogue limits, and two preparations per approved package remain. Public access,
visitor authentication/quotas, abuse protection, GPU arbitration with other clients,
and production recovery require separate design and verification. No deployment
or new inference is authorized by this closure. Raw station evidence stays private.

The public value is inspectable separation of conversation, goal admission and
controlled execution, with an unchanged action-confirmation boundary. No financial
ROI, production readiness or universal model-quality claim is made.
