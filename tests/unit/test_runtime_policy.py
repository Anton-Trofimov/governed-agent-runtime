import json
from copy import deepcopy
from pathlib import Path

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
        trace_id="trace-s01-policy",
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


def evaluate(
    state: dict,
    proposal: dict,
    *,
    policy_override: dict | None = None,
) -> dict:
    policy = (
        policy_override
        if policy_override is not None
        else load_yaml(ROOT / "specs/core/policy-spec.yaml")
    )

    return evaluate_proposal(
        state,
        proposal,
        policy=policy,
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


def validate_decision(decision: dict) -> None:
    schema = json.loads(
        (ROOT / "schemas/runtime-decision.schema.json").read_text()
    )

    Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    ).validate(decision)


def test_premature_rollback_is_replaced_with_safer_path() -> None:
    state = build_s01_state()
    state["session_state"]["phase"] = "EXECUTE"
    state["session_state"]["task_state"] = "ACTION_CANDIDATE"
    state["action_readiness"]["role_authorized"] = True

    proposal = {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-premature-rollback",
        "proposal_type": "CALL_TOOL",
        "rationale": "Rollback the version associated with elevated errors.",
        "created_at": state["updated_at"],
        "payload": {
            "tool_name": "rollback_deployment",
            "arguments": {
                "service_id": "payment-api",
                "environment_id": "production",
                "deployment_target_id": "payment-api-prod-eu-central-1",
                "deployment_id": "deployment-payment-api-20260728-1140",
                "target_version_id": "2.4.1",
                "remediation_plan_id": "plan-s01-001",
                "remediation_plan_version": "1",
            },
        },
    }

    decision = evaluate(state, proposal)
    validate_decision(decision)

    assert decision["decision"] == "REPLACE_WITH_SAFER_PATH"
    assert "EVIDENCE_INSUFFICIENT" in decision["reason_codes"]
    assert decision["tool_execution_allowed"] is False
    assert decision["next_state"] == "PREPARING"
    assert (
        decision["safer_path"]["tool_name"]
        == "create_remediation_plan"
    )

    failed_gate = next(
        item
        for item in decision["gate_results"]
        if item["status"] == "FAILED"
    )

    assert failed_gate["gate_id"] == "G05_EVIDENCE_SUFFICIENCY"


def remediation_plan_proposal(state: dict) -> dict:
    return {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-remediation-plan",
        "proposal_type": "CREATE_DRAFT",
        "rationale": (
            "Record the supported regression and unresolved rollback checks."
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
                    "Version 2.4.2 has elevated 5xx errors while "
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
                    "Stop if projected capacity headroom is below minimum."
                ],
            },
        },
    }


def test_remediation_plan_is_allowed_through_ph001() -> None:
    state = build_s01_state()
    proposal = remediation_plan_proposal(state)

    assert state["session_state"]["task_state"] == "HYPOTHESIS_READY"
    assert state["session_state"]["phase"] == "DIAGNOSE"

    decision = evaluate(state, proposal)
    validate_decision(decision)

    assert decision["decision"] == "ALLOW"
    assert decision["next_state"] == "PREPARING"
    assert decision["tool_execution_allowed"] is True
    assert decision["reason_codes"] == []

    # Policy evaluation must not mutate phase before T015 is applied.
    assert state["session_state"]["phase"] == "DIAGNOSE"


def test_ph001_requires_hypothesis_ready_task_state() -> None:
    state = build_s01_state()
    state["session_state"]["task_state"] = "DIAGNOSING"

    decision = evaluate(
        state,
        remediation_plan_proposal(state),
    )
    validate_decision(decision)

    assert decision["decision"] == "REPLACE_WITH_SAFER_PATH"
    assert "TOOL_NOT_ALLOWED_IN_PHASE" in decision["reason_codes"]
    assert decision["tool_execution_allowed"] is False

    failed_gate = next(
        item
        for item in decision["gate_results"]
        if item["status"] == "FAILED"
    )

    assert failed_gate["gate_id"] == "G03_PHASE_PERMISSION"


def test_ph001_requires_create_draft_proposal() -> None:
    state = build_s01_state()
    proposal = remediation_plan_proposal(state)
    proposal["proposal_type"] = "CALL_TOOL"

    decision = evaluate(state, proposal)
    validate_decision(decision)

    assert decision["decision"] == "REPLACE_WITH_SAFER_PATH"
    assert "TOOL_NOT_ALLOWED_IN_PHASE" in decision["reason_codes"]
    assert decision["tool_execution_allowed"] is False


def test_invalid_proposal_is_blocked_at_schema_gate() -> None:
    state = build_s01_state()
    invalid_proposal = {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-invalid",
        "proposal_type": "CALL_TOOL",
        "rationale": "Missing tool arguments.",
        "payload": {
            "tool_name": "get_service_metrics"
        },
    }

    decision = evaluate(state, invalid_proposal)
    validate_decision(decision)

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == ["INVALID_PROPOSAL_SCHEMA"]
    assert (
        decision["next_state"]
        == state["session_state"]["task_state"]
    )
    assert decision["tool_execution_allowed"] is False
    assert decision["gate_results"][0]["gate_id"] == "G01_SCHEMA_VALIDITY"
    assert decision["gate_results"][0]["status"] == "FAILED"


