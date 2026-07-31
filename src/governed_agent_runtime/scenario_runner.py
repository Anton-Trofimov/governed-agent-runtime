"""Run deterministic governed scenario paths end to end."""

import json
from pathlib import Path
from typing import Any

import yaml

from governed_agent_runtime.evidence_engine import (
    apply_evidence_assessment,
    evaluate_s01_evidence,
)
from governed_agent_runtime.execution_trace import (
    append_preparation_tool_execution,
    build_decision_application_trace,
)
from governed_agent_runtime.preparation_tools import (
    apply_preparation_tool_result,
    execute_preparation_tool,
)
from governed_agent_runtime.runtime_policy import evaluate_proposal
from governed_agent_runtime.scenario_loader import load_scenario_bundle
from governed_agent_runtime.state_builder import (
    build_normalized_state,
    normalize_selected_sources,
)
from governed_agent_runtime.state_transition import (
    apply_runtime_decision_with_record,
)


def run_s01_preparation_path(
    project_root: Path,
) -> dict[str, Any]:
    """Run S01 from supported hypothesis to governed action candidate."""
    adapter_contracts = _load_yaml(
        project_root
        / "specs/core/source-adapter-contracts.yaml"
    )
    policy = _load_yaml(
        project_root / "specs/core/policy-spec.yaml"
    )
    tool_contracts = _load_yaml(
        project_root / "specs/core/tool-contracts.yaml"
    )
    transition_spec = _load_yaml(
        project_root / "specs/core/state-transition-table.yaml"
    )

    proposal_schema = _load_json(
        project_root / "schemas/model-proposal.schema.json"
    )
    tool_result_schema = _load_json(
        project_root / "schemas/tool-result.schema.json"
    )

    bundle = load_scenario_bundle(project_root, "S01")
    observations = normalize_selected_sources(
        bundle,
        adapter_contracts,
    )

    raw_state = build_normalized_state(
        bundle,
        observations,
        trace_id="trace-s01-preparation-path",
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

    initial_state = apply_evidence_assessment(
        raw_state,
        assessment,
    )

    proposal = _s01_remediation_plan_proposal(initial_state)

    decision = evaluate_proposal(
        initial_state,
        proposal,
        policy=policy,
        tool_contracts=tool_contracts,
        proposal_schema=proposal_schema,
        transition_spec=transition_spec,
    )

    state_after_decision, decision_application_record = (
        apply_runtime_decision_with_record(
            initial_state,
            decision,
            transition_spec=transition_spec,
        )
    )

    trace = build_decision_application_trace(
        initial_state,
        proposal,
        decision,
        state_after_decision,
        application_record=decision_application_record,
    )

    tool_execution = execute_preparation_tool(
        state_after_decision,
        proposal,
        decision,
        tool_contracts=tool_contracts,
        tool_result_schema=tool_result_schema,
    )

    final_state, tool_application_record = (
        apply_preparation_tool_result(
            state_after_decision,
            proposal,
            tool_execution,
            tool_result_schema=tool_result_schema,
            transition_spec=transition_spec,
        )
    )

    final_trace = append_preparation_tool_execution(
        trace,
        state_after_decision,
        proposal,
        decision,
        tool_execution,
        final_state,
        application_record=tool_application_record,
    )

    return {
        "scenario_id": "S01",
        "governed_outcome": "DRAFT_CREATED",
        "initial_state": initial_state,
        "proposal": proposal,
        "decision": decision,
        "state_after_decision": state_after_decision,
        "tool_execution": tool_execution,
        "final_state": final_state,
        "trace": final_trace,
    }


def _s01_remediation_plan_proposal(
    state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-s01-acceptance-remediation-plan",
        "proposal_type": "CREATE_DRAFT",
        "rationale": (
            "Record the supported regression and unresolved rollback "
            "preconditions before operational execution."
        ),
        "created_at": state["updated_at"],
        "payload": {
            "tool_name": "create_remediation_plan",
            "arguments": {
                "service_id": "payment-api",
                "environment_id": "production",
                "candidate_action": {
                    "action_type": "rollback_deployment",
                },
                "rationale": (
                    "Version 2.4.2 has elevated 5xx errors while "
                    "dependencies remain healthy."
                ),
                "evidence_ids": [
                    "ev-s01-version-error-old",
                    "ev-s01-version-error-new",
                ],
                "required_precondition_ids": [
                    "ROLLBACK_DATABASE_COMPATIBLE",
                    "ROLLBACK_TRANSITIONAL_CAPACITY_SUFFICIENT",
                ],
                "risks": [
                    "Current old-version capacity is insufficient.",
                ],
                "verification_steps": [
                    "Verify version-specific 5xx rate after traffic shift.",
                ],
                "stop_conditions": [
                    "Stop if projected capacity headroom is below minimum.",
                ],
            },
        },
    }


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
