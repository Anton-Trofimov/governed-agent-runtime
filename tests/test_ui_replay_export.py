"""Recorded presentation must preserve source events and accepted observations."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ui_export", ROOT / "ui/scripts/export_runs.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize("name,relative", MODULE.RUNS.items())
def test_exported_replay_preserves_source_and_observation_boundary(name, relative):
    directory = ROOT / "evidence" / relative
    trace = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
    replay = MODULE.build_replay(trace)
    source = {event["event_id"]: event for event in trace}
    assert replay["events"][0]["observation"] == trace[0]["state"]
    for frame in replay["events"]:
        event = source[frame["source"]]
        assert frame["at"] == event["at"]
        assert frame["kind"] == event["kind"]
        if frame["kind"] == "model_output":
            assert frame["text"] == json.loads(event["raw"])["rationale"]
        if frame["kind"] == "observation_applied":
            assert frame["observation"] == event["observation"]
        elif frame["kind"] != "started":
            assert frame["observation"] is None
    asset = json.loads((ROOT / f"ui/public/runs/{name}.json").read_text())
    assert replay == asset["replay"]
    last = next(frame["observation"] for frame in reversed(replay["events"])
                if frame["observation"])
    assert last == asset["view"]["observation"]["value"]


def test_export_is_reproducible_and_evidence_remains_unchanged():
    MODULE.export(check=True)


def test_confirmation_explains_action_and_gates_preserve_recorded_status():
    trace = [json.loads(line) for line in
             (ROOT / 'evidence' / MODULE.RUNS['success'] / 'trace.jsonl').read_text().splitlines()]
    frames = MODULE.build_replay(trace)['events']
    pending = next(e for e in frames if e['kind'] == 'confirmation_pending')
    assert '6 до 8' in pending['summary']
    checks = next(e for e in frames if e['kind'] == 'preflight')['checks']
    assert any(c['id'] == 'G08_CONFIRMATION' and c['status'] == 'SKIPPED' for c in checks)
