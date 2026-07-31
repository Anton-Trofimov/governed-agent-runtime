import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

from governed_agent_runtime.evidence_engine import (
    apply_evidence_assessment,
    evaluate_s01_evidence,
)
from governed_agent_runtime.runtime_policy import evaluate_proposal
from governed_agent_runtime.scenario_loader import load_scenario_bundle
from governed_agent_runtime.state_builder import (
    build_normalized_state,
    normalize_selected_sources,
)
from governed_agent_runtime.state_transition import (
    apply_runtime_decision,
)

ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def build_s01_state() -> dict:
    bundle = load_scenario_bundle(ROOT, "S01")
    adapter_contracts = load_yaml(
        ROOT / "specs/core/source-adapter-contracts.yaml"
    )
    observations = normalize_selected_sources(bundle, adapter_contracts)

    state = build_normalized_state(
        bundle,
        observations,
        trace_id="trace-s01-transition",
        tool_call_count=6,
        tool_call_budget=10,
    )

    capacity_profile = load_yaml(
        ROOT / "knowledge/capacity-profiles.yaml"
    )["profiles"][0]

    assessment = evaluate_s01_evidence(
        observations,
        capacity_profile,
        reference_time=bundle.scenario["reference_time"],
    )

    return apply_evidence_assessment(state, assessment)


def evaluate(state: dict, proposal: dict) -> dict:
    return evaluate_proposal(
        state,
        proposal,
        policy=load_yaml(ROOT / "specs/core/policy-spec.yaml"),
        tool_contracts=load_yaml(
            ROOT / "specs/core/tool-contracts.yaml"
        ),
        proposal_schema=json.loads(
            (ROOT / "schemas/model-proposal.schema.json").read_text()
        ),
        transition_spec=load_yaml(
            ROOT / "specs/core/state-transition-table.yaml"
        ),
    )


def apply(state: dict, decision: dict) -> dict:
    return apply_runtime_decision(
        state,
        decision,
        transition_spec=load_yaml(
            ROOT / "specs/core/state-transition-table.yaml"
        ),
    )


def validate_state(state: dict) -> None:
    schema = json.loads(
        (ROOT / "schemas/normalized-state.schema.json").read_text()
    )

    Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    ).validate(state)


def remediation_plan_proposal(state: dict) -> dict:
    return {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-remediation-plan-transition",
        "proposal_type": "CREATE_DRAFT",
        "rationale": (
            "Record the supported regression and unresolved checks."
        ),
        "created_at": state["updated_at"],
        "payload": {
            "tool_name": "create_remediation_plan",
            "arguments": {
                "service_id": "payment-api",
                "environment_id": "production",
                "candidate_action": {
                    "action_type": "rollback_deployment"
                },
                "rationale": (
                    "Version 2.4.2 has elevated errors while "
                    "dependencies remain healthy."
                ),
                "evidence_ids": [
                    "ev-s01-version-error-old",
                    "ev-s01-version-error-new",
                ],
                "required_precondition_ids": [
                    "ROLLBACK_DATABASE_COMPATIBLE",
                    "ROLLBACK_TRANSITIONAL_CAPACITY_SUFFICIENT",
                ],
                "risks": [
                    "Current old-version capacity is insufficient."
                ],
                "verification_steps": [
                    "Verify version-specific 5xx rate after traffic shift."
                ],
                "stop_conditions": [
                    "Stop if capacity headroom is below minimum."
                ],
            },
        },
    }


def rollback_proposal(state: dict) -> dict:
    return {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-premature-transition",
        "proposal_type": "CALL_TOOL",
        "rationale": "Rollback the version associated with elevated errors.",
        "created_at": state["updated_at"],
        "payload": {
            "tool_name": "rollback_deployment",
            "arguments": {
                "service_id": "payment-api",
                "environment_id": "production",
                "deployment_target_id": (
                    "payment-api-prod-eu-central-1"
                ),
                "deployment_id": (
                    "deployment-payment-api-20260728-1140"
                ),
                "target_version_id": "2.4.1",
                "remediation_plan_id": "plan-s01-001",
                "remediation_plan_version": "1",
            },
        },
    }


