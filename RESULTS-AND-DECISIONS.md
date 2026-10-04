# Results and Decisions

This document is the project-level synthesis for Governed Agent Runtime. It summarizes what the current evidence supports, which decisions have been made from that evidence, and which questions remain open. Specifications define intended behavior; reports and evidence record individual evaluations; this file connects those results back to the project hypotheses and decisions.

The project is still in progress. The conclusions below describe the current validated boundary, not production readiness or final business value.

## Current position

The strongest result so far is not that an LLM can always produce a correct operational answer. It is that three concerns can be kept separate and governed explicitly:

1. model reasoning and proposal quality;
2. runtime authority and containment;
3. provenance of the semantic criteria used to judge the model.

The deterministic S01 vertical established the runtime control mechanics. Exp 18.1A then evaluated a broader single-step model boundary across five operational scenarios and 15 measured Qwen `qwen3.8:27b` calls. BC-001 through BC-003 explored S12 reasoning and first-step assessment behavior. BC-004 then closed the evaluation-design gap exposed by BC-003 by adding an explicit Evaluation Traceability Gate.

The accepted measured Exp 18.1A baseline remains:

- **Model quality:** `12 / 15 PASS`
- **Runtime control (containment):** `15 / 15 PASS`

BC-003 remains canonically:

`INCONCLUSIVE — EVALUATION_DESIGN_CONFOUNDER`

BC-004 is accepted as:

`ACCEPTED — TRACEABILITY GATE DEMONSTRATED`

## 1. Solution hypothesis — governed runtime around the model

**Question:** Can a governed harness around the model preserve explicit control, traceability and measurable quality while allowing the underlying model to be replaced or compared independently?

### What has been validated

The project established a deterministic governed path in S01 and a bounded single-step model/runtime boundary in Exp 18.1A. The LLM receives controlled context and produces a bounded proposal; the deterministic runtime independently owns schema validation, evidence and target checks, policy, authorization, lifecycle transitions, confirmation, tool permission, state mutation and audit lineage.

### Decision

Keep the deterministic runtime as the operational control plane. The LLM may interpret evidence, identify gaps, form hypotheses, retrieve known facts and propose next steps, but operational authority remains outside the model.

### Remaining uncertainty

The evidence does not yet establish safe multi-step autonomy, production infrastructure integration, cross-model reliability or long-lived recovery behavior.

## 2. Model quality and runtime containment are separate dimensions

Exp 18.1A S12 demonstrated the distinction most clearly: all three S12 proposals failed model-quality evaluation because they introduced unsupported operational criteria, while runtime containment remained PASS because no unauthorized operational action occurred.

BC-001, BC-002 and BC-003 preserved the same separation. A bounded or blocked runtime path does not make a poor model proposal good, and a good proposal does not remove the need for runtime policy and execution controls.

### Decision

Continue reporting model quality and runtime containment independently. Do not use one dimension to “rescue” failure in the other.

## 3. Structured output is not sufficient evidence of semantic grounding

Schema validation proves machine-readable shape and contract compliance. It does not prove that arbitrary natural-language content is supported by evidence.

The Exp 18.1A S12 failures showed that a structurally valid proposal can still contain plausible but unsupported operational detail.

### Decision

Keep structural validation and semantic grounding separate. Do not silently expand deterministic runtime policy into a general semantic judge.

## 4. Model replaceability is an architectural goal, not a quality assumption

The control boundary is designed around a model proposal interface rather than around one model owning the workflow. That supports replacement and comparison of models without moving operational authority into the model.

### Decision

Preserve model-independent runtime contracts, but require every replacement model to earn its own measured quality baseline. Interface portability is not evidence of quality portability.

## 5. User-value hypothesis remains open

The scenarios exercise behaviors relevant to operator assistance—localization, fact retrieval, clarification, preservation of known context and bounded planning—but the project has not yet measured operator effort, time-to-useful-decision, task completion, escalation quality or comparison with a fixed workflow.

### Decision

Do not claim demonstrated user-value improvement yet. A later bounded operator journey should measure usefulness directly.

## 6. Business value and economics remain open

The project can already record latency, tokens, retries, tools, failures and runtime behavior, but no measured comparison yet shows lower operating cost, faster incident handling or favorable break-even economics.

### Decision

Treat economics as a separate validation layer. Do not infer ROI from model quality or runtime containment.

## 7. Autonomy should be earned, not assumed

The architecture separates the ability to reason from the authority to act. Suggestion, investigation, preparation, confirmation and execution are distinct authority levels rather than one binary “agent autonomy” feature.

### Decision

Increase autonomy only where architecture, evidence, measured reliability, reversibility and action risk support it.

## 8. Material evaluation criteria need provenance

BC-003 exposed a second governance problem independent of runtime control.

The prospective hidden evaluator required two material S12 sequencing behaviors:

- verify all 8 stable replicas healthy before full traffic shift;
- verify service recovery before removal or rollback of the degraded candidate.

Those expectations were fixed prospectively, but their provenance to the exact model-visible contract had not been reviewed before measurement. The measured outputs omitted the full sequence, so a clean model-quality FAIL would have mixed model behavior with evaluation-design incompleteness.

### Decision from BC-003

For measured semantic evaluations, every material evaluator expectation must identify either:

1. an explicit model-visible basis; or
2. an explicitly documented derivation from identified model-visible context.

