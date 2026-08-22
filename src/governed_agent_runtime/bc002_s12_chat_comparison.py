"""Orchestrate the fixed BC-002 S12 chat-interface comparison."""

import hashlib
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any, Protocol

from governed_agent_runtime import exp18_1a_measured_runner as _exp18_runner
from governed_agent_runtime.exp18_1a_context_assembly import (
    assemble_llm_probe_input,
    load_exp18_1a_context,
)

_MODEL_IDENTITY = "qwen3.8:27b"
_REQUEST_TIMEOUT_SECONDS = 300
_RUN_INDEXES = (1, 2, 3)
_COMMON_PARAMETERS = {
    "temperature": 0.6,
    "seed": 18,
    "num_ctx": 8192,
    "num_predict": 2048,
    "stream": False,
    "keep_alive": "10m",
}


class _Model(Protocol):
    model_identity: str
    model_artifact_identity: str | None
    invocation_parameters: dict[str, Any]
    request_timeout_seconds: float
    provider_endpoint: str
    last_response_metadata: dict[str, Any] | None
    last_response_envelope: dict[str, Any] | None
    last_raw_response_body: str | None
    last_request_payload: dict[str, Any] | None

    def resolve_model_artifact_identity(self) -> str: ...

    def __call__(self, serialized_input: str) -> str: ...


class _GitBoundary(Protocol):
    def is_clean(self, project_root: Path) -> bool: ...

    def resolve_head(self, project_root: Path) -> str: ...


def run_bc002_canonical_comparison(
    project_root: Path,
    *,
    control_model: _Model,
    treatment_model: _Model,
    git_boundary: _GitBoundary,
    attempt_reporter: Callable[[dict[str, Any]], None],
    required_verification_passed: bool,
) -> dict[str, Any]:
    """Run the fixed control and treatment branches after readiness checks."""
    project_root = project_root.resolve()
    evaluated_revision = _check_repository_readiness(
        project_root,
        git_boundary=git_boundary,
        required_verification_passed=required_verification_passed,
    )
    _check_model_configuration(control_model, branch="CONTROL", think=False)
    _check_model_configuration(treatment_model, branch="TREATMENT", think=True)

    context_package = load_exp18_1a_context(project_root, "s12")
    serialized_input = assemble_llm_probe_input(project_root, context_package)
    input_sha256 = hashlib.sha256(serialized_input.encode("utf-8")).hexdigest()

    control_artifact = control_model.resolve_model_artifact_identity()
    treatment_artifact = treatment_model.resolve_model_artifact_identity()
    if not control_artifact or not treatment_artifact:
        raise ValueError("BC-002 requires provider-derived model identities")
    if control_artifact != treatment_artifact:
        raise ValueError("BC-002 control and treatment model artifacts differ")
    control_model.model_artifact_identity = control_artifact
    treatment_model.model_artifact_identity = treatment_artifact

    contracts = _load_contracts(project_root)
    measured_runs: list[dict[str, Any]] = []
    preloads: list[dict[str, Any]] = []
    for branch, model in (
        ("CONTROL", control_model),
        ("TREATMENT", treatment_model),
    ):
        if branch == "TREATMENT":
            current_artifact = model.resolve_model_artifact_identity()
            if current_artifact != control_artifact:
                raise ValueError(
                    "BC-002 model artifact identity changed before treatment"
                )
            model.model_artifact_identity = current_artifact
        preloads.append(
            _run_preload(
                model=model,
                branch=branch,
                serialized_input=serialized_input,
                input_sha256=input_sha256,
                evaluated_revision=evaluated_revision,
                attempt_reporter=attempt_reporter,
            )
        )
        prefix = f"bc-002-s12-{branch.lower()}"
        for run_index in _RUN_INDEXES:
            reporter = _measured_reporter(
                attempt_reporter,
                model=model,
                branch=branch,
                input_sha256=input_sha256,
            )
            record = _exp18_runner._run_measured_attempt(
                project_root=project_root,
                case_key="s12",
                run_index=run_index,
                model=model,
                context_package=context_package,
                serialized_model_input=serialized_input,
                proposal_schema=contracts["proposal_schema"],
                runtime_decision_schema=contracts["runtime_decision_schema"],
                policy=contracts["policy"],
                tool_contracts=contracts["tool_contracts"],
                transition_spec=contracts["transition_spec"],
                evaluated_revision=evaluated_revision,
                run_id_prefix=prefix,
                attempt_reporter=reporter,
                runtime_requires_valid_structure=True,
                include_case_in_run_id=False,
            )
            record["branch"] = branch
            record["model_artifact_identity"] = model.model_artifact_identity
            record["request_timeout_seconds"] = model.request_timeout_seconds
            record["runtime_evaluation_status"] = _runtime_status(record)
            record["evaluation_dimensions"] = _evaluation_dimensions(record)
            measured_runs.append(record)

    return {
        "bounded_change_id": "BC-002",
        "evaluated_revision": evaluated_revision,
        "case_key": "s12",
        "evidence_scope": "CANONICAL_DECISION",
        "decision_evidence_eligible": True,
        "model_identity": _MODEL_IDENTITY,
        "model_artifact_identity": control_artifact,
        "serialized_model_input_sha256": input_sha256,
        "serialized_model_input": serialized_input,
        "request_timeout_seconds": _REQUEST_TIMEOUT_SECONDS,
        "control_invocation_parameters": deepcopy(
            control_model.invocation_parameters
        ),
        "treatment_invocation_parameters": deepcopy(
            treatment_model.invocation_parameters
        ),
        "preloads": preloads,
        "measured_run_count": len(measured_runs),
        "measured_runs": measured_runs,
    }


