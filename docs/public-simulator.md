# Public simulator candidate

This opt-in PoC profile runs deterministic preset dialogue and synthetic
operations, not an LLM or a production service. See the
[application contract](../specs/bounded-changes/bc-015-public-simulator.md).
Deployment and browser/transport acceptance are pending; do not expose the local
personal-demo listener as a substitute.

Build the UI using the existing locked dependency/build instructions. The new
module is `governed_agent_runtime.public_simulator`; its `--help` lists the exact
HTTPS application origin, static-site origin and loopback listener port inputs.
It has no provider, owner/admin, inference or arbitrary-tool switch. Terminating
the process stops this application; disabling a transport alone is not proof of
execution cancellation. Do not enable automatic restarts for this finite PoC.

The external static entry uses this **public, non-secret** configuration shape:

```json
{"mode":"external-entry","origin":"https://demo.example"}
```

Its only cross-origin request is the read-only availability probe. Interactive
sessions and commands stay on the destination origin. The endpoint is necessarily
visible to browsers; no credential belongs in this file. `recorded-only` still
makes no backend requests. Missing/invalid config fails closed. A published config
change takes effect on reload; it is not an emergency access barrier.

The simulator's own app-config route selects the same-origin interactive UI.
Its HTTPS transport must preserve the configured public Host. Forwarded headers
do not grant trust or change authorization; public profile ignores them, local
profiles still reject them. Only the intended loopback listener may be forwarded.
Actual transport behavior, resource isolation and shutdown need deployment review.

Bounded allowances are not visitor authentication or protection against denial of
service. One visitor can consume a shared allowance. Process restarts invalidate
sessions and begin a new owner-controlled PoC allowance. Synthetic execution files
live in a temporary directory outside the repository and are removed after orderly
shutdown; an abrupt termination can leave them behind. This is not research evidence.

The existing local personal demo and recorded assets keep their independent paths.
