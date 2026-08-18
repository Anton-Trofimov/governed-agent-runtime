"""Run the bounded 15-call Exp 18.1A measured proposal probe."""

import json
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any, Protocol

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from governed_agent_runtime.exp18_1a_context_assembly import (
    assemble_llm_probe_input,
    load_exp18_1a_context,
)
from governed_agent_runtime.llm_probe_contracts import (
    validate_proposal_context_consistency,
)
from governed_agent_runtime.runtime_policy import evaluate_proposal

_CASES = ("s02", "s07", "s08a", "s08b", "s12")
_RUN_INDEXES = (1, 2, 3)
_MODEL_IDENTITY = "qwen3.8:27b"
_INVOCATION_PARAMETERS = {
    "temperature": 0,
    "seed": 18,
    "num_ctx": 8192,
    "num_predict": 2048,
    "think": False,
    "stream": False,
    "keep_alive": "10m",
}


class _InjectedModel(Protocol):
    model_identity: str
    invocation_parameters: dict[str, Any]
    last_response_metadata: dict[str, Any] | None

    def __call__(self, serialized_input: str) -> str: ...


def run_exp18_1a_measured_evaluation(
    project_root: Path,
    *,
    model: _InjectedModel,
    warm_up: Callable[[_InjectedModel], None],
    evaluated_revision: str,
) -> dict[str, Any]:
    """Run one warm-up followed by the 15 fixed measured attempts."""
    _validate_configuration(model, evaluated_revision)
    proposal_schema = _load_json(
        project_root / "schemas/model-proposal.schema.json"
    )
    runtime_decision_schema = _load_json(
        project_root / "schemas/runtime-decision.schema.json"
    )
    policy = _load_yaml(project_root / "specs/core/policy-spec.yaml")
    tool_contracts = _load_yaml(
        project_root / "specs/core/tool-contracts.yaml"
    )
    transition_spec = _load_yaml(
        project_root / "specs/core/state-transition-table.yaml"
    )

    warm_up(model)
    measured_runs: list[dict[str, Any]] = []
    for case_key in _CASES:
        context_package = load_exp18_1a_context(project_root, case_key)
        serialized_model_input = assemble_llm_probe_input(
            project_root,
            context_package,
        )
        for run_index in _RUN_INDEXES:
            measured_runs.append(
                _run_measured_attempt(
                    project_root=project_root,
                    case_key=case_key,
                    run_index=run_index,
                    model=model,
                    context_package=context_package,
                    serialized_model_input=serialized_model_input,
                    proposal_schema=proposal_schema,
                    runtime_decision_schema=runtime_decision_schema,
                    policy=policy,
                    tool_contracts=tool_contracts,
                    transition_spec=transition_spec,
                )
            )

    return {
        "experiment_id": "exp-18-1a",
        "evaluated_revision": evaluated_revision,
        "model_identity": model.model_identity,
        "invocation_parameters": deepcopy(model.invocation_parameters),
        "warm_up": {
            "completed": True,
            "included_in_measured_runs": False,
        },
        "measured_runs": measured_runs,
    }


def _run_measured_attempt(
    *,
    project_root: Path,
    case_key: str,
    run_index: int,
    model: _InjectedModel,
    context_package: dict[str, Any],
    serialized_model_input: str,
    proposal_schema: dict[str, Any],
    runtime_decision_schema: dict[str, Any],
    policy: dict[str, Any],
    tool_contracts: dict[str, Any],
    transition_spec: dict[str, Any],
) -> dict[str, Any]:
    run_id = f"exp-18-1a-{case_key}-run-{run_index}"
    state = _runtime_state_from_context(context_package, run_id)
    state_before = deepcopy(state)
    record = _base_record(
        run_id=run_id,
        case_key=case_key,
        run_index=run_index,
        model=model,
        context_package=context_package,
        serialized_model_input=serialized_model_input,
        state=state,
    )

    try:
        raw_response = model(serialized_model_input)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        record.update(
            {
                "status": "MODEL_ERROR",
                "error": str(error),
                "provider_metadata": None,
                "raw_model_response": None,
                "proposal": None,
                "validation_results": {},
                "validation_errors": {},
                "runtime_decision": None,
                "runtime_state_before_evaluation": state_before,
                "runtime_state_after_evaluation": deepcopy(state),
            }
        )
        return record

    record["raw_model_response"] = raw_response
    record["provider_metadata"] = deepcopy(model.last_response_metadata)
    try:
        proposal = json.loads(raw_response)
    except json.JSONDecodeError as error:
        record.update(
            {
                "status": "PROPOSAL_PARSE_ERROR",
                "error": str(error),
                "proposal": None,
                "validation_results": {"parse": "FAILED"},
                "validation_errors": {"parse": str(error)},
                "runtime_decision": None,
                "runtime_state_before_evaluation": state_before,
                "runtime_state_after_evaluation": deepcopy(state),
            }
        )
        return record

    validation_results = {"parse": "PASSED"}
    validation_errors: dict[str, str] = {}
    try:
        _validate_schema(proposal, proposal_schema)
    except ValidationError as error:
        validation_results.update(
            {
                "proposal_schema": "FAILED",
                "proposal_context_semantics": "SKIPPED",
            }
        )
        validation_errors["proposal_schema"] = error.message
    else:
        validation_results["proposal_schema"] = "PASSED"
        try:
            validate_proposal_context_consistency(context_package, proposal)
        except ValueError as error:
            validation_results["proposal_context_semantics"] = "FAILED"
            validation_errors["proposal_context_semantics"] = str(error)
        else:
            validation_results["proposal_context_semantics"] = "PASSED"

    runtime_decision = evaluate_proposal(
        state,
        proposal,
        policy=policy,
        tool_contracts=tool_contracts,
        proposal_schema=proposal_schema,
        transition_spec=transition_spec,
    )
    _validate_schema(runtime_decision, runtime_decision_schema)
    record.update(
        {
            "status": "COMPLETED",
            "error": None,
            "proposal": proposal,
            "validation_results": validation_results,
            "validation_errors": validation_errors,
            "runtime_decision": runtime_decision,
            "runtime_state_before_evaluation": state_before,
            "runtime_state_after_evaluation": deepcopy(state),
        }
    )
    return record


