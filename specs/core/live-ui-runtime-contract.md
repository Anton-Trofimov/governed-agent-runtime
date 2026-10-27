# Local live UI/runtime contract

Contract v0.4 includes the approved BC-012 initial-dialogue extension below.
Local simulator implementation is authorized; real inference and deployment
remain separately gated.
BC-006 execution and confirmation contracts remain authoritative; recorded
BC-010 data and schemas are unchanged. The simulator entry point uses a deterministic provider; the separate Ollama
entry point requires revision/profile-bound approval. Injected providers in tests
exercise failure boundaries without real inference.

## HTTP adapter and session design

Selected design: Starlette HTTP adapter served by one Uvicorn process, without
reload or multiple workers. Route handlers validate and enqueue commands; a
dedicated serialized worker owns the blocking runtime/provider calls. Status,
polling and decisions must stay responsive while that worker waits. Framework
versions are pinned in the `live` optional dependencies. The local entry point
serves the built UI and does not provide a switch to real Ollama.

Use server-side in-memory sessions and an opaque random 256-bit capability in a
host-only cookie: `HttpOnly`, `SameSite=Strict`, `Path=/api`, no Domain attribute.
Do not encode identity, roles, goals or state in the cookie. Do not put capability
values in JSON, JavaScript storage, URLs, traces or logs. Store only their hashes
in the session lookup. For the loopback HTTP profile only, Secure is false;
non-loopback access is rejected, not enabled by changing this flag. A future
HTTPS deployment must review Secure cookies and the complete public boundary.

Require the configured exact Host (including port). All POST routes, including
bootstrap, require the exact same-origin Origin, application/json and
`X-GAR-Request: live.v1`; reject absent/null/foreign Origin. Reject cross-site
Fetch Metadata where present. Do not enable CORS or trust forwarded headers.
The custom header is a request-shape check, not a credential. GET routes are
read-only; private responses use Cache-Control: no-store. Render goals/model
text as text, never executable HTML. This is a local session design, not public
authentication or protection from a malicious process on the same machine.

Bootstrap first establishes an idle session without reserving a slot or touching
the provider. UI serializes bootstrap across same-origin tabs with a browser
Web Lock, probes GET /api/session inside that lock, then bootstraps only if
missing. Wait for its response and verify GET /api/session before enabling start.
If browser locking is unavailable, do not enable live bootstrap in this profile;
recorded mode remains available. Tabs share a session and its run, not separate
operators. An isolated browser profile is a different session.

A lost bootstrap response can leave an idle orphan, never an active run. Retry
under the same lock after probing the cookie; without a usable cookie a new idle
session may be created. Do not deduplicate unauthenticated bootstrap globally by
a client command_id or let that ID recover a capability. Once authenticated,
ordinary command deduplication applies. Unknown/stale cookies cannot authorize
commands; explicit bootstrap replaces them only with a fresh idle session.

Session idle expiry is 60 minutes with no owned reservation or worker; authorized
reads renew that viewing window. While work is owned, session expiry is suspended
and runtime/reservation deadlines govern. After terminal/release, the viewing
window starts anew. Process restart invalidates all capabilities. Bound retained
state to 16 sessions, 8 runs and 512 command records per session; reject excess
with SESSION_CAPACITY/SESSION_LIMIT rather than silently evicting live state or
idempotency records. This is local memory bounding, not public rate limiting.
Check capacity before admitting a new reservation/run; always retain enough
command capacity for its bounded run, including a stop request.

## Ownership and state

The server owns admission, session identity, run identity, command deduplication,
deadlines and runtime authority. The browser renders snapshots/events and submits
bounded commands. It cannot select role, provider, model settings, target or tools.
Session/run IDs are identifiers, not credentials. A server-issued session
capability authenticates access to that session; it does not identify a person.
Both reads and writes require ownership checks. Do not expose another session's
goal, events, pending action or identifiers through availability responses.

Keep these independent fields; a network outage must not rewrite runtime state:

| Field | Values / meaning |
| --- | --- |
| availability | `available`, `busy`, `unavailable`; backend admission status |
| session_state | `open`, `expired`; expired sessions cannot issue commands |
| phase | `preparing`, `ready`, `running`, `awaiting_confirmation`, `stopping`, `terminal` |
| runtime_state | Existing BC-006 state or null before runtime starts |
| model_status | `unknown`, `preparing`, `ready`, `inference`, `unavailable`; observed only |
| connection | UI-local `connected`, `reconnecting`, `disconnected` |

