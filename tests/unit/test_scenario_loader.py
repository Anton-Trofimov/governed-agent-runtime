from pathlib import Path

from governed_agent_runtime.scenario_loader import load_scenario_bundle

ROOT = Path(__file__).resolve().parents[2]


def test_load_s01_bundle() -> None:
    bundle = load_scenario_bundle(ROOT, "S01")

    assert bundle.scenario_id == "S01"
    assert bundle.user_request["known_context"]["service_id"] == "payment-api"
    assert len(bundle.source_payloads) == 6
    assert set(bundle.source_payloads) == set(
        bundle.scenario["tool_source_files"]
    )


def test_loader_does_not_load_hidden_evaluation() -> None:
    bundle = load_scenario_bundle(ROOT, "S01")

    serialized = repr(bundle)
    assert "hidden_root_cause" not in serialized
    assert "acceptable_paths" not in serialized
