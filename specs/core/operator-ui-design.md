# Operator UI — accepted design baseline

Accepted in human review on 2026-10-19 (Europe/Moscow). This is the project-local
presentation and interaction target for the next UI implementation step, not a
claim that live integration is implemented. The accepted sketch was preserved
first; the subsequent authorized React transfer implements recorded playback
under BC-010, with browser visual acceptance still pending.

[Accepted interactive sketch](../../docs/operator-ui-sketch.html) preserves the
reviewed r7 appearance with the r8 disclosure correction requested on 2026-10-19.
It is illustrative, not recorded execution evidence.
Normative runtime/confirmation contracts retain authority over execution.

## Scope and dependencies

- Shared product: [product brief](product-brief.md); the UI is not a separate
  product or control plane.
- Existing static viewer: [BC-010](../bounded-changes/bc-010-recorded-run-ui.md).
  Its implemented scope and acceptance are not expanded by this design record.
- Outcome semantics: [BC-009](../bounded-changes/bc-009-operator-outcome-view.md),
  including unknown effects, recovery versus completion and historical sources.
- Execution and action bindings: [BC-006](../bounded-changes/bc-006-s12-bounded-remediation-loop.md)
  and [confirmation contract](confirmation-contract.yaml).
- Recorded demonstrations require a trace-derived step projection: BC-009's last
  proposal alone is not full dialogue history. Never invent missing messages.
- A live browser bridge, arbitrary initial goal, cooperative stop and per-run
  ownership require a separately scoped implementation and verification. The
  sketch's scripts are not a production runtime adapter.

## Layout and copy

Desktop: dark charcoal service state on the left, light dialogue in the centre,
runtime journal on the right. State and chat panels align at the top and have
matching height when side by side. On narrow screens, state is above dialogue;
the version statuses and total traffic remain visible when details collapse:
`2.4.1 · Healthy`, `2.4.2 · Degraded`, `Общий трафик · 820 RPS` in the
initial example. Derive these values from the same observations as the table;
update them throughout execution. Keep the incident explanation visible too.
On desktop, table details are open by default and can be collapsed manually.
On mobile, table details start collapsed. Version statuses, total traffic and
the incident explanation remain visible on both sizes regardless of disclosure
state. The technical journal may also collapse. Preserve readable labels,
keyboard focus and touch targets; verify the actual implementation at 390, 768
and 1440 CSS pixels. R7 received provisional phone readability acceptance, not
final responsive acceptance of the React implementation. Mobile text targets:
16 px body/messages, 14–15 px statuses/table/buttons, 13 px secondary explanations,
and approximately 1.5 line height. Keep desktop sizes and heading sizes unchanged.

Keep the existing project brand. Header concept:

**Агентная платформа с разделением ответственности**

LLM предлагает · Runtime контролирует · Оператор задаёт цель и принимает решения

Page heading: **Восстановление сервиса payment-api**, with stronger typography
and a distinct monospace service name. Remove the old operational-overview,
results-page and large saved-run explanatory banners.

Chat header: **Агент управления сервисом**. Use the accepted blue/italic emphasis
and subtle contrasting header surface. Do not repeat `payment-api` here.
Place the readable status beside the compact stop control. Use `Активен` in green
only for an active scenario; distinguish not started, stopping and terminal states.
The stop icon has a modest red accent and a large enough touch target, with an
accessible name and tooltip **Остановить выполнение**. It must not dominate the
main action. The history remains visible after stopping.

Introductory copy:

> **Восстановите сервис payment-api после неудачного обновления.**
>
> - Вы задаёте цель и подтверждаете изменения.
> - Агент оценивает состояние среды и предлагает действия.
> - Runtime проверяет условия и управляет выполнением.

Place **Выберите режим** directly above the entry buttons in a slightly larger
label, not in the top context row.
Entry choices: **Начать живой сценарий** / **Посмотреть пример**. Live entry starts
model loading when integrated; no load percentage without measured progress.
A request submitted while loading waits without requiring duplicate submission.

Keep the environment explanation in a persistent, legible page footer rather
than repeating it in the service panel:

> В живом режиме инференс LLM осуществляется на реальной AI-инфраструктуре.
>
> Условия работы сервиса payment-api и операции - моделируются.

