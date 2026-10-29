# BC-013 — Explicit recorded-only UI build

2026-10-29. Contract preparation; implementation and verification pending.
Current lifecycle is recorded in [specs router](../README.md).

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

Use one non-secret build-time setting: `VITE_APP_MODE`.
Accepted values: `recorded-only` and `live-enabled`.
An absent setting preserves existing behavior as `live-enabled`; any present
unsupported value, including empty, fails configuration/build with a clear error.
Development startup follows the same validation.

Resolve configuration before application initialization. It is immutable for
that loaded build. URL, storage, cookies and server responses cannot override it.
Do not infer mode by probing a server, and do not reuse a test-only loader override
as the production configuration. Keep the existing relative asset-base support.

## Recorded-only behavior

- Load only static recorded assets required for home, replay, journal and report.
- Do not initialize live status/session/run requests, polling, streams, commands,
  provider discovery or reconnect logic. Mount, idle, navigation and reload obey
  the same rule. No fallback to live API on an asset error.
- Ignore saved live-session hints without displaying their history or contacting
  a backend. Do not clear unrelated storage or claim to cancel a previous run.
- Normalize a stale live URL to the recorded home view; Back/Forward cannot restore
  a live screen. Existing recorded navigation remains available.
- Home offers recorded viewing without a live mode chooser. Hide live start,
  restart, stop, owner controls, composer and live return/result links.
- Historical operator decisions remain visible and clearly recorded; disabled
  historical confirmation displays may remain. They send no commands.
- Keep saved/synthetic labeling, source references, original model explanations,
  runtime checks, recovery-versus-completion distinctions and report access.
- Help/footer describe recorded viewing without live readiness, model loading,
  reconnection, temporary unavailability or promises of future live availability.
- Missing, malformed or unsupported recorded assets produce a truthful content
  error. Never fabricate success. Unavailable browser storage does not block viewing.

Live-enabled builds retain existing behavior and runtime authority. This change
does not change live input profiles, admission, confirmation or provider budgets.

## Acceptance and evidence

| Case | Expected result |
| --- | --- |
| Backend absent | Both saved outcomes, replay, journal and final report remain usable |
| Mount, idle beyond polling interval, navigation and reload | No live HTTP request, stream or command attempted |
| Stale live URL/history and seeded live storage | Recorded home fallback; no live restoration; recorded navigation works |
| Missing/malformed recorded data and denied storage | Clear content error or usable storage-independent view; no live fallback |
| Recorded UI | No actionable live controls or live-return promises; historical decisions preserved |
| Setting absent or live-enabled | Existing live tests and behavior preserved |
| Unsupported or empty setting | Build/development configuration fails before app startup |
| Relative base path | Static assets and report navigation work under a non-root path |

Use focused failing checks for the intended behavior before implementation.
Verify network absence at the transport boundary, not merely hidden buttons.
Exercise the real application entry/configuration, not only injected loaders.
Run UI tests, typecheck/build for both modes, recorded export consistency and
required repository regression gates. Record exact commands, revision and results.
Perform a static-server browser smoke with network observation and representative
desktop/mobile views; report any unavailable manual verification explicitly.
No real model call is needed. A build alone does not establish browser acceptance.

## Exclusions and completion

No hosting, public networking, authentication, runtime execution changes, new
recorded evidence, model evaluation, dependency upgrades or layout redesign.
No claim of public deployment readiness or prose correctness follows from this BC.

Update user-facing build instructions during implementation. Close with verification
evidence and human disposition; do not present this contract as implemented.
