"""Convert validated raw source responses into normalized factual observations."""

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any


class SourceAdapterError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _validate_aware_timestamp(
    value: Any,
    *,
    field_name: str,
) -> None:
    if not isinstance(value, str):
        raise SourceAdapterError(
            "INVALID_SOURCE_TIMESTAMP",
            (
                f"{field_name} must be a timezone-aware "
                "ISO 8601 string"
            ),
        )

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise SourceAdapterError(
            "INVALID_SOURCE_TIMESTAMP",
            (
                f"{field_name} must be a timezone-aware "
                "ISO 8601 string"
            ),
        ) from error

    if parsed.utcoffset() is None:
        raise SourceAdapterError(
            "INVALID_SOURCE_TIMESTAMP",
            f"{field_name} must include a timezone offset",
        )


Observation = dict[str, Any]
Normalizer = Callable[
    [Mapping[str, Any], str, str, str],
    list[Observation],
]


def normalize_source(
    tool_name: str,
    source: Mapping[str, Any],
    adapter_contracts: Mapping[str, Any],
    *,
    collected_at: str,
    raw_reference: str,
    expected_service_id: str,
    expected_environment_id: str,
) -> list[Observation]:
    adapter = _find_adapter_contract(tool_name, adapter_contracts)
    _validate_required_fields(source, adapter["required_source_fields"])
    _validate_target(
        source,
        expected_service_id=expected_service_id,
        expected_environment_id=expected_environment_id,
    )

    try:
        normalizer = NORMALIZERS[tool_name]
    except KeyError as error:
        raise SourceAdapterError(
            "ADAPTER_NOT_IMPLEMENTED",
            f"No source adapter implemented for tool: {tool_name}",
        ) from error

    observations = normalizer(
        source,
        adapter["source_type"],
        collected_at,
        raw_reference,
    )

    for observation in observations:
        observation_id = observation.get(
            "observation_id",
            "<unknown-observation>",
        )

        for field_name in (
            "observed_at",
            "collected_at",
        ):
            _validate_aware_timestamp(
                observation.get(field_name),
                field_name=(
                    f"{observation_id}.{field_name}"
                ),
            )

    return observations


def _find_adapter_contract(
    tool_name: str,
    adapter_contracts: Mapping[str, Any],
) -> Mapping[str, Any]:
    matches = [
        adapter
        for adapter in adapter_contracts["source_adapters"].values()
        if adapter["tool_name"] == tool_name
    ]

    if len(matches) != 1:
        raise SourceAdapterError(
            "ADAPTER_CONTRACT_NOT_FOUND",
            f"Expected one adapter contract for {tool_name}, got {len(matches)}",
        )

    return matches[0]


def _validate_required_fields(
    source: Mapping[str, Any],
    required_fields: list[str],
) -> None:
    missing = [field for field in required_fields if field not in source]

    if missing:
        raise SourceAdapterError(
            "MISSING_REQUIRED_SOURCE_FIELD",
            f"Missing required source fields: {missing}",
        )


def _validate_target(
    source: Mapping[str, Any],
    *,
    expected_service_id: str,
    expected_environment_id: str,
) -> None:
    if source["service_id"] != expected_service_id:
        raise SourceAdapterError(
            "SOURCE_TARGET_MISMATCH",
            "Source service_id differs from the resolved service",
        )

    if source["environment_id"] != expected_environment_id:
        raise SourceAdapterError(
            "SOURCE_TARGET_MISMATCH",
            "Source environment_id differs from the resolved environment",
        )


def _base_scope(source: Mapping[str, Any]) -> dict[str, Any]:
    scope = {
        "service_id": source["service_id"],
        "environment_id": source["environment_id"],
    }

    deployment_target_id = source.get("deployment_target_id")

    if deployment_target_id is not None:
        scope["deployment_target_id"] = deployment_target_id

    return scope


def _observation(
    *,
    observation_id: str,
    source: Mapping[str, Any],
    source_type: str,
    collected_at: str,
    raw_reference: str,
    summary: str,
    fact_type: str,
    value: Any,
    scope: Mapping[str, Any] | None = None,
    observed_at: str | None = None,
    **extra: Any,
) -> Observation:
    observation: Observation = {
        "observation_id": observation_id,
        "source_type": source_type,
        "source_id": source["source_id"],
        "observed_at": observed_at or source["source_timestamp"],
        "collected_at": collected_at,
        "scope": dict(scope or _base_scope(source)),
        "summary": summary,
        "fact_type": fact_type,
        "value": value,
        "raw_reference": raw_reference,
    }

    observation.update(extra)
    return observation


