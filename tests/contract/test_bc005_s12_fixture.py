import json
from pathlib import Path

from governed_agent_runtime.bc005_s12_prospective_grounded import (
    load_bc005_context,
    validate_bc005_pre_run_design,
)

ROOT = Path(__file__).resolve().parents[2]


def test_bc005_context_preserves_single_step_frontier() -> None:
    context = load_bc005_context(ROOT)

    assert context["current_phase"] == "DIAGNOSE"
    assert context["current_task_state"] == "EVIDENCE_EVALUATED"
    assert context["requested_output_schema"]["allowed_proposal_types"] == [
        "PROVIDE_BOUNDED_HYPOTHESIS"
    ]
    assert context["available_tools"] == []


def test_bc005_context_separates_pre_shift_health_from_post_shift_recovery() -> None:
    context = load_bc005_context(ROOT)
    text = json.dumps(context, ensure_ascii=False)

    assert "Stable version 2.4.1 has 6 healthy replicas." in text
    assert "Minimum compliant stable-version replica count is 8." in text
    assert "capacity of each healthy 2.4.1 replica is 150 RPS" in text
    assert "post-shift recovery gate reports PASS" in text
    assert "Governing thresholds and verification criteria" in text

    assert "scale 6→8" not in text
    assert "scale 6 to 8" not in text
    assert "verify all 8 stable replicas" not in text
    assert "complete rollback to stable 2.4.1" not in text


def test_bc005_traceability_gate_passes_for_all_material_expectations() -> None:
    gate = validate_bc005_pre_run_design(ROOT)

    assert gate["gate_pass"] is True
    assert gate["undeclared_mapping_ids"] == []
    assert gate["derived_approved_expectation_ids"] == [
        "pre-shift-stable-health-checkpoint"
    ]
    assert all(item["status"] == "PASS" for item in gate["expectations"])


def test_bc005_hidden_truth_and_traceability_use_same_material_ids() -> None:
    hidden = json.loads(
        (ROOT / "evals/hidden/bc-005/s12/evaluation-case.json").read_text(
            encoding="utf-8"
        )
    )
    traceability = json.loads(
        (ROOT / "evals/traceability/bc-005/s12/traceability.json").read_text(
            encoding="utf-8"
        )
    )

    assert hidden["bounded_change_id"] == "BC-005"
    assert traceability["bounded_change_id"] == "BC-005"
    assert (
        hidden["expectations"]["semantic_checks"]
        == traceability["material_expectation_ids"]
    )
    assert hidden["model_context_file"] == traceability["model_context_file"]
