"""Evaluate structured proposals through deterministic runtime policy gates."""

from collections.abc import Mapping
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from governed_agent_runtime.contract_schema import normalize_contract_schema


def evaluate_proposal(
    state: Mapping[str, Any],
    proposal: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    tool_contracts: Mapping[str, Any],
    proposal_schema: Mapping[str, Any],
    transition_spec: Mapping[str, Any],
) -> dict[str, Any]:
    gate_results: list[dict[str, Any]] = []

    schema_error = _validate_proposal_schema(
        proposal,
        proposal_schema,
        tool_contracts,
    )

    if schema_error is not None:
        return _failure_decision(
            state,
            proposal,
            policy,
            gate_results,
            failed_gate_id="G01_SCHEMA_VALIDITY",
            decision="BLOCK",
            reason_code="INVALID_PROPOSAL_SCHEMA",
            next_state=state["session_state"]["task_state"],
            details={"message": schema_error},
        )

    _append_gate(gate_results, "G01_SCHEMA_VALIDITY", "PASSED")

    tool_name = _proposal_tool_name(proposal)
    tool_contract = (
        _find_tool_contract(tool_name, tool_contracts)
        if tool_name is not None
        else None
    )

    if not _target_is_resolved(state, proposal, tool_contract):
        return _failure_decision(
            state,
            proposal,
            policy,
            gate_results,
            failed_gate_id="G02_TARGET_RESOLUTION",
            decision="ASK_CLARIFICATION",
            reason_code="TARGET_NOT_RESOLVED",
        )

    _append_gate(gate_results, "G02_TARGET_RESOLUTION", "PASSED")

    if not _phase_allows_proposal(
        state,
        proposal,
        tool_contract,
        policy,
        transition_spec,
    ):
        return _failure_decision(
            state,
            proposal,
            policy,
            gate_results,
            failed_gate_id="G03_PHASE_PERMISSION",
            decision="REPLACE_WITH_SAFER_PATH",
            reason_code="TOOL_NOT_ALLOWED_IN_PHASE",
            safer_path=_safer_path(proposal),
        )

    _append_gate(gate_results, "G03_PHASE_PERMISSION", "PASSED")

    state_changing = (
        tool_contract is not None
        and tool_contract["category"] == "state_changing"
    )

    if state_changing:
        if not state["action_readiness"]["role_authorized"]:
            return _failure_decision(
                state,
                proposal,
                policy,
                gate_results,
                failed_gate_id="G04_ROLE_AUTHORIZATION",
                decision="BLOCK",
                reason_code="ROLE_NOT_AUTHORIZED",
            )

        _append_gate(gate_results, "G04_ROLE_AUTHORIZATION", "PASSED")
    else:
        _append_gate(
            gate_results,
            "G04_ROLE_AUTHORIZATION",
            "NOT_APPLICABLE",
        )

    if state_changing:
        evidence = state["evidence_state"]
        readiness = state["action_readiness"]

        if (
            evidence["evidence_sufficiency"] != "SUFFICIENT"
            or not readiness["evidence_gate_passed"]
        ):
            return _failure_decision(
                state,
                proposal,
                policy,
                gate_results,
                failed_gate_id="G05_EVIDENCE_SUFFICIENCY",
                decision="REPLACE_WITH_SAFER_PATH",
                reason_code="EVIDENCE_INSUFFICIENT",
                safer_path=_safer_path(proposal),
            )

        _append_gate(gate_results, "G05_EVIDENCE_SUFFICIENCY", "PASSED")
    else:
        _append_gate(
            gate_results,
            "G05_EVIDENCE_SUFFICIENCY",
            "NOT_APPLICABLE",
        )

    if state_changing:
        evidence = state["evidence_state"]
        readiness = state["action_readiness"]

        if (
            evidence["freshness_status"] != "FRESH"
            or not readiness["freshness_gate_passed"]
        ):
            return _failure_decision(
                state,
                proposal,
                policy,
                gate_results,
                failed_gate_id="G06_FRESHNESS_AND_CONSISTENCY",
                decision="REPLACE_WITH_SAFER_PATH",
                reason_code="EVIDENCE_STALE_OR_CONFLICTING",
                safer_path=_safer_path(proposal),
            )

        _append_gate(
            gate_results,
            "G06_FRESHNESS_AND_CONSISTENCY",
            "PASSED",
        )
    else:
        _append_gate(
            gate_results,
            "G06_FRESHNESS_AND_CONSISTENCY",
            "NOT_APPLICABLE",
        )

    if state_changing:
        readiness = state["action_readiness"]

        if (
            not readiness["preconditions_passed"]
            or readiness["conflicting_operation_present"]
        ):
            return _failure_decision(
                state,
                proposal,
                policy,
                gate_results,
                failed_gate_id="G07_TECHNICAL_PRECONDITIONS",
                decision="BLOCK",
                reason_code="TECHNICAL_PRECONDITION_FAILED",
            )

        _append_gate(
            gate_results,
            "G07_TECHNICAL_PRECONDITIONS",
            "PASSED",
        )
    else:
        _append_gate(
            gate_results,
            "G07_TECHNICAL_PRECONDITIONS",
            "NOT_APPLICABLE",
        )

    if state_changing:
        confirmation = state.get("confirmation_state")

        if not confirmation or confirmation.get("status") != "VALID":
            return _failure_decision(
                state,
                proposal,
                policy,
                gate_results,
                failed_gate_id="G08_CONFIRMATION",
                decision="REQUIRE_CONFIRMATION",
                reason_code="CONFIRMATION_REQUIRED_OR_INVALID",
            )

        _append_gate(gate_results, "G08_CONFIRMATION", "PASSED")
    else:
        _append_gate(
            gate_results,
            "G08_CONFIRMATION",
            "NOT_APPLICABLE",
        )

    session = state["session_state"]

    if (
        tool_name is not None
        and session["tool_call_count"] >= session["tool_call_budget"]
    ):
        return _failure_decision(
            state,
            proposal,
            policy,
            gate_results,
            failed_gate_id="G09_BUDGET_AND_REPETITION",
            decision="SAFE_FALLBACK",
            reason_code="EXECUTION_BUDGET_EXCEEDED",
        )

    if session.get("repeated_call_count", 0) > 1:
        return _failure_decision(
            state,
            proposal,
            policy,
            gate_results,
            failed_gate_id="G09_BUDGET_AND_REPETITION",
            decision="SAFE_FALLBACK",
            reason_code="REPEATED_TOOL_CALL",
        )

    _append_gate(gate_results, "G09_BUDGET_AND_REPETITION", "PASSED")

    if not (
        state.get("trace_id")
        and session.get("session_id")
        and proposal.get("proposal_id")
    ):
        return _failure_decision(
            state,
            proposal,
            policy,
            gate_results,
            failed_gate_id="G10_AUDIT_READINESS",
            decision="BLOCK",
            reason_code="AUDIT_DATA_INCOMPLETE",
        )

    _append_gate(gate_results, "G10_AUDIT_READINESS", "PASSED")

    decision, next_state = _successful_outcome(
        proposal,
        tool_contract,
    )

    return _decision(
        state,
        proposal,
        decision=decision,
        reason_codes=[],
        gate_results=gate_results,
        next_state=next_state,
        safer_path=None,
        tool_execution_allowed=tool_name is not None,
        confirmation_request_required=False,
    )


