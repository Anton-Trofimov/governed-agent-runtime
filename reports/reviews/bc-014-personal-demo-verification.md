# BC-014 personal launcher — offline verification

Date: 2026-11-11. Accepted base: `c4ba6da` (BC-013).
Implementation is identified by the commit containing this report / its PR head.
Status: offline checks passed; owner reported station acceptance 2026-11-11.

## Verified

- 410 Python tests passed, including 24 new personal-launcher cases.
- Ruff and git diff whitespace checks passed.
- 94 existing UI tests passed; TypeScript/Vite build and recorded export check passed.
- Actual `--prepare` completed; subsequent CLI cancellation used that prepared
  build without test/build/provider execution.
- Case-insensitive confirmation, invalid-input re-prompt, missing/stale/tampered
  build rejection, occupied port, shared coordinator exclusion, recovery refusal,
  stop/probe/start failures, preservation of uncertainty on failed restart.
- A real subprocess with an injected non-model blocking provider was terminated
  mid-call. The replacement service retained quarantine; mocked administrative
  recovery then allowed a new explicit fake-provider call. No old goal replay.
- Repeat normal start, unavailable-provider cleanup, no two-preparation allowance,
  unchanged inference/confirmation limits, cleanup isolation and preservation of
  old research instructions/launcher during shortcut installation.

## Boundaries

No actual Ollama inference, system-service stop/start, GPU measurement or station
modification was performed. Administrative recovery calls were mocked. It remains
necessary to check one real showing and interrupted/repeated startup on the owner's
Linux/WSL systemd station. A cold model still needs load time; no one-second inference
claim. Existing per-session retention/dialogue/run limits remain.

No UI/source assets, research launcher/provider/runtime implementation, historical
evidence, Pages repository, deployment pin, DNS or public service were changed.
The new CLI reuses those components with a separately specified personal lifecycle.
An existing Starlette test-client deprecation warning remains non-blocking.

Tests were added with this implementation; an independently recorded pre-implementation
RED run is not claimed. Initial validation found and corrected explicit subprocess
check flags and import ordering before the complete passing run.

## Owner station check — 2026-11-11

Owner reports the personal launcher working and both local entries usable without
the two-preparation smoke quota. Supplied terminal output shows affirmative `y`
accepted, followed by explicitly confirmed service recovery and successful startup.
This confirms recovery integration on the station, not automatic cancellation of
provider computation. Owner requested clearer yes/no prompting; accepted short
answers and case-insensitive behavior remain unchanged. Other UI stop-behavior
observations were explicitly deferred and are not claimed resolved here.
No station raw records were imported and no old evidence was deleted.
