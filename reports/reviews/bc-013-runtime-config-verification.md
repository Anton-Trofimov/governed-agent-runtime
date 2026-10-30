# BC-013 runtime configuration verification

2026-10-30. Implementation reviewed at
`73bb7920c54e660549e7f681997694bd237578d7`, based on accepted main
`b1f1f9445f2c4c1689d73fb080fd4f0d542af74b` and the existing BC-013 draft.
Status: automated checks passed; browser verification and human acceptance open.

## Scope and result

One build reads a static mode file before live initialization. Missing, invalid,
failed or timed-out configuration selects autonomous recorded viewing. The home
notice says live mode is unavailable, not occupied, with a recorded-example
alternative. Explicit live-enabled configuration preserves the local adapter.
Runtime policy, evidence and authorization code are unchanged.

The focused RED test used saved live history with the real default loader.
Before implementation it restored LiveWorkspace instead of the recorded home
and failed to find the example entry. After implementation the same test passes,
including both recorded outcomes, report access, stale history and ten simulated
seconds of idle time without a live API request. Existing tests now explicitly
select live-enabled where they exercise that behavior; their assertions remain.

## Checks executed

Environment: Python 3.12.14, Node 24.22.1, npm 11.9.0. UI dependencies from the
existing lockfile; isolated Python virtual environment installed with `.[dev,live]`.

| Check | Result |
| --- | --- |
| `npm test` in ui | 12 files, 94 tests PASS |
| `npm run build` in ui | TypeScript and Vite PASS; notices packaged |
| `python ui/scripts/export_runs.py --check` | PASS; saved projections unchanged |
| `ruff check .` | PASS |
| `pytest` | 386 PASS; one existing Starlette/httpx deprecation warning |
| `git diff --check` | PASS |
| Artifact inspection | 11 files; root LICENSE/NOTICE byte-identical; React, React DOM, Scheduler and Zod license texts included; font notice present; no source maps; relative entry assets resolve in output |

The bundled JavaScript SHA-256 was
`ab97b2ea6d2e0c9a28de1f165b1e388b28be1c4e35b935bc6233a7121e4f4503`.
The supplied output config is live-enabled for local compatibility. An autonomous
publication must explicitly select recorded-only in its output config; a fresh
build restores the supplied local configuration. This is documented in ui/README.

Tests cover configuration schema failures, request/JSON failure, bounded response
decoding, ignored late responses, initialization barrier, remount, stored history,
recorded content validation failures and denied browser storage. Assertions observe
fetch calls, not only button visibility. Static requests are allowed.

## Limitations and remaining review

Real-browser execution was attempted using Playwright, but Chromium was absent
and its download repeatedly returned invalid ZIP archives. No browser smoke,
subdirectory network capture or desktop/mobile visual acceptance is claimed.
Automated jsdom checks and relative asset inspection do not substitute for these.
Before acceptance, serve the built output under a subpath and inspect at 390, 768
and 1440 CSS pixels: both examples, reports, reload/history, more than one polling
interval idle, configuration failure, and zero live API requests in recorded-only.
Also verify explicit live-enabled local behavior in the browser.

No real model calls, hosting, public exposure, backend access-control changes,
full security certification or human disposition occurred. Existing model-prose
limitations and historical evidence are unchanged. The PR remains a draft.
