import importlib
import json
from copy import deepcopy
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
REVISION = "0123456789abcdef0123456789abcdef01234567"
ARTIFACT_DIGEST = "sha256:provider-qwen-artifact"
CANONICAL_PARAMETERS = {
    "temperature": 0,
    "seed": 18,
    "num_ctx": 8192,
    "num_predict": 2048,
    "think": True,
    "stream": False,
    "keep_alive": "10m",
}


def live_module() -> ModuleType:
    module_name = "governed_agent_runtime.bc001_live_evaluation"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        pytest.fail(f"missing BC-001 live boundary: {module_name}", pytrace=False)


def valid_proposal(call_index: int) -> str:
    return json.dumps(
        {
            "schema_version": "0.1.0",
            "proposal_id": f"proposal-live-bc001-{call_index}",
            "proposal_type": "CREATE_DRAFT",
            "rationale": "Prepare a bounded plan without execution.",
            "payload": {
                "tool_name": "create_remediation_plan",
                "arguments": {
                    "service_id": "payment-api",
                    "environment_id": "production",
                    "candidate_action": {
                        "action_type": "rollback_deployment"
                    },
                    "rationale": "Use the supplied rollback evidence.",
                    "evidence_ids": ["ev-runtime-rollback-basis"],
                    "risks": ["Review supplied constraints."],
                    "verification_steps": ["Verify supplied health facts."],
                    "stop_conditions": ["Stop on conflicting operation."],
                },
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class GitStub:
    clean = True
    revision = REVISION

    def is_clean(self, project_root: Path) -> bool:
        assert project_root == ROOT
        return self.clean

    def resolve_head(self, project_root: Path) -> str:
        assert project_root == ROOT
        return self.revision


class FakeModel:
    def __init__(
        self,
        *,
        fail_preflight: bool = False,
        failing_call: int | None = None,
        invocation_parameters: dict | None = None,
        provider_version: str = "0.12.3-test",
    ) -> None:
        self.model_identity = "qwen3.8:27b"
        self.model_artifact_identity = None
        self.invocation_parameters = deepcopy(
            invocation_parameters or CANONICAL_PARAMETERS
        )
        self.request_timeout_seconds = 300
        self.provider_version = provider_version
        self.fail_preflight = fail_preflight
        self.failing_call = failing_call
        self.preflight_calls = 0
        self.provider_version_calls = 0
        self.received_inputs: list[str] = []
        self.last_response_metadata: dict | None = None

    def resolve_model_artifact_identity(self) -> str:
        self.preflight_calls += 1
        if self.fail_preflight:
            raise ValueError("synthetic model inventory failure")
        self.model_artifact_identity = ARTIFACT_DIGEST
        return ARTIFACT_DIGEST

    def resolve_provider_version(self) -> str:
        self.provider_version_calls += 1
        if not self.provider_version:
            raise ValueError("synthetic provider version failure")
        return self.provider_version

    def __call__(self, serialized_input: str) -> str:
        call_index = len(self.received_inputs)
        self.received_inputs.append(serialized_input)
        if call_index == self.failing_call:
            self.last_response_metadata = None
            raise RuntimeError("synthetic provider failure")
        self.last_response_metadata = {
            "model": self.model_identity,
            "done": True,
            "done_reason": "stop",
            "total_duration": 1000 + call_index,
            "prompt_eval_count": 3496,
            "eval_count": 100 + call_index,
            "eval_duration": 500 + call_index,
            "thinking": "test-only reasoning content",
        }
        return valid_proposal(call_index)


class ModelFactory:
    def __init__(self, model: FakeModel) -> None:
        self.model = model
        self.calls: list[dict] = []

    def __call__(self, **configuration: object) -> FakeModel:
        self.calls.append(deepcopy(configuration))
        return self.model


def configure(
    monkeypatch: pytest.MonkeyPatch,
    *,
    model: FakeModel | None = None,
    clean: bool = True,
    verification_failure: bool = False,
) -> tuple[ModuleType, FakeModel, ModelFactory]:
    live = live_module()
    GitStub.clean = clean
    selected_model = model or FakeModel()
    factory = ModelFactory(selected_model)
    monkeypatch.setattr(live, "_SubprocessGitBoundary", GitStub)
    monkeypatch.setattr(live, "OllamaGenerateModel", factory)

    def verify(project_root: Path) -> dict:
        assert project_root == ROOT
        if verification_failure:
            raise RuntimeError("synthetic required verification failure")
        return {
            "status": "PASSED",
            "commands": [
                "git diff --check",
                ".venv/bin/ruff check .",
                ".venv/bin/pytest",
            ],
        }

    monkeypatch.setattr(live, "_run_required_verification", verify)
    return live, selected_model, factory


def run_live(live: ModuleType, tmp_path: Path) -> dict:
    return live.run_bc001_live_evaluation(
        ROOT,
        evidence_directory=tmp_path / "bc001-staging",
        base_url="http://127.0.0.1:11434",
    )


def test_live_path_constructs_fixed_adapter_and_persists_complete_schedule(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, model, factory = configure(monkeypatch)

    result = run_live(live, tmp_path)

    evidence = tmp_path / "bc001-staging"
    manifest = json.loads((evidence / "manifest.json").read_text())
    assert factory.calls == [
        {
            "base_url": "http://127.0.0.1:11434",
            "model_identity": "qwen3.8:27b",
            "model_schema": json.loads(
                (ROOT / "schemas/model-proposal.schema.json").read_text()
            ),
            "temperature": 0,
            "seed": 18,
            "num_ctx": 8192,
            "num_predict": 2048,
            "think": True,
            "keep_alive": "10m",
            "request_timeout_seconds": 300,
        }
    ]
    assert model.preflight_calls == 1
    assert model.provider_version_calls == 1
    assert len(model.received_inputs) == 4
    assert result["preload"]["included_in_measured_runs"] is False
    assert len(result["measured_runs"]) == 3
    assert manifest["status"] == "COMPLETED"
    assert manifest["bounded_change_id"] == "BC-001"
    assert manifest["evidence_scope"] == "CANONICAL_DECISION"
    assert manifest["decision_evidence_eligible"] is True
    assert manifest["evaluated_revision"] == REVISION
    assert manifest["verification"]["status"] == "PASSED"
    assert manifest["model_identity"] == "qwen3.8:27b"
    assert manifest["model_artifact_identity"] == ARTIFACT_DIGEST
    assert manifest["invocation_parameters"] == CANONICAL_PARAMETERS
    assert manifest["request_timeout_seconds"] == 300
    assert manifest["python_runtime"]["implementation"]
    assert manifest["python_runtime"]["version"]
    assert manifest["provider"]["name"] == "Ollama"
    assert manifest["provider"]["version"] == "0.12.3-test"
    assert manifest["preload"]["included_in_measured_runs"] is False
    assert manifest["expected_measured_call_count"] == 3
    assert manifest["measured_run_ids"] == [
        "bc-001-s12-run-1",
        "bc-001-s12-run-2",
        "bc-001-s12-run-3",
    ]
    assert (evidence / "preload" / "bc-001-s12-preload.raw.json").exists()
    for run_index in (1, 2, 3):
        stem = f"bc-001-s12-run-{run_index}"
        assert (evidence / "attempts" / f"{stem}.raw.json").exists()
        assert (evidence / "attempts" / f"{stem}.result.json").exists()


def test_dirty_git_and_failed_verification_block_before_model_preflight(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, dirty_model, _ = configure(monkeypatch, clean=False)
    with pytest.raises(ValueError, match="clean"):
        run_live(live, tmp_path)
    assert dirty_model.preflight_calls == 0
    assert dirty_model.received_inputs == []

    live, failed_model, _ = configure(
        monkeypatch,
        verification_failure=True,
    )
    with pytest.raises(RuntimeError, match="verification"):
        live.run_bc001_live_evaluation(
            ROOT,
            evidence_directory=tmp_path / "failed-verification",
        )
    assert failed_model.preflight_calls == 0
    assert failed_model.received_inputs == []


def test_core_readiness_failure_blocks_before_model_preflight(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, model, _ = configure(monkeypatch)
    original_assemble = live._comparison.assemble_llm_probe_input
    monkeypatch.setattr(
        live._comparison,
        "assemble_llm_probe_input",
        lambda *_: "changed-input",
    )

    with pytest.raises(ValueError, match="input identity"):
        run_live(live, tmp_path)

    assert model.preflight_calls == 0
    assert model.received_inputs == []
    monkeypatch.setattr(
        live._comparison,
        "assemble_llm_probe_input",
        original_assemble,
    )

    invalid_model = FakeModel(
        invocation_parameters={**CANONICAL_PARAMETERS, "num_predict": 4096}
    )
    live, invalid_model, _ = configure(
        monkeypatch,
        model=invalid_model,
    )
    with pytest.raises(ValueError, match="configuration"):
        live.run_bc001_live_evaluation(
            ROOT,
            evidence_directory=tmp_path / "invalid-configuration",
        )
    assert invalid_model.preflight_calls == 0
    assert invalid_model.received_inputs == []


def test_model_preflight_failure_blocks_preload_and_measured_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, model, _ = configure(
        monkeypatch,
        model=FakeModel(fail_preflight=True),
    )

    with pytest.raises(ValueError, match="inventory"):
        run_live(live, tmp_path)

    assert model.preflight_calls == 1
    assert model.received_inputs == []


def test_missing_provider_version_blocks_before_inference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, model, _ = configure(
        monkeypatch,
        model=FakeModel(provider_version=""),
    )

    with pytest.raises(ValueError, match="provider version"):
        run_live(live, tmp_path)

    assert model.provider_version_calls == 1
    assert model.preflight_calls == 0
    assert model.received_inputs == []


def test_raw_is_durable_before_interpretation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, _, _ = configure(monkeypatch)
    original_validate = live._comparison._exp18_runner._validate_schema
    evidence = tmp_path / "bc001-staging"
    validation_count = 0

    def validate(instance: object, schema: dict) -> None:
        nonlocal validation_count
        if validation_count == 0:
            assert (
                evidence / "attempts" / "bc-001-s12-run-1.raw.json"
            ).exists()
        validation_count += 1
        original_validate(instance, schema)

    monkeypatch.setattr(
        live._comparison._exp18_runner,
        "_validate_schema",
        validate,
    )
    run_live(live, tmp_path)

    assert validation_count > 0


def test_prior_raw_survives_later_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, _, _ = configure(
        monkeypatch,
        model=FakeModel(failing_call=2),
    )

    run_live(live, tmp_path)

    attempts = tmp_path / "bc001-staging" / "attempts"
    first_raw = json.loads(
        (attempts / "bc-001-s12-run-1.raw.json").read_text()
    )
    failed_raw = json.loads(
        (attempts / "bc-001-s12-run-2.raw.json").read_text()
    )
    assert first_raw["raw_model_response"]
    assert failed_raw["raw_model_response"] is None
    assert "synthetic provider failure" in failed_raw["provider_failure"]


def test_existing_or_repository_evidence_target_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, model, _ = configure(monkeypatch)
    existing = tmp_path / "existing"
    existing.mkdir()

    with pytest.raises(ValueError, match="already exists"):
        live.run_bc001_live_evaluation(ROOT, evidence_directory=existing)
    with pytest.raises(ValueError, match="outside"):
        live.run_bc001_live_evaluation(
            ROOT,
            evidence_directory=ROOT / "bc001-evidence",
        )

    assert model.preflight_calls == 0
    assert model.received_inputs == []


def test_duplicate_attempt_event_cannot_overwrite_first_record(
    tmp_path: Path,
) -> None:
    live = live_module()
    target = tmp_path / "attempt.raw.json"
    first = {"event_type": "RAW", "raw_model_response": "first"}
    duplicate = {"event_type": "RAW", "raw_model_response": "duplicate"}

    live._write_immutable_attempt_json(target, first)
    with pytest.raises(ValueError, match="already exists"):
        live._write_immutable_attempt_json(target, duplicate)

    assert json.loads(target.read_text()) == first
