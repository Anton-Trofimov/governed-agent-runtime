"""Build deterministic claims and evidence assessment for S01."""

from copy import deepcopy
from datetime import datetime
from typing import Any


def evaluate_s01_evidence(
    observations: list[dict[str, Any]],
    capacity_profile: dict[str, Any],
    *,
    reference_time: str,
) -> dict[str, Any]:
    claims: list[dict[str, Any]] = []
    evidence_items: list[dict[str, Any]] = []
    contradictions: list[dict[str, Any]] = []
    completed_checks: list[str] = []
    missing_checks: list[str] = []
    evidence_gaps: list[dict[str, Any]] = []
    uncertainty_notes: list[str] = []

    old_error = _latest_metric(
        observations,
        "payment_api_http_5xx_rate",
        version_id="2.4.1",
    )
    new_error = _latest_metric(
        observations,
        "payment_api_http_5xx_rate",
        version_id="2.4.2",
    )

    regression_supported = False
    regression_evidence_ids: list[str] = []

    if old_error and new_error:
        completed_checks.append("VERSION_SPECIFIC_ERROR_METRICS")

        old_value = old_error["latest_value"]
        new_value = new_error["latest_value"]

        regression_supported = (
            new_value >= old_value * 5
            and new_value - old_value >= 0.01
        )

        for suffix, metric, summary in (
            (
                "old",
                old_error,
                f"Version 2.4.1 latest 5xx rate is {old_value:.3%}.",
            ),
            (
                "new",
                new_error,
                f"Version 2.4.2 latest 5xx rate is {new_value:.3%}.",
            ),
        ):
            evidence_id = f"ev-s01-version-error-{suffix}"
            regression_evidence_ids.append(evidence_id)
            evidence_items.append(
                _evidence_from_observation(
                    evidence_id=evidence_id,
                    claim_id="claim-s01-version-regression",
                    observation=metric["observation"],
                    support_type=(
                        "SUPPORTS"
                        if regression_supported
                        else "NEUTRAL"
                    ),
                    summary=summary,
                    reference_time=reference_time,
                )
            )
    else:
        missing_checks.append("VERSION_SPECIFIC_ERROR_METRICS")
        evidence_gaps.append(
            {
                "gap_id": "gap-s01-version-error-metrics",
                "required_data": "5xx rate grouped by version",
                "diagnostic_purpose": (
                    "Determine whether degradation is associated "
                    "with version 2.4.2."
                ),
            }
        )

    claims.append(
        {
            "claim_id": "claim-s01-version-regression",
            "statement": (
                "Version 2.4.2 has a materially higher 5xx rate "
                "than version 2.4.1."
            ),
            "status": (
                "SUPPORTED"
                if regression_supported
                else "UNKNOWN"
            ),
            "scope": {
                "service_id": "payment-api",
                "environment_id": "production",
                "version_id": "2.4.2",
            },
            "evidence_ids": regression_evidence_ids,
        }
    )

    dependency_observations = [
        item
        for item in observations
        if item["fact_type"] == "DEPENDENCY_STATUS"
    ]

    dependencies_healthy = bool(dependency_observations) and all(
        item["value"]["availability_status"] == "HEALTHY"
        for item in dependency_observations
    )

    dependency_evidence_ids: list[str] = []

    if dependency_observations:
        completed_checks.append("DEPENDENCY_HEALTH")

        for index, observation in enumerate(
            dependency_observations,
            start=1,
        ):
            evidence_id = f"ev-s01-dependency-{index}"
            dependency_evidence_ids.append(evidence_id)
            dependency = observation["value"]

            evidence_items.append(
                _evidence_from_observation(
                    evidence_id=evidence_id,
                    claim_id="claim-s01-dependencies-healthy",
                    observation=observation,
                    support_type=(
                        "SUPPORTS"
                        if dependency["availability_status"] == "HEALTHY"
                        else "CONTRADICTS"
                    ),
                    summary=(
                        f"Dependency {dependency['dependency_id']} is "
                        f"{dependency['availability_status']}."
                    ),
                    reference_time=reference_time,
                )
            )
    else:
        missing_checks.append("DEPENDENCY_HEALTH")
        evidence_gaps.append(
            {
                "gap_id": "gap-s01-dependency-health",
                "required_data": "current dependency health",
                "diagnostic_purpose": (
                    "Distinguish an application regression "
                    "from dependency degradation."
                ),
            }
        )

    claims.append(
        {
            "claim_id": "claim-s01-dependencies-healthy",
            "statement": (
                "Observed payment-api dependencies are healthy "
                "in the diagnostic window."
            ),
            "status": (
                "SUPPORTED"
                if dependencies_healthy
                else "UNKNOWN"
            ),
            "scope": {
                "service_id": "payment-api",
                "environment_id": "production",
            },
            "evidence_ids": dependency_evidence_ids,
        }
    )

    desired = _fact(observations, "DESIRED_REPLICAS")
    ready = _fact(observations, "READY_REPLICAS")
    readiness_evidence_ids: list[str] = []

    all_replicas_ready = bool(
        desired
        and ready
        and desired["value"] == ready["value"]
    )

    for suffix, observation in (
        ("desired", desired),
        ("ready", ready),
    ):
        if observation is None:
            continue

        evidence_id = f"ev-s01-replicas-{suffix}"
        readiness_evidence_ids.append(evidence_id)
        evidence_items.append(
            _evidence_from_observation(
                evidence_id=evidence_id,
                claim_id="claim-s01-ready-with-errors",
                observation=observation,
                support_type="SUPPORTS",
                summary=observation["summary"],
                reference_time=reference_time,
            )
        )

    claims.append(
        {
            "claim_id": "claim-s01-ready-with-errors",
            "statement": (
                "All desired replicas are ready while version 2.4.2 "
                "continues to produce elevated application errors."
            ),
            "status": (
                "SUPPORTED"
                if all_replicas_ready and regression_supported
                else "UNKNOWN"
            ),
            "scope": {
                "service_id": "payment-api",
                "environment_id": "production",
            },
            "evidence_ids": (
                readiness_evidence_ids + regression_evidence_ids
            ),
        }
    )

    if all_replicas_ready and regression_supported:
        contradictions.append(
            {
                "contradiction_id": "contradiction-s01-readiness-vs-errors",
                "summary": (
                    "Replica readiness is normal while application-level "
                    "5xx errors are elevated on version 2.4.2."
                ),
                "evidence_ids": (
                    readiness_evidence_ids + regression_evidence_ids
                ),
                "interpretation": (
                    "Readiness does not prove correct application behavior."
                ),
            }
        )

    rollout = _fact(observations, "ROLLOUT_STATUS")
    version_group = _version_group(
        observations,
        version_id="2.4.1",
    )
    total_rps = _fact(observations, "TOTAL_REQUEST_RATE")

    deployment_evidence_ids: list[str] = []

    if rollout is not None:
        completed_checks.append("DEPLOYMENT_AND_ROLLOUT_STATE")
        evidence_id = "ev-s01-rollout-status"
        deployment_evidence_ids.append(evidence_id)
        evidence_items.append(
            _evidence_from_observation(
                evidence_id=evidence_id,
                claim_id="claim-s01-rollout-paused",
                observation=rollout,
                support_type="SUPPORTS",
                summary=rollout["summary"],
                reference_time=reference_time,
            )
        )
    else:
        missing_checks.append("DEPLOYMENT_AND_ROLLOUT_STATE")

    claims.append(
        {
            "claim_id": "claim-s01-rollout-paused",
            "statement": "The rollout is paused for validation.",
            "status": (
                "SUPPORTED"
                if rollout
                and rollout["value"] == "PAUSED_FOR_VALIDATION"
                else "UNKNOWN"
            ),
            "scope": {
                "service_id": "payment-api",
                "environment_id": "production",
            },
            "evidence_ids": deployment_evidence_ids,
        }
    )

    capacity_evidence_ids: list[str] = []
    capacity_insufficient = False

    if version_group and total_rps:
        completed_checks.append("ROLLBACK_PROJECTED_CAPACITY")

        old_replica_count = version_group["value"]["replica_count"]
        safe_rps_per_replica = capacity_profile[
            "validated_safe_rps_per_replica"
        ]
        safe_capacity = old_replica_count * safe_rps_per_replica
        current_rps = total_rps["value"]

        capacity_insufficient = safe_capacity < current_rps

        for evidence_id, observation, summary in (
            (
                "ev-s01-current-traffic",
                total_rps,
                f"Current request rate is {current_rps} RPS.",
            ),
            (
                "ev-s01-old-version-replicas",
                version_group,
                (
                    f"Version 2.4.1 currently has "
                    f"{old_replica_count} replicas."
                ),
            ),
        ):
            capacity_evidence_ids.append(evidence_id)
            evidence_items.append(
                _evidence_from_observation(
                    evidence_id=evidence_id,
                    claim_id="claim-s01-rollback-capacity-insufficient",
                    observation=observation,
                    support_type="SUPPORTS",
                    summary=summary,
                    reference_time=reference_time,
                )
            )

        capacity_evidence_ids.append("ev-s01-capacity-profile")
        evidence_items.append(
            {
                "evidence_id": "ev-s01-capacity-profile",
                "claim_id": (
                    "claim-s01-rollback-capacity-insufficient"
                ),
                "source_type": "CAPACITY_PROFILE",
                "support_type": "SUPPORTS",
                "summary": (
                    f"Validated safe capacity is "
                    f"{safe_rps_per_replica} RPS per replica; "
                    f"three replicas provide {safe_capacity} RPS."
                ),
                "freshness_status": "FRESH",
                "raw_reference": (
                    "knowledge://capacity-profiles/"
                    f"{capacity_profile['profile_id']}"
                ),
            }
        )
    else:
        missing_checks.append("ROLLBACK_PROJECTED_CAPACITY")
        evidence_gaps.append(
            {
                "gap_id": "gap-s01-rollback-capacity",
                "required_data": (
                    "current traffic, old-version replica count "
                    "and validated capacity profile"
                ),
                "diagnostic_purpose": (
                    "Determine whether immediate traffic return "
                    "to version 2.4.1 is safe."
                ),
            }
        )

    claims.append(
        {
            "claim_id": "claim-s01-rollback-capacity-insufficient",
            "statement": (
                "The current version 2.4.1 replica group cannot safely "
                "carry all current traffic."
            ),
            "status": (
                "SUPPORTED"
                if capacity_insufficient
                else "UNKNOWN"
            ),
            "scope": {
                "service_id": "payment-api",
                "environment_id": "production",
                "version_id": "2.4.1",
            },
            "evidence_ids": capacity_evidence_ids,
        }
    )

    compatibility = _fact(
        observations,
        "ROLLBACK_COMPATIBILITY",
    )
    compatibility_evidence_ids: list[str] = []
    database_compatibility_unknown = True

    if compatibility:
        compatibility_value = compatibility["value"]
        database_status = compatibility_value.get(
            "database_compatibility_status",
            "UNKNOWN",
        )
        configuration_status = compatibility_value.get(
            "configuration_compatibility_status",
            "UNKNOWN",
        )

        database_compatibility_unknown = database_status != "CONFIRMED"

        evidence_id = "ev-s01-rollback-compatibility"
        compatibility_evidence_ids.append(evidence_id)
        evidence_items.append(
            _evidence_from_observation(
                evidence_id=evidence_id,
                claim_id="claim-s01-db-compatibility-unknown",
                observation=compatibility,
                support_type=(
                    "SUPPORTS"
                    if database_compatibility_unknown
                    else "CONTRADICTS"
                ),
                summary=(
                    f"Database compatibility is {database_status}; "
                    f"configuration compatibility is "
                    f"{configuration_status}."
                ),
                reference_time=reference_time,
            )
        )

        if database_compatibility_unknown:
            missing_checks.append(
                "ROLLBACK_DATABASE_COMPATIBILITY"
            )
        else:
            completed_checks.append(
                "ROLLBACK_DATABASE_COMPATIBILITY"
            )

        if configuration_status == "CONFIRMED":
            completed_checks.append(
                "ROLLBACK_CONFIGURATION_COMPATIBILITY"
            )
        else:
            missing_checks.append(
                "ROLLBACK_CONFIGURATION_COMPATIBILITY"
            )
    else:
        missing_checks.extend(
            [
                "ROLLBACK_DATABASE_COMPATIBILITY",
                "ROLLBACK_CONFIGURATION_COMPATIBILITY",
            ]
        )

    claims.append(
        {
            "claim_id": "claim-s01-db-compatibility-unknown",
            "statement": (
                "Database compatibility with the rollback target "
                "has not been confirmed."
            ),
            "status": (
                "SUPPORTED"
                if database_compatibility_unknown
                else "CONTRADICTED"
            ),
            "scope": {
                "service_id": "payment-api",
                "environment_id": "production",
                "version_id": "2.4.1",
            },
            "evidence_ids": compatibility_evidence_ids,
        }
    )

    if capacity_insufficient:
        missing_checks.append("ROLLBACK_TRANSITIONAL_CAPACITY")
        evidence_gaps.append(
            {
                "gap_id": "gap-s01-transitional-capacity",
                "required_data": (
                    "validated scale-up, readiness, warm-up "
                    "and gradual traffic-shift plan"
                ),
                "diagnostic_purpose": (
                    "Define a safe rollback transition when three "
                    "old-version replicas cannot carry all traffic."
                ),
            }
        )

    core_diagnosis_supported = (
        regression_supported and dependencies_healthy
    )

    action_checks_missing = any(
        check.startswith("ROLLBACK_")
        for check in missing_checks
    )

    if core_diagnosis_supported and action_checks_missing:
        sufficiency = "PARTIAL"
    elif core_diagnosis_supported:
        sufficiency = "SUFFICIENT"
    else:
        sufficiency = "INSUFFICIENT"

    cause_status = (
        "SUPPORTED"
        if core_diagnosis_supported
        else "UNCONFIRMED"
    )

    hypotheses = [
        {
            "hypothesis_id": "hyp-s01-version-regression",
            "statement": (
                "The elevated payment-api error rate is associated "
                "with application version 2.4.2."
            ),
            "hypothesis_source": "DETERMINISTIC_RULE",
            "cause_status": cause_status,
            "supported_claim_ids": [
                claim["claim_id"]
                for claim in claims
                if claim["status"] == "SUPPORTED"
            ],
            "contradicted_claim_ids": [
                claim["claim_id"]
                for claim in claims
                if claim["status"] == "CONTRADICTED"
            ],
        }
    ]

    if sufficiency == "PARTIAL":
        recommended_next_step = {
            "proposal_type": "CREATE_DRAFT",
            "tool_name": "create_remediation_plan",
            "rationale": (
                "Record the supported version regression and the "
                "missing rollback compatibility and capacity checks."
            ),
            "missing_preconditions": sorted(set(missing_checks)),
        }
        uncertainty_notes.append(
            "Regression diagnosis is supported, but rollback is not ready."
        )
    elif sufficiency == "SUFFICIENT":
        recommended_next_step = {
            "proposal_type": "CREATE_DRAFT",
            "tool_name": "create_remediation_plan",
            "rationale": (
                "Prepare the exact rollback plan before confirmation."
            ),
            "missing_preconditions": [],
        }
    else:
        recommended_next_step = {
            "proposal_type": "CALL_TOOL",
            "rationale": (
                "Collect missing version, deployment or dependency evidence."
            ),
        }
        uncertainty_notes.append(
            "Current evidence does not support a bounded root-cause conclusion."
        )

    return {
        "claims": claims,
        "evidence_items": evidence_items,
        "mandatory_checks_completed": sorted(set(completed_checks)),
        "mandatory_checks_missing": sorted(set(missing_checks)),
        "freshness_status": _aggregate_freshness(evidence_items),
        "contradictions": contradictions,
        "evidence_sufficiency": sufficiency,
        "evidence_gaps": evidence_gaps,
        "hypotheses": hypotheses,
        "recommended_next_step": recommended_next_step,
        "uncertainty_notes": uncertainty_notes,
    }


