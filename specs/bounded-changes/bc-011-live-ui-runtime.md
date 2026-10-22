# BC-011 — local live UI/runtime interaction

Local implementation authorized by human, 2026-10-21, with deterministic model
simulation only. Real model calls and station/public deployment remain separately
gated. The offline server must identify the simulator and provide no real-provider
activation path; this approval does not authorize inference.

## Goal and baseline

Run the existing modeled payment-api recovery through the accepted UI with real
LLM inference, explicit operator decisions and live observed state. One local
operator, one active run, one backend process. Recorded examples remain independent.
Base: merged `5eaae4ba101e78d1e98d753607f2e1f994bcf338` (BC-009 PR #10, BC-010 PR #11).

Material dependencies:

- BC-006 runtime and `core/bounded-remediation.yaml`: admission, state, budgets,
  tool execution and terminal outcomes remain authoritative.
- `core/confirmation-contract.yaml`, explicit bounded-remediation profile:
  action-bound consent, revalidation, invalidation and single consumption.
- BC-009 view v1 / runner output contract: compatible final outcomes and sources.
- BC-010 UI/replay v2: retain recorded mode; live events need a separately versioned
  transport envelope, not fabricated replay records or mutations of old evidence.
- BC-008 goals supply the two initial suggestions, not new evaluation approval.

## Observed gaps at baseline

`bc006_runner.run_live` is a measured-experiment runner: revision/packet approval,
fixed cases/provider identity and repository verification precede model calls.
It is not an HTTP request handler. Preserve those entry points and safeguards.
`RemediationRuntime.submit` blocks in `confirm(request)`. False means rejection;
expiry is checked only after a true response returns. Add an explicit typed
confirmation result/timeout boundary while preserving existing CLI behavior.
Runtime accepts predefined BC-008 goal variants, not an arbitrary browser goal.
Add an explicit bounded operator-goal input; never let it replace policy, role,
target, tool allowlist, model configuration or instructions owned by runtime.
No browser session, transport, idempotency or cooperative stop currently exists.

## Proposed architecture and scope

React UI → same-origin Python HTTP adapter → one serialized run worker → existing
runtime and configured Ollama adapter. Request threads never mutate runtime state.
Use HTTP commands plus cursor-based polling (~1 second while active) first;
WebSockets, token streaming, task brokers and databases are unnecessary for this slice.
Selected contract design: Starlette with one Uvicorn process and a separate
serialized worker; server dependencies are in the optional `live` extra. Keep backend code under
`src/governed_agent_runtime/`, UI under `ui/`,
shared contracts in `schemas/` and `specs/core/`; no new standalone API project.

Local access only: bind loopback, enforce allowed Host/Origin, accept bounded JSON
commands, use a server-issued local session capability, no permissive CORS. Never
expose Ollama directly or accept browser-supplied provider URLs, paths or roles.
Local same-origin checks and capability handling must be reviewed before first use.
Phone-to-station access, public tokens/accounts/quotas and hosting are deferred.
Do not expose live mode publicly before a separately agreed and verified access,
isolation and resource-abuse protection design. Registration/accounts are not a
prerequisite; a browser session is not verified personal identity. Session/run
ownership must still protect both reads and commands from other sessions.

Future publication may separate frontend hosting from the station while retaining
a same-origin browser API boundary. Public visitors must receive only scoped
modeled-scenario authority, never administrative or arbitrary infrastructure
authority. Provider and administrative services remain private. Public routing,
service recovery after station restart and deployment are separate future work.

The backend atomically reserves one live slot, including model preparation;
session creation alone must not bypass admission or cause duplicate preparation.
Other sessions receive a busy response and can use recorded examples independently.
UI copy: “Живой режим занят. Пока можно посмотреть демонстрационный пример”.
When free, offer an explicit start; never automatically switch modes or start a
waiting visitor's task. No multi-user queue or estimated wait is promised.
Bound abandoned preparation/reservations with a server-owned deadline/release
contract before implementation; do not allow an unused session to hold the slot
indefinitely. Existing run and confirmation deadlines remain authoritative.

Before public access, separately choose start/preparation rate limits, per-run
inference budgets and aggregate station limits. Anonymous session-based limits
are not reliable per-person quotas; new sessions must not defeat global limits.
No public rate limiter or multi-user scheduler is added by this planning update.

## User flow

1. “Начать живой сценарий” first establishes/reuses an idle local session, then
   separately requests admission and model preparation. Bootstrap alone never
   loads a model. Show only observed availability/loading/inference states; no fake
   percentage, VRAM or power data. Health checks never load the model.
2. Show two editable suggestions: “После обновления сервис работает нестабильно.
   Восстанови его работу безопасным способом” and “Восстанови работу сервиса”.
   Accept a non-empty arbitrary initial goal (limit: 2,000 Unicode code points).
   Preserve exact input in new run evidence. Off-topic text may fail the task;
   it never broadens execution authority. One submitted goal creates one run.
3. While preparing, retain one submitted goal bound to the owning session/run:
   “Модель загружается. Запрос принят и будет выполнен после подготовки”. Execute
   it once after successful preparation. This is not a multi-user queue. On
   preparation failure, preserve the text for explicit retry, show the failure
   and never execute it later automatically. Reconnect must not duplicate it.
4. Agent proposals, runtime decisions and accepted observations update their
   corresponding panels. Original rationale stays visible; summaries stay labeled.
5. A pending action shows exact target/change, consequence and server expiry.
   Only explicit Confirm/Reject commands submit consent. Free text during this
   wait produces a short platform instruction, never rejection or a model call.
6. Reject ends the run with operator handoff; it neither undoes earlier effects
   nor claims a fresh observation. Expiry ends distinctly from rejection.
7. “Начать заново” after terminal completion creates a new run and fresh modeled
   environment. No terminal resume. Refresh/reconnect retrieves the existing run;
   it never silently restarts or resets the environment.

## Proposed HTTP boundary

Detailed design draft: [live UI/runtime contract](../core/live-ui-runtime-contract.md).
It defines transport states, ownership, command acknowledgement and release;
open choices there must be resolved before implementation.

Wire schemas: `schemas/bc011-live.schema.json`; session/bootstrap details are
defined in the linked contract. All mutating commands carry a command_id;
authenticated payload mismatch on reuse is rejected.
Same ID/payload returns the stored acknowledgement and never repeats execution.

| Operation | Contract |
|---|---|
| GET /api/status | Backend/provider reachability and observed model status; no loading side effect |
| POST /api/session/bootstrap | Idle cookie session only; no model preparation or slot reservation |
| POST /api/sessions | Authenticated admission and preparation request; no service operation |
| GET /api/session | Own reservation/current run and preparation state |
| POST /api/runs | Session + initial goal + command_id; server creates run ID and fresh environment |
| GET /api/runs/{id} | Authoritative snapshot, cursor, pending decision and terminal outcome |
| GET /api/runs/{id}/events?after=cursor | Ordered event envelope; duplicate-free UI application; bounded pages |
| POST /api/runs/{id}/decisions | command_id + confirmation_id + approve/reject; server owns action binding |
| POST /api/runs/{id}/stop | Idempotent cooperative stop request; acknowledgement is not terminal confirmation |
| POST /api/session/release | Explicit unused-reservation release; active runs require stop |

Proposed live envelope: version, run_id, sequence, timestamp, kind, actor, payload,
source reference when applicable. Snapshot includes its last sequence. Catch-up
must handle events between snapshot and polling without loss or duplication.
Separate delivery cursor from original trace event ID. Do not expose hidden
experimental truth, full provider internals, secrets or arbitrary filesystem paths.
Unknown run/session/expired binding fails closed. A second active run returns a
clear busy response. Retain command results for the lifetime of the run/session.
After server restart old sessions cannot execute commands or resume workers;
preserved artifacts may be inspected read-only. Do not infer a terminal outcome
from a lost process when a write outcome is unknown.

## Confirmation, stop and connection semantics

Runtime owns the existing 300-second confirmation deadline. Browser countdown is
informational. Explicit expiry must unblock the worker without manufacturing an
approval; late or foreign confirmation and a new command reusing consumed consent
are rejected. A duplicate command ID returns its stored acknowledgement without
consuming consent again.
Check expiry and stop request immediately before dispatch under the same serialized
worker boundary. Preserve revalidation and unknown-write-effect handling.

Stop during inference: record the request, wait for the bounded provider call to
return/fail, then discard its proposal; never execute it. No immediate GPU abort
promise. Stop while awaiting consent unblocks that wait with a distinct result.
Stop during an already dispatched operation waits for outcome/verification before
terminal reporting; it does not undo the operation or falsely report cancellation.
A race with completed work must retain the actual completion outcome.

A transient disconnect is delivery failure, not consent/rejection or task failure.
Proposed UI recovery window: 30 seconds, with a stable reconnecting indicator;
after that show disconnected and allow explicit reconnection to the same run.
No automatic resend of writes, no loss of pending action. Server confirmation TTL
continues independently. Idle warning around five minutes must not reset a run or
extend an expiring confirmation; inference/loading is not operator inactivity.

## Evidence and approval boundary

Define a separate local demonstration profile and pre-run approval scope before
real inference; do not reuse or weaken BC-006/008 experiment approvals. Pin the
allowed model/configuration and preserve input, provider identity, timing, actions,
decisions and trace in a unique external run directory. No changes to old evidence.
Repository checks run as a startup/preflight gate, not on every HTTP poll.
A demo run is not automatically accepted experimental evidence or a new benchmark.
Keep complete sensitive run evidence in access-restricted local storage, separate
from curated demonstration results and experimental evidence. Publish only
necessary reviewed/sanitized derivatives under the repository disclosure rules
in `AGENTS.md`; never automatically copy external traces or user goals into Git.

## Acceptance and sequence

1. Agree this boundary; specify typed commands/events/confirmation outcomes and
   startup approval. Decide the minimal HTTP implementation without new hierarchy.
2. Offline tests with deterministic provider: nominal completion; reject; timeout
   without reply; stale/foreign/duplicate consent; stop at each safe boundary;
   ambiguous write; disconnect/cursor recovery; duplicate start; server restart;
   simultaneous clients/busy during preparation and execution; foreign-session
   reads/commands; preparation failure/retry and abandoned-slot release;
   arbitrary text cannot authorize an action.
3. Connect UI and test snapshot/event consistency, decision states, report and
   restart semantics; preserve the two recorded examples and responsive baseline.
4. Run repository and UI gates, then human pre-run review for a bounded station
   smoke. Only after approval run real inference and assess actual behavior.

Out of scope: conversational clarifications mid-run, arbitrary tools/targets,
production operations, persistent worker recovery, multi-user scheduling, remote
publication/security scheme, GPU telemetry, new model-quality experiments and
reusable SDD changes. Do not silently fold these into button wiring.
