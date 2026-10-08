# Specification Router

Use this file to answer: **Which authoritative specification should I read for this concern?**

Load only the rows relevant to the bounded task, then inspect the affected schemas or other formal contracts, implementation, and tests or evaluations. This router summarizes applicability and does not duplicate specification content.

## Concern routing

| Concern | Authority | Scope | Lifecycle | Relevance |
| --- | --- | --- | --- | --- |
| Product intent | [`core/product-brief.md`](./core/product-brief.md) | Product concept, user, problem, hypotheses and success direction | Active | Current |
| Agent role and behavioral boundary | [`core/agent-charter.md`](./core/agent-charter.md) | Permitted responsibilities, behavioral principles and limits of model authority | Active | Current |
| Runtime architecture and control ownership | [`core/runtime-architecture.md`](./core/runtime-architecture.md) | Component boundaries and deterministic control-plane responsibilities | Active | Current |
| State semantics and lifecycle | [`core/state-dictionary.md`](./core/state-dictionary.md), [`core/state-transition-table.yaml`](./core/state-transition-table.yaml) | Canonical state, ownership, transitions and decision application | Active | Current |
| Evidence | [`core/evidence-model.md`](./core/evidence-model.md) | Evidence records, claims, freshness, sufficiency and gaps | Active | Current |
| Model-visible context assembly | [`core/context-assembly-spec.md`](./core/context-assembly-spec.md) | Context sources, visibility and bounded assembly | Active | Current |
| Source adapters | [`core/source-adapter-contracts.yaml`](./core/source-adapter-contracts.yaml) | Validation and normalization of raw source observations | Active | Current |
| Policy, authorization and action readiness | [`core/policy-spec.yaml`](./core/policy-spec.yaml), [`core/action-preconditions.yaml`](./core/action-preconditions.yaml) | Proposal admission, gates, permissions, preconditions and safer paths | Active | Current |
| Tools and tool results | [`core/tool-contracts.yaml`](./core/tool-contracts.yaml) | Tool inputs, categories, output envelopes and execution boundaries | Active | Current |
| Human confirmation | [`core/confirmation-contract.yaml`](./core/confirmation-contract.yaml) | Confirmation bindings, validity, invalidation and consumption | Active | Current |
| Execution trace | [`core/execution-trace-contract.md`](./core/execution-trace-contract.md) | Governed lineage from proposal through decision, result and state application | Active | Current |
| Exp 18.0 and deterministic S01 | [`experiments/exp-18-0/experiment-scope.md`](./experiments/exp-18-0/experiment-scope.md), [`experiment-plan.md`](./experiments/exp-18-0/experiment-plan.md), [`acceptance-cases.yaml`](./experiments/exp-18-0/acceptance-cases.yaml), [`evaluation-plan.md`](./experiments/exp-18-0/evaluation-plan.md) | Original deterministic scope, S01–S12 acceptance matrix and evaluation plan; only the S01 implementation is formally frozen | Active; S01 frozen | Current scenario/evaluation authority; frozen S01 is a historical reference |
| Exp 18.1A single-step Qwen baseline | [`experiments/exp-18-1/single-step-llm-probe-design.md`](./experiments/exp-18-1/single-step-llm-probe-design.md) | Model-visible input, selected cases, single-call evaluation, grading separation and evidence contract | Frozen | Historical reference; current accepted single-step baseline |
| BC-001 S12 reasoning mode comparison | [`bounded-changes/bc-001-s12-reasoning-mode-comparison.md`](./bounded-changes/bc-001-s12-reasoning-mode-comparison.md) | Controlled S12 `think=true` comparison against the frozen Exp 18.1A S12 baseline | Completed; disposition: Inconclusive | Historical bounded-change result; canonical execution was integration-confounded |
| BC-002 S12 reasoning comparison on chat interface | [`bounded-changes/bc-002-s12-reasoning-comparison-chat-interface.md`](./bounded-changes/bc-002-s12-reasoning-comparison-chat-interface.md) | Chat-based S12 `think=false` control versus `think=true` treatment | Completed; disposition: Not supported | Historical bounded-change result; reasoning retained more supplied context but semantic grounding remained 0/3 PASS in both branches |
| BC-003 S12 first-step assessment | [`bounded-changes/bc-003-s12-first-step-assessment.md`](./bounded-changes/bc-003-s12-first-step-assessment.md) | Redesigned S12 first-step capability probe from `EVIDENCE_EVALUATED` to `HYPOTHESIS_READY` | Completed; disposition: Inconclusive | Historical bounded-change result; canonical model-quality disposition is `INCONCLUSIVE — EVALUATION_DESIGN_CONFOUNDER`, while runtime containment was 3/3 PASS |
| BC-004 Evaluation Traceability Gate | [`bounded-changes/bc-004-evaluation-traceability-gate.md`](./bounded-changes/bc-004-evaluation-traceability-gate.md) | Explicit expectation→model-visible-basis mapping, exact reference validation and human review of derived expectations before measured evaluation | Completed; disposition: Accepted | Current evaluation-governance baseline; gate demonstrated and merged to `main` |
| BC-005 S12 prospective grounded assessment | [`bounded-changes/bc-005-s12-prospective-grounded-assessment.md`](./bounded-changes/bc-005-s12-prospective-grounded-assessment.md) | First prospective single-step S12 model-quality evaluation using BC-004 traceability before measurement; separates pre-shift stable health from post-shift service recovery | Completed; disposition: Not supported | Historical measured baseline; 0/3 semantic PASS, runtime containment 3/3 PASS |
| BC-005-D1 self-review instruction diagnostic | [`bounded-changes/bc-005-d1-self-review.md`](./bounded-changes/bc-005-d1-self-review.md) | Single generic final-review instruction; frozen BC-005 comparator/evaluator, one diagnostic pool | Completed; disposition: Not supported | Historical diagnostic; semantic 0/3, containment 3/3; human review accepted |
| BC-005-D3 independent Qwen judge | [`bounded-changes/bc-005-d3-independent-judge.md`](./bounded-changes/bc-005-d3-independent-judge.md) | Two isolated reviews of D1/D2 answers against identical D1 input | Completed; disposition: Not supported | Two calls; judge missed known A violation, B agreed with human review |

