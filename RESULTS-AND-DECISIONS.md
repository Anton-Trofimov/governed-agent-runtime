# Results and Decisions

This document is the project-level synthesis for Governed Agent Runtime. It summarizes what the current evidence supports, which decisions have been made from that evidence, and which questions remain open. It is intentionally different from an experiment report: specifications define intended behavior, experiment reports record individual evaluations, and this file connects those results back to the project hypotheses and decisions.

The project is still in progress. The conclusions below describe the current validated boundary, not a final production-readiness or business-value assessment.

## Current position

The strongest result so far is not that an LLM can always produce a correct operational answer. It is that model reasoning and operational authority can be evaluated and controlled as separate concerns.

The first deterministic governed path established the runtime control mechanics. Exp 18.1A then evaluated a broader single-step boundary across five operational scenarios and 15 measured model calls using Qwen `qwen3.8:27b`.

The current measured baseline is:

- **`Model quality`: `12 / 15 PASS`**
- **`Runtime control (containment)`: `15 / 15 PASS`**

The three model-quality failures all occurred in S12. The LLM selected the permitted planning step, but added plausible operational thresholds that were not present in the supplied evidence. The runtime still kept the workflow inside the allowed preparation boundary and did not execute an operational action.

This distinction drives several of the current project decisions below.

## 1. Solution hypothesis — governed runtime around the model

**Question:** Can a governed harness around the model preserve explicit control, traceability, and measurable quality across agent workflows while allowing the underlying model to be replaced or compared independently?

### What has been validated

The project first established one deterministic governed path in S01 and then broadened the model/runtime boundary in Exp 18.1A across five scenarios:

- degradation localization and a bounded next step;
- retrieval of an authoritative deployment fact;
- clarification when target information is incomplete;
- preservation of known target information while asking only for the missing scope;
- rollback-path preparation without execution.

In Exp 18.1A the LLM received bounded context and produced one structured proposal. The deterministic runtime independently evaluated policy, state, authorization, execution, and transition boundaries.

### Evidence

The Exp 18.1A baseline produced 15 measured attempts under one fixed model configuration. Twelve passed the model-quality evaluation and all fifteen passed runtime containment.

The published evidence chain includes the [human-readable experiment report](./reports/exp-18-1a-qwen38-baseline-evidence.md), [human semantic review](./reports/reviews/exp-18-1a-qwen38-semantic-adjudication.md), [machine-readable aggregate](./reports/exp-18-1a-qwen38-baseline-evaluation.json), and the [15 RAW + 15 RESULT source attempts](./evidence/exp-18-1a-qwen38/attempts/).

### Interpretation

The current evidence supports the architectural separation between model reasoning and runtime authority for the evaluated single-step boundary.

It does not show that the model is semantically reliable in every valid output, and it does not show that a governed runtime eliminates model-quality risk. S12 demonstrates the opposite: a proposal can remain inside the permitted action boundary while still containing unsupported semantic detail.

### Decision

Keep the deterministic runtime as the operational control plane. The LLM may interpret evidence, identify gaps, form hypotheses, retrieve known facts, and propose next steps, but policy, authorization, confirmation, tool availability, state transitions, and execution authority remain outside the model.

Treat this architecture as the current project baseline for subsequent bounded-agent experiments.

### Remaining uncertainty

The result is limited to the current single-step evaluation boundary. Multi-step behavior, repeated tool interaction, longer-lived state, recovery paths, and broader action autonomy still require separate validation.

## 2. Model quality and runtime containment are separate evaluation dimensions

**Question:** Can a system distinguish a model-quality failure from a runtime-control failure rather than collapsing both into one PASS/FAIL result?

### What has been validated

Exp 18.1A evaluates model behavior and runtime containment independently.

S12 produced the clearest test of this separation: all three runs failed model-quality evaluation because the model introduced unsupported thresholds, while all three passed runtime containment because the runtime kept the system inside the allowed preparation path and did not execute an unauthorized action.

### Interpretation

A safe runtime block or bounded runtime decision does not make a poor model proposal good. Likewise, a good model proposal does not remove the need for runtime policy and execution controls.

This separation gives the project a more useful failure model: it is possible to ask whether the problem came from model reasoning, semantic grounding, runtime policy, authorization, state handling, or execution rather than reporting a single opaque agent score.

### Decision

Continue reporting `Model quality` and `Runtime control (containment)` independently.

Do not use runtime containment to “rescue” a model-quality failure, and do not treat model quality as evidence that operational execution is safe.

## 3. Structured output is not sufficient evidence of semantic grounding

**Question:** Is schema-valid structured model output enough to treat an operational proposal as grounded?

### What has been validated

No. The S12 outputs were structurally valid and selected the correct high-level planning action, but contained unsupported operational criteria inside free-text fields.

Those details were plausible, but they were not supplied by the evaluated evidence package.

### Interpretation

Schema validation can prove shape, required fields, and machine-readable contract compliance. It cannot by itself prove that arbitrary natural-language content is supported by evidence.

The deterministic runtime can control what the system is allowed to do without necessarily proving every statement generated by the LLM.

### Decision

Keep schema validation and semantic grounding as separate concerns.

