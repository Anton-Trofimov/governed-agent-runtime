"""Run the bounded Exp 18.1A S01 single-call plumbing smoke."""

import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from governed_agent_runtime.contract_schema import normalize_contract_schema
from governed_agent_runtime.evidence_engine import (
    apply_evidence_assessment,
    evaluate_s01_evidence,
)
from governed_agent_runtime.llm_probe_contracts import (
    validate_model_context_package,
    validate_proposal_context_consistency,
)
from governed_agent_runtime.runtime_policy import evaluate_proposal
from governed_agent_runtime.scenario_loader import ScenarioBundle, load_scenario_bundle
from governed_agent_runtime.state_builder import (
    build_normalized_state,
    normalize_selected_sources,
)


class _InjectedModel(Protocol):
    model_identity: str
    invocation_parameters: dict[str, Any]

    def __call__(self, serialized_input: str) -> str: ...


def build_s01_model_context(project_root: Path) -> dict[str, Any]:
    """Build the S01 smoke context from approved deterministic inputs."""
    state, bundle = _build_s01_runtime_state(project_root)
    tool_contracts = _load_yaml(project_root / "specs/core/tool-contracts.yaml")
    policy = _load_yaml(project_root / "specs/core/policy-spec.yaml")
    context = _context_from_state(
        project_root,
        state,
        bundle.user_request,
        tool_contracts,
        policy,
    )
    _validate_schema(
        context,
        project_root / "schemas/model-context-package.schema.json",
    )
    validate_model_context_package(context)
    return context


