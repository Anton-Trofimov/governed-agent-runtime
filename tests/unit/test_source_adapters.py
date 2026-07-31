import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from governed_agent_runtime.scenario_loader import load_scenario_bundle
from governed_agent_runtime.source_adapters import (
    SourceAdapterError,
    normalize_source,
)

ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def test_s01_sources_normalize_to_expected_observations() -> None:
    bundle = load_scenario_bundle(ROOT, "S01")
    contracts = load_yaml(ROOT / "specs/core/source-adapter-contracts.yaml")
    expected = json.loads(
        (
            ROOT
            / "tests/fixtures/s01/expected-normalized-summary.json"
        ).read_text()
    )

    actual_counts = {}

    for tool_name, source in bundle.source_payloads.items():
        observations = normalize_source(
            tool_name,
            source,
            contracts,
            collected_at=bundle.scenario["reference_time"],
            raw_reference=f"fixture://s01/{tool_name}",
            expected_service_id="payment-api",
            expected_environment_id="production",
        )

        actual_counts[tool_name] = len(observations)

        for observation in observations:
            assert observation["source_id"] == source["source_id"]
            assert observation["raw_reference"]
            assert observation["scope"]["service_id"] == "payment-api"
            assert observation["scope"]["environment_id"] == "production"
            assert "root_cause" not in observation
            assert "action_ready" not in observation

    assert actual_counts == expected["expected_observation_counts"]
    assert sum(actual_counts.values()) == expected[
        "expected_total_observations"
    ]


def test_s01_version_metrics_remain_separate() -> None:
    bundle = load_scenario_bundle(ROOT, "S01")
    contracts = load_yaml(ROOT / "specs/core/source-adapter-contracts.yaml")

    observations = normalize_source(
        "get_service_metrics",
        bundle.source_payloads["get_service_metrics"],
        contracts,
        collected_at=bundle.scenario["reference_time"],
        raw_reference="fixture://s01/get_service_metrics",
        expected_service_id="payment-api",
        expected_environment_id="production",
    )

    error_series = [
        item
        for item in observations
        if item.get("metric_name") == "payment_api_http_5xx_rate"
    ]

    assert len(error_series) == 2
    assert {
        item["scope"]["version_id"]
        for item in error_series
    } == {"2.4.1", "2.4.2"}


def test_target_mismatch_is_rejected() -> None:
    bundle = load_scenario_bundle(ROOT, "S01")
    contracts = load_yaml(ROOT / "specs/core/source-adapter-contracts.yaml")

    with pytest.raises(SourceAdapterError) as error:
        normalize_source(
            "get_service_status",
            bundle.source_payloads["get_service_status"],
            contracts,
            collected_at=bundle.scenario["reference_time"],
            raw_reference="fixture://s01/get_service_status",
            expected_service_id="other-service",
            expected_environment_id="production",
        )

    assert error.value.code == "SOURCE_TARGET_MISMATCH"

@pytest.mark.parametrize(
    (
        "tool_name",
        "timestamp_path",
        "invalid_value",
    ),
    [
        (
            "get_service_status",
            ("source_timestamp",),
            "not-a-timestamp",
        ),
        (
            "get_recent_deployments",
            ("deployments", 0, "started_at"),
            "2026-07-28T11:40:00",
        ),
        (
            "get_recent_runtime_events",
            ("events", 0, "occurred_at"),
            "not-a-timestamp",
        ),
        (
            "get_service_metrics",
            (
                "metric_series",
                0,
                "points",
                0,
                "timestamp",
            ),
            "not-a-timestamp",
        ),
    ],
)
def test_invalid_timestamps_used_by_normalized_observations_are_rejected(
    tool_name: str,
    timestamp_path: tuple[str | int, ...],
    invalid_value: str,
) -> None:
    bundle = load_scenario_bundle(ROOT, "S01")
    contracts = load_yaml(
        ROOT / "specs/core/source-adapter-contracts.yaml"
    )

    source = deepcopy(bundle.source_payloads[tool_name])
    current = source

    for key in timestamp_path[:-1]:
        current = current[key]

    current[timestamp_path[-1]] = invalid_value

    with pytest.raises(SourceAdapterError) as error:
        normalize_source(
            tool_name,
            source,
            contracts,
            collected_at=bundle.scenario["reference_time"],
            raw_reference=f"fixture://s01/{tool_name}",
            expected_service_id="payment-api",
            expected_environment_id="production",
        )

    assert error.value.code == "INVALID_SOURCE_TIMESTAMP"


def test_invalid_runtime_collection_timestamp_is_rejected(
) -> None:
    bundle = load_scenario_bundle(ROOT, "S01")
    contracts = load_yaml(
        ROOT / "specs/core/source-adapter-contracts.yaml"
    )

    with pytest.raises(SourceAdapterError) as error:
        normalize_source(
            "get_service_status",
            bundle.source_payloads["get_service_status"],
            contracts,
            collected_at="2026-07-28T12:00:00",
            raw_reference="fixture://s01/get_service_status",
            expected_service_id="payment-api",
            expected_environment_id="production",
        )

    assert error.value.code == "INVALID_SOURCE_TIMESTAMP"

def test_timezone_offsets_are_preserved_during_normalization(
) -> None:
    bundle = load_scenario_bundle(ROOT, "S01")
    contracts = load_yaml(
        ROOT / "specs/core/source-adapter-contracts.yaml"
    )

    source = deepcopy(
        bundle.source_payloads["get_service_status"]
    )
    source_timestamp = "2026-07-28T15:00:00+03:00"
    collected_at = "2026-07-28T15:00:05+03:00"

    source["source_timestamp"] = source_timestamp

    observations = normalize_source(
        "get_service_status",
        source,
        contracts,
        collected_at=collected_at,
        raw_reference="fixture://s01/get_service_status",
        expected_service_id="payment-api",
        expected_environment_id="production",
    )

    assert {
        observation["observed_at"]
        for observation in observations
    } == {source_timestamp}

    assert {
        observation["collected_at"]
        for observation in observations
    } == {collected_at}