A session may outlive a run to inspect its result and explicitly start anew.
Starting reserves one global slot atomically, including preparation. Preparation
belongs to a reservation; no run exists until a goal is accepted. After acceptance
the server allocates one run ID, stores the exact goal and binds it to the
reservation. A preparation failure before goal acceptance has no runtime outcome.
A failure after acceptance ends that run with a preparation failure, not a
fabricated runtime decision. Retry uses a new command and a new run/reservation;
old pending goals never execute automatically.

When preparation succeeds, a reservation with a goal starts once; one without a
goal becomes `ready`. Other sessions remain able to view recorded examples.
Status polling does not load a model, create a session, reserve a slot or extend
a reservation. Simultaneous starts admit exactly one owner; others receive busy.
An availability notification never automatically starts a waiting visitor.

## Commands and responses

Wire envelope version: `live.v1`. Identifiers are opaque, bounded strings;
timestamps are UTC RFC 3339; cursors are non-negative integers. Reject unknown
command fields, oversized bodies, invalid enums and invalid identifiers before
any side effect. Request bodies never carry credentials, operator roles or paths.
Wire shapes are defined in `schemas/bc011-live.schema.json` (Draft 2020-12).
Resolve references from the repository only, never fetch remote schema URLs.
Validate formats explicitly, including calendar-valid UTC timestamps. HTTP body
limit is 16 KiB before JSON parsing; reject duplicate keys and non-finite numbers.
Responses have a 1 MiB ceiling, events a 64 KiB ceiling; page size is at most
100 events and may be smaller to fit the byte ceiling. Never truncate an original
model explanation silently: fail projection explicitly if its bound is exceeded.

Every POST has `command` and `command_id`; route and command discriminator must
match. Bootstrap has the harmless unauthenticated retry exception above.
For authenticated commands, the idempotency key is session + command_id, across
all command routes. Record canonical method/path/body and acknowledgement under
one serialized admission boundary. Same key and payload returns the original
acknowledgement, including after terminal completion; changed payload is rejected.
Deduplication follows authentication and precedes new execution. Retain records
for the owning session's lifetime. A new session cannot reuse ownership of a run.

| Method / path | Request fields beyond command_id | Result |
| --- | --- | --- |
| GET /api/status | None | version, availability, observed model_status, server_time; no owner details |
| POST /api/session/bootstrap | command=bootstrap | Idle session establishment only; capability in Set-Cookie, never JSON |
| POST /api/sessions | command=prepare | Reserve preparation for the authenticated session; acknowledgement |
| GET /api/session | None | Own reservation/current run IDs and phase, deadlines, preparation error if any |
| POST /api/runs | command=start_run, reservation_id, goal | Acknowledgement with run_id; goal at most 2,000 Unicode code points |
| GET /api/runs/{id} | None | Atomic snapshot and its cursor |
| GET /api/runs/{id}/events | after, optional limit | Ordered events, next_cursor, has_more |
| POST /api/runs/{id}/decisions | command=decide, confirmation_id, decision: approve or reject | Command acknowledgement; never a promise of execution |
| POST /api/runs/{id}/stop | command=stop | Accepted cooperative stop; actual phase/outcome arrives separately |
| POST /api/session/release | command=release, reservation_id | Release unused reservation or request preparation stop; cannot detach an active run |

Idle sessions never start preparation without successful slot admission. Success
acknowledgements include kind=ack, version, command_id, disposition, session_id,
nullable reservation_id/run_id and server_time. Inspect GET /api/session or the
snapshot for current phase/cursor. Errors have kind=error and nullable command_id,
code and a safe human message, never raw exceptions. Schema definitions select
the applicable shape; handlers must not validate a command against an unrelated
response definition just because the root union accepts it.

