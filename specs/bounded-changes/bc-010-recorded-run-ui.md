# BC-010 — adaptive recorded-run viewer

Planning baseline: 2026-10-15. Human selected this bounded UI direction.
This document defines the selected scope; current lifecycle is in specs/README.md.

## Current human disposition — 2026-10-21

Basic React UI design at `6637dc9` accepted by the human owner. Further visual
adjustments may follow during later work. This supersedes pending design review
in earlier handoffs, without claiming exhaustive viewport, zoom or keyboard QA.
Integration reconciliation and final BC closure remain separate from design
acceptance. Next authorized activity is live-integration planning, not live
execution, public station access or publication under this recorded-only BC.

## Accepted next design checkpoint — 2026-10-19

Human accepted the [operator UI design](../core/operator-ui-design.md) and its
[interactive sketch](../../docs/operator-ui-sketch.html). That document records
the next presentation/interaction target, including deferred live boundaries.
React transfer is now authorized. Recorded replay extends presentation only;
all live execution exclusions remain in force.

## Purpose and project fit

Let the operator understand what happened, why execution ended, what remains
unfinished and what is unknown, without reading raw trace files. Operator UI is
one direction of Governed Agent Runtime under the shared product brief,
architecture and root AGENTS.md, not a separate product or control plane.

## Material dependency and baseline

Depends on BC-009 operator outcome presentation at revision
`9fe3fe73dcb549402ac89519b23379fd2ce6725d` (implementation closure `ac4ac53`).
See [BC-009](bc-009-operator-outcome-view.md) and its JSON `view_version: "1"`.
The local BC-009 baseline was published through the GitHub connector as
`a5d4248bce84cc5e0ceea43f1f789ae482cb8526` in PR #10. Its tree is exactly
`ab057d4e734b950df7342fef7d8fb0ec9c0298d7`, identical to local `9fe3fe7`.
The pin records provenance, not a claim that any later projection is compatible.

Generate UI data from BC-009 `build_view` for exactly these saved synthetic runs:

- BC-006 `run-001`: success;
- BC-007 `run-001`: model STOP after recovery FAIL.

Do not edit historical evidence or earlier review snapshots. Use generated assets
with source hashes/event references. Reuse the BC-009 deterministic text report
for details; visible summaries and state must agree with the same projection.
Do not parse display text to reconstruct domain state. Any incompatible projection
change must be explicitly assessed against BC-009 and its contract tests.

## Technical choice

Use React + TypeScript + Vite in `ui/`, with responsive CSS and a reproducible
lockfile. Pin actual package versions when implementation starts. The component
structure is justified by the run selector, status, state panel and report.
Avoid adding a router, global state framework or a large UI kit without a concrete
need. Keep dependencies small and use accessible native controls where practical.

Build a portable static application. It must run locally and build without Sites,
a hosting account, a particular domain or a running Python/model server. Hosting
and custom-domain configuration are deferred. Support configurable asset base
paths so deployment is not hard-coded to a hostname or root path.
Python is used offline to prepare the recorded view assets, not in the browser.
No new HTTP API or backend framework is selected in this BC.

## Operator experience

One screen with a labeled run selector and three conceptual areas:

1. Operator communication: final status, reached state, remaining work and relevant
   unknowns. The last model rationale is clearly labeled as explanation before
   action (or of STOP), never a newly generated final answer.
2. System state: versions/replicas, traffic, recovery, conflicts and observation
   timestamp with timezone. Execution status is separate from service recovery.
3. Expandable report/details: deterministic report, source references and original
   rationale access. Preserve BC-009 budget-excerpt labeling and evidence integrity.

Always mark the run as saved and synthetic. Opening or switching it does not
refresh service health. Timestamp means observation time, not page load time.
Source event references must be inspectable as text; do not create broken links
that imply the full evidence repository is served by the static application.
No confirmation buttons or controls that imply live execution. A chat-shaped
recorded timeline exposes original model proposals and historical runtime events.
It is not a live conversation. Live entry is visibly unavailable.

Desktop: communication and state side by side where readable. Narrow screen:
stack state, communication, then journal. Keep the version summary and total
traffic visible independently of details. The versions table is always visible;
safety conditions default open on desktop and closed on narrow screens.
Exact spacing, palette and layout can evolve during review without changing these
semantic boundaries. Do not use color as the only status indicator.

## Local persistence and failure behavior

Persist only selected run ID in browser local storage, scoped/versioned for this
viewer. It is a convenience preference, not user identity, durable task history
or a source of operational truth. Unknown stored IDs fall back to the default run;
unavailable storage must not prevent viewing. Do not persist sensitive content.

