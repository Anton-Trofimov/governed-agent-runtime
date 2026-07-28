"""Build normalized runtime state from validated source observations."""

from collections.abc import Iterable, Mapping
from typing import Any

from governed_agent_runtime.scenario_loader import ScenarioBundle
from governed_agent_runtime.source_adapters import normalize_source


def normalize_selected_sources(
    bundle: ScenarioBundle,
    adapter_contracts: Mapping[str, Any],
    *,
    tool_names: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    selected_tools = list(
        tool_names
        if tool_names is not None
        else bundle.scenario["tool_source_files"]
    )

    known_context = bundle.user_request["known_context"]
    observations: list[dict[str, Any]] = []

    for tool_name in selected_tools:
        if tool_name not in bundle.source_payloads:
            raise ValueError(
                f"Scenario {bundle.scenario_id} has no source for {tool_name}"
            )

        observations.extend(
            normalize_source(
                tool_name,
                bundle.source_payloads[tool_name],
                adapter_contracts,
                collected_at=bundle.scenario["reference_time"],
                raw_reference=(
                    f"fixture://{bundle.scenario_id.lower()}/{tool_name}"
                ),
                expected_service_id=known_context["service_id"],
                expected_environment_id=known_context["environment_id"],
            )
        )

    return observations


def build_normalized_state(
    bundle: ScenarioBundle,
    observations: list[dict[str, Any]],
    *,
    trace_id: str,
    state_version: int = 1,
    tool_call_count: int = 0,
    tool_call_budget: int = 3,
    task_state: str = "DIAGNOSING",
) -> dict[str, Any]:
    request = bundle.user_request
    known_context = request["known_context"]
    deployment_target_id = _resolve_deployment_target_id(observations)

    return {
        "schema_version": "0.1.0",
        "trace_id": trace_id,
        "state_version": state_version,
        "updated_at": bundle.scenario["reference_time"],
        "session_state": {
            "session_id": request["session_id"],
            "current_goal": request["message"],
            "phase": bundle.scenario["initial_phase"],
            "task_state": task_state,
            "resolved_service_id": known_context["service_id"],
            "resolved_environment_id": known_context["environment_id"],
            "resolved_scope": {
                "deployment_target_id": deployment_target_id
            },
            "tool_call_count": tool_call_count,
            "tool_call_budget": tool_call_budget,
            "repeated_call_count": 0,
            "capability_gaps": [],
        },
        "observed_state": {
            "reference_time": bundle.scenario["reference_time"],
            "observations": observations,
        },
        "evidence_state": {
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
            "target_resolved": deployment_target_id is not None,
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


def _resolve_deployment_target_id(
    observations: list[dict[str, Any]],
) -> str | None:
    targets = {
        observation["scope"]["deployment_target_id"]
        for observation in observations
        if observation["scope"].get("deployment_target_id")
    }

    if len(targets) > 1:
        raise ValueError(
            f"Conflicting deployment targets in observations: {targets}"
        )

    return next(iter(targets), None)
