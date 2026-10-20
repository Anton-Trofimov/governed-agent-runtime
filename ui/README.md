# Operator UI — BC-010

Local static viewer of two recorded synthetic runs. No live calls, execution,
login or hosting integration. Source authority: `specs/bounded-changes/bc-010-recorded-run-ui.md`.

## Develop

Use Node 24 (implementation checked with 24.19.0) and npm. From `ui/`:

```bash
npm ci
npm run dev
```

Open the local URL printed by Vite. For another device on the same trusted LAN,
use the computer's LAN address and the printed port; firewall/access may need
configuration. This static viewer has no authentication. Do not expose a live
runtime through these development instructions.

## Verify and build

```bash
npm test
npm run build
```

The build is `ui/dist/`; relative asset URLs support a domain root or subdirectory.
Serve it with an HTTP server, not by double-clicking `index.html` (JSON is fetched).
From `ui/dist/`, with Python installed:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Open http://localhost:8000. On Windows, `py` may be used instead of `python`.
The build needs no Node, Python runtime APIs or Ollama after static hosting.

## Regenerate/verify recorded assets

From the repository root, with project Python dependencies installed:

```bash
PYTHONPATH=src .venv/bin/python ui/scripts/export_runs.py
PYTHONPATH=src .venv/bin/python ui/scripts/export_runs.py --check
```

The exporter reads only the two declared evidence directories and uses BC-009
`build_view` / `render_text`. `public/runs/*.json` contains generated views,
reports, selected chronological trace events and evidence hashes; it is not a
new measured run. Do not edit by hand.
Only selected run ID is persisted in local storage. No accounts or task history.

## Human visual review still required

Automated component tests use jsdom, not browser layout. Check both runs at 390,
768 and 1440 CSS pixels, keyboard focus, touch controls, enlarged text, report
expansion and lack of page-wide overflow. This environment has no supported
browser-control plugin, so actual browser visual/responsive QA was not performed.

## Recorded demonstration

The React workspace follows the accepted r8 sketch: dark service state, a chat-shaped
recorded timeline, and runtime journal. Select “Посмотреть пример”, then choose the saved demonstration. “Далее” advances one recorded event; “К результату” shows the final
BC-009 outcome; “К началу” resets playback. Historical confirmations are text only.
The dashboard uses the most recent accepted observation at the replay cursor.
No model inference, tools, live confirmation or cancellation are connected.
Live prompt input and suggestions are hidden until live mode is available.
The versions table is always visible. Safety conditions default open on desktop
and closed on mobile. Version summary and total traffic remain visible. Original model rationale remains in its source language.

On desktop the bounded chat and journal scroll independently; mobile chat uses
bounded internal scrolling, side gutters and a compact service summary. Event summaries explain the
action; original model rationale remains visible, while details retain actual gate
statuses/IDs and explained contract references. Changed values are emphasized
for two seconds.
“Открыть итоговый отчёт” opens the unchanged BC-009 report at completion.
Infrastructure telemetry, reconnection and access/security are documented future
work only; no station connection or live session mechanism is implemented.

“Как это работает” opens an explanatory dialog without auto-opening. Historical
confirmation buttons are disabled. The opening “Восстанови работу сервиса” is
explicitly a demonstration phrase from BC-008, not a recorded request of the
BC-006/007 evidence. Full model explanations are preserved verbatim.
