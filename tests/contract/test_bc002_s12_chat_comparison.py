import importlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from governed_agent_runtime.exp18_1a_context_assembly import (
    assemble_llm_probe_input,
    load_exp18_1a_context,
)

ROOT = Path(__file__).resolve().parents[2]
REVISION = "0123456789abcdef0123456789abcdef01234567"
DIGEST = "sha256:provider-model-artifact"


def valid_proposal(index: int) -> str:
    return json.dumps(
        {
            "schema_version": "0.1.0",
            "proposal_id": f"proposal-bc002-{index}",
            "proposal_type": "CREATE_DRAFT",
            "rationale": "Prepare the governed rollback plan.",
            "payload": {
                "tool_name": "create_remediation_plan",
                "arguments": {
                    "service_id": "payment-api",
                    "environment_id": "production",
                    "candidate_action": {"action_type": "rollback_deployment"},
                    "rationale": "Use the supplied rollback basis.",
                    "evidence_ids": ["ev-runtime-rollback-basis"],
                    "risks": ["Use supplied transition constraints."],
                    "verification_steps": ["Verify supplied facts."],
                    "stop_conditions": ["Stop on a conflicting operation."],
                },
            },
        }
    )


class GitStub:
    def is_clean(self, project_root: Path) -> bool:
        return True

    def resolve_head(self, project_root: Path) -> str:
        return REVISION


class ModelStub:
    def __init__(self, think: bool, *, response: str | None = None) -> None:
        self.model_identity = "qwen3.8:27b"
        self.model_artifact_identity = None
        self.request_timeout_seconds = 300
        self.invocation_parameters = {
            "temperature": 0.6,
            "seed": 18,
            "num_ctx": 8192,
            "num_predict": 2048,
            "think": think,
            "stream": False,
            "keep_alive": "10m",
        }
        self.provider_endpoint = "/api/chat"
        self.response = response
        self.received_inputs: list[str] = []
        self.last_response_metadata = None
        self.last_response_envelope = None
        self.last_raw_response_body = None
        self.last_request_payload = None
        self.preflight_calls = 0

    def resolve_model_artifact_identity(self) -> str:
        self.preflight_calls += 1
        self.model_artifact_identity = DIGEST
        return DIGEST

    def __call__(self, serialized_input: str) -> str:
        index = len(self.received_inputs)
        self.received_inputs.append(serialized_input)
        content = valid_proposal(index) if self.response is None else self.response
        self.last_request_payload = {
            "model": self.model_identity,
            "messages": [{"role": "user", "content": serialized_input}],
            "stream": False,
            "think": self.invocation_parameters["think"],
            "format": json.loads(
                (ROOT / "schemas/model-proposal.schema.json").read_text()
            ),
            "keep_alive": "10m",
            "options": {
                key: self.invocation_parameters[key]
                for key in ("temperature", "seed", "num_ctx", "num_predict")
            },
        }
        self.last_response_envelope = {
            "model": self.model_identity,
            "message": {
                "role": "assistant",
                "thinking": valid_proposal(99),
                "content": content,
            },
            "done": True,
            "done_reason": "stop",
            "eval_count": 100,
        }
        self.last_raw_response_body = json.dumps(self.last_response_envelope)
        self.last_response_metadata = {
            "model": self.model_identity,
            "thinking": valid_proposal(99),
            "done": True,
            "done_reason": "stop",
            "eval_count": 100,
        }
        return content


def module():
    return importlib.import_module(
        "governed_agent_runtime.bc002_s12_chat_comparison"
    )


def run(control: ModelStub, treatment: ModelStub, reported: list[dict]):
    return module().run_bc002_canonical_comparison(
        ROOT,
        control_model=control,
        treatment_model=treatment,
        git_boundary=GitStub(),
        attempt_reporter=lambda event: reported.append(deepcopy(event)),
        required_verification_passed=True,
    )


