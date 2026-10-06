"""Prospective BC-005-D1 diagnostic, isolated from the canonical baseline."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from governed_agent_runtime import bc005_live_evaluation as live
from governed_agent_runtime import bc005_s12_prospective_grounded as probe
from governed_agent_runtime.bc001_live_evaluation import _run_required_verification
from governed_agent_runtime.exp18_1a_live_evaluation import _SubprocessGitBoundary
from governed_agent_runtime.ollama_model_adapter import OllamaChatModel

SELF_REVIEW_INSTRUCTION = (
    "Before returning your final proposal, review the entire plan against all supplied "
    "facts, constraints, and dependencies. Verify that each action's preconditions are "
    "satisfied when that action would be performed and that the action order does not "
    "violate any constraint. Do not treat a planned action as already completed or its "
    "outcome as confirmed. Correct any contradictions before answering."
)

def assemble_diagnostic_input(root: Path) -> str:
    original = probe.assemble_llm_probe_input(root, probe.load_bc005_context(root))
    envelope = json.loads(original)
    envelope["final_review_instruction"] = SELF_REVIEW_INSTRUCTION
    return json.dumps(envelope, separators=(",", ":"))


def _baseline_manifest(root: Path) -> dict[str, Any]:
    path = root / "evidence/bc-005-s12-prospective-grounded-assessment/manifest.json"
    manifest = json.loads(path.read_text())
    paths = {
        "model_context": "fixtures/model-context/bc-005/s12/context-package.json",
        "hidden_evaluator": "evals/hidden/bc-005/s12/evaluation-case.json",
        "traceability_bundle": "evals/traceability/bc-005/s12/traceability.json",
    }
    for key, name in paths.items():
        if live._sha256_file(root / name) != manifest["prospective_artifact_sha256"][key]:
            raise ValueError(f"BC-005 baseline artifact drift: {key}")
    schema = manifest["model_proposal_schema"]
    if live._sha256_file(root / schema["path"]) != schema["sha256"]:
        raise ValueError("BC-005 proposal schema drift")
    original = probe.assemble_llm_probe_input(root, probe.load_bc005_context(root))
    if hashlib.sha256(original.encode()).hexdigest() != manifest["serialized_model_input_sha256"]:
        raise ValueError("BC-005 baseline input drift")
    return manifest


def run_diagnostic(
    project_root: Path,
    *,
    evidence_directory: Path,
    approved_revision: str,
    human_pre_run_approved: bool,
    base_url: str = "http://127.0.0.1:11434",
) -> dict[str, Any]:
    """Run the one fixed D1 pool, without modifying canonical BC-005 artifacts."""
    root = project_root.resolve()
    target = evidence_directory.resolve()
    live._validate_evidence_target(root, target)
    if not human_pre_run_approved:
        raise ValueError("BC-005-D1 human pre-run approval required")
    git = _SubprocessGitBoundary()
    revision = git.resolve_head(root)
    if not git.is_clean(root) or not revision or revision != approved_revision:
        raise ValueError("BC-005-D1 requires clean exact approved revision")
    baseline = _baseline_manifest(root)
    gate = probe.validate_bc005_pre_run_design(root)
    if not gate["gate_pass"]:
        raise ValueError("BC-005-D1 traceability gate must PASS")
    verification = _run_required_verification(root)
    if verification.get("status") != "PASSED":
        raise ValueError("BC-005-D1 verification failed")
    if not git.is_clean(root) or git.resolve_head(root) != revision:
        raise ValueError("BC-005-D1 checkout changed during verification")

    context = probe.load_bc005_context(root)
    serialized = assemble_diagnostic_input(root)
    input_hash = hashlib.sha256(serialized.encode()).hexdigest()
    contracts = probe._load_contracts(root)
    parameters = deepcopy(baseline["invocation_parameters"])
    stream = parameters.pop("stream")
    if stream is not False:
        raise ValueError("BC-005-D1 stream drift")
    model = OllamaChatModel(
        base_url=base_url,
        model_identity=baseline["model_identity"],
        model_schema=contracts["proposal_schema"],
        request_timeout_seconds=baseline["request_timeout_seconds"],
        **parameters,
    )
    probe._check_model_configuration(model)
    version = model.resolve_provider_version()
    digest = model.resolve_model_artifact_identity()
    model.model_artifact_identity = digest
    if version != baseline["provider"]["version"]:
        raise ValueError("BC-005-D1 provider version differs from baseline")
    if digest != baseline["model_artifact_identity"]:
        raise ValueError("BC-005-D1 model digest differs from baseline")

    (target / "preload").mkdir(parents=True)
    (target / "attempts").mkdir()
    expected = ["preload/bc-005-d1-s12-preload.raw.json"] + [
        f"attempts/bc-005-d1-s12-run-{i}.{suffix}.json"
        for i in (1, 2, 3) for suffix in ("raw", "result")
    ]
    manifest = {
        "experiment_id": "BC-005-D1",
        "bounded_change_id": "BC-005",
        "evidence_scope": "DIAGNOSTIC",
        "decision_evidence_eligible": False,
        "status": "RUNNING",
        "started_at": live._utc_now(),
        "evaluated_revision": revision,
        "approved_revision": approved_revision,
        "human_pre_run_approved": True,
        "baseline_evaluated_revision": baseline["evaluated_revision"],
        "baseline_input_sha256": baseline["serialized_model_input_sha256"],
        "baseline_artifact_sha256": baseline["prospective_artifact_sha256"],
        "model_proposal_schema": baseline["model_proposal_schema"],
        "serialized_model_input_sha256": input_hash,
        "final_review_instruction": SELF_REVIEW_INSTRUCTION,
        "provider": {"name": "Ollama", "version": version},
        "provider_endpoint": "/api/chat",
        "model_identity": model.model_identity,
        "model_artifact_identity": digest,
        "invocation_parameters": deepcopy(model.invocation_parameters),
        "request_timeout_seconds": model.request_timeout_seconds,
        "verification": verification,
        "traceability_gate": gate,
        "expected_measured_call_count": 3,
        "actual_measured_call_count": 0,
        "expected_evidence_files": expected,
        "written_evidence_files": [],
    }
    live._atomic_write_json(target / "manifest.json", manifest)

    def persist(event: dict[str, Any]) -> None:
        record = deepcopy(event)
        record.update(experiment_id="BC-005-D1", evidence_scope="DIAGNOSTIC",
                      decision_evidence_eligible=False)
        preload = record["attempt_kind"] == "PRELOAD"
        if preload:
            record["run_id"] = "bc-005-d1-s12-preload"
        suffix = "raw" if record["event_type"] == "RAW" else "result"
        directory = "preload" if preload else "attempts"
        relative = f"{directory}/{record['run_id']}.{suffix}.json"
        if relative not in expected:
            raise ValueError("Unexpected diagnostic evidence identity")
        live._write_immutable(target / relative, record)
        manifest["written_evidence_files"].append(relative)
        if not preload and suffix == "raw":
            manifest["actual_measured_call_count"] += 1
        live._atomic_write_json(target / "manifest.json", manifest)

    try:
        probe._run_preload(
            model=model, serialized_input=serialized, input_sha256=input_hash,
            evaluated_revision=revision, attempt_reporter=persist,
        )
        for i in (1, 2, 3):
            probe._exp18_runner._run_measured_attempt(
                project_root=root, case_key="s12", run_index=i, model=model,
                context_package=context, serialized_model_input=serialized,
                proposal_schema=contracts["proposal_schema"],
                runtime_decision_schema=contracts["runtime_decision_schema"],
                policy=contracts["policy"], tool_contracts=contracts["tool_contracts"],
                transition_spec=contracts["transition_spec"],
                evaluated_revision=revision, run_id_prefix="bc-005-d1-s12",
                attempt_reporter=probe._measured_reporter(
                    persist, model=model, input_sha256=input_hash,
                ),
                runtime_requires_valid_structure=True, include_case_in_run_id=False,
            )
        manifest.update(status="COMPLETED", completed_at=live._utc_now())
    except Exception as error:
        manifest.update(status="FAILED", failure_type=type(error).__name__, failure=str(error))
        raise
    finally:
        live._atomic_write_json(target / "manifest.json", manifest)
    return manifest
