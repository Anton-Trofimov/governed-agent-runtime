# Exp 18.0 S01 Deterministic Codex Review 03

- Reviewed commit: `de022516c0f698bb8f1c5b6cbb698d7055ef9731`
- Review mode: fresh, independent, read-only
- Codex CLI: `0.141.0`
- Model: `gpt-5.5`

Reviewed HEAD `de022516c0f698bb8f1c5b6cbb698d7055ef9731` read-only.

I verified the prior review items. Clarification/safe-stop transitions, transition-specific terminal outcomes, and evidence blocker recomputation appear closed. Tool Result Envelope validation is structurally present, but has the timestamp validation gap below. Invalid normalized timestamp rejection is not fully closed for metric point timestamps.

**Findings**

**High — Invalid metric point timestamps can enter normalized observations and change the S01 diagnosis**

Evidence:
- Contract says invalid timestamps must reject normalization: [specs/core/source-adapter-contracts.yaml](/home/anton/projects/governed-agent-runtime/specs/core/source-adapter-contracts.yaml:197).
- Metric points are copied into normalized observations without validating each point timestamp: [source_adapters.py](/home/anton/projects/governed-agent-runtime/src/governed_agent_runtime/source_adapters.py:286).
- S01 evidence selects the latest metric point by raw string ordering: [evidence_engine.py](/home/anton/projects/governed-agent-runtime/src/governed_agent_runtime/evidence_engine.py:683).
- Existing negative timestamp tests cover `source_timestamp`, deployment `started_at`, and runtime event `occurred_at`, but not metric point timestamps: [test_source_adapters.py](/home/anton/projects/governed-agent-runtime/tests/unit/test_source_adapters.py:104).

Concrete failure scenario:
A malformed old-version 5xx point such as `{"timestamp": "zzzz-not-a-date", "value": 0.5}` is accepted by `normalize_source()`. Because `_latest_metric()` uses `max(..., key=lambda point: point["timestamp"])`, that invalid string is treated as latest and changes `claim-s01-version-regression` from `SUPPORTED` to `UNKNOWN`, driving evidence sufficiency to `INSUFFICIENT`.

Smallest justified fix:
Validate every metric point `timestamp` in `_normalize_service_metrics()` before returning observations, using the same timezone-aware parser as promoted normalized timestamps. Prefer parsing timestamps for latest-point selection rather than string comparison.

Missing test:
Add a negative source-adapter test for `get_service_metrics -> metric_series[*].points[*].timestamp`, asserting `SourceAdapterError.code == "INVALID_SOURCE_TIMESTAMP"` and no observations returned.

**Medium — Tool Result Envelope timestamp formats are not actually enforced at the application boundary**

Evidence:
- T019 requires complete Tool Result Envelope validation before state update: [state-transition-table.yaml](/home/anton/projects/governed-agent-runtime/specs/core/state-transition-table.yaml:206).
- The schema declares `collected_at` and `source_timestamp` as `format: date-time`: [tool-result.schema.json](/home/anton/projects/governed-agent-runtime/schemas/tool-result.schema.json:36).
- `apply_preparation_tool_result()` validates the schema without any explicit timestamp parsing: [preparation_tools.py](/home/anton/projects/governed-agent-runtime/src/governed_agent_runtime/preparation_tools.py:158).
- The trace stores the nested envelope as authoritative: [execution_trace.py](/home/anton/projects/governed-agent-runtime/src/governed_agent_runtime/execution_trace.py:278), while the trace contract requires the complete validated envelope: [execution-trace-contract.md](/home/anton/projects/governed-agent-runtime/specs/core/execution-trace-contract.md:11).
- Existing app-boundary test only removes `schema_version`; it does not mutate timestamp formats: [test_preparation_tools.py](/home/anton/projects/governed-agent-runtime/tests/unit/test_preparation_tools.py:376).

Concrete failure scenario:
An externally supplied `create_remediation_plan` execution record with `tool_result["collected_at"] = "not-a-date"` and otherwise valid fields passes the current application boundary, mutates state to `ACTION_CANDIDATE`, and can be recorded in the trace as the authoritative tool result envelope.

Smallest justified fix:
Add explicit timezone-aware timestamp validation for `tool_result.collected_at` and non-null `tool_result.source_timestamp` in `apply_preparation_tool_result()` before any state copy/mutation. Do not rely on JSON Schema `format` behavior alone.

Missing test:
Add a negative application-boundary test that mutates `tool_result["collected_at"]` and asserts `ValueError` plus unchanged input state.

**Verification Note**

I could not run `pytest` because this read-only sandbox has no usable writable temp directory for pytest capture. I did run direct read-only Python probes confirming the metric timestamp failure scenario and that the current JSON Schema validation does not reject malformed date-time strings in this environment.

**Verdict**

The deterministic S01 baseline is not ready to freeze.

S02-S12 deterministic extension should not begin until the metric timestamp normalization bug is fixed. The tool-result timestamp validation gap should also be closed before freeze because it weakens the claimed application-boundary and audit-trace contract.