def test_recoverable_invalid_proposal_retains_state_and_phase() -> None:
    state = build_s01_state()
    original = deepcopy(state)

    proposal = {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-invalid-transition",
        "proposal_type": "CALL_TOOL",
        "rationale": "Missing tool arguments.",
        "payload": {
            "tool_name": "get_service_metrics",
        },
    }

    decision = evaluate(state, proposal)
    updated = apply(state, decision)

    validate_state(updated)

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == ["INVALID_PROPOSAL_SCHEMA"]
    assert (
        decision["next_state"]
        == original["session_state"]["task_state"]
    )
    assert updated["state_version"] == original["state_version"] + 1
    assert (
        updated["session_state"]["task_state"]
        == original["session_state"]["task_state"]
    )
    assert (
        updated["session_state"]["phase"]
        == original["session_state"]["phase"]
    )
    assert updated["execution_state"]["terminal_outcome"] is None
    assert updated["action_readiness"]["action_ready"] is False
    assert state == original


def test_allowed_remediation_plan_transitions_to_preparing() -> None:
    state = build_s01_state()
    original = deepcopy(state)

    decision = evaluate(
        state,
        remediation_plan_proposal(state),
    )
    updated = apply(state, decision)

    validate_state(updated)

    assert decision["decision"] == "ALLOW"
    assert decision["next_state"] == "PREPARING"
    assert updated["state_version"] == original["state_version"] + 1
    assert updated["session_state"]["task_state"] == "PREPARING"
    assert updated["session_state"]["phase"] == "PREPARE"
    assert updated["action_readiness"]["action_ready"] is False
    assert updated["execution_state"] == original["execution_state"]
    assert state == original


def test_premature_rollback_transitions_to_preparation_path() -> None:
    state = build_s01_state()
    state["session_state"]["phase"] = "EXECUTE"
    state["session_state"]["task_state"] = "ACTION_CANDIDATE"
    state["action_readiness"]["role_authorized"] = True
    original = deepcopy(state)

    decision = evaluate(state, rollback_proposal(state))
    updated = apply(state, decision)

    validate_state(updated)

    assert decision["decision"] == "REPLACE_WITH_SAFER_PATH"
    assert decision["next_state"] == "PREPARING"
    assert decision["tool_execution_allowed"] is False
    assert updated["state_version"] == original["state_version"] + 1
    assert updated["session_state"]["task_state"] == "PREPARING"
    assert updated["session_state"]["phase"] == "PREPARE"
    assert updated["action_readiness"]["action_ready"] is False
    assert updated["execution_state"] == original["execution_state"]
    assert state == original


def test_unsupported_transition_is_rejected() -> None:
    state = build_s01_state()

    decision = {
        "schema_version": "0.1.0",
        "decision_id": "decision-unsupported-transition",
        "proposal_id": "proposal-unsupported-transition",
        "decision": "ALLOW",
        "reason_codes": [],
        "message": None,
        "gate_results": [],
        "next_state": "EXECUTING",
        "safer_path": None,
        "tool_execution_allowed": True,
        "confirmation_request_required": False,
        "decided_at": state["updated_at"],
    }

    with pytest.raises(ValueError, match="transition"):
        apply(state, decision)

def build_t033_state() -> dict:
    state = build_s01_state()
    state["session_state"]["phase"] = "EXECUTE"
    state["session_state"]["task_state"] = "ACTION_CANDIDATE"
    state["action_readiness"]["role_authorized"] = True
    return state


