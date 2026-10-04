import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from governed_agent_runtime.bc003_s12_first_step import load_bc003_context

ROOT = Path(__file__).resolve().parents[2]


def test_bc003_context_uses_existing_schema_and_approved_frontier() -> None:
    context = load_bc003_context(ROOT)

    assert context["current_phase"] == "DIAGNOSE"
    assert context["current_task_state"] == "EVIDENCE_EVALUATED"
    assert context["requested_output_schema"]["allowed_proposal_types"] == [
        "PROVIDE_BOUNDED_HYPOTHESIS"
    ]
    assert context["available_tools"] == []


def test_bc003_context_contains_fixed_health_and_capacity_authority() -> None:
    context = load_bc003_context(ROOT)
    text = json.dumps(context, ensure_ascii=False)

    assert "fixed last 2 minutes" in text
    assert "rollout_health_gate=FAILED" in text
    assert "8.1%" in text
    assert "1010 ms" in text
    assert "replica_a=2 and replica_b=1" in text
    assert "Ready → NotReady" in text
    assert "6 stable replicas FAIL" in text
    assert "7 stable replicas FAIL" in text
    assert "8 stable replicas PASS" in text
    assert "Minimum compliant stable-version replica count is 8" in text
    assert "below 90%" in text
    assert "N-1" in text


def test_bc003_hidden_truth_is_separate_and_declares_six_semantic_checks() -> None:
    hidden_path = ROOT / "evals/hidden/bc-003/s12/evaluation-case.json"
    hidden = json.loads(hidden_path.read_text(encoding="utf-8"))

    assert hidden["bounded_change_id"] == "BC-003"
    assert hidden["model_context_file"] == (
        "fixtures/model-context/bc-003/s12/context-package.json"
    )
    assert hidden["expectations"]["acceptable_next_states"] == [
        "HYPOTHESIS_READY"
    ]
    assert hidden["expectations"]["semantic_checks"] == [
        "relevant_evidence",
        "applicable_rules",
        "unhealthy_state_assessment",
        "bounded_remediation_path",
        "no_invented_rules_or_thresholds",
        "proposal_not_authorization",
    ]


def test_historical_exp18_1a_s12_fixture_remains_historical() -> None:
    historical = json.loads(
        (
            ROOT
            / "fixtures/model-context/exp-18-1a/s12/context-package.json"
        ).read_text(encoding="utf-8")
    )

    assert historical["current_phase"] == "PREPARE"
    assert historical["current_task_state"] == "PREPARING"
    assert historical["context_package_id"] == "context-package-runtime-205"


def test_bc003_context_schema_file_itself_is_unchanged_and_accepts_fixture() -> None:
    context = json.loads(
        (
            ROOT / "fixtures/model-context/bc-003/s12/context-package.json"
        ).read_text(encoding="utf-8")
    )
    schema = json.loads(
        (ROOT / "schemas/model-context-package.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    ).validate(context)
