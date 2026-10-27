# Current Development Status

Non-normative handoff. Specifications and recorded evidence remain authoritative.
This file is not model-visible operational evidence.

## Preset entry feedback — 2026-10-27

Anonymous live visitors poll availability without creating a session or reservation.
Busy feedback persists, disables admission, and clears when capacity becomes available;
SESSION_REQUIRED no longer appears as transport loss. Recorded initial state remains
labelled as initial. Capacity-choice wording and simulator/model guidance are distinct.
Choice count, budgets and submission semantics are unchanged. Verification: 374 Python
tests, 73 UI tests, Ruff and UI build pass; no station inference performed.

## Server-selected input profile — 2026-10-27

Implemented `preset-only` as the service/CLI default, with explicit
`local-free-text` opt-in. Fixed command IDs resolve on the server; invalid input
is rejected before model invocation. Informational choices cannot admit recovery.
UI follows server metadata; model smoke approval must match the input profile.
See [transport contract](../specs/core/live-ui-runtime-contract.md#server-selected-input-profiles)
and [local startup](../docs/local-ui-simulator.md).
Loopback transport, private evidence and existing smoke budgets remain unchanged;
this change does not establish deployment readiness. No station inference performed.

## BC-012 closure preparation — 2026-10-26

**Accepted for bounded local use; documentary closure prepared for PR.**
Owner reviewed `8941d67a45d80b193e3ffd92c8b7ad09a62cc206` and approved closure.
[Disposition and concise results](../reports/decisions/bc-012-initial-dialogue-disposition.md)
record automated checks separately from owner-observed station smokes and limits.

Initial dialogue supports five calls without automatic remediation; goal admission
preserves original operator text and existing action-bound confirmations. Navigation
preserves preparation/dialogue without another admission or renewed deadlines.
Final owner checks observed nominal completion and explicit non-action/hypothetical
questions without execution. Two-preparation limits were visible across browsers.
Offline checks: 366 Python tests, 71 UI tests, Ruff, build, recorded export and diff
PASS. No model call or station-marker removal performed during closure.

Residual prose inaccuracies, new-composer mobile review and status-text contrast
remain deferred. Semantic classification is model-dependent; raw station evidence
stays private. No public access, GPU scheduler or deployment is included.
Next: PR verification and owner merge decision; choose any next bounded scope
separately. BC-011 remains the merged baseline until BC-012 integration.

## BC-011 closure — 2026-10-24

**Accepted as a bounded local integration with recorded limitations.**
Owner accepted UI baseline 02ca894 and requested documentary closure and PR/merge.
[Disposition and concise results](../reports/decisions/bc-011-live-ui-runtime-disposition.md)
separate automated verification, owner-observed station behavior and remaining gaps.

Loopback-only UI/backend connects a pinned local Ollama model to the existing
modeled payment-api runtime. Action-bound confirmations, one active slot, session
ownership, idempotency, deadlines and uncertain-provider quarantine are retained.
Recorded examples remain independent. Two preparations per approved local package
are a smoke budget, not public visitor quotas.

Verification: 337 Python tests, 63 UI tests, Ruff, TypeScript/Vite build, recorded
asset consistency and diff checks PASS. Offline tests do not call a real model.
Owner observed successful recovery, refusal and confirmation expiry during station
smokes and accepted the current desktop/mobile presentation. Full private trace
review and exhaustive device/accessibility coverage are not claimed.

Known boundaries: arbitrary initial questions are not separated from recovery
goals; no free dialogue during execution; no public admission/abuse protection or
GPU arbitration with unrelated Ollama clients. Public exposure is not authorized.
[Startup and limits](../docs/local-ui-simulator.md).
Integration status and CI are recorded in [PR #12](https://github.com/Anton-Trofimov/governed-agent-runtime/pull/12).

BC-011 merged through PR #12 at `668a50e`.
Next: [BC-012 initial dialogue](../specs/bounded-changes/bc-012-initial-dialogue-and-goal-admission.md).
The owner approved its design and resource bounds with a limit of 5 pre-execution
model calls. Local fake-provider implementation is recorded above.
Real inference requires separate revision-bound approval.

## Accepted operator presentation — 2026-10-21

BC-009 content/projection accepted; BC-010 basic desktop/mobile design accepted
at `6637dc9`. Human requested concise documentary closure of both BCs. See
[BC-009 decision](../reports/decisions/bc-009-operator-outcome-disposition.md) and
[BC-010 decision](../reports/decisions/bc-010-recorded-run-ui-disposition.md).
Cosmetic iteration stops here; full browser/accessibility coverage and external
usability are not claimed. BC-009 merged via PR #10 at `215f7b2`. BC-010 delivery
is tracked in [PR #11](https://github.com/Anton-Trofimov/governed-agent-runtime/pull/11);
GitHub PR state is authoritative for integration status. Connector publication
uses new commit SHAs with verified identical source trees; local review revisions
remain provenance references. CI includes Python and UI tests/build/export checks.
Latest implementation verification: 28 UI tests, 290 Python tests, Ruff,
TypeScript/build, deterministic export and diff PASS.

The viewer is recorded-only. It distinguishes proposals, runtime checks, operator
decisions and accepted observations. Preserve original explanations and source
references, unknown-effect warnings and the difference between stopped execution
and recovered service. Initial demo text is illustrative, not an archived request.

Next: plan a separate local live UI/runtime BC. One operator/run; real inference,
modeled service. Specify start/events, exact-action confirmation, refusal/expiry,
cooperative stop and new-environment restart. Existing confirmation is a blocking
callback; arbitrary text must not become consent. Reconnect must not replay writes.
Public access/security, hosting and GPU telemetry remain separate decisions.

### Deferred non-normative hypothesis

Explicit structured dependencies → simple deterministic CI checks → later
agent-assisted consistency audit. Evaluate usefulness through actual incompatibilities
caught, false positives, maintenance cost and reduction in manual checking.
The empirical candidate boundary is **runner output contract → presentation layer**:
BC-009 already consumes recorded runner outputs. Open automation only through a
separate BC when a concrete need or change to that contract arises. No dependency
manifest/graph, new CI checks, post-merge agent audit or automatic project-map
construction is authorized by this hypothesis.

### Previous checkpoints

BC-006 merged through [PR #7](https://github.com/Anton-Trofimov/governed-agent-runtime/pull/7),
main `d636d2d3062af0dcb374710b63a16bde3d88766a`; PR verify CI succeeded.
BC-007 documentary closure requested by the human at 17:54:03 +03:00:
**ACCEPTED WITH RECORDED CAVEAT for one synthetic FAIL→STOP trajectory.**
[Measured review](../reports/reviews/bc-007-run-001-measured-review.md),
[decision](../reports/decisions/bc-007-recovery-failure-disposition.md),
[evidence/integrity](../evidence/bc-007-recovery-failure/README.md).
Evaluated revision `5fa93b14ee8306e13e1c38990e306128eea5faed`.
5 model calls, 6 tools, 2 confirmed writes, 0 rejections; SAFE_FALLBACK /
MODEL_REQUESTED_STOP, task_completed=false. Candidate preserved.
Read-repeat argumentation caveat retained; adaptation after rejection NOT OBSERVED.
Pre-run review and packet remain unchanged historical snapshots.

BC-007 merged via PR #8; verify CI PASS; main
`84822d64bc1203147cde3f849a2f1c6222df9f4c`.
Next selected design: [BC-008 operator goal framing](../specs/bounded-changes/bc-008-operator-goal-framing.md),
two requests × three paired seeds in nominal recovery PASS environment.
Implementation and offline controls complete (2026-10-13): 275 tests/Ruff/diff PASS.
[Human pre-run review](../reports/reviews/bc-008-pre-run-review.md) approved
2026-10-13 02:06:08 +03:00. Measured evidence received: six completed trajectories
plus one KeyboardInterrupt-interrupted A-20; explicitly requested retry retained
separately. 33 actual model calls total, no new calls during review.
[Measured review](../reports/reviews/bc-008-measured-review.md): identical action
sequences across completed A/B pairs; rationale numerical/semantic caveats retained.
Human disposition 2026-10-13 03:30:46 +03:00: ACCEPTED WITH RECORDED CAVEATS.
[Documentary closure](../reports/decisions/bc-008-operator-goal-framing-disposition.md)
prepared; PR/merge pending. Next recommendation: bounded operator outcome
presentation, using existing evidence; no new measured experiment approved.
Deferred: visible STOP explanation and explicit field definitions. No SDD change.

### Branch audit — 2026-10-12

Remote main: `d636d2d3062af0dcb374710b63a16bde3d88766a`.
Five old branch heads are ancestors of main (GitHub compare branch→main:
behind_by=0) and their PRs are merged:

- `bc-005-s12-prospective-grounded-assessment` — PR #3.
- `bc-005-d1-self-review` — PR #4.
- `bc-005-d2-human-review` — PR #5.
- `bc-005-d3-judge-diagnostic` — PR #6.
- `bc-006-bounded-remediation` — PR #7.

These branch refs are candidates for removal; history/evidence remains on main
and in merged PRs. No branches deleted in this audit. Keep main and active
`bc-007-recovery-failure` until its own integration; no open PR currently exists.

## Historical checkpoint — 2026-10-06

BC-005 measured baseline is closed with human-confirmed material semantic failure:
`NOT SUPPORTED FOR THIS BOUNDED FIXTURE / MODEL / CONFIGURATION`.
Evaluated revision: `f033f04820e1d044c72da0d2682cc62e99b73936`.
Canonical pool: 0/3 semantic PASS; automatic checks and runtime containment 3/3 PASS.
No execution/state mutation. Runtime did not detect the free-text ordering failure.
BC-003 disposition remains INCONCLUSIVE — EVALUATION_DESIGN_CONFOUNDER.

- Canonical evidence: `evidence/bc-005-s12-prospective-grounded-assessment/`.
- Evidence report: `reports/bc-005-s12-prospective-grounded-assessment-evidence.md`.
- Human adjudication: `reports/reviews/bc-005-s12-post-run-review.md`.
- Decision: `reports/decisions/bc-005-s12-prospective-grounded-assessment-disposition.md`.
- BC-005 integrated through PR #3; CI #9 PASS; merge `bc91ed5df96b3952cc7a2ee4e2f0f928eeb5e4e2`.

## BC-005-D1 closure — 2026-10-07

D1 completed one excluded preload + three measured calls at
`cd58890caebf7267b523db37ffd92390499a2e41`. Human accepted the complete review on
2026-10-07 and authorized documentary closure/publication/merge through PR #4.
Disposition: NOT SUPPORTED for this bounded fixture/model/configuration.
Semantic 0/3; automatic checks and runtime containment 3/3 PASS. All finals are
identical and repeat the pre-shift ordering/health-checkpoint failure.

- Evidence: `evidence/bc-005-d1-self-review/` (original bytes plus separate adjudication).
- Report: `reports/bc-005-d1-self-review-evidence.md`.
- Human review: `reports/reviews/bc-005-d1-post-run-review.md`.
- Decision: `reports/decisions/bc-005-d1-self-review-disposition.md`.
- Historical pre-run review and original pending offline evaluations remain snapshots.
- No further D1 inference or prompt iteration.

## BC-005-D2 closure — 2026-10-08

One manual observation outside the project, exact D1 scenario input, passed all
six semantic criteria. Human explicitly APPROVED the review and requested closure.
Configuration and provenance remain in the linked review materials. Schema and
bounded contract checks PASS; governed runtime NOT RUN; containment NOT ASSESSED.

- [Human review](../reports/reviews/bc-005-d2-post-run-review.md).
- [Evidence report](../reports/bc-005-d2-independent-codex-evidence.md).
- [Decision](../reports/decisions/bc-005-d2-independent-codex-disposition.md).
- Final adjudication: `evidence/bc-005-d2-independent-codex/adjudication/human-assessments.json`.
- Original pending agent assessment/provenance remain historical snapshots.
- Two earlier in-project attempts are excluded; one positive observation is not
  a controlled model benchmark or a general reliability result.

## BC-005-D3 closure — 2026-10-08

Two isolated Qwen judge calls completed; exact kit requests/hashes and finals verified.
Both returned PASS. A missed the known D1 material violation; B agrees with the
accepted D2 review. Disposition NOT SUPPORTED for this bounded judge configuration.
User supplied approval with results, then requested closure after the analysis.

- [Evidence](../reports/bc-005-d3-independent-judge-evidence.md).
- [Post-run review](../reports/reviews/bc-005-d3-judge-post-run-review.md).
- [Decision](../reports/decisions/bc-005-d3-independent-judge-disposition.md).
- Immutable original pool: `evidence/bc-005-d3-independent-judge/`.
- Original pending pre-run/kit labels remain historical; closure does not rewrite them.

## BC-006 documentary closure — 2026-10-12

**ACCEPTED for one nominal synthetic trajectory; documentary closure complete.**
Run-001 human acceptance: 2026-10-12 01:18:14 +03:00. Closure requested at
01:47:39 +03:00. Evaluated revision: `a4eb739017b058a8d2b425db4942f7c722f1eb98`.
5 actual Qwen calls, 9 tools, 3 individually confirmed writes, 0 rejections;
runtime-verified COMPLETED. Recovery-after-rejection NOT OBSERVED.

- [Accepted measured review](../reports/reviews/bc-006-run-001-measured-review.md).
- [Original evidence / integrity](../evidence/bc-006-bounded-remediation/README.md).
- [Closure decision and findings](../reports/decisions/bc-006-bounded-remediation-disposition.md).
- [Non-normative pre-run human-review aid](../reports/reviews/bc-006-human-review-state-snapshots.md).
- [Historical exact pre-run review](../reports/reviews/bc-006-pre-run-review.md),
  generated packet and pending template remain unchanged; their labels are historical.
- Fixed goal/rules and synthetic adapters: no natural operator UX, independent
  strategy selection, general reliability, production or model-comparison claim.
- Last implementation verification: 259 tests, Ruff and diff checks PASS locally;
  documentary closure verification is recorded in the pre-PR handoff. No remote CI claim.
- Integrated through PR #7 after explicit human PR and merge decisions. No new
  model calls, runtime/contracts changes or reusable SDD changes in that closure.

## Station evidence convention

For future external staging use:
`/home/anton/projects/evidence/governed-agent-runtime/<bounded-change>/<unique-run-id>/`.
Each pool retains its manifest.json, preload/ and attempts/. Never overwrite or mix
pools. Existing station folders have not been moved automatically. Accepted evidence
may be copied unchanged into the repository for reproducibility after pool completion.

## Verification and authority

Use `.venv/bin/ruff check .`, `.venv/bin/pytest`, `git diff --check`.
Keep measured RAW/RESULT/manifest bytes immutable. Record new adjudication separately.
Review/approval is not operational execution authorization. No production safety,
general reliability or user/business-value claim is established by this baseline.