def _validate_proposal_schema(
    proposal: Mapping[str, Any],
    proposal_schema: Mapping[str, Any],
    tool_contracts: Mapping[str, Any],
) -> str | None:
    try:
        Draft202012Validator(
            proposal_schema,
            format_checker=FormatChecker(),
        ).validate(proposal)

        tool_name = _proposal_tool_name(proposal)

        if tool_name is not None:
            contract = _find_tool_contract(tool_name, tool_contracts)
            arguments = proposal["payload"].get("arguments", {})

            Draft202012Validator(
                normalize_contract_schema(
                    contract["input_schema"]
                ),
                format_checker=FormatChecker(),
            ).validate(arguments)

    except (ValidationError, ValueError) as error:
        return str(error)

    return None


def _find_tool_contract(
    tool_name: str,
    tool_contracts: Mapping[str, Any],
) -> Mapping[str, Any]:
    matches = [
        tool
        for tool in tool_contracts["tools"]
        if tool["tool_name"] == tool_name
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Expected one tool contract for {tool_name}, got {len(matches)}"
        )

    return matches[0]


def _proposal_tool_name(
    proposal: Mapping[str, Any],
) -> str | None:
    if proposal.get("proposal_type") in {
        "CALL_TOOL",
        "CREATE_DRAFT",
        "REQUEST_CONFIRMATION",
    }:
        return proposal.get("payload", {}).get("tool_name")

    return None


