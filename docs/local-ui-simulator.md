# Local UI/runtime simulator

BC-011/012 local integration check, not real LLM inference or experimental model evidence.
Linux/WSL, one backend process, one active modeled run. The provider uses scripted
initial-dialogue replies and a fixed nominal recovery path after a supported explicit goal. Runtime policies,
explicit confirmations and modeled operations are real application code.

From the repository with its virtual environment activated:

```sh
python -m pip install -e '.[dev,live]'
npm ci --prefix ui
npm --prefix ui run build
python -m governed_agent_runtime.live_http --evidence-dir "$HOME/.local/state/gar-ui-simulator"
```

Both CLI entry points default to `--input-profile preset-only`: the UI offers
fixed commands and the server rejects free text. For local free-text checks,
explicitly pass `--input-profile local-free-text`. Ollama approval templates and
startup must use the same profile; old templates without this field are rejected.
Changing this input profile does not enable public networking or alter smoke budgets.

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
before a separately reviewed local recovery. The simulator entry point has no
real provider; the separately gated Ollama entry point below has no automated
recovery command.

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
the workspace; it preserves preparation, dialogue and active execution. Returning
does not request another preparation or renew deadlines; use explicit stop to end work.

Before goal submission, the countdown uses server time. After 300 seconds in
ready state without a goal, the reservation expires and the slot is released;
use “Начать заново” explicitly. A free slot does not extend an expired reservation.

## Paired local entries — simulator only

Stop any server using these ports, build the UI, then run from the activated
virtual environment:

```sh
python -m governed_agent_runtime.live_dual_http \
  --evidence-dir "$HOME/.local/state/gar-ui-simulator/paired-$(date -u +%Y%m%dT%H%M%SZ)"
```

The visitor entry is `http://127.0.0.1:8000` (four preset calls); the owner entry
is `http://127.0.0.1:8001` (five free-text calls). Both bind loopback only. One
process owns their shared execution slot. Separate cookies and server-bound
profiles keep ownership distinct even in the same browser. Ports may be changed
with `--public-port` and `--owner-port`; use the matching exact origins.

New visitor admissions start disabled. Enable them from the owner start screen;
this control does not reserve the slot. Starting either scenario makes the other
entry busy. Disabling new visitor admissions preserves an already admitted run;
the owner may start after that run releases the slot. No preemption is provided.
The switch resets to disabled after process restart. Ctrl+C closes both listeners
and the shared service. The existing quarantine behavior remains in force.

Check: enable visitor admissions; start a visitor scenario; observe owner busy;
disable new admissions and finish the visitor scenario; start owner free-text;
verify visitor cannot start; stop owner; verify visitor remains paused until
enabled again. Check both completion and explicit rejection/stop.

This launcher is simulator-only and is not a public deployment or a paired
Ollama launcher. Do not expose either port through a tunnel or proxy.

## Local Ollama connection — revision-bound station smoke

The simulator command above remains inference-free. The separate entry point
`python -m governed_agent_runtime.live_ollama_http` requires a private approval
file; merely running the UI or opening a recorded example never loads a model.
The pinned [local profile](../specs/core/live-model-profile.json) uses BC-008
B-18's model/configuration. No model download or fallback substitution is provided.

Before the first smoke, review the final revision/profile and confirm that Ollama
is available only locally, no other client is using it and no earlier request is
outstanding. A loopback binding of this application does not change Ollama's own
listener or firewall configuration. Do not publish either service through a
proxy, tunnel or port forwarding. These checks are a local test boundary, not a
public authentication or GPU-abuse protection solution.

Prepare the approval template **without contacting Ollama**, in the repository
with the virtual environment activated:

```sh
python -m governed_agent_runtime.live_ollama_http \
  --evidence-dir "$HOME/.local/state/gar-ui-ollama/smoke-001" \
  --write-approval-template "$HOME/.local/state/gar-ui-ollama/approval-001.json"
```

The template records the revision/profile hash and private destination, with
`approved`, `exclusive_provider` and `no_outstanding_work` set to false. After
human review, fill `reviewer` and explicitly set those three fields to true.
Do not approve automatically or copy an old approval to a changed revision.
Stop the simulator before the approved run (both use the same loopback port).
Only after that approval:

```sh
python -m governed_agent_runtime.live_ollama_http \
  --evidence-dir "$HOME/.local/state/gar-ui-ollama/smoke-001" \
  --approval-file "$HOME/.local/state/gar-ui-ollama/approval-001.json"
```

Startup requires a clean checkout and runs Python/UI verification before serving
`http://127.0.0.1:8000`. It consumes the approval once, but performs no inference
until explicit admission. Two preparation attempts are allowed in total; failed
attempts count. Suggested bounded review: one nominal goal with the necessary
confirmations, then a fresh run with explicit refusal. Runtime budgets remain
16 proposals, 20 tool calls and 3 state-changing modeled operations per run.
The preparation, inference and operator deadlines retain their separate meanings.
No automatic rerun is scheduled and `keep_alive` remains 10 minutes.

Provider version or digest mismatch prevents preload/inference. If the installed
profile differs, stop and review the difference rather than editing the check
away. All requests use a fixed local provider address, without environment proxy
or HTTP redirect support. Browser payloads cannot configure it.

The coordinator uses shared private local state across evidence directories;
only one instance can own it. An outstanding provider-operation marker blocks
admission after uncertain completion/restart. Do not remove it to force retry:
first establish that provider work has ended, then review local recovery and a
new startup approval. This lock cannot exclude unrelated direct Ollama clients.

Raw goals, requests, responses, approval and results stay in private local evidence.
Only reviewed/sanitized conclusions belong in Git. Never upload these directories
wholesale. A successful smoke is an integration observation, not a new quality
benchmark or evidence of safe public deployment.


## BC-012 initial dialogue (local development)

The simulator entry point now uses a bounded initial dialogue before creating a
remediation run. `Что ты умеешь?` and `Почему сервис работает нестабильно?` return
fixed informational replies; `Восстанови работу сервиса` starts the existing
confirmation-governed scenario. `Напиши стихотворение` returns a scope reply;
other text receives a scripted clarification. This is a deterministic UI fixture,
not evidence of language understanding.

Up to five dialogue calls share the reservation, with a 300-second user wait and
a 600-second absolute window after model readiness. Reload restores the owned
transcript without resending a call. During execution only existing exact-action
decisions are accepted. The local profile is now BC012-local-ollama-v1; earlier
revision/profile approvals cannot authorize this version. Bounded owner-run
real-model smokes are recorded in the
[BC-012 disposition](../reports/decisions/bc-012-initial-dialogue-disposition.md);
they are not a general semantic-quality guarantee.
