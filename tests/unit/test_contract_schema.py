from copy import deepcopy

from governed_agent_runtime.contract_schema import (
    normalize_contract_schema,
)


def test_contract_schema_is_normalized_recursively_without_mutation() -> None:
    authored_schema = {
        "type": "object",
        "additional_properties": False,
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additional_properties": False,
                },
            },
        },
    }
    original_schema = deepcopy(authored_schema)

    normalized = normalize_contract_schema(authored_schema)

    assert normalized["additionalProperties"] is False
    assert (
        normalized["properties"]["items"]["items"][
            "additionalProperties"
        ]
        is False
    )

    assert authored_schema == original_schema
    assert "additional_properties" in authored_schema
    assert "additionalProperties" not in authored_schema
