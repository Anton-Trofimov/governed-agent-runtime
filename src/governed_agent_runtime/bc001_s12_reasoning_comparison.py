"""Orchestrate the fixed BC-001 S12 reasoning-mode comparison."""

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

_CANONICAL_MODEL_TAG = "qwen3.8:27b"
_CANONICAL_PARAMETERS = {
    "temperature": 0,
    "seed": 18,
    "num_ctx": 8192,
    "num_predict": 2048,
    "think": True,
    "stream": False,
    "keep_alive": "10m",
}
_FROZEN_S12_INPUT_SHA256 = (
    "4b79c52363bec8bcfd5b8d67e0410669a0095cea0accbf21751cd294dc8ec269"
)
_RUN_INDEXES = (1, 2, 3)
_REQUEST_TIMEOUT_SECONDS = 300


class _InjectedModel(Protocol):
    model_identity: str
    model_artifact_identity: str
    invocation_parameters: dict[str, Any]
    request_timeout_seconds: float
    last_response_metadata: dict[str, Any] | None

    def resolve_model_artifact_identity(self) -> str: ...

    def __call__(self, serialized_input: str) -> str: ...


class _GitBoundary(Protocol):
    def is_clean(self, project_root: Path) -> bool: ...

    def resolve_head(self, project_root: Path) -> str: ...


def run_bc001_canonical_comparison(
    project_root: Path,
    *,
    model: _InjectedModel,
    git_boundary: _GitBoundary,
    attempt_reporter: Callable[[dict[str, Any]], None],
    required_verification_passed: bool,
    expected_baseline_artifact_identity: str | None = None,
) -> dict[str, Any]:
    """Run the canonical fixed BC-001 schedule after all readiness checks."""
    return _run_comparison(
        project_root,
        model=model,
        git_boundary=git_boundary,
        attempt_reporter=attempt_reporter,
        required_verification_passed=required_verification_passed,
        expected_baseline_artifact_identity=(
            expected_baseline_artifact_identity
        ),
        canonical=True,
    )


def run_bc001_noncanonical_reproduction(
    project_root: Path,
    *,
    model: _InjectedModel,
    git_boundary: _GitBoundary,
    attempt_reporter: Callable[[dict[str, Any]], None],
    required_verification_passed: bool,
) -> dict[str, Any]:
    """Run a clearly separated reproduction that cannot be decision evidence."""
    return _run_comparison(
        project_root,
        model=model,
        git_boundary=git_boundary,
        attempt_reporter=attempt_reporter,
        required_verification_passed=required_verification_passed,
        expected_baseline_artifact_identity=None,
        canonical=False,
    )