def _normalize_service_status(
    source: Mapping[str, Any],
    source_type: str,
    collected_at: str,
    raw_reference: str,
) -> list[Observation]:
    observations = []

    for field in (
        "desired_replicas",
        "ready_replicas",
        "available_replicas",
    ):
        observations.append(
            _observation(
                observation_id=f"{source['source_id']}-{field}",
                source=source,
                source_type=source_type,
                collected_at=collected_at,
                raw_reference=raw_reference,
                summary=f"{field} is {source[field]}",
                fact_type=field.upper(),
                value=source[field],
            )
        )

    for index, replica in enumerate(source["replica_statuses"], start=1):
        scope = _base_scope(source)
        scope.update(
            {
                "replica_id": replica["replica_id"],
                "version_id": replica["version_id"],
            }
        )

        observations.append(
            _observation(
                observation_id=f"{source['source_id']}-replica-{index}",
                source=source,
                source_type=source_type,
                collected_at=collected_at,
                raw_reference=raw_reference,
                summary=(
                    f"Replica {replica['replica_id']} is "
                    f"{replica['readiness']} and {replica['availability']}"
                ),
                fact_type="REPLICA_STATUS",
                value=replica,
                scope=scope,
            )
        )

    for index, transition in enumerate(
        source.get("readiness_transitions", []),
        start=1,
    ):
        observations.append(
            _observation(
                observation_id=f"{source['source_id']}-transition-{index}",
                source=source,
                source_type=source_type,
                collected_at=collected_at,
                raw_reference=raw_reference,
                summary="Replica readiness transition observed",
                fact_type="READINESS_TRANSITION",
                value=transition,
                observed_at=transition.get(
                    "occurred_at",
                    source["source_timestamp"],
                ),
            )
        )

    return observations


def _normalize_service_metrics(
    source: Mapping[str, Any],
    source_type: str,
    collected_at: str,
    raw_reference: str,
) -> list[Observation]:
    observations = []

    for index, series in enumerate(source["metric_series"], start=1):
        scope = _base_scope(source)
        scope.update(series.get("dimensions", {}))

        observations.append(
            _observation(
                observation_id=f"{source['source_id']}-series-{index}",
                source=source,
                source_type=source_type,
                collected_at=collected_at,
                raw_reference=raw_reference,
                summary=(
                    f"Metric {series['metric_name']} contains "
                    f"{len(series['points'])} point(s)"
                ),
                fact_type="METRIC_SERIES",
                value=series["points"],
                scope=scope,
                metric_name=series["metric_name"],
                unit=series["unit"],
                dimensions=series.get("dimensions", {}),
                time_window=source["window"],
            )
        )

    return observations


def _normalize_deployments(
    source: Mapping[str, Any],
    source_type: str,
    collected_at: str,
    raw_reference: str,
) -> list[Observation]:
    observations = [
        _observation(
            observation_id=f"{source['source_id']}-rollout-status",
            source=source,
            source_type=source_type,
            collected_at=collected_at,
            raw_reference=raw_reference,
            summary=f"Rollout status is {source['rollout_status']}",
            fact_type="ROLLOUT_STATUS",
            value=source["rollout_status"],
        )
    ]

    for index, deployment in enumerate(source["deployments"], start=1):
        scope = _base_scope(source)
        scope["deployment_id"] = deployment["deployment_id"]

        observations.append(
            _observation(
                observation_id=f"{source['source_id']}-deployment-{index}",
                source=source,
                source_type=source_type,
                collected_at=collected_at,
                raw_reference=raw_reference,
                summary=(
                    f"Deployment {deployment['deployment_id']} "
                    f"is {deployment['status']}"
                ),
                fact_type="DEPLOYMENT",
                value=deployment,
                scope=scope,
                observed_at=deployment.get(
                    "started_at",
                    source["source_timestamp"],
                ),
            )
        )

    for index, group in enumerate(
        source["active_version_groups"],
        start=1,
    ):
        scope = _base_scope(source)
        scope["version_id"] = group["version_id"]

        observations.append(
            _observation(
                observation_id=f"{source['source_id']}-version-group-{index}",
                source=source,
                source_type=source_type,
                collected_at=collected_at,
                raw_reference=raw_reference,
                summary=(
                    f"Version {group['version_id']} has "
                    f"{group['replica_count']} replicas and "
                    f"{group['traffic_percent']}% traffic"
                ),
                fact_type="ACTIVE_VERSION_GROUP",
                value=group,
                scope=scope,
            )
        )

    for index, candidate in enumerate(
        source.get("rollback_candidates", []),
        start=1,
    ):
        observations.append(
            _observation(
                observation_id=f"{source['source_id']}-rollback-{index}",
                source=source,
                source_type=source_type,
                collected_at=collected_at,
                raw_reference=raw_reference,
                summary=(
                    f"Rollback candidate {candidate['version_id']} "
                    f"availability is {candidate['artifact_available']}"
                ),
                fact_type="ROLLBACK_CANDIDATE",
                value=candidate,
            )
        )

    observations.append(
        _observation(
            observation_id=f"{source['source_id']}-compatibility",
            source=source,
            source_type=source_type,
            collected_at=collected_at,
            raw_reference=raw_reference,
            summary="Rollback compatibility information was collected",
            fact_type="ROLLBACK_COMPATIBILITY",
            value=source.get("compatibility_references", {}),
        )
    )

    return observations


