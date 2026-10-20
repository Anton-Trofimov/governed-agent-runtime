"""Read-only, deterministic presentation of recorded bounded-remediation outcomes."""

import argparse
import hashlib
import json
from pathlib import Path


def build_view(run_directory):
    """Project historical evidence; never authorize execution or query a model."""
    directory = Path(run_directory)
    sources = {name: (directory / name).read_bytes() for name in ("manifest.json", "trace.jsonl")}
    manifest = json.loads(sources["manifest.json"])
    events = [json.loads(line) for line in sources["trace.jsonl"].splitlines() if line.strip()]
    ids = [e["event_id"] for e in events]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate trace event IDs")
    outcome = manifest["outcome"]
    transitions = [e for e in events if e["kind"] == "transition"]
    state = outcome["task_state"]
    if not transitions or transitions[-1]["current"] != state:
        raise ValueError("Manifest and terminal transition disagree or are missing")
    if state not in ("COMPLETED", "SAFE_FALLBACK", "FAILED"):
        raise ValueError("Run has no supported terminal outcome")
    completed = outcome["task_completed"]
    if not isinstance(completed, bool) or completed != (state == "COMPLETED"):
        raise ValueError("Contradictory completion flags")
    terminals = [e for e in events if e["kind"] == "terminal"]
    if not completed and (
        not terminals
        or terminals[-1]["outcome"] != state
        or terminals[-1]["reason"] != outcome["stop_reason"]
    ):
        raise ValueError("Terminal reason missing or contradictory")

    def ref(e):
        return f"trace.jsonl#{e['event_id']}"

    observation = proposal = failure = None
    pending = None
    actions = []
    active = raw = None
    for e in events:
        kind = e["kind"]
        if kind == "model_output":
            proposal = None
            try:
                candidate = json.loads(e["raw"])
                if isinstance(candidate, dict) and isinstance(candidate.get("rationale"), str):
                    proposal = {"value": candidate, "source": ref(e)}
            except (ValueError, TypeError):
                pass
        elif kind == "confirmation_pending":
            pending = {"tool": e["record"]["tool_name"], "source": ref(e)}
        elif kind in ("confirmation_consumed", "confirmation_status"):
            if e.get("record", {}).get("status") != "PENDING":
                pending = None
        elif kind == "tool_call_started":
            active = {"tool": e["tool"], "write": e["write"], "effect": "UNKNOWN", "source": ref(e)}
            actions.append(active)
            raw = None
        elif kind == "tool_result_raw":
            raw = e.get("result", {})
        elif kind == "observation_applied":
            observation = {"value": e["observation"], "source": ref(e)}
            if (
                active is not None
                and raw
                and raw.get("tool_name") == active["tool"]
                and raw.get("observation") == e["observation"]
            ):
                active["effect"] = "OBSERVED"
                active["result_source"] = ref(e)
                active = raw = None
        elif kind == "runner_failure":
            failure = {
                "value": {"type": e["type"], "message": e.get("message", "")},
                "source": ref(e),
            }
    unknown_write = any(a["write"] and a["effect"] == "UNKNOWN" for a in actions)
    if completed:
        obs = observation["value"] if observation else {}
        if (
            unknown_write
            or obs.get("candidate_count") != 0
            or obs.get("rollout_state") != "ROLLED_BACK"
            or not actions
            or actions[-1]["tool"] != "read_operational_status"
            or actions[-1]["effect"] != "OBSERVED"
            or not any(
                a["tool"] == "finalize_rollback" and a["effect"] == "OBSERVED" for a in actions
            )
        ):
            raise ValueError("Completed run lacks verified final rollback evidence")
    return {
        "view_version": "1",
        "historical_only": True,
        "sources": {n: hashlib.sha256(b).hexdigest() for n, b in sources.items()},
        "scope": manifest.get("scope"),
        "run_id": manifest.get("case", {}).get("run_id"),
        "task_state": state,
        "stop_reason": outcome["stop_reason"],
        "outcome_source": "manifest.json#/outcome",
        "terminal_source": ref(transitions[-1]),
        "rollback_completed": completed,
        "observation": observation,
        "actions": actions,
        "unknown_write_effect": unknown_write,
        "pending_confirmation": pending,
        "model_proposal": proposal,
        "failure": failure,
    }