| HTTP / code | Meaning |
| --- | --- |
| 202 | New asynchronous command accepted; inspect session/run for result |
| 200 | Read or already completed synchronous acknowledgement |
| 400 / INVALID_REQUEST | Invalid command or cursor; no action |
| 401 / SESSION_REQUIRED | Missing/expired session capability; no action |
| 403 / ORIGIN_REJECTED | Host/origin/request-shape checks failed; no side effect |
| 404 / NOT_FOUND | Missing or non-owned run/confirmation; do not reveal which |
| 409 / LIVE_BUSY | Slot unavailable to this session; recorded mode remains available |
| 409 / COMMAND_CONFLICT | Same command_id used for a different command |
| 409 / ACTION_NOT_PENDING | Consumed, superseded or otherwise unavailable action |
| 409 / CONFIRMATION_EXPIRED | Own action expired; no execution |
| 409 / CURSOR_INVALID | Cursor ahead of stream; re-fetch own snapshot |
| 410 / EVENTS_UNAVAILABLE | Requested retained history unavailable; re-fetch own snapshot |
| 413 / REQUEST_TOO_LARGE | Input exceeds declared size limits |
| 503 / LIVE_UNAVAILABLE | Preparation/provider/startup gate unavailable; do not retry mutations automatically |
| 503 / SESSION_CAPACITY | Local retained-session capacity exhausted |
| 409 / SESSION_LIMIT | Session retention/command budget exhausted; no silent history eviction |

Never automatically resend a mutation after an ambiguous transport failure.
Reconcile using the owning session/run; an explicit retry of an unresolved
command must retain its original command_id and payload. This differs from a new
attempt after a known preparation failure, which uses new IDs. A lost response
must not produce a new goal/run or a second confirmation.

## Snapshot and event delivery

Snapshot fields: version, run_id, phase, runtime_state, goal, model_status,
service_view, pending_confirmation or null, stop_requested, terminal or null,
cursor, server_time. Service view is a sanitized projection of accepted
observations, not inferred recovery. Unknown values remain unknown. No old
recorded example may masquerade as current live state.

An event has kind=event, version, run_id, sequence, occurred_at, event_kind, actor, payload and
optional source_ref. Sequence starts at 1 and increases within one run; it is
not a trace event ID. `source_ref` contains only approved logical artifact/event
references, never local paths. Proposed typed payload families:

| event_kind | actor | Payload meaning |
| --- | --- | --- |
| goal_accepted | operator | Exact accepted goal |
| phase_changed | platform | New phase and reason |
| model_status_changed | platform | Observed status; no invented progress |
| proposal_recorded | agent | Validated proposal and original explanation |
| admission_checked | runtime | Stage, result, explained checks and allowed references |
| confirmation_requested | runtime | Pending exact-action confirmation projection |
| operator_decision | operator | Submitted approve/reject and confirmation_id |
| confirmation_resolved | runtime | Accepted/rejected/expired/invalidated/consumed status |
| tool_started | runtime | Tool identity and explained bounded action |
| observation_accepted | runtime | Validated result and resulting service projection |
| stop_requested | operator | Cooperative stop request |
| run_finished | platform | Terminal envelope with runtime outcome when available |

These are transport events; counts need not equal trace.jsonl or recorded-demo
counts. No inferred gate gets an event claiming it actually ran. Polling is
read-only, approximately once per second while active, with bounded pages.
Snapshot projection and cursor are captured atomically; events after that cursor
must include every subsequent update. UI applies only increasing contiguous
sequences, ignores duplicates and resynchronizes on a gap. A stale poll response
cannot overwrite a newer snapshot. Terminal results remain readable for the
session lifetime, without holding the execution slot.

Schemas enforce wire shape, not truth, ownership or order. Server semantic checks
must additionally enforce run IDs across pages, contiguous sequences, next_cursor,
timestamp/deadline ordering, matching phase/runtime/terminal states, healthy <=
desired, stable traffic <= total and recovery binding to the current shift. Gate
statuses preserve PASSED/FAILED/SKIPPED/NOT_APPLICABLE; no invented REJECT decision.
Observation projection uses an explicit field allowlist. A source_ref allowlist
prevents arbitrary file links; serving an artifact still requires separate access
checks. Invalid/rejected proposals must be explained through runtime checks;
proposal_recorded contains only structurally validated BC-006 proposals.

## Confirmation and terminal result

Pending confirmation includes confirmation_id, created_at, expires_at and the
user-visible action, target, parameters, rationale, evidence, consequences,
risks and verification information required by confirmation-contract.yaml.
Server retains all binding hashes and identity/role checks. Browser submits only
confirmation_id and approve/reject; it cannot amend the action being authorized.

The internal confirmation wait returns one typed result: approved, rejected,
expired or stopped. Free text returns a UI instruction and does not enter this
wait result or invoke the model. Expiry is server-driven after 300 seconds even
if nobody responds. Approval is not execution: preserve existing revalidation,
binding, expiry and single-consumption checks immediately before tool dispatch.
Invalidation follows BC-006 recoverable feedback rules; it never becomes consent
for a changed action. Preserve the existing CLI behavior through an adapter.