The `Lifecycle` and `Relevance` columns are the project-local authority for current applicability. Existing artifact-local `Status`, `Spec version`, specification-family markers and similar legacy metadata are non-authoritative for current lifecycle and applicability and must not override this router.

Do not perform repository-wide metadata cleanup solely to align those legacy fields. Remove or normalize them opportunistically when the relevant artifact is next touched, unless a concrete conflict requires earlier correction and human disposition.

`Active` means the artifact is current project authority for its concern.

`Frozen` means the accepted baseline is a historical reference. Later experiments build from or compare against it rather than rewriting its specification, evidence or adjudication.

## Change route

For a behavioral change, follow the applicable authority from this router into the affected formal contracts and tests before implementation:

    human intent and bounded concern
    -> authoritative specification
    -> schemas, tables or other formal contracts
    -> focused RED test when required
    -> smallest implementation
    -> blocking verification
    -> evidence, review and human disposition when applicable

See `AGENTS.md` for project-local execution, conflict-escalation and evidence-integrity rules. The external reusable SDD Operating Model is not required context for routine changes.

## Identifier legend

Identifiers preserve historical names. Their prefix denotes a stable entity or category; the remainder identifies an instance. Do not infer changing hierarchy or business meaning from numbering, and do not create identifiers merely for taxonomy completeness.

| Form | Existing use | Authority or note |
| --- | --- | --- |
| `exp-18-0`, `Exp 18.1A`, `Exp 18.1B` | Experiment or bounded experiment slice | Machine/path forms and human-readable forms differ historically; preserve the established form in each artifact. `Exp 18.1B` is an existing planned label in the frozen Exp 18.1A design, not the current active bounded change |
| `BC-001`–`BC-005` | Prospective bounded changes | Established project-local bounded-change family. Use `BC-*` only for explicitly selected prospective bounded changes; do not retrofit historical artifacts |
| `S01`–`S12` | Acceptance-scenario identities | Defined in Exp 18.0 acceptance cases; do not rename |
| `S08A`, `S08B` | Exp 18.1A evaluation variants of historical S08 | Useful probe labels, while hidden evaluation records retain canonical `scenario_id: S08`; preserve this distinction |
| `G01_*`–`G10_*` | Ordered deterministic runtime gates | Defined in `core/policy-spec.yaml` |
| `P001`–`P010` | General policy rules | `PH001` and `SP001` are existing specialized policy-rule prefixes; their numbering is not a hierarchy |
| `T001`–`T036` | Runtime state transitions | Defined in `core/state-transition-table.yaml` |
| `DA001`, `CINV01`–`CINV08` | Decision-application and confirmation-invalidation rules | Existing specialized rule categories; do not normalize them into another prefix |
| snake-case names such as `create_remediation_plan` | Tool identities | Defined by `core/tool-contracts.yaml`; tools do not use a separate numeric prefix |

No `REQ` or `AC` identifier family is established for this project. Keep
requirements and acceptance criteria as concise sections within the applicable
`BC-*` specification. Do not retrofit `BC-*` or another identifier family into
historical artifacts.

## D2 exploratory observation (non-normative)

BC-005-D2 is closed with one human-approved positive observation. It introduced no
runtime contract or retrospectively registered experiment specification. Its
[report](../reports/bc-005-d2-independent-codex-evidence.md) and
[decision](../reports/decisions/bc-005-d2-independent-codex-disposition.md) record
the exact D1 input comparison and environment limits. No next bounded change is selected.
