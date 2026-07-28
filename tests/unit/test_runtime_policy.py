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


def test_remediation_plan_is_allowed_with_partial_evidence() -> None:
    state = build_s01_state()
    state["session_state"]["phase"] = "PREPARE"

    proposal = {
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

    decision = evaluate(state, proposal)
    validate_decision(decision)

    assert decision["decision"] == "ALLOW"
    assert decision["next_state"] == "PREPARING"
    assert decision["tool_execution_allowed"] is True
    assert decision["reason_codes"] == []


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