Serialize competing stop/approve/expire commands with dispatch. If stop is
accepted before dispatch, do not start the action. If already dispatched, await
the actual result without claiming rollback or cancellation. No new recovery
action or model step starts after a stop request; runtime-owned verification of
an already dispatched operation may finish. During inference discard a late proposal.
Reject and timeout are distinct runtime reasons; neither restores the service.

Terminal envelope distinguishes origin (`runtime` or `platform`), reason_code,
safe explanation and nullable runtime_outcome. A platform preparation error must
not invent SAFE_FALLBACK or COMPLETED. Runtime outcomes preserve BC-009 semantics,
including task completion, service recovery and unknown write effects. Server
restart invalidates prior capabilities; it does not manufacture terminal evidence
or resume workers. Historical files remain private read-only evidence.

## Deadlines, release and startup

Agreed ready-without-goal reservation lifetime: 300 seconds after readiness.
Show remaining time; polling does not extend it. Release on explicit departure
when delivered, otherwise expiry. Browser close/unload is not reliable consent
or cancellation. During a run, reconnect does not extend confirmation deadlines;
the proposed five-minute idle warning is informational, not an environment reset.

### Provider deadlines and preparation

Initial local profile values, to verify in the separately approved station smoke:

| Boundary | Limit | Expiry behavior |
| --- | --- | --- |
| Read-only provider metadata request | 5 seconds | Report unavailable; no implicit model load |
| Complete preparation, including metadata checks and preload | 300 seconds total | End waiting goal with PREPARATION_TIMEOUT; no later automatic start |
| One inference request, including response read | 300 seconds total | End run through runtime failure handling; discard any late proposal |
| Ready without goal | 300 seconds after readiness | Release reservation; model residency unchanged |
| Each explicit confirmation | Existing 300 seconds | Existing expired-confirmation terminal outcome |
| Reconciliation of a still-observable timed-out call | At most 30 additional seconds | Stay unavailable if completion cannot be established |

Use monotonic absolute worker deadlines, not only socket inactivity timeouts.
The existing urllib adapter's timeout bounds blocking I/O; it does not by itself
provide an end-to-end worker deadline or prove cancellation. Enforce the live
deadline outside that blocking call without letting a detached call execute a
late proposal or freeing the single slot. Do not change measured runner behavior.
The 300-second inference limit and 10m keep_alive match the saved BC-008 B-18
invocation configuration; preparation and reconciliation limits are design values,
not measured loading guarantees. No whole-run five-minute deadline is introduced.

On explicit preparation admission, verify configured provider version and pinned
model digest through metadata endpoints, then preload the configured model using
an empty-prompt generate request with stream=false, the configured context options
and unchanged keep_alive. Do not send the user's goal in that request. Validate
a completed load-only response for the selected model; only then publish ready.
Metadata success or presence in /api/ps alone is not readiness for this session.
Preload counts as a provider operation in private evidence, not an agent proposal
or a BC-006 model reasoning step. No automatic pull, model substitution, preload
retry, context enlargement or keep_alive adjustment is permitted.

No user goal: preload success starts the ready reservation clock. Goal already
accepted: preload success starts exactly that run once. A timeout or failed
preparation requires a new explicit start; retain the old text for convenience.
UI: “Не удалось подготовить модель. Запрос не выполнен.” If provider completion
is uncertain, additionally show “Живой режим временно недоступен. Можно посмотреть
демонстрационный пример.” Do not offer an executable retry while admission is
unavailable. Successful recovery enables explicit start, never replays old goals.

### Recovery and restart

Distinguish completion of provider work from acceptance of its output. A complete
validated provider envelope with done=true can establish that this request
finished even if its proposal is invalid, late or discarded. A socket timeout,
connection loss after possible dispatch, incomplete/malformed envelope, or
unclassified provider error does not establish completion. Do not automatically
resend these requests. A failure proven to precede dispatch may release the
reservation after local cleanup; ambiguous dispatch is treated conservatively.

