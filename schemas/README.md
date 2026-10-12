# Schemas

Machine-checkable contracts for the governed runtime and evaluation harness.

Runtime contracts:

- `model-proposal.schema.json`
- `normalized-state.schema.json`
- `tool-result.schema.json`
- `runtime-decision.schema.json`
- `confirmation.schema.json`
- `execution-trace.schema.json`

Evaluation and model-interface contracts:

- `model-context-package.schema.json`
- `llm-probe-evaluation-case.schema.json`
- `evaluation-traceability.schema.json`

Schemas use JSON Schema Draft 2020-12.

The Markdown and YAML specifications define behavior. JSON Schemas define the
machine-checkable structure of runtime and evaluation objects.

BC-006 uses scoped `bc006-proposal`, `bc006-context` and `bc006-observation` schemas;
see `specs/core/bounded-remediation.yaml`. Historical model schemas are unchanged.
