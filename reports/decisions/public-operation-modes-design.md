# Public operation modes — agreed design

2026-10-29 (Europe/Moscow). Owner-approved design direction after PR #14.
Status: design only; not implemented, not deployment or inference authorization.
Existing runtime contracts remain authoritative until a bounded implementation
updates the relevant specifications, schemas and tests.

## Public modes

Use one mutually exclusive selector, not independent toggles:

| Admin label | Visitor experience | Public admission |
| --- | --- | --- |
| Живой режим | Live scenario and recorded example | Allowed only when backend/provider are ready and limits permit |
| Пауза | Temporary unavailability and recorded example | New admissions rejected; admitted work may finish |
| Только демонстрация | Recorded examples without live controls or promises of return | Rejected server-side; browser makes no station API requests |

Only-demonstration mode is reversible. Visitor wording is simply
«Демонстрационный пример»; station topology is not visitor-facing copy.
Do not claim increased load when the owner paused for another reason.

The independently hosted static interface, recorded scenarios, journals and
reports must work with the station switched off. Publication mode must be
available independently of that station. Server admission enforcement must
also reject old tabs and direct requests; hiding controls is insufficient.
An inactive public backend route must not remain a bypass.

Enable live access only after explicit owner action and readiness checks.
Failed readiness leaves public live admission disabled. Model loading can take
time; instant readiness is not promised. Define propagation and ordering in
the implementation contract so UI state cannot override server authorization.

## Owner access and resource use

Public mode does not revoke the private/local owner entry. The project remains
launchable independently; an unavailable provider is reported without admitting
a run. This does not mean keeping a model resident indefinitely.

Normal operation is live access enabled, with the owner pausing it whenever GPU
resources are needed elsewhere. Do not introduce an application-wide GPU scheduler.
The project's single active slot does not govern WebUI or other model clients.
Use provider queueing where supported, but retain bounded application deadlines;
waiting, overload and timeout must not be represented as successful execution.

Before permitting shared-provider operation, specify it separately from the
current exclusive-provider smoke approval and check one bounded concurrent
WebUI/project scenario. No concurrent station inference is authorized by this
design record. Other agents using GPU outside Ollama are not covered by its queue.

## Emergency public shutoff

Emergency shutoff is separate from the normal mode selector:

- Reject new public admissions and block further steps of the public run.
- Close the public backend access path; retain the static demonstration.
- Request cancellation of outstanding project inference where supported.
- Keep public access disabled across backend/provider restart until explicit
  owner re-enable.
- Public requests cannot start the stopped Ollama service or lift this latch.

Stopping a run or disconnecting transport is not proof that GPU computation
stopped. Preserve uncertain-completion/quarantine behavior. Do not claim reversal
of an already executed action.

Force-stopping the shared Ollama service remains a terminal operation by the
owner, not a process-control feature in the web admin UI. It can affect WebUI
and other clients. A deployment-specific runbook must identify the actual
service stop command and any automatic restart behavior; unloading one model
alone is not a persistent public-admission barrier.

## Implementation sequence and unresolved choices

1. Specify public mode storage/control, private owner authentication, emergency
   latch and safe transition ordering.
2. Select independent static hosting and protected connectivity. No VPS is
   required by this design; no hosting vendor, DNS or tunnel is configured here.
3. Define public admission/rate/resource limits separately from the current
   two-preparation local smoke package.
4. Implement in bounded changes with contract tests for stale tabs, reconnect,
   restart, station-off demonstration and owner/public separation.
5. Verify deployment connectivity and the approved shared-provider scenario
   before enabling public live access.

No public endpoints, credentials, station details or private evidence belong
in this record. Public networking remains disabled at this design stage.