def run_s01_llm_probe_smoke(
    project_root: Path,
    *,
    model: _InjectedModel,
) -> dict[str, Any]:
    """Invoke one injected model and stop after deterministic evaluation."""
    started_at = _now()
    state, bundle = _build_s01_runtime_state(project_root)
    tool_contracts = _load_yaml(project_root / "specs/core/tool-contracts.yaml")
    policy = _load_yaml(project_root / "specs/core/policy-spec.yaml")
    transition_spec = _load_yaml(
        project_root / "specs/core/state-transition-table.yaml"
    )
    proposal_schema = _load_json(
        project_root / "schemas/model-proposal.schema.json"
    )

    context = _context_from_state(
        project_root,
        state,
        bundle.user_request,
        tool_contracts,
        policy,
    )
    _validate_schema(
        context,
        project_root / "schemas/model-context-package.schema.json",
    )
    validate_model_context_package(context)

    invocation_payload = {
        "instructions": (
            "Return exactly one JSON Model Proposal for the next bounded step. "
            "Use only the supplied context and requested output contract."
        ),
        "context_package": context,
    }
    serialized_model_input = json.dumps(
        invocation_payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    model_identity = model.model_identity
    invocation_parameters = deepcopy(model.invocation_parameters)
    raw_model_response = model(serialized_model_input)
    proposal = json.loads(raw_model_response)

    _validate_schema(
        proposal,
        project_root / "schemas/model-proposal.schema.json",
    )
    validate_proposal_context_consistency(context, proposal)

    state_before_evaluation = deepcopy(state)
    runtime_decision = evaluate_proposal(
        state,
        proposal,
        policy=policy,
        tool_contracts=tool_contracts,
        proposal_schema=proposal_schema,
        transition_spec=transition_spec,
    )
    state_after_evaluation = deepcopy(state)
    _validate_schema(
        runtime_decision,
        project_root / "schemas/runtime-decision.schema.json",
    )

    return {
        "purpose": "PLUMBING_SMOKE",
        "included_in_evaluation_sample": False,
        "smoke_id": "smoke-session-s01-001",
        "started_at": started_at,
        "completed_at": _now(),
        "context_package": context,
        "serialized_model_input": serialized_model_input,
        "model_identity": model_identity,
        "invocation_parameters": invocation_parameters,
        "raw_model_response": raw_model_response,
        "proposal": proposal,
        "validation_results": {
            "context_schema": "PASSED",
            "context_semantics": "PASSED",
            "proposal_schema": "PASSED",
            "proposal_context_semantics": "PASSED",
        },
        "runtime_decision": runtime_decision,
        "runtime_state_before_evaluation": state_before_evaluation,
        "runtime_state_after_evaluation": state_after_evaluation,
    }


def _build_s01_runtime_state(
    project_root: Path,
) -> tuple[dict[str, Any], ScenarioBundle]:
    bundle = load_scenario_bundle(project_root, "S01")
    adapter_contracts = _load_yaml(
        project_root / "specs/core/source-adapter-contracts.yaml"
    )
    observations = normalize_selected_sources(bundle, adapter_contracts)
    state = build_normalized_state(
        bundle,
        observations,
        trace_id="trace-s01-llm-probe-smoke",
        tool_call_count=6,
        tool_call_budget=10,
    )
    capacity_profile = _load_yaml(
        project_root / "knowledge/capacity-profiles.yaml"
    )["profiles"][0]
    assessment = evaluate_s01_evidence(
        observations,
        capacity_profile,
        reference_time=bundle.scenario["reference_time"],
    )
    return apply_evidence_assessment(state, assessment), bundle


def _context_from_state(
    project_root: Path,
    state: dict[str, Any],
    user_request: dict[str, Any],
    tool_contracts: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    session = state["session_state"]
    evidence = state["evidence_state"]
    diagnostic = state["diagnostic_assessment"]
    service = _service_record(project_root, session["resolved_service_id"])
    available_tools = [
        {
            "tool_name": tool["tool_name"],
            "category": tool["category"],
            "description": tool["purpose"],
            "input_schema": normalize_contract_schema(tool["input_schema"]),
        }
        for tool in tool_contracts["tools"]
        if session["phase"] in tool["allowed_phases"]
    ]
    constraints = [
        {
            "constraint_id": rule["rule_id"],
            "description": rule["effect"],
        }
        for rule in policy["policy_rules"]
    ]

    return {
        "schema_version": "0.1.0",
        "context_package_id": "context-package-smoke-001",
        "assembled_at": state["updated_at"],
        "user_request": {
            "request_id": _neutral_identifier(user_request["request_id"]),
            "text": user_request["message"],
            "received_at": user_request["submitted_at"],
        },
        "session_summary": (
            "The target is resolved and deterministic evidence has been "
            "assessed for the paused production rollout."
        ),
        "current_goal": session["current_goal"],
        "requested_operation": "diagnose",
        "resolved_target": {
            "service_id": session["resolved_service_id"],
            "environment_id": session["resolved_environment_id"],
            "scope": deepcopy(session["resolved_scope"]),
        },
        "resolved_fields": [
            "resolved_target.service_id",
            "resolved_target.environment_id",
            "resolved_target.scope",
        ],
        "unresolved_fields": [],
        "current_phase": session["phase"],
        "current_task_state": session["task_state"],
        "relevant_service_context": [
            {
                "context_id": f"service-{service['service_id']}",
                "summary": (
                    f"{service['service_display_name']} has "
                    f"{service['criticality']} criticality."
                ),
                "source": "service-catalog",
            }
        ],
        "observed_state_summary": [
            {
                "context_id": _neutral_identifier(item["observation_id"]),
                "summary": item["summary"],
                "source": item["source_type"],
                "observed_at": item["observed_at"],
            }
            for item in state["observed_state"]["observations"]
        ],
        "evidence_summary": [
            {
                "evidence_id": _neutral_identifier(item["evidence_id"]),
                "summary": item["summary"],
                "source_type": item["source_type"],
                "freshness_status": item["freshness_status"],
            }
            for item in evidence["evidence_items"]
        ],
        "active_hypotheses": [
            {
                "hypothesis_id": _neutral_identifier(item["hypothesis_id"]),
                "statement": item["statement"],
                "cause_status": item["cause_status"],
                "evidence_ids": _hypothesis_evidence_ids(item, evidence),
                "missing_evidence": evidence["mandatory_checks_missing"],
            }
            for item in diagnostic["hypotheses"]
        ],
        "evidence_gaps": [
            {
                "gap_id": _neutral_identifier(item["gap_id"]),
                "required_data": item["required_data"],
                "purpose": item["diagnostic_purpose"],
            }
            for item in evidence["evidence_gaps"]
        ],
        "capability_gaps": deepcopy(session["capability_gaps"]),
        "relevant_runbooks": [],
        "available_tools": available_tools,
        "applicable_constraints": constraints,
        "remaining_budget_summary": {
            "tool_calls_remaining": (
                session["tool_call_budget"] - session["tool_call_count"]
            ),
            "model_calls_remaining": 1,
            "token_budget_remaining": None,
        },
        "requested_output_schema": {
            "schema_ref": (
                "https://governed-agent-runtime.local/schemas/"
                "model-proposal.schema.json"
            ),
            "schema_version": "0.1.0",
            "allowed_proposal_types": policy["phases"][session["phase"]][
                "allowed_proposals"
            ],
            "response_format": "JSON_OBJECT",
        },
    }


def _hypothesis_evidence_ids(
    hypothesis: dict[str, Any],
    evidence_state: dict[str, Any],
) -> list[str]:
    supported_claims = set(hypothesis["supported_claim_ids"])
    return sorted(
        {
            _neutral_identifier(item["evidence_id"])
            for item in evidence_state["evidence_items"]
            if item["claim_id"] in supported_claims
        }
    )


def _neutral_identifier(identifier: str) -> str:
    return re.sub("s01", "runtime", identifier, flags=re.IGNORECASE)


def _service_record(project_root: Path, service_id: str) -> dict[str, Any]:
    catalog = _load_yaml(project_root / "knowledge/service-catalog.yaml")
    return next(
        service
        for service in catalog["services"]
        if service["service_id"] == service_id
    )


def _validate_schema(instance: dict[str, Any], schema_path: Path) -> None:
    checker = FormatChecker()
    if "date-time" not in checker.checkers:
        checker.checkers["date-time"] = (
            lambda value: datetime.fromisoformat(value),
            (TypeError, ValueError),
        )
    Draft202012Validator(
        _load_json(schema_path),
        format_checker=checker,
    ).validate(instance)


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
