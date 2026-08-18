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
EVALUATED_REVISION = "0123456789abcdef0123456789abcdef01234567"
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


def live_evaluation_module() -> ModuleType:
    module_name = "governed_agent_runtime.exp18_1a_live_evaluation"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        pytest.fail(
            f"missing Exp 18.1A live evaluation boundary: {module_name}",
            pytrace=False,
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


class GitBoundaryStub:
    def __init__(self, *, clean: bool) -> None:
        self.clean = clean
        self.calls: list[tuple[str, Path]] = []

    def is_clean(self, project_root: Path) -> bool:
        self.calls.append(("is_clean", project_root))
        return self.clean

    def resolve_head(self, project_root: Path) -> str:
        self.calls.append(("resolve_head", project_root))
        return EVALUATED_REVISION


class FakeModel:
    def __init__(self, *, failing_call: int | None = None) -> None:
        self.model_identity = "qwen3.8:27b"
        self.invocation_parameters = deepcopy(CANONICAL_PARAMETERS)
        self.failing_call = failing_call
        self.received_inputs: list[str] = []
        self.last_response_metadata: dict | None = None

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
            "prompt_eval_count": 4000 + call_index,
            "eval_count": 40 + call_index,
        }
        return json.dumps(
            {
                "schema_version": "0.1.0",
                "proposal_id": f"proposal-live-{call_index:03d}",
                "proposal_type": "STOP_OR_ESCALATE",
                "rationale": "Return one bounded result without execution.",
                "payload": {
                    "outcome": "SAFE_FALLBACK",
                    "summary": "Stop after the single measured proposal.",
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )


class ModelFactorySpy:
    def __init__(self, model: FakeModel) -> None:
        self.model = model
        self.calls: list[dict] = []

    def __call__(self, **configuration: object) -> FakeModel:
        self.calls.append(deepcopy(configuration))
        return self.model


class WarmUpSpy:
    def __init__(self) -> None:
        self.calls: list[FakeModel] = []

    def __call__(self, model: FakeModel) -> None:
        self.calls.append(model)


class CheckpointingRunnerStub:
    """Exercise the harness checkpoint seam without real provider access."""

    def __init__(self) -> None:
        self.revisions: list[str] = []

    def __call__(
        self,
        project_root: Path,
        *,
        model: FakeModel,
        warm_up: WarmUpSpy,
        evaluated_revision: str,
        attempt_completed: object,
    ) -> dict:
        self.revisions.append(evaluated_revision)
        warm_up(model)
        records = []
        for case_key in CASES:
            context = load_exp18_1a_context(project_root, case_key)
            serialized_input = assemble_llm_probe_input(project_root, context)
            for run_index in (1, 2, 3):
                try:
                    raw_response = model(serialized_input)
                except RuntimeError as error:
                    record = {
                        "status": "MODEL_ERROR",
                        "error": str(error),
                        "raw_model_response": None,
                        "provider_metadata": None,
                    }
                else:
                    record = {
                        "status": "COMPLETED",
                        "error": None,
                        "raw_model_response": raw_response,
                        "provider_metadata": deepcopy(
                            model.last_response_metadata
                        ),
                    }
                record.update(
                    {
                        "case_key": case_key,
                        "run_index": run_index,
                        "serialized_model_input": serialized_input,
                        "model_identity": model.model_identity,
                        "invocation_parameters": deepcopy(
                            model.invocation_parameters
                        ),
                    }
                )
                records.append(record)
                attempt_completed(record)
        return {
            "evaluated_revision": evaluated_revision,
            "measured_runs": records,
        }


def run_live(
    tmp_path: Path,
    *,
    git: GitBoundaryStub,
    model: FakeModel | None = None,
    measured_runner: object | None = None,
) -> tuple[dict, FakeModel, ModelFactorySpy, WarmUpSpy]:
    live = live_evaluation_module()
    selected_model = model or FakeModel()
    model_factory = ModelFactorySpy(selected_model)
    warm_up = WarmUpSpy()
    result = live.run_exp18_1a_live_evaluation(
        ROOT,
        evidence_directory=tmp_path / "exp18-1a-evidence",
        base_url="http://127.0.0.1:11434",
        request_timeout_seconds=600,
        git_boundary=git,
        model_factory=model_factory,
        warm_up=warm_up,
        measured_runner=measured_runner or CheckpointingRunnerStub(),
    )
    return result, selected_model, model_factory, warm_up


def test_dirty_repository_aborts_before_model_construction_or_warm_up(
    tmp_path: Path,
) -> None:
    live = live_evaluation_module()
    git = GitBoundaryStub(clean=False)
    model_factory = ModelFactorySpy(FakeModel())
    warm_up = WarmUpSpy()

    with pytest.raises(ValueError, match="clean"):
        live.run_exp18_1a_live_evaluation(
            ROOT,
            evidence_directory=tmp_path / "evidence",
            base_url="http://127.0.0.1:11434",
            request_timeout_seconds=600,
            git_boundary=git,
            model_factory=model_factory,
            warm_up=warm_up,
            measured_runner=CheckpointingRunnerStub(),
        )

    assert git.calls == [("is_clean", ROOT)]
    assert model_factory.calls == []
    assert warm_up.calls == []


def test_repository_evidence_directory_aborts_before_model_construction() -> None:
    live = live_evaluation_module()
    git = GitBoundaryStub(clean=True)
    model_factory = ModelFactorySpy(FakeModel())

    with pytest.raises(ValueError, match="outside"):
        live.run_exp18_1a_live_evaluation(
            ROOT,
            evidence_directory=ROOT / "live-evidence",
            base_url="http://127.0.0.1:11434",
            request_timeout_seconds=600,
            git_boundary=git,
            model_factory=model_factory,
            warm_up=WarmUpSpy(),
            measured_runner=CheckpointingRunnerStub(),
        )

    assert model_factory.calls == []


def test_live_run_binds_clean_head_canonical_model_and_manifest(
    tmp_path: Path,
) -> None:
    result, model, model_factory, warm_up = run_live(
        tmp_path,
        git=GitBoundaryStub(clean=True),
    )
    evidence = tmp_path / "exp18-1a-evidence"

    assert result["evaluated_revision"] == EVALUATED_REVISION
    assert len(warm_up.calls) == 1
    assert len(model.received_inputs) == 15
    assert model_factory.calls == [
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
            "keep_alive": "10m",
            "request_timeout_seconds": 600,
        }
    ]

    manifest = json.loads((evidence / "manifest.json").read_text())
    assert manifest["evaluated_revision"] == EVALUATED_REVISION
    assert manifest["selected_cases"] == list(CASES)
    assert manifest["runs_per_case"] == 3
    assert manifest["expected_measured_call_count"] == 15
    assert manifest["model_identity"] == "qwen3.8:27b"
    assert manifest["invocation_parameters"] == CANONICAL_PARAMETERS
    assert manifest["run_id"]

    for serialized_input in model.received_inputs:
        envelope = json.loads(serialized_input)
        assert HIDDEN_KEYS.isdisjoint(collect_keys(envelope))
        assert set(envelope) == {
            "instructions",
            "context_package",
            "model_proposal_schema",
        }


def test_raw_checkpoint_survives_post_response_validation_failure(
    tmp_path: Path,
) -> None:
    class ValidationFailureRunner:
        def __call__(
            self,
            project_root: Path,
            *,
            model: FakeModel,
            warm_up: WarmUpSpy,
            evaluated_revision: str,
            attempt_completed: object,
        ) -> dict:
            del evaluated_revision, attempt_completed
            warm_up(model)
            context = load_exp18_1a_context(project_root, "s02")
            model(assemble_llm_probe_input(project_root, context))
            raise RuntimeError("synthetic post-response validation failure")

    with pytest.raises(RuntimeError, match="post-response validation"):
        run_live(
            tmp_path,
            git=GitBoundaryStub(clean=True),
            measured_runner=ValidationFailureRunner(),
        )

    raw_path = (
        tmp_path
        / "exp18-1a-evidence"
        / "attempts"
        / "s02-run-1.raw.json"
    )
    raw = json.loads(raw_path.read_text())
    assert raw["evaluated_revision"] == EVALUATED_REVISION
    assert raw["case_key"] == "s02"
    assert raw["run_index"] == 1
    assert raw["raw_model_response"]
    assert raw["provider_failure"] is None
    assert raw["provider_metadata"]["done_reason"] == "stop"
    assert not raw_path.with_name("s02-run-1.result.json").exists()


def test_completed_checkpoints_survive_a_later_provider_failure(
    tmp_path: Path,
) -> None:
    result, _, _, _ = run_live(
        tmp_path,
        git=GitBoundaryStub(clean=True),
        model=FakeModel(failing_call=4),
    )
    attempts = tmp_path / "exp18-1a-evidence" / "attempts"

    assert len(result["measured_runs"]) == 15
    assert len(list(attempts.glob("*.raw.json"))) == 15
    assert len(list(attempts.glob("*.result.json"))) == 15
    assert (attempts / "s02-run-1.raw.json").exists()
    assert (attempts / "s02-run-1.result.json").exists()
    failed_raw = json.loads(
        (attempts / "s07-run-2.raw.json").read_text()
    )
    assert failed_raw["raw_model_response"] is None
    assert "synthetic provider failure" in failed_raw["provider_failure"]


def test_each_enriched_checkpoint_retains_revision_and_exact_raw_evidence(
    tmp_path: Path,
) -> None:
    result, model, _, _ = run_live(
        tmp_path,
        git=GitBoundaryStub(clean=True),
    )
    attempts = tmp_path / "exp18-1a-evidence" / "attempts"

    for call_index, record in enumerate(result["measured_runs"]):
        stem = f"{record['case_key']}-run-{record['run_index']}"
        raw = json.loads((attempts / f"{stem}.raw.json").read_text())
        enriched = json.loads(
            (attempts / f"{stem}.result.json").read_text()
        )
        assert raw["evaluated_revision"] == EVALUATED_REVISION
        assert raw["serialized_model_input"] == model.received_inputs[call_index]
        assert raw["raw_model_response"] == record["raw_model_response"]
        assert enriched["evaluated_revision"] == EVALUATED_REVISION
        assert enriched["case_key"] == record["case_key"]
        assert enriched["run_index"] == record["run_index"]
        assert enriched["serialized_model_input"] == raw[
            "serialized_model_input"
        ]
        assert enriched["raw_model_response"] == raw["raw_model_response"]