def test_t015_rejects_non_allow_decision() -> None:
    state = build_s01_state()
    decision = evaluate(state, remediation_plan_proposal(state))

    decision["decision"] = "REPLACE_WITH_SAFER_PATH"
    decision["reason_codes"] = ["SAFER_PATH_AVAILABLE"]
    decision["safer_path"] = {
        "proposal_type": "CREATE_DRAFT",
        "tool_name": "create_remediation_plan",
    }
    decision["tool_execution_allowed"] = False

    with pytest.raises(ValueError, match="transition semantics"):
        apply(state, decision)


def test_t015_requires_tool_execution_permission() -> None:
    state = build_s01_state()
    decision = evaluate(state, remediation_plan_proposal(state))
    decision["tool_execution_allowed"] = False

    with pytest.raises(ValueError, match="transition semantics"):
        apply(state, decision)


def test_t033_requires_safer_path_replacement_decision() -> None:
    state = build_t033_state()
    decision = evaluate(state, rollback_proposal(state))

    decision["decision"] = "ALLOW"
    decision["reason_codes"] = []
    decision["safer_path"] = None
    decision["tool_execution_allowed"] = True

    with pytest.raises(ValueError, match="transition semantics"):
        apply(state, decision)


def test_t033_forbids_tool_execution_permission() -> None:
    state = build_t033_state()
    decision = evaluate(state, rollback_proposal(state))
    decision["tool_execution_allowed"] = True

    with pytest.raises(ValueError, match="transition semantics"):
        apply(state, decision)


def test_t033_requires_preparation_safer_path() -> None:
    state = build_t033_state()
    decision = evaluate(state, rollback_proposal(state))
    decision["safer_path"] = {
        "proposal_type": "CALL_TOOL",
        "tool_name": "get_service_metrics",
    }

    with pytest.raises(ValueError, match="transition semantics"):
        apply(state, decision)

def test_t018_records_draft_created_terminal_outcome() -> None:
    state = build_s01_state()
    state["session_state"]["task_state"] = "PREPARING"
    state["session_state"]["phase"] = "PREPARE"

    decision = {
        "schema_version": "0.1.0",
        "decision_id": "decision-terminal-completed",
        "proposal_id": "proposal-terminal-completed",
        "decision": "ALLOW",
        "reason_codes": [],
        "message": None,
        "gate_results": [],
        "next_state": "COMPLETED",
        "safer_path": None,
        "tool_execution_allowed": False,
        "confirmation_request_required": False,
        "decided_at": state["updated_at"],
    }

    updated = apply(state, decision)

    validate_state(updated)

    assert updated["session_state"]["task_state"] == "COMPLETED"
    assert (
        updated["execution_state"]["terminal_outcome"]
        == "DRAFT_CREATED"
    )

def test_budget_exhaustion_from_hypothesis_ready_reaches_safe_fallback(
) -> None:
    state = build_s01_state()
    state["session_state"]["tool_call_count"] = state[
        "session_state"
    ]["tool_call_budget"]

    decision = evaluate(
        state,
        remediation_plan_proposal(state),
    )

    assert decision["decision"] == "SAFE_FALLBACK"
    assert decision["reason_codes"] == [
        "EXECUTION_BUDGET_EXCEEDED"
    ]
    assert decision["next_state"] == "SAFE_FALLBACK"
    assert decision["tool_execution_allowed"] is False

    updated = apply(state, decision)

    validate_state(updated)

    assert (
        updated["session_state"]["task_state"]
        == "SAFE_FALLBACK"
    )
    assert (
        updated["execution_state"]["terminal_outcome"]
        == "SAFE_FALLBACK"
    )
    assert updated["execution_state"]["execution_status"] == (
        "NOT_STARTED"
    )

