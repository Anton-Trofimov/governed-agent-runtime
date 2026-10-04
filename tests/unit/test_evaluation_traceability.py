import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from governed_agent_runtime.evaluation_traceability import (
    TraceabilityBundle,
    evaluate_traceability,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _context() -> dict:
    return {
        "observed_state_summary": [
            {
                "context_id": "obs-1",
                "summary": "Stable replicas are healthy.",
            }
        ],
        "evidence_summary": [
            {
                "evidence_id": "ev-1",
                "summary": "Capacity finding is authoritative.",
            }
        ],
        "applicable_constraints": [
            {
                "constraint_id": "R1",
                "description": "Use the supplied capacity finding.",
            }
        ],
    }


def _bundle(mapping: dict, *, material_ids: list[str] | None = None) -> TraceabilityBundle:
    return TraceabilityBundle.model_validate(
        {
            "schema_version": "0.1.0",
            "case_id": "test-case",
            "model_context_file": "fixtures/test-context.json",
            "material_expectation_ids": material_ids or [mapping["expectation_id"]],
            "mappings": [mapping],
        }
    )


def _explicit_mapping(**overrides: object) -> dict:
    mapping = {
        "expectation_id": "explicit-1",
        "required_behavior": "Preserve the authoritative capacity finding.",
        "basis_type": "EXPLICIT_MODEL_VISIBLE",
        "visible_refs": ["ev-1", "R1"],
        "semantic_review_required": False,
    }
    mapping.update(overrides)
    return mapping


def _derived_mapping(**overrides: object) -> dict:
    mapping = {
        "expectation_id": "derived-1",
        "required_behavior": "Verify the stable replicas before traffic shift.",
        "basis_type": "DERIVED_FROM_MODEL_VISIBLE",
        "visible_refs": ["obs-1", "ev-1", "R1"],
        "derivation": "The compliant state depends on healthy stable replicas.",
        "semantic_review_required": True,
        "semantic_review_disposition": "APPROVED",
    }
    mapping.update(overrides)
    return mapping


def _result_for(result, expectation_id: str):
    return next(item for item in result.expectations if item.expectation_id == expectation_id)


def test_traceability_schema_accepts_bc003_diagnostic_bundle() -> None:
    schema = json.loads((REPO_ROOT / "schemas/evaluation-traceability.schema.json").read_text())
    bundle = json.loads(
        (
            REPO_ROOT
            / "evals/traceability/bc-003/s12/traceability.json"
        ).read_text()
    )

    Draft202012Validator(schema).validate(bundle)


def test_explicit_mapping_with_existing_refs_passes() -> None:
    result = evaluate_traceability(_bundle(_explicit_mapping()), _context())

    item = _result_for(result, "explicit-1")
    assert result.gate_pass is True
    assert item.status == "PASS"
    assert item.reasons == []
    assert item.resolved_visible_refs["ev-1"]["summary"] == "Capacity finding is authoritative."


def test_explicit_mapping_with_missing_ref_fails() -> None:
    mapping = _explicit_mapping(visible_refs=["missing-ref"])

    result = evaluate_traceability(_bundle(mapping), _context())

    item = _result_for(result, "explicit-1")
    assert result.gate_pass is False
    assert item.status == "FAIL"
    assert "UNKNOWN_VISIBLE_REF:missing-ref" in item.reasons


def test_derived_mapping_with_approved_review_passes() -> None:
    result = evaluate_traceability(_bundle(_derived_mapping()), _context())

    item = _result_for(result, "derived-1")
    assert result.gate_pass is True
    assert item.status == "PASS"


def test_derived_mapping_with_pending_review_fails() -> None:
    mapping = _derived_mapping(semantic_review_disposition="PENDING")

    result = evaluate_traceability(_bundle(mapping), _context())

    item = _result_for(result, "derived-1")
    assert result.gate_pass is False
    assert "HUMAN_REVIEW_PENDING" in item.reasons


def test_derived_mapping_with_rejected_review_fails() -> None:
    mapping = _derived_mapping(semantic_review_disposition="REJECTED")

    result = evaluate_traceability(_bundle(mapping), _context())

    item = _result_for(result, "derived-1")
    assert result.gate_pass is False
    assert "HUMAN_REVIEW_REJECTED" in item.reasons


def test_derived_mapping_without_derivation_is_contract_invalid() -> None:
    mapping = _derived_mapping()
    del mapping["derivation"]

    with pytest.raises(ValidationError, match="non-empty derivation"):
        _bundle(mapping)


def test_material_expectation_without_mapping_fails() -> None:
    bundle = _bundle(
        _explicit_mapping(),
        material_ids=["explicit-1", "missing-mapping"],
    )

    result = evaluate_traceability(bundle, _context())

    item = _result_for(result, "missing-mapping")
    assert result.gate_pass is False
    assert item.status == "FAIL"
    assert item.reasons == ["MAPPING_MISSING"]


def test_bc003_diagnostic_distinguishes_explicit_approved_and_rejected_basis() -> None:
    bundle = TraceabilityBundle.model_validate_json(
        (
            REPO_ROOT
            / "evals/traceability/bc-003/s12/traceability.json"
        ).read_text()
    )
    context = json.loads(
        (
            REPO_ROOT
            / "fixtures/model-context/bc-003/s12/context-package.json"
        ).read_text()
    )

    result = evaluate_traceability(bundle, context)

    minimum = _result_for(result, "minimum-8-stable-replicas")
    pre_shift = _result_for(result, "verify-stable-before-shift")
    recovery = _result_for(result, "verify-recovery-before-remove")

    assert minimum.status == "PASS"
    assert pre_shift.status == "PASS"
    assert recovery.status == "FAIL"
    assert recovery.reasons == ["HUMAN_REVIEW_REJECTED"]
    assert result.gate_pass is False


def test_undeclared_mapping_blocks_gate() -> None:
    bundle = TraceabilityBundle.model_validate(
        {
            "schema_version": "0.1.0",
            "case_id": "test-case",
            "model_context_file": "fixtures/test-context.json",
            "material_expectation_ids": ["explicit-1"],
            "mappings": [
                _explicit_mapping(),
                _explicit_mapping(expectation_id="extra-mapping"),
            ],
        }
    )

    result = evaluate_traceability(bundle, _context())

    assert result.gate_pass is False
    assert result.undeclared_mapping_ids == ["extra-mapping"]
