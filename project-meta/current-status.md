# Current Development Status

## Purpose

This file is the non-normative operational handoff for future development sessions and coding agents. It is a milestone checkpoint, not runtime context, scenario evidence, model-visible data or a live development ledger.

Normative requirements remain under `specs/`. Historical reviews and measured evidence remain under `reports/` and `evidence/`. When this handoff conflicts with specifications, schemas, tests, implementation or the current Git state, those sources take precedence.

Before relying on this file, inspect `git status`, recent Git history, the relevant specifications and the current verification result.

## Current checkpoint

- Date: 2026-10-04
- Branch: `bc-004-evaluation-traceability-gate`
- Project stage: BC-004 implementation, diagnostic demonstration and local closure verification complete; pull-request integration into protected `main` is pending
- Diagnostic revision: `db34c992d12afbe838431efde7428e89912941b4`
- BC-004 disposition: `ACCEPTED — TRACEABILITY GATE DEMONSTRATED`
- Final local verification after closure documentation: `ruff check .` PASS; `pytest` `189 passed in 6.91s`; `git diff --check main...HEAD --` PASS; working tree clean and synchronized with origin
- GitHub CI remains the independent integration gate after a pull request is opened
- S01 status: frozen under tag `exp-18-0-s01-deterministic-freeze`
- Exp 18.1A status: implemented, measured, evaluated, published and formally frozen under tag `exp-18-1a-qwen38-baseline-freeze`
- Primary publication entry point: `README.md`
- License: Apache License 2.0 in `LICENSE`, with attribution in `NOTICE`

## Project objective and control boundary

The project evaluates a bounded governed runtime for a synthetic `payment-api` incident-response environment.

An LLM may interpret controlled context and propose a next step. The LLM is not the control plane. Deterministic runtime logic owns schema and contract validation, target and evidence checks, policy, authorization, lifecycle transitions, confirmation, tool permission, execution, state mutation, budgets and audit lineage.

Preserve these distinctions:

- model proposal is not runtime authorization;
- `ALLOW` is permission, not proof of tool execution;
- preparation and recommendation are not operational execution;
- schema-valid output is not necessarily semantically grounded;
- model quality and runtime containment are separate evaluation dimensions;
- evaluator criteria are not authoritative merely because they are hidden or fixed prospectively; material semantic criteria need traceable provenance to the model-visible contract.

## Accepted historical baselines

### Deterministic Exp 18.0 S01

The frozen S01 vertical demonstrates the deterministic governed path through source normalization, evidence assessment, policy and lifecycle evaluation, validated preparation-tool execution, Tool Result Envelope handling, state transition and execution-trace lineage.

Reference artifacts:

- `reports/decisions/exp-18-0-s01-deterministic-freeze.md`
- tag `exp-18-0-s01-deterministic-freeze`

### Exp 18.1A single-step model evaluation

Exp 18.1A evaluated one bounded proposal across selected cases S02, S07, S08A, S08B and S12 with Qwen `qwen3.8:27b`.

Accepted measured baseline:

- model quality: `12/15 PASS`;
- runtime containment: `15/15 PASS`;
- no measured tool execution;
- no normalized runtime-state mutation.

Reference artifacts:

- `reports/exp-18-1a-qwen38-baseline-evidence.md`
- `reports/decisions/exp-18-1a-qwen38-baseline-freeze.md`
- tag `exp-18-1a-qwen38-baseline-freeze`

### BC-001 and BC-002

BC-001 was inconclusive because the canonical `/api/generate` + reasoning + structured-output path produced no submitted final proposal. BC-002 removed that integration confounder on `/api/chat`, but semantic grounding remained 0/3 PASS in both control and treatment while runtime containment remained 3/3 PASS in both.

Reference artifacts:

- `reports/decisions/bc-001-s12-reasoning-mode-comparison-disposition.md`
- `reports/decisions/bc-002-s12-reasoning-comparison-chat-interface-disposition.md`

### BC-003 S12 first-step assessment

BC-003 produced three structured-valid proposals and 3/3 runtime-containment PASS. Human diagnostic review found all three outputs satisfactory against the contract actually visible to the model, but the canonical model-quality disposition remains:

