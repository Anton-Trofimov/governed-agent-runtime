import json
from pathlib import Path

from governed_agent_runtime.bc006_runtime import RemediationRuntime

ROOT = Path(__file__).resolve().parents[2]


def test_shift_at_six_is_rejected_before_adapter_and_feedback_is_explicit():
    runtime = RemediationRuntime(ROOT)
    context = runtime.issue_context()
    runtime.submit(
        json.dumps(
            {
                "context_id": context["context_id"],
                "tool_name": "shift_traffic_to_stable",
                "arguments": context["target"],
                "rationale": "Move traffic off degraded candidate",
            }
        ),
        confirm=lambda request: True,
    )
    assert runtime.adapter_calls == []
    context = runtime.issue_context()
    assert context["last_step"]["execution_started"] is False
    assert context["last_step"]["decision"] == "REPLACE_WITH_SAFER_PATH"
    assert context["observations"]["healthy"] == 6
    assert context["observations"]["stable_traffic_rps"] == 615


from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from governed_agent_runtime.bc006_runtime import canonical, capacity, digest
from governed_agent_runtime.state_transition import apply_remediation_event


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 10, tzinfo=UTC)

    def __call__(self):
        return self.now


def propose(runtime, tool, extra=None, confirm=lambda request: True):
    ctx = runtime.issue_context()
    assert ctx is not None
    args = {} if tool == "STOP" else ctx["target"] | (extra or {})
    proposal = {
        "context_id": ctx["context_id"],
        "tool_name": tool,
        "arguments": args,
        "rationale": "Fixture proposal, not model evidence",
    }
    runtime.submit(canonical(proposal), confirm=confirm)
    return ctx


def ready(runtime):
    propose(runtime, "scale_stable", {"desired_replicas": 8})
    propose(runtime, "read_operational_status")


def shifted(runtime):
    ready(runtime)
    propose(runtime, "shift_traffic_to_stable")
    return runtime.observation["shift_id"]


def happy(runtime):
    sid = shifted(runtime)
    propose(runtime, "read_post_shift_recovery", {"shift_id": sid})
    propose(runtime, "finalize_rollback", {"shift_id": sid})


def test_scripted_path_separates_requested_observed_and_terminal_and_counts():
    rt = RemediationRuntime(ROOT, clock=Clock())
    initial = propose(rt, "scale_stable", {"desired_replicas": 8})
    assert initial["capacity"]["pass"] is False
    assert rt.observation["desired"] == 8 and rt.observation["healthy"] == 6
    assert rt.observation["scale_status"] == "PENDING"
    pending = propose(rt, "read_operational_status")
    assert pending["observations"]["healthy"] == 6
    assert rt.observation["healthy"] == 8
    assert capacity(rt.observation)["pass"] is True
    propose(rt, "shift_traffic_to_stable")
    sid = rt.observation["shift_id"]
    assert rt.observation["recovery"]["status"] == "PENDING"
    propose(rt, "read_post_shift_recovery", {"shift_id": sid})
    assert rt.observation["recovery"]["status"] == "PASS"
    propose(rt, "finalize_rollback", {"shift_id": sid})
    assert rt.summary() == {
        "task_state": "COMPLETED",
        "stop_reason": None,
        "task_completed": True,
        "model_calls": 5,
        "tool_calls": 9,
        "write_calls": 3,
        "rejections": 0,
        "recovery_after_rejection": "NOT_OBSERVED",
    }
    assert rt.observation["candidate_count"] == 0
    assert rt.adapter_calls[-1]["tool_name"] == "read_operational_status"
    assert [c["status"] for c in rt.confirmations] == ["CONSUMED"] * 3
    with pytest.raises(ValueError):
        rt.issue_context()


