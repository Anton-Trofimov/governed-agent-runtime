import hashlib
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
EVALUATED_REVISION = "0123456789abcdef0123456789abcdef01234567"
CANONICAL_PARAMETERS = {
    "temperature": 0,
    "seed": 18,
    "num_ctx": 8192,
    "num_predict": 2048,
    "think": True,
    "stream": False,
    "keep_alive": "10m",
}


def bc001_module() -> ModuleType:
    module_name = "governed_agent_runtime.bc001_s12_reasoning_comparison"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        pytest.fail(f"missing BC-001 boundary: {module_name}", pytrace=False)


def valid_proposal(call_index: int) -> str:
    return json.dumps(
        {
            "schema_version": "0.1.0",
            "proposal_id": f"proposal-bc001-{call_index}",
            "proposal_type": "CREATE_DRAFT",
            "rationale": "Prepare the bounded plan without execution.",
            "payload": {
                "tool_name": "create_remediation_plan",
                "arguments": {
                    "service_id": "payment-api",
                    "environment_id": "production",
                    "candidate_action": {
                        "action_type": "rollback_deployment"
                    },
                    "rationale": "Use the supplied rollback basis.",
                    "evidence_ids": ["ev-runtime-rollback-basis"],
                    "risks": ["Review the supplied transition constraints."],
                    "verification_steps": ["Verify supplied health facts."],
                    "stop_conditions": ["Stop on a conflicting operation."],
                },
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class GitBoundaryStub:
    def __init__(
        self,
        *,
        clean: bool = True,
        revision: str = EVALUATED_REVISION,
    ) -> None:
        self.clean = clean
        self.revision = revision

    def is_clean(self, project_root: Path) -> bool:
        assert project_root == ROOT
        return self.clean

    def resolve_head(self, project_root: Path) -> str:
        assert project_root == ROOT
        return self.revision


class ModelStub:
    def __init__(
        self,
        *,
        model_identity: str = "qwen3.8:27b",
        artifact_identity: str = "caller-supplied-untrusted-text",
        provider_artifact_identity: str = "sha256:current-model-artifact",
        parameters: dict | None = None,
        request_timeout_seconds: float = 300,
    ) -> None:
        self.model_identity = model_identity
        self.model_artifact_identity = artifact_identity
        self.provider_artifact_identity = provider_artifact_identity
        self.invocation_parameters = deepcopy(
            parameters if parameters is not None else CANONICAL_PARAMETERS
        )
        self.request_timeout_seconds = request_timeout_seconds
        self.received_inputs: list[str] = []
        self.preflight_calls = 0
        self.last_response_metadata: dict | None = None

    def resolve_model_artifact_identity(self) -> str:
        self.preflight_calls += 1
        self.model_artifact_identity = self.provider_artifact_identity
        return self.provider_artifact_identity

    def __call__(self, serialized_input: str) -> str:
        call_index = len(self.received_inputs)
        self.received_inputs.append(serialized_input)
        self.last_response_metadata = {
            "model": self.model_identity,
            "done": True,
            "done_reason": "stop",
            "total_duration": 1000 + call_index,
            "prompt_eval_count": 3496,
            "eval_count": 100 + call_index,
            "eval_duration": 500 + call_index,
            "thinking": "diagnostic reasoning" if call_index else "preload",
        }
        return valid_proposal(call_index)


def run_canonical(
    model: ModelStub,
    reported: list[dict],
    **overrides: object,
) -> dict:
    runner = bc001_module()
    arguments = {
        "model": model,
        "git_boundary": GitBoundaryStub(),
        "attempt_reporter": lambda event: reported.append(deepcopy(event)),
        "required_verification_passed": True,
    }
    arguments.update(overrides)
    return runner.run_bc001_canonical_comparison(ROOT, **arguments)


def test_canonical_schedule_is_one_excluded_preload_then_three_s12_runs() -> None:
    model = ModelStub()
    reported: list[dict] = []

    result = run_canonical(model, reported)

    canonical_input = assemble_llm_probe_input(
        ROOT, load_exp18_1a_context(ROOT, "s12")
    )
    assert model.received_inputs == ["", canonical_input, canonical_input, canonical_input]
    assert result["bounded_change_id"] == "BC-001"
    assert result["evidence_scope"] == "CANONICAL_DECISION"
    assert result["decision_evidence_eligible"] is True
    assert result["model_artifact_identity"] == "sha256:current-model-artifact"
    assert result["request_timeout_seconds"] == 300
    assert model.preflight_calls == 1
    assert result["serialized_model_input_sha256"] == hashlib.sha256(
        canonical_input.encode()
    ).hexdigest()
    assert result["preload"] == {
        "completed": True,
        "included_in_measured_runs": False,
        "attempt_kind": "PRELOAD",
    }
    assert [record["run_index"] for record in result["measured_runs"]] == [1, 2, 3]
    assert all(record["case_key"] == "s12" for record in result["measured_runs"])
    assert all(record["invocation_parameters"] == CANONICAL_PARAMETERS for record in result["measured_runs"])
    assert [event["event_type"] for event in reported] == [
        "RAW",
        "RAW",
        "RESULT",
        "RAW",
        "RESULT",
        "RAW",
        "RESULT",
    ]
    assert reported[0]["attempt_kind"] == "PRELOAD"
    assert reported[0]["included_in_measured_runs"] is False
    assert all(event["attempt_kind"] == "MEASURED" for event in reported[1:])
    for run_index, record in enumerate(result["measured_runs"], start=1):
        run_id = f"bc-001-s12-run-{run_index}"
        assert record["run_id"] == run_id
        assert record["runtime_state_before_evaluation"]["trace_id"] == (
            f"trace-{run_id}"
        )
        assert record["runtime_state_before_evaluation"]["session_state"][
            "session_id"
        ] == f"session-{run_id}"
    assert [event["run_id"] for event in reported[1::2]] == [
        "bc-001-s12-run-1",
        "bc-001-s12-run-2",
        "bc-001-s12-run-3",
    ]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"git_boundary": GitBoundaryStub(clean=False)}, "clean"),
        ({"git_boundary": GitBoundaryStub(revision="")}, "revision"),
        ({"required_verification_passed": False}, "verification"),
    ],
)
def test_readiness_failure_blocks_before_any_provider_call(
    overrides: dict,
    message: str,
) -> None:
    model = ModelStub()

    with pytest.raises(ValueError, match=message):
        run_canonical(model, [], **overrides)

    assert model.received_inputs == []


