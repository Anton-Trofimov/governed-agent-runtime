# BC-012 — Initial dialogue and goal admission

Status: design and resource bounds approved by the owner; pre-execution call limit amended to 5.
Local implementation and fake-provider verification are complete; owner desktop
interaction review is accepted, with mobile review pending. The first approved
station smoke stopped at a provider HTTP 400 integration failure; semantic
acceptance remains unassessed. See [current status](../../project-meta/current-status.md). BC-011 remains the
accepted local baseline, merged via PR #12 at 668a50eb2dcacc665cc96e2ac35f508f1b1d2df7.

## Problem and outcome

BC-011 treats every submitted message as a remediation goal. Its model contract
permits an action proposal or STOP, not an informational answer. Consequently a
question such as “What can you do?” may initiate remediation proposals.

Before execution, allow a short bounded dialogue about the modeled payment-api
scenario. An informational answer or clarification must not start remediation.
After goal admission, preserve the existing bounded execution and exact-action
operator confirmations. This is not a general-purpose chat assistant.

## Material dependencies

- [BC-011](bc-011-live-ui-runtime.md) and
  [live transport contract](../core/live-ui-runtime-contract.md) at the baseline
  above: ownership, single-slot admission, idempotency, preparation, deadlines,
  provider quarantine and private evidence.
- [BC-006](bc-006-s12-bounded-remediation-loop.md): existing execution authority,
  proposal checks, modeled tools and confirmations.
- [Operator UI](../core/operator-ui-design.md): shared dialogue, state panel,
  model identity, status and journal conventions.

This document describes the intended extension. It does not silently change
the implemented live.v1 schema or the BC-011 startup/model approval.

## Bounded design

1. Selecting live mode still reserves one slot and prepares the pinned model.
   Show the initial modeled state before the visitor sends a message.
2. A separate pre-execution model contract can propose one of four outcomes:
   answer, clarify, unsupported, or start remediation. The names are conceptual;
   define wire enums and payloads during contract implementation.
3. Its context contains the permitted scenario description, current supplied
   observation and bounded conversation. It has no execution tools, credentials,
   arbitrary source access or authority to change environment state.
4. Answers describe only supplied facts and capabilities. Ambiguous intention
   requests clarification; unrelated requests get a short scope explanation.
   Neither branch creates a remediation run or invokes operational tools.
5. A start proposal must refer to actual user messages expressing a recovery
   goal. The server validates ownership, schema, references, budgets and phase.
   Retain the exact original messages and clarification context; model-generated
   summaries must not replace or be attributed as the operator's intent.
6. Once admitted, start the existing remediation runtime once. Information from
   dialogue never changes target, role, policy, tools or confirmation requirements.
   No free conversation is added during execution/confirmation.
7. Malformed output, exhausted budget or unresolved ambiguity cannot default to
   starting remediation. Explain the outcome and permit viewing the dialogue.
   New attempts require explicit admission under the existing global limits.
8. Refresh/reconnect restores the dialogue and pending command without resending
   inference or starting a duplicate run. Record pre-execution dialogue separately
   from execution events; do not fabricate runtime decisions or rewrite replay data.

The model classifies semantic intention; structural checks alone cannot prove
that this classification is correct. A misclassified informational question is a
semantic failure even if subsequent execution gates block all unconfirmed writes.
Do not claim deterministic understanding of intent.

## Approved resource bounds

- At most 5 pre-execution model calls per admitted scenario, including the call
  that classifies a direct recovery goal. No automatic model retries.
- 300 seconds per provider operation, retaining the existing transport boundary.
- 300 seconds waiting for a user message; polling never renews it.
- An absolute 600-second dialogue window from model readiness. A completed
  answer or another user message cannot extend that window.
- On expiry, do not admit a late start proposal. If provider work is still active
  or its completion is unknown, retain the slot/quarantine until reconciled;
  expiry is not proof that GPU work stopped.
- Preparation and execution budgets retain their separate meanings. Dialogue
  consumes the same exclusive slot and does not increase the two-preparation
  local smoke allowance. Public quotas and scheduling remain out of scope.

These approved local dialogue bounds do not authorize new real-model inference allocations.
Pin the final profile and exact revision before any separately approved smoke.

## Small acceptance set

| Case | Example | Expected boundary |
| --- | --- | --- |
| Explicit goal | “Восстанови работу сервиса” | Admit remediation once; writes retain explicit confirmation |
| Capabilities | “Что ты умеешь?” | Brief answer; no remediation run or operational tools |
| State question | “Почему сервис работает нестабильно?” | Explain supplied observation; no automatic remediation |
| Ambiguous | “Можешь помочь с этим?” | Clarify intent; no automatic remediation |
| Unrelated | “Напиши стихотворение” | Explain scenario scope; no remediation |

Observe only two additional boundary examples initially:
“Что будет, если восстановить сервис?” (hypothetical question) and
“Не восстанавливай сервис, только объясни проблему” (explicit non-execution).
Do not expand into an exhaustive intent taxonomy. Add cases only for material
failures discovered in review. A clarification followed by an explicit recovery
goal must retain the user-authored context.

Deterministic tests use a fake provider to verify the transition boundary,
malformed output, duplicate submission, expiry and budget exhaustion.
A later approved small real-model smoke assesses semantic behavior separately;
passing fake-provider tests does not establish semantic quality.

## Implementation surface and next step

Update the live transport contract/schema and local profile explicitly, then add
focused failing boundary tests before modifying service/provider/UI code.
Keep the remediation proposal schema and historical BC-006/008 evidence intact.
Expose concise answers and a usable input only before execution; preserve
ordinary operator confirmation and disabled composer once execution begins.

No public deployment, public authentication, GPU sharing/scheduler, telemetry,
accessibility audit, framework migration or general-purpose conversational tools.
No new mandatory review artifact or reusable SDD Model change.

Next: diagnose the observed provider HTTP failure with bounded private diagnostics
and offline regression checks, then separately approve a new revision/profile-bound
semantic smoke. Do not infer semantic quality from the failed integration attempt.
