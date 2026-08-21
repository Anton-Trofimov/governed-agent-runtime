# Current Development Status

## Purpose

This file is the non-normative operational handoff for future development sessions and coding agents. It is a milestone checkpoint, not runtime context, scenario evidence, model-visible data or a live development ledger.

Normative requirements remain under `specs/`. Historical reviews and measured evidence remain under `reports/` and `evidence/`. When this handoff conflicts with specifications, schemas, tests, implementation or the current Git state, those sources take precedence.

Before relying on this file, inspect `git status`, recent Git history, the relevant specifications and the current verification result.

## Current checkpoint

- Date: 2026-08-21
- Checkpoint source commit: `47a58138f422d4a87f310125b63131569d1faba9`
- Branch: `main`
- Project stage: deterministic S01 baseline plus measured Exp 18.1A single-step model/runtime baseline
- S01 status: frozen under tag `exp-18-0-s01-deterministic-freeze`
- Exp 18.1A status: implemented, measured, evaluated and published; no experiment-specific freeze/tag has been created
- Primary publication entry point: `README.md`
- License: Apache License 2.0 in `LICENSE`, with attribution in `NOTICE`
- Current regression count: not asserted by this checkpoint; run the current suite before relying on a count
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
- published semantic-review revision: `4fef19fcf2ab7738c43d6575fcff517b67d89c7a`.

Evidence navigation:

- project synthesis: `RESULTS-AND-DECISIONS.md`;
- human experiment report: `reports/exp-18-1a-qwen38-baseline-evidence.md`;
- detailed semantic review: `reports/reviews/exp-18-1a-qwen38-semantic-adjudication.md`;
- machine-readable aggregate: `reports/exp-18-1a-qwen38-baseline-evaluation.json`;
- published source attempts: `evidence/exp-18-1a-qwen38/attempts/`.

## Current interpretation

The current evidence supports keeping the deterministic runtime as the operational control plane and evaluating model reasoning separately from runtime containment. It also demonstrates that valid structured output can contain unsupported semantic detail that deterministic schema and policy checks do not judge.

The evidence does not establish production readiness, safe multi-step autonomy, cross-model reliability, favorable economics, reduced operator effort, user value or business value. No model comparison has been completed.

Exp 18.1A remains bounded to the evaluated model, fixed configuration, five context packages, single proposal, deterministic runtime boundary and published evidence set. The experiment report records evidence but is not itself a freeze decision.

## Next validation path

The next work should build from the published baseline without retroactively changing it:

1. record the Exp 18.1A baseline decision and freeze the accepted reference without rewriting its evidence;
2. run a controlled S12 reasoning follow-up to test whether additional reasoning improves grounding or produces more unsupported detail;
3. design and evaluate a bounded multi-step runtime across evidence gathering, proposal, runtime decision, confirmation or tool interaction, state transition and trace;
4. measure failure handling, latency, tokens, retries, tool usage and cost per useful outcome;
5. compare additional models inside the same controlled boundary;
6. validate operator usefulness and business value against an appropriate fixed-workflow or human baseline.

These are future validation stages, not completed project claims.

## Verification commands

Use the project virtual environment and run:

    source .venv/bin/activate
    ruff check .
    pytest
    git diff --check

Run the deterministic S01 acceptance path with:

    pytest tests/acceptance/test_s01_preparation_path.py -q

Do not carry the historical `68 passed` count forward as the current regression result. Record a new count only after running the current suite at the revision being reported.

## Repository-context boundaries

Development and publication materials such as `AGENTS.md`, `project-meta/`, `reports/`, `evidence/`, `docs/`, `README.md` and `RESULTS-AND-DECISIONS.md` are not runtime or model-visible evidence merely because they exist in the repository.

Runtime loaders must use explicitly declared source paths and must not broadly scan the repository. Hidden evaluation truth must remain outside model-visible context assembly.

## Maintenance rule

Update this handoff when the deterministic baseline, experiment stage, measured result, review verdict, freeze status, material limitation or next validation block changes. Preserve historical reports as records of their reviewed commits rather than rewriting them to match later code.
