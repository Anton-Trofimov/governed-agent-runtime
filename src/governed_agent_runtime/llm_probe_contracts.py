"""Validate cross-object and path semantics for the Exp 18.1A probe."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

_RESERVED_EVALUATOR_KEYS = frozenset(
    {
        "scenario_id",
        "hidden_facts",
        "expectations",
    }
)


def validate_model_context_package(
    context_package: Mapping[str, Any],
) -> None:
    """Validate model-context semantics not expressible by its JSON Schema."""
    resolved_fields = set(context_package["resolved_fields"])
    unresolved_fields = set(context_package["unresolved_fields"])
    overlap = resolved_fields & unresolved_fields

    if overlap:
        fields = ", ".join(sorted(overlap))
        raise ValueError(
            "resolved_fields and unresolved_fields must be disjoint; "
            f"overlap: {fields}"
        )

    reserved_keys = _find_reserved_evaluator_keys(context_package)
    if reserved_keys:
        keys = ", ".join(sorted(reserved_keys))
        raise ValueError(
            "Model context contains evaluation-only reserved keys: "
            f"{keys}"
        )


def validate_proposal_context_consistency(
    context_package: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> None:
    """Validate proposal references against the model-visible context."""
    payload = proposal["payload"]

    if "missing_fields" in payload:
        unresolved_fields = set(context_package["unresolved_fields"])
        invented_fields = set(payload["missing_fields"]) - unresolved_fields
        if invented_fields:
            fields = ", ".join(sorted(invented_fields))
            raise ValueError(
                "Proposal missing_fields must be members of "
                f"context unresolved_fields; unknown: {fields}"
            )

    if "tool_name" in payload:
        available_tools = {
            tool["tool_name"] for tool in context_package["available_tools"]
        }
        tool_name = payload["tool_name"]
        if tool_name not in available_tools:
            raise ValueError(
                f"Proposed tool {tool_name!r} is not in context available_tools"
            )


def validate_evaluation_artifact_paths(
    *,
    repository_root: Path,
    model_context_path: Path,
    evaluation_case_path: Path,
) -> None:
    """Keep model-visible context and hidden evaluation artifacts separated."""
    repository_root = repository_root.resolve()
    model_visible_root = (
        repository_root / "fixtures" / "model-context" / "exp-18-1a"
    ).resolve()
    hidden_evaluation_root = (
        repository_root / "evals" / "hidden" / "exp-18-1a"
    ).resolve()
    model_context_path = _resolve_from_root(model_context_path, repository_root)
    evaluation_case_path = _resolve_from_root(
        evaluation_case_path,
        repository_root,
    )

    if not _is_within(model_context_path, model_visible_root):
        raise ValueError(
            "Model context path must remain under the Exp 18.1A model-visible root"
        )

    if (
        not _is_within(evaluation_case_path, hidden_evaluation_root)
        or _is_within(evaluation_case_path, model_visible_root)
    ):
        raise ValueError(
            "Evaluation-only case path must remain under the Exp 18.1A "
            "hidden-evaluation root and outside the model-visible area"
        )


def _find_reserved_evaluator_keys(value: Any) -> set[str]:
    """Find explicit evaluator structure as a defense-in-depth check."""
    if isinstance(value, Mapping):
        found = _RESERVED_EVALUATOR_KEYS & value.keys()
        for item in value.values():
            found |= _find_reserved_evaluator_keys(item)
        return found

    if isinstance(value, list):
        found: set[str] = set()
        for item in value:
            found |= _find_reserved_evaluator_keys(item)
        return found

    return set()


def _resolve_from_root(path: Path, repository_root: Path) -> Path:
    if not path.is_absolute():
        path = repository_root / path
    return path.resolve()


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents
