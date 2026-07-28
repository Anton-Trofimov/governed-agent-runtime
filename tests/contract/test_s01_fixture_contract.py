import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = ROOT / "fixtures/scenarios/s01"
HIDDEN_EVAL = ROOT / "evals/hidden/exp-18-0/s01/hidden-evaluation.yaml"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_s01_source_mapping_and_visibility() -> None:
    scenario = load_yaml(SCENARIO_DIR / "scenario.yaml")
    contracts = load_yaml(ROOT / "specs/core/tool-contracts.yaml")

    read_only_tools = {
        tool["tool_name"]
        for tool in contracts["tools"]
        if tool["category"] == "read_only"
    }

    mapped_tools = set(scenario["tool_source_files"])
    assert mapped_tools <= read_only_tools

    assert HIDDEN_EVAL.exists()
    assert (ROOT / "fixtures").resolve() not in HIDDEN_EVAL.resolve().parents
    assert not list(SCENARIO_DIR.rglob("*hidden*"))


def test_s01_source_files_are_consistent() -> None:
    scenario = load_yaml(SCENARIO_DIR / "scenario.yaml")
    request = load_json(SCENARIO_DIR / scenario["user_request_file"])

    expected_service = request["known_context"]["service_id"]
    expected_environment = request["known_context"]["environment_id"]

    forbidden_keys = {
        "hidden_root_cause",
        "acceptable_paths",
        "expected_outcomes",
        "premature_or_prohibited_actions",
    }

    for relative_path in scenario["tool_source_files"].values():
        source_path = SCENARIO_DIR / relative_path
        source = load_json(source_path)

        assert source["service_id"] == expected_service
        assert source["environment_id"] == expected_environment
        assert source["source_id"]
        assert source["source_timestamp"]
        assert forbidden_keys.isdisjoint(source)


def test_s01_capacity_constraint() -> None:
    traffic = load_json(SCENARIO_DIR / "source/traffic.json")
    deployments = load_json(SCENARIO_DIR / "source/deployments.json")
    capacity = load_yaml(ROOT / "knowledge/capacity-profiles.yaml")

    safe_rps_per_replica = capacity["profiles"][0][
        "validated_safe_rps_per_replica"
    ]

    old_version_group = next(
        group
        for group in deployments["active_version_groups"]
        if group["version_id"] == "2.4.1"
    )

    safe_old_version_capacity = (
        old_version_group["replica_count"] * safe_rps_per_replica
    )

    assert traffic["total_request_rate_rps"] == 500
    assert safe_old_version_capacity == 420
    assert safe_old_version_capacity < traffic["total_request_rate_rps"]
