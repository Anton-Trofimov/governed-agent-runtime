"""Execute canonical BC-001 with concrete readiness and durable staging."""

import hashlib
import json
import platform
import subprocess
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from governed_agent_runtime import (
    bc001_s12_reasoning_comparison as _comparison,
)
from governed_agent_runtime.exp18_1a_live_evaluation import (
    _atomic_write_json,
    _SubprocessGitBoundary,
)
from governed_agent_runtime.ollama_model_adapter import OllamaGenerateModel

_MODEL_IDENTITY = "qwen3.8:27b"
_REQUEST_TIMEOUT_SECONDS = 300
_INVOCATION_PARAMETERS = {
    "temperature": 0,
    "seed": 18,
    "num_ctx": 8192,
    "num_predict": 2048,
    "think": True,
    "stream": False,
    "keep_alive": "10m",
}
_MEASURED_RUN_IDS = tuple(
    f"bc-001-s12-run-{run_index}" for run_index in (1, 2, 3)
)


def run_bc001_live_evaluation(
    project_root: Path,
    *,
    evidence_directory: Path,
    base_url: str = "http://127.0.0.1:11434",
) -> dict[str, Any]:
    """Run the fixed canonical comparison after concrete readiness checks."""
    project_root = project_root.resolve()
    evidence_directory = evidence_directory.resolve()
    _validate_evidence_target(project_root, evidence_directory)

    git = _SubprocessGitBoundary()
    if not git.is_clean(project_root):
        raise ValueError("BC-001 live evaluation requires a clean worktree")
    evaluated_revision = git.resolve_head(project_root)
    if not evaluated_revision:
        raise ValueError("BC-001 evaluated revision must be non-empty")

    verification = _run_required_verification(project_root)
    if verification.get("status") != "PASSED":
        raise RuntimeError("BC-001 required verification did not pass")
    if not git.is_clean(project_root):
        raise ValueError("BC-001 worktree changed during verification")
    if git.resolve_head(project_root) != evaluated_revision:
        raise ValueError("BC-001 revision changed during verification")

    context = _comparison.load_exp18_1a_context(project_root, "s12")
    serialized_input = _comparison.assemble_llm_probe_input(
        project_root,
        context,
    )
    input_sha256 = hashlib.sha256(serialized_input.encode("utf-8")).hexdigest()
    if input_sha256 != _comparison._FROZEN_S12_INPUT_SHA256:
        raise ValueError("BC-001 frozen S12 input identity mismatch")
    proposal_schema = _load_json(
        project_root / "schemas/model-proposal.schema.json"
    )
    model = OllamaGenerateModel(
        base_url=base_url,
        model_identity=_MODEL_IDENTITY,
        model_schema=proposal_schema,
        temperature=_INVOCATION_PARAMETERS["temperature"],
        seed=_INVOCATION_PARAMETERS["seed"],
        num_ctx=_INVOCATION_PARAMETERS["num_ctx"],
        num_predict=_INVOCATION_PARAMETERS["num_predict"],
        think=_INVOCATION_PARAMETERS["think"],
        keep_alive=_INVOCATION_PARAMETERS["keep_alive"],
        request_timeout_seconds=_REQUEST_TIMEOUT_SECONDS,
    )
    provider_version = model.resolve_provider_version()

    preload_directory = evidence_directory / "preload"
    attempts_directory = evidence_directory / "attempts"
    preload_directory.mkdir(parents=True)
    attempts_directory.mkdir()
    manifest_path = evidence_directory / "manifest.json"
    manifest = _initial_manifest(
        evaluated_revision=evaluated_revision,
        verification=verification,
        input_sha256=input_sha256,
        provider_version=provider_version,
    )
    _atomic_write_json(manifest_path, manifest)

    def report_attempt(event: dict[str, Any]) -> None:
        relative_path = _event_path(event)
        _write_immutable_attempt_json(
            evidence_directory / relative_path,
            event,
        )
        manifest["written_evidence_files"].append(relative_path.as_posix())
        artifact_identity = event.get("model_artifact_identity")
        if artifact_identity:
            manifest["model_artifact_identity"] = artifact_identity
        _atomic_write_json(manifest_path, manifest)

    try:
        result = _comparison.run_bc001_canonical_comparison(
            project_root,
            model=model,
            git_boundary=git,
            attempt_reporter=report_attempt,
            required_verification_passed=True,
        )
    except Exception as error:
        manifest.update(
            {
                "status": "FAILED",
                "failure_type": type(error).__name__,
                "failure": str(error),
                "model_artifact_identity": model.model_artifact_identity,
            }
        )
        _atomic_write_json(manifest_path, manifest)
        raise

    manifest.update(
        {
            "status": "COMPLETED",
            "completed_at": _utc_now(),
            "model_artifact_identity": result["model_artifact_identity"],
            "actual_measured_call_count": len(result["measured_runs"]),
        }
    )
    _atomic_write_json(manifest_path, manifest)
    return result