@pytest.mark.parametrize("healthy,desired", [(6, 6), (7, 7), (6, 8)])
def test_insufficient_actual_capacity_never_calls_write(healthy, desired):
    fixture = json.loads((ROOT / "fixtures/scenarios/bc-006/s12.json").read_text())
    fixture["initial"].update(healthy=healthy, desired=desired)
    rt = RemediationRuntime(ROOT, clock=Clock(), fixture=fixture)
    propose(rt, "shift_traffic_to_stable")
    assert not rt.adapter_calls
    assert rt.last_step["execution_started"] is False
    assert not rt.terminal


def test_rejected_then_repaired_completes_without_hidden_advice():
    rt = RemediationRuntime(ROOT, clock=Clock())
    propose(rt, "shift_traffic_to_stable")
    happy(rt)
    assert rt.summary()["recovery_after_rejection"] == "OBSERVED"
    assert rt.model_calls == 6
    assert len([c for c in rt.adapter_calls if c["write"]]) == 3
    assert rt.inputs[1]["context"]["last_step"]["result"] is None


def test_repeat_rejection_and_third_distinct_rejection_stop():
    rt = RemediationRuntime(ROOT, clock=Clock())
    propose(rt, "shift_traffic_to_stable")
    propose(rt, "shift_traffic_to_stable")
    assert rt.stop_reason == "REPEATED_REJECTION"
    assert not rt.adapter_calls
    rt = RemediationRuntime(ROOT, clock=Clock())
    propose(rt, "shift_traffic_to_stable")
    propose(rt, "read_post_shift_recovery", {"shift_id": "foreign-a"})
    propose(rt, "finalize_rollback", {"shift_id": "foreign-b"})
    assert rt.stop_reason == "REJECTION_BUDGET_EXHAUSTED"
    assert not rt.adapter_calls


@pytest.mark.parametrize("status", ["PENDING", "FAIL", "UNKNOWN"])
def test_removal_needs_recovery_pass(status):
    rt = RemediationRuntime(ROOT, clock=Clock())
    sid = shifted(rt)
    rt.observation["recovery"]["status"] = status
    before = deepcopy(rt.adapter_calls)
    propose(rt, "finalize_rollback", {"shift_id": sid})
    assert rt.adapter_calls == before
    assert rt.observation["candidate_count"] == 2


@pytest.mark.parametrize("change", ["foreign", "stale", "future"])
def test_recovery_pass_must_be_fresh_and_bound(change):
    clock = Clock()
    rt = RemediationRuntime(ROOT, clock=clock)
    sid = shifted(rt)
    propose(rt, "read_post_shift_recovery", {"shift_id": sid})
    if change == "foreign":
        rt.observation["recovery"]["shift_id"] = "foreign"
    else:
        delta = timedelta(seconds=-1801 if change == "stale" else 10)
        rt.observation["recovery"]["observed_at"] = (clock() + delta).isoformat()
    calls = len(rt.adapter_calls)
    propose(rt, "finalize_rollback", {"shift_id": sid})
    assert len(rt.adapter_calls) == calls


@pytest.mark.parametrize("mode", ["reject", "expire", "state", "parameters", "role"])
def test_confirmation_boundaries(mode):
    clock = Clock()
    rt = RemediationRuntime(ROOT, clock=clock)

    def confirm(request):
        if mode == "reject":
            return False
        if mode == "expire":
            clock.now += timedelta(seconds=300)
        elif mode == "state":
            rt.env.state["total_rps"] = 900
        elif mode == "parameters":
            rt.prepared["arguments"]["desired_replicas"] = 7
        elif mode == "role":
            rt.role_authorized = False
        return True

    propose(rt, "scale_stable", {"desired_replicas": 8}, confirm=confirm)
    assert not rt.adapter_calls
    assert rt.confirmations[0]["status"] in {"REJECTED", "EXPIRED", "INVALIDATED"}
    assert rt.observation["desired"] == 6


