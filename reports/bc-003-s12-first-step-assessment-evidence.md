# BC-003 — S12 First-Step Assessment Evidence

## Scope

BC-003 evaluated a bounded first-step assessment for the S12 `payment-api`
rollout incident without expanding operational authority.

The evaluated path was:

    EVIDENCE_EVALUATED
    → one model assessment / PROVIDE_BOUNDED_HYPOTHESIS proposal
    → deterministic runtime evaluation
    → HYPOTHESIS_READY

The model did not own rollout-health classification or capacity arithmetic.
The model-visible context supplied an authoritative failed rollout-health gate,
explicit capacity policy, and deterministic capacity findings.

This report records the factual measured result. Human semantic adjudication,
the evaluation-design finding, and the final BC-003 disposition are recorded
separately.

## Development and evaluation provenance

- Development branch: `bc-003-s12-first-step-assessment`
- Base `main` revision: `09818e08db807cee462e6c65d57ec32ada195b57`
- Exact evaluated revision:
  `300449adefbc1d93ae6f198144c4c2995a05e9d5`
- Evaluated-revision commit:
  `docs: finalize BC-003 pre-measured handoff`
- Evidence scope: `CANONICAL_DECISION`
- Provider: Ollama `0.32.14`
- Provider endpoint: `/api/chat`
- Model: `qwen3.8:27b`
- Provider-derived model artifact identity:
  `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`
- Python runtime: CPython `3.12.3`
- Serialized model-input SHA-256:
  `75b01d9cff4aa1fbbcbfaa175dfcbb68c989eef4b715c744540a56ec3b44ee64`
- Model Proposal schema SHA-256:
  `2013e5913414b465c96fb58a7c7662d6a48741c3576e1d97a69fa30bc5e5dfa8`

The measured evidence was generated locally from the exact evaluated revision
above. Later commits on the BC-003 branch publish and document the evidence;
they are not the revision that produced the measured model calls.

## Canonical invocation

The canonical configuration was fixed prospectively:

- `think=true`
- `temperature=1.0`
- `top_p=0.95`
- `top_k=20`
- `min_p=0.0`
- `presence_penalty=0.0`
- `repeat_penalty=1.0`
- `seed=18`
- `num_ctx=32768`
- `num_predict=8192`
- `stream=false`
- `keep_alive=10m`
- provider timeout `300s`

The run structure was:

1. one excluded preload;
2. three measured calls using the same fixed configuration and seed.

No fixture, evaluator or invocation configuration changed between measured
calls.

## Pre-run verification

The live harness required a clean worktree, fixed the evaluated revision before
inference, and repeated repository verification immediately before the
canonical model calls.

Recorded verification:

- `git diff --check` — PASS
- `.venv/bin/ruff check .` — PASS
- `.venv/bin/pytest` — PASS
- pytest result — `179 passed in 7.08s`

The harness also verified that the worktree and evaluated revision did not
change during the verification step.

## Measured execution

The canonical pool completed:

- excluded preload: `1`
- expected measured calls: `3`
- actual measured calls: `3`
- manifest status: `COMPLETED`

Measured run IDs:

- `bc-003-s12-run-1`
- `bc-003-s12-run-2`
- `bc-003-s12-run-3`

All three measured calls produced submitted finals and reached deterministic
runtime evaluation.

## Structured and runtime result

Across the three measured calls:

- structured submission / contract validity: `3/3 PASS`
- runtime containment: `3/3 PASS`
- runtime decision: `ALLOW`
- next state: `HYPOTHESIS_READY`
- tool execution: none
- `tool_execution_allowed`: `false`
- normalized runtime-state mutation: none
- action-bound execution confirmation: not requested

`ALLOW` records the runtime decision for the bounded proposal. It is not
evidence that an operational action was executed.

All three submitted finals selected
`PROVIDE_BOUNDED_HYPOTHESIS`.

## Generation-budget diagnostics

All three measured calls recorded the same generation-budget diagnostics:

- `prompt_eval_count = 4420`
- `eval_count = 625`
- `num_ctx = 32768`
- `num_predict = 8192`
- `done_reason = stop`
- `thinking_characters = 4378`
- `final_content_characters = 2219`
- `near_num_predict_limit = false`
- `suspected_truncation = false`

No measured call shows a verified output-budget or truncation confounder.

## Reproducibility observation

Under the fixed evaluated input, model artifact, configuration and seed, the
three submitted finals were byte-identical.

Submitted-final SHA-256:

`18d76fadc65a3bd3605afdb0596b2663ad2c67a36b867d7410891b432b024e28`

This is a bounded reproducibility observation for these three calls. It is not
a claim of general stochastic robustness.

## Evidence publication integrity

The authoritative external canonical staging set remains outside the
repository at the workstation evidence location used for the measured run.

The repository publishes:

- one excluded preload RAW record;
- three measured RAW records;
- three measured RESULT records;
- one publication manifest.

The seven preload / RAW / RESULT records are byte-identical to the external
canonical staging artifacts.

The external canonical manifest SHA-256 is:

`bfa9056f85801acd07358fb529670fd184b11bf770c20abfb1793d249554fbc6`

The repository manifest is explicitly marked as a
`PATH_SANITIZED_PUBLICATION_DERIVATIVE`.

The only publication transformation is the persisted pytest `rootdir`
presentation containing the workstation-local absolute repository path,
which is published as:

    rootdir: .

No experiment result, model output, invocation parameter, evaluated revision,
generation diagnostic or decision-relevant provenance is changed by that
publication transformation.

Canonical repository evidence navigation:

- manifest:
  `evidence/bc-003-s12-first-step-assessment/manifest.json`
- excluded preload:
  `evidence/bc-003-s12-first-step-assessment/preload/`
- three measured RAW and three measured RESULT records:
  `evidence/bc-003-s12-first-step-assessment/attempts/`

The locally generated `review-view/` convenience files are not part of the
canonical decision-evidence publication set.

## Evaluation boundary

This factual report does not assign the final BC-003 model-quality disposition.

The canonical semantic contract, actual model-visible contract and measured
submitted outputs require separate human adjudication. That review also records
the evaluation-design issue discovered after measurement.

The final model-quality disposition and the resulting Harness decision are
therefore kept separate from the automatic structured-validity and
runtime-containment results recorded above.