This describes the integrated target. An unconnected build must explicitly show
that live execution is unavailable. Preserve sufficient footer text/background
contrast, including within embedded previews.

## Service dashboard

The left panel describes observed service state independently of the agent's plan.
Use two version rows with columns **Версия / Реплик / Состояние / RPS**. Avoid a
separate `Здоровых` column and redundant stable/new labels. Use `Healthy` (green)
and `Degraded` (red) only where supported by observation; unknown is not healthy.
Do not invent per-replica health or infer candidate health from replica count.
The sketch's example labels require a verified data mapping before React use.

Initial incident copy, red when supported by the fixture/observations:

> Выявлена деградация версии 2.4.2: повышены доля ошибок и время ответа. Rollout
> версии 2.4.2 приостановлен. Требуется восстановить работоспособность payment-api.

Do not append instructions about confirmation or verification to this dashboard
copy. Do not assert capacity shortage or a specific SLO without evidence.
Highlight traffic routed to the degraded version in red with the row's textual
status; 205 RPS denotes routed traffic, not 205 failed requests per second.
Keep total traffic and observation time. Show operation conflicts only when
material, with a concrete explanation; omit an unexplained default conflicts row.
Do not show a generic initial `Восстановление` row anticipating future work.

Update the incident description from new observations, not from a proposal or
confirmation click:

- Traffic shift observed: version 2.4.2 receives 0 RPS, all traffic is on 2.4.1,
  candidate replicas remain. Service recovery is not yet confirmed. Use an amber
  unresolved-state explanation; retain any still-observed degradation separately.
- Recovery FAIL: keep a red service-level warning even with zero candidate traffic.
- Recovery PASS: recovery on 2.4.1 is confirmed; remaining candidate replicas and
  incomplete rollback remain visible. Zero traffic alone is not a defect and
  does not imply traffic must be redistributed to that version.
- Rollback verified: show completion, zero candidate replicas and resolved state.
- Unknown write effect: last observation cannot certify the current system state.

## Visible operational constraints

Expose **Условия безопасной работы** in the service details independently of the
agent: 150 RPS capacity per replica (not per version), utilization below 90%
after traffic transfer, and below 90% with one replica unavailable (N−1).
These values describe the current bounded scenario; production presentation must
read the applicable contract/context rather than assume universal constants.

An action rationale should explain the material constraint using grounded data.
For 820 RPS and eight replicas, utilization is about 68.3%; with one unavailable,
78.1%. Seven replicas would yield about 91.1% under N−1 and fail the threshold.
A displayed explanation does not substitute for runtime checks in the journal.
Do not fabricate such an explanation as a historical model message: preserve the
recorded rationale, or label independently calculated context as runtime/UI data.

## Dialogue and action decisions

Classic chat, with distinct authors: operator, agent, runtime. Model proposals and
rationales must not masquerade as executed actions or verified runtime results.
The right journal contains actual execution events, not hidden reasoning.

Allow a free-form initial request. A T9-like suggestion above the input inserts
editable text; it does not send automatically. Offer both exact BC-008 texts
from [goal framing](bc008-goal-framing.json):

- После обновления сервис работает нестабильно. Восстанови его работу безопасным способом
- Восстанови работу сервиса

The introductory heading is presentation copy, not a third measured request.
BC-008 verified these formulations within its recorded experiment; this is not
validation of a future browser integration or arbitrary wording. Proposed helper
text after the corresponding integrated request has been verified:

> Пример проверен на предложенном запросе. Вы можете написать свой — формулировка
> и содержание запроса могут повлиять на ход выполнения и результат.

Do not claim verification before it occurs. Arbitrary goal text never extends
runtime permissions or changes control-plane rules.

A state-changing proposal shows the action, rationale and expected change, with
**Подтвердить / Отклонить** bound to one current action. Below them:

> Действие изменяет состояние системы и требует явного подтверждения оператора.
> Текстовые сообщения не считаются разрешением на выполнение.

For the first live iteration, disable free-text input while waiting for the action
choice, with **Подтвердите или отклоните предложенное действие**. Clarifying
model dialogue at this point is deferred. If text nevertheless reaches the
interface boundary, it is neither approval nor refusal; do not pass it to the
terminal's confirmation parser. Point to the pending action decision instead.