def apply_evidence_assessment(
    state: dict[str, Any],
    assessment: dict[str, Any],
) -> dict[str, Any]:
    updated = deepcopy(state)
    updated["state_version"] += 1

    evidence_state = updated["evidence_state"]
    evidence_state["claims"] = assessment["claims"]
    evidence_state["evidence_items"] = assessment["evidence_items"]
    evidence_state["mandatory_checks_completed"] = assessment[
        "mandatory_checks_completed"
    ]
    evidence_state["mandatory_checks_missing"] = assessment[
        "mandatory_checks_missing"
    ]
    evidence_state["freshness_status"] = assessment["freshness_status"]
    evidence_state["contradictions"] = assessment["contradictions"]
    evidence_state["evidence_sufficiency"] = assessment[
        "evidence_sufficiency"
    ]
    evidence_state["evidence_gaps"] = assessment["evidence_gaps"]

    diagnostic = updated["diagnostic_assessment"]
    diagnostic["hypotheses"] = assessment["hypotheses"]
    diagnostic["recommended_next_step"] = assessment[
        "recommended_next_step"
    ]
    diagnostic["uncertainty_notes"] = assessment[
        "uncertainty_notes"
    ]

    updated["session_state"]["task_state"] = (
        "HYPOTHESIS_READY"
        if assessment["hypotheses"]
        else "EVIDENCE_EVALUATED"
    )

    action_readiness = updated["action_readiness"]
    action_readiness["evidence_gate_passed"] = (
        assessment["evidence_sufficiency"] == "SUFFICIENT"
    )
    action_readiness["freshness_gate_passed"] = (
        assessment["freshness_status"] == "FRESH"
    )
    action_readiness["action_ready"] = False

    evidence_owned_blockers = {
        "EVIDENCE_INSUFFICIENT",
        "EVIDENCE_STALE_OR_CONFLICTING",
    }

    retained_blockers = [
        reason_code
        for reason_code in action_readiness[
            "blocking_reason_codes"
        ]
        if reason_code not in evidence_owned_blockers
    ]

    current_evidence_blockers = []

    if not action_readiness["evidence_gate_passed"]:
        current_evidence_blockers.append(
            "EVIDENCE_INSUFFICIENT"
        )

    if not action_readiness["freshness_gate_passed"]:
        current_evidence_blockers.append(
            "EVIDENCE_STALE_OR_CONFLICTING"
        )

    action_readiness["blocking_reason_codes"] = [
        *retained_blockers,
        *current_evidence_blockers,
    ]

    return updated


