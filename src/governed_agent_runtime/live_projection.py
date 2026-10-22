"""Explicit public projections for BC-011; never export provider internals."""

from copy import deepcopy
from datetime import datetime

TOOLS = {
    "scale_stable": "Увеличить число реплик стабильной версии до 8",
    "read_operational_status": "Проверить состояние реплик и трафика",
    "shift_traffic_to_stable": "Перенести весь трафик на стабильную версию",
    "read_post_shift_recovery": "Проверить восстановление после переноса трафика",
    "finalize_rollback": "Удалить проблемную версию после подтверждения восстановления",
    "STOP": "Остановить дальнейшие действия",
}
FIELDS = ("observation_id", "observed_at", "stable_version_id", "candidate_version_id",
          "desired", "healthy", "candidate_count", "stable_traffic_rps", "total_rps",
          "safe_rps_per_replica", "conflicting_operation", "rollout_state", "shift_id")


def utc(value):
    return datetime.fromisoformat(value).isoformat().replace("+00:00", "Z")


def observation(value):
    result = {key: deepcopy(value[key]) for key in FIELDS}
    result["observed_at"] = utc(result["observed_at"])
    result["recovery"] = {key: value["recovery"][key] for key in ("status", "shift_id")}
    return result


def confirmation(request, created_at, expires_at):
    return {
        "confirmation_id": request["confirmation_id"], "created_at": created_at,
        "expires_at": expires_at, "action_summary": TOOLS[request["tool_name"]],
        "target_summary": "Моделируемый сервис payment-api",
        "parameters": [{"name": k, "value": v} for k, v in request["arguments"].items()],
        "rationale": request["rationale"],
        "evidence_summary": "Основание: " + request["observed"]["observation_id"],
        "expected_effect": TOOLS[request["tool_name"]],
        "affected_scope": "Только моделируемая среда текущего запуска",
        "estimated_duration": None,
        "key_risks": ["Подтверждение не заменяет повторную проверку runtime"],
        "stop_conditions": ["Изменение условий или неизвестный исход операции"],
        "verification_steps": ["Runtime проверяет результат и наблюдает состояние сервиса"],
    }


def outcome(rt):
    obs = rt.observation
    recovered = (obs["shift_id"] is not None and obs["recovery"]["status"] == "PASS"
                 and obs["recovery"]["shift_id"] == obs["shift_id"])
    unknown = rt.stop_reason == "UNKNOWN_WRITE_OUTCOME"
    reason = {
        "CONFIRMATION_REJECTED": "Оператор отклонил предложенное действие.",
        "CONFIRMATION_EXPIRED": "Срок подтверждения истёк.",
        "OPERATOR_REQUESTED_STOP": "Выполнение остановлено по запросу оператора.",
    }.get(rt.stop_reason, "Выполнение завершено.")
    if unknown:
        explanation = reason + " Исход изменения неизвестен. Оператору необходимо проверить состояние сервиса."
    elif rt.task_state == "COMPLETED":
        explanation = "Восстановление проверено runtime. Откат завершён."
    else:
        remaining = obs["total_rps"] - obs["stable_traffic_rps"]
        explanation = (reason + f" По последнему наблюдению: версия {obs['stable_version_id']} "
                       f"обслуживает {obs['stable_traffic_rps']} RPS; "
                       f"реплик версии {obs['candidate_version_id']} — {obs['candidate_count']}" +
                       (" без трафика. " if remaining == 0 else f", трафик — {remaining} RPS. "))
        explanation += ("Проверка восстановления пройдена; откат не завершён. "
                        "Дальнейшее решение по оставшимся репликам — за оператором." if recovered else
                        "Восстановление не подтверждено. Дальнейшее восстановление — за оператором.")
    return {
        "origin": "runtime", "reason_code": rt.stop_reason or "COMPLETED",
        "explanation": explanation,
        "runtime_outcome": {"task_state": rt.task_state, "stop_reason": rt.stop_reason,
                            "rollback_completed": rt.task_state == "COMPLETED",
                            "unknown_write_effect": unknown},
    }
