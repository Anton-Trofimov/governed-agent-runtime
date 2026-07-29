"""Execute deterministic preparation-tool mocks and apply results."""

import hashlib
import json
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from jsonschema import Draft202012Validator, ValidationError


def execute_preparation_tool(
    state: Mapping[str, Any],
    proposal: Mapping[str, Any],
    decision: Mapping[str, Any],
    *,
    tool_contracts: Mapping[str, Any],
    tool_result_schema: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute one allowed deterministic preparation-tool mock."""
    _validate_runtime_context(state, proposal, decision)

    payload = proposal["payload"]
    tool_name = payload["tool_name"]
    arguments = deepcopy(payload["arguments"])

    contract = _find_tool_contract(tool_name, tool_contracts)

    if contract["category"] != "preparation":
        raise ValueError(
            f"Tool {tool_name} is not a preparation tool"
        )

    phase = state["session_state"]["phase"]

    if phase not in contract["allowed_phases"]:
        raise ValueError(
            f"Preparation tool requires PREPARE phase; got {phase}"
        )

    _validate_arguments(arguments, contract["input_schema"])

    canonical_arguments = json.dumps(
        arguments,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    arguments_hash = hashlib.sha256(
        canonical_arguments.encode("utf-8")
    ).hexdigest()

    session_id = state["session_state"]["session_id"]

    stable_digest = hashlib.sha256(
        f"{session_id}:{arguments_hash}".encode()
    ).hexdigest()

    mock_contract = contract["deterministic_mock"]

    tool_call_id = (
        f"{mock_contract['tool_call_id_prefix']}-"
        f"{stable_digest[:16]}"
    )
    remediation_plan_id = (
        f"{mock_contract['artifact_id_prefix']}-"
        f"{stable_digest[:16]}"
    )

    missing_preconditions = list(
        arguments.get("required_precondition_ids", [])
    )

    readiness_key = (
        "missing_preconditions"
        if missing_preconditions
        else "no_missing_preconditions"
    )
    readiness_status = mock_contract["readiness_status"][
        readiness_key
    ]

    validation_warnings = []

    if missing_preconditions:
        validation_warnings.append(
            "Operational action is not ready for execution."
        )

    timestamp = state["updated_at"]
    plan_version = mock_contract["fixed_plan_version"]

    tool_result = {
        "schema_version": "0.1.0",
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
        "status": "SUCCEEDED",
        "collected_at": timestamp,
        "source_timestamp": None,
        "raw_reference": (
            f"mock://remediation-plans/"
            f"{remediation_plan_id}/{plan_version}"
        ),
        "result": {
            "remediation_plan_id": remediation_plan_id,
            "plan_version": plan_version,
            "readiness_status": readiness_status,
            "missing_preconditions": missing_preconditions,
            "validation_warnings": validation_warnings,
        },
        "errors": [],
    }

    try:
        Draft202012Validator(tool_result_schema).validate(
            tool_result
        )
    except ValidationError as error:
        raise ValueError(
            "Generated preparation tool result failed schema "
            f"validation: {error.message}"
        ) from error

    successful_result = mock_contract["successful_result"]

    return {
        "tool_category": contract["category"],
        "arguments": arguments,
        "arguments_hash": arguments_hash,
        "idempotency_key": f"idempotency-{stable_digest}",
        "target": {
            "service_id": arguments["service_id"],
            "environment_id": arguments["environment_id"],
        },
        "started_at": timestamp,
        "completed_at": timestamp,
        "transition_id": successful_result["transition_id"],
        "next_state": successful_result["next_state"],
        "resulting_phase": successful_result["resulting_phase"],
        "tool_result": tool_result,
    }


def apply_preparation_tool_result(
    state: Mapping[str, Any],
    proposal: Mapping[str, Any],
    execution: Mapping[str, Any],
    *,
    transition_spec: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Normalize a successful preparation result and apply its transition."""
    tool_result = execution["tool_result"]

    if tool_result["status"] != "SUCCEEDED":
        raise ValueError(
            "Preparation tool result must be successful"
        )

    if (
        tool_result["tool_name"]
        != proposal["payload"]["tool_name"]
    ):
        raise ValueError(
            "Preparation tool result does not match proposal"
        )

    transition = _find_transition_by_id(
        execution["transition_id"],
        transition_spec,
    )

    current_state = state["session_state"]["task_state"]

    if transition["from"] != current_state:
        raise ValueError(
            "Preparation result transition does not match "
            f"current task state {current_state}"
        )

    if transition["to"] != execution["next_state"]:
        raise ValueError(
            "Preparation result next state does not match "
            "the transition contract"
        )

    updated = deepcopy(dict(state))
    updated["state_version"] += 1
    updated["session_state"]["task_state"] = transition["to"]

    resulting_phase = transition.get("resulting_phase")

    if resulting_phase is not None:
        updated["session_state"]["phase"] = resulting_phase

    updated["session_state"]["tool_call_count"] += 1

    proposed_action = deepcopy(
        proposal["payload"]["arguments"]["candidate_action"]
    )
    plan_result = tool_result["result"]

    proposed_action["remediation_plan_id"] = plan_result[
        "remediation_plan_id"
    ]
    proposed_action["remediation_plan_version"] = plan_result[
        "plan_version"
    ]

    updated["action_readiness"]["candidate_action"] = (
        proposed_action
    )
    updated["action_readiness"]["action_ready"] = False

    return updated, {
        "application_rule_type": "STATE_TRANSITION",
        "application_rule_id": transition["transition_id"],
        "lifecycle_disposition": None,
    }


def _validate_runtime_context(
    state: Mapping[str, Any],
    proposal: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> None:
    if decision["decision"] != "ALLOW":
        raise ValueError(
            "Preparation tool requires an ALLOW runtime decision"
        )

    if decision["tool_execution_allowed"] is not True:
        raise ValueError(
            "Preparation tool requires tool execution permission"
        )

    if (
        decision["proposal_id"]
        != proposal.get("proposal_id")
    ):
        raise ValueError(
            "Runtime decision does not match the proposal"
        )

    phase = state["session_state"]["phase"]

    if phase != "PREPARE":
        raise ValueError(
            f"Preparation tool requires PREPARE phase; got {phase}"
        )

    task_state = state["session_state"]["task_state"]

    if task_state != "PREPARING":
        raise ValueError(
            "Preparation tool requires PREPARING task state"
        )

    if decision["next_state"] != task_state:
        raise ValueError(
            "Runtime decision is stale for the current task state"
        )

    session = state["session_state"]

    if session["tool_call_count"] >= session["tool_call_budget"]:
        raise ValueError(
            "Preparation tool call budget is exhausted"
        )

    if proposal.get("proposal_type") != "CREATE_DRAFT":
        raise ValueError(
            "Preparation tool requires CREATE_DRAFT proposal"
        )


def _find_tool_contract(
    tool_name: str,
    tool_contracts: Mapping[str, Any],
) -> Mapping[str, Any]:
    matches = [
        contract
        for contract in tool_contracts["tools"]
        if contract["tool_name"] == tool_name
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Expected one tool contract for {tool_name}, "
            f"found {len(matches)}"
        )

    return matches[0]


def _validate_arguments(
    arguments: Mapping[str, Any],
    input_schema: Mapping[str, Any],
) -> None:
    schema = _normalize_contract_schema(input_schema)

    try:
        Draft202012Validator(schema).validate(arguments)
    except ValidationError as error:
        raise ValueError(
            "Invalid preparation tool arguments: "
            f"{error.message}"
        ) from error


def _normalize_contract_schema(value: Any) -> Any:
    if isinstance(value, Mapping):
        normalized = {}

        for key, item in value.items():
            normalized_key = (
                "additionalProperties"
                if key == "additional_properties"
                else key
            )
            normalized[normalized_key] = (
                _normalize_contract_schema(item)
            )

        return normalized

    if isinstance(value, list):
        return [
            _normalize_contract_schema(item)
            for item in value
        ]

    return value


def _find_transition_by_id(
    transition_id: str,
    transition_spec: Mapping[str, Any],
) -> Mapping[str, Any]:
    matches = [
        transition
        for transition in transition_spec["transitions"]
        if transition["transition_id"] == transition_id
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Expected one transition {transition_id}, "
            f"found {len(matches)}"
        )

    return matches[0]
