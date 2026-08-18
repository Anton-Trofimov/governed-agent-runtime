import importlib
import json
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

from governed_agent_runtime.contract_schema import normalize_contract_schema
from governed_agent_runtime.llm_probe_contracts import (
    validate_model_context_package,
    validate_proposal_context_consistency,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas"


class SpyModel:
    def __init__(self, raw_response: str) -> None:
        self.model_identity = "test-model-v1"
        self.invocation_parameters = {"temperature": 0, "seed": 18}
        self.raw_response = raw_response
        self.received_inputs: list[str] = []

    def __call__(self, serialized_input: str) -> str:
        self.received_inputs.append(serialized_input)
        return self.raw_response


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_schema(instance: dict, schema_name: str) -> None:
    format_checker = FormatChecker()
    if "date-time" not in format_checker.checkers:
        format_checker.checkers["date-time"] = (
            lambda value: datetime.fromisoformat(value),
            (TypeError, ValueError),
        )
    Draft202012Validator(
        load_json(SCHEMA_DIR / schema_name),
        format_checker=format_checker,
    ).validate(instance)


def smoke_module() -> ModuleType:
    module_name = "governed_agent_runtime.s01_llm_probe_smoke"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        pytest.fail(
            f"missing S01 LLM plumbing smoke boundary: {module_name}",
            pytrace=False,
        )


def raw_tool_proposal() -> str:
    return json.dumps(
        {
            "schema_version": "0.1.0",
            "proposal_id": "proposal-s01-smoke-001",
            "proposal_type": "CALL_TOOL",
            "rationale": "Refresh version-specific error metrics.",
            "created_at": "2026-07-28T12:00:00Z",
            "payload": {
                "tool_name": "get_service_metrics",
                "arguments": {
                    "service_id": "payment-api",
                    "environment_id": "production",
                    "metric_names": ["payment_api_http_5xx_rate"],
                    "start_time": "2026-07-28T11:40:00Z",
                    "end_time": "2026-07-28T12:00:00Z",
                    "group_by": ["version_id"],
                },
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def raw_schema_invalid_answer_proposal() -> str:
    return json.dumps(
        {
            "schema_version": "0.1.0",
            "proposal_id": "proposal-invalid-answer-001",
            "proposal_type": "PROVIDE_ANSWER",
            "rationale": "Provide the observed diagnosis and next step.",
            "payload": {
                "diagnosis": "The service is returning elevated errors.",
                "safest_next_step": "Collect version-specific metrics.",
                "evidence_gaps": [],
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def collect_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys |= collect_keys(item)
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys |= collect_keys(item)
        return keys
    return set()


def contains_value(value: object, expected: object) -> bool:
    if value == expected:
        return True
    if isinstance(value, dict):
        return any(contains_value(item, expected) for item in value.values())
    if isinstance(value, list):
        return any(contains_value(item, expected) for item in value)
    return False


def test_s01_smoke_builds_context_only_from_approved_inputs() -> None:
    smoke = smoke_module()

    context = smoke.build_s01_model_context(ROOT)

    validate_schema(context, "model-context-package.schema.json")
    validate_model_context_package(context)

    assert {"scenario_id", "hidden_facts", "expectations"}.isdisjoint(
        collect_keys(context)
    )
    assert "s01" not in json.dumps(context).casefold()

    tool_contracts = load_yaml(ROOT / "specs/core/tool-contracts.yaml")
    approved_tools = {
        tool["tool_name"]: tool for tool in tool_contracts["tools"]
    }
    assert context["available_tools"]
    for tool in context["available_tools"]:
        approved = approved_tools[tool["tool_name"]]
        assert tool == {
            "tool_name": approved["tool_name"],
            "category": approved["category"],
            "description": approved["purpose"],
            "input_schema": normalize_contract_schema(
                approved["input_schema"]
            ),
        }

    policy = load_yaml(ROOT / "specs/core/policy-spec.yaml")
    approved_constraint_ids = {
        rule["rule_id"] for rule in policy["policy_rules"]
    }
    assert context["applicable_constraints"]
    assert {
        constraint["constraint_id"]
        for constraint in context["applicable_constraints"]
    } <= approved_constraint_ids


def test_s01_smoke_captures_one_call_and_stops_after_runtime_evaluation() -> None:
    smoke = smoke_module()
    raw_response = raw_tool_proposal()
    model = SpyModel(raw_response)

    result = smoke.run_s01_llm_probe_smoke(ROOT, model=model)

    assert len(model.received_inputs) == 1
    assert result["serialized_model_input"] == model.received_inputs[0]
    assert contains_value(
        json.loads(result["serialized_model_input"]),
        result["context_package"],
    )
    assert "s01" not in json.dumps(result["context_package"]).casefold()
    assert "s01" not in result["serialized_model_input"].casefold()

    assert result["model_identity"] == model.model_identity
    assert result["invocation_parameters"] == model.invocation_parameters
    assert result["raw_model_response"] == raw_response
    assert result["proposal"] == json.loads(raw_response)

    validate_schema(result["context_package"], "model-context-package.schema.json")
    validate_model_context_package(result["context_package"])
    validate_schema(result["proposal"], "model-proposal.schema.json")
    validate_proposal_context_consistency(
        result["context_package"],
        result["proposal"],
    )
    validate_schema(result["runtime_decision"], "runtime-decision.schema.json")

    assert result["validation_results"] == {
        "context_schema": "PASSED",
        "context_semantics": "PASSED",
        "proposal_schema": "PASSED",
        "proposal_context_semantics": "PASSED",
    }
    assert "reason_codes" in result["runtime_decision"]

    assert result["runtime_state_before_evaluation"] == (
        result["runtime_state_after_evaluation"]
    )
    state = result["runtime_state_after_evaluation"]
    assert state["execution_state"]["execution_status"] == "NOT_STARTED"
    assert state["session_state"]["tool_call_count"] == (
        result["runtime_state_before_evaluation"]["session_state"][
            "tool_call_count"
        ]
    )
    assert not hasattr(smoke, "execute_preparation_tool")
    assert not hasattr(smoke, "apply_runtime_decision_with_record")

    assert result["purpose"] == "PLUMBING_SMOKE"
    assert result["included_in_evaluation_sample"] is False
    assert result["smoke_id"]
    assert result["started_at"]
    assert result["completed_at"]
    assert result["context_package"]["context_package_id"]
    assert result["runtime_decision"]["decision_id"]


def test_s01_smoke_contains_schema_invalid_model_proposal() -> None:
    smoke = smoke_module()
    raw_response = raw_schema_invalid_answer_proposal()
    model = SpyModel(raw_response)

    result = smoke.run_s01_llm_probe_smoke(ROOT, model=model)

    assert len(model.received_inputs) == 1
    assert result["raw_model_response"] == raw_response
    assert result["proposal"] == json.loads(raw_response)
    assert result["validation_results"] == {
        "context_schema": "PASSED",
        "context_semantics": "PASSED",
        "parse": "PASSED",
        "proposal_schema": "FAILED",
        "proposal_context_semantics": "SKIPPED",
    }

    decision = result["runtime_decision"]
    validate_schema(decision, "runtime-decision.schema.json")
    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == ["INVALID_PROPOSAL_SCHEMA"]
    assert decision["tool_execution_allowed"] is False

    assert result["runtime_state_before_evaluation"] == (
        result["runtime_state_after_evaluation"]
    )
    assert result["runtime_state_after_evaluation"]["execution_state"][
        "execution_status"
    ] == "NOT_STARTED"
    assert not hasattr(smoke, "execute_preparation_tool")
    assert not hasattr(smoke, "apply_runtime_decision_with_record")
