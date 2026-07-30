import json
from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from governed_agent_runtime.evidence_engine import (
    apply_evidence_assessment,
    evaluate_s01_evidence,
)
from governed_agent_runtime.execution_trace import (
    build_decision_application_trace,
)
from governed_agent_runtime.runtime_policy import evaluate_proposal
from governed_agent_runtime.scenario_loader import load_scenario_bundle
from governed_agent_runtime.scenario_runner import run_s01_preparation_path
from governed_agent_runtime.state_builder import (
    build_normalized_state,
    normalize_selected_sources,
)
from governed_agent_runtime.state_transition import (
    apply_runtime_decision_with_record,
)

ROOT = Path(__file__).resolve().parents[2]

TOOL_EXECUTION_EVENT_TYPES = {
    "TOOL_CALL_STARTED",
    "TOOL_RESULT_RECEIVED",
    "EXECUTION_STARTED",
    "EXECUTION_COMPLETED",
}


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_s01_state() -> dict:
    bundle = load_scenario_bundle(ROOT, "S01")
    adapter_contracts = load_yaml(
        ROOT / "specs/core/source-adapter-contracts.yaml"
    )
    observations = normalize_selected_sources(
        bundle,
        adapter_contracts,
    )

    state = build_normalized_state(
        bundle,
        observations,
        trace_id="trace-s01-decision-application",
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
        policy=load_yaml(
            ROOT / "specs/core/policy-spec.yaml"
        ),
        tool_contracts=load_yaml(
            ROOT / "specs/core/tool-contracts.yaml"
        ),
        proposal_schema=json.loads(
            (
                ROOT / "schemas/model-proposal.schema.json"
            ).read_text(encoding="utf-8")
        ),
        transition_spec=load_yaml(
            ROOT / "specs/core/state-transition-table.yaml"
        ),
    )


def apply_with_record(
    state: dict,
    decision: dict,
) -> tuple[dict, dict]:
    return apply_runtime_decision_with_record(
        state,
        decision,
        transition_spec=load_yaml(
            ROOT / "specs/core/state-transition-table.yaml"
        ),
    )


def validate_trace(trace: dict) -> None:
    schema = json.loads(
        (
            ROOT / "schemas/execution-trace.schema.json"
        ).read_text(encoding="utf-8")
    )

    Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    ).validate(trace)


def remediation_plan_proposal(state: dict) -> dict:
    return {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-remediation-plan-trace",
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
                    "action_type": "rollback_deployment",
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
                    "Current old-version capacity is insufficient.",
                ],
                "verification_steps": [
                    "Verify version-specific 5xx rate after traffic shift.",
                ],
                "stop_conditions": [
                    "Stop if capacity headroom is below minimum.",
                ],
            },
        },
    }


