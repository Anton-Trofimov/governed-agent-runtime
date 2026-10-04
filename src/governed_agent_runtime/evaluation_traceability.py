"""Deterministic validation for evaluation-expectation provenance."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


VISIBLE_ID_KEYS = frozenset({"context_id", "evidence_id", "constraint_id"})


class BasisType(StrEnum):
    """Allowed model-visible provenance types."""

    EXPLICIT_MODEL_VISIBLE = "EXPLICIT_MODEL_VISIBLE"
    DERIVED_FROM_MODEL_VISIBLE = "DERIVED_FROM_MODEL_VISIBLE"


class SemanticReviewDisposition(StrEnum):
    """Human disposition for a derived semantic expectation."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"


class TraceabilityEntry(BaseModel):
    """One material evaluator expectation and its claimed visible basis."""

    model_config = ConfigDict(extra="forbid")

    expectation_id: str = Field(min_length=1)
    required_behavior: str = Field(min_length=1)
    basis_type: BasisType
    visible_refs: list[str] = Field(min_length=1)
    derivation: str | None = None
    semantic_review_required: bool
    semantic_review_disposition: SemanticReviewDisposition | None = None

    @model_validator(mode="after")
    def validate_basis_semantics(self) -> TraceabilityEntry:
        if len(self.visible_refs) != len(set(self.visible_refs)):
            raise ValueError("visible_refs must be unique")

        if self.basis_type is BasisType.EXPLICIT_MODEL_VISIBLE:
            if self.semantic_review_required:
                raise ValueError("explicit mappings must not require semantic review")
            if self.derivation is not None:
                raise ValueError("explicit mappings must not provide a derivation")
            if self.semantic_review_disposition is not None:
                raise ValueError("explicit mappings must not provide a review disposition")
            return self

        if not self.semantic_review_required:
            raise ValueError("derived mappings must require semantic review")
        if self.derivation is None or not self.derivation.strip():
            raise ValueError("derived mappings require a non-empty derivation")
        if self.semantic_review_disposition is None:
            raise ValueError("derived mappings require a human review disposition")
        return self


class TraceabilityBundle(BaseModel):
    """Traceability mappings for all material expectations in one evaluation case."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1.0"]
    bounded_change_id: str | None = Field(default=None, min_length=1)
    case_id: str = Field(min_length=1)
    model_context_file: str = Field(min_length=1)
    material_expectation_ids: list[str] = Field(min_length=1)
    mappings: list[TraceabilityEntry]

    @model_validator(mode="after")
    def validate_identifiers(self) -> TraceabilityBundle:
        if len(self.material_expectation_ids) != len(set(self.material_expectation_ids)):
            raise ValueError("material_expectation_ids must be unique")
        mapping_ids = [entry.expectation_id for entry in self.mappings]
        if len(mapping_ids) != len(set(mapping_ids)):
            raise ValueError("mapping expectation_id values must be unique")
        return self


class ExpectationGateResult(BaseModel):
    """Deterministic gate result for one material expectation."""

    expectation_id: str
    status: Literal["PASS", "FAIL"]
    reasons: list[str] = Field(default_factory=list)
    resolved_visible_refs: dict[str, dict[str, Any]] = Field(default_factory=dict)


class TraceabilityGateResult(BaseModel):
    """Aggregate deterministic traceability-gate result."""

    gate_pass: bool
    expectations: list[ExpectationGateResult]
    undeclared_mapping_ids: list[str] = Field(default_factory=list)


def _collect_visible_refs(
    value: Any,
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    """Collect exact canonical model-visible IDs and detect ambiguous duplicates."""
    index: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            record = dict(item)
            for key in VISIBLE_ID_KEYS:
                identifier = item.get(key)
                if isinstance(identifier, str) and identifier:
                    if identifier in index and index[identifier] != record:
                        duplicates.add(identifier)
                    else:
                        index[identifier] = record
            for child in item.values():
                visit(child)
            return

        if isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return index, duplicates


def evaluate_traceability(
    bundle: TraceabilityBundle,
    model_context: Mapping[str, Any],
) -> TraceabilityGateResult:
    """Evaluate the BC-004 traceability gate.

    The first implementation step intentionally leaves gate behavior unimplemented so
    focused contract tests can establish the required RED state before implementation.
    """
    del bundle, model_context
    return TraceabilityGateResult(gate_pass=False, expectations=[])