def test_clarification_from_hypothesis_ready_enters_waiting_state(
) -> None:
    state = build_s01_state()

    proposal = {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-clarification",
        "proposal_type": "ASK_CLARIFICATION",
        "rationale": "User input is required before continuing.",
        "payload": {
            "question": (
                "Which deployment target should be investigated?"
            ),
            "missing_fields": ["deployment_target"],
        },
    }

    decision = evaluate(state, proposal)

    assert decision["decision"] == "ASK_CLARIFICATION"
    assert decision["reason_codes"] == []
    assert decision["next_state"] == "NEEDS_CLARIFICATION"
    assert decision["tool_execution_allowed"] is False
    assert decision["confirmation_request_required"] is False

    updated = apply(state, decision)

    validate_state(updated)

    assert (
        updated["session_state"]["task_state"]
        == "NEEDS_CLARIFICATION"
    )
    assert updated["session_state"]["phase"] == "DIAGNOSE"
    assert updated["execution_state"]["terminal_outcome"] is None
    assert updated["action_readiness"]["action_ready"] is False


def test_non_budget_safe_stop_from_hypothesis_ready_is_terminal(
) -> None:
    state = build_s01_state()

    proposal = {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-safe-stop",
        "proposal_type": "STOP_OR_ESCALATE",
        "rationale": (
            "A bounded safe result is available without further tools."
        ),
        "payload": {
            "outcome": "SAFE_FALLBACK",
            "summary": (
                "Preserve the bounded hypothesis and stop safely."
            ),
        },
    }

    decision = evaluate(state, proposal)

    assert decision["decision"] == "SAFE_FALLBACK"
    assert decision["reason_codes"] == []
    assert decision["next_state"] == "SAFE_FALLBACK"
    assert decision["tool_execution_allowed"] is False
    assert decision["confirmation_request_required"] is False

    updated = apply(state, decision)

    validate_state(updated)

    assert (
        updated["session_state"]["task_state"]
        == "SAFE_FALLBACK"
    )
    assert (
        updated["execution_state"]["terminal_outcome"]
        == "SAFE_FALLBACK"
    )
    assert updated["execution_state"]["execution_status"] == (
        "NOT_STARTED"
    )
    assert updated["action_readiness"]["action_ready"] is False

def test_t016_records_answered_terminal_outcome() -> None:
    state = build_s01_state()

    proposal = {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-terminal-answer",
        "proposal_type": "PROVIDE_ANSWER",
        "rationale": (
            "The bounded diagnostic answer is sufficient."
        ),
        "payload": {
            "answer": (
                "Version 2.4.2 is associated with elevated "
                "5xx errors."
            ),
            "evidence_ids": [
                "ev-s01-version-error-old",
                "ev-s01-version-error-new",
            ],
            "freshness_note": (
                "The supporting evidence is fresh."
            ),
        },
    }

    decision = evaluate(state, proposal)

    assert decision["decision"] == "PROVIDE_ANSWER"
    assert decision["reason_codes"] == []
    assert decision["next_state"] == "COMPLETED"
    assert decision["tool_execution_allowed"] is False
    assert decision["confirmation_request_required"] is False

    updated = apply(state, decision)

    validate_state(updated)

    assert updated["session_state"]["task_state"] == "COMPLETED"
    assert (
        updated["execution_state"]["terminal_outcome"]
        == "ANSWERED"
    )

def test_t029_preserves_generic_completed_terminal_outcome(
) -> None:
    state = build_s01_state()
    state["session_state"]["task_state"] = "VERIFYING"
    state["session_state"]["phase"] = "EXECUTE"

    decision = {
        "schema_version": "0.1.0",
        "decision_id": "decision-t029-completed",
        "proposal_id": "proposal-t029-completed",
        "decision": "ALLOW",
        "reason_codes": [],
        "message": None,
        "gate_results": [],
        "next_state": "COMPLETED",
        "safer_path": None,
        "tool_execution_allowed": False,
        "confirmation_request_required": False,
        "decided_at": state["updated_at"],
    }

    updated = apply(state, decision)

    validate_state(updated)

    assert updated["session_state"]["task_state"] == "COMPLETED"
    assert (
        updated["execution_state"]["terminal_outcome"]
        == "COMPLETED"
    )

