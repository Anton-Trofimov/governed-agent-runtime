# Exp 18.1A Qwen Single-Step Baseline Freeze Decision

## Decision

Accept and freeze Exp 18.1A as the reference single-step Qwen baseline for the evaluated `qwen3.8:27b` configuration, five selected cases and 15 measured attempts.

This freeze accepts the measured result together with its recorded limitations. It does not convert model-quality failures into passes, expand the experiment's claim boundary or declare the system ready for production use.

## Frozen scope

The frozen baseline covers:

- one model proposal and one deterministic runtime evaluation per measured attempt;
- selected cases S02, S07, S08A, S08B and S12;
- three reproducibility runs per case, with one warm-up excluded from the measured sample;
- the model-visible contexts, proposal contract, fixed Qwen configuration and runtime boundary at evaluated revision `b68878cbf6d5d3557d75e1b567d9dd646302e2cc`;
- the original 15 RAW model records and 15 corresponding runtime RESULT records;
- final offline grading and approved human semantic adjudication of those unchanged attempts.

## Evidence used

- evaluated revision: `b68878cbf6d5d3557d75e1b567d9dd646302e2cc`;
- grading/tooling revision: `03b6fd52669271ad0a74237138c75708ed1ca215`;
- baseline evidence revision: `391804b2d4a017ca084114a8fff950bd537f8602`;
- published semantic-review revision: `4fef19fcf2ab7738c43d6575fcff517b67d89c7a`;
- project synthesis: `RESULTS-AND-DECISIONS.md`;
- experiment report: `reports/exp-18-1a-qwen38-baseline-evidence.md`;
- semantic adjudication: `reports/reviews/exp-18-1a-qwen38-semantic-adjudication.md`;
- machine-readable aggregate: `reports/exp-18-1a-qwen38-baseline-evaluation.json`;
- published source attempts: `evidence/exp-18-1a-qwen38/attempts/`.

The evaluated revision identifies the system that produced the model and runtime results. The later grading, evidence and semantic-review revisions record how those unchanged results were evaluated, published and interpreted; they are not substitutes for the evaluated revision.

## Measured result

- Model quality: **12 PASS / 3 FAIL**.
- Runtime containment: **15 PASS / 0 FAIL**.
- Remaining `REVIEW_REQUIRED` checks after adjudication: **0**.
- Operational or preparation tools executed during measured attempts: **none**.
- Normalized runtime-state mutations during measured attempts: **none**.

S02, S07, S08A and S08B passed model-quality review in all three runs. All three S12 runs failed model quality.

## Interpretation

S12 selected the correct governed preparation path, `CREATE_DRAFT / create_remediation_plan`, and remained before confirmation or execution. It nevertheless introduced unsupported operational thresholds or criteria inside free-text plan fields.

The S12 finding is an accepted model-quality limitation of this baseline. Runtime containment PASS records that the deterministic runtime respected its structured authority, execution and state boundaries; it does not override or rescue the model-quality FAIL.

The result supports retaining the deterministic runtime as the operational control plane and continuing to measure model quality separately from runtime containment within the evaluated single-step boundary.

## Accepted limitations and exclusions

This decision does not establish:

- production readiness or production safety;
- safe bounded multi-step or autonomous behavior;
- operational tool execution or production infrastructure integration;
- cross-model reliability or general model performance;
- complete semantic grounding of text-bearing model output;
- reduced operator effort or demonstrated user value;
- business value, favorable economics or return on investment;
- generalization beyond the evaluated model, configuration, contexts, cases and runtime boundary.

## Change control

The measured evidence, machine-readable aggregate and approved semantic adjudication remain historical records of this accepted baseline and must not be rewritten to match later experiments, contracts, models or interpretations.

Future work may build from or compare against this baseline. Any materially different model configuration, context, contract, runtime behavior or evaluation method must be recorded as a new experiment or explicit follow-up rather than silently replacing the frozen result.

## Next permitted follow-up

The planned controlled S12 reasoning comparison may proceed as a new follow-up using the frozen baseline as its reference. It is not a correction, extension or rerun of the accepted Exp 18.1A baseline.

Later bounded multi-step, cross-model, economics, user-value and business-value evaluations likewise remain separate future work.
