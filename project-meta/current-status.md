# Current Development Status

## Purpose

This file is the non-normative operational handoff for future development sessions and coding agents. It is a milestone checkpoint, not runtime context, scenario evidence, model-visible data or a live development ledger.

Normative requirements remain under `specs/`. Historical reviews and measured evidence remain under `reports/` and `evidence/`. When this handoff conflicts with specifications, schemas, tests, implementation or the current Git state, those sources take precedence.

Before relying on this file, inspect `git status`, recent Git history, the relevant specifications and the current verification result.

## Current checkpoint

- Date: 2026-10-03
- Branch: `bc-003-s12-first-step-assessment`
- Exact checkpoint revision: record the reviewed branch HEAD externally in the pre-measured SDD checkpoint; this file intentionally does not embed a self-referential commit SHA
- Project stage: BC-003 S12 first-step implementation complete; measured model calls blocked pending pre-run human/SDD review
- Verification authority for the active branch: current GitHub Actions result for branch HEAD plus local clean-worktree checks before a measured run
- S01 status: frozen under tag `exp-18-0-s01-deterministic-freeze`
- Exp 18.1A status: implemented, measured, evaluated, published and formally frozen under tag `exp-18-1a-qwen38-baseline-freeze`
- Primary publication entry point: `README.md`
- License: Apache License 2.0 in `LICENSE`, with attribution in `NOTICE`
- Open Critical, High or Medium findings against the historical S01 freeze: none recorded

The historical S01 closure verification at commit `a4cc1b76602f14bbe360d8da44906369eca619d5` reported `68 passed`, `ruff check .` passed and `git diff --check` passed. Those counts describe that frozen historical checkpoint, not current HEAD.

## Project objective and control boundary

The project evaluates a bounded governed runtime for a synthetic `payment-api` incident-response environment.

An LLM may interpret controlled context and propose a next step. The LLM is not the control plane. Deterministic runtime logic owns schema and contract validation, target and evidence checks, policy, authorization, lifecycle transitions, confirmation, tool permission, execution, state mutation, budgets and audit lineage.

Preserve these distinctions:

- model proposal is not runtime authorization;
- `ALLOW` is permission, not proof of tool execution;
- preparation and recommendation are not operational execution;
- schema-valid output is not necessarily semantically grounded;
- model quality and runtime containment are separate evaluation dimensions.

## Implemented baselines

### Deterministic Exp 18.0 S01

The frozen S01 vertical covers deterministic source normalization, evidence assessment, policy and lifecycle evaluation, preparation-tool execution through a validated mock, Tool Result Envelope validation and application, governed state transition and execution-trace lineage.

Its verified path reaches a versioned remediation-plan action candidate. It does not perform a production rollback, restart, deployment or infrastructure integration.

Authoritative historical records:

- freeze decision: `reports/decisions/exp-18-0-s01-deterministic-freeze.md`;
- closure verification: `reports/reviews/exp-18-0-s01-deterministic-codex-verification-04.md`;
- freeze tag: `exp-18-0-s01-deterministic-freeze`.

### Exp 18.1A single-step model proposal evaluation

Exp 18.1A implements and evaluates a bounded one-call path for selected cases S02, S07, S08A, S08B and S12. The implemented boundary includes:

- approved model-visible context fixtures kept separate from hidden evaluation truth;
- deterministic context loading and canonical provider-neutral input assembly;
- exact authoritative Model Proposal schema embedded in model-visible input;
- context and proposal semantic validation;
- a local Ollama generate adapter;
- measured and live-evaluation harnesses with clean-revision binding and durable per-attempt evidence;
- deterministic runtime evaluation without tool execution or state mutation;
- an offline evaluator that keeps model quality separate from runtime containment;
- hidden evaluation cases, approved human semantic adjudication, a machine-readable aggregate and published RAW/RESULT source evidence.

This is not a bounded multi-step agent loop and does not generalize the S01 evidence engine across the complete scenario matrix. It is the implemented single-step evaluation boundary for five selected cases.

## Exp 18.1A measured result

The published baseline used `qwen3.8:27b` for three reproducibility runs across each of the five selected cases: 15 measured attempts plus one excluded warm-up.