def rollback_proposal(state: dict) -> dict:
    return {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-premature-rollback-trace",
        "proposal_type": "CALL_TOOL",
        "rationale": (
            "Rollback the version associated with elevated errors."
        ),
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


def invalid_proposal() -> dict:
    return {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-invalid-trace",
        "proposal_type": "CALL_TOOL",
        "rationale": "Missing tool arguments.",
        "payload": {
            "tool_name": "get_service_metrics",
        },
    }


def assert_trace_event_order(
    trace: dict,
    decision: dict,
) -> None:
    event_types = [
        event["event_type"]
        for event in trace["events"]
    ]

    expected = (
        ["PROPOSAL_CREATED"]
        + ["GATE_EVALUATED"] * len(decision["gate_results"])
        + ["RUNTIME_DECISION", "STATE_UPDATED"]
    )

    assert event_types == expected
    assert [
        event["sequence"]
        for event in trace["events"]
    ] == list(range(1, len(trace["events"]) + 1))

    assert not TOOL_EXECUTION_EVENT_TYPES.intersection(event_types)


def test_t015_trace_records_validated_state_transition() -> None:
    state = build_s01_state()

    proposal = remediation_plan_proposal(state)
    decision = evaluate(state, proposal)

    state_original = deepcopy(state)
    proposal_original = deepcopy(proposal)
    decision_original = deepcopy(decision)

    updated, application_record = apply_with_record(
        state,
        decision,
    )

    updated_original = deepcopy(updated)

    trace = build_decision_application_trace(
        state,
        proposal,
        decision,
        updated,
        application_record=application_record,
    )

    validate_trace(trace)
    assert_trace_event_order(trace, decision)

    assert application_record == {
        "application_rule_type": "STATE_TRANSITION",
        "application_rule_id": "T015",
        "lifecycle_disposition": None,
    }

    state_event = trace["events"][-1]
    payload = state_event["payload"]

    assert payload["application_rule_type"] == "STATE_TRANSITION"
    assert payload["application_rule_id"] == "T015"
    assert payload["previous_task_state"] == "HYPOTHESIS_READY"
    assert payload["new_task_state"] == "PREPARING"
    assert payload["previous_phase"] == "DIAGNOSE"
    assert payload["new_phase"] == "PREPARE"
    assert payload["new_state_version"] == (
        payload["previous_state_version"] + 1
    )

    assert state == state_original
    assert proposal == proposal_original
    assert decision == decision_original
    assert updated == updated_original


def test_t033_trace_records_safer_preparation_transition() -> None:
    state = build_s01_state()
    state["session_state"]["phase"] = "EXECUTE"
    state["session_state"]["task_state"] = "ACTION_CANDIDATE"
    state["action_readiness"]["role_authorized"] = True

    proposal = rollback_proposal(state)
    decision = evaluate(state, proposal)

    updated, application_record = apply_with_record(
        state,
        decision,
    )

    trace = build_decision_application_trace(
        state,
        proposal,
        decision,
        updated,
        application_record=application_record,
    )

    validate_trace(trace)
    assert_trace_event_order(trace, decision)

    assert decision["decision"] == "REPLACE_WITH_SAFER_PATH"
    assert application_record == {
        "application_rule_type": "STATE_TRANSITION",
        "application_rule_id": "T033",
        "lifecycle_disposition": None,
    }

    payload = trace["events"][-1]["payload"]

    assert payload["previous_task_state"] == "ACTION_CANDIDATE"
    assert payload["new_task_state"] == "PREPARING"
    assert payload["previous_phase"] == "EXECUTE"
    assert payload["new_phase"] == "PREPARE"
    assert payload["action_ready_after"] is False


def test_da001_trace_records_recoverable_rejection() -> None:
    state = build_s01_state()
    proposal = invalid_proposal()
    decision = evaluate(state, proposal)

    updated, application_record = apply_with_record(
        state,
        decision,
    )

    trace = build_decision_application_trace(
        state,
        proposal,
        decision,
        updated,
        application_record=application_record,
    )

    validate_trace(trace)
    assert_trace_event_order(trace, decision)

    assert decision["decision"] == "BLOCK"
    assert decision["next_state"] == (
        state["session_state"]["task_state"]
    )
    assert application_record == {
        "application_rule_type": "DECISION_APPLICATION_RULE",
        "application_rule_id": "DA001",
        "lifecycle_disposition": (
            "RECOVERABLE_PROPOSAL_REJECTION"
        ),
    }

    payload = trace["events"][-1]["payload"]

    assert payload["previous_task_state"] == "HYPOTHESIS_READY"
    assert payload["new_task_state"] == "HYPOTHESIS_READY"
    assert payload["previous_phase"] == payload["new_phase"]
    assert payload["terminal_outcome_after"] is None

    runtime_event = trace["events"][-2]

    assert runtime_event["event_type"] == "RUNTIME_DECISION"
    assert runtime_event["payload"]["decision"] == "BLOCK"
    assert runtime_event["payload"]["next_state"] == (
        state["session_state"]["task_state"]
    )

def test_preparation_trace_retains_complete_tool_result_envelope(
) -> None:
    outcome = run_s01_preparation_path(ROOT)

    result_event = next(
        event
        for event in outcome["trace"]["events"]
        if event["event_type"] == "TOOL_RESULT_RECEIVED"
    )

    payload = result_event["payload"]
    executed_tool_result = outcome["tool_execution"]["tool_result"]

    assert "tool_result" in payload
    assert payload["tool_result"] == executed_tool_result
    assert payload["tool_result"] is not executed_tool_result

    assert payload["tool_result"]["schema_version"] == "0.1.0"
    assert "collected_at" in payload["tool_result"]
    assert "source_timestamp" in payload["tool_result"]

    for field in (
        "tool_call_id",
        "tool_name",
        "status",
        "raw_reference",
        "result",
        "errors",
    ):
        assert payload[field] == payload["tool_result"][field]

    validate_trace(outcome["trace"])

    recorded_tool_result = deepcopy(payload["tool_result"])

    outcome["tool_execution"]["tool_result"]["result"][
        "readiness_status"
    ] = "MUTATED_AFTER_TRACE"

    assert payload["tool_result"] == recorded_tool_result