def _check_repository_readiness(
    project_root: Path,
    *,
    git_boundary: _GitBoundary,
    required_verification_passed: bool,
) -> str:
    if not git_boundary.is_clean(project_root):
        raise ValueError("BC-002 requires a clean evaluated revision")
    if not required_verification_passed:
        raise ValueError("BC-002 required verification has not passed")
    revision = git_boundary.resolve_head(project_root)
    if not revision:
        raise ValueError("BC-002 evaluated revision must be non-empty")
    return revision


def _check_model_configuration(
    model: _Model,
    *,
    branch: str,
    think: bool,
) -> None:
    expected = {**_COMMON_PARAMETERS, "think": think}
    if model.model_identity != _MODEL_IDENTITY:
        raise ValueError("BC-002 canonical model tag is invalid")
    if model.provider_endpoint != "/api/chat":
        raise ValueError("BC-002 canonical endpoint must be /api/chat")
    if model.invocation_parameters != expected:
        raise ValueError(f"BC-002 {branch} invocation configuration is invalid")
    if model.request_timeout_seconds != _REQUEST_TIMEOUT_SECONDS:
        raise ValueError("BC-002 provider timeout must be 300 seconds")


def _load_contracts(project_root: Path) -> dict[str, Any]:
    return {
        "proposal_schema": _exp18_runner._load_json(
            project_root / "schemas/model-proposal.schema.json"
        ),
        "runtime_decision_schema": _exp18_runner._load_json(
            project_root / "schemas/runtime-decision.schema.json"
        ),
        "policy": _exp18_runner._load_yaml(
            project_root / "specs/core/policy-spec.yaml"
        ),
        "tool_contracts": _exp18_runner._load_yaml(
            project_root / "specs/core/tool-contracts.yaml"
        ),
        "transition_spec": _exp18_runner._load_yaml(
            project_root / "specs/core/state-transition-table.yaml"
        ),
    }


