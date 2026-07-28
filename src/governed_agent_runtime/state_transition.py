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
    current_state = state["session_state"]["task_state"]
    next_state = decision["next_state"]

    application_rule = _find_decision_application_rule(
        decision,
        transition_spec,
    )

    if application_rule is not None:
        return _apply_lifecycle_disposition(
            state,
            decision,
            application_rule,
            transition_spec,
        )

    transition = _find_transition(
        current_state,
        next_state,
        transition_spec,
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

    return updated


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
