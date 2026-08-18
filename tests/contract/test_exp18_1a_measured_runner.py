import importlib
import json
from copy import deepcopy
from pathlib import Path
from types import ModuleType

import pytest

from governed_agent_runtime.exp18_1a_context_assembly import (
    assemble_llm_probe_input,
    load_exp18_1a_context,
)

ROOT = Path(__file__).resolve().parents[2]
CASES = ("s02", "s07", "s08a", "s08b", "s12")
CANONICAL_PARAMETERS = {
    "temperature": 0,
    "seed": 18,
    "num_ctx": 8192,
    "num_predict": 2048,
    "think": False,
    "stream": False,
    "keep_alive": "10m",
}
HIDDEN_KEYS = {"scenario_id", "hidden_facts", "expectations"}


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


def valid_raw_proposal(call_index: int) -> str:
    return json.dumps(
        {
            "schema_version": "0.1.0",
            "proposal_id": f"proposal-measured-{call_index:03d}",
            "proposal_type": "STOP_OR_ESCALATE",
            "rationale": "Return one bounded safe result without execution.",
            "payload": {
                "outcome": "SAFE_FALLBACK",
                "summary": "Stop after the bounded single-step evaluation.",
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def invalid_raw_proposal() -> str:
    return json.dumps(
        {
            "schema_version": "0.1.0",
            "proposal_id": "proposal-schema-invalid",
            "proposal_type": "PROVIDE_ANSWER",
            "rationale": "Return a malformed answer payload.",
            "payload": {"invented_field": "not allowed"},
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class ScriptedModel:
    def __init__(
        self,
        events: list[tuple[str, int | None]],
        *,
        invalid_call: int | None = None,
        failing_call: int | None = None,
    ) -> None:
        self.model_identity = "qwen3.8:27b"
        self.invocation_parameters = deepcopy(CANONICAL_PARAMETERS)
        self.events = events
        self.invalid_call = invalid_call
        self.failing_call = failing_call
        self.received_inputs: list[str] = []
        self.metadata_history: list[dict | None] = []
        self.last_response_metadata: dict | None = None

    def __call__(self, serialized_input: str) -> str:
        call_index = len(self.received_inputs)
        self.events.append(("measured", call_index))
        self.received_inputs.append(serialized_input)
        if call_index == self.failing_call:
            self.last_response_metadata = None
            self.metadata_history.append(None)
            raise RuntimeError("synthetic provider failure")

        self.last_response_metadata = {
            "model": self.model_identity,
            "created_at": f"2026-08-19T12:00:{call_index:02d}Z",
            "done": True,
            "done_reason": "stop",
            "total_duration": 1000 + call_index,
            "prompt_eval_count": 4000 + call_index,
            "eval_count": 40 + call_index,
        }
        self.metadata_history.append(deepcopy(self.last_response_metadata))
        if call_index == self.invalid_call:
            return invalid_raw_proposal()
        return valid_raw_proposal(call_index)


class WarmUpSpy:
    def __init__(self, events: list[tuple[str, int | None]]) -> None:
        self.events = events
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, model: ScriptedModel) -> None:
        self.events.append(("warm_up", None))
        self.calls.append(
            (model.model_identity, deepcopy(model.invocation_parameters))
        )


def measured_runner_module() -> ModuleType:
    module_name = "governed_agent_runtime.exp18_1a_measured_runner"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        pytest.fail(
            f"missing Exp 18.1A measured runner boundary: {module_name}",
            pytrace=False,
        )


def test_measured_runner_schedules_canonical_hidden_safe_inputs() -> None:
    runner = measured_runner_module()
    events: list[tuple[str, int | None]] = []
    model = ScriptedModel(events)
    warm_up = WarmUpSpy(events)

    result = runner.run_exp18_1a_measured_evaluation(
        ROOT,
        model=model,
        warm_up=warm_up,
        evaluated_revision="revision-under-test",
    )

    expected_schedule = [
        (case_key, run_index)
        for case_key in CASES
        for run_index in (1, 2, 3)
    ]
    assert events[0] == ("warm_up", None)
    assert len(warm_up.calls) == 1
    assert warm_up.calls[0] == ("qwen3.8:27b", CANONICAL_PARAMETERS)
    assert len(model.received_inputs) == 15
    assert len(result["measured_runs"]) == 15
    assert result["warm_up"]["included_in_measured_runs"] is False
    assert result["evaluated_revision"] == "revision-under-test"
    assert result["model_identity"] == "qwen3.8:27b"
    assert result["invocation_parameters"] == CANONICAL_PARAMETERS
    assert [
        (record["case_key"], record["run_index"])
        for record in result["measured_runs"]
    ] == expected_schedule

    for call_index, record in enumerate(result["measured_runs"]):
        case_key, run_index = expected_schedule[call_index]
        context = load_exp18_1a_context(ROOT, case_key)
        canonical_input = assemble_llm_probe_input(ROOT, context)

        assert record["run_id"]
        assert record["case_key"] == case_key
        assert record["run_index"] == run_index
        assert record["model_identity"] == "qwen3.8:27b"
        assert record["invocation_parameters"] == CANONICAL_PARAMETERS
        assert record["context_package"] == context
        assert record["serialized_model_input"] == canonical_input
        assert model.received_inputs[call_index] == canonical_input
        assert json.loads(canonical_input) == {
            "instructions": json.loads(canonical_input)["instructions"],
            "context_package": context,
            "model_proposal_schema": json.loads(canonical_input)[
                "model_proposal_schema"
            ],
        }
        assert HIDDEN_KEYS.isdisjoint(collect_keys(json.loads(canonical_input)))
        assert record["raw_model_response"] == valid_raw_proposal(call_index)
        assert record["provider_metadata"] == model.metadata_history[call_index]
        assert record["validation_results"]["proposal_schema"] == "PASSED"
        assert record["validation_results"]["proposal_context_semantics"] == (
            "PASSED"
        )
        assert record["runtime_decision"]
        assert record["runtime_state_before_evaluation"] == (
            record["runtime_state_after_evaluation"]
        )
        assert "tool_result" not in record


def test_measured_runner_records_invalid_proposal_and_provider_failure() -> None:
    runner = measured_runner_module()
    events: list[tuple[str, int | None]] = []
    model = ScriptedModel(events, invalid_call=0, failing_call=1)

    result = runner.run_exp18_1a_measured_evaluation(
        ROOT,
        model=model,
        warm_up=WarmUpSpy(events),
        evaluated_revision="revision-under-test",
    )

    assert len(model.received_inputs) == 15
    assert len(result["measured_runs"]) == 15

    invalid_record = result["measured_runs"][0]
    assert invalid_record["raw_model_response"] == invalid_raw_proposal()
    assert invalid_record["proposal"] == json.loads(invalid_raw_proposal())
    assert invalid_record["validation_results"]["parse"] == "PASSED"
    assert invalid_record["validation_results"]["proposal_schema"] == "FAILED"
    assert invalid_record["validation_results"][
        "proposal_context_semantics"
    ] == "SKIPPED"
    assert invalid_record["runtime_decision"]["decision"] == "BLOCK"
    assert invalid_record["runtime_decision"]["reason_codes"] == [
        "INVALID_PROPOSAL_SCHEMA"
    ]
    assert invalid_record["runtime_decision"]["tool_execution_allowed"] is False
    assert invalid_record["runtime_state_before_evaluation"] == (
        invalid_record["runtime_state_after_evaluation"]
    )

    failed_record = result["measured_runs"][1]
    assert failed_record["status"] == "MODEL_ERROR"
    assert "synthetic provider failure" in failed_record["error"]
    assert failed_record["raw_model_response"] is None
    assert failed_record["proposal"] is None
    assert failed_record["runtime_decision"] is None
    assert failed_record["serialized_model_input"] == model.received_inputs[1]
    assert HIDDEN_KEYS.isdisjoint(
        collect_keys(json.loads(failed_record["serialized_model_input"]))
    )
    assert sum(
        record["status"] == "MODEL_ERROR"
        for record in result["measured_runs"]
    ) == 1
