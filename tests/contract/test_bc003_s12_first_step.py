import json
from copy import deepcopy
from pathlib import Path

import pytest

from governed_agent_runtime.bc003_s12_first_step import (
    load_bc003_context,
    run_bc003_first_step,
)
from governed_agent_runtime.exp18_1a_context_assembly import (
    assemble_llm_probe_input,
)

ROOT = Path(__file__).resolve().parents[2]
REVISION = "0123456789abcdef0123456789abcdef01234567"
DIGEST = "sha256:provider-model-artifact"


def valid_proposal(index: int) -> str:
    return json.dumps(
        {
            "schema_version": "0.1.0",
            "proposal_id": f"proposal-bc003-{index}",
            "proposal_type": "PROVIDE_BOUNDED_HYPOTHESIS",
            "rationale": (
                "The candidate rollout is unhealthy; capacity findings require "
                "8 healthy stable replicas before a full traffic shift. This "
                "is a proposal, not execution authorization."
            ),
            "payload": {
                "hypotheses": [
                    {
                        "hypothesis_id": "hyp-bc003-rollout-regression",
                        "statement": (
                            "Scale 2.4.1 from 6 to 8, verify all 8 are healthy, "
                            "shift traffic away from 2.4.2, verify recovery, "
                            "then remove or roll back 2.4.2."
                        ),
                        "source": "DETERMINISTIC_RULE",
                        "cause_status": "SUPPORTED",
                        "evidence_ids": [
                            "ev-bc003-rollout-health",
                            "ev-bc003-capacity-policy",
                            "ev-bc003-capacity-findings",
                        ],
                        "missing_evidence": [],
                    }
                ]
            },
        }
    )


class GitStub:
    def is_clean(self, project_root: Path) -> bool:
        return True

    def resolve_head(self, project_root: Path) -> str:
        return REVISION


class ModelStub:
    def __init__(self) -> None:
        self.model_identity = "qwen3.8:27b"
        self.model_artifact_identity = None
        self.request_timeout_seconds = 300
        self.provider_endpoint = "/api/chat"
        self.invocation_parameters = {
            "temperature": 0.6,
            "seed": 18,
            "num_ctx": 8192,
            "num_predict": 2048,
            "think": True,
            "stream": False,
            "keep_alive": "10m",
        }
        self.received_inputs: list[str] = []
        self.last_response_metadata = None
        self.last_response_envelope = None
        self.last_raw_response_body = None
        self.last_request_payload = None

    def resolve_model_artifact_identity(self) -> str:
        self.model_artifact_identity = DIGEST
        return DIGEST

    def __call__(self, serialized_input: str) -> str:
        index = len(self.received_inputs)
        self.received_inputs.append(serialized_input)
        content = valid_proposal(index)
        self.last_request_payload = {
            "model": self.model_identity,
            "messages": [{"role": "user", "content": serialized_input}],
        }
        self.last_response_envelope = {
            "model": self.model_identity,
            "message": {"thinking": "diagnostic", "content": content},
            "done": True,
        }
        self.last_raw_response_body = json.dumps(self.last_response_envelope)
        self.last_response_metadata = {
            "model": self.model_identity,
            "thinking": "diagnostic",
            "done": True,
        }
        return content


def test_bc003_runs_one_preload_and_three_measured_calls() -> None:
    model = ModelStub()
    reported: list[dict] = []

    result = run_bc003_first_step(
        ROOT,
        model=model,
        git_boundary=GitStub(),
        attempt_reporter=lambda event: reported.append(deepcopy(event)),
        required_verification_passed=True,
    )

    exact_input = assemble_llm_probe_input(ROOT, load_bc003_context(ROOT))
    assert model.received_inputs == [exact_input] * 4
    assert result["bounded_change_id"] == "BC-003"
    assert result["measured_run_count"] == 3
    assert [record["run_id"] for record in result["measured_runs"]] == [
        "bc-003-s12-run-1",
        "bc-003-s12-run-2",
        "bc-003-s12-run-3",
    ]
    assert [event["run_id"] for event in reported if event["event_type"] == "RAW"] == [
        "bc-003-s12-preload",
        "bc-003-s12-run-1",
        "bc-003-s12-run-2",
        "bc-003-s12-run-3",
    ]


def test_bc003_valid_hypothesis_routes_to_hypothesis_ready_without_execution() -> None:
    result = run_bc003_first_step(
        ROOT,
        model=ModelStub(),
        git_boundary=GitStub(),
        attempt_reporter=lambda event: None,
        required_verification_passed=True,
    )

    for record in result["measured_runs"]:
        decision = record["runtime_decision"]
        assert decision["decision"] == "ALLOW"
        assert decision["next_state"] == "HYPOTHESIS_READY"
        assert decision["tool_execution_allowed"] is False
        assert (
            record["runtime_state_before_evaluation"]
            == record["runtime_state_after_evaluation"]
        )
        assert record["evaluation_dimensions"]["runtime_control_containment"][
            "status"
        ] == "PASS"


def test_bc003_configuration_drift_blocks_before_provider_inference() -> None:
    model = ModelStub()
    model.invocation_parameters["temperature"] = 0.7

    with pytest.raises(ValueError, match="configuration"):
        run_bc003_first_step(
            ROOT,
            model=model,
            git_boundary=GitStub(),
            attempt_reporter=lambda event: None,
            required_verification_passed=True,
        )

    assert model.received_inputs == []
