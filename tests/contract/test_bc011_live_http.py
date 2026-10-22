import json
import time
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from governed_agent_runtime.live_http import create_app
from governed_agent_runtime.live_service import LiveService, SimulatedModel

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "http://127.0.0.1:8000"
HEADERS = {"origin": ORIGIN, "x-gar-request": "live.v1"}


def post(client, path, command, **fields):
    return client.post(path, json={"command": command, "command_id": uuid4().hex, **fields},
                       headers=HEADERS)


def wait_for(read, predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = read()
        if predicate(value):
            return value
        time.sleep(.01)
    raise AssertionError(f"State did not converge: {value}")


@pytest.fixture
def live(tmp_path):
    service = LiveService(ROOT, tmp_path / "evidence")
    with TestClient(create_app(service), base_url=ORIGIN) as client:
        yield service, client


def start(client):
    assert post(client, "/api/session/bootstrap", "bootstrap").status_code == 200
    prepared = post(client, "/api/sessions", "prepare")
    assert prepared.status_code == 202, prepared.text
    started = post(client, "/api/runs", "start_run",
                   reservation_id=prepared.json()["reservation_id"], goal="Восстанови сервис")
    assert started.status_code == 202, started.text
    return started.json()["run_id"]


def pending(client, run_id):
    return wait_for(lambda: client.get(f"/api/runs/{run_id}").json(),
                    lambda x: x["phase"] in {"awaiting_confirmation", "terminal"})


def test_nominal_three_explicit_confirmations_and_refresh(live):
    service, client = live
    run_id = start(client)
    for _ in range(3):
        snap = pending(client, run_id)
        assert snap["phase"] == "awaiting_confirmation", snap
        assert client.get("/api/session").json()["current_run_id"] == run_id
        response = post(client, f"/api/runs/{run_id}/decisions", "decide",
                        confirmation_id=snap["pending_confirmation"]["confirmation_id"],
                        decision="approve")
        assert response.status_code == 202
        old_id = snap["pending_confirmation"]["confirmation_id"]
        wait_for(lambda: client.get(f"/api/runs/{run_id}").json(), lambda s, previous=old_id:
                 not s["pending_confirmation"] or
                 s["pending_confirmation"]["confirmation_id"] != previous)
    snap = wait_for(lambda: client.get(f"/api/runs/{run_id}").json(),
                    lambda s: s["phase"] == "terminal")
    assert snap["terminal"]["runtime_outcome"]["task_state"] == "COMPLETED", snap
    assert snap["service_view"]["candidate_count"] == 0
    assert client.get("/api/status").json()["availability"] == "available"
    with service.condition:
        assert len(service.runs[run_id]["rt"].adapter_calls) == 6
    events = client.get(f"/api/runs/{run_id}/events?after=0").json()["events"]
    assert [e["sequence"] for e in events] == list(range(1, len(events)+1))
    assert len([e for e in events if e["event_kind"] == "operator_decision"]) == 3


def test_reject_finishes_and_new_run_has_fresh_environment(live):
    _, client = live
    run_id = start(client)
    snap = pending(client, run_id)
    post(client, f"/api/runs/{run_id}/decisions", "decide",
         confirmation_id=snap["pending_confirmation"]["confirmation_id"], decision="reject")
    result = wait_for(lambda: client.get(f"/api/runs/{run_id}").json(),
                      lambda s: s["phase"] == "terminal")
    assert result["terminal"]["reason_code"] == "CONFIRMATION_REJECTED"
    next_id = start(client)
    assert next_id != run_id
    assert pending(client, next_id)["service_view"]["desired"] == 6


def test_foreign_session_is_busy_and_cannot_read_or_stop(live):
    service, first = live
    run_id = start(first)
    with TestClient(create_app(service), base_url=ORIGIN) as second:
        post(second, "/api/session/bootstrap", "bootstrap")
        assert post(second, "/api/sessions", "prepare").json()["code"] == "LIVE_BUSY"
        assert second.get(f"/api/runs/{run_id}").status_code == 404
        assert post(second, f"/api/runs/{run_id}/stop", "stop").status_code == 404


def test_timeout_without_reply_and_no_invented_rejection(tmp_path):
    service = LiveService(ROOT, tmp_path / "evidence", confirmation_seconds=.08)
    with TestClient(create_app(service), base_url=ORIGIN) as client:
        run_id = start(client)
        result = wait_for(lambda: client.get(f"/api/runs/{run_id}").json(),
                          lambda s: s["phase"] == "terminal")
        assert result["terminal"]["reason_code"] == "CONFIRMATION_EXPIRED"
        assert service.runs[run_id]["rt"].adapter_calls == []


def test_duplicate_decision_and_changed_payload(live):
    _, client = live
    run_id = start(client)
    snap = pending(client, run_id)
    body = {"command": "decide", "command_id": "same-command",
            "confirmation_id": snap["pending_confirmation"]["confirmation_id"], "decision": "reject"}
    path = f"/api/runs/{run_id}/decisions"
    first = client.post(path, json=body, headers=HEADERS)
    assert client.post(path, json=body, headers=HEADERS).json() == first.json()
    assert client.post(path, json=body | {"decision": "approve"}, headers=HEADERS).status_code == 409


def test_origin_content_cookie_and_body_boundaries(live):
    _, client = live
    body = {"command": "bootstrap", "command_id": "one"}
    assert client.post("/api/session/bootstrap", json=body).status_code == 403
    assert client.post("/api/session/bootstrap", json=body,
                       headers=HEADERS | {"origin": "https://foreign.invalid"}).status_code == 403
    valid = client.post("/api/session/bootstrap", json=body, headers=HEADERS)
    cookie = valid.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert "domain=" not in cookie
    assert post(client, "/api/sessions", "prepare", role="admin").status_code == 400
    assert client.post("/api/sessions", content=b"x" * 16385,
                       headers=HEADERS | {"content-type": "application/json"}).status_code == 413
    assert client.post("/api/sessions", content='{"command":"prepare","command":"prepare"}',
                       headers=HEADERS | {"content-type": "application/json"}).status_code == 400


class BlockedModel(SimulatedModel):
    def __init__(self):
        self.entered, self.release = Event(), Event()

    def infer(self, context):
        self.entered.set()
        self.release.wait(3)
        return super().infer(context)


def test_stop_during_inference_discards_late_proposal(tmp_path):
    model = BlockedModel()
    service = LiveService(ROOT, tmp_path / "evidence", provider=model)
    with TestClient(create_app(service), base_url=ORIGIN) as client:
        run_id = start(client)
        assert model.entered.wait(2)
        assert post(client, f"/api/runs/{run_id}/stop", "stop").status_code == 202
        assert client.get("/api/status").json()["availability"] == "busy"
        model.release.set()
        result = wait_for(lambda: client.get(f"/api/runs/{run_id}").json(),
                          lambda s: s["phase"] == "terminal")
        assert result["terminal"]["reason_code"] == "OPERATOR_REQUESTED_STOP"
        assert service.runs[run_id]["rt"].adapter_calls == []


def test_ready_reservation_expiry_releases_slot_without_run(tmp_path):
    service = LiveService(ROOT, tmp_path / "evidence", ready_seconds=.04)
    with TestClient(create_app(service), base_url=ORIGIN) as client:
        post(client, "/api/session/bootstrap", "bootstrap")
        post(client, "/api/sessions", "prepare")
        wait_for(lambda: client.get("/api/status").json(), lambda s: s["availability"] == "available")
        assert service.runs == {}


def test_late_done_releases_quarantine_without_executing_old_goal(tmp_path):
    model = BlockedModel()
    service = LiveService(ROOT, tmp_path / "evidence", provider=model,
                          inference_seconds=.03, reconciliation_seconds=1)
    with TestClient(create_app(service), base_url=ORIGIN) as client:
        run_id = start(client)
        assert model.entered.wait(2)
        result = wait_for(lambda: client.get(f"/api/runs/{run_id}").json(),
                          lambda s: s["phase"] == "terminal")
        assert result["terminal"]["reason_code"] == "PROVIDER_OR_RUNNER_FAILURE"
        assert client.get("/api/status").json()["availability"] == "unavailable"
        model.release.set()
        wait_for(lambda: client.get("/api/status").json(), lambda s: s["availability"] == "available")
        assert service.runs[run_id]["rt"].adapter_calls == []
        assert not service.marker.exists()


class LostResponseModel(SimulatedModel):
    def infer(self, context):
        raise ConnectionError("Private provider details must not escape")


def test_lost_response_marker_survives_restart_and_old_cookie_is_invalid(tmp_path):
    evidence = tmp_path / "evidence"
    first = LiveService(ROOT, evidence, provider=LostResponseModel())
    with TestClient(create_app(first), base_url=ORIGIN) as client:
        run_id = start(client)
        wait_for(lambda: client.get(f"/api/runs/{run_id}").json(), lambda s: s["phase"] == "terminal")
        old_cookie = client.cookies.get("gar_local_session")
        assert first.marker.exists()
        assert post(client, "/api/sessions", "prepare").status_code == 503
        assert "Private provider" not in client.get(f"/api/runs/{run_id}").text
    second = LiveService(ROOT, evidence)
    with TestClient(create_app(second), base_url=ORIGIN) as client:
        client.cookies.set("gar_local_session", old_cookie, domain="127.0.0.1", path="/api")
        assert client.get("/api/session").status_code == 401
        assert client.get("/api/status").json()["availability"] == "unavailable"
        post(client, "/api/session/bootstrap", "bootstrap")
        assert post(client, "/api/sessions", "prepare").status_code == 503
        assert post(client, "/api/reset", "reset").status_code in {404, 405}


def test_approve_then_stop_before_dispatch_never_executes(live):
    service, client = live
    run_id = start(client)
    snap = pending(client, run_id)
    with service.condition:
        session = service.authenticate(client.cookies.get("gar_local_session"))
        service.command(session, f"/api/runs/{run_id}/decisions", {
            "command": "decide", "command_id": "approve", "decision": "approve",
            "confirmation_id": snap["pending_confirmation"]["confirmation_id"]})
        service.command(session, f"/api/runs/{run_id}/stop", {"command": "stop", "command_id": "stop"})
    wait_for(lambda: client.get(f"/api/runs/{run_id}").json(), lambda s: s["phase"] == "terminal")
    assert service.runs[run_id]["rt"].adapter_calls == []


def test_duplicate_start_does_not_allocate_second_run(live):
    service, client = live
    post(client, "/api/session/bootstrap", "bootstrap")
    prepared = post(client, "/api/sessions", "prepare").json()
    body = {"command": "start_run", "command_id": "unique-start", "goal": "Восстанови сервис",
            "reservation_id": prepared["reservation_id"]}
    first = client.post("/api/runs", json=body, headers=HEADERS)
    assert client.post("/api/runs", json=body, headers=HEADERS).json() == first.json()
    assert len(service.runs) == 1


def test_wire_output_matches_schema_and_poll_is_read_only(live):
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    service, client = live
    registry = Registry()
    for name in ("bc011-live.schema.json", "bc006-proposal.schema.json"):
        registry = registry.with_resource("https://governed-agent-runtime.invalid/schemas/" + name,
            Resource.from_contents(json.loads((ROOT / "schemas" / name).read_text()),
                                   default_specification=DRAFT202012))
    schema = json.loads((ROOT / "schemas/bc011-live.schema.json").read_text())
    validator = Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())
    for _ in range(2):
        validator.validate(client.get("/api/status").json())
    assert service.sessions == {} and service.slot is None and not service.marker.exists()
    run_id = start(client)
    snap = pending(client, run_id)
    validator.validate(snap)
    validator.validate(client.get("/api/session").json())
    validator.validate(client.get(f"/api/runs/{run_id}/events?after=0").json())
    assert client.get(f"/api/runs/{run_id}/events?after=9999").json()["code"] == "CURSOR_INVALID"
    assert client.get(f"/api/runs/{run_id}/events?after=-1").status_code == 400


def test_second_coordinator_cannot_use_same_evidence_store(live):
    service, _ = live
    with pytest.raises(ValueError, match="active coordinator"):
        LiveService(ROOT, service.evidence)