def test_timeout_mismatch_blocks_before_provider_or_identity_preflight() -> None:
    model = ModelStub(request_timeout_seconds=299)

    with pytest.raises(ValueError, match="timeout"):
        run_canonical(model, [])

    assert model.preflight_calls == 0
    assert model.received_inputs == []


def test_input_identity_mismatch_blocks_before_any_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = bc001_module()
    model = ModelStub()
    monkeypatch.setattr(runner, "assemble_llm_probe_input", lambda *_: "changed")

    with pytest.raises(ValueError, match="input identity"):
        run_canonical(model, [])

    assert model.received_inputs == []


@pytest.mark.parametrize(
    ("model", "expected_identity", "message"),
    [
        (ModelStub(model_identity="other:latest"), None, "model tag"),
        (ModelStub(parameters={**CANONICAL_PARAMETERS, "num_predict": 4096}), None, "configuration"),
        (ModelStub(), "sha256:known-baseline", "artifact"),
        (ModelStub(provider_artifact_identity=""), None, "immutable"),
    ],
)
def test_canonical_model_or_configuration_failure_blocks_provider(
    model: ModelStub,
    expected_identity: str | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        run_canonical(
            model,
            [],
            expected_baseline_artifact_identity=expected_identity,
        )

    assert model.received_inputs == []


def test_noncanonical_model_is_separated_from_decision_evidence() -> None:
    runner = bc001_module()
    model = ModelStub(model_identity="other:latest")
    reported: list[dict] = []

    result = runner.run_bc001_noncanonical_reproduction(
        ROOT,
        model=model,
        git_boundary=GitBoundaryStub(),
        attempt_reporter=lambda event: reported.append(deepcopy(event)),
        required_verification_passed=True,
    )

    assert len(model.received_inputs) == 4
    assert result["evidence_scope"] == "NON_CANONICAL_REPRODUCTION"
    assert result["decision_evidence_eligible"] is False
    assert all(event["decision_evidence_eligible"] is False for event in reported)


def test_provider_identity_replaces_untrusted_caller_text() -> None:
    model = ModelStub(
        artifact_identity="arbitrary-caller-value",
        provider_artifact_identity="sha256:provider-inventory-digest",
    )

    result = run_canonical(model, [])

    assert model.preflight_calls == 1
    assert result["model_artifact_identity"] == (
        "sha256:provider-inventory-digest"
    )


def test_raw_is_reported_before_interpretation_and_results_stay_nonmutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = bc001_module()
    model = ModelStub()
    events: list[str] = []
    reported: list[dict] = []
    original_validate = runner._exp18_runner._validate_schema

    def validate(instance: object, schema: dict) -> None:
        events.append("VALIDATE")
        original_validate(instance, schema)

    def report(event: dict) -> None:
        reported.append(deepcopy(event))
        events.append(f"{event['event_type']}:{event['attempt_kind']}")

    monkeypatch.setattr(runner._exp18_runner, "_validate_schema", validate)
    result = runner.run_bc001_canonical_comparison(
        ROOT,
        model=model,
        git_boundary=GitBoundaryStub(),
        attempt_reporter=report,
        required_verification_passed=True,
    )

    first_measured_raw = events.index("RAW:MEASURED")
    assert first_measured_raw < events.index("VALIDATE")
    for record in result["measured_runs"]:
        assert record["runtime_state_before_evaluation"] == record["runtime_state_after_evaluation"]
        assert "tool_result" not in record
        assert record["evaluation_dimensions"]["semantic_grounding"] == "HUMAN_REVIEW_REQUIRED"
        assert record["evaluation_dimensions"]["runtime_control_containment"]["normalized_state_mutated"] is False
        assert record["evaluation_dimensions"]["runtime_control_containment"]["tool_execution_occurred"] is False
    measured_raw = next(event for event in reported if event["attempt_kind"] == "MEASURED")
    assert measured_raw["provider_metadata"]["thinking"] == "diagnostic reasoning"
    assert measured_raw["model_artifact_identity"] == model.model_artifact_identity


def test_containment_exposes_unexpected_execution_and_mutation() -> None:
    runner = bc001_module()
    state_before = {
        "execution_state": {
            "execution_status": "NOT_STARTED",
            "executed_tool_call_id": None,
            "side_effect_summary": None,
        }
    }
    state_after = deepcopy(state_before)
    state_after["execution_state"] = {
        "execution_status": "COMPLETED",
        "executed_tool_call_id": "tool-call-unexpected",
        "side_effect_summary": "unexpected effect",
    }

    dimensions = runner._evaluation_dimensions(
        {
            "runtime_state_before_evaluation": state_before,
            "runtime_state_after_evaluation": state_after,
            "tool_result": {"unexpected": True},
        }
    )

    containment = dimensions["runtime_control_containment"]
    assert containment["tool_execution_occurred"] is True
    assert containment["normalized_state_mutated"] is True
