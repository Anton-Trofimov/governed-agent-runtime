# Preset input and paired local entries — closure record

2026-10-28. Implementation branch: `preset-only-input`.
Owner station revision: `db7e36e8f480661c922cba23c28c534cef6dd55e`.
Local verification revision: `d248c86` (local implementation history; remote
history contains separate file-upload commits). PR integration is not implied.

## Scope and review

Closure is prepared for bounded local use. Review covered server-selected input
profiles, transport schemas, session ownership, shared admission control,
persistence, launcher approval binding and UI availability feedback against the
[transport contract](../../specs/core/live-ui-runtime-contract.md).

- Visitor entry accepts four server-owned choice IDs; arbitrary text/extra fields
  are rejected before inference. Informational choices cannot admit remediation.
  Answered informational choices disappear; the preset dialogue has four calls.
- Owner entry retains free text and five initial calls. Both entries share one
  execution slot, provider coordination and the approved preparation budget.
  Session ownership is scoped to the listener; cookies are separate.
- Owner control pauses new visitor preparations without interrupting admitted
  work. First startup enables access; manual setting persists atomically.
  Availability is restored from the server after reload.
- Paired Ollama approval binds both listener roles and profiles. Existing
  revision/profile checks, single-use approval, quarantine and two-preparation
  package limit remain. These are loopback entries, not public hosting.

## Automated verification

Local verification: 386 Python tests and 78 UI tests PASS; Ruff, TypeScript/Vite
build, recorded-data export check and diff checks PASS. Python emitted one
Starlette TestClient/httpx deprecation warning. No real inference was initiated
by these checks. Contract tests cover profile rejection, cross-entry ownership,
shared admission, persistence/error handling and approval topology mismatch.
CI results are tracked on the PR for its final head revision.

## Owner-observed station checks

Pinned profile: `BC012-local-ollama-v1`, `qwen3.8:27b`, Ollama `0.32.14`.
These findings derive from supplied transcripts/screenshots and owner reports;
private raw station evidence was not independently audited. They are not a
controlled benchmark or an aggregate success-rate estimate.

- Visitor preset run: three explanatory requests followed by explicit recovery;
  scale to eight, observe readiness, shift traffic, observe recovery PASS,
  finalize rollback and final read. Three separate approvals. Supplied final
  report shows COMPLETED, eight stable Ready replicas serving 820 RPS and zero
  candidate replicas/traffic.
- Owner free-text run: unrelated currency question redirected to scenario scope;
  discussion alone did not start recovery. Explicit recovery led through the
  normal proposals and three approvals. Supplied excerpt ends at final approval;
  final COMPLETED report for this particular run was not supplied.
- Second owner run: explicit non-execution request produced explanation; later
  explicit recovery proposed scaling. Rejection of that first change ended in
  SAFE_FALLBACK / CONFIRMATION_REJECTED with original service state retained.
- Exhaustion of the shared two-preparation package was visible on both entries.
  A previously timed-out preparation also consumed a package admission.
- Admission switching was previously reported working with the simulator. Manual
  switching with Ollama was not repeated in these runs and remains unverified.

## Known limitations in model explanations

Free-form prose contains factual errors even when the subsequent action path is
correct. Representative observed errors:

- N-1 calculation stated `820 / 5 = 170`; the correct value is **164 RPS**.
- An answer associated stable traffic with 820 RPS, although current stable
  traffic was 615 RPS; a later table correctly listed 615 RPS.
- An explanation treated projected full-transfer load as current load. At 615
  RPS on six stable replicas, normal utilization is 68.3% and N-1 is 82.0%.
  For projected 820 RPS those values are 91.1% and 109.3%. These are different
  questions and must not be conflated.

Execution proposals in the supplied sequences used the correct full-transfer
capacity requirement and required readiness/recovery observations. This does
not mean runtime corrected or certified the earlier prose. Runtime governs
action admissibility and execution; factual accuracy and semantic intent
understanding in unrestricted dialogue remain model limitations.

Presentation limitations also remain: Markdown syntax can appear literally in
chat, and executor explanations may be English. No wording/rendering changes
or model/prompt changes are included in this closure.

## Remaining boundary

No internet deployment, public owner authentication, visitor abuse controls or
production payment infrastructure integration is established. Owner control
assumes trusted local access. Real LLM inference still operates on a synthetic
service/tool environment. Shared package limits are local smoke limits, not a
production per-user quota. No additional adverse prompt was added. A future
necessary station check can include admission switching with Ollama; this
record does not authorize another inference package or merge.
