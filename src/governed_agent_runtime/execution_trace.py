"""Build deterministic append-only decision-application traces."""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


def build_decision_application_trace(
    state_before: Mapping[str, Any],
    proposal: Mapping[str, Any],
    decision: Mapping[str, Any],
    state_after: Mapping[str, Any],
    *,
    application_record: Mapping[str, Any],
) -> dict[str, Any]:
    """Record proposal, policy, decision and applied state update."""
    _validate_application(
        state_before,
        decision,
        state_after,
        application_record,
    )

    trace_id = state_before["trace_id"]
    decision_time = decision["decided_at"]
    proposal_time = proposal.get("created_at", decision_time)

    events: list[dict[str, Any]] = []

    _append_event(
        events,
        trace_id=trace_id,
        event_type="PROPOSAL_CREATED",
        occurred_at=proposal_time,
        payload={
            "proposal": deepcopy(dict(proposal)),
        },
    )

    for gate_result in decision["gate_results"]:
        _append_event(
            events,
            trace_id=trace_id,
            event_type="GATE_EVALUATED",
            occurred_at=decision_time,
            payload={
                "decision_id": decision["decision_id"],
                "proposal_id": decision["proposal_id"],
                **deepcopy(dict(gate_result)),
            },
        )

    _append_event(
        events,
        trace_id=trace_id,
        event_type="RUNTIME_DECISION",
        occurred_at=decision_time,
        payload=_runtime_decision_payload(decision),
    )

    _append_event(
        events,
        trace_id=trace_id,
        event_type="STATE_UPDATED",
        occurred_at=decision_time,
        payload=_state_updated_payload(
            state_before,
            decision,
            state_after,
            application_record,
        ),
    )

    return {
        "schema_version": "0.1.0",
        "trace_id": trace_id,
        "session_id": state_before["session_state"]["session_id"],
        "started_at": state_before["updated_at"],
        "completed_at": None,
        "terminal_outcome": state_after["execution_state"][
            "terminal_outcome"
        ],
        "events": events,
    }


def _append_event(
    events: list[dict[str, Any]],
    *,
    trace_id: str,
    event_type: str,
    occurred_at: str,
    payload: dict[str, Any],
) -> None:
    sequence = len(events) + 1

    events.append(
        {
            "sequence": sequence,
            "event_id": f"{trace_id}-event-{sequence:04d}",
            "event_type": event_type,
            "occurred_at": occurred_at,
            "visibility": "RUNTIME_ONLY",
            "payload": payload,
        }
    )


def _runtime_decision_payload(
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "decision_id": decision["decision_id"],
        "proposal_id": decision["proposal_id"],
        "decision": decision["decision"],
        "reason_codes": deepcopy(decision["reason_codes"]),
        "message": decision.get("message"),
        "next_state": decision["next_state"],
        "safer_path": deepcopy(decision.get("safer_path")),
        "tool_execution_allowed": decision[
            "tool_execution_allowed"
        ],
        "confirmation_request_required": decision[
            "confirmation_request_required"
        ],
    }


def _state_updated_payload(
    state_before: Mapping[str, Any],
    decision: Mapping[str, Any],
    state_after: Mapping[str, Any],
    application_record: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "decision_id": decision["decision_id"],
        "proposal_id": decision["proposal_id"],
        "application_rule_type": application_record[
            "application_rule_type"
        ],
        "application_rule_id": application_record[
            "application_rule_id"
        ],
        "lifecycle_disposition": application_record[
            "lifecycle_disposition"
        ],
        "previous_state_version": state_before["state_version"],
        "new_state_version": state_after["state_version"],
        "previous_task_state": state_before["session_state"][
            "task_state"
        ],
        "new_task_state": state_after["session_state"][
            "task_state"
        ],
        "previous_phase": state_before["session_state"]["phase"],
        "new_phase": state_after["session_state"]["phase"],
        "action_ready_before": state_before["action_readiness"][
            "action_ready"
        ],
        "action_ready_after": state_after["action_readiness"][
            "action_ready"
        ],
        "terminal_outcome_before": state_before["execution_state"][
            "terminal_outcome"
        ],
        "terminal_outcome_after": state_after["execution_state"][
            "terminal_outcome"
        ],
    }


def _validate_application(
    state_before: Mapping[str, Any],
    decision: Mapping[str, Any],
    state_after: Mapping[str, Any],
    application_record: Mapping[str, Any],
) -> None:
    expected_version = state_before["state_version"] + 1

    if state_after["state_version"] != expected_version:
        raise ValueError(
            "Applied state version must increment by exactly one"
        )

    if (
        state_after["session_state"]["task_state"]
        != decision["next_state"]
    ):
        raise ValueError(
            "Applied task state must match decision next_state"
        )

    rule_type = application_record["application_rule_type"]
    rule_id = application_record["application_rule_id"]
    disposition = application_record["lifecycle_disposition"]

    if rule_type == "STATE_TRANSITION":
        if not rule_id.startswith("T"):
            raise ValueError(
                "State transition record must use a T rule identifier"
            )

        if disposition is not None:
            raise ValueError(
                "State transition cannot declare a lifecycle disposition"
            )

        return

    if rule_type == "DECISION_APPLICATION_RULE":
        if not rule_id.startswith("DA"):
            raise ValueError(
                "Decision application record must use a DA identifier"
            )

        if not isinstance(disposition, str) or not disposition:
            raise ValueError(
                "Decision application rule requires a disposition"
            )

        return

    raise ValueError(
        f"Unsupported application rule type: {rule_type}"
    )