def render_text(view):
    """Outcome first, historical facts second, technical/model details last."""
    state = view["task_state"]
    obs = view["observation"]
    o = obs["value"] if obs else None
    unknown = view["unknown_write_effect"]
    pending = view["pending_confirmation"]
    interrupted = view["failure"] and view["failure"]["value"]["type"] == "KeyboardInterrupt"
    if state == "COMPLETED":
        lines = ["Откат завершён."]
    elif state == "SAFE_FALLBACK":
        lines = ["Выполнение остановлено; откат не завершён."]
        if view["stop_reason"] == "MODEL_REQUESTED_STOP":
            lines.append("Модель предложила остановиться; runtime завершил выполнение.")
    elif interrupted:
        lines = ["Выполнение прервано; откат не завершён."]
        if pending and not unknown:
            lines.append("Прерывание произошло во время ожидания подтверждения действия.")
    else:
        lines = ["Выполнение завершилось ошибкой; откат не завершён."]
    if unknown:
        lines.append(
            "Исход одного из начатых изменений неизвестен. Перед продолжением требуется проверить его результат."
        )
    elif o:
        recovery = o["recovery"]
        if recovery["status"] == "PASS" and recovery["shift_id"] == o["shift_id"] and o["shift_id"]:
            lines.append("Восстановление после переноса трафика подтверждено.")
        elif recovery["status"] == "FAIL":
            lines.append(
                "Проверка восстановления завершилась с FAIL. Подтверждения восстановления нет."
            )
            if o["candidate_count"]:
                lines.append(
                    f"Удаление реплик версии {o['candidate_version_id']} не выполнено: необходимое условие recovery PASS не выполнено."
                )
        else:
            lines.append("Восстановление после переноса трафика не подтверждено.")
        if pending and pending["tool"] == "shift_traffic_to_stable" and o["shift_id"] is None:
            lines.append("Перенос трафика не выполнен.")
    if o and not unknown:
        if state == "COMPLETED":
            lines.append(f"Реплики нестабильной версии {o['candidate_version_id']} удалены.")
        else:
            if o["stable_traffic_rps"] == o["total_rps"]:
                lines.append(f"Все {o['total_rps']} RPS перенесены на стабильную версию.")
            elif any(a["tool"] == "scale_stable" and a["effect"] == "OBSERVED" for a in view["actions"]):
                lines.append(f"Масштабирование до {o['healthy']} работоспособных реплик стабильной версии подтверждено.")
            lines.append(f"Реплики версии {o['candidate_version_id']} остаются: {o['candidate_count']}.")
    lines.insert(0, "Статус")
    if state != "COMPLETED":
        lines.append(
            "Требуется проверить причину остановки и определить дальнейшие действия. Автоматический повтор не назначен."
        )
    lines.extend(["", "Подтверждённое состояние"])
    if o:
        if unknown:
            lines.append(
                f"Последние подтверждённые данные до изменения с неизвестным исходом: {o['observed_at']}."
            )
        else:
            lines.append(
                f"Состояние подтверждено на момент завершения запуска; время последней проверки: {o['observed_at']}."
            )
        lines.extend(
            [
                f"Стабильная версия {o['stable_version_id']}: {o['healthy']} работоспособных реплик; задано {o['desired']}.",
                f"Трафик на стабильной версии: {o['stable_traffic_rps']} из {o['total_rps']} RPS.",
                f"Реплик версии {o['candidate_version_id']}: {o['candidate_count']}.",
                f"Проверка восстановления после переноса трафика: {o['recovery']['status']} (данные последней проверки).",
                "Конфликты: "
                + (
                    "обнаружены."
                    if o["conflicting_operation"]
                    else "не обнаружены на момент проверки."
                ),
            ]
        )
    else:
        lines.append("Подтверждённые данные отсутствуют; состояние неизвестно.")
    lines.append(f"Статус исполнения: {state}; откат " + ("завершён." if view["rollback_completed"] else "не завершён."))
    lines.extend(
        [
            "",
            "Отчёт / Подробнее",
            f"Результат runtime: {state}; причина: {view['stop_reason'] or 'завершение подтверждено'}.",
            f"Основание: {view['outcome_source']}; {view['terminal_source']}.",
            "Отчёт построен по сохранённому запуску; новой проверки сервиса при открытии отчёта нет.",
        ]
    )
    if view["failure"]:
        f = view["failure"]
        lines.append(f"Ошибка runner: {f['value']['type']} [{f['source']}].")
    if o:
        lines.extend(
            [
                f"Наблюдение {o['observation_id']} [{obs['source']}].",
                f"Recovery: {o['recovery']['status']}; операция переноса трафика: {o['shift_id']}; проверка recovery относится к операции: {o['recovery']['shift_id']}.",
            ]
        )
    for a in view["actions"]:
        if not a["write"]:
            continue
        source = a.get("result_source", a["source"])
        if a["effect"] == "UNKNOWN":
            text = f"{a['tool']}: действие начато, результат неизвестен"
        elif o and not unknown and a["tool"] == "scale_stable":
            text = f"Масштабирование подтверждено: {o['healthy']} работоспособных реплик стабильной версии по последней проверке [{obs['source']}]"
        elif o and not unknown and a["tool"] == "shift_traffic_to_stable":
            text = f"Перенос трафика подтверждён: {o['stable_traffic_rps']} RPS на стабильной версии [{obs['source']}]"
        elif o and not unknown and a["tool"] == "finalize_rollback":
            text = f"Удаление реплик версии {o['candidate_version_id']}: по последней проверке осталось {o['candidate_count']} реплик [{obs['source']}]"
        else:
            text = f"{a['tool']}: результат принят runtime"
        lines.append(f"{text} [{source}].")
    if pending:
        lines.append(
            f"Ожидалось подтверждение {pending['tool']} [{pending['source']}]; это не подтверждение исполнения."
        )
    if view["model_proposal"]:
        import re

        p = view["model_proposal"]
        raw = p["value"]["rationale"]
        # Only omit whole budget-bearing sentences/clauses; never correct model content.
        pieces = re.split(r"(?<=[.;])\s+", raw)
        selected = [
            s
            for s in pieces
            if not (
                re.search(r"\bwrite[s]?\b", s, re.IGNORECASE)
                and re.search(r"\b(budget|remain\w*)\b", s, re.IGNORECASE)
            )
        ]
        excerpt = " ".join(selected)
        label = (
            "Пояснение модели об остановке"
            if p["value"].get("tool_name") == "STOP"
            else "Пояснение модели перед действием"
        )
        lines.extend(
            [
                "",
                f"{label} ({p['value'].get('tool_name', 'unknown')}) [{p['source']}].",
                "Это объяснение предложения, а не отчёт о последующем результате выполнения.",
            ]
        )
        if excerpt != raw:
            lines.append(
                "Выдержка: служебная фраза о бюджете операций опущена; полный оригинал сохранён в evidence."
            )
        lines.append("> " + excerpt.replace("\n", "\n> "))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        view = build_view(args.run_directory)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Представление недоступно: evidence неполно или противоречиво ({error}).\n")
    print(
        json.dumps(view, ensure_ascii=False, indent=2) if args.as_json else render_text(view),
        end="\n" if args.as_json else "",
    )


if __name__ == "__main__":
    main()