def _base_record(
    *,
    run_id: str,
    case_key: str,
    run_index: int,
    model: _InjectedModel,
    context_package: dict[str, Any],
    serialized_model_input: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "case_key": case_key,
        "run_index": run_index,
        "model_identity": model.model_identity,
        "invocation_parameters": deepcopy(model.invocation_parameters),
        "context_package": deepcopy(context_package),
        "serialized_model_input": serialized_model_input,
        "provider_metadata": None,
        "raw_model_response": None,
        "proposal": None,
        "validation_results": {},
        "validation_errors": {},
        "runtime_decision": None,
        "runtime_state_before_evaluation": deepcopy(state),
        "runtime_state_after_evaluation": deepcopy(state),
    }


def _runtime_state_from_context(
    context_package: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    """Project only runtime-policy inputs from one approved context fixture."""
    target = context_package["resolved_target"]
    budget = context_package["remaining_budget_summary"]
    target_resolved = not context_package["unresolved_fields"]
    return {
        "schema_version": "0.1.0",
        "trace_id": f"trace-{run_id}",
        "state_version": 1,
        "updated_at": context_package["assembled_at"],
        "session_state": {
            "session_id": f"session-{run_id}",
            "current_goal": context_package["current_goal"],
            "phase": context_package["current_phase"],
            "task_state": context_package["current_task_state"],
            "resolved_service_id": target["service_id"],
            "resolved_environment_id": target["environment_id"],
            "resolved_scope": deepcopy(target["scope"]),
            "tool_call_count": 0,
            "tool_call_budget": budget["tool_calls_remaining"],
            "repeated_call_count": 0,
            "capability_gaps": [],
        },
        "observed_state": {
            "reference_time": context_package["assembled_at"],
            "observations": [],
        },
        "evidence_state": {
            "claims": [],
            "evidence_items": [],
            "mandatory_checks_completed": [],
            "mandatory_checks_missing": [],
            "freshness_status": "UNKNOWN",
            "contradictions": [],
            "evidence_sufficiency": "INSUFFICIENT",
            "evidence_gaps": [],
        },
        "diagnostic_assessment": {
            "hypotheses": [],
            "recommended_next_step": None,
            "uncertainty_notes": [],
        },
        "action_readiness": {
            "candidate_action": None,
            "target_resolved": target_resolved,
            "role_authorized": False,
            "evidence_gate_passed": False,
            "freshness_gate_passed": False,
            "preconditions_passed": False,
            "conflicting_operation_present": False,
            "confirmation_required": False,
            "action_ready": False,
            "blocking_reason_codes": [],
        },
        "confirmation_state": None,
        "execution_state": {
            "execution_status": "NOT_STARTED",
            "executed_tool_call_id": None,
            "side_effect_summary": None,
            "verification_status": "NOT_REQUIRED",
            "execution_error": None,
            "terminal_outcome": None,
        },
    }


def _validate_configuration(
    model: _InjectedModel,
    evaluated_revision: str,
) -> None:
    if model.model_identity != _MODEL_IDENTITY:
        raise ValueError(
            f"Exp 18.1A model must be {_MODEL_IDENTITY!r}; "
            f"got {model.model_identity!r}"
        )
    if model.invocation_parameters != _INVOCATION_PARAMETERS:
        raise ValueError("Exp 18.1A invocation parameters are not canonical")
    if not evaluated_revision:
        raise ValueError("evaluated_revision must be non-empty")


def _validate_schema(instance: Any, schema: dict[str, Any]) -> None:
    Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    ).validate(instance)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))
