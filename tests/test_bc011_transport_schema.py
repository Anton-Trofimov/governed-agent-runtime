"""Offline wire-shape checks; these do not prove HTTP/session enforcement."""

import copy
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


@lru_cache
def validator():
    path = Path(__file__).resolve().parents[1] / "schemas/bc011-live.schema.json"
    schema = json.loads(path.read_text())
    Draft202012Validator.check_schema(schema)
    registry = Registry()
    for item in path.parent.glob("*.schema.json"):
        resource = Resource.from_contents(json.loads(item.read_text()),
                                          default_specification=DRAFT202012)
        registry = registry.with_resource(
            "https://governed-agent-runtime.invalid/schemas/" + item.name, resource)
    checker = FormatChecker()

    @checker.checks("date-time", raises=ValueError)
    def utc_time(value):
        if not isinstance(value, str):
            return True
        return value.endswith("Z") and datetime.fromisoformat(value).tzinfo is not None

    return Draft202012Validator(schema, format_checker=checker, registry=registry)


def test_commands_bind_identity_without_client_authority():
    v = validator()
    start = {"command": "start_run", "command_id": "cmd-1",
             "reservation_id": "reservation-1", "goal": "Восстанови сервис"}
    v.validate(start)
    for field in ("role", "user_id", "provider_url", "tool_name", "session_secret"):
        assert not v.is_valid({**start, field: "client-selected"})
    for goal in ("", " \n\t", "x" * 2001):
        assert not v.is_valid({**start, "goal": goal})
    v.validate({**start, "goal": "я" * 2000})


def test_confirmation_is_one_action_and_explicit_enum():
    v = validator()
    command = {"command": "decide", "command_id": "cmd-2",
               "confirmation_id": "confirm-1", "decision": "approve"}
    v.validate(command)
    for decision in (True, "CONFIRM", "подтверждаю", "", "stop"):
        assert not v.is_valid({**command, "decision": decision})
    for field in ("confirmation_id", "command_id"):
        invalid = dict(command)
        del invalid[field]
        assert not v.is_valid(invalid)
    assert not v.is_valid({**command, "parameters": {"desired_replicas": 8}})


def event(kind, actor, payload):
    return {"kind": "event", "version": "live.v1", "run_id": "run-1",
            "sequence": 1, "occurred_at": "2026-10-21T12:00:00Z",
            "event_kind": kind, "actor": actor, "payload": payload}


def test_events_cannot_misattribute_consent_or_accept_untyped_payload():
    v = validator()
    value = event("operator_decision", "operator",
                  {"confirmation_id": "confirm-1", "decision": "approve"})
    v.validate(value)
    assert not v.is_valid({**value, "actor": "agent"})
    assert not v.is_valid({**value, "sequence": 0})
    assert not v.is_valid({**value, "occurred_at": "yesterday"})
    assert not v.is_valid({**value, "occurred_at": "2026-02-30T12:00:00Z"})
    assert not v.is_valid({**value, "version": "replay.v2"})
    invalid = copy.deepcopy(value)
    invalid["payload"]["secret"] = "not-allowed"
    assert not v.is_valid(invalid)


def test_preparation_failure_has_no_fabricated_runtime_outcome():
    v = validator()
    terminal = {"origin": "platform", "reason_code": "PREPARATION_FAILED",
                "explanation": "Подготовка не завершена", "runtime_outcome": None}
    value = event("run_finished", "platform", terminal)
    v.validate(value)
    invalid = copy.deepcopy(value)
    invalid["payload"]["runtime_outcome"] = {
        "task_state": "COMPLETED", "stop_reason": None,
        "rollback_completed": True, "unknown_write_effect": False}
    assert not v.is_valid(invalid)


@pytest.mark.parametrize("status", ["available", "busy", "unavailable"])
def test_public_status_contains_no_owner_data(status):
    v = validator()
    value = {"kind": "status", "version": "live.v1", "availability": status,
             "model_status": "unknown", "server_time": "2026-10-21T12:00:00Z"}
    v.validate(value)
    for field in ("run_id", "session_id", "goal", "confirmation_id"):
        assert not v.is_valid({**value, field: "private"})


def test_page_bound_and_no_unknown_event_type():
    v = validator()
    value = {"kind": "events", "version": "live.v1", "run_id": "run-1",
             "events": [], "next_cursor": 0, "has_more": False}
    v.validate(value)
    assert not v.is_valid({**value, "next_cursor": -1})
    item = event("goal_accepted", "operator", {"goal": "Восстанови сервис"})
    assert not v.is_valid({**value, "events": [item] * 101})
    assert not v.is_valid({**item, "event_kind": "execute_arbitrary_tool"})


def test_live_proposal_reuses_existing_tool_argument_contract():
    v = validator()
    proposal = {"context_id": "ctx-1", "tool_name": "scale_stable",
                "arguments": {"service_id": "payment-api", "environment_id": "synthetic",
                              "deployment_target_id": "stable", "desired_replicas": 8},
                "rationale": "Capacity requires eight replicas."}
    value = event("proposal_recorded", "agent", {"proposal": proposal})
    v.validate(value)
    proposal["arguments"]["desired_replicas"] = 9
    assert not v.is_valid(value)


def test_gate_statuses_preserve_runtime_vocabulary():
    v = validator()
    value = event("admission_checked", "runtime", {
        "stage": "preflight", "result": "REPLACE_WITH_SAFER_PATH",
        "explanation": "Capacity is insufficient", "checks": [
            {"id": "G08_CONFIRMATION", "label": "Confirmation", "status": "SKIPPED",
             "reason": None, "reference": None}]})
    for status in ("PASSED", "FAILED", "SKIPPED", "NOT_APPLICABLE"):
        value["payload"]["checks"][0]["status"] = status
        v.validate(value)
    value["payload"]["result"] = "REJECT"
    assert not v.is_valid(value)


def test_snapshot_requires_pending_action_and_terminal_result():
    v = validator()
    value = {"kind": "snapshot", "version": "live.v1", "run_id": "run-1",
             "phase": "preparing", "runtime_state": None, "goal": "Восстанови сервис",
             "model_status": "preparing", "service_view": None,
             "pending_confirmation": None, "stop_requested": False, "terminal": None,
             "cursor": 1, "server_time": "2026-10-21T12:00:00Z"}
    v.validate(value)
    assert not v.is_valid({**value, "phase": "awaiting_confirmation"})
    assert not v.is_valid({**value, "phase": "terminal"})
    terminal = {"origin": "runtime", "reason_code": "COMPLETED", "explanation": "Verified",
                "runtime_outcome": {"task_state": "COMPLETED", "stop_reason": None,
                                    "rollback_completed": True, "unknown_write_effect": False}}
    v.validate({**value, "phase": "terminal", "runtime_state": "COMPLETED",
                "terminal": terminal})
    terminal["runtime_outcome"]["unknown_write_effect"] = True
    assert not v.is_valid({**value, "phase": "terminal", "terminal": terminal})