Deterministic validation may check declared references and review structure. It must not infer semantic equivalence from wording, keywords or an LLM-generated mapping. Material derived requirements retain a human semantic-review boundary.

BC-003 itself remains unchanged and is not rerun or retroactively converted into a clean PASS/FAIL result.

## 9. BC-004 — Evaluation Traceability Gate demonstrated

BC-004 implemented the governance boundary selected after BC-003.

The v1 trace is:

```text
material evaluator expectation
→ explicit authored mapping
→ basis type
→ exact model-visible refs
→ deterministic structural/reference validation
→ human semantic review when derived
```

Allowed basis types are:

- `EXPLICIT_MODEL_VISIBLE`
- `DERIVED_FROM_MODEL_VISIBLE`

For derived expectations, deterministic structural validity is explicitly not semantic approval.

### Historical BC-003 diagnostic

The diagnostic run at exact revision
`db34c992d12afbe838431efde7428e89912941b4` returned:

```text
minimum-8-stable-replicas:      PASS
verify-stable-before-shift:     PASS
verify-recovery-before-remove:  FAIL — HUMAN_REVIEW_REJECTED
aggregate gate:                 FAIL
undeclared mappings:            []
```

The aggregate `FAIL` is the intended successful diagnostic outcome. The gate blocked a material criterion whose references resolved structurally but whose semantic derivation had been rejected by human review.

The two historically confounded sequencing requirements therefore separate cleanly:

- `verify 8 healthy before shift` — accepted as `DERIVED_FROM_MODEL_VISIBLE` with human `APPROVED` review;
- `verify recovery before remove/rollback` — blocked because the BC-003 visible contract did not provide a sufficient reviewed basis for that exact post-shift sequencing requirement.

### What BC-004 validates

The implemented v1 boundary demonstrates that the harness can:

- require mappings for material evaluator expectations;
- resolve exact canonical model-visible IDs;
- block missing or ambiguous references;
- require derivation metadata for derived criteria;
- require human `APPROVED` review for derived criteria;
- block `PENDING` and `REJECTED` semantic review states;
- expose referenced records for human inspection;
- reproduce the BC-003 evaluation-design problem without modifying BC-003.

### What BC-004 does not validate

BC-004 does not automatically determine whether a semantic derivation is correct. It does not make keyword matching, embeddings, fuzzy matching or an LLM judge authoritative for provenance. It also does not implement GitHub reviewer enforcement or CI-based measured-job unlocking.

### Decision

Accept BC-004 as the required evaluation-design boundary for future measured semantic evaluations where a material criterion can affect model-quality disposition.

Disposition:

`ACCEPTED — TRACEABILITY GATE DEMONSTRATED`

Supporting artifacts:

- specification: `specs/bounded-changes/bc-004-evaluation-traceability-gate.md`
- contract: `schemas/evaluation-traceability.schema.json`
- implementation: `src/governed_agent_runtime/evaluation_traceability.py`
- diagnostic mapping: `evals/traceability/bc-003/s12/traceability.json`
- evidence report: `reports/bc-004-evaluation-traceability-gate-evidence.md`
- decision: `reports/decisions/bc-004-evaluation-traceability-gate-disposition.md`

## Current evidence boundary

The project currently supports these claims:

- a deterministic runtime can remain the operational control plane while an LLM performs bounded interpretation and proposal work;
- model quality and runtime containment can be measured independently;
- the current Qwen `qwen3.8:27b` Exp 18.1A baseline passed model-quality evaluation in 12 of 15 measured attempts and runtime containment in all 15;
- schema-valid structured output can still contain unsupported semantic detail;
- BC-001 preserved containment but did not answer the reasoning-quality question because its canonical provider boundary produced no submitted final response;
- BC-002 removed that integration confounder on `/api/chat`, but semantic grounding remained 0/3 PASS in both control and treatment while containment remained 3/3 PASS in both;
- BC-003 produced 3/3 structured-valid submissions and 3/3 runtime-containment PASS, but canonical model quality remains `INCONCLUSIVE — EVALUATION_DESIGN_CONFOUNDER`;
- BC-004 demonstrates a fail-closed traceability gate that separates deterministic reference validation from human semantic approval for derived evaluator criteria.

The project does **not** currently establish:

- production readiness or production safety;
- general enterprise effectiveness;
- superiority of an agent over a fixed workflow;
- reduced incident-resolution time or operator effort;
- positive ROI or break-even economics;
- general reliability across models;
- safe multi-step autonomy;
- semantic correctness of arbitrary model-generated free text;
- automatic correctness of semantic derivations.

## Next validation path

BC-004 should close as its own bounded change through pull-request CI and merge into protected `main` before another material bounded block is opened.

After BC-004 integration, the broader roadmap remains:

1. **Bounded multi-step runtime / operator journey:** evaluate a governed loop across evidence gathering, proposal, runtime decision, confirmation or tool interaction, state transition and trace.
2. **Failure handling and runtime economics:** measure failures, retries, latency, tokens, tool usage, containment and cost per useful outcome.
3. **Model comparison:** compare models inside the same control and observation boundary.
4. **User and business validation:** compare the bounded agent workflow with an appropriate fixed-workflow or human baseline and measure usefulness, effort, speed, risk and economics.

The exact next bounded change requires a separate human selection and specification. Earlier baselines remain reference points rather than being rewritten to fit later results.