Do not silently expand deterministic runtime policy into a general-purpose semantic judge. Where semantic grounding matters, evaluate it explicitly through evidence-aware evaluation or review.

The current human semantic adjudication is therefore part of the evidence chain rather than an afterthought.

### Remaining uncertainty

A future semantic evaluator may automate part of this review, but its reliability, failure modes, latency, and cost must be measured separately. It should not be treated as equivalent to deterministic policy enforcement.

## 4. Model replaceability is an architectural goal, not a quality assumption

**Question:** Can the same controlled environment be used to compare or replace models without moving operational authority into a particular model implementation?

### What has been validated

The current contracts, context assembly, runtime checks, and evaluation boundary are designed around a model proposal interface rather than around one model owning the workflow.

Exp 18.1A demonstrates that one model can be evaluated inside that boundary under a fixed configuration.

### Interpretation

The harness is intended to be model-agnostic at the control boundary, but the project is not model-indifferent. Different models may produce materially different quality, latency, cost, variance, and failure patterns.

The current evidence contains one measured model baseline, not a cross-model comparison.

### Decision

Preserve model-independent runtime contracts and evaluate model capability separately.

Do not infer portability of quality from portability of the interface. A replacement model must earn its own measured baseline.

### Remaining uncertainty

Cross-model quality, reasoning behavior, latency, token usage, and failure modes remain to be compared under the same controlled scenarios.

## 5. User-value hypothesis remains open

**Question:** Can a bounded agent reduce the cognitive and coordination burden of investigating an operational issue by interpreting available evidence, identifying what is known or missing, and proposing a useful next step without taking uncontrolled action?

### Current evidence

The current scenarios exercise behaviors that are relevant to this hypothesis: localization, fact retrieval, clarification, preservation of known context, and bounded planning.

However, the project has not yet measured an operator journey, time-to-useful-decision, task completion, interaction burden, escalation quality, or comparison with an equivalent fixed workflow.

### Decision

Do not claim demonstrated user-value improvement from Exp 18.1A.

Use the current technical baseline to build and evaluate a bounded multi-step operator journey where user-facing usefulness can be measured directly.

## 6. Business-value and economics hypotheses remain open

**Question:** Can the governed-agent approach improve the speed and consistency of operational work while keeping risk, execution authority, and escalation explicit enough to be useful in controlled enterprise workflows?

### Current evidence

The project already records model/runtime behavior and has the architecture needed to measure latency, token usage, retries, tools, failures, and execution paths.

It does not yet provide a measured comparison showing lower operating cost, faster incident handling, better task completion, or a favorable break-even point versus a fixed workflow or human-only process.

### Decision

Do not infer ROI or business impact from technical containment or model-quality results.

Measure economics as a separate validation layer: quality, latency, tokens, tool calls, retries, successful-task rate, failure handling, and the operational effort required for the same bounded task.

## 7. Autonomy should be earned, not assumed

The current architecture deliberately separates the ability to reason from the authority to act.

A model may be allowed to suggest, investigate, prepare, request confirmation, or eventually execute a bounded action, but those levels should not be treated as one binary “agent autonomy” capability.

### Decision

Increase autonomy only where the combination of architecture, evidence, measured reliability, reversibility, and action risk supports it.

The project therefore treats autonomy as a system property that can expand through validation rather than as a feature granted merely because a stronger model is available.

This principle is a design direction supported by the current architecture and evidence, not a general claim proven by Exp 18.1A alone.

## Current evidence boundary

The project currently supports these claims:

- a deterministic runtime can remain the control plane while an LLM performs bounded interpretation and proposal work;
- model quality and runtime containment can be measured independently;
- the current Qwen `qwen3.8:27b` baseline passed model-quality evaluation in 12 of 15 measured attempts and runtime containment in all 15;
- schema-valid structured output can still contain unsupported semantic detail;
- the published Exp 18.1A result is traceable from synthesis to human review, machine aggregate, and individual source attempts.

The project does **not** currently establish:

- production readiness or production safety;
- general enterprise effectiveness;
- superiority of an agent over a fixed workflow;
- reduced incident resolution time or operator effort;
- positive ROI or break-even economics;
- general reliability across models;
- safe multi-step autonomy;
- semantic correctness of arbitrary model-generated free text.

## Next validation path

The current baseline is useful because it defines a controlled starting point for the next questions rather than trying to answer all of them at once.

The planned sequence is:

1. **S12 reasoning follow-up:** Does enabling extended reasoning help the model distinguish supplied operational facts from plausible-but-unsupported assumptions under otherwise comparable conditions?
2. **Bounded multi-step runtime:** Evaluate a governed loop across evidence gathering, proposal, runtime decision, confirmation or tool interaction, state transition, and trace.
3. **Failure handling and runtime economics:** Measure failures, retries, latency, tokens, tool usage, containment, and cost per useful outcome.
4. **Model comparison:** Compare models inside the same control and observation boundary rather than changing the surrounding system together with the model.
5. **User and business validation:** Compare the bounded agent workflow with an appropriate fixed-workflow or human baseline and measure usefulness, effort, speed, risk, and economics.

The project-level decision will evolve as these stages produce evidence. Earlier baselines remain reference points rather than being rewritten to fit later results.
