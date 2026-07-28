import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from governed_agent_runtime.scenario_loader import load_scenario_bundle
from governed_agent_runtime.state_builder import (
    build_normalized_state,
    normalize_selected_sources,
)

ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def test_build_full_s01_normalized_state() -> None:
    bundle = load_scenario_bundle(ROOT, "S01")
    contracts = load_yaml(
        ROOT / "specs/core/source-adapter-contracts.yaml"
    )

    observations = normalize_selected_sources(bundle, contracts)

    state = build_normalized_state(
        bundle,
        observations,
        trace_id="trace-s01-full-state",
        tool_call_count=6,
        tool_call_budget=6,
    )

    schema = json.loads(
        (ROOT / "schemas/normalized-state.schema.json").read_text()
    )

    Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    ).validate(state)

    assert len(state["observed_state"]["observations"]) == 30
    assert state["session_state"]["resolved_service_id"] == "payment-api"
    assert state["session_state"]["resolved_environment_id"] == "production"
    assert (
        state["session_state"]["resolved_scope"]["deployment_target_id"]
        == "payment-api-prod-eu-central-1"
    )
    assert state["evidence_state"]["evidence_items"] == []
    assert state["diagnostic_assessment"]["hypotheses"] == []
    assert state["action_readiness"]["action_ready"] is False

    json.dumps(state)


def test_selected_sources_do_not_expose_hidden_truth() -> None:
    bundle = load_scenario_bundle(ROOT, "S01")
    contracts = load_yaml(
        ROOT / "specs/core/source-adapter-contracts.yaml"
    )

    observations = normalize_selected_sources(
        bundle,
        contracts,
        tool_names=[
            "get_service_metrics",
            "get_recent_deployments",
            "get_dependency_status",
        ],
    )

    state = build_normalized_state(
        bundle,
        observations,
        trace_id="trace-s01-selected-state",
        tool_call_count=3,
        tool_call_budget=3,
    )

    serialized = json.dumps(state)

    assert "hidden_root_cause" not in serialized
    assert "acceptable_paths" not in serialized
    assert "expected_initial_runtime_behavior" not in serialized


def test_reference_time_is_a_string() -> None:
    bundle = load_scenario_bundle(ROOT, "S01")

    assert isinstance(bundle.scenario["reference_time"], str)
    assert bundle.scenario["reference_time"].endswith("Z")
