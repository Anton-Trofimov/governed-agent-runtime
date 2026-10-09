import json
from copy import deepcopy
from pathlib import Path
from typing import ClassVar

import pytest

from governed_agent_runtime import bc006_runner as runner
from governed_agent_runtime.bc006_runtime import SYSTEM, canonical

ROOT = Path(__file__).resolve().parents[2]


def test_review_packet_is_reproducible_and_bc004_passes():
    a, b = runner.build_review_packet(ROOT), runner.build_review_packet(ROOT)
    assert a == b
    assert a["actual_model_calls"] == 0
    assert a["human_pre_run_review"] == "PENDING"
    assert all(g["gate_pass"] for g in a["packet"]["traceability_results"])
    assert a["packet"]["nominal"]["summary"]["model_calls"] == 5
    assert a["packet"]["reject_then_repair"]["summary"]["model_calls"] == 6


def test_live_approval_rejects_pending_or_wrong_packet(monkeypatch):
    monkeypatch.setattr(
        runner.subprocess,
        "check_output",
        lambda cmd, **kw: "revision\n" if "rev-parse" in cmd else "",
    )
    packet = {"packet_sha256": "hash"}
    with pytest.raises(ValueError, match="approval"):
        runner.verify_approval(ROOT, {}, packet)
    approval = {
        "disposition": "APPROVED",
        "approved_revision": "revision",
        "packet_sha256": "hash",
        "scope": "BC-006_ONE_TRAJECTORY",
        "reviewer": "human",
        "reviewed_at": "2026-10-10",
    }
    assert runner.verify_approval(ROOT, approval, packet) == "revision"
    approval["packet_sha256"] = "wrong"
    with pytest.raises(ValueError):
        runner.verify_approval(ROOT, approval, packet)


def fake_gates(monkeypatch):
    monkeypatch.setattr(runner, "verify_approval", lambda *args: "test-revision")
    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: None)


class FakeOllama:
    mode = "normal"
    instances: ClassVar[list] = []

    def __init__(self, **kwargs):
        self.config = kwargs
        self.last_request_payload = None
        self.last_response_envelope = self.last_raw_response_body = self.last_response_metadata = (
            None
        )
        self.calls = 0
        self.instances.append(self)

    def resolve_provider_version(self):
        return "wrong" if self.mode == "version" else "0.32.14"

    def resolve_model_artifact_identity(self):
        return "22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643"

    def __call__(self, serialized):
        self.calls += 1
        self.last_request_payload = {
            "messages": [
                {"role": "system", "content": self.config["system_message"]},
                {"role": "user", "content": serialized},
            ]
        }
        if self.mode == "timeout":
            raise TimeoutError("test")
        ctx = json.loads(serialized)
        obs = ctx["observations"]
        if obs["desired"] == 6:
            tool, args = "scale_stable", {"desired_replicas": 8}
        elif obs["healthy"] == 6:
            tool, args = "read_operational_status", {}
        elif not obs["shift_id"]:
            tool, args = "shift_traffic_to_stable", {}
        elif obs["recovery"]["status"] != "PASS":
            tool, args = "read_post_shift_recovery", {"shift_id": obs["shift_id"]}
        else:
            tool, args = "finalize_rollback", {"shift_id": obs["shift_id"]}
        raw = canonical(runner.scripted_proposal(ctx, tool, args))
        self.last_response_envelope = {
            "done": True,
            "done_reason": "length" if self.mode == "truncated" else "stop",
            "message": {"content": raw},
        }
        self.last_raw_response_body = canonical(self.last_response_envelope)
        self.last_response_metadata = {"prompt_eval_count": 100, "eval_count": 100}
        return raw


@pytest.mark.parametrize("mode", ["normal", "timeout", "truncated", "version"])
def test_api_trajectory_retains_evidence_and_never_retries(mode, monkeypatch, tmp_path):
    fake_gates(monkeypatch)
    FakeOllama.mode = mode
    monkeypatch.setattr(runner, "OllamaChatModel", FakeOllama)
    output = tmp_path / "unique-run"
    result = runner.run_live(
        ROOT,
        output=output,
        provider="ollama",
        approval={},
        user_id="tester",
        confirm=lambda request: True,
    )
    expected = 5 if mode == "normal" else 0 if mode == "version" else 1
    assert result["actual_model_calls"] == expected
    assert FakeOllama.instances[-1].calls == expected
    assert result["status"] == ("COMPLETED" if mode == "normal" else "STOPPED")
    assert json.loads((output / "manifest.json").read_text()) == result
    if mode != "version":
        provider = json.loads((output / "step-01.provider.json").read_text())
        inp = json.loads((output / "step-01.input.json").read_text())
        assert provider["request"]["messages"] == inp["messages"]
    with pytest.raises(FileExistsError):
        runner.run_live(ROOT, output=output, provider="ollama", approval={}, user_id="tester")


@pytest.mark.parametrize("stale", [False, True])
def test_manual_transfer_is_exact_and_bound(stale, monkeypatch, tmp_path):
    fake_gates(monkeypatch)
    output = tmp_path / "manual"
    raw_files = []

    def response(_):
        pending_path = max(output.glob("step-*.input.json"))
        pending = json.loads(pending_path.read_text())
        ctx = pending["context"]
        # A safe stop tests transport without mimicking the whole planner.
        raw = canonical(
            {
                "context_id": ctx["context_id"],
                "tool_name": "STOP",
                "arguments": {},
                "rationale": "Stop this transport test",
            }
        )
        file = tmp_path / "reply.json"
        exact = json.dumps(
            {"raw_response": raw, "input_sha256": "old" if stale else pending["input_sha256"]}
        )
        file.write_text(exact)
        raw_files.append(exact.encode())
        return str(file)

    result = runner.run_live(
        ROOT,
        output=output,
        provider="manual",
        approval={},
        user_id="tester",
        manual_metadata={
            "model_identity": "test",
            "environment": "test",
            "independent_session_per_call": True,
        },
        manual_read=response,
    )
    assert result["outcome"]["stop_reason"] == (
        "INVALID_OR_STALE_PROPOSAL" if stale else "MODEL_REQUESTED_STOP"
    )
    assert (output / "step-01.manual.raw.json").read_bytes() == raw_files[0]
    assert (output / "step-01.prompt.txt").read_text().startswith(SYSTEM)


def test_actual_chat_adapter_supports_system_without_changing_default(monkeypatch):
    import governed_agent_runtime.ollama_model_adapter as adapter
    from governed_agent_runtime.ollama_model_adapter import OllamaChatModel

    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"message":{"content":"{}"},"done":true,"done_reason":"stop"}'

    def urlopen(request, **kwargs):
        captured.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr(adapter, "urlopen", urlopen)
    cfg = runner.build_review_packet(ROOT)["packet"]["model_config"]
    params = deepcopy(cfg["invocation_parameters"])
    params.pop("stream")
    for system in (None, SYSTEM):
        model = OllamaChatModel(
            base_url="http://localhost:1",
            model_identity="test",
            model_schema={},
            request_timeout_seconds=1,
            system_message=system,
            **params,
        )
        model("exact")
    assert captured[0]["messages"] == [{"role": "user", "content": "exact"}]
    assert captured[1]["messages"] == [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "exact"},
    ]
