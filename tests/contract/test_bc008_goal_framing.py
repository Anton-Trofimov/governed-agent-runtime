"""Bounded goal/seed isolation; only offline and fake-provider execution."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from governed_agent_runtime import bc006_runner as runner
from governed_agent_runtime.bc006_runtime import RemediationRuntime, canonical

ROOT = Path(__file__).resolve().parents[2]


def context(variant=None):
    return RemediationRuntime(
        ROOT, clock=runner.fixed_clock, session_id="paired", goal_variant=variant
    ).issue_context()


def test_only_goal_changes_and_no_detailed_route_leaks():
    old, a, b = context(), context("A"), context("B")
    cfg = json.loads((ROOT / "specs/core/bc008-goal-framing.json").read_text())
    for variant, c in [("A", a), ("B", b)]:
        assert c["current_goal"] == cfg["goals"][variant]
        assert c["applicable_constraints"][0]["description"] == cfg["goals"][variant]
        assert old["current_goal"] not in canonical(c)
        c["context_id"] = old["context_id"]
        c["current_goal"] = old["current_goal"]
        c["applicable_constraints"][0]["description"] = old["current_goal"]
        assert c == old
    assert context() == old  # no mutation of shared legacy profile
    with pytest.raises(ValueError):
        context("C")


def test_packet_covers_six_cases_and_separates_recovery_from_completion():
    p = runner.build_review_packet(ROOT, experiment="BC-008")
    assert p == runner.build_review_packet(ROOT, experiment="BC-008")
    assert list(p["packet"]["cases"]) == ["A-18", "B-18", "B-19", "A-19", "A-20", "B-20"]
    for run_id, case in p["packet"]["cases"].items():
        assert case["model_config"]["invocation_parameters"]["seed"] == int(run_id[2:])
    for variant in ["A", "B"]:
        ctl = p["packet"]["controls"][variant]
        assert ctl["complete"]["summary"]["task_completed"]
        stop = ctl["stop_after_pass"]
        assert stop["summary"]["stop_reason"] == "MODEL_REQUESTED_STOP"
        assert not stop["summary"]["task_completed"]
        assert stop["final_observation"]["recovery"]["status"] == "PASS"
        assert stop["final_observation"]["candidate_count"] == 2
    assert p["actual_model_calls"] == 0


def test_approval_cannot_cross_case_or_bypass_semantic_review(monkeypatch):
    monkeypatch.setattr(
        runner.subprocess,
        "check_output",
        lambda cmd, **kw: "revision\n" if "rev-parse" in cmd else "",
    )
    packet = runner.build_review_packet(ROOT, experiment="BC-008")
    approval = {
        "disposition": "APPROVED",
        "scope": "BC-008_ONE_TRAJECTORY",
        "approved_revision": "revision",
        "packet_sha256": packet["packet_sha256"],
        "reviewer": "human",
        "reviewed_at": "2026-10-12",
        "run_id": "A-18",
        "variant": "A",
        "seed": 18,
        "approved_derived_expectations": ["operator-goal-recovery-evidence"],
    }
    assert runner.verify_approval(ROOT, approval, packet, "BC-008", "A-18") == "revision"
    for field, value in [
        ("scope", "BC-007_ONE_TRAJECTORY"),
        ("seed", 19),
        ("variant", "B"),
        ("run_id", "B-18"),
        ("packet_sha256", "wrong"),
        ("approved_derived_expectations", []),
    ]:
        bad = deepcopy(approval)
        bad[field] = value
        with pytest.raises(ValueError):
            runner.verify_approval(ROOT, bad, packet, "BC-008", "A-18")
    with pytest.raises(ValueError):
        runner.verify_approval(ROOT, approval, packet, "BC-008", "A-99")


@pytest.mark.parametrize("variant", ["A", "B"])
def test_short_goal_does_not_weaken_capacity_gate(variant):
    rt = RemediationRuntime(ROOT, clock=runner.fixed_clock, goal_variant=variant)
    c = rt.issue_context()
    confirmations = []
    rt.submit(
        canonical(runner.scripted_proposal(c, "shift_traffic_to_stable")),
        confirm=lambda x: confirmations.append(x) or True,
    )
    assert rt.rejections == 1
    assert not confirmations and not rt.adapter_calls


@pytest.mark.parametrize("variant", ["A", "B"])
def test_goal_does_not_permit_removal_without_recovery(variant):
    from test_bc006_remediation import propose, shifted

    rt = RemediationRuntime(ROOT, clock=runner.fixed_clock, goal_variant=variant)
    sid = shifted(rt)
    calls = len(rt.adapter_calls)
    confirmations = []
    propose(
        rt,
        "finalize_rollback",
        {"shift_id": sid},
        confirm=lambda x: confirmations.append(x) or True,
    )
    assert rt.rejections == 1
    assert len(rt.adapter_calls) == calls and not confirmations
    assert rt.observation["candidate_count"] == 2


@pytest.mark.parametrize("run_id", ["A-18", "B-18", "B-19", "A-19", "A-20", "B-20"])
def test_runner_sends_exact_case_goal_seed_and_records_lineage(run_id, monkeypatch, tmp_path):
    from test_bc006_runner import FakeOllama, fake_gates

    class CaseFake(FakeOllama):
        mode = "normal"

        def __call__(self, serialized):
            ctx = json.loads(serialized)
            assert ctx["current_goal"] == goal
            assert ctx["applicable_constraints"][0]["description"] == goal
            assert self.config["seed"] == seed
            return super().__call__(serialized)

    variant, seed_text = run_id.split("-")
    seed = int(seed_text)
    goal = json.loads((ROOT / "specs/core/bc008-goal-framing.json").read_text())["goals"][variant]
    fake_gates(monkeypatch)
    monkeypatch.setattr(runner, "OllamaChatModel", CaseFake)
    result = runner.run_live(
        ROOT,
        output=tmp_path / run_id,
        provider="ollama",
        approval={},
        user_id="tester",
        confirm=lambda _: True,
        experiment="BC-008",
        run_id=run_id,
    )
    assert result["status"] == "COMPLETED"
    assert result["scope"] == "BC-008"
    assert result["fixture_id"] == "bc008-s12-nominal-v1"
    assert result["case"] == {
        "run_id": run_id,
        "variant": variant,
        "seed": seed,
        "operator_goal": goal,
    }
    assert result["model_config"]["invocation_parameters"]["seed"] == seed
    first = json.loads((tmp_path / run_id / "step-01.input.json").read_text())["context"]
    assert first["observations"]["desired"] == first["observations"]["healthy"] == 6
    assert first["ledger"] == []
    assert result["outcome"]["write_calls"] == 3