After uncertain completion, mark provider admission unavailable. Reconcile only
the original outstanding operation for at most 30 seconds; do not issue another
preload or inference as a probe. If that operation returns a valid terminal
envelope and the worker has exited, clear the outstanding-operation marker and
allow a new explicit start. The old terminal result remains unchanged. If the
transport is already lost, there is no response to reconcile: require local
owner recovery. Neither /api/ps, low GPU utilization, a successful health request,
nor elapsed keep_alive is proof that an unknown request or queue is finished.

Persist a minimal private outstanding-operation marker before preload/inference dispatch;
clear it only on established completion. Failure to persist blocks dispatch.
The marker contains correlation IDs and status, not prompts, credentials or
network details; it is runtime recovery state, never a public report. An uncleared
marker at startup blocks preparation even though browser sessions are invalidated.
Marker removal alone is not a supported recovery operation.

For the first local slice, uncertain completion requires the station owner to
establish that the old adapter worker and provider request/queue cannot continue,
using the station's separate administrative controls if necessary. Then a local
startup disposition records that recovery and reruns metadata/profile checks.
An application restart alone, or a visitor's refresh, cannot grant that disposition.
No browser reset endpoint, automatic provider restart/unload, shell execution,
administrative credentials or station power control is added to this application.
If the old worker cannot be shown to have stopped, live admission stays disabled.
Recorded examples and readable results remain available where the UI is served.

The initial profile assumes exclusive provider use during an approved live smoke;
other local inference clients must not submit work concurrently. This is an
operating precondition, not a claim that a browser session lock isolates the GPU
from unrelated software. On clean startup, the local owner confirms exclusive
use and no prior outstanding work before enabling live admission.

Keep the configured provider keep_alive unchanged; model residency is independent
of reservation expiry, confirmation expiry and whether another run may start.

Local startup must pass repository verification and validate the approved demo
profile before enabling model preparation. The profile pins model identity,
invocation settings, request limits, runtime budgets, modeled fixture and a
private evidence destination. A browser command cannot grant startup approval.
Health polling and recorded examples never initiate inference. Public exposure,
rate limits and multi-user scheduling retain BC-011's separate decision boundary.

## Remaining design choices and verification

Human authorized local implementation and deterministic simulator tests.
Before real inference: approve the concrete pinned startup
profile and bounded station smoke. Reservation expiry does not
change the existing runtime confirmation deadline. The exact wire schemas have
offline tests; their success does not establish secure HTTP behavior.

Offline acceptance must exercise atomic competing starts, preparation failure
and explicit retry, abandoned reservation expiry, read/write ownership, duplicate
and conflicting commands, lost responses, cursor races, confirmation expiry
without a reply, stop/approve dispatch races, unknown provider/write completion
and process restart. Provider tests must cover preload without a goal, no implicit
health-check loading, absolute deadline expiry despite continuing I/O, late done
without goal replay, lost response remaining unavailable, marker persistence
failure, uncleared marker at restart and rejection of public recovery commands.
Retain existing runtime and recorded-UI regression gates.
Real inference requires the separate bounded pre-run approval in BC-011.
The offline implementation is exercised through `tests/contract/test_bc011_*`
and `ui/src/live.test.tsx`; the provider-specific preload/metadata protocol above
remains a future real-adapter acceptance requirement. Linux/WSL file locking
prevents two coordinators from using one private evidence directory.

