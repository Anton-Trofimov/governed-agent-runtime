"""Normalize authored tool contracts into canonical JSON Schema."""

from collections.abc import Mapping
from typing import Any


def normalize_contract_schema(value: Any) -> Any:
    """Return a recursively normalized copy of a tool-contract schema."""
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}

        for key, item in value.items():
            normalized_key = (
                "additionalProperties"
                if key == "additional_properties"
                else key
            )
            normalized[normalized_key] = normalize_contract_schema(item)

        return normalized

    if isinstance(value, list):
        return [
            normalize_contract_schema(item)
            for item in value
        ]

    return value
