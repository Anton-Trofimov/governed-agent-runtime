# BC-014 — Quick local personal demonstration

Status: owner intent approved 2026-11-11; implemented; offline verification passed; station acceptance pending.

## Intent and boundary

A prepared personal demonstration starts with one command and one case-insensitive
terminal confirmation. It is not a measured experiment. Preserve the existing
revision-bound smoke launcher, frozen evidence, recorded UI and deployment pins.
Depends on BC-011/012 transport and dialogue and accepted BC-013 baseline c4ba6da.

## Contract

- Separate local CLI; paired loopback profiles and existing runtime action gates.
- Explicit offline preparation builds UI once and records source/output hashes.
  Normal startup verifies that prepared UI, but does not run tests/install/build.
- Terminal yes/y/да is case-insensitive; invalid input re-prompts; empty/no cancels.
  No approval JSON or two-preparation smoke allowance. Existing per-run dialogue,
  step, deadline, ownership and memory bounds remain. This is not unlimited chat.
- Shared coordinator lock/marker with the research launcher; no parallel bypass.
  No automatic resubmission of old goals. Unknown completion still blocks dispatch.
- A local terminal-only recovery option may explicitly stop the system Ollama
  service, establish no remaining Ollama processes, archive the minimal marker,
  and restart the service while holding the coordinator lock. Refusal/failure
  leaves admission closed. Warn that unrelated clients are affected. No HTTP
  recovery endpoint, shell command injection or silent service restart.
- Preparation/metadata mismatches yield an actionable startup error, not a pull
  or silent model substitution. Keep pinned provider/model configuration.
- Transient private demo records remain separate from research evidence. Remove
  only prior launcher-owned demo sessions under the shared lock after recovery.
  Remove the current session after orderly worker exit; interrupted sessions are
  removed at next successful startup. Never clean research records or approvals.
- UI remains unmodified. No public exposure, Pages publication or deployment changes.

## Acceptance

Offline tests: confirmation normalization/cancel; stale/missing build; busy port;
shared lock exclusion; unknown-work refusal; failed stop/probe/restart; successful
recovery and subsequent startup; no new inference on startup metadata checks;
no smoke quota and preserved per-run bounds; private cleanup excludes research.
Run required Python/UI regressions before delivery. Owner station check: normal
start, real scenario, stop during response, process exit and repeat start including
explicit recovery when needed. Do not claim this station check from fake providers.