Record confirmation identity, actor/session, time, bound proposal/parameters and
outcome. Preserve existing revalidation, expiry and single-use semantics. A new
or changed proposal invalidates the old decision controls.

- Confirm: execute only after runtime authorization/revalidation; show the
  operator decision and execution result separately.
- Decline: end the run without executing that proposal. Earlier changes remain;
  no automatic replan or repeated request for consent.
- Confirmation expiry: end the attempt, then allow a new scenario. Do not imply
  the current blocking CLI proactively pushes a timer event to a browser.
- Stop: request termination at the next safe boundary. A model call may finish,
  but its returned proposal must not start a new action after cancellation.
  Resolve any already-started operation's outcome; do not report it as undone.
  Show `Останавливаем…` until runtime confirms the terminal result.
- Restart: new run and initial synthetic environment, not resume. Reset must be
  runtime-owned, not only a cleared chat. Page refresh may offer/start a new
  scenario only once active-run ownership and cleanup are defined; it is not
  permission to leave an old run executing unseen.

For a known refusal/stop outcome, use:

> Выполнение остановлено по вашему решению. Уже выполненные изменения сохранены.
> Дальнейшее восстановление сервиса необходимо обеспечить самостоятельно.

Adapt the reason for timeout or system failure, and retain unknown-effect warnings
where applicable; do not promise known persistence of an unverified write.
Terminal entry choices: **Начать заново / Посмотреть демонстрационный пример**.
Resume from terminal state is excluded from this first iteration.

## Demonstration and sketch boundaries

A real demonstration is explicitly **Демонстрационный пример**, replaying saved
run events without new LLM calls. User-facing outcome choices replace BC IDs:
**Восстановление завершено / Восстановление не подтверждено**. BC identifiers and
source hashes belong in technical details. Recorded confirmations are historical
facts, not currently actionable permission controls.

The retained sketch has working local illustrative buttons and deliberately
unconnected live-mode preview. Its wording `Эскиз`, `иллюстративные события`,
`модель не подключена`, and `Следующее событие примера` is review scaffolding,
not final product copy. Do not transplant these scripts or fabricated responses
as real execution. Keep mode labels and the agreed environment footer in product.

## Verified implementation boundary at this checkpoint

Code inspection at local revision `4f61a98` and 49 existing BC-006 remediation /
BC-008 goal-framing tests passed on 2026-10-19. This establishes no new measured
LLM outcome or browser QA:

- Action-bound confirmation and terminal `CONFIRMATION_REJECTED` already exist.
- Decline does not execute the candidate or undo earlier actions. The last
  observation is retained; decline does not automatically re-observe the service.
- A fresh runtime starts a fresh synthetic environment; terminal resume is absent.
- Confirmation currently blocks in a callback; CLI accepts an exact token and
  treats other input as refusal. UI text must not reuse that parsing path.
- Arbitrary initial goals, browser sessions/API, cooperative UI stop and chat
  while awaiting confirmation are not implemented.

React recorded-view transfer is implemented under BC-010; visual acceptance
remains pending. Live integration,
telemetry, deployment, accounts and reusable SDD changes are not part of this
preservation step. GPU/VRAM/power telemetry remains an optional later hypothesis.

## Superseding review decisions — 2026-10-19

Versions/replicas are always expanded on desktop and mobile. Only safety conditions
remain collapsible (desktop open, mobile closed). Example selection appears after
recorded mode is selected, above the chat. Prompt input appears only in live mode.
Show contextual event explanations, source-backed gate details, 1.5-second changed
value emphasis and a visible final report action. Bound journal height to chat.
Common helper: “Агент может отвечать на английском. Для удобства можно включить
перевод страницы в браузере.” Live helper wording is defined in BC-010.

### AI infrastructure panel — planned, not connected

A compact panel above the runtime journal may show server availability, model
name and state (unloaded/loading/ready/inference), GPU name, occupied/total VRAM
and power in W. Display measured values only, with stale/unavailable indication.
Server availability is separate from model readiness. Starting live mode may load
the model; availability checks must not load it. Recorded examples remain usable
independently of the station. Keep the live button in place when unavailable.

