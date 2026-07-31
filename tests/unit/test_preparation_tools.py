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
from governed_agent_runtime.execution_trace import (
    append_preparation_tool_execution,
    build_decision_application_trace,
)
from governed_agent_runtime.preparation_tools import (
    apply_preparation_tool_result,
    execute_preparation_tool,
)
from governed_agent_runtime.runtime_policy import evaluate_proposal
from governed_agent_runtime.scenario_loader import load_scenario_bundle
from governed_agent_runtime.state_builder import (
    build_normalized_state,
    normalize_selected_sources,
)
from governed_agent_runtime.state_transition import (
    apply_runtime_decision_with_record,
)

ROOT = Path(__file__).resolve().parents[2]

OPERATIONAL_EXECUTION_EVENTS = {
    "EXECUTION_STARTED",
    "EXECUTION_COMPLETED",
}


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
        trace_id="trace-s01-preparation-tool",
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

    updated = apply_evidence_assessment(state, assessment)

    return updated


def remediation_plan_proposal(state: dict) -> dict:
    return {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-preparation-tool",
        "proposal_type": "CREATE_DRAFT",
        "rationale": (
            "Create a controlled remediation plan before rollback."
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
        proposal_schema=load_json(
            ROOT / "schemas/model-proposal.schema.json"
        ),
        transition_spec=load_yaml(
            ROOT / "specs/core/state-transition-table.yaml"
        ),
    )


def prepare_allowed_tool_call() -> tuple[dict, dict, dict, dict]:
    state_before_decision = build_s01_state()
    proposal = remediation_plan_proposal(state_before_decision)
    decision = evaluate(state_before_decision, proposal)

    prepared_state, application_record = (
        apply_runtime_decision_with_record(
            state_before_decision,
            decision,
            transition_spec=load_yaml(
                ROOT / "specs/core/state-transition-table.yaml"
            ),
        )
    )

    trace = build_decision_application_trace(
        state_before_decision,
        proposal,
        decision,
        prepared_state,
        application_record=application_record,
    )

    assert prepared_state["session_state"]["task_state"] == "PREPARING"
    assert prepared_state["session_state"]["phase"] == "PREPARE"
    assert decision["decision"] == "ALLOW"
    assert decision["tool_execution_allowed"] is True

    return prepared_state, proposal, decision, trace


def execute(
    state: dict,
    proposal: dict,
    decision: dict,
) -> dict:
    return execute_preparation_tool(
        state,
        proposal,
        decision,
        tool_contracts=load_yaml(
            ROOT / "specs/core/tool-contracts.yaml"
        ),
        tool_result_schema=load_json(
            ROOT / "schemas/tool-result.schema.json"
        ),
    )


def apply_result(
    state: dict,
    proposal: dict,
    execution: dict,
) -> tuple[dict, dict]:
    return apply_preparation_tool_result(
        state,
        proposal,
        execution,
        tool_result_schema=load_json(
            ROOT / "schemas/tool-result.schema.json"
        ),
        transition_spec=load_yaml(
            ROOT / "specs/core/state-transition-table.yaml"
        ),
    )


def validate_tool_result(tool_result: dict) -> None:
    Draft202012Validator(
        load_json(ROOT / "schemas/tool-result.schema.json"),
        format_checker=FormatChecker(),
    ).validate(tool_result)


def validate_trace(trace: dict) -> None:
    Draft202012Validator(
        load_json(ROOT / "schemas/execution-trace.schema.json"),
        format_checker=FormatChecker(),
    ).validate(trace)


def test_create_remediation_plan_updates_state_and_trace() -> None:
    state, proposal, decision, trace = prepare_allowed_tool_call()

    state_original = deepcopy(state)
    proposal_original = deepcopy(proposal)
    decision_original = deepcopy(decision)
    trace_original = deepcopy(trace)
    execution_state_original = deepcopy(state["execution_state"])

    execution = execute(state, proposal, decision)
    tool_result = execution["tool_result"]

    validate_tool_result(tool_result)

    updated, application_record = apply_result(
        state,
        proposal,
        execution,
    )

    updated_trace = append_preparation_tool_execution(
        trace,
        state,
        proposal,
        decision,
        execution,
        updated,
        application_record=application_record,
    )

    validate_trace(updated_trace)

    result = tool_result["result"]

    assert tool_result["tool_name"] == "create_remediation_plan"
    assert tool_result["status"] == "SUCCEEDED"
    assert result["plan_version"] == "1"
    assert result["readiness_status"] == "PRECONDITIONS_PENDING"
    assert result["missing_preconditions"] == [
        "ROLLBACK_DATABASE_COMPATIBLE",
        "ROLLBACK_TRANSITIONAL_CAPACITY_SUFFICIENT",
    ]

    assert application_record == {
        "application_rule_type": "STATE_TRANSITION",
        "application_rule_id": "T019",
        "lifecycle_disposition": None,
    }

    assert updated["state_version"] == state["state_version"] + 1
    assert updated["session_state"]["task_state"] == "ACTION_CANDIDATE"
    assert updated["session_state"]["phase"] == "PREPARE"
    assert updated["session_state"]["tool_call_count"] == (
        state["session_state"]["tool_call_count"] + 1
    )

    candidate_action = updated["action_readiness"]["candidate_action"]

    assert candidate_action["action_type"] == "rollback_deployment"
    assert candidate_action["remediation_plan_id"] == (
        result["remediation_plan_id"]
    )
    assert candidate_action["remediation_plan_version"] == "1"

    assert updated["action_readiness"]["action_ready"] is False
    assert updated["execution_state"] == execution_state_original
    assert updated["execution_state"]["terminal_outcome"] is None

    new_event_types = [
        event["event_type"]
        for event in updated_trace["events"][len(trace["events"]):]
    ]

    assert new_event_types == [
        "TOOL_CALL_STARTED",
        "TOOL_RESULT_RECEIVED",
        "STATE_UPDATED",
    ]

    all_event_types = {
        event["event_type"]
        for event in updated_trace["events"]
    }

    assert not OPERATIONAL_EXECUTION_EVENTS.intersection(
        all_event_types
    )

    assert state == state_original
    assert proposal == proposal_original
    assert decision == decision_original
    assert trace == trace_original


def test_same_inputs_produce_stable_tool_and_plan_ids() -> None:
    state, proposal, decision, _ = prepare_allowed_tool_call()

    first = execute(state, proposal, decision)
    second = execute(state, proposal, decision)

    assert first["arguments_hash"] == second["arguments_hash"]
    assert first["idempotency_key"] == second["idempotency_key"]
    assert (
        first["tool_result"]["tool_call_id"]
        == second["tool_result"]["tool_call_id"]
    )
    assert (
        first["tool_result"]["result"]["remediation_plan_id"]
        == second["tool_result"]["result"]["remediation_plan_id"]
    )


@pytest.mark.parametrize(
    ("mutation", "expected_message"),
    [
        ("decision", "ALLOW"),
        ("permission", "tool execution"),
        ("phase", "PREPARE"),
    ],
)
def test_preparation_tool_rejects_invalid_runtime_context(
    mutation: str,
    expected_message: str,
) -> None:
    state, proposal, decision, _ = prepare_allowed_tool_call()

    state = deepcopy(state)
    decision = deepcopy(decision)

    if mutation == "decision":
        decision["decision"] = "BLOCK"
    elif mutation == "permission":
        decision["tool_execution_allowed"] = False
    elif mutation == "phase":
        state["session_state"]["phase"] = "DIAGNOSE"
    else:
        raise AssertionError(f"Unknown mutation: {mutation}")

    with pytest.raises(ValueError, match=expected_message):
        execute(state, proposal, decision)


def test_preparation_tool_rejects_invalid_arguments() -> None:
    state, proposal, decision, _ = prepare_allowed_tool_call()
    invalid_proposal = deepcopy(proposal)

    del invalid_proposal["payload"]["arguments"]["stop_conditions"]

    with pytest.raises(ValueError, match="arguments"):
        execute(state, invalid_proposal, decision)

def test_application_rejects_schema_invalid_tool_result_envelope(
) -> None:
    state, proposal, decision, _ = prepare_allowed_tool_call()
    execution = execute(state, proposal, decision)

    execution["tool_result"].pop("schema_version")

    state_before = deepcopy(state)

    with pytest.raises(
        ValueError,
        match="schema|validation|envelope",
    ):
        apply_result(
            state,
            proposal,
            execution,
        )

    assert state == state_before

