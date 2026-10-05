import json
from copy import deepcopy
from pathlib import Path

import pytest

from governed_agent_runtime.bc005_s12_prospective_grounded import (
    load_bc005_context,
    run_bc005_first_step,
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
            "proposal_id": f"proposal-bc005-{index}",
            "proposal_type": "PROVIDE_BOUNDED_HYPOTHESIS",
            "rationale": (
                "The candidate rollout is unhealthy and the stable capacity "
                "findings require a bounded scale-before-shift path. This is "
                "a proposal, not execution authorization."
            ),
            "payload": {
                "hypotheses": [
                    {
                        "hypothesis_id": "hyp-bc005-rollout-regression",
                        "statement": (
                            "Scale stable 2.4.1 from 6 to 8, establish all 8 "
                            "stable replicas are healthy, shift traffic away "
                            "from degraded 2.4.2, require post-shift recovery "
                            "PASS, then remove the 2.4.2 candidate replicas or "
                            "complete rollback to 2.4.1."
                        ),
                        "source": "DETERMINISTIC_RULE",
                        "cause_status": "SUPPORTED",
                        "evidence_ids": [
                            "ev-bc005-rollout-health",
                            "ev-bc005-capacity-policy",
                            "ev-bc005-capacity-findings",
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
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "presence_penalty": 0.0,
            "repeat_penalty": 1.0,
            "seed": 18,
            "num_ctx": 32768,
            "num_predict": 8192,
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
            "done_reason": "stop",
            "prompt_eval_count": 650,
            "eval_count": 950,
        }
        self.last_raw_response_body = json.dumps(self.last_response_envelope)
        self.last_response_metadata = {
            "model": self.model_identity,
            "thinking": "diagnostic",
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 650,
            "eval_count": 950,
        }
        return content


def test_bc005_runs_one_preload_and_three_measured_calls_after_all_gates() -> None:
    model = ModelStub()
    reported: list[dict] = []

    result = run_bc005_first_step(
        ROOT,
        model=model,
        git_boundary=GitStub(),
        attempt_reporter=lambda event: reported.append(deepcopy(event)),
        required_verification_passed=True,
        human_pre_run_approved=True,
        approved_revision=REVISION,
    )

    exact_input = assemble_llm_probe_input(ROOT, load_bc005_context(ROOT))
    assert model.received_inputs == [exact_input] * 4
    assert result["bounded_change_id"] == "BC-005"
    assert result["traceability_gate"]["gate_pass"] is True
    assert result["measured_run_count"] == 3
    assert [record["run_id"] for record in result["measured_runs"]] == [
        "bc-005-s12-run-1",
        "bc-005-s12-run-2",
        "bc-005-s12-run-3",
    ]
    assert [event["run_id"] for event in reported if event["event_type"] == "RAW"] == [
        "bc-005-s12-preload",
        "bc-005-s12-run-1",
        "bc-005-s12-run-2",
        "bc-005-s12-run-3",
    ]


def test_bc005_valid_hypothesis_routes_without_execution_or_state_mutation() -> None:
    result = run_bc005_first_step(
        ROOT,
        model=ModelStub(),
        git_boundary=GitStub(),
        attempt_reporter=lambda event: None,
        required_verification_passed=True,
        human_pre_run_approved=True,
        approved_revision=REVISION,
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


def test_bc005_human_pre_run_gate_blocks_before_provider_inference() -> None:
    model = ModelStub()

    with pytest.raises(ValueError, match="human pre-run"):
        run_bc005_first_step(
            ROOT,
            model=model,
            git_boundary=GitStub(),
            attempt_reporter=lambda event: None,
            required_verification_passed=True,
            human_pre_run_approved=False,
            approved_revision=REVISION,
        )

    assert model.received_inputs == []


def test_bc005_configuration_drift_blocks_before_provider_inference() -> None:
    model = ModelStub()
    model.invocation_parameters["temperature"] = 0.7

    with pytest.raises(ValueError, match="configuration"):
        run_bc005_first_step(
            ROOT,
            model=model,
            git_boundary=GitStub(),
            attempt_reporter=lambda event: None,
            required_verification_passed=True,
            human_pre_run_approved=True,
            approved_revision=REVISION,
        )

    assert model.received_inputs == []


def test_bc005_approval_revision_mismatch_blocks_before_provider_inference() -> None:
    model = ModelStub()

    with pytest.raises(ValueError, match="not bound to the evaluated revision"):
        run_bc005_first_step(
            ROOT,
            model=model,
            git_boundary=GitStub(),
            attempt_reporter=lambda event: None,
            required_verification_passed=True,
            human_pre_run_approved=True,
            approved_revision="ffffffffffffffffffffffffffffffffffffffff",
        )

    assert model.received_inputs == []


@pytest.fixture(autouse=True)
def approved_design_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    # Only runner mechanics are tested here; canonical approval is separately tested.
    monkeypatch.setattr(
        "governed_agent_runtime.bc005_s12_prospective_grounded.validate_bc005_pre_run_design",
        lambda root: {"gate_pass": True},
    )