def _latest_metric(
    observations: list[dict[str, Any]],
    metric_name: str,
    *,
    version_id: str,
) -> dict[str, Any] | None:
    for observation in observations:
        if (
            observation.get("fact_type") == "METRIC_SERIES"
            and observation.get("metric_name") == metric_name
            and observation["scope"].get("version_id") == version_id
        ):
            latest_point = max(
                observation["value"],
                key=lambda point: datetime.fromisoformat(
                    point["timestamp"]
                ),
            )
            return {
                "observation": observation,
                "latest_value": latest_point["value"],
            }

    return None


def _fact(
    observations: list[dict[str, Any]],
    fact_type: str,
) -> dict[str, Any] | None:
    return next(
        (
            observation
            for observation in observations
            if observation.get("fact_type") == fact_type
        ),
        None,
    )


def _version_group(
    observations: list[dict[str, Any]],
    *,
    version_id: str,
) -> dict[str, Any] | None:
    return next(
        (
            observation
            for observation in observations
            if observation.get("fact_type") == "ACTIVE_VERSION_GROUP"
            and observation["scope"].get("version_id") == version_id
        ),
        None,
    )


def _evidence_from_observation(
    *,
    evidence_id: str,
    claim_id: str,
    observation: dict[str, Any],
    support_type: str,
    summary: str,
    reference_time: str,
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "claim_id": claim_id,
        "source_type": observation["source_type"],
        "support_type": support_type,
        "summary": summary,
        "freshness_status": _freshness(
            observation["observed_at"],
            reference_time,
        ),
        "raw_reference": observation["raw_reference"],
    }


def _freshness(observed_at: str, reference_time: str) -> str:
    observed = _parse_datetime(observed_at)
    reference = _parse_datetime(reference_time)
    age_seconds = abs((reference - observed).total_seconds())

    return "FRESH" if age_seconds <= 300 else "STALE"


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _aggregate_freshness(
    evidence_items: list[dict[str, Any]],
) -> str:
    statuses = {
        item["freshness_status"]
        for item in evidence_items
    }

    if not statuses:
        return "UNKNOWN"

    if statuses == {"FRESH"}:
        return "FRESH"

    if statuses == {"STALE"}:
        return "STALE"

    return "MIXED"
