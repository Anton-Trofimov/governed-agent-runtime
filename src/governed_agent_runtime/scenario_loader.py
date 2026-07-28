"""Load deterministic scenario fixtures without hidden evaluation data."""

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ScenarioBundle:
    scenario_id: str
    scenario_dir: Path
    scenario: dict[str, Any]
    user_request: dict[str, Any]
    source_payloads: dict[str, dict[str, Any]]
    source_paths: dict[str, Path]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text())
    return _normalize_yaml_values(loaded)


def _normalize_yaml_values(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _normalize_yaml_values(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_normalize_yaml_values(item) for item in value]

    return value


def load_scenario_bundle(project_root: Path, scenario_id: str) -> ScenarioBundle:
    scenario_dir = (
        project_root / "fixtures" / "scenarios" / scenario_id.lower()
    ).resolve()

    scenario_path = scenario_dir / "scenario.yaml"

    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario not found: {scenario_id}")

    scenario = _load_yaml(scenario_path)

    if scenario["scenario_id"] != scenario_id.upper():
        raise ValueError(
            f"Scenario ID mismatch: expected {scenario_id.upper()}, "
            f"got {scenario['scenario_id']}"
        )

    request_path = (scenario_dir / scenario["user_request_file"]).resolve()
    _ensure_inside_scenario(request_path, scenario_dir)

    source_payloads: dict[str, dict[str, Any]] = {}
    source_paths: dict[str, Path] = {}

    for tool_name, relative_path in scenario["tool_source_files"].items():
        source_path = (scenario_dir / relative_path).resolve()
        _ensure_inside_scenario(source_path, scenario_dir)

        source_payloads[tool_name] = _load_json(source_path)
        source_paths[tool_name] = source_path

    return ScenarioBundle(
        scenario_id=scenario["scenario_id"],
        scenario_dir=scenario_dir,
        scenario=scenario,
        user_request=_load_json(request_path),
        source_payloads=source_payloads,
        source_paths=source_paths,
    )


def _ensure_inside_scenario(path: Path, scenario_dir: Path) -> None:
    if path != scenario_dir and scenario_dir not in path.parents:
        raise ValueError(f"Fixture path escapes scenario directory: {path}")
