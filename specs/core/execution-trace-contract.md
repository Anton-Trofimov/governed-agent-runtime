# Execution Trace Contract

## Purpose

The execution trace records the governed lineage from proposal and runtime
decision through tool execution, produced artifacts and normalized-state
updates.

## Tool result recording

For every `TOOL_RESULT_RECEIVED` event, the trace must retain the complete
validated Tool Result Envelope that was received by the runtime.

The envelope includes:

- `schema_version`;
- `tool_call_id`;
- `tool_name`;
- `status`;
- `collected_at`;
- `source_timestamp`;
- `raw_reference`;
- `result`;
- `errors`.

The nested `tool_result` is the authoritative record of the tool response that
was used by the runtime.

Selected flattened fields may remain in the event payload for indexing and
inspection. When present, they must match the authoritative nested envelope.

## Required invariants

- The trace stores a deep copy of the validated Tool Result Envelope.
- Later mutation of the execution object must not change the trace.
- The recorded envelope is identical to the result passed to state application.
- Artifact identifiers, versions, readiness and warnings remain auditable.
- A trace record does not prove persistence in an external audit store.
- Raw source data may remain behind `raw_reference`; it need not be duplicated.

## Deterministic Exp 18.0 scope

The current vertical validates this contract for the deterministic
`create_remediation_plan` preparation tool. Other preparation and
state-changing tools must follow the same contract when implemented.
