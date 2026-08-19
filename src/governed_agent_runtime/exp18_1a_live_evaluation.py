"""Run Exp 18.1A against Ollama while durably capturing raw evidence."""

import json
import os
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from governed_agent_runtime.exp18_1a_measured_runner import (
    run_exp18_1a_measured_evaluation,
)
from governed_agent_runtime.ollama_model_adapter import OllamaGenerateModel

_CASES = ("s02", "s07", "s08a", "s08b", "s12")
_RUNS_PER_CASE = 3
_EXPECTED_ATTEMPTS = 15
_MODEL_IDENTITY = "qwen3.8:27b"
_REQUEST_TIMEOUT_SECONDS = 300
_INVOCATION_PARAMETERS = {
    "temperature": 0,
    "seed": 18,
    "num_ctx": 8192,
    "num_predict": 2048,
    "think": False,
    "stream": False,
    "keep_alive": "10m",
}


class _GitBoundary(Protocol):
    def is_clean(self, project_root: Path) -> bool: ...

    def resolve_head(self, project_root: Path) -> str: ...


class _SubprocessGitBoundary:
    def is_clean(self, project_root: Path) -> bool:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return not result.stdout.strip()

    def resolve_head(self, project_root: Path) -> str:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()


def run_exp18_1a_live_evaluation(
    project_root: Path,
    *,
    evidence_directory: Path,
    base_url: str = "http://127.0.0.1:11434",
    request_timeout_seconds: float = _REQUEST_TIMEOUT_SECONDS,
    git_boundary: _GitBoundary | None = None,
    model_factory: Callable[..., Any] = OllamaGenerateModel,
    warm_up: Callable[[Any], None] | None = None,
    measured_runner: Callable[..., dict[str, Any]] = (
        run_exp18_1a_measured_evaluation
    ),
) -> dict[str, Any]:
    """Execute the fixed live probe and checkpoint each lifecycle event."""
    project_root = project_root.resolve()
    git = git_boundary or _SubprocessGitBoundary()
    if not git.is_clean(project_root):
        raise ValueError("Exp 18.1A live evaluation requires a clean worktree")
    evaluated_revision = git.resolve_head(project_root)

    evidence_directory = evidence_directory.resolve()
    if evidence_directory == project_root or evidence_directory.is_relative_to(
        project_root
    ):
        raise ValueError("evidence_directory must be outside the repository")
    if request_timeout_seconds != _REQUEST_TIMEOUT_SECONDS:
        raise ValueError("Exp 18.1A request timeout must be 300 seconds")

    attempts_directory = evidence_directory / "attempts"
    attempts_directory.mkdir(parents=True, exist_ok=True)
    proposal_schema = _load_json(
        project_root / "schemas/model-proposal.schema.json"
    )
    model = model_factory(
        base_url=base_url,
        model_identity=_MODEL_IDENTITY,
        model_schema=proposal_schema,
        temperature=_INVOCATION_PARAMETERS["temperature"],
        seed=_INVOCATION_PARAMETERS["seed"],
        num_ctx=_INVOCATION_PARAMETERS["num_ctx"],
        num_predict=_INVOCATION_PARAMETERS["num_predict"],
        keep_alive=_INVOCATION_PARAMETERS["keep_alive"],
        request_timeout_seconds=request_timeout_seconds,
    )

    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    run_id = f"exp-18-1a-{uuid4()}"
    _atomic_write_json(
        evidence_directory / "manifest.json",
        {
            "experiment_id": "exp-18-1a",
            "run_id": run_id,
            "started_at": started_at,
            "evaluated_revision": evaluated_revision,
            "selected_cases": list(_CASES),
            "runs_per_case": _RUNS_PER_CASE,
            "expected_attempts": _EXPECTED_ATTEMPTS,
            "expected_measured_call_count": _EXPECTED_ATTEMPTS,
            "model_identity": _MODEL_IDENTITY,
            "invocation_parameters": _INVOCATION_PARAMETERS,
            "request_timeout_seconds": _REQUEST_TIMEOUT_SECONDS,
        },
    )

    def report_attempt(event: dict[str, Any]) -> None:
        event_type = event.get("event_type")
        if event_type == "RAW":
            suffix = "raw"
        elif event_type == "ENRICHED":
            suffix = "result"
        else:
            raise ValueError(f"Unsupported attempt event type: {event_type!r}")
        filename = f"{event['case_key']}-run-{event['run_index']}.{suffix}.json"
        _atomic_write_json(attempts_directory / filename, event)

    return measured_runner(
        project_root,
        model=model,
        warm_up=warm_up or _warm_up_model,
        evaluated_revision=evaluated_revision,
        attempt_reporter=report_attempt,
    )


def _warm_up_model(model: Callable[[str], str]) -> None:
    model("")


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(
                value,
                temporary_file,
                sort_keys=True,
                separators=(",", ":"),
            )
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