Connection recovery and execution state are separate. Candidate parameters, to be
validated in live integration: consecutive failed checks before declaring offline,
up to 30 seconds for automatic reconnection to the same run, and an inactivity
warning after 5 minutes of waiting for the user. Model loading/execution is not user
inactivity. Never resend a write or reset the environment on reconnect. Runtime
confirmation expiry retains authority. Expired sessions need explicit restart.
These are future transport/session requirements, not implemented behavior.
Access/security design is a separate task before public station connection; no
token, invitation or authentication mechanism is selected by this UI change.

## Reading and explanation refinement — 2026-10-19

The next accepted trial shows full original rationale outside disclosure, with
separate labels for UI summaries and original text. Technical details explain
what each source file/contract means. Consumed confirmations show disabled
Confirm/Reject controls with the recorded choice selected. No active consent
is offered in replay. Highlight changes for two seconds.

On mobile the conversation uses bounded internal scrolling with page-scroll side gutters and compact state above the messages, derived
from the same observation, a return link to full state and compact playback
controls. Desktop retains bounded internal streams. Scroll new messages to their
beginning. Runtime journal uses neutral light gray. Responsive acceptance pending.

A non-automatic “ⓘ Как это работает” dialog explains the five-stage flow and
value of separate model/operator/runtime responsibility. Use the same real-LLM
versus simulated-service explanation in it and the footer. The current build
explicitly remains recorded-only. Request provenance is defined in BC-010: the
short BC-008 phrase is illustrative for the older BC-006/007 runs.

Review 2026-10-20: follow BC-010 readability refinement for contextual G08 statuses,
FAIL example explanation, larger desktop header and compact mobile help.

### Recorded event linkage — 2026-10-23

Proposal and admission events retain distinct source IDs. The recorded projection
links them by the source trace's unique model-output `tick` and matching preflight
or revalidation `tick`, never adjacent event numbers. Ambiguous links fail export.
Details expose reciprocal proposal/check links only when the target is already
revealed. Navigation opens details, scrolls the target stream and highlights the
record for two seconds, without advancing playback or moving the desktop page.
The runtime journal explains its scope: checks/execution, proposals in chat.
The value explanation is shown on the welcome screen before mode selection.

Accepted refinement: use the compact brand header on home and both work modes;
remove OPERATOR WORKSPACE and the repeated responsibility line. The composer has
a very light gray-blue surround and a white editable field. Operator cards use
muted sage green with a darker author badge, consistently for goals, approvals
and refusals; this color identifies the actor, not execution success. Confirmation
controls remain distinctly darker. Live and recorded details share reciprocal
proposal/check navigation; live identifiers belong to their own event stream.

Accepted mobile/viewport refinement: mode entry and recorded-example selection
align the task toolbar to the viewport top, without scrolling on ordinary events.
The failure note retains both explanations with compact spacing. Both report
buttons open a modal, with close/Escape and focus returned to the trigger; opening
or closing a report never changes run state. On narrow screens an explicit event
link also brings the target panel into view when its record is off screen, then
highlights it. Visible targets and desktop links do not move the page. Mobile chat
gets more available viewport height through compact header/status spacing, not
smaller message text. Stop has a small visible circle and a 44px touch target.
Welcome spacing is reduced while preserving text and mode button touch sizes.

Final prototype spacing refinement: desktop task controls stay fully visible in
a compact toolbar; the failure explanation is one naturally wrapping paragraph.
On mobile, own-live-run access belongs beside/below home navigation, outside the
chat; terminal access says “Результат живого запуска”, active access retains the
server-derived confirmation countdown when connected. Navigation stays read-only.
The disabled composer sizes to its explanatory text, retaining its quiet italic
styling, border and wrapping without clipping; no free conversation is enabled.
Replay progress and its information control sit to the right of playback buttons
on mobile too; narrow viewports may wrap without overlap. Expanded event details
open above the controls without reducing the chat height.

### Local model review refinement — 2026-10-23