def _validate_evidence_target(
    project_root: Path,
    evidence_directory: Path,
) -> None:
    if evidence_directory == project_root or evidence_directory.is_relative_to(
        project_root
    ):
        raise ValueError("evidence_directory must be outside the repository")
    if evidence_directory.exists():
        raise ValueError("evidence_directory already exists")


def _run_required_verification(project_root: Path) -> dict[str, Any]:
    commands = (
        ("git diff --check", ["git", "diff", "--check"]),
        (
            ".venv/bin/ruff check .",
            [str(project_root / ".venv/bin/ruff"), "check", "."],
        ),
        (
            ".venv/bin/pytest",
            [str(project_root / ".venv/bin/pytest")],
        ),
    )
    results: list[dict[str, Any]] = []
    for display, command in commands:
        completed = subprocess.run(
            command,
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        )
        result = {
            "command": display,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        results.append(result)
        if completed.returncode != 0:
            raise RuntimeError(f"Required verification failed: {display}")
    return {"status": "PASSED", "commands": results}


def _initial_manifest(
    *,
    evaluated_revision: str,
    verification: dict[str, Any],
    input_sha256: str,
    provider_version: str,
) -> dict[str, Any]:
    return {
        "bounded_change_id": "BC-001",
        "run_id": f"bc-001-{uuid4()}",
        "status": "RUNNING",
        "started_at": _utc_now(),
        "evidence_scope": "CANONICAL_DECISION",
        "decision_evidence_eligible": True,
        "evaluated_revision": evaluated_revision,
        "verification": deepcopy(verification),
        "python_runtime": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "provider": {
            "name": "Ollama",
            "version": provider_version,
        },
        "model_identity": _MODEL_IDENTITY,
        "model_artifact_identity": None,
        "frozen_baseline_digest_limitation": True,
        "serialized_model_input_sha256": input_sha256,
        "invocation_parameters": deepcopy(_INVOCATION_PARAMETERS),
        "request_timeout_seconds": _REQUEST_TIMEOUT_SECONDS,
        "preload": {
            "run_id": "bc-001-s12-preload",
            "included_in_measured_runs": False,
            "evidence_file": (
                "preload/bc-001-s12-preload.raw.json"
            ),
        },
        "expected_measured_call_count": 3,
        "measured_run_ids": list(_MEASURED_RUN_IDS),
        "expected_evidence_files": [
            "preload/bc-001-s12-preload.raw.json",
            *[
                f"attempts/{run_id}.{suffix}.json"
                for run_id in _MEASURED_RUN_IDS
                for suffix in ("raw", "result")
            ],
        ],
        "written_evidence_files": [],
    }


def _event_path(event: dict[str, Any]) -> Path:
    if event.get("bounded_change_id") != "BC-001":
        raise ValueError("Attempt does not belong to BC-001")
    if event.get("evidence_scope") != "CANONICAL_DECISION":
        raise ValueError("Non-canonical evidence cannot enter canonical staging")
    if event.get("decision_evidence_eligible") is not True:
        raise ValueError("Ineligible evidence cannot enter canonical staging")

    event_type = event.get("event_type")
    attempt_kind = event.get("attempt_kind")
    run_id = event.get("run_id")
    if attempt_kind == "PRELOAD" and event_type == "RAW":
        if run_id != "bc-001-s12-preload":
            raise ValueError("Unexpected BC-001 preload identity")
        return Path("preload") / f"{run_id}.raw.json"
    if attempt_kind == "MEASURED" and run_id in _MEASURED_RUN_IDS:
        if event_type == "RAW":
            suffix = "raw"
        elif event_type == "RESULT":
            suffix = "result"
        else:
            raise ValueError(f"Unsupported measured event: {event_type!r}")
        return Path("attempts") / f"{run_id}.{suffix}.json"
    raise ValueError("Unsupported BC-001 attempt metadata")


def _write_immutable_attempt_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    if path.exists():
        raise ValueError(f"Canonical evidence file already exists: {path}")
    _atomic_write_json(path, value)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
