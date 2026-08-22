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
            "proposal_id": f"proposal-live-bc002-{index}",
            "proposal_type": "CREATE_DRAFT",
            "rationale": "Prepare the governed plan.",
            "payload": {
                "tool_name": "create_remediation_plan",
                "arguments": {
                    "service_id": "payment-api",
                    "environment_id": "production",
                    "candidate_action": {"action_type": "rollback_deployment"},
                    "rationale": "Use supplied evidence.",
                    "evidence_ids": ["ev-runtime-rollback-basis"],
                    "risks": ["Use supplied constraints."],
                    "verification_steps": ["Verify supplied facts."],
                    "stop_conditions": ["Stop on conflicting operation."],
                },
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
    def __init__(
        self,
        configuration: dict,
        artifact_identities: list[str] | None = None,
    ) -> None:
        self.model_identity = configuration["model_identity"]
        self.model_artifact_identity = None
        self.request_timeout_seconds = configuration["request_timeout_seconds"]
        self.provider_endpoint = "/api/chat"
        self.invocation_parameters = {
            "temperature": configuration["temperature"],
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
        self.preflight_calls = 0
        self.artifact_identities = artifact_identities or [DIGEST]
        self.last_request_payload = None

    def resolve_provider_version(self) -> str:
        return "0.12.3-test"

    def resolve_model_artifact_identity(self) -> str:
        self.preflight_calls += 1
        index = min(self.preflight_calls - 1, len(self.artifact_identities) - 1)
        self.model_artifact_identity = self.artifact_identities[index]
        return self.model_artifact_identity

    def __call__(self, serialized_input: str) -> str:
        index = len(self.received_inputs)
        self.received_inputs.append(serialized_input)
        content = valid_proposal(index)
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
                "thinking": "diagnostic only",
                "content": content,
            },
            "done": True,
            "done_reason": "stop",
            "eval_count": 100,
        }
        self.last_raw_response_body = json.dumps(self.last_response_envelope)
        self.last_response_metadata = {
            "model": self.model_identity,
            "thinking": "diagnostic only",
            "done": True,
            "done_reason": "stop",
            "eval_count": 100,
        }
        return content


class Factory:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.models: list[FakeChatModel] = []
        self.treatment_artifact_identities = [DIGEST]

    def __call__(self, **configuration: object) -> FakeChatModel:
        config = deepcopy(configuration)
        self.calls.append(config)
        identities = (
            self.treatment_artifact_identities
            if config["think"] is True
            else [DIGEST]
        )
        model = FakeChatModel(config, identities)
        self.models.append(model)
        return model


def configure(monkeypatch: pytest.MonkeyPatch):
    live = importlib.import_module("governed_agent_runtime.bc002_live_evaluation")
    factory = Factory()
    monkeypatch.setattr(live, "_SubprocessGitBoundary", GitStub)
    monkeypatch.setattr(live, "OllamaChatModel", factory)
    monkeypatch.setattr(
        live,
        "_run_required_verification",
        lambda root: {"status": "PASSED", "commands": ["test-only"]},
    )
    return live, factory


def test_live_boundary_builds_fixed_branches_and_persists_schedule(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, factory = configure(monkeypatch)
    evidence = tmp_path / "bc002-staging"

    result = live.run_bc002_live_evaluation(ROOT, evidence_directory=evidence)

    assert [call["think"] for call in factory.calls] == [False, True]
    assert all(call["temperature"] == 0.6 for call in factory.calls)
    assert all(len(model.received_inputs) == 4 for model in factory.models)
    assert factory.models[0].received_inputs == factory.models[1].received_inputs
    manifest = json.loads((evidence / "manifest.json").read_text())
    assert manifest["bounded_change_id"] == "BC-002"
    assert manifest["status"] == "COMPLETED"
    assert manifest["expected_measured_call_count"] == 6
    assert manifest["model_artifact_identity"] == DIGEST
    assert manifest["provider"] == {"name": "Ollama", "version": "0.12.3-test"}
    assert len(manifest["expected_evidence_files"]) == 14
    assert manifest["written_evidence_files"] == manifest["expected_evidence_files"]
    assert len(result["measured_runs"]) == 6
    control_raw = json.loads(
        (evidence / "attempts/bc-002-s12-control-run-1.raw.json").read_text()
    )
    assert control_raw["provider_response_envelope"]["message"]["thinking"]
    assert control_raw["raw_provider_response_body"]
    assert control_raw["branch"] == "CONTROL"
    assert control_raw["provider_request_payload"]["messages"] == [
        {
            "role": "user",
            "content": result["serialized_model_input"],
        }
    ]
    schema_path = ROOT / "schemas/model-proposal.schema.json"
    assert control_raw["provider_request_payload"]["format"] == json.loads(
        schema_path.read_text()
    )
    assert manifest["model_proposal_schema"] == {
        "path": "schemas/model-proposal.schema.json",
        "sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest(),
    }
    assert (evidence / "preload/bc-002-s12-control-preload.raw.json").exists()
    assert (evidence / "preload/bc-002-s12-treatment-preload.raw.json").exists()


def test_live_raw_exists_before_runtime_evaluation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, _ = configure(monkeypatch)
    evidence = tmp_path / "bc002-staging"
    original = live._comparison._exp18_runner.evaluate_proposal

    def evaluate(*args: object, **kwargs: object):
        assert (evidence / "attempts/bc-002-s12-control-run-1.raw.json").exists()
        return original(*args, **kwargs)

    monkeypatch.setattr(live._comparison._exp18_runner, "evaluate_proposal", evaluate)
    live.run_bc002_live_evaluation(ROOT, evidence_directory=evidence)


def test_existing_target_is_rejected_before_provider_construction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, factory = configure(monkeypatch)
    target = tmp_path / "existing"
    target.mkdir()

    with pytest.raises(ValueError, match="already exists"):
        live.run_bc002_live_evaluation(ROOT, evidence_directory=target)

    assert factory.calls == []


def test_dirty_git_blocks_before_provider_construction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, factory = configure(monkeypatch)
    GitStub.clean = False
    try:
        with pytest.raises(ValueError, match="clean"):
            live.run_bc002_live_evaluation(
                ROOT,
                evidence_directory=tmp_path / "bc002-staging",
            )
    finally:
        GitStub.clean = True
    assert factory.calls == []


def test_attempt_files_are_immutable(tmp_path: Path) -> None:
    live = importlib.import_module("governed_agent_runtime.bc002_live_evaluation")
    path = tmp_path / "attempt.raw.json"
    live._write_immutable(path, {"first": True})

    with pytest.raises(ValueError, match="already exists"):
        live._write_immutable(path, {"first": False})

    assert json.loads(path.read_text()) == {"first": True}


def test_artifact_drift_preserves_control_and_blocks_treatment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, factory = configure(monkeypatch)
    factory.treatment_artifact_identities = [DIGEST, "sha256:changed-artifact"]
    evidence = tmp_path / "bc002-staging"

    with pytest.raises(ValueError, match="artifact.*changed"):
        live.run_bc002_live_evaluation(ROOT, evidence_directory=evidence)

    assert len(factory.models[0].received_inputs) == 4
    assert factory.models[1].received_inputs == []
    assert (evidence / "preload/bc-002-s12-control-preload.raw.json").exists()
    for index in (1, 2, 3):
        stem = evidence / f"attempts/bc-002-s12-control-run-{index}"
        assert stem.with_suffix(".raw.json").exists()
        assert stem.with_suffix(".result.json").exists()
    assert not (evidence / "preload/bc-002-s12-treatment-preload.raw.json").exists()
