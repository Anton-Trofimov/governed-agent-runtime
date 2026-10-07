import json
from pathlib import Path

from governed_agent_runtime import bc005_d1_self_review as d1
from governed_agent_runtime import bc005_s12_prospective_grounded as baseline

ROOT = Path(__file__).resolve().parents[2]


def test_only_change_is_final_generic_instruction() -> None:
    old = baseline.assemble_llm_probe_input(ROOT, baseline.load_bc005_context(ROOT))
    new = d1.assemble_diagnostic_input(ROOT)
    envelope = json.loads(new)
    assert list(envelope)[-1] == "final_review_instruction"
    assert envelope.pop("final_review_instruction") == d1.SELF_REVIEW_INSTRUCTION
    assert json.dumps(envelope, separators=(",", ":")) == old


def configured(monkeypatch):
    import runpy

    helpers = runpy.run_path(str(ROOT / "tests/contract/test_bc005_live_evaluation.py"))
    factory = helpers["Factory"]()
    original = factory.__call__

    def make_model(**config):
        model = original(**config)
        model.resolve_provider_version = lambda: "0.32.14"
        digest = d1._baseline_manifest(ROOT)["model_artifact_identity"]
        model.resolve_model_artifact_identity = lambda: digest
        return model

    monkeypatch.setattr(d1, "OllamaChatModel", make_model)
    monkeypatch.setattr(d1, "_SubprocessGitBoundary", helpers["GitStub"])
    monkeypatch.setattr(d1, "_run_required_verification", lambda root: {"status": "PASSED"})
    return factory, helpers["REVISION"]


def test_fixed_pool_is_isolated_and_offline_evaluable(monkeypatch, tmp_path):
    from governed_agent_runtime.bc005_offline_evaluator import evaluate_bc005_attempt

    factory, revision = configured(monkeypatch)
    output = tmp_path / "d1"
    manifest = d1.run_diagnostic(
        ROOT, evidence_directory=output, approved_revision=revision,
        human_pre_run_approved=True,
    )
    assert manifest["status"] == "COMPLETED"
    assert manifest["actual_measured_call_count"] == 3
    assert manifest["written_evidence_files"] == manifest["expected_evidence_files"]
    assert factory.models[0].received_inputs == [d1.assemble_diagnostic_input(ROOT)] * 4
    for path in output.rglob("*.json"):
        record = json.loads(path.read_text())
        assert record["experiment_id"] == "BC-005-D1"
        assert record["evidence_scope"] == "DIAGNOSTIC"
        assert record["decision_evidence_eligible"] is False
    for i in (1, 2, 3):
        result = evaluate_bc005_attempt(
            output / f"attempts/bc-005-d1-s12-run-{i}.raw.json",
            output / f"attempts/bc-005-d1-s12-run-{i}.result.json",
            ROOT / "evals/hidden/bc-005/s12/evaluation-case.json",
        )
        assert result["model_quality"]["status"] == "REVIEW_REQUIRED"
        assert result["runtime_containment"]["status"] == "PASS"


def test_approval_and_revision_gates_block_provider(monkeypatch, tmp_path):
    import pytest

    factory, revision = configured(monkeypatch)
    for approved, sha in ((False, revision), (True, "wrong")):
        with pytest.raises(ValueError):
            d1.run_diagnostic(
                ROOT, evidence_directory=tmp_path / "d1", approved_revision=sha,
                human_pre_run_approved=approved,
            )
    assert factory.calls == []


def test_baseline_drift_blocks_provider(monkeypatch, tmp_path):
    import pytest

    factory, revision = configured(monkeypatch)
    original = d1.live._sha256_file
    monkeypatch.setattr(d1.live, "_sha256_file", lambda path: (
        "wrong" if path.name == "context-package.json" else original(path)
    ))
    with pytest.raises(ValueError, match="baseline artifact drift"):
        d1.run_diagnostic(
            ROOT, evidence_directory=tmp_path / "d1", approved_revision=revision,
            human_pre_run_approved=True,
        )
    assert factory.calls == []


def test_raw_persisted_before_runtime_failure(monkeypatch, tmp_path):
    import pytest

    factory, revision = configured(monkeypatch)
    output = tmp_path / "d1"

    def fail_runtime(*args, **kwargs):
        assert (output / "attempts/bc-005-d1-s12-run-1.raw.json").exists()
        raise RuntimeError("injected runtime failure")

    monkeypatch.setattr(d1.probe._exp18_runner, "evaluate_proposal", fail_runtime)
    with pytest.raises(RuntimeError, match="injected runtime failure"):
        d1.run_diagnostic(
            ROOT, evidence_directory=output, approved_revision=revision,
            human_pre_run_approved=True,
        )
    assert json.loads((output / "manifest.json").read_text())["status"] == "FAILED"
    assert len(factory.models[0].received_inputs) == 2