def _normalize_runtime_events(
    source: Mapping[str, Any],
    source_type: str,
    collected_at: str,
    raw_reference: str,
) -> list[Observation]:
    observations = []

    for index, event in enumerate(source["events"], start=1):
        observations.append(
            _observation(
                observation_id=f"{source['source_id']}-event-{index}",
                source=source,
                source_type=source_type,
                collected_at=collected_at,
                raw_reference=raw_reference,
                summary=f"Runtime event {event['event_type']} observed",
                fact_type="RUNTIME_EVENT",
                value=event,
                observed_at=event["occurred_at"],
            )
        )

    for index, operation in enumerate(
        source.get("active_operations", []),
        start=1,
    ):
        observations.append(
            _observation(
                observation_id=f"{source['source_id']}-operation-{index}",
                source=source,
                source_type=source_type,
                collected_at=collected_at,
                raw_reference=raw_reference,
                summary="Active runtime operation observed",
                fact_type="ACTIVE_OPERATION",
                value=operation,
            )
        )

    return observations


def _normalize_dependencies(
    source: Mapping[str, Any],
    source_type: str,
    collected_at: str,
    raw_reference: str,
) -> list[Observation]:
    observations = []

    for index, dependency in enumerate(
        source["dependency_states"],
        start=1,
    ):
        scope = _base_scope(source)
        scope["dependency_id"] = dependency["dependency_id"]

        observations.append(
            _observation(
                observation_id=f"{source['source_id']}-dependency-{index}",
                source=source,
                source_type=source_type,
                collected_at=collected_at,
                raw_reference=raw_reference,
                summary=(
                    f"Dependency {dependency['dependency_id']} is "
                    f"{dependency['availability_status']}"
                ),
                fact_type="DEPENDENCY_STATUS",
                value=dependency,
                scope=scope,
            )
        )

    return observations


def _normalize_traffic(
    source: Mapping[str, Any],
    source_type: str,
    collected_at: str,
    raw_reference: str,
) -> list[Observation]:
    observations = [
        _observation(
            observation_id=f"{source['source_id']}-total-rps",
            source=source,
            source_type=source_type,
            collected_at=collected_at,
            raw_reference=raw_reference,
            summary=(
                f"Total request rate is "
                f"{source['total_request_rate_rps']} RPS"
            ),
            fact_type="TOTAL_REQUEST_RATE",
            value=source["total_request_rate_rps"],
            unit="requests_per_second",
            time_window=source["window"],
        )
    ]

    for index, group in enumerate(source["traffic_groups"], start=1):
        scope = _base_scope(source)
        scope.update(group["group_by"])

        observations.append(
            _observation(
                observation_id=f"{source['source_id']}-group-{index}",
                source=source,
                source_type=source_type,
                collected_at=collected_at,
                raw_reference=raw_reference,
                summary=(
                    f"Traffic group has {group['request_rate_rps']} RPS "
                    f"and {group['traffic_percent']}% traffic"
                ),
                fact_type="TRAFFIC_GROUP",
                value=group,
                scope=scope,
                time_window=source["window"],
            )
        )

    return observations


NORMALIZERS: dict[str, Normalizer] = {
    "get_service_status": _normalize_service_status,
    "get_service_metrics": _normalize_service_metrics,
    "get_recent_deployments": _normalize_deployments,
    "get_recent_runtime_events": _normalize_runtime_events,
    "get_dependency_status": _normalize_dependencies,
    "get_traffic_breakdown": _normalize_traffic,
}
