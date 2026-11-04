# Governed Agent operator UI

One React UI supports saved synthetic runs and the bounded local live adapter.
Runtime authorization and execution remain server-owned. The UI does not certify
model explanations or turn recorded evidence into a new execution.

## Build and verify

From `ui/` (Node/npm are required):

```sh
npm ci
npm test
npm run build
```

The build writes `dist/`, including `LICENSE`, `NOTICE`,
`THIRD-PARTY-NOTICES.txt` and the bundled font license. Publish only reviewed output,
not the repository, local configuration or raw evidence directories.

From the repository root, check the two exported recorded examples:

```sh
python ui/scripts/export_runs.py --check
```

The assets are selected trace-derived projections of BC-006 success and BC-007
recovery FAIL / safe fallback. Original rationales and final reports are retained.
Source export is read-only with respect to historical evidence.

## Mode configuration (BC-013)

The application reads `app-config.json` beside `index.html` before initializing
live behavior. The same JavaScript/CSS build supports either exact configuration:

```json
{"mode":"recorded-only"}
```

```json
{"mode":"live-enabled"}
```

The supplied `public/app-config.json` enables existing **local** live launchers.
For autonomous static publication, replace `dist/app-config.json` with the
recorded-only object. Do this after each fresh build: Vite copies the supplied
local configuration again. No recompilation is required to change the output
configuration. The publication workflow must select its intended configuration
explicitly; this repository does not deploy a public site.

Recorded-only mode requests static assets only. It has no live status polling,
session restoration, live commands or owner controls. The home screen says:
“Живой режим сейчас недоступен. Вы можете посмотреть сохранённый пример.”
It does not say busy or promise a later opening. Saved confirmations remain
historical, disabled displays. Both examples, journal, replay and reports work
without a backend. Browser storage is optional (selected example only).

A missing/invalid configuration, failed request or timeout (3 seconds including
JSON decoding) falls back to recorded-only. Late responses cannot enable live
mode. Configuration is fetched without credentials, cache or redirect following.
Mode is fixed for that page load; published edits apply after reload/new opening
and hosting propagation. URL, cookies and browser storage cannot select live mode.
This file is public, contains no secrets, and is **not authorization or an emergency
shutdown**. A backend must independently enforce admission and permissions.

Assets use a relative base, supporting static hosting under a subdirectory.
For a local static preview, run `npm run preview -- --host 127.0.0.1` and open the
reported address. The local live adapter serves `dist/` and its relative `/api`
routes; see [local simulator instructions](../docs/local-ui-simulator.md).
Enabling live UI alone does not connect an external backend or configure access.

## Presentation and scope

Desktop state, chat and journal panels retain the accepted layout; mobile uses a
compact service summary and bounded message scrolling. “Как это работает” opens
only on request. Replay distinguishes model proposals, checks, historical operator
confirmations, tool calls and accepted observations. “К результату” exposes the
unchanged recorded outcome and final report. Selecting another example resets
playback. No inference occurs while browsing saved examples.

Authority: [BC-013](../specs/bounded-changes/bc-013-recorded-only-build.md),
[BC-010](../specs/bounded-changes/bc-010-recorded-run-ui.md), and the
[live contract](../specs/core/live-ui-runtime-contract.md).