def _target_is_resolved(
    state: Mapping[str, Any],
    proposal: Mapping[str, Any],
    tool_contract: Mapping[str, Any] | None,
) -> bool:
    if tool_contract is None:
        return True

    session = state["session_state"]

    if not (
        session.get("resolved_service_id")
        and session.get("resolved_environment_id")
    ):
        return False

    arguments = proposal["payload"].get("arguments", {})

    if (
        "service_id" in arguments
        and arguments["service_id"] != session["resolved_service_id"]
    ):
        return False

    if (
        "environment_id" in arguments
        and arguments["environment_id"]
        != session["resolved_environment_id"]
    ):
        return False

    if tool_contract["category"] == "state_changing":
        scope = session.get("resolved_scope") or {}

        if not scope.get("deployment_target_id"):
            return False

    return True


def _phase_allows_proposal(
    state: Mapping[str, Any],
    proposal: Mapping[str, Any],
    tool_contract: Mapping[str, Any] | None,
    policy: Mapping[str, Any],
    transition_spec: Mapping[str, Any],
) -> bool:
    phase = state["session_state"]["phase"]
    phase_policy = policy["phases"][phase]

    proposal_allowed = (
        proposal["proposal_type"]
        in phase_policy["allowed_proposals"]
    )
    tool_category_allowed = (
        tool_contract is None
        or tool_contract["category"]
        in phase_policy["allowed_tool_categories"]
    )

    if proposal_allowed and tool_category_allowed:
        return True

    return _matches_transition_aware_phase_rule(
        state,
        proposal,
        tool_contract,
        policy,
        transition_spec,
    )


def _matches_transition_aware_phase_rule(
    state: Mapping[str, Any],
    proposal: Mapping[str, Any],
    tool_contract: Mapping[str, Any] | None,
    policy: Mapping[str, Any],
    transition_spec: Mapping[str, Any],
) -> bool:
    if tool_contract is None:
        return False

    session = state["session_state"]
    tool_category = tool_contract["category"]

    next_state_by_category = {
        "read_only": "DIAGNOSING",
        "preparation": "PREPARING",
        "state_changing": "EXECUTING",
    }

    try:
        decision_next_state = next_state_by_category[tool_category]
    except KeyError:
        return False

    for rule in policy.get(
        "transition_aware_phase_rules",
        [],
    ):
        transition_id = rule.get("transition_id")

        if not isinstance(transition_id, str) or not transition_id:
            continue

        matching_transitions = [
            transition
            for transition in transition_spec["transitions"]
            if transition.get("transition_id") == transition_id
        ]

        if len(matching_transitions) != 1:
            continue

        transition = matching_transitions[0]

        if (
            transition.get("from") != session["task_state"]
            or transition.get("to") != decision_next_state
            or transition.get("resulting_phase")
            != rule["permission_phase"]
        ):
            continue

        if not rule.get(
            "tool_execution_after_transition_only",
            False,
        ):
            continue

        if rule["permission_phase"] not in tool_contract[
            "allowed_phases"
        ]:
            continue

        if (
            rule["current_phase"] == session["phase"]
            and rule["current_task_state"]
            == session["task_state"]
            and rule["proposal_type"]
            == proposal["proposal_type"]
            and rule["tool_category"] == tool_category
            and rule["decision_next_state"]
            == decision_next_state
        ):
            return True

    return False


def _successful_outcome(
    proposal: Mapping[str, Any],
    tool_contract: Mapping[str, Any] | None,
) -> tuple[str, str]:
    proposal_type = proposal["proposal_type"]

    if tool_contract is not None:
        next_state = {
            "read_only": "DIAGNOSING",
            "preparation": "PREPARING",
            "state_changing": "EXECUTING",
        }[tool_contract["category"]]

        return "ALLOW", next_state

    if proposal_type == "PROVIDE_ANSWER":
        return "PROVIDE_ANSWER", "COMPLETED"

    if proposal_type == "ASK_CLARIFICATION":
        return "ASK_CLARIFICATION", "NEEDS_CLARIFICATION"

    if proposal_type == "STOP_OR_ESCALATE":
        outcome = proposal["payload"]["outcome"]

        if outcome == "ESCALATE":
            return "ESCALATE", "ESCALATED"

        return "SAFE_FALLBACK", "SAFE_FALLBACK"

    return "ALLOW", state_for_proposal(proposal_type)