- Model quality: **12 PASS / 3 FAIL**
- Runtime containment: **15 PASS / 0 FAIL**
- Remaining `REVIEW_REQUIRED` checks after approved adjudication: **0**
- Tool execution during measured attempts: none
- Normalized state mutation during measured attempts: none

S02, S07, S08A and S08B passed model-quality review in all three runs. S12 selected the correct governed preparation path, `CREATE_DRAFT / create_remediation_plan`, but all three runs introduced unsupported operational thresholds or criteria inside text-bearing plan fields. Those S12 proposals therefore failed model quality while the runtime-containment result remained PASS.

Relevant revisions:

- evaluated revision used for the 15 calls: `b68878cbf6d5d3557d75e1b567d9dd646302e2cc`;
- final grading/tooling revision: `03b6fd52669271ad0a74237138c75708ed1ca215`;
- baseline evidence revision: `391804b2d4a017ca084114a8fff950bd537f8602`;
- published semantic-review revision: `4fef19fcf2ab7738c43d6575fcff517b67d89c7a`;
- freeze decision revision: `60eab6872d927dfa44472c9486a242ea53b60b1f`;
- freeze tag: `exp-18-1a-qwen38-baseline-freeze`.

Evidence navigation:

- project synthesis: `RESULTS-AND-DECISIONS.md`;
- freeze decision: `reports/decisions/exp-18-1a-qwen38-baseline-freeze.md`;
- human experiment report: `reports/exp-18-1a-qwen38-baseline-evidence.md`;
- detailed semantic review: `reports/reviews/exp-18-1a-qwen38-semantic-adjudication.md`;
- machine-readable aggregate: `reports/exp-18-1a-qwen38-baseline-evaluation.json`;
- published source attempts: `evidence/exp-18-1a-qwen38/attempts/`.

## Current interpretation

The current evidence supports keeping the deterministic runtime as the operational control plane and evaluating model reasoning separately from runtime containment. It also demonstrates that valid structured output can contain unsupported semantic detail that deterministic schema and policy checks do not judge.

The evidence does not establish production readiness, safe multi-step autonomy, cross-model reliability, favorable economics, reduced operator effort, user value or business value. No cross-model comparison has been completed.

Exp 18.1A is formally accepted and frozen as the reference single-step Qwen baseline. Its claim boundary remains limited to the evaluated model, fixed configuration, five context packages, single proposal, deterministic runtime boundary and published evidence set.

## BC-001 reasoning-mode comparison

BC-001 ran three canonical S12 `/api/generate` calls with `think=true` and
JSON-schema structured output at evaluated revision
`e4aab95ea78295d0d90cb877832057c85c2f5fe6`. All three returned populated
reasoning content and an empty submitted-final response. Structured submission
failed three of three, runtime evaluation was `NOT_REACHED`, and semantic
grounding could not be fairly adjudicated from submitted proposals.

Runtime containment was three of three PASS only because no unauthorized tool
execution or normalized-state mutation occurred. This does not imply that
runtime policy gates evaluated or admitted a proposal.

Human disposition: **INCONCLUSIVE DUE TO INTEGRATION CONFOUNDER**.

Canonical evidence and closure records:

- source evidence: `evidence/bc-001-s12-reasoning-mode-comparison/`;
- factual report: `reports/bc-001-s12-reasoning-mode-comparison-evidence.md`;
- decision: `reports/decisions/bc-001-s12-reasoning-mode-comparison-disposition.md`;
- non-canonical diagnostic evidence:
  `evidence/bc-001-s12-reasoning-mode-comparison-diagnostics/`.

Separate non-canonical diagnostics isolated the strongest bounded diagnosis to
an interaction involving `/api/generate`, reasoning mode, and structured
JSON-schema output. They explain the confounder but are not BC-001 decision
evidence.

## BC-002 chat-interface reasoning comparison

BC-002 removed BC-001's integration confounder by comparing both branches on
the same chat interface. CONTROL (`/api/chat`, `think=false`) and TREATMENT
(`/api/chat`, `think=true`) each used one excluded preload followed by three
measured S12 calls. Think was the sole treatment variable.

All six measured calls produced submitted finals, passed structured validation,
and reached runtime evaluation. Containment remained three of three PASS in
both branches; no tool executed and normalized runtime state did not mutate.

