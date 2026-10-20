import hashlib
import json
from pathlib import Path

import pytest

from governed_agent_runtime.operator_outcome import build_view

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "evidence"


def test_success_and_no_source_mutation():
    p = E / "bc-006-bounded-remediation/run-001"
    before = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in p.iterdir()}
    v = build_view(p)
    assert v["rollback_completed"] is True
    assert v["observation"]["value"]["candidate_count"] == 0
    assert v["observation"]["value"]["recovery"]["status"] == "PASS"
    assert v["historical_only"] is True
    assert before == {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in p.iterdir()}


def test_stop_rationale_is_separate():
    v = build_view(E / "bc-007-recovery-failure/run-001")
    assert v["rollback_completed"] is False
    assert v["stop_reason"] == "MODEL_REQUESTED_STOP"
    assert v["observation"]["value"]["recovery"]["status"] == "FAIL"
    assert "Re-reading would repeat" in v["model_proposal"]["value"]["rationale"]


def test_interrupt_does_not_execute_pending_shift():
    v = build_view(E / "bc-008-operator-goal-framing/A-20")
    assert v["failure"]["value"]["type"] == "KeyboardInterrupt"
    assert v["pending_confirmation"]["tool"] == "shift_traffic_to_stable"
    assert [a["tool"] for a in v["actions"] if a["write"]] == ["scale_stable"]
    assert v["unknown_write_effect"] is False


def edited(tmp_path):
    p = E / "bc-008-operator-goal-framing/A-20"
    m = json.loads((p / "manifest.json").read_text())
    es = [json.loads(s) for s in (p / "trace.jsonl").read_text().splitlines()]
    return m, es


def save(tmp_path, m, es):
    (tmp_path / "manifest.json").write_text(json.dumps(m))
    (tmp_path / "trace.jsonl").write_text("\n".join(json.dumps(e) for e in es))
    return build_view(tmp_path)


def test_unapplied_pass_and_unknown_write(tmp_path):
    m, es = edited(tmp_path)
    es.insert(
        -3,
        {
            "kind": "tool_call_started",
            "event_id": "test-start",
            "tool": "shift_traffic_to_stable",
            "write": True,
        },
    )
    es.insert(
        -3,
        {
            "kind": "tool_result_raw",
            "event_id": "test-raw",
            "result": {"observation": {"recovery": {"status": "PASS"}}},
        },
    )
    v = save(tmp_path, m, es)
    assert v["observation"]["value"]["recovery"]["status"] == "UNKNOWN"
    assert v["unknown_write_effect"] is True
    assert v["rollback_completed"] is False


def test_fabricated_success_rejected(tmp_path):
    m, es = edited(tmp_path)
    m["outcome"].update(task_completed=True, task_state="COMPLETED")
    with pytest.raises(ValueError):
        save(tmp_path, m, es)


def test_missing_terminal_rejected(tmp_path):
    m, es = edited(tmp_path)
    es = [e for e in es if e["kind"] not in ("terminal", "transition")]
    with pytest.raises(ValueError):
        save(tmp_path, m, es)


def test_all_recorded_runs():
    for manifest in (E / "bc-008-operator-goal-framing").glob("*/manifest.json"):
        v = build_view(manifest.parent)
        assert v["rollback_completed"] == (manifest.parent.name != "A-20")


def test_model_success_cannot_override_runtime(tmp_path):
    m, es = edited(tmp_path)
    es.insert(
        -3,
        {
            "kind": "model_output",
            "event_id": "invented-success",
            "raw": json.dumps(
                {"tool_name": "STOP", "rationale": "Recovery PASS; rollback completed."}
            ),
        },
    )
    v = save(tmp_path, m, es)
    assert v["rollback_completed"] is False
    assert v["observation"]["value"]["recovery"]["status"] == "UNKNOWN"
    assert v["model_proposal"]["value"]["rationale"] == "Recovery PASS; rollback completed."


def test_render_interruption_and_stop():
    from governed_agent_runtime.operator_outcome import render_text

    interruption = render_text(build_view(E / "bc-008-operator-goal-framing/A-20"))
    assert "KeyboardInterrupt" in interruption
    assert "Ожидалось подтверждение shift_traffic_to_stable" in interruption
    assert "Состояние подтверждено на момент завершения запуска" in interruption
    stopped = render_text(build_view(E / "bc-007-recovery-failure/run-001"))
    assert "Recovery: FAIL" in stopped
    assert "Пояснение модели об остановке (STOP)" in stopped


def test_summary_first_and_budget_excerpt():
    from governed_agent_runtime.operator_outcome import render_text

    v = build_view(E / "bc-006-bounded-remediation/run-001")
    raw = v["model_proposal"]["value"]["rationale"]
    text = render_text(v)
    assert text.startswith("Статус\nОткат завершён.")
    assert "Восстановление после переноса трафика подтверждено" in text
    assert text.index("Стабильная версия") < text.index("Отчёт / Подробнее")
    assert "1 write remains" not in text
    assert "1 write remains" in raw
    assert "Пояснение модели перед действием" in text
    assert "Состояние подтверждено на момент завершения запуска" in text


def test_stop_summary_tracks_reached_state():
    from copy import deepcopy

    from governed_agent_runtime.operator_outcome import render_text

    view = build_view(E / "bc-007-recovery-failure/run-001")
    failed = render_text(view).split("Подтверждённое состояние")[0]
    assert "Все 820 RPS перенесены" in failed
    assert "FAIL" in failed
    recovered = deepcopy(view)
    recovered["observation"]["value"]["recovery"]["status"] = "PASS"
    summary = render_text(recovered).split("Подтверждённое состояние")[0]
    assert "Восстановление после переноса трафика подтверждено." in summary
    assert "откат не завершён" in summary
    assert "остаются: 2" in summary
    assert "FAIL" not in summary
    recovered["unknown_write_effect"] = True
    summary = render_text(recovered).split("Подтверждённое состояние")[0]
    assert "Исход одного из начатых изменений неизвестен" in summary
    assert "Восстановление после переноса трафика подтверждено." not in summary
    assert "Все 820 RPS перенесены" not in summary