Validate loaded view shape/version at the UI boundary. Missing, malformed or
unsupported data produces a clear unavailable state, never fabricated success.
While changing runs, never show one run's title with another run's state/report.
Unknown write effects suppress assurances based on older observations, as in BC-009.

## Acceptance and verification

- For both runs, status/state/report agree with generated BC-009 output;
  recovery and task completion remain distinct.
- The operator can identify outcome, termination cause and remaining/unknown work
  without opening raw evidence. Human review records concrete ambiguities; no
  claim of general usability or productivity improvement follows from one review.
- Inspect at representative widths 390, 768 and 1440 CSS pixels. No page-level
  horizontal overflow; technical text wraps or scrolls within its details area.
  Selector and report control work with keyboard and touch; focus is visible,
  labels are explicit and content remains usable at enlarged text/zoom.
- Focused UI checks cover run switching, invalid/missing data, unsupported version,
  unknown effect and unavailable local storage. Type checking and production build
  pass. Run required repository regression gates for the completed logical block.
- Compare generated assets with their source projections and verify no source
  evidence mutation. No new model calls or runtime execution are needed.
- Browser checks must be actually performed with an available supported tool or
  reported as unverified for human execution; a build alone is not responsive QA.

## Exclusions and later decisions

No live runtime/Ollama connection, API, authentication, user-owned sessions,
server cache, polling, command interpretation, refusal/timeout implementation,
resume, streaming reasoning or publication in this BC.

Later needs: live confirmation/expiry/refusal and connection-loss contracts;
user → task → run ownership and persisted history; deployment/domain choice.
Each is considered from observed need, not automatically authorized here.
Dependency automation remains a deferred hypothesis; this BC introduces none.

## Recorded replay projection — 2026-10-19

A separate `replay.version: "1"` asset accompanies the unchanged BC-009 view.
Material dependency: the saved runner `trace.jsonl` event semantics (BC-006 and
BC-007 evidence listed above). Source SHA-256 remains in the BC-009 view.
Each selected event carries its original event ID, timestamp and kind.
Initial state comes from `started.state`; subsequent state comes only from
`observation_applied.observation`. Never apply raw tool results or future final
state at an earlier replay cursor. Preserve original model-output rationale.
Runtime descriptions are deterministic UI labels, not invented model answers.
Confirmation consumed is historical evidence, not a request for a fresh decision.

Playback is manual next-event progression, reset and jump-to-result. Controls
never execute tools, make model calls or mutate evidence. Reset returns to the
initial recorded state. Final outcome/report remains the BC-009 projection and
is displayed only at the end. Unknown write effects retain the BC-009 warning.
A replay is an explicitly selected subset of trace events, not the full audit log.
Validate replay version, initial state, ordered event identities and final
observation consistency. Source export must remain reproducible and read-only.

The accepted sketch and subsequent human review define visual composition.
Live prompt input and suggestions are deferred to live mode; no user text is
submitted in this BC.
Live runtime transport, cancellation and confirmation are separate future work.

## Human review refinement — 2026-10-19

Replay projection version is now `2`: required deterministic `summary`, optional
recorded gate checks and contract references. BC-009 view version stays `1`.
Version 1 replay assets are rejected rather than silently mixed with version 2.

Before mode selection show neither example selector nor prompt input. In recorded
mode show the example selector above the chat; changing it preserves recorded
mode but resets the cursor. Live entry remains unavailable. Prompt input and
suggestions belong only to the future live mode.
Version/replica table is always visible. Safety conditions default open on desktop
and closed on mobile. Journal and chat have bounded matching desktop heights and
independent scrolling. Changed state values receive a two-second emphasis, with
reduced-motion support; initial loading and reset must not imply a new operation.

Every event explains its action and distinguishes proposal, permission,
confirmation, execution start and accepted observation. Preserve original model
rationale visibly in the message; technical sources remain under details. Human-readable summaries are deterministic presentation,
not invented model quotations. Gate details use actual recorded IDs/statuses and
references to policy/tool contracts; skipped/not-applicable is never called passed.
Confirmation context comes from the associated proposal and confirmation record.
Expose a final-report button at completion. A compact translation hint appears
below the conversation. Live helper copy is deferred with live input:
“Используйте подсказку или свой запрос. Формулировка может повлиять на результат.”

## Full rationale and mobile reading refinement — 2026-10-19

Show original model rationale in full in each model message, outside details.
Label the preceding deterministic summary “Краткое объяснение, сформировано
интерфейсом” and the original separately “Оригинальное пояснение модели”.
Details contain tool identifiers and human explanations of trace/contract sources.
Consumed historical confirmations display disabled Confirm/Reject choices, with
Confirm visibly selected and labeled as a recorded operator decision.