def state_for_proposal(proposal_type: str) -> str:
    return {
        "PROVIDE_BOUNDED_HYPOTHESIS": "HYPOTHESIS_READY",
        "REQUEST_CONFIRMATION": "AWAITING_CONFIRMATION",
    }.get(proposal_type, "DIAGNOSING")


def _safer_path(
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    tool_name = _proposal_tool_name(proposal)

    if tool_name in {
        "rollback_deployment",
        "restart_single_replica",
    }:
        return {
            "proposal_type": "CREATE_DRAFT",
            "tool_name": "create_remediation_plan",
            "rationale": (
                "Record supported evidence, missing preconditions, risks "
                "and verification steps before requesting execution."
            ),
        }

    return {
        "proposal_type": "CALL_TOOL",
        "rationale": (
            "Collect the lowest-risk missing evidence before continuing."
        ),
    }


def _failure_decision(
    state: Mapping[str, Any],
    proposal: Mapping[str, Any],
    policy: Mapping[str, Any],
    gate_results: list[dict[str, Any]],
    *,
    failed_gate_id: str,
    decision: str,
    reason_code: str,
    next_state: str | None = None,
    safer_path: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _append_gate(
        gate_results,
        failed_gate_id,
        "FAILED",
        reason_code=reason_code,
        details=details,
    )
    _append_skipped_gates(gate_results, policy)

    reason_codes = [reason_code]

    if safer_path is not None:
        reason_codes.append("SAFER_PATH_AVAILABLE")

    if next_state is None:
        next_state = {
            "ASK_CLARIFICATION": "NEEDS_CLARIFICATION",
            "REPLACE_WITH_SAFER_PATH": (
                "PREPARING"
                if safer_path
                and safer_path.get("tool_name") == "create_remediation_plan"
                else "DIAGNOSING"
            ),
            "BLOCK": "BLOCKED",
            "SAFE_FALLBACK": "SAFE_FALLBACK",
            "REQUIRE_CONFIRMATION": "AWAITING_CONFIRMATION",
            "ESCALATE": "ESCALATED",
        }[decision]

    return _decision(
        state,
        proposal,
        decision=decision,
        reason_codes=reason_codes,
        gate_results=gate_results,
        next_state=next_state,
        safer_path=safer_path,
        tool_execution_allowed=False,
        confirmation_request_required=decision == "REQUIRE_CONFIRMATION",
    )


def _append_skipped_gates(
    gate_results: list[dict[str, Any]],
    policy: Mapping[str, Any],
) -> None:
    completed = {item["gate_id"] for item in gate_results}

    for gate in policy["gate_order"]:
        if gate["gate_id"] not in completed:
            _append_gate(gate_results, gate["gate_id"], "SKIPPED")


def _append_gate(
    gate_results: list[dict[str, Any]],
    gate_id: str,
    status: str,
    *,
    reason_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    gate_results.append(
        {
            "gate_id": gate_id,
            "status": status,
            "reason_code": reason_code,
            "details": details,
        }
    )


def _decision(
    state: Mapping[str, Any],
    proposal: Mapping[str, Any],
    *,
    decision: str,
    reason_codes: list[str],
    gate_results: list[dict[str, Any]],
    next_state: str,
    safer_path: dict[str, Any] | None,
    tool_execution_allowed: bool,
    confirmation_request_required: bool,
) -> dict[str, Any]:
    proposal_id = proposal.get("proposal_id", "unknown-proposal")

    return {
        "schema_version": "0.1.0",
        "decision_id": f"decision-{proposal_id}",
        "proposal_id": proposal_id,
        "decision": decision,
        "reason_codes": reason_codes,
        "message": None,
        "gate_results": gate_results,
        "next_state": next_state,
        "safer_path": safer_path,
        "tool_execution_allowed": tool_execution_allowed,
        "confirmation_request_required": confirmation_request_required,
        "decided_at": state["updated_at"],
    }
