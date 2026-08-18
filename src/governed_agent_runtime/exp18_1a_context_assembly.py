"""Load approved Exp 18.1A contexts and assemble canonical model input."""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from governed_agent_runtime.llm_probe_contracts import (
    validate_model_context_package,
)

_CASE_FIXTURE_PATHS = {
    "s02": Path("fixtures/model-context/exp-18-1a/s02/context-package.json"),
    "s07": Path("fixtures/model-context/exp-18-1a/s07/context-package.json"),
    "s08a": Path("fixtures/model-context/exp-18-1a/s08a/context-package.json"),
    "s08b": Path("fixtures/model-context/exp-18-1a/s08b/context-package.json"),
    "s12": Path("fixtures/model-context/exp-18-1a/s12/context-package.json"),
}
_CANONICAL_INSTRUCTIONS = (
    "Return exactly one JSON Model Proposal for the next bounded step. "
    "Use only the supplied context and requested output contract."
)


def load_exp18_1a_context(
    project_root: Path,
    case_key: str,
) -> dict[str, Any]:
    """Load and validate one approved selected-case context fixture."""
    try:
        fixture_path = _CASE_FIXTURE_PATHS[case_key]
    except KeyError as error:
        supported = ", ".join(_CASE_FIXTURE_PATHS)
        raise ValueError(
            f"Unsupported Exp 18.1A case key {case_key!r}; supported: {supported}"
        ) from error

    context_package = _load_json(project_root / fixture_path)
    context_schema = _load_json(
        project_root / "schemas/model-context-package.schema.json"
    )
    Draft202012Validator(
        context_schema,
        format_checker=FormatChecker(),
    ).validate(context_package)
    validate_model_context_package(context_package)
    return context_package


def assemble_llm_probe_input(
    project_root: Path,
    context_package: dict[str, Any],
) -> str:
    """Serialize the canonical provider-neutral single-step model envelope."""
    proposal_schema = _load_json(
        project_root / "schemas/model-proposal.schema.json"
    )
    envelope = {
        "instructions": _CANONICAL_INSTRUCTIONS,
        "context_package": context_package,
        "model_proposal_schema": proposal_schema,
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
