import importlib
import json
import shutil
from pathlib import Path
from types import ModuleType

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from governed_agent_runtime.llm_probe_contracts import (
    validate_model_context_package,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "fixtures/model-context/exp-18-1a"
CASES = ("s02", "s07", "s08a", "s08b", "s12")
CANONICAL_INSTRUCTIONS = (
    "Return exactly one JSON Model Proposal for the next bounded step. "
    "Use only the supplied context and requested output contract."
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def context_assembly_module() -> ModuleType:
    module_name = "governed_agent_runtime.exp18_1a_context_assembly"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        pytest.fail(
            f"missing selected-case context assembly boundary: {module_name}",
            pytrace=False,
        )


def isolated_approved_root(tmp_path: Path, case: str) -> Path:
    fixture_target = (
        tmp_path
        / "fixtures/model-context/exp-18-1a"
        / case
        / "context-package.json"
    )
    fixture_target.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE_ROOT / case / "context-package.json", fixture_target)

    schema_target = tmp_path / "schemas"
    schema_target.mkdir()
    for schema_name in (
        "model-context-package.schema.json",
        "model-proposal.schema.json",
    ):
        shutil.copyfile(ROOT / "schemas" / schema_name, schema_target / schema_name)
    return tmp_path


@pytest.mark.parametrize("case", CASES)
def test_selected_case_loads_and_assembles_canonical_model_input(
    tmp_path: Path,
    case: str,
) -> None:
    approved_context = load_json(FIXTURE_ROOT / case / "context-package.json")
    authoritative_proposal_schema = load_json(
        ROOT / "schemas/model-proposal.schema.json"
    )
    isolated_root = isolated_approved_root(tmp_path, case)
    assembly = context_assembly_module()

    context = assembly.load_exp18_1a_context(isolated_root, case)
    serialized_model_input = assembly.assemble_llm_probe_input(
        isolated_root,
        context,
    )
    repeated_input = assembly.assemble_llm_probe_input(isolated_root, context)

    assert context == approved_context
    Draft202012Validator(
        load_json(ROOT / "schemas/model-context-package.schema.json"),
        format_checker=FormatChecker(),
    ).validate(context)
    validate_model_context_package(context)

    assert serialized_model_input == repeated_input
    envelope = json.loads(serialized_model_input)
    assert envelope == {
        "instructions": CANONICAL_INSTRUCTIONS,
        "context_package": approved_context,
        "model_proposal_schema": authoritative_proposal_schema,
    }
    assert serialized_model_input == json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert all(label not in serialized_model_input.casefold() for label in CASES)