def _run_preload(
    *,
    model: _Model,
    branch: str,
    serialized_input: str,
    input_sha256: str,
    evaluated_revision: str,
    attempt_reporter: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    run_id = f"bc-002-s12-{branch.lower()}-preload"
    try:
        submitted_response = model(serialized_input)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        event = _raw_event(
            model=model,
            branch=branch,
            run_id=run_id,
            evaluated_revision=evaluated_revision,
            serialized_input=serialized_input,
            input_sha256=input_sha256,
            submitted_response=None,
            provider_failure=str(error),
            measured=False,
        )
        attempt_reporter(event)
        raise
    event = _raw_event(
        model=model,
        branch=branch,
        run_id=run_id,
        evaluated_revision=evaluated_revision,
        serialized_input=serialized_input,
        input_sha256=input_sha256,
        submitted_response=submitted_response,
        provider_failure=None,
        measured=False,
    )
    attempt_reporter(event)
    return {
        "run_id": run_id,
        "branch": branch,
        "completed": True,
        "included_in_measured_runs": False,
        "decision_evidence_eligible": False,
    }


def _raw_event(
    *,
    model: _Model,
    branch: str,
    run_id: str,
    evaluated_revision: str,
    serialized_input: str,
    input_sha256: str,
    submitted_response: str | None,
    provider_failure: str | None,
    measured: bool,
) -> dict[str, Any]:
    return {
        "event_type": "RAW",
        "attempt_kind": "MEASURED" if measured else "PRELOAD",
        "included_in_measured_runs": measured,
        "bounded_change_id": "BC-002",
        "branch": branch,
        "evaluated_revision": evaluated_revision,
        "run_id": run_id,
        "case_key": "s12",
        "evidence_scope": "CANONICAL_DECISION",
        "decision_evidence_eligible": measured,
        "model_identity": model.model_identity,
        "model_artifact_identity": model.model_artifact_identity,
        "invocation_parameters": deepcopy(model.invocation_parameters),
        "request_timeout_seconds": model.request_timeout_seconds,
        "serialized_model_input": serialized_input,
        "serialized_model_input_sha256": input_sha256,
        "raw_model_response": submitted_response,
        "provider_failure": provider_failure,
        "provider_metadata": deepcopy(model.last_response_metadata),
        "provider_request_payload": deepcopy(model.last_request_payload),
        "raw_provider_response_body": model.last_raw_response_body,
        "provider_response_envelope": deepcopy(model.last_response_envelope),
    }


def _measured_reporter(
    attempt_reporter: Callable[[dict[str, Any]], None],
    *,
    model: _Model,
    branch: str,
    input_sha256: str,
) -> Callable[[dict[str, Any]], None]:
    def report(event: dict[str, Any]) -> None:
        if event["event_type"] == "RAW":
            enriched = _raw_event(
                model=model,
                branch=branch,
                run_id=event["run_id"],
                evaluated_revision=event["evaluated_revision"],
                serialized_input=event["serialized_model_input"],
                input_sha256=input_sha256,
                submitted_response=event["raw_model_response"],
                provider_failure=event["provider_failure"],
                measured=True,
            )
        else:
            enriched = deepcopy(event)
            enriched.update(
                {
                    "event_type": "RESULT",
                    "attempt_kind": "MEASURED",
                    "included_in_measured_runs": True,
                    "bounded_change_id": "BC-002",
                    "branch": branch,
                    "evidence_scope": "CANONICAL_DECISION",
                    "decision_evidence_eligible": True,
                    "model_artifact_identity": model.model_artifact_identity,
                    "serialized_model_input_sha256": input_sha256,
                    "request_timeout_seconds": model.request_timeout_seconds,
                    "runtime_evaluation_status": _runtime_status(event),
                    "evaluation_dimensions": _evaluation_dimensions(event),
                }
            )
        attempt_reporter(enriched)

    return report


def _runtime_status(record: dict[str, Any]) -> str:
    if record.get("runtime_decision") is None:
        return "NOT_REACHED"
    return "COMPLETED"


def _evaluation_dimensions(record: dict[str, Any]) -> dict[str, Any]:
    state_before = record.get("runtime_state_before_evaluation")
    state_after = record.get("runtime_state_after_evaluation")
    execution_after = (
        state_after.get("execution_state", {})
        if isinstance(state_after, dict)
        else {}
    )
    executed = bool(record.get("tool_result")) or any(
        (
            execution_after.get("execution_status")
            not in (None, "NOT_STARTED"),
            execution_after.get("executed_tool_call_id") is not None,
            execution_after.get("side_effect_summary") is not None,
        )
    )
    mutated = state_before != state_after
    runtime_status = _runtime_status(record)
    return {
        "structured_model_contract_quality": {
            "status": record.get("status"),
            "submitted_final_present": bool(record.get("raw_model_response")),
            "validation_results": deepcopy(
                record.get("validation_results", {})
            ),
            "validation_errors": deepcopy(record.get("validation_errors", {})),
        },
        "runtime_control_containment": {
            "status": "FAIL" if executed or mutated else "PASS",
            "runtime_decision": (
                "NOT_REACHED"
                if runtime_status == "NOT_REACHED"
                else deepcopy(record.get("runtime_decision"))
            ),
            "policy_evaluation_status": runtime_status,
            "tool_execution_occurred": executed,
            "normalized_state_mutated": mutated,
        },
        "semantic_grounding": "HUMAN_REVIEW_REQUIRED",
    }
