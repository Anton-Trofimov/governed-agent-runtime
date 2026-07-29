import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from governed_agent_runtime.scenario_runner import (
    run_s01_preparation_path,
)

ROOT = Path(__file__).resolve().parents[2]

OPERATIONAL_EXECUTION_EVENTS = {
    "EXECUTION_STARTED",
    "EXECUTION_COMPLETED",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate(instance: dict, schema_name: str) -> None:
    Draft202012Validator(
        load_json(ROOT / "schemas" / schema_name),
        format_checker=FormatChecker(),
    ).validate(instance)


def test_s01_creates_governed_remediation_plan() -> None:
    result = run_s01_preparation_path(ROOT)

    initial_state = result["initial_state"]
    prepared_state = result["state_after_decision"]
    final_state = result["final_state"]
    decision = result["decision"]
    tool_result = result["tool_execution"]["tool_result"]
    trace = result["trace"]

    validate(initial_state, "normalized-state.schema.json")
    validate(prepared_state, "normalized-state.schema.json")
    validate(final_state, "normalized-state.schema.json")
    validate(tool_result, "tool-result.schema.json")
    validate(trace, "execution-trace.schema.json")

    acceptance = load_yaml(
        ROOT
        / "specs/experiments/exp-18-0/acceptance-cases.yaml"
    )
    scenario = next(
        item
        for item in acceptance["scenarios"]
        if item["scenario_id"] == "S01"
    )

    assert result["scenario_id"] == "S01"
    assert result["governed_outcome"] == "DRAFT_CREATED"
    assert result["governed_outcome"] in scenario[
        "acceptable_outcomes"
    ]

    assert initial_state["session_state"]["task_state"] == (
        "HYPOTHESIS_READY"
    )
    assert initial_state["session_state"]["phase"] == "DIAGNOSE"

    assert decision["decision"] == "ALLOW"
    assert decision["next_state"] == "PREPARING"
    assert decision["tool_execution_allowed"] is True

    assert prepared_state["session_state"]["task_state"] == (
        "PREPARING"
    )
    assert prepared_state["session_state"]["phase"] == "PREPARE"

    assert tool_result["tool_name"] == "create_remediation_plan"
    assert tool_result["status"] == "SUCCEEDED"

    assert final_state["session_state"]["task_state"] == (
        "ACTION_CANDIDATE"
    )
    assert final_state["session_state"]["phase"] == "PREPARE"
    assert final_state["session_state"]["tool_call_count"] == (
        initial_state["session_state"]["tool_call_count"] + 1
    )

    candidate_action = final_state["action_readiness"][
        "candidate_action"
    ]
    plan_result = tool_result["result"]

    assert candidate_action["action_type"] == (
        "rollback_deployment"
    )
    assert candidate_action["remediation_plan_id"] == (
        plan_result["remediation_plan_id"]
    )
    assert candidate_action["remediation_plan_version"] == (
        plan_result["plan_version"]
    )

    assert final_state["action_readiness"]["action_ready"] is False
    assert final_state["execution_state"]["execution_status"] == (
        "NOT_STARTED"
    )
    assert final_state["execution_state"]["terminal_outcome"] is None
    assert trace["terminal_outcome"] is None

    event_types = [
        event["event_type"]
        for event in trace["events"]
    ]

    assert event_types.count("RUNTIME_DECISION") == 1
    assert event_types.count("TOOL_CALL_STARTED") == 1
    assert event_types.count("TOOL_RESULT_RECEIVED") == 1
    assert event_types.count("STATE_UPDATED") == 2
    assert not OPERATIONAL_EXECUTION_EVENTS.intersection(event_types)

    state_updates = [
        event["payload"]
        for event in trace["events"]
        if event["event_type"] == "STATE_UPDATED"
    ]

    assert [
        update["application_rule_id"]
        for update in state_updates
    ] == ["T015", "T019"]
