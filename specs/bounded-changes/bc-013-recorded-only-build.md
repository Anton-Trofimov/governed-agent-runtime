# BC-013 — Explicit recorded-only UI configuration

2026-10-30. Runtime configuration and unavailable-mode notice approved by owner.
Implemented with automated and bounded browser verification; human acceptance pending.

## Intent and dependencies

A static build must let a reader explore saved synthetic runs without a backend
and without attempting live API access.

Baseline: PR #14 merge `b1f1f9445f2c4c1689d73fb080fd4f0d542af74b`.
Preserve [BC-010](bc-010-recorded-run-ui.md) recorded projection, replay and report
semantics, [operator UI design](../core/operator-ui-design.md), and the existing
[live transport contract](../core/live-ui-runtime-contract.md) in live-enabled builds.

Within recorded-only builds this BC supersedes earlier presentation requirements
to retain a disabled live entry or return-to-live control. Historical evidence and
previous acceptance records are unchanged. This is not a backend authorization control.

## Configuration contract

Use one frontend build with a non-secret static `app-config.json` next to the
site entry point. Schema: exactly `{ "mode": "recorded-only" }` or
`{ "mode": "live-enabled" }`. Read it before mounting the application, using the
relative asset base, no credentials, no cache and no redirect following.
Allow at most 3 seconds including response decoding. Missing, malformed, unknown,
failed or timed-out configuration resolves to recorded-only. A late response must
not enable live mode after fallback. No API probing is permitted to infer mode.

The resolved mode is fixed for this page load. URL/history/storage/cookies cannot
override it. Editing the published configuration applies on reload/new opening,
subject to hosting propagation; no automatic polling or hot switching. This is
presentation configuration, not backend authorization or an emergency control.

The repository supplies `live-enabled` for existing local launchers. Autonomous
publication explicitly replaces only the output configuration with `recorded-only`;
no recompilation is necessary. Missing configuration is always recorded-only.
Do not place credentials, private endpoints or operational settings in this file.

## Recorded-only behavior

- Load only static recorded assets required for home, replay, journal and report.
- Do not initialize live status/session/run requests, polling, streams, commands,
  provider discovery or reconnect logic. Mount, idle, navigation and reload obey
  the same rule. No fallback to live API on an asset error.
- Ignore saved live-session hints without displaying their history or contacting
  a backend. Do not clear unrelated storage or claim to cancel a previous run.
- Normalize a stale live URL to the recorded home view; Back/Forward cannot restore
  a live screen. Existing recorded navigation remains available.
- Home offers recorded viewing without a live mode chooser. Display the neutral
  notice “Живой режим сейчас недоступен. Вы можете посмотреть сохранённый пример”.
  Do not describe this as busy or promise later availability. Hide live start,
  restart, stop, owner controls, composer and live return/result links.
- Historical operator decisions remain visible and clearly recorded; disabled
  historical confirmation displays may remain. They send no commands.
- Keep saved/synthetic labeling, source references, original model explanations,
  runtime checks, recovery-versus-completion distinctions and report access.
- Help/footer describe recorded viewing without live readiness, model loading,
  reconnection, temporary unavailability or promises of future live availability.
- Missing, malformed or unsupported recorded assets produce a truthful content
  error. Never fabricate success. Unavailable browser storage does not block viewing.

Live-enabled configuration retains existing behavior and runtime authority. This change
does not change live input profiles, admission, confirmation or provider budgets.

## Acceptance and evidence

| Case | Expected result |
| --- | --- |
| Backend absent | Both saved outcomes, replay, journal and final report remain usable |
| Mount, idle beyond polling interval, navigation and reload | No live HTTP request, stream or command attempted |
| Stale live URL/history and seeded live storage | Recorded home fallback; no live restoration; recorded navigation works |
| Missing/malformed recorded data and denied storage | Clear content error or usable storage-independent view; no live fallback |
| Recorded UI | No actionable live controls or live-return promises; historical decisions preserved |
| Explicit live-enabled configuration | Existing live tests and behavior preserved |
| Missing, invalid, failed or timed-out configuration | Recorded-only fallback, no live API access, neutral unavailable notice |
| Relative base path | Static assets and report navigation work under a non-root path |

Use focused failing checks for the intended behavior before implementation.
Verify network absence at the transport boundary, not merely hidden buttons.
Exercise the real application entry/configuration, not only injected loaders.
Run UI tests, typecheck/build and exercise both configurations of that same build, recorded export consistency and
required repository regression gates. Record exact commands, revision and results.
Perform a static-server browser smoke with network observation and representative
desktop/mobile views; report any unavailable manual verification explicitly.
No real model call is needed. A build alone does not establish browser acceptance.

## Exclusions and completion

No hosting, public networking, authentication, runtime execution changes, new
recorded evidence, model evaluation, dependency upgrades or layout redesign.
No claim of public deployment readiness or prose correctness follows from this BC.

Include root LICENSE, NOTICE and notices for bundled dependencies/fonts in the
output. Update user-facing build instructions during implementation. Close with verification
evidence and human disposition; do not present this contract as implemented.