Shared live/replay proposal cards place “Краткое объяснение, сформировано
интерфейсом” before the deterministic summary and emphasize “Ответ агента” above
unaltered rationale. Disclosure uses the same small type size. Live timestamps
include date and time. Redundant simulated-service text is omitted from consent
controls; action identity and bindings remain intact.
Live status uses a quiet rounded badge: preparation, ready, executing, operator
confirmation, stopping or finished. Only preparation/execution animate; stop is
separate and visually subordinate, with an accessible touch target. Readiness
must not claim verified VRAM placement. Simulator labels do not claim model loading.
Desktop spacing accommodates the brand header and bounded panels where viewport
height permits; small screens retain scrolling and readable message text.
Welcome state is labelled initial; replay state is labelled recorded with dates
in disclosure. Live observation timestamps remain visible.
The live report summarizes the actual goal, terminal explanation, observed initial
and final state, recorded operator decisions and tool calls. Tool calls are not
labelled successful changes without result evidence; unknown write effects remain
explicit. No new inference is used to produce the report.

Accepted presentation refinement: compact author/source attribution in the header,
source link in both report modes, and a neutral welcome badge. Own live-result
access is a button beside home navigation on desktop and mobile, outside the
demo chat; mobile explicitly names the live result. Return remains read-only.
Preparation may say the first start takes several minutes, without promising
VRAM placement or a two-minute deadline. Motion respects reduced-motion settings.

### Responsive review and admission feedback — 2026-10-24

Mobile status shares a wrapping row with model identity; ready/preparation labels
are concise and timeout has a muted error tone on all viewports. Help text stays
secondary and readable. Versions/replicas remain expanded. Both modes expose an
explicit mobile chat anchor. Successful live entry/admission may scroll once to
chat and its state summary; polling must not move the page. Rejected admission
stays at its notice. Replay entry preserves scenario selection and failure context.
Latest command rejection and prior reservation expiry are separate facts: session
polling must not overwrite a newer busy/limit rejection with historical expiry.
Connection feedback may temporarily take precedence without losing that rejection.
Task outcome and termination reason have explicit labels; codes are diagnostic,
not a claim of service recovery. Report actions have independent spacing.
Brand attribution aligns to the brand text's right edge; platform title stays
centered. Replay warning is one wrapping paragraph with bold title and italic
explanation. Footer and secondary notes use compact spacing without overlays.

Mobile finishing review (2026-10-24): preparation includes model identity in its
compact status; other phases put provider/model on two lines beside controls.
Replay helper text is shorter on mobile, and its scenario explanation is 2px
smaller. Additional chat height comes from compact secondary content and a small
viewport-height adjustment. Native scrollbars remain visible when the platform
permits, with a reserved gutter and neutral thumb; no custom scroll implementation.
Initial degradation is emphasized in the compact state. Accessibility methodology
and audit scope remain a separate deferred decision, not part of this update.


### BC-012 initial dialogue composer

Keep short suggestions beside the input label when width permits, wrapping on
narrow screens. Use a two-line input that grows with text up to a bounded height.
Suggestions populate editable text only. Hide an informational suggestion after
its exact full query has a subsequent agent reply in the retained transcript;
do not infer answer quality or prohibit manually repeating a question.

Show `Обращения: n/5` beside the send timer and, to its right, the quiet terracotta explanation
`Восстановление начнётся только по вашему запросу.` After the fourth reply, show a dismissible modal once per dialogue, explaining
that one call remains and a final question ends the initial dialogue after its answer.
Dismissal sends no command, preserves draft text and does not pause server deadlines.
Remember dismissal across refresh in this browser tab; keep a muted red inline
warning with a circled exclamation mark. Close the modal if the dialogue expires.
The ordinary explanation and warning wrap on narrow screens. The fifth call may be a question or a recovery request;
there is no extra sixth call and no automatic recovery on budget exhaustion.
Simulator-specific explanation remains conditional on the provider kind.

### Preset entry feedback

A visitor without a session reads availability without creating a reservation.
SESSION_REQUIRED is not a connection failure: busy feedback persists across polls,
start is disabled while busy, and the recorded initial scenario state remains
visible and labelled as initial. Availability recovery enables a new explicit start.
Simulator guidance explicitly states that replies are predefined and no real LLM
is called; live-model guidance must not be shown for the simulator. The capacity
choice names stable replicas and full traffic. This refinement does not change
choice count, dialogue budgets or command submission semantics.

Preset informational choices disappear after their replies and return on a new
admission. Buttons use modestly reduced vertical padding; mobile touch targets
remain at least 44px. Operator release of initial dialogue is labelled explicitly
as operator stop without execution; OPERATOR_REQUESTED_STOP has a readable label.