@pytest.mark.parametrize("change", ["extra", "context", "target", "tool"])
def test_untrusted_proposal_cannot_inject_runtime_fields(change):
    rt = RemediationRuntime(ROOT, clock=Clock())
    ctx = rt.issue_context()
    proposal = {
        "context_id": ctx["context_id"],
        "tool_name": "scale_stable",
        "arguments": ctx["target"] | {"desired_replicas": 8},
        "rationale": "scale",
    }
    if change == "extra":
        proposal["arguments"]["remediation_plan_id"] = "forged"
    elif change == "context":
        proposal["context_id"] = "old"
    elif change == "target":
        proposal["arguments"]["deployment_target_id"] = "other"
    else:
        proposal["tool_name"] = "shell"
    rt.submit(canonical(proposal), confirm=lambda req: pytest.fail("No confirmation expected"))
    assert not rt.adapter_calls
    assert rt.terminal


def test_stale_observation_requires_read_and_refresh():
    clock = Clock()
    rt = RemediationRuntime(ROOT, clock=clock)
    clock.now += timedelta(seconds=1801)
    propose(rt, "scale_stable", {"desired_replicas": 8})
    assert not rt.adapter_calls
    propose(rt, "read_operational_status")
    propose(rt, "scale_stable", {"desired_replicas": 8})
    assert rt.write_calls == 1


@pytest.mark.parametrize("fault", ["timeout", "schema", "scope", "foreign_recovery"])
def test_bad_write_result_stops_without_applying_or_retry(fault):
    rt = RemediationRuntime(ROOT, clock=Clock())
    original = rt.env.call
    before = deepcopy(rt.observation)

    def broken(name, args):
        result = original(name, args)
        if fault == "timeout":
            raise TimeoutError("Unknown result")
        if fault == "schema":
            result["observation"]["healthy"] = "8"
        elif fault == "scope":
            result["observation"]["scope"]["service_id"] = "wrong"
        else:
            result["observation"]["recovery"]["status"] = "PASS"
        return result

    rt.env.call = broken
    propose(rt, "scale_stable", {"desired_replicas": 8})
    assert rt.observation == before
    assert rt.stop_reason == "UNKNOWN_WRITE_OUTCOME"
    assert len(rt.adapter_calls) == 1


def test_context_replay_visibility_and_no_double_inference():
    clock = Clock()
    rt = RemediationRuntime(ROOT, clock=clock)
    propose(rt, "shift_traffic_to_stable")
    ready(rt)
    ctx = rt.assemble_context()
    assert canonical(ctx) == canonical(rt.assemble_context())
    assert ctx["observations"]["healthy"] == 8
    assert len(ctx["ledger"]) == 3
    assert ctx["ledger"][0]["execution_started"] is False
    assert ctx["ledger"][1]["result"]["healthy"] == 6
    assert ctx["ledger"][1]["result"]["desired"] == 8
    text = canonical(ctx)
    for forbidden in ("environment_schedule", "scale_ready_after_ticks", "state_hash", "plan_hash"):
        assert forbidden not in text
    rt.issue_context()
    with pytest.raises(ValueError):
        rt.issue_context()
    assert digest(rt.pending["messages"]) == rt.pending["input_sha256"]


def test_budgets_and_context_overflow_stop_without_extra_calls():
    rt = RemediationRuntime(ROOT, clock=Clock())
    rt.model_calls = 16
    assert rt.issue_context() is None
    assert rt.stop_reason == "MODEL_BUDGET_EXHAUSTED"
    rt = RemediationRuntime(ROOT, clock=Clock())
    rt.tool_calls = 19
    propose(rt, "scale_stable", {"desired_replicas": 8})
    assert not rt.adapter_calls
    rt = RemediationRuntime(ROOT, clock=Clock())
    rt.profile["budgets"]["context_bytes"] = 1
    assert rt.issue_context() is None
    assert rt.stop_reason == "CONTEXT_OVERFLOW_DESIGN_FAILURE"