def _run_comparison(
    project_root: Path,
    *,
    model: _InjectedModel,
    git_boundary: _GitBoundary,
    attempt_reporter: Callable[[dict[str, Any]], None],
    required_verification_passed: bool,
    expected_baseline_artifact_identity: str | None,
    canonical: bool,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    (
        context_package,
        serialized_model_input,
        input_sha256,
        evaluated_revision,
    ) = _check_readiness(
        project_root,
        model=model,
        git_boundary=git_boundary,
        required_verification_passed=required_verification_passed,
        expected_baseline_artifact_identity=(
            expected_baseline_artifact_identity
        ),
        canonical=canonical,
    )
    evidence_scope = (
        "CANONICAL_DECISION"
        if canonical
        else "NON_CANONICAL_REPRODUCTION"
    )
    decision_evidence_eligible = canonical

    _run_preload(
        model=model,
        evaluated_revision=evaluated_revision,
        evidence_scope=evidence_scope,
        decision_evidence_eligible=decision_evidence_eligible,
        attempt_reporter=attempt_reporter,
    )

    proposal_schema = _exp18_runner._load_json(
        project_root / "schemas/model-proposal.schema.json"
    )
    runtime_decision_schema = _exp18_runner._load_json(
        project_root / "schemas/runtime-decision.schema.json"
    )
    policy = _exp18_runner._load_yaml(
        project_root / "specs/core/policy-spec.yaml"
    )
    tool_contracts = _exp18_runner._load_yaml(
        project_root / "specs/core/tool-contracts.yaml"
    )
    transition_spec = _exp18_runner._load_yaml(
        project_root / "specs/core/state-transition-table.yaml"
    )

    measured_runs: list[dict[str, Any]] = []
    for run_index in _RUN_INDEXES:
        record = _exp18_runner._run_measured_attempt(
            project_root=project_root,
            case_key="s12",
            run_index=run_index,
            model=model,
            context_package=context_package,
            serialized_model_input=serialized_model_input,
            proposal_schema=proposal_schema,
            runtime_decision_schema=runtime_decision_schema,
            policy=policy,
            tool_contracts=tool_contracts,
            transition_spec=transition_spec,
            evaluated_revision=evaluated_revision,
            run_id_prefix="bc-001",
            attempt_reporter=_measured_reporter(
                attempt_reporter,
                model_artifact_identity=model.model_artifact_identity,
                input_sha256=input_sha256,
                request_timeout_seconds=model.request_timeout_seconds,
                evidence_scope=evidence_scope,
                decision_evidence_eligible=decision_evidence_eligible,
            ),
        )
        record["model_artifact_identity"] = model.model_artifact_identity
        record["request_timeout_seconds"] = model.request_timeout_seconds
        record["evaluation_dimensions"] = _evaluation_dimensions(record)
        measured_runs.append(record)

    return {
        "bounded_change_id": "BC-001",
        "evaluated_revision": evaluated_revision,
        "case_key": "s12",
        "evidence_scope": evidence_scope,
        "decision_evidence_eligible": decision_evidence_eligible,
        "model_identity": model.model_identity,
        "model_artifact_identity": model.model_artifact_identity,
        "frozen_baseline_artifact_identity": (
            expected_baseline_artifact_identity
        ),
        "frozen_baseline_digest_limitation": (
            expected_baseline_artifact_identity is None
        ),
        "invocation_parameters": deepcopy(model.invocation_parameters),
        "request_timeout_seconds": model.request_timeout_seconds,
        "serialized_model_input_sha256": input_sha256,
        "preload": {
            "completed": True,
            "included_in_measured_runs": False,
            "attempt_kind": "PRELOAD",
        },
        "measured_runs": measured_runs,
    }


def _check_readiness(
    project_root: Path,
    *,
    model: _InjectedModel,
    git_boundary: _GitBoundary,
    required_verification_passed: bool,
    expected_baseline_artifact_identity: str | None,
    canonical: bool,
) -> tuple[dict[str, Any], str, str, str]:
    if not git_boundary.is_clean(project_root):
        raise ValueError("BC-001 requires a clean evaluated revision")
    if not required_verification_passed:
        raise ValueError("BC-001 required verification has not passed")
    evaluated_revision = git_boundary.resolve_head(project_root)
    if not evaluated_revision:
        raise ValueError("BC-001 evaluated revision must be non-empty")
    if canonical and model.model_identity != _CANONICAL_MODEL_TAG:
        raise ValueError(
            f"BC-001 canonical model tag must be {_CANONICAL_MODEL_TAG!r}"
        )
    if model.invocation_parameters != _CANONICAL_PARAMETERS:
        raise ValueError("BC-001 invocation configuration is not canonical")
    if model.request_timeout_seconds != _REQUEST_TIMEOUT_SECONDS:
        raise ValueError("BC-001 provider timeout must be 300 seconds")

    context_package = load_exp18_1a_context(project_root, "s12")
    serialized_model_input = assemble_llm_probe_input(
        project_root,
        context_package,
    )
    input_sha256 = hashlib.sha256(
        serialized_model_input.encode("utf-8")
    ).hexdigest()
    if input_sha256 != _FROZEN_S12_INPUT_SHA256:
        raise ValueError("BC-001 frozen S12 input identity mismatch")

    artifact_identity = model.resolve_model_artifact_identity()
    if not artifact_identity:
        raise ValueError("BC-001 requires a provider-derived immutable identity")
    if (
        canonical
        and expected_baseline_artifact_identity is not None
        and artifact_identity != expected_baseline_artifact_identity
    ):
        raise ValueError(
            "BC-001 model artifact mismatches the authoritative baseline artifact"
        )
    return (
        context_package,
        serialized_model_input,
        input_sha256,
        evaluated_revision,
    )


def _run_preload(
    *,
    model: _InjectedModel,
    evaluated_revision: str,
    evidence_scope: str,
    decision_evidence_eligible: bool,
    attempt_reporter: Callable[[dict[str, Any]], None],
) -> None:
    try:
        raw_response = model("")
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        attempt_reporter(
            _preload_event(
                model=model,
                evaluated_revision=evaluated_revision,
                evidence_scope=evidence_scope,
                decision_evidence_eligible=decision_evidence_eligible,
                raw_model_response=None,
                provider_failure=str(error),
                provider_metadata=None,
            )
        )
        raise

    attempt_reporter(
        _preload_event(
            model=model,
            evaluated_revision=evaluated_revision,
            evidence_scope=evidence_scope,
            decision_evidence_eligible=decision_evidence_eligible,
            raw_model_response=raw_response,
            provider_failure=None,
            provider_metadata=deepcopy(model.last_response_metadata),
        )
    )


def _preload_event(
    *,
    model: _InjectedModel,
    evaluated_revision: str,
    evidence_scope: str,
    decision_evidence_eligible: bool,
    raw_model_response: str | None,
    provider_failure: str | None,
    provider_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "event_type": "RAW",
        "attempt_kind": "PRELOAD",
        "included_in_measured_runs": False,
        "bounded_change_id": "BC-001",
        "evaluated_revision": evaluated_revision,
        "run_id": "bc-001-s12-preload",
        "case_key": "s12",
        "run_index": 0,
        "evidence_scope": evidence_scope,
        "decision_evidence_eligible": decision_evidence_eligible,
        "model_identity": model.model_identity,
        "model_artifact_identity": model.model_artifact_identity,
        "invocation_parameters": deepcopy(model.invocation_parameters),
        "request_timeout_seconds": model.request_timeout_seconds,
        "serialized_model_input": "",
        "raw_model_response": raw_model_response,
        "provider_failure": provider_failure,
        "provider_metadata": provider_metadata,
    }


def _measured_reporter(
    attempt_reporter: Callable[[dict[str, Any]], None],
    *,
    model_artifact_identity: str,
    input_sha256: str,
    request_timeout_seconds: float,
    evidence_scope: str,
    decision_evidence_eligible: bool,
) -> Callable[[dict[str, Any]], None]:
    def report(event: dict[str, Any]) -> None:
        enriched = deepcopy(event)
        enriched.update(
            {
                "event_type": (
                    "RESULT"
                    if event["event_type"] == "ENRICHED"
                    else "RAW"
                ),
                "attempt_kind": "MEASURED",
                "included_in_measured_runs": True,
                "bounded_change_id": "BC-001",
                "evidence_scope": evidence_scope,
                "decision_evidence_eligible": decision_evidence_eligible,
                "model_artifact_identity": model_artifact_identity,
                "serialized_model_input_sha256": input_sha256,
                "request_timeout_seconds": request_timeout_seconds,
            }
        )
        if event["event_type"] == "ENRICHED":
            enriched["evaluation_dimensions"] = _evaluation_dimensions(event)
        attempt_reporter(enriched)

    return report


def _evaluation_dimensions(record: dict[str, Any]) -> dict[str, Any]:
    state_before = record.get("runtime_state_before_evaluation")
    state_after = record.get("runtime_state_after_evaluation")
    execution_after = (
        state_after.get("execution_state", {})
        if isinstance(state_after, dict)
        else {}
    )
    tool_execution_occurred = bool(record.get("tool_result")) or any(
        (
            execution_after.get("execution_status")
            not in (None, "NOT_STARTED"),
            execution_after.get("executed_tool_call_id") is not None,
            execution_after.get("side_effect_summary") is not None,
        )
    )
    return {
        "structured_model_contract_quality": {
            "status": record.get("status"),
            "validation_results": deepcopy(
                record.get("validation_results", {})
            ),
            "validation_errors": deepcopy(record.get("validation_errors", {})),
        },
        "runtime_control_containment": {
            "runtime_decision": deepcopy(record.get("runtime_decision")),
            "tool_execution_occurred": tool_execution_occurred,
            "normalized_state_mutated": state_before != state_after,
        },
        "semantic_grounding": "HUMAN_REVIEW_REQUIRED",
    }
