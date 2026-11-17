# BC-015 — bounded public simulator and external live entry

Status: implementation in progress; no public deployment acceptance.
Baseline: PR #16 merge `f264bd662363817a733294510b8079c1933dca14`.

## Scope and authority

Reuse BC-012 preset dialogue and BC-006 synthetic operations with the deterministic
simulator only. No model calls, provider selection, real tools, owner controls or
host administration. Personal/local entry points retain their contracts.
Operational design and deployment acceptance belong to the separate deployment
project; this public contract contains only reusable application behavior.

The new explicit external-entry configuration extends BC-013; recorded-only still
makes no backend requests. External-entry keeps recorded playback independent and
opens the interactive UI on its own HTTPS origin. Sessions/commands stay same-origin.

## Availability presentation

Configuration is fixed per page load, fails closed, and contains no credentials.
An HTTPS origin (no userinfo, query, fragment or path) identifies the public entry.
Only GET /public/status is probed with credentials omitted, no redirects/cache.
Timeout includes body decoding: 4 seconds. No overlapping probes. Normal delay
after completion is 15 seconds. Three consecutive failures establish unavailable;
the first two preserve the last confirmed state. Unknown starts unavailable.
Two consecutive successful replies restore availability after unknown/offline.
Explicit server unavailable applies immediately; busy is distinct from offline.
Failure backoff is 15/30/60 seconds, capped at 60. Hidden tabs suspend new probes;
returning resumes one probe. Unmount cancels work and ignores late results.
No response changes replay selection, navigation, session or runtime state.
The link can become stale between check and click; availability is advisory.

## Public simulator boundary

Separate opt-in factory/launcher, loopback listener behind an HTTPS transport.
Exact public Host/Origin, Secure HttpOnly host-only SameSite=Strict cookie at /api.
Existing POST shape, schemas, ownership, idempotency and confirmation remain required.
Forwarded headers never determine identity/origin/authorization. Local profile
continues rejecting forwarded headers. No public admin routes or provider injection.
Only status permits an exact configured static-site Origin with no credentials;
all session/command CORS remains forbidden. Status contains only availability and
the simulator label, no session or station details. No wildcard CORS.

Finite PoC defaults: one slot, 20 preparations per process, 1-hour admission window,
16 sessions, 8 runs and 512 command records per session; existing bounded dialogue,
step/confirmation limits remain. Request bodies <=16 KiB and 5-second read deadline.
Global request buckets bound ingress without storing IPs; no visitor fairness or
DDoS protection claim. Deployment still requires resource isolation and transport
review. Restart is an explicit owner action and begins a new PoC allowance.
Admission closure does not claim cancellation of accepted work. Transport cutoff
does not prove an already accepted run stopped. No automatic restart/recovery.
Temporary synthetic evidence is bounded by the process allowance and removed only
after service shutdown. No measured evidence, usage analytics or real inference.

## Acceptance

Focused failure tests precede implementation. Verify secure cookie, exact host and
origin, denied admin/free text/provider selection, cross-session isolation, idempotency,
global bounds, no inference, status without bootstrap, status-only CORS, timeouts,
hysteresis/backoff and replay independence. Run existing Python/UI regression gates,
typecheck/build and recorded-export check. Browser and actual transport checks are
separate: passing local tests does not authorize station exposure or prove reachability.