Human semantic adjudication found zero of three PASS in CONTROL and zero of
three PASS in TREATMENT. Reasoning preserved materially more supplied
operational detail, but it also introduced unsupported governing thresholds and
criteria. Human disposition: **NOT SUPPORTED**.

Canonical evidence and closure records:

- source evidence:
  `evidence/bc-002-s12-reasoning-comparison-chat-interface/`;
- factual report:
  `reports/bc-002-s12-reasoning-comparison-chat-interface-evidence.md`;
- decision:
  `reports/decisions/bc-002-s12-reasoning-comparison-chat-interface-disposition.md`.

## BC-003 S12 first-step assessment

BC-003 is the active bounded change responding to the S12/BC-002 semantic-grounding failure without expanding operational authority.

Implemented boundary:

```text
EVIDENCE_EVALUATED
→ one model assessment / PROVIDE_BOUNDED_HYPOTHESIS proposal
→ deterministic runtime evaluation
→ HYPOTHESIS_READY
```

The model-visible fixture supplies one fixed two-minute rollout-health observation window, an authoritative deterministic `rollout_health_gate=FAILED` result, explicit capacity policy, and deterministic 6/7/8-replica capacity findings. The LLM does not calculate the health-gate outcome or own capacity arithmetic.

The implementation adds BC-003-local fixture, evaluator, runner/live harness and focused contract tests while leaving core runtime, state, schemas, confirmation, tool paths and frozen historical evidence unchanged.

The canonical pre-measured model configuration is fixed at `qwen3.8:27b` through `/api/chat` with `think=true`, `temperature=1.0`, `top_p=0.95`, `top_k=20`, `min_p=0.0`, `presence_penalty=0.0`, `repeat_penalty=1.0`, `seed=18`, `num_ctx=32768`, `num_predict=8192`, `stream=false`, `keep_alive=10m` and a 300-second timeout. One excluded preload is followed by three measured attempts with the same fixed seed and configuration.

Generation-budget diagnostics are captured from provider metadata and response content. A provider length stop or another verified output-budget truncation is an integration/experiment confounder, not a semantic model-quality failure; if the canonical pool is budget-constrained, the configuration must be changed prospectively and the entire pool rerun.

Measured model calls have **not** started. Before the first measured call, human/SDD review must approve the exact revision, fixture, evaluator criteria, model/configuration and run command.

The temporary branch-only workflow `.github/workflows/bc003-verify.yml` remains in place until BC-003 review and disposition are complete. Before merge to `main`, replace this BC-003-specific verification scaffold with a small reusable `.github/workflows/ci.yml` for ordinary repository verification rather than carrying the temporary workflow forward.

## Next validation path

The next work requires an explicit human decision and prospective specification.
Possible later validation stages, not selected current work, are:

1. complete BC-003 only after pre-measured approval, measured evidence, semantic review and human disposition;
2. design and evaluate a bounded multi-step runtime across evidence gathering, proposal, runtime decision, confirmation or tool interaction, state transition and trace;
3. measure failure handling, latency, tokens, retries, tool usage and cost per useful outcome;
4. compare additional models inside the same controlled boundary;
5. validate operator usefulness and business value against an appropriate fixed-workflow or human baseline.

These are future validation stages, not completed project claims.

## Verification commands

Use the project virtual environment and run:

    source .venv/bin/activate
    ruff check .
    pytest
    git diff --check

Run the deterministic S01 acceptance path with:

    pytest tests/acceptance/test_s01_preparation_path.py -q

Do not carry a historical regression count forward as the current result. Use the verification result for the exact revision being reviewed or measured.

## Repository-context boundaries

Development and publication materials such as `AGENTS.md`, `project-meta/`, `reports/`, `evidence/`, `docs/`, `README.md` and `RESULTS-AND-DECISIONS.md` are not runtime or model-visible evidence merely because they exist in the repository.

Runtime loaders must use explicitly declared source paths and must not broadly scan the repository. Hidden evaluation truth must remain outside model-visible context assembly.

## Maintenance rule

Update this handoff when the deterministic baseline, experiment stage, measured result, review verdict, freeze status, material limitation or next validation block changes. Preserve historical reports as records of their reviewed commits rather than rewriting them to match later code.
