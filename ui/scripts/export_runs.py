"""Generate portable BC-010 assets without mutating saved evidence."""

import argparse
import json
from pathlib import Path

from governed_agent_runtime.operator_outcome import build_view, render_text

ROOT = Path(__file__).resolve().parents[2]
RUNS = {
    "success": "bc-006-bounded-remediation/run-001",
    "stop": "bc-007-recovery-failure/run-001",
}


GATES = {
    "G01_SCHEMA_VALIDITY": "Структура предложения и соответствие схеме",
    "G02_TARGET_RESOLUTION": "Определение целевого сервиса и среды",
    "G03_PHASE_PERMISSION": "Допустимость действия на текущем этапе",
    "G04_ROLE_AUTHORIZATION": "Полномочия оператора",
    "G05_EVIDENCE_SUFFICIENCY": "Достаточность данных для решения",
    "G06_FRESHNESS_AND_CONSISTENCY": "Актуальность и согласованность состояния",
    "G07_TECHNICAL_PRECONDITIONS": "Технические условия выполнения",
    "G08_CONFIRMATION": "Явное подтверждение оператора",
    "G09_BUDGET_AND_REPETITION": "Бюджет действий и повторов",
    "G10_AUDIT_READINESS": "Готовность регистрации действий в журнале",
}


def action_description(tool, arguments, state):
    stable = state.get("stable_version_id", "—")
    candidate = state.get("candidate_version_id", "—")
    return {
        "scale_stable": f"увеличить количество реплик версии {stable} с {state.get('desired')} до {arguments.get('desired_replicas')}",
        "shift_traffic_to_stable": f"перенести весь трафик ({state.get('total_rps')} RPS) на версию {stable}",
        "read_operational_status": "получить актуальное состояние реплик, трафика и rollout",
        "read_post_shift_recovery": "проверить восстановление сервиса после переноса трафика",
        "finalize_rollback": f"удалить реплики версии {candidate} для завершения отката",
        "STOP": "остановить выполнение задачи",
    }.get(tool, f"выполнить действие {tool}")


def build_replay(trace):
    """Project selected recorded events; never turn a raw tool result into state."""
    events = []
    state = {}
    proposal = {}
    action = ""
    for event in trace:
        kind = event["kind"]
        frame = {"source": event["event_id"], "at": event["at"], "kind": kind,
                 "actor": "Runtime", "text": "", "observation": None}
        if kind == "started":
            frame.update(text="Начальное наблюдение сохранённого запуска",
                         observation=event["state"])
        elif kind == "model_output":
            proposal = json.loads(event["raw"])
            frame.update(actor="LLM", text=proposal["rationale"],
                         tool=proposal["tool_name"])
        elif kind in ("preflight", "revalidation"):
            frame["text"] = f"Проверка действия: {event['decision']}"
            if event.get("reason"):
                frame["text"] += f" · {event['reason']}"
        elif kind == "confirmation_pending":
            frame["text"] = "Запрошено явное подтверждение оператора (запись)"
        elif kind == "confirmation_consumed":
            frame.update(actor="Оператор", text="Подтверждение принято runtime (запись)")
        elif kind == "tool_call_started":
            frame["text"] = f"Начат вызов: {event['tool']}"
        elif kind == "observation_applied":
            frame.update(text="Принято новое наблюдение состояния сервиса",
                         observation=event["observation"])
        elif kind == "terminal":
            frame["text"] = f"Выполнение завершено: {event['outcome']} · {event['reason']}"
        elif kind == "terminal_verified":
            frame["text"] = "Runtime проверил завершение задачи"
        else:
            continue
        if kind == "started":
            state = event["state"]
        if kind == "model_output":
            action = action_description(proposal["tool_name"], proposal["arguments"], state)
            frame["summary"] = f"Предложение агента: {action}."
        elif kind in ("preflight", "revalidation"):
            decision = event["decision"]
            result = {"ALLOW": "действие разрешено", "REQUIRE_CONFIRMATION": "требуется явное подтверждение оператора",
                      "SAFE_FALLBACK": "выполнение переводится в безопасное завершение"}.get(decision, decision)
            phase = "Повторная проверка перед выполнением" if kind == "revalidation" else "Проверка предложения"
            frame["summary"] = f"{phase}: {action} — {result} ({decision})."
            frame["checks"] = [{"id": g["gate_id"], "label": GATES.get(g["gate_id"], g["gate_id"]),
                                "status": g["status"], "reason": g.get("reason_code"),
                                "reference": "specs/core/policy-spec.yaml"} for g in event["gates"]]
        elif kind in ("confirmation_pending", "confirmation_consumed"):
            assert event["record"]["tool_name"] == proposal["tool_name"]
            prefix = "Запрошено подтверждение" if kind == "confirmation_pending" else "Оператор подтвердил действие"
            frame["summary"] = f"{prefix}: {action}."
            frame["reference"] = "specs/core/confirmation-contract.yaml"
        elif kind == "tool_call_started":
            actual = action_description(event["tool"], event["arguments"], state)
            frame["summary"] = f"Начато действие: {actual} ({event['tool']})."
            frame["reference"] = "specs/core/tool-contracts.yaml"
        elif kind == "observation_applied":
            new = event["observation"]
            labels = {"desired": "Реплик основной версии", "healthy": "Ready основной версии",
                      "candidate_count": "Реплик новой версии", "stable_traffic_rps": "Трафик основной версии, RPS"}
            changes = [f"{label}: {state.get(key)} → {new[key]}" for key, label in labels.items()
                       if state.get(key) != new[key]]
            if state.get("recovery", {}).get("status") != new["recovery"]["status"]:
                changes.append(f"Проверка восстановления: {new['recovery']['status']}")
            frame["summary"] = "Принято наблюдение: " + ("; ".join(changes) if changes else "показатели состояния не изменились") + "."
            state = new
        frame.setdefault("summary", frame["text"])
        if kind == "model_output":
            frame["reference"] = "specs/core/tool-contracts.yaml"
        events.append(frame)
    frames = {frame["source"]: frame for frame in events}
    proposals = {}
    for event in trace:
        if event["kind"] == "model_output":
            tick = event["tick"]
            if tick in proposals:
                raise ValueError("Ambiguous model proposal tick")
            proposals[tick] = event["event_id"]
    for event in trace:
        if event["kind"] in ("preflight", "revalidation"):
            proposal_source = proposals[event["tick"]]
            frames[event["event_id"]]["proposal_source"] = proposal_source
            frames[proposal_source].setdefault("related_checks", []).append(event["event_id"])
    assert events and events[0]["kind"] == "started"
    return {"version": "2", "events": events}


def export(check=False):
    output = ROOT / "ui/public/runs"
    for name, relative in RUNS.items():
        run = ROOT / "evidence" / relative
        before = {p.name: p.read_bytes() for p in run.iterdir() if p.is_file()}
        view = build_view(run)
        trace = [json.loads(line) for line in before["trace.jsonl"].decode().splitlines()]
        payload = {"id": name, "view": view, "report": render_text(view),
                   "replay": build_replay(trace)}
        content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        path = output / f"{name}.json"
        if check:
            if not path.exists() or path.read_text() != content:
                raise ValueError(f"Generated asset differs: {path}")
        else:
            output.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        assert before == {p.name: p.read_bytes() for p in run.iterdir() if p.is_file()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    export(parser.parse_args().check)
