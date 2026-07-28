import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from governed_agent_runtime.evidence_engine import (
    apply_evidence_assessment,
    evaluate_s01_evidence,
)
from governed_agent_runtime.scenario_loader import load_scenario_bundle
from governed_agent_runtime.state_builder import (
    build_normalized_state,
    normalize_selected_sources,
)

ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def build_s01_inputs() -> tuple:
    bundle = load_scenario_bundle(ROOT, "S01")
    contracts = load_yaml(
        ROOT / "specs/core/source-adapter-contracts.yaml"
    )
    observations = normalize_selected_sources(bundle, contracts)
    capacity_profile = load_yaml(
        ROOT / "knowledge/capacity-profiles.yaml"
    )["profiles"][0]

    return bundle, observations, capacity_profile


def test_s01_evidence_assessment() -> None:
    bundle, observations, capacity_profile = build_s01_inputs()

    assessment = evaluate_s01_evidence(
        observations,
        capacity_profile,
        reference_time=bundle.scenario["reference_time"],
    )

    claim_statuses = {
        claim["claim_id"]: claim["status"]
        for claim in assessment["claims"]
    }

    assert claim_statuses["claim-s01-version-regression"] == "SUPPORTED"
    assert claim_statuses["claim-s01-dependencies-healthy"] == "SUPPORTED"
    assert (
        claim_statuses["claim-s01-rollback-capacity-insufficient"]
        == "SUPPORTED"
    )
    assert (
        claim_statuses["claim-s01-db-compatibility-unknown"]
        == "SUPPORTED"
    )

    assert assessment["evidence_sufficiency"] == "PARTIAL"
    assert assessment["freshness_status"] == "FRESH"

    assert (
        "ROLLBACK_DATABASE_COMPATIBILITY"
        in assessment["mandatory_checks_missing"]
    )
    assert (
        "ROLLBACK_TRANSITIONAL_CAPACITY"
        in assessment["mandatory_checks_missing"]
    )

    assert len(assessment["contradictions"]) == 1
    assert (
        assessment["hypotheses"][0]["hypothesis_source"]
        == "DETERMINISTIC_RULE"
    )
    assert assessment["hypotheses"][0]["cause_status"] == "SUPPORTED"

    assert (
        assessment["recommended_next_step"]["tool_name"]
        == "create_remediation_plan"
    )


def test_s01_assessment_updates_valid_normalized_state() -> None:
    bundle, observations, capacity_profile = build_s01_inputs()

    state = build_normalized_state(
        bundle,
        observations,
        trace_id="trace-s01-evidence",
        tool_call_count=6,
        tool_call_budget=6,
    )

    assessment = evaluate_s01_evidence(
        observations,
        capacity_profile,
        reference_time=bundle.scenario["reference_time"],
    )

    updated = apply_evidence_assessment(state, assessment)

    schema = json.loads(
        (ROOT / "schemas/normalized-state.schema.json").read_text()
    )

    Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    ).validate(updated)

    assert updated["state_version"] == 2
    assert updated["session_state"]["task_state"] == "HYPOTHESIS_READY"
    assert updated["action_readiness"]["action_ready"] is False
    assert (
        updated["action_readiness"]["evidence_gate_passed"]
        is False
    )
    assert updated["action_readiness"]["blocking_reason_codes"] == [
        "EVIDENCE_INSUFFICIENT"
    ]

    serialized = json.dumps(updated)

    assert "hidden_root_cause" not in serialized
    assert "acceptable_paths" not in serialized


def test_missing_version_metrics_produces_insufficient_evidence() -> None:
    bundle = load_scenario_bundle(ROOT, "S01")
    contracts = load_yaml(
        ROOT / "specs/core/source-adapter-contracts.yaml"
    )

    observations = normalize_selected_sources(
        bundle,
        contracts,
        tool_names=[
            "get_service_status",
            "get_recent_deployments",
            "get_dependency_status",
            "get_traffic_breakdown",
        ],
    )

    capacity_profile = load_yaml(
        ROOT / "knowledge/capacity-profiles.yaml"
    )["profiles"][0]

    assessment = evaluate_s01_evidence(
        observations,
        capacity_profile,
        reference_time=bundle.scenario["reference_time"],
    )

    assert assessment["evidence_sufficiency"] == "INSUFFICIENT"
    assert (
        "VERSION_SPECIFIC_ERROR_METRICS"
        in assessment["mandatory_checks_missing"]
    )
