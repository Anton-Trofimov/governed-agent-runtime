import hashlib
import importlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REVISION = "0123456789abcdef0123456789abcdef01234567"
DIGEST = "sha256:provider-model-artifact"


def valid_proposal(index: int) -> str:
    return json.dumps(
        {
            "schema_version": "0.1.0",
            "proposal_id": f"proposal-live-bc003-{index}",
            "proposal_type": "PROVIDE_BOUNDED_HYPOTHESIS",
            "rationale": "Bounded proposal only.",
            "payload": {
                "hypotheses": [
                    {
                        "hypothesis_id": "hyp-live-bc003",
                        "statement": "Use the approved scale-before-shift path.",
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
    clean = True

    def is_clean(self, project_root: Path) -> bool:
        return self.clean

    def resolve_head(self, project_root: Path) -> str:
        return REVISION


class FakeChatModel:
    def __init__(self, configuration: dict) -> None:
        self.model_identity = configuration["model_identity"]
        self.model_artifact_identity = None
        self.request_timeout_seconds = configuration["request_timeout_seconds"]
        self.provider_endpoint = "/api/chat"
        self.invocation_parameters = {
            "temperature": configuration["temperature"],
            "top_p": configuration["top_p"],
            "top_k": configuration["top_k"],
            "min_p": configuration["min_p"],
            "presence_penalty": configuration["presence_penalty"],
            "repeat_penalty": configuration["repeat_penalty"],
            "seed": configuration["seed"],
            "num_ctx": configuration["num_ctx"],
            "num_predict": configuration["num_predict"],
            "think": configuration["think"],
            "stream": False,
            "keep_alive": configuration["keep_alive"],
        }
        self.received_inputs: list[str] = []
        self.last_response_metadata = None
        self.last_response_envelope = None
        self.last_raw_response_body = None
        self.last_request_payload = None

    def resolve_provider_version(self) -> str:
        return "0.32.14-test"

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
            "prompt_eval_count": 600,
            "eval_count": 900,
        }
        self.last_raw_response_body = json.dumps(self.last_response_envelope)
        self.last_response_metadata = {
            "model": self.model_identity,
            "thinking": "diagnostic",
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 600,
            "eval_count": 900,
        }
        return content


class Factory:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.models: list[FakeChatModel] = []

    def __call__(self, **configuration: object) -> FakeChatModel:
        config = deepcopy(configuration)
        self.calls.append(config)
        model = FakeChatModel(config)
        self.models.append(model)
        return model


def configure(monkeypatch: pytest.MonkeyPatch):
    live = importlib.import_module("governed_agent_runtime.bc003_live_evaluation")
    factory = Factory()
    monkeypatch.setattr(live, "_SubprocessGitBoundary", GitStub)
    monkeypatch.setattr(live, "OllamaChatModel", factory)
    monkeypatch.setattr(
        live,
        "_run_required_verification",
        lambda root: {"status": "PASSED", "commands": ["test-only"]},
    )
    return live, factory


def test_live_boundary_persists_one_preload_and_three_measured_attempts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, factory = configure(monkeypatch)
    evidence = tmp_path / "bc003-staging"

    result = live.run_bc003_live_evaluation(ROOT, evidence_directory=evidence)

    assert len(factory.calls) == 1
    assert factory.calls[0]["think"] is True
    assert factory.calls[0]["temperature"] == 1.0
    assert factory.calls[0]["top_p"] == 0.95
    assert factory.calls[0]["top_k"] == 20
    assert factory.calls[0]["min_p"] == 0.0
    assert factory.calls[0]["presence_penalty"] == 0.0
    assert factory.calls[0]["repeat_penalty"] == 1.0
    assert factory.calls[0]["seed"] == 18
    assert factory.calls[0]["num_ctx"] == 32768
    assert factory.calls[0]["num_predict"] == 8192
    assert len(factory.models[0].received_inputs) == 4
    manifest = json.loads((evidence / "manifest.json").read_text())
    assert manifest["bounded_change_id"] == "BC-003"
    assert manifest["expected_measured_call_count"] == 3
    assert manifest["model_artifact_identity"] == DIGEST
    assert manifest["written_evidence_files"] == manifest["expected_evidence_files"]
    assert manifest["post_run_budget_review_required"] is True
    assert len(manifest["generation_budget_diagnostics"]) == 3
    assert all(
        not item["suspected_truncation"]
        for item in manifest["generation_budget_diagnostics"]
    )
    assert len(result["measured_runs"]) == 3
    assert (evidence / "preload/bc-003-s12-preload.raw.json").exists()
    schema_path = ROOT / "schemas/model-proposal.schema.json"
    assert manifest["model_proposal_schema"]["sha256"] == hashlib.sha256(
        schema_path.read_bytes()
    ).hexdigest()


def test_live_raw_exists_before_runtime_evaluation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, _ = configure(monkeypatch)
    evidence = tmp_path / "bc003-staging"
    original = live._probe._exp18_runner.evaluate_proposal

    def evaluate(*args: object, **kwargs: object):
        assert (evidence / "attempts/bc-003-s12-run-1.raw.json").exists()
        return original(*args, **kwargs)

    monkeypatch.setattr(live._probe._exp18_runner, "evaluate_proposal", evaluate)
    live.run_bc003_live_evaluation(ROOT, evidence_directory=evidence)


def test_dirty_git_blocks_before_provider_construction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, factory = configure(monkeypatch)
    GitStub.clean = False
    try:
        with pytest.raises(ValueError, match="clean"):
            live.run_bc003_live_evaluation(
                ROOT,
                evidence_directory=tmp_path / "bc003-staging",
            )
    finally:
        GitStub.clean = True
    assert factory.calls == []
