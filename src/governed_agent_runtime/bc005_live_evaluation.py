"""Execute canonical BC-005 with verification and durable evidence staging."""

import hashlib
import json
import platform
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from governed_agent_runtime import bc005_s12_prospective_grounded as _probe
from governed_agent_runtime.bc001_live_evaluation import _run_required_verification
from governed_agent_runtime.exp18_1a_live_evaluation import (
    _atomic_write_json,
    _SubprocessGitBoundary,
)
from governed_agent_runtime.ollama_model_adapter import OllamaChatModel

_MODEL_IDENTITY = "qwen3.8:27b"
_TIMEOUT = 300
_PARAMETERS = {
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
_MEASURED_RUN_IDS = tuple(f"bc-005-s12-run-{index}" for index in (1, 2, 3))


def run_bc005_live_evaluation(
    project_root: Path,
    *,
    evidence_directory: Path,
    human_pre_run_approved: bool,
    approved_revision: str,
    base_url: str = "http://127.0.0.1:11434",
) -> dict[str, Any]:
    """Run the fixed BC-005 probe after all blocking pre-run gates."""
    project_root = project_root.resolve()
    evidence_directory = evidence_directory.resolve()
    _validate_evidence_target(project_root, evidence_directory)

    design_gate = _probe.validate_bc005_pre_run_design(project_root)
    if not design_gate["gate_pass"]:
        raise ValueError("BC-005 traceability gate must PASS before live evaluation")
    if not human_pre_run_approved:
        raise ValueError("BC-005 human pre-run checkpoint has not been approved")

    git = _SubprocessGitBoundary()
    if not git.is_clean(project_root):
        raise ValueError("BC-005 live evaluation requires a clean worktree")
    evaluated_revision = git.resolve_head(project_root)
    if not evaluated_revision:
        raise ValueError("BC-005 evaluated revision must be non-empty")
    if approved_revision != evaluated_revision:
        raise ValueError("BC-005 human approval is not bound to the evaluated revision")

    verification = _run_required_verification(project_root)
    if verification.get("status") != "PASSED":
        raise RuntimeError("BC-005 required verification did not pass")
    if not git.is_clean(project_root):
        raise ValueError("BC-005 worktree changed during verification")
    if git.resolve_head(project_root) != evaluated_revision:
        raise ValueError("BC-005 revision changed during verification")

    context = _probe.load_bc005_context(project_root)
    serialized_input = _probe.assemble_llm_probe_input(project_root, context)
    input_sha256 = hashlib.sha256(serialized_input.encode("utf-8")).hexdigest()

    schema_path = project_root / "schemas/model-proposal.schema.json"
    schema_bytes = schema_path.read_bytes()
    schema = json.loads(schema_bytes)
    schema_sha256 = hashlib.sha256(schema_bytes).hexdigest()

    artifact_hashes = {
        "model_context": _sha256_file(
            project_root / "fixtures/model-context/bc-005/s12/context-package.json"
        ),
        "hidden_evaluator": _sha256_file(
            project_root / "evals/hidden/bc-005/s12/evaluation-case.json"
        ),
        "traceability_bundle": _sha256_file(
            project_root / "evals/traceability/bc-005/s12/traceability.json"
        ),
    }

    model = OllamaChatModel(
        base_url=base_url,
        model_identity=_MODEL_IDENTITY,
        model_schema=schema,
        temperature=_PARAMETERS["temperature"],
        top_p=_PARAMETERS["top_p"],
        top_k=_PARAMETERS["top_k"],
        min_p=_PARAMETERS["min_p"],
        presence_penalty=_PARAMETERS["presence_penalty"],
        repeat_penalty=_PARAMETERS["repeat_penalty"],
        seed=_PARAMETERS["seed"],
        num_ctx=_PARAMETERS["num_ctx"],
        num_predict=_PARAMETERS["num_predict"],
        think=_PARAMETERS["think"],
        keep_alive=_PARAMETERS["keep_alive"],
        request_timeout_seconds=_TIMEOUT,
    )
    provider_version = model.resolve_provider_version()

    (evidence_directory / "preload").mkdir(parents=True)
    (evidence_directory / "attempts").mkdir()
    manifest_path = evidence_directory / "manifest.json"
    manifest = _initial_manifest(
        evaluated_revision=evaluated_revision,
        verification=verification,
        input_sha256=input_sha256,
        provider_version=provider_version,
        schema_sha256=schema_sha256,
        design_gate=design_gate,
        artifact_hashes=artifact_hashes,
        approved_revision=approved_revision,
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
        result = _probe.run_bc005_first_step(
            project_root,
            model=model,
            git_boundary=git,
            attempt_reporter=report_attempt,
            required_verification_passed=True,
            human_pre_run_approved=True,
            approved_revision=approved_revision,
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
            "generation_budget_diagnostics": [
                run["generation_budget_diagnostics"]
                for run in result["measured_runs"]
            ],
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
    schema_sha256: str,
    design_gate: dict[str, Any],
    artifact_hashes: dict[str, str],
    approved_revision: str,
) -> dict[str, Any]:
    expected_files = ["preload/bc-005-s12-preload.raw.json"]
    expected_files.extend(
        f"attempts/{run_id}.{suffix}.json"
        for run_id in _MEASURED_RUN_IDS
        for suffix in ("raw", "result")
    )
    return {
        "bounded_change_id": "BC-005",
        "run_id": f"bc-005-{uuid4()}",
        "status": "RUNNING",
        "started_at": _utc_now(),
        "evidence_scope": "CANONICAL_DECISION",
        "decision_evidence_eligible": True,
        "evaluated_revision": evaluated_revision,
        "human_pre_run_approved": True,
        "approved_revision": approved_revision,
        "verification": deepcopy(verification),
        "traceability_gate": deepcopy(design_gate),
        "prospective_artifact_sha256": deepcopy(artifact_hashes),
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
            "sha256": schema_sha256,
        },
        "invocation_parameters": deepcopy(_PARAMETERS),
        "request_timeout_seconds": _TIMEOUT,
        "preload": {
            "run_id": "bc-005-s12-preload",
            "included_in_measured_runs": False,
        },
        "expected_measured_call_count": 3,
        "measured_run_ids": list(_MEASURED_RUN_IDS),
        "expected_evidence_files": expected_files,
        "written_evidence_files": [],
        "post_run_budget_review_required": True,
    }


def _event_path(event: dict[str, Any]) -> Path:
    if event.get("bounded_change_id") != "BC-005":
        raise ValueError("Attempt does not belong to BC-005")
    if event.get("evidence_scope") != "CANONICAL_DECISION":
        raise ValueError("Non-canonical evidence cannot enter canonical staging")
    run_id = event.get("run_id")
    if event.get("attempt_kind") == "PRELOAD":
        if (
            run_id != "bc-005-s12-preload"
            or event.get("event_type") != "RAW"
            or event.get("decision_evidence_eligible") is not False
        ):
            raise ValueError("Unexpected BC-005 preload event")
        return Path("preload") / f"{run_id}.raw.json"
    if event.get("attempt_kind") == "MEASURED" and run_id in _MEASURED_RUN_IDS:
        if event.get("decision_evidence_eligible") is not True:
            raise ValueError("BC-005 measured evidence must be eligible")
        event_type = event.get("event_type")
        if event_type == "RAW":
            suffix = "raw"
        elif event_type == "RESULT":
            suffix = "result"
        else:
            raise ValueError("Unsupported BC-005 measured event")
        return Path("attempts") / f"{run_id}.{suffix}.json"
    raise ValueError("Unsupported BC-005 attempt metadata")


def _write_immutable(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise ValueError(f"Canonical evidence file already exists: {path}")
    _atomic_write_json(path, value)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