Design references: [Starlette responses](https://starlette.dev/responses/),
[Starlette lifespan](https://starlette.dev/lifespan/),
[OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[OWASP CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
Provider references: [Ollama load-only request](https://github.com/ollama/ollama/blob/main/docs/api.md#load-a-model),
[Ollama generate](https://docs.ollama.com/api/generate),
[Ollama loaded models](https://docs.ollama.com/api/ps),
[Python urllib timeouts](https://docs.python.org/3/library/urllib.request.html).

## Accepted interaction refinement — 2026-10-22

One explicit start requests admission/preparation; no second start inside the chat.
A successful reservation owns a fresh modeled environment and exposes its initial
`service_view` before goal submission or provider readiness. The run uses that
same environment. Reservation expiry/release discards it without executing tools.
Only successful new admission replaces the displayed history; a busy rejection
preserves the previous result. Refresh and result viewing never request admission.

Confirmation controls live in the runtime request card. Once the backend accepts
a decision, controls disappear and a separate operator card records the exact
action, choice and time. Confirmation is not execution. During work, a compact
disabled composer explains current state in muted italic text; no additional
model conversation is enabled. Recorded/live modes share actor styling and labels.
Navigation and admission errors stay outside message scrolling. Returning home
preserves the owned reservation/dialogue under BC-012; navigation alone does not
stop preparation, dialogue or an active run. Explicit release remains available.
Terminal explanations distinguish recovered service from incomplete rollback,
using the last accepted observation and preserving unknown-effect warnings.

### Deadline and desktop review refinement

The ready-without-goal deadline is checked at command admission as well as during
maintenance. Expiry releases the reservation, records `READY_EXPIRED` for its
owner and creates no run. A fresh start remains explicit. The browser uses the
session's `server_time` before a run and snapshot time afterwards; local clock
skew must not produce a false zero countdown. Zero remaining time disables goal
submission while the authoritative session state is refreshed.

Desktop workspaces use a compact brand header, task heading and chat-level controls.
The state panel (safe-operation conditions initially expanded), chat including its
composer/playback controls and runtime journal share a bottom edge. Message and
journal streams scroll internally. Scenario-failure context stays above all three
panels. Entry scroll happens only on mode entry, not on subsequent events.
Actor labels remain explicit; denser desktop message spacing does not reduce
mobile text sizes or enable any additional conversation.

### Owner navigation and stable workspace refinement

Home, recorded demo and live workspace are browser-history screens. Logo/home and
Back/Forward use the same navigation boundary: leaving a reservation, dialogue or
active run preserves it and never resets deadlines (BC-012 refinement). History
navigation, refresh and viewing a terminal result never request new admission.
The owner sees return-to-run (or view-result after termination) on home and demo,
not another visitor's busy warning. Confirmation countdown uses server time and
the current confirmation deadline; running phases without an exposed deadline
show status only. Disconnected state must not claim a fresh deadline/status.
Live navigation sits beside the task heading, outside the message composer.
Simulator identity stays visible in the live chat header and footer. Desktop panels have a viewport-bounded,
content-independent common height; longer state content scrolls. Mode entry
scrolls to the task heading, preserving the failure-scenario context below it.

### Review refinement — 2026-10-23

Home groups live start/return and recorded viewing in the central mode chooser.
An active owner sees return and the applicable deadline; a terminal owner sees
explicit restart and read-only result access. New admission can fail busy without
replacing the previous result. Home navigation belongs beside the task heading,
not beside the message composer. Demo viewing retains compact owner access near
playback controls. Simulator identity stays explicit in the live header/footer.

Live proposal cards expose a human-readable action summary and original rationale.
Admission events carry `proposal_sequence` (nullable when no valid proposal was
published), assigned by the server within the exact submit invocation, never by
adjacent IDs. Proposal events carry `action_summary`. UI links only resolve within
the current run to an existing proposal/admission event. Details show `event-N`
as a live-stream identifier, not a raw trace ID. Reciprocal navigation opens the
target details and highlights for two seconds without scrolling the page.
Journal follow-to-bottom applies only while the reader is already at the bottom;
reading older entries or navigating to a linked check must not be interrupted.

### Local provider implementation handoff (2026-10-23)

The concrete profile is `live-model-profile.json`; activation and private approval
are specified in BC-011's local Ollama slice. Implementation and offline tests are
authorized; actual station inference still requires revision-bound human approval.
The simulator CLI remains inference-free. The separate Ollama CLI binds loopback,
uses no proxy/redirect and accepts no browser-supplied provider configuration.

`status` and `session` responses now include server-owned `provider` metadata:
`kind` (`simulator` or `ollama`) and nullable `model_name`. These disclose no owner,
endpoint or private path. Older UI responses without it render an unknown-provider
label rather than claiming actual inference. Runtime/consent semantics are unchanged.
A shared user-scoped coordinator lock and outstanding marker survive evidence
location changes. Approval consumption and the two-preparation smoke allowance
bound the test; they are not public authentication or per-person rate limiting.

### Review diagnostics and truthful summaries — 2026-10-23

Status may include `unavailability_reason`: null, `SMOKE_LIMIT`,
`PROVIDER_UNAVAILABLE` or `SERVER_CLOSED`. Quarantine/closure take precedence over
exhausted preparation allowance; an occupied slot remains busy. UI explains an
exhausted local test allowance without representing it as another user's run.
This does not introduce public rate limits or change the two-preparation profile.
Consumed approval is rejected with a concise CLI error before preflight/provider
activation; consumption remains exclusive and durable, including races.
Action summaries use actual proposal/confirmation arguments, never a fixed replica
count. Unknown tools receive a neutral label; no summary grants permission.


## BC-012 initial dialogue extension (approved design)

The dialogue-enabled local service preserves `live.v1` execution events and adds
`POST /api/dialogue` (`command=dialogue`, command_id, reservation_id, text).
Text is nonblank, at most 2,000 code points. The old external `start_run` command
is rejected with GOAL_ADMISSION_REQUIRED in this service; only a validated
`start_remediation` dialogue result can create a run. Historical BC-011 fixtures
continue to exercise the earlier service contract.

The session adds `dialogue`: null or an owned bounded transcript with reservation_id,
state (`preparing`, `ready`, `thinking`, `admitted`, `terminal`), messages, calls,
reason, absolute_expires_at and run_id. Messages have opaque IDs, actor, text and
time; agent messages additionally identify answer/clarify/unsupported/start_remediation.
This history is separate from remediation events, retained after completion and
reconnect, and replaced only by an explicitly admitted new scenario. No cross-session
transcript access is allowed. A single message may wait for preparation; there is
no queue of additional messages and no automatic resend or model retry.
Home/demo/history navigation preserves the same owned reservation during preparation,
ready and thinking phases; returning does not request another preparation. The owner
sees return access and phase-appropriate status/countdown outside the live screen.
Ready countdown uses the earlier idle/absolute deadline; thinking exposes status
rather than a user-decision countdown. Polling does not renew either deadline.
Explicit stop/release and expiry still terminate dialogue; other sessions remain
excluded while the slot is owned, including during in-flight cancellation.

`schemas/bc012-dialogue.schema.json` defines the separate model result. The model
returns a bounded reply and user-message references only for start_remediation.
The model instruction explicitly requires `goal_message_ids: []` for answer,
clarify and unsupported; references are mandatory only for start_remediation.
For start_remediation, instruct the model to return a brief goal-handoff reply
(1–2 sentences), with no operational plan, capacity calculation, proposed first
action or request to confirm an action. It may explain that subsequent changes
require explicit operator confirmation. This is model-authored text, not a fixed
runtime notice or an executable plan. Informational answers remain substantive.
The dialogue capability summary is not the executor's complete planning context;
BC-006 still assembles and checks each concrete action. This instruction adds no
semantic validator, automatic rewrite or retry of reply text.
The dialogue context projects tool names, categories, preconditions and confirmation
requirements, plus the exact BC006-capacity rule, from
`specs/core/bounded-remediation.yaml` as descriptive capabilities
of the later executor, not callable dialogue tools. STOP may be proposed by that
executor. Do not promise resume rollout, candidate scaling, partial traffic shifts
or arbitrary deployments. Desired/healthy counts describe the stable version;
candidate_count does not establish candidate health. Explanations distinguish
observed facts, hypotheses and unknowns: PAUSED is an operational state, not proof
of root cause; unsupported operations do not imply known ineffectiveness. Do not
invent tool responses when their preconditions are unmet. State-changing actions need
explicit confirmations; read-only observations do not. These prompt clarifications
do not replace validation or establish semantic accuracy; invalid output is neither
repaired nor retried automatically.

The server requires existing user references including the latest message, checks
schema, ownership, phase, deadline and budget, and retains all exact user text plus
clarification context in private dialogue evidence. The runtime goal preserves all exact
user text in transcript order, including earlier constraints, never a model
summary or a model-selected subset. Agent replies remain separate context in
the private transcript; they are not attributed as operator intent. If the combined
goal exceeds the existing 2,000-code-point runtime bound, end with
DIALOGUE_GOAL_TOO_LONG; never truncate or summarize it silently. These checks do
not prove semantic classification correctness. Dialogue has no tool interface.

The local-free-text profile fixes 5 calls (preset-only fixes 4), including classification of an immediate recovery goal,
300 seconds per call, 300 seconds waiting for the next user message, and 600 seconds
absolute time from successful preparation. The final permitted response may admit a goal;
a final non-start response ends dialogue with DIALOGUE_LIMIT. The idle clock starts
at readiness or completion of a reply; the absolute clock never resets. Expiry,
release, invalid output and provider failure cannot start remediation. A late
reply is discarded. In-flight work retains the slot until completion is known;
unknown completion retains provider quarantine. Polling never renews deadlines.

Profile/version and revision approval must be renewed before real-model evaluation.
The two-preparation allowance and all BC-006 confirmation/execution budgets remain
unchanged. Fake-provider tests verify transport and transitions, not semantic quality.

### Private provider failure diagnostics (BC-012)

Provider failures retain their exception class in private evidence. HTTP failures
also retain the fixed API path, status code and an error-body excerpt bounded to
4096 bytes, with truncation/read-failure flags. Treat the excerpt as untrusted and
potentially sensitive: never return it through the public API or UI, copy it to
Git, or treat it as instructions. Do not record response headers or error URLs.
Diagnostic extraction must not replace the original failure or authorize retries.
An HTTP error alone does not establish provider completion: existing quarantine
and explicit reconciliation remain unchanged. No model/schema/profile change is
implied by these diagnostics.

### Dialogue provider format compatibility

The full BC-012 dialogue schema remains authoritative for server validation.
For Ollama structured output only, omit `reply.pattern`: the pinned provider
rejected its unanchored non-whitespace expression during grammar conversion.
All other schema fields remain unchanged. The provider format is a generation
aid, not admission authority; whitespace-only replies must still fail runtime
validation without creating a remediation run. Do not alter prompts, model
settings, retry budgets or quarantine as part of this compatibility fix.

## Server-selected input profiles

The dialogue service supports `preset-only` and `local-free-text`. CLI startup
defaults to `preset-only`; free text requires an explicit server startup argument.
Unknown profiles fail startup. Profiles cannot be changed through HTTP, cookies,
query parameters or model output. Session metadata exposes the selected profile
and the fixed command catalog for presentation only.

In `preset-only`, `/api/dialogue` accepts `choice_id` instead of `text`, with a
closed schema. The server resolves capabilities/state/capacity/recover choices to
fixed scenario text. Extra fields, arbitrary text and unknown choices fail before
command bookkeeping, expiry processing or provider invocation. The legacy start
route remains blocked. Only the recover choice may admit remediation, even if a
model misclassifies an informational choice. Ownership, deadlines, idempotency,
confirmation and provider budgets remain unchanged. Local free-text behavior is
retained explicitly. This input boundary alone does not enable public transport;
loopback restrictions and private smoke evidence remain in force.

Preset recovery uses only the fixed recovery goal; prior informational choices
remain transcript context, not accumulated operator constraints. Local free-text
goal assembly continues to preserve all operator messages. Real-model smoke
approval must also match the server input profile.

Preset-only refinement: four initial-dialogue calls per admission, including the
recovery request; local-free-text retains five. Session input_policy exposes
max_calls. After an informational choice receives an agent reply, it is omitted
from choices for that admission, including read-only reconnect. A new admission
restores the catalogue. This presentation filtering is not a new authorization
gate; direct repeated valid choices remain subject to the same call budget.
State and capacity prompts retain explicit non-execution intent; the capacity
question no longer explicitly requests an N-1 explanation. Recovery admission
and execution constraints remain unchanged.

## Paired loopback entrypoints (simulator integration)

One process owns one DialogueService, provider, execution slot, lock, budgets and
quarantine state. Two separately bound loopback listeners expose server-selected
profiles: public-facing preset-only (4 calls) and owner local-free-text (5 calls).
This slice is local-only; neither listener supports proxy headers or external
binding. The existing real-model approval/launcher remains unchanged.

Sessions are bound at bootstrap to their entrypoint and input profile. Distinct
cookie names prevent port-sharing browsers from overwriting each other; cookie
names alone are not authorization. Authentication rejects a token from the other
entrypoint, even when copied under the expected cookie name. Snapshots, traces,
confirmations and stop commands retain session ownership checks. Client body,
query, Host and Origin cannot select or upgrade the entrypoint/profile.

Both entrypoints contend atomically for the same slot. Opening pages, polling or
bootstrapping sessions never reserves capacity or calls the provider. Neither
entrypoint preempts a preparation, initial dialogue or execution owned by another.

The owner listener alone exposes a same-origin control to enable/disable new
public admissions. Disabled state is enforced before prepare, under the shared
lock; accepted command replays remain idempotent. Existing public admissions may
continue, confirm, stop and view results. Private admissions remain eligible when
the shared slot is free. No control route or control metadata is exposed through
the public listener. The setting is process-local and defaults disabled at paired
startup; the owner explicitly enables it. Shutdown of either listener shuts down
both and closes the service once. No actual model loading or public deployment is
part of this slice.