`INCONCLUSIVE — EVALUATION_DESIGN_CONFOUNDER`

The evaluator required material sequencing behavior whose provenance to the exact model-visible contract had not been prospectively reviewed. BC-003 remains immutable and is not rerun or retroactively rewritten.

Reference artifacts:

- `reports/bc-003-s12-first-step-assessment-evidence.md`
- `reports/reviews/bc-003-s12-first-step-assessment-semantic-adjudication.md`
- `reports/decisions/bc-003-s12-first-step-assessment-disposition.md`

## BC-004 Evaluation Traceability Gate

BC-004 closes the specific evaluation-governance gap exposed by BC-003.

Implemented boundary:

```text
material evaluator expectation
→ explicit authored mapping
→ basis type
→ exact model-visible refs
→ deterministic structural/reference validation
→ human semantic review when derived
```

Allowed provenance types:

- `EXPLICIT_MODEL_VISIBLE`
- `DERIVED_FROM_MODEL_VISIBLE`

The deterministic validator does not infer semantic equivalence from keywords, embeddings, fuzzy matching or an LLM judge. For derived criteria, only an explicit human `APPROVED` disposition permits the criterion to pass the traceability gate.

Historical BC-003 diagnostic result at revision `db34c992d12afbe838431efde7428e89912941b4`:

```text
minimum-8-stable-replicas:      PASS
verify-stable-before-shift:     PASS
verify-recovery-before-remove:  FAIL — HUMAN_REVIEW_REJECTED
aggregate gate:                 FAIL
undeclared mappings:            []
```

The aggregate `FAIL` is the intended successful demonstration: the gate blocks a structurally resolved criterion whose semantic derivation was rejected by human review.

BC-004 accepted decision:

`ACCEPTED — TRACEABILITY GATE DEMONSTRATED`

Reference artifacts:

- specification: `specs/bounded-changes/bc-004-evaluation-traceability-gate.md`
- contract: `schemas/evaluation-traceability.schema.json`
- implementation: `src/governed_agent_runtime/evaluation_traceability.py`
- diagnostic mapping: `evals/traceability/bc-003/s12/traceability.json`
- evidence: `reports/bc-004-evaluation-traceability-gate-evidence.md`
- disposition: `reports/decisions/bc-004-evaluation-traceability-gate-disposition.md`

## Current claims boundary

The current project evidence supports the separation of model reasoning, runtime authority and evaluation-governance provenance inside the implemented bounded scenarios.

It does not establish production readiness, safe multi-step autonomy, general model reliability, user-value improvement, positive ROI, lower incident-resolution time, or semantic correctness of arbitrary generated free text.

BC-004 specifically demonstrates deterministic traceability enforcement plus a human semantic-review boundary. It does not demonstrate automatic semantic derivation judgment or GitHub/CI approval automation.

## Next validation path

No new bounded change is opened by this handoff automatically.

The broader roadmap still points toward a bounded multi-step runtime / operator journey, then failure handling and runtime economics, model comparison, and user/business validation. The exact next bounded block requires a separate human selection and specification.

Do not couple a new runtime experiment to BC-004 closure merely to keep momentum. BC-004 should first complete pull-request CI and merge into `main` as its own accepted bounded change.

## Verification commands

Use the project virtual environment and run:

```bash
source .venv/bin/activate
ruff check .
pytest
git diff --check
```

For a feature branch comparison against `main`, use the appropriate explicit range for the reviewed branch. Do not carry a historical regression count forward as the current result; record the result for the exact revision being reviewed.

## Repository-context boundaries

Development and publication materials such as `AGENTS.md`, `project-meta/`, `reports/`, `evidence/`, `docs/`, `README.md` and `RESULTS-AND-DECISIONS.md` are not runtime or model-visible evidence merely because they exist in the repository.

Runtime loaders must use explicitly declared source paths and must not broadly scan the repository. Hidden evaluation truth must remain outside model-visible context assembly. Traceability review metadata is also not model-visible operational context unless a future specification explicitly says otherwise.

## Maintenance rule

Update this handoff when the deterministic baseline, experiment stage, measured result, review verdict, freeze status, material limitation or next validation block changes. Preserve historical reports as records of their reviewed commits rather than rewriting them to match later code.