def test_policy_evaluation_does_not_mutate_state() -> None:
    state = build_s01_state()
    original = deepcopy(state)

    proposal = {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-answer",
        "proposal_type": "PROVIDE_ANSWER",
        "rationale": "Provide a bounded diagnostic summary.",
        "payload": {
            "answer": "Version 2.4.2 is associated with elevated errors.",
            "evidence_ids": [
                "ev-s01-version-error-old",
                "ev-s01-version-error-new",
            ],
            "freshness_note": "Evidence is fresh at reference time.",
        },
    }

    evaluate(state, proposal)

    assert state == original


def test_other_block_decision_keeps_blocked_next_state() -> None:
    state = build_s01_state()
    state["session_state"]["phase"] = "EXECUTE"
    state["session_state"]["task_state"] = "ACTION_CANDIDATE"

    proposal = {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-unauthorized-rollback",
        "proposal_type": "CALL_TOOL",
        "rationale": "Attempt rollback without an authorized role.",
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

    decision = evaluate(state, proposal)
    validate_decision(decision)

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == ["ROLE_NOT_AUTHORIZED"]
    assert decision["next_state"] == "BLOCKED"
    assert decision["tool_execution_allowed"] is False

def test_unexpected_preparation_tool_argument_is_blocked_at_schema_gate() -> None:
    state = build_s01_state()
    proposal = remediation_plan_proposal(state)
    proposal["payload"]["arguments"]["unexpected_argument"] = (
        "must-not-pass-policy-admission"
    )

    decision = evaluate(state, proposal)
    validate_decision(decision)

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == ["INVALID_PROPOSAL_SCHEMA"]
    assert (
        decision["next_state"]
        == state["session_state"]["task_state"]
    )
    assert decision["tool_execution_allowed"] is False

    schema_gate = decision["gate_results"][0]
    assert schema_gate["gate_id"] == "G01_SCHEMA_VALIDITY"
    assert schema_gate["status"] == "FAILED"
    assert schema_gate["reason_code"] == "INVALID_PROPOSAL_SCHEMA"

def assert_invalid_candidate_action_is_blocked(
    state: dict,
    proposal: dict,
) -> None:
    decision = evaluate(state, proposal)
    validate_decision(decision)

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == ["INVALID_PROPOSAL_SCHEMA"]
    assert (
        decision["next_state"]
        == state["session_state"]["task_state"]
    )
    assert decision["tool_execution_allowed"] is False

    schema_gate = decision["gate_results"][0]
    assert schema_gate["gate_id"] == "G01_SCHEMA_VALIDITY"
    assert schema_gate["status"] == "FAILED"
    assert schema_gate["reason_code"] == "INVALID_PROPOSAL_SCHEMA"


def test_unsupported_candidate_action_type_is_blocked_at_schema_gate() -> None:
    state = build_s01_state()
    proposal = remediation_plan_proposal(state)
    proposal["payload"]["arguments"]["candidate_action"] = {
        "action_type": "unsupported_operational_action"
    }

    assert_invalid_candidate_action_is_blocked(state, proposal)


def test_unknown_candidate_action_field_is_blocked_at_schema_gate() -> None:
    state = build_s01_state()
    proposal = remediation_plan_proposal(state)
    proposal["payload"]["arguments"]["candidate_action"][
        "model_selected_priority"
    ] = "CRITICAL"

    assert_invalid_candidate_action_is_blocked(state, proposal)


def test_runtime_owned_plan_reference_is_blocked_at_schema_gate() -> None:
    state = build_s01_state()
    proposal = remediation_plan_proposal(state)
    candidate_action = proposal["payload"]["arguments"]["candidate_action"]
    candidate_action["remediation_plan_id"] = "model-supplied-plan"
    candidate_action["remediation_plan_version"] = "999"

    assert_invalid_candidate_action_is_blocked(state, proposal)

def assert_invalid_ph001_transition_is_rejected(
    transition_id: str,
) -> None:
    state = build_s01_state()
    proposal = remediation_plan_proposal(state)
    policy = load_yaml(ROOT / "specs/core/policy-spec.yaml")

    rule = next(
        item
        for item in policy["transition_aware_phase_rules"]
        if item["rule_id"] == "PH001"
    )
    rule["transition_id"] = transition_id

    decision = evaluate(
        state,
        proposal,
        policy_override=policy,
    )
    validate_decision(decision)

    assert decision["decision"] == "REPLACE_WITH_SAFER_PATH"
    assert "TOOL_NOT_ALLOWED_IN_PHASE" in decision[
        "reason_codes"
    ]
    assert "SAFER_PATH_AVAILABLE" in decision[
        "reason_codes"
    ]
    assert decision["next_state"] == "DIAGNOSING"
    assert decision["safer_path"]["proposal_type"] == "CALL_TOOL"
    assert decision["tool_execution_allowed"] is False

    failed_gate = next(
        item
        for item in decision["gate_results"]
        if item["status"] == "FAILED"
    )

    assert failed_gate["gate_id"] == "G03_PHASE_PERMISSION"


def test_ph001_rejects_unknown_transition_reference() -> None:
    assert_invalid_ph001_transition_is_rejected("T999")


def test_ph001_rejects_transition_for_different_source_state() -> None:
    assert_invalid_ph001_transition_is_rejected("T033")
