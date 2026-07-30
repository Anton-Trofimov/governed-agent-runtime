"""Validate and apply runtime decisions to normalized state copies."""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


def apply_runtime_decision(
    state: Mapping[str, Any],
    decision: Mapping[str, Any],
    *,
    transition_spec: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply one validated decision without executing a tool."""
    updated, _ = apply_runtime_decision_with_record(
        state,
        decision,
        transition_spec=transition_spec,
    )

    return updated


def apply_runtime_decision_with_record(
    state: Mapping[str, Any],
    decision: Mapping[str, Any],
    *,
    transition_spec: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply a decision and return the authoritative rule record."""
    current_state = state["session_state"]["task_state"]
    next_state = decision["next_state"]

    application_rule = _find_decision_application_rule(
        decision,
        transition_spec,
    )

    if application_rule is not None:
        updated = _apply_lifecycle_disposition(
            state,
            decision,
            application_rule,
            transition_spec,
        )

        return updated, {
            "application_rule_type": (
                "DECISION_APPLICATION_RULE"
            ),
            "application_rule_id": application_rule["rule_id"],
            "lifecycle_disposition": application_rule[
                "lifecycle_disposition"
            ],
        }

    transition = _find_transition(
        current_state,
        next_state,
        transition_spec,
    )

    _validate_transition_semantics(
        decision,
        transition,
    )

    updated = deepcopy(dict(state))
    updated["state_version"] += 1
    updated["session_state"]["task_state"] = next_state

    resulting_phase = transition.get("resulting_phase")

    if resulting_phase is not None:
        updated["session_state"]["phase"] = resulting_phase

    invariants = set(transition.get("invariants", []))

    if "action_ready_remains_false" in invariants:
        updated["action_readiness"]["action_ready"] = False

    return updated, {
        "application_rule_type": "STATE_TRANSITION",
        "application_rule_id": transition["transition_id"],
        "lifecycle_disposition": None,
    }


def _find_decision_application_rule(
    decision: Mapping[str, Any],
    transition_spec: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    reason_codes = set(decision.get("reason_codes", []))

    matches = [
        rule
        for rule in transition_spec.get(
            "decision_application_rules",
            [],
        )
        if rule["decision"] == decision["decision"]
        and rule["reason_code"] in reason_codes
    ]

    if len(matches) > 1:
        raise ValueError(
            "Expected at most one decision application rule, "
            f"found {len(matches)}"
        )

    return matches[0] if matches else None


def _apply_lifecycle_disposition(
    state: Mapping[str, Any],
    decision: Mapping[str, Any],
    application_rule: Mapping[str, Any],
    transition_spec: Mapping[str, Any],
) -> dict[str, Any]:
    disposition_id = application_rule["lifecycle_disposition"]

    try:
        disposition = transition_spec["lifecycle_dispositions"][
            disposition_id
        ]
    except KeyError as error:
        raise ValueError(
            f"Unknown lifecycle disposition: {disposition_id}"
        ) from error

    if disposition["task_state_effect"] != "RETAIN_CURRENT":
        raise ValueError(
            "Unsupported lifecycle task-state effect: "
            f"{disposition['task_state_effect']}"
        )

    if disposition["phase_effect"] != "RETAIN_CURRENT":
        raise ValueError(
            "Unsupported lifecycle phase effect: "
            f"{disposition['phase_effect']}"
        )

    current_state = state["session_state"]["task_state"]

    if decision["next_state"] != current_state:
        raise ValueError(
            "Recoverable decision next_state must retain "
            f"current task state {current_state}"
        )

    if (
        disposition["tool_execution_allowed"] is False
        and decision["tool_execution_allowed"] is not False
    ):
        raise ValueError(
            "Recoverable proposal rejection cannot allow tool execution"
        )

    if disposition["terminal_state"] is not None:
        raise ValueError(
            "Recoverable proposal rejection cannot set a terminal state"
        )

    updated = deepcopy(dict(state))
    updated["state_version"] += 1

    return updated


def _validate_transition_semantics(
    decision: Mapping[str, Any],
    transition: Mapping[str, Any],
) -> None:
    requirements = transition.get("decision_requirements")

    if requirements is None:
        return

    mismatches: list[str] = []

    for field in (
        "decision",
        "tool_execution_allowed",
        "confirmation_request_required",
    ):
        if (
            field in requirements
            and decision.get(field) != requirements[field]
        ):
            mismatches.append(field)

    if requirements.get("reason_codes_empty") is True:
        if decision.get("reason_codes") != []:
            mismatches.append("reason_codes_empty")

    required_reason_codes = set(
        requirements.get("required_reason_codes", [])
    )
    actual_reason_codes = set(
        decision.get("reason_codes", [])
    )

    if not required_reason_codes.issubset(
        actual_reason_codes
    ):
        mismatches.append("required_reason_codes")

    if "safer_path" in requirements:
        expected_safer_path = requirements["safer_path"]
        actual_safer_path = decision.get("safer_path")

        if expected_safer_path is None:
            if actual_safer_path is not None:
                mismatches.append("safer_path")
        elif not isinstance(actual_safer_path, Mapping) or any(
            actual_safer_path.get(key) != value
            for key, value in expected_safer_path.items()
        ):
            mismatches.append("safer_path")

    if mismatches:
        raise ValueError(
            "Invalid transition semantics for "
            f"{transition['transition_id']}: "
            f"{', '.join(mismatches)}"
        )


def _find_transition(
    current_state: str,
    next_state: str,
    transition_spec: Mapping[str, Any],
) -> Mapping[str, Any]:
    matches = [
        transition
        for transition in transition_spec["transitions"]
        if transition["from"] == current_state
        and transition["to"] == next_state
    ]

    if len(matches) != 1:
        raise ValueError(
            "Unsupported or ambiguous transition: "
            f"{current_state} -> {next_state}; found {len(matches)}"
        )

    return matches[0]
