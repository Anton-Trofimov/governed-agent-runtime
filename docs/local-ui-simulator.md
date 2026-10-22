# Local UI/runtime simulator

BC-011 implementation check, not real LLM inference or experimental model evidence.
Linux/WSL, one backend process, one active modeled run. The provider follows a
fixed nominal recovery path regardless of the entered goal. Runtime policies,
explicit confirmations and modeled operations are real application code.

From the repository with its virtual environment activated:

```sh
python -m pip install -e '.[dev,live]'
npm ci --prefix ui
npm --prefix ui run build
python -m governed_agent_runtime.live_http --evidence-dir "$HOME/.local/state/gar-ui-simulator"
```

Open `http://127.0.0.1:8000` in a browser supporting Web Locks. Use that exact
origin. The entry point runs Python verification before serving; it binds only
loopback and has no real-provider switch. A static Python file server still
supports recorded examples but cannot run the interactive simulator.

Choose live mode: that single action requests admission and preparation. The
initial service state is visible before submitting a goal, independently of
provider readiness. Submit a goal and approve or
reject each proposed change. Nominal completion requires three approvals.
Refresh restores the same session/run; tabs in the same browser profile share
ownership. Use another browser profile to check busy/foreign-session behavior.
Recorded examples stay independent. All local simulator screens identify the
simulator; their output must not be reported as LLM evidence.

The server enforces 300 seconds for ready-without-goal, each confirmation and
each provider operation. The UI countdown is informational. Refusal/expiry ends
the run, while its chat, runtime events and summary remain available. Starting
anew creates a fresh modeled environment. Closing a tab is not a reliable stop;
use the explicit stop control when that is intended.

An uncertain provider completion leaves private recovery state in the selected
evidence directory and disables new starts. Refresh, new cookies and backend
restart cannot clear it. No browser reset or administrative service is exposed.
Do not delete the marker as a shortcut: establish that prior work has stopped
before a separately reviewed local recovery. The executable entry point currently
has no real provider and no automated recovery command.

Local traces, outcomes and manifests remain private in that directory. Never
copy them to Git automatically. Public results must be reviewed and sanitized.

Verification covers offline contracts and HTTP/React integration. It does not
establish real provider cancellation, station availability, public abuse
protection, or complete browser/mobile visual acceptance. See the
[live contract](../specs/core/live-ui-runtime-contract.md) for the authority.

New admission clears chat, journal and goal; a busy rejection preserves the old
result. Confirmation controls appear in the runtime request card. The accepted
choice remains in a separate operator card. The disabled composer explains
progress without offering additional conversation. “К началу” is always above
the workspace; it releases an unused reservation but does not stop an active run.

Before goal submission, the countdown uses server time. After 300 seconds in
ready state without a goal, the reservation expires and the slot is released;
use “Начать заново” explicitly. A free slot does not extend an expired reservation.