Neither BC-006 nor BC-007 selected evidence contains a Russian operator request
(17 files inspected in each run). The short phrase “Восстанови работу сервиса” is
from BC-008 `specs/core/bc008-goal-framing.json`, variant B. It may introduce this
UI as an explicitly illustrative request, not an original utterance of these runs.
Do not alter evidence or present runtime current_goal as a user utterance.

On phones use a bounded internally scrolling conversation with side gutters for
page scrolling. Keep the compact service summary above the message viewport,
linked to full state, derived from the same accepted observation, including
unknown/recovery distinctions and two-second changed-value emphasis. Advancing
replay scrolls only the internal streams to the new event's start on all devices.
Journal uses a neutral light-gray background. No new live execution is introduced.

Add an explicitly opened “ⓘ Как это работает” dialog beside the platform heading.
Describe roles, verification, confirmation and recorded evidence in plain language.
Support close button, Escape and return focus; do not auto-open. Footer and dialog:
“В живом режиме инференс LLM осуществляется на реальной AI-инфраструктуре.
Условия работы сервиса payment-api и операции с ним моделируются.”
Clearly state that the current build supports recorded mode only.

## Readability review — 2026-10-20

Give desktop branding and responsibility text more space and larger type; keep
help separate without overlap. Redistribute wide-screen columns moderately toward
chat/journal, preserving usable laptop state-table width. Mobile help is slightly
more compact. Describe traceability and deliberately bounded interaction without
claiming production suitability. Add project authorship and AI-assisted SDD credit;
external profile links require known URLs.

Explain G08 SKIPPED in preflight/revalidation as a separate confirmation stage,
not permission or necessarily waiting for a human. A gate skipped after a prior
failure must instead explain that earlier failure. Preserve raw statuses. Actual
confirmation consumption remains a distinct event. Introduce the recorded FAIL
example as an intentionally modeled failed recovery check that tests stopping
and handoff; emphasize FAIL in UI summaries without modifying model quotations.

## Mobile space and header alignment — 2026-10-20

Center the two responsibility lines within their shared desktop text column;
place help to the right, vertically centered across both lines. Emphasize the
bounded-interaction/value paragraph in dark blue without a colored background.
Mobile message text is 14px, with tighter heading and helper spacing. Size the chat
relative to viewport height, with a readable minimum for short screens. The compact
state sticks to the page viewport top only within the chat; ancestor overflow must
not capture its sticky positioning. Message scrolling remains internal and page
scroll side gutters remain available. Validate the result on actual mobile UI.

## Recorded example clarity and palette — 2026-10-20

Restore whole-header centering with equal desktop side columns, gray value-copy
background and the recorded/English note below playback. Mobile messages now use
12px per human review; notes use 11px. Preserve accepted sticky service summary.
Use a restrained blue-gray page, white chat, darker neutral-gray journal and
light message cards. FAIL context uses a circled exclamation, italic two-paragraph
copy and a dynamically derived replay event number (not a fabricated agent step).
Explain MODEL_REQUESTED_STOP as an agent-requested stop accepted by runtime,
retaining the technical code. Do not imply successful recovery or infrastructure
shutdown. Only attach FAIL-specific explanation when the recorded recovery failed.

Help may summarize the selected saved run: count model_output proposals,
preflight and revalidation checks separately, and confirmation_consumed decisions.
These are admission-check rounds, not all internal checks. Initial intent is a
conceptual interaction, not an original user utterance present in these records.
Do not present these run-specific counts as universal or live-run limits.

## Event breakdown and restrained background — 2026-10-20

Move run-specific counts out of general help to a disclosure beside the replay
event counter, available only in recorded mode. Separate agent proposals, runtime
admission rounds, operator confirmations and remaining lifecycle/tool/observation
events. Derive all counts from the selected replay. Label the initial request as
prepared for demonstration; it is not a counted recorded event. Keep the breakdown
compact without a colored backing. Repeat checks mean revalidation before execution.
Lighten only the overall page background; preserve chat, journal and message colors.
For the recorded recovery-FAIL safe fallback, explain that the agent correctly
requested a stop and runtime ended the run, retaining SAFE_FALLBACK and
MODEL_REQUESTED_STOP and the operator recovery handoff. Do not apply that positive
assessment to arbitrary stops or alter recorded model quotations.

Follow-up review: list tool calls separately from remaining events (success: 6
and 11; stop: 4 and 8). Provide a circled close control on the right of the open
breakdown, returning focus to its information toggle. Lighten page to #f4f7f9.

Latest visual review replaces the circled close icon with the standard “Закрыть”
button, reduces the information toggle to 16px in a 28px-high counter row, and
lightens the page to #f7f9fa. Preserve message and journal surfaces.
