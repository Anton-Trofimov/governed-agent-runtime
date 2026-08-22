"""Execute canonical BC-002 with concrete readiness and durable staging."""

import hashlib
import json
import platform
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from governed_agent_runtime import bc002_s12_chat_comparison as _comparison
from governed_agent_runtime.bc001_live_evaluation import (
    _run_required_verification,
)
from governed_agent_runtime.exp18_1a_live_evaluation import (
    _atomic_write_json,
    _SubprocessGitBoundary,
)
from governed_agent_runtime.ollama_model_adapter import OllamaChatModel

_MODEL_IDENTITY = "qwen3.8:27b"
_TIMEOUT = 300
_COMMON = {
    "temperature": 0.6,
    "seed": 18,
    "num_ctx": 8192,
    "num_predict": 2048,
    "stream": False,
    "keep_alive": "10m",
}
_BRANCHES = (("CONTROL", False), ("TREATMENT", True))
_RUN_IDS = tuple(
    f"bc-002-s12-{branch.lower()}-run-{index}"
    for branch, _ in _BRANCHES
    for index in (1, 2, 3)
)


def run_bc002_live_evaluation(
    project_root: Path,
    *,
    evidence_directory: Path,
    base_url: str = "http://127.0.0.1:11434",
) -> dict[str, Any]:
    """Run the fixed chat comparison after concrete readiness checks."""
    project_root = project_root.resolve()
    evidence_directory = evidence_directory.resolve()
    _validate_evidence_target(project_root, evidence_directory)

    git = _SubprocessGitBoundary()
    if not git.is_clean(project_root):
        raise ValueError("BC-002 live evaluation requires a clean worktree")
    evaluated_revision = git.resolve_head(project_root)
    if not evaluated_revision:
        raise ValueError("BC-002 evaluated revision must be non-empty")
    verification = _run_required_verification(project_root)
    if verification.get("status") != "PASSED":
        raise RuntimeError("BC-002 required verification did not pass")
    if not git.is_clean(project_root):
        raise ValueError("BC-002 worktree changed during verification")
    if git.resolve_head(project_root) != evaluated_revision:
        raise ValueError("BC-002 revision changed during verification")

    context = _comparison.load_exp18_1a_context(project_root, "s12")
    serialized_input = _comparison.assemble_llm_probe_input(project_root, context)
    input_sha256 = hashlib.sha256(serialized_input.encode("utf-8")).hexdigest()
    proposal_schema_path = project_root / "schemas/model-proposal.schema.json"
    proposal_schema_bytes = proposal_schema_path.read_bytes()
    proposal_schema = json.loads(proposal_schema_bytes)
    proposal_schema_sha256 = hashlib.sha256(
        proposal_schema_bytes
    ).hexdigest()
    models = {
        branch: OllamaChatModel(
            base_url=base_url,
            model_identity=_MODEL_IDENTITY,
            model_schema=proposal_schema,
            temperature=_COMMON["temperature"],
            seed=_COMMON["seed"],
            num_ctx=_COMMON["num_ctx"],
            num_predict=_COMMON["num_predict"],
            think=think,
            keep_alive=_COMMON["keep_alive"],
            request_timeout_seconds=_TIMEOUT,
        )
        for branch, think in _BRANCHES
    }
    provider_version = models["CONTROL"].resolve_provider_version()

    (evidence_directory / "preload").mkdir(parents=True)
    (evidence_directory / "attempts").mkdir()
    manifest_path = evidence_directory / "manifest.json"
    manifest = _initial_manifest(
        evaluated_revision=evaluated_revision,
        verification=verification,
        input_sha256=input_sha256,
        provider_version=provider_version,
        proposal_schema_sha256=proposal_schema_sha256,
    )
    _atomic_write_json(manifest_path, manifest)

    def report_attempt(event: dict[str, Any]) -> None:
        relative_path = _event_path(event)
        _write_immutable(evidence_directory / relative_path, event)
        manifest["written_evidence_files"].append(relative_path.as_posix())
        artifact = event.get("model_artifact_identity")
        if artifact:
            manifest["model_artifact_identity"] = artifact
        _atomic_write_json(manifest_path, manifest)

    try:
        result = _comparison.run_bc002_canonical_comparison(
            project_root,
            control_model=models["CONTROL"],
            treatment_model=models["TREATMENT"],
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
                "model_artifact_identity": models[
                    "CONTROL"
                ].model_artifact_identity,
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


def _validate_evidence_target(project_root: Path, target: Path) -> None:
    if target == project_root or target.is_relative_to(project_root):
        raise ValueError("evidence_directory must be outside the repository")
    if target.exists():
        raise ValueError("evidence_directory already exists")


def _initial_manifest(
    *,
    evaluated_revision: str,
    verification: dict[str, Any],
    input_sha256: str,
    provider_version: str,
    proposal_schema_sha256: str,
) -> dict[str, Any]:
    expected_files = []
    for branch, think in _BRANCHES:
        branch_name = branch.lower()
        expected_files.append(
            f"preload/bc-002-s12-{branch_name}-preload.raw.json"
        )
        expected_files.extend(
            f"attempts/bc-002-s12-{branch_name}-run-{index}.{suffix}.json"
            for index in (1, 2, 3)
            for suffix in ("raw", "result")
        )
    return {
        "bounded_change_id": "BC-002",
        "run_id": f"bc-002-{uuid4()}",
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
        "provider": {"name": "Ollama", "version": provider_version},
        "provider_endpoint": "/api/chat",
        "model_identity": _MODEL_IDENTITY,
        "model_artifact_identity": None,
        "serialized_model_input_sha256": input_sha256,
        "model_proposal_schema": {
            "path": "schemas/model-proposal.schema.json",
            "sha256": proposal_schema_sha256,
        },
        "request_timeout_seconds": _TIMEOUT,
        "branches": {
            branch: {
                "think": think,
                "invocation_parameters": {**_COMMON, "think": think},
                "preload_run_id": (
                    f"bc-002-s12-{branch.lower()}-preload"
                ),
                "preload_included_in_measured_runs": False,
                "measured_run_ids": [
                    f"bc-002-s12-{branch.lower()}-run-{index}"
                    for index in (1, 2, 3)
                ],
            }
            for branch, think in _BRANCHES
        },
        "expected_measured_call_count": 6,
        "measured_run_ids": list(_RUN_IDS),
        "expected_evidence_files": expected_files,
        "written_evidence_files": [],
    }


def _event_path(event: dict[str, Any]) -> Path:
    if event.get("bounded_change_id") != "BC-002":
        raise ValueError("Attempt does not belong to BC-002")
    if event.get("evidence_scope") != "CANONICAL_DECISION":
        raise ValueError("Non-canonical evidence cannot enter canonical staging")
    run_id = event.get("run_id")
    branch = event.get("branch")
    if branch not in ("CONTROL", "TREATMENT"):
        raise ValueError("BC-002 attempt branch is invalid")
    expected_preload = f"bc-002-s12-{branch.lower()}-preload"
    if event.get("attempt_kind") == "PRELOAD":
        if event.get("decision_evidence_eligible") is not False:
            raise ValueError("BC-002 preload cannot be decision evidence")
        if event.get("event_type") != "RAW" or run_id != expected_preload:
            raise ValueError("Unexpected BC-002 preload event")
        return Path("preload") / f"{run_id}.raw.json"
    if event.get("attempt_kind") == "MEASURED" and run_id in _RUN_IDS:
        if event.get("decision_evidence_eligible") is not True:
            raise ValueError("BC-002 measured evidence must be eligible")
        event_type = event.get("event_type")
        if event_type == "RAW":
            suffix = "raw"
        elif event_type == "RESULT":
            suffix = "result"
        else:
            raise ValueError("Unsupported BC-002 measured event")
        return Path("attempts") / f"{run_id}.{suffix}.json"
    raise ValueError("Unsupported BC-002 attempt metadata")


def _write_immutable(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise ValueError(f"Canonical evidence file already exists: {path}")
    _atomic_write_json(path, value)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