def test_terminal_state_cannot_be_reopened():
    rt = RemediationRuntime(ROOT, clock=Clock())
    for terminal in ("COMPLETED", "BLOCKED", "FAILED", "SAFE_FALLBACK"):
        with pytest.raises(ValueError):
            apply_remediation_event(terminal, "continue", profile=rt.profile)


def test_reused_response_cannot_reuse_consumed_confirmation():
    rt = RemediationRuntime(ROOT, clock=Clock())
    ctx = rt.issue_context()
    proposal = canonical(
        {
            "context_id": ctx["context_id"],
            "tool_name": "scale_stable",
            "arguments": ctx["target"] | {"desired_replicas": 8},
            "rationale": "scale",
        }
    )
    rt.submit(proposal, confirm=lambda req: True)
    with pytest.raises(ValueError):
        rt.submit(proposal, confirm=lambda req: True)
    assert rt.write_calls == 1
    assert rt.confirmations[0]["status"] == "CONSUMED"


def test_read_does_not_manufacture_readiness_and_different_schedule_is_honored():
    fixture = json.loads((ROOT / "fixtures/scenarios/bc-006/s12.json").read_text())
    fixture["environment_schedule"]["scale_ready_after_ticks"] = 3
    rt = RemediationRuntime(ROOT, fixture=fixture, clock=Clock())
    propose(rt, "scale_stable", {"desired_replicas": 8})
    propose(rt, "read_operational_status")
    assert rt.observation["healthy"] == 6
    tick = rt.env.tick
    propose(rt, "shift_traffic_to_stable")
    assert rt.env.tick == tick
    propose(rt, "read_operational_status")
    assert rt.observation["healthy"] == 6
    propose(rt, "read_operational_status")
    assert rt.observation["healthy"] == 8


def test_recovery_failure_is_observed_but_not_admitted_for_removal():
    fixture = json.loads((ROOT / "fixtures/scenarios/bc-006/s12.json").read_text())
    fixture["environment_schedule"]["recovery_outcome"] = "FAIL"
    rt = RemediationRuntime(ROOT, fixture=fixture, clock=Clock())
    sid = shifted(rt)
    propose(rt, "read_post_shift_recovery", {"shift_id": sid})
    assert rt.observation["recovery"]["status"] == "FAIL"
    calls = len(rt.adapter_calls)
    propose(rt, "finalize_rollback", {"shift_id": sid})
    assert len(rt.adapter_calls) == calls
    assert not rt.summary()["task_completed"]


def test_successful_write_ack_is_not_terminal_without_final_observation():
    rt = RemediationRuntime(ROOT, clock=Clock())
    sid = shifted(rt)
    propose(rt, "read_post_shift_recovery", {"shift_id": sid})
    original = rt.env.call

    def final_read_fails(name, args):
        if name == "read_operational_status":
            raise TimeoutError("final verification unavailable")
        return original(name, args)

    rt.env.call = final_read_fails
    propose(rt, "finalize_rollback", {"shift_id": sid})
    assert rt.observation["candidate_count"] == 0
    assert rt.task_state == "FAILED"
    assert not rt.summary()["task_completed"]


def test_read_of_same_facts_does_not_reset_rejection_signature():
    rt = RemediationRuntime(ROOT, clock=Clock())
    propose(rt, "shift_traffic_to_stable")
    propose(rt, "read_operational_status")
    propose(rt, "shift_traffic_to_stable")
    assert rt.stop_reason == "REPEATED_REJECTION"


def test_scale_ack_cannot_claim_unobserved_readiness():
    rt = RemediationRuntime(ROOT, clock=Clock())
    original = rt.env.call

    def forged_readiness(name, args):
        result = original(name, args)
        result["observation"]["healthy"] = 8
        result["observation"]["scale_status"] = "SUCCEEDED"
        return result

    rt.env.call = forged_readiness
    propose(rt, "scale_stable", {"desired_replicas": 8})
    assert rt.stop_reason == "UNKNOWN_WRITE_OUTCOME"
    assert rt.observation["healthy"] == 6
