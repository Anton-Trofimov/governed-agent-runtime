import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_SOURCES = {
    "DETERMINISTIC_RULE",
    "RUNBOOK_GROUNDED",
    "MODEL_PRIOR",
}


def find_hypothesis_source_enums(value: object) -> list[set[str]]:
    found: list[set[str]] = []

    if isinstance(value, dict):
        for key, item in value.items():
            if key == "enum" and isinstance(item, list):
                values = set(item)
                if "RUNBOOK_GROUNDED" in values:
                    found.append(values)
            else:
                found.extend(find_hypothesis_source_enums(item))

    elif isinstance(value, list):
        for item in value:
            found.extend(find_hypothesis_source_enums(item))

    return found


def test_hypothesis_source_enums_are_aligned() -> None:
    schema_names = [
        "model-proposal.schema.json",
        "normalized-state.schema.json",
    ]

    for schema_name in schema_names:
        schema = json.loads((ROOT / "schemas" / schema_name).read_text())
        enums = find_hypothesis_source_enums(schema)

        assert enums == [EXPECTED_SOURCES]
