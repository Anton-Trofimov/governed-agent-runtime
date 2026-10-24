# BC-011 — local live UI/runtime disposition

2026-10-24 (Europe/Moscow). Implementation accepted by the owner: public revision
02ca89472ad371b216640a6ff79800bad5a9f7c8.

**Decision: ACCEPTED for bounded local integration, with the limitations below.**
The owner accepted the working UI and requested concise documentary closure and
PR/merge before continuing the separately drafted initial-dialogue change.

## Result and verification

- Local React UI and loopback backend connect pinned Ollama inference to the
  modeled payment-api runtime. Initial state, proposals, checks, action-bound
  confirmations, operator decisions and outcome are inspectable.
- Automated baseline: 337 Python and 63 UI tests; Ruff, TypeScript/Vite build,
  deterministic recorded-data export and diff checks PASS. Tests cover ownership,
  idempotency, deadlines, refusal, cooperative stop, read-only restoration and
  unknown provider completion; automated tests use fake providers, not real LLMs.
- Owner-run station smokes observed real inference, nominal completion, explicit
  refusal and confirmation expiry. Desktop/mobile UI was accepted after iterative
  review. These are owner-reported integration observations across successive
  revisions, not a controlled quality benchmark or a complete test matrix at the
  final revision.
- Full station evidence remains private and has not been comprehensively reviewed.
  No aggregated real-call success rate, universal model reliability, production
  readiness or measured financial/productivity ROI is claimed.

## Material limits and next boundary

Arbitrary initial text still becomes a recovery goal: a capabilities question can
lead to an action proposal. Intent routing remains separate future work; existing
execution/confirmation gates are retained, not presented as proof of semantic
understanding. Free dialogue during execution is not supported.

One active local slot and two preparation attempts per approved package remain.
A session is not verified user identity; the local coordinator does not exclude
unrelated direct Ollama clients. Public access, station exposure, abuse protection,
GPU arbitration and restart/network acceptance require a separately agreed design
and verification. No deployment is authorized by this closure.

The deliverable's public value is an inspectable local interactive integration
with visible authority boundaries. Further cosmetic iteration and accessibility
audit are deferred. BC-012 design can resume after BC-011 integration; it is not
part of this delivery. [PR #12](https://github.com/Anton-Trofimov/governed-agent-runtime/pull/12) records CI and merge status.