def test_fixed_chat_schedule_uses_exact_s12_content_for_both_preloads() -> None:
    control = ModelStub(False)
    treatment = ModelStub(True)
    reported: list[dict] = []

    result = run(control, treatment, reported)

    exact_input = assemble_llm_probe_input(ROOT, load_exp18_1a_context(ROOT, "s12"))
    assert control.received_inputs == [exact_input] * 4
    assert treatment.received_inputs == [exact_input] * 4
    assert result["bounded_change_id"] == "BC-002"
    assert result["measured_run_count"] == 6
    assert [record["run_id"] for record in result["measured_runs"]] == [
        *[f"bc-002-s12-control-run-{i}" for i in (1, 2, 3)],
        *[f"bc-002-s12-treatment-run-{i}" for i in (1, 2, 3)],
    ]
    assert [event["run_id"] for event in reported if event["event_type"] == "RAW"] == [
        "bc-002-s12-control-preload",
        *[f"bc-002-s12-control-run-{i}" for i in (1, 2, 3)],
        "bc-002-s12-treatment-preload",
        *[f"bc-002-s12-treatment-run-{i}" for i in (1, 2, 3)],
    ]
    assert reported[0]["included_in_measured_runs"] is False
    assert reported[0]["decision_evidence_eligible"] is False
    assert reported[0]["provider_response_envelope"]["message"]["content"]
    assert reported[0]["raw_provider_response_body"]
    first_measured_raw = next(
        event
        for event in reported
        if event["run_id"] == "bc-002-s12-control-run-1"
        and event["event_type"] == "RAW"
    )
    request = first_measured_raw["provider_request_payload"]
    assert request["messages"] == [{"role": "user", "content": exact_input}]
    assert request["format"] == json.loads(
        (ROOT / "schemas/model-proposal.schema.json").read_text()
    )
    assert result["measured_runs"][0]["evaluation_dimensions"][
        "structured_model_contract_quality"
    ]["submitted_final_present"] is True


def test_reasoning_is_never_promoted_and_invalid_final_is_not_reached() -> None:
    control = ModelStub(False, response="")
    treatment = ModelStub(True, response="")

    result = run(control, treatment, [])

    for record in result["measured_runs"]:
        assert record["proposal"] is None
        assert record["runtime_decision"] is None
        assert record["runtime_evaluation_status"] == "NOT_REACHED"
        dimensions = record["evaluation_dimensions"]
        assert dimensions["structured_model_contract_quality"][
            "submitted_final_present"
        ] is False
        assert dimensions["runtime_control_containment"] == {
            "status": "PASS",
            "runtime_decision": "NOT_REACHED",
            "policy_evaluation_status": "NOT_REACHED",
            "tool_execution_occurred": False,
            "normalized_state_mutated": False,
        }

    schema_invalid = run(
        ModelStub(False, response="{}"),
        ModelStub(True, response="{}"),
        [],
    )
    for record in schema_invalid["measured_runs"]:
        assert record["status"] == "PROPOSAL_VALIDATION_ERROR"
        assert record["runtime_evaluation_status"] == "NOT_REACHED"
        assert record["runtime_decision"] is None
        assert record["evaluation_dimensions"][
            "structured_model_contract_quality"
        ]["submitted_final_present"] is True


def test_configuration_or_artifact_mismatch_blocks_before_inference() -> None:
    control = ModelStub(False)
    treatment = ModelStub(True)
    treatment.invocation_parameters["temperature"] = 0.7
    with pytest.raises(ValueError, match="configuration"):
        run(control, treatment, [])
    assert control.received_inputs == treatment.received_inputs == []

    control = ModelStub(False)
    treatment = ModelStub(True)
    treatment.resolve_model_artifact_identity = lambda: "sha256:other"
    with pytest.raises(ValueError, match="artifact"):
        run(control, treatment, [])
    assert control.received_inputs == treatment.received_inputs == []
