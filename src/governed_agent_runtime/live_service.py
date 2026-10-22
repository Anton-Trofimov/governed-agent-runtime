"""Local single-slot coordinator. Production provider activation is deliberately absent."""

import fcntl
import hashlib
import json
import os
import secrets
import threading
import time
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from governed_agent_runtime.bc006_runtime import (
    ConfirmationResult,
    RemediationRuntime,
    SyntheticEnvironment,
    canonical,
    utcnow,
)
from governed_agent_runtime.live_projection import TOOLS, confirmation, observation, outcome


def identifier():
    return uuid4().hex


def now():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class LiveError(Exception):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(code)


class SimulatedModel:
    """Deterministic nominal proposal path; not LLM evidence or arbitrary-text reasoning."""

    def prepare(self):
        return {"done": True}

    def infer(self, context):
        obs = context["observations"]
        args = dict(context["target"])
        if obs["desired"] < 8:
            tool = "scale_stable"
            args["desired_replicas"] = 8
        elif obs["healthy"] < 8:
            tool = "read_operational_status"
        elif obs["shift_id"] is None:
            tool = "shift_traffic_to_stable"
        elif obs["recovery"]["status"] != "PASS":
            tool = "read_post_shift_recovery"
            args["shift_id"] = obs["shift_id"]
        else:
            tool = "finalize_rollback"
            args["shift_id"] = obs["shift_id"]
        return {"done": True, "proposal": {"context_id": context["context_id"],
                "tool_name": tool, "arguments": args,
                "rationale": "Имитатор модели: " + TOOLS[tool] + "."}}


class LiveService:
    def __init__(self, root, evidence, *, provider=None, preparation_seconds=300,
                 inference_seconds=300, ready_seconds=300, confirmation_seconds=300,
                 reconciliation_seconds=30, monotonic=time.monotonic):
        self.root = Path(root)
        self.evidence = Path(evidence).resolve()
        if self.evidence.is_relative_to(self.root.resolve()):
            raise ValueError("Live evidence must be outside the repository")
        self.evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.evidence, 0o700)
        self.process_lock = (self.evidence / "coordinator.lock").open("a")
        try:
            fcntl.flock(self.process_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.process_lock.close()
            raise ValueError("Evidence directory already has an active coordinator") from None
        self.provider = provider or SimulatedModel()
        self.preparation_seconds, self.inference_seconds = preparation_seconds, inference_seconds
        self.ready_seconds, self.confirmation_seconds = ready_seconds, confirmation_seconds
        self.reconciliation_seconds = reconciliation_seconds
        self.monotonic = monotonic
        self.condition = threading.Condition(threading.RLock())
        self.sessions, self.runs = {}, {}
        self.slot = None
        self.marker = self.evidence / "outstanding-operation.json"
        self.quarantined = self.marker.exists()
        self.model_status = "unknown"
        self.closed = False
        self.threads = []
        self.maintenance = threading.Thread(target=self._maintain, daemon=True)
        self.maintenance.start()

    def _spawn(self, target, *args):
        thread = threading.Thread(target=target, args=args, daemon=True)
        self.threads = [existing for existing in self.threads if existing.is_alive()]
        self.threads.append(thread)
        thread.start()

    def _maintain(self):
        with self.condition:
            while not self.closed:
                self._expire()
                self.condition.wait(0.1)

    def _expire(self):
        tick = self.monotonic()
        if self.slot and self.slot["phase"] == "ready" and tick >= self.slot["deadline"]:
            self.slot["session"]["preparation_error"] = {
                "code": "READY_EXPIRED",
                "message": "Время ожидания запроса истекло. Начните сценарий заново."}
            self._release()
        for key, session in list(self.sessions.items()):
            owned = self.slot and self.slot["session_id"] == session["id"]
            if not owned and tick - session["touched"] >= 3600:
                for run_id in session["runs"]:
                    self.runs.pop(run_id, None)
                del self.sessions[key]

    def close(self):
        with self.condition:
            self.closed = True
            for run in self.runs.values():
                if run["phase"] != "terminal":
                    run["stop_requested"] = True
            if self.slot:
                self.slot["cancel"] = True
            self.condition.notify_all()
        self.maintenance.join(1)
        for thread in self.threads:
            thread.join(0.1)
        if not any(thread.is_alive() for thread in self.threads):
            self.process_lock.close()

    def bootstrap(self, token=None):
        with self.condition:
            self._expire()
            key = hashlib.sha256((token or "").encode()).hexdigest()
            if key in self.sessions:
                self.sessions[key]["touched"] = self.monotonic()
                return token, self.sessions[key]
            if len(self.sessions) >= 16:
                raise LiveError("SESSION_CAPACITY", 503)
            token = secrets.token_urlsafe(32)
            session = {"id": identifier(), "commands": {}, "runs": [], "current": None,
                       "touched": self.monotonic(), "preparation_error": None}
            self.sessions[hashlib.sha256(token.encode()).hexdigest()] = session
            return token, session

    def authenticate(self, token):
        self._expire()
        key = hashlib.sha256((token or "").encode()).hexdigest()
        session = self.sessions.get(key)
        if not session:
            raise LiveError("SESSION_REQUIRED", 401)
        session["touched"] = self.monotonic()
        return session

    def status(self):
        with self.condition:
            self._expire()
            availability = "unavailable" if self.quarantined or self.closed else (
                "busy" if self.slot else "available")
            return {"kind": "status", "version": "live.v1", "availability": availability,
                    "model_status": self.model_status, "server_time": now()}

    def session_view(self, session):
        slot = self.slot if self.slot and self.slot["session_id"] == session["id"] else None
        reservation = None
        if slot and not slot.get("run_id"):
            reservation = {"reservation_id": slot["id"], "phase": slot["phase"],
                           "expires_at": slot.get("expires_at"),
                           "service_view": deepcopy(slot["service_view"])}
        return {"kind": "session", "version": "live.v1", "session_id": session["id"],
                "session_state": "open", "expires_at": None if slot else (
                    datetime.now(UTC) + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
                "reservation": reservation, "current_run_id": session["current"],
                "model_status": self.model_status, "preparation_error": session["preparation_error"],
                "server_time": now()}

    def owned_run(self, session, run_id):
        if run_id not in session["runs"] or run_id not in self.runs:
            raise LiveError("NOT_FOUND", 404)
        return self.runs[run_id]

    def snapshot(self, run):
        result = {key: deepcopy(run[key]) for key in (
            "run_id", "phase", "runtime_state", "goal", "service_view", "pending_confirmation",
            "stop_requested", "terminal")}
        return {"kind": "snapshot", "version": "live.v1", **result,
                "model_status": run["model_status"], "cursor": len(run["events"]),
                "server_time": now()}

    def events(self, run, after, limit=100):
        if after > len(run["events"]):
            raise LiveError("CURSOR_INVALID")
        page = []
        size = 0
        for event in run["events"][after:after + limit]:
            size += len(canonical(event).encode())
            if size > 900_000:
                break
            page.append(deepcopy(event))
        return {"kind": "events", "version": "live.v1", "run_id": run["run_id"],
                "events": page, "next_cursor": after + len(page),
                "has_more": after + len(page) < len(run["events"])}

    def _event(self, run, kind, actor, payload):
        event = {"kind": "event", "version": "live.v1", "run_id": run["run_id"],
                 "sequence": len(run["events"]) + 1, "occurred_at": now(),
                 "event_kind": kind, "actor": actor, "payload": deepcopy(payload)}
        if len(canonical(event).encode()) > 65536 or len(run["events"]) >= 1000:
            raise ValueError("Live projection limit exceeded")
        run["events"].append(event)
        self.condition.notify_all()

    def _phase(self, run, phase):
        run["phase"] = phase
        self._event(run, "phase_changed", "platform", {"phase": phase, "reason": phase.upper()})

    def _release(self):
        if self.slot:
            session = self.slot["session"]
            session["touched"] = self.monotonic()
        self.slot = None
        self.condition.notify_all()

    def command(self, session, path, body):
        """Caller holds condition; runtime dispatch uses the same lock."""
        command_id, action = body["command_id"], body["command"]
        key = canonical({"path": path, "body": body})
        old = session["commands"].get(command_id)
        if old:
            if old[0] != key:
                raise LiveError("COMMAND_CONFLICT")
            return deepcopy(old[1])
        self._expire()
        # Reserve bounded emergency stop capacity; do not evict deduplication records.
        if len(session["commands"]) >= (512 if action == "stop" else 480):
            raise LiveError("SESSION_LIMIT")
        reservation_id = run_id = None
        if action == "prepare":
            if self.closed or self.quarantined:
                raise LiveError("LIVE_UNAVAILABLE", 503)
            if self.slot:
                raise LiveError("LIVE_BUSY")
            if len(session["runs"]) >= 8 or len(session["commands"]) > 430:
                raise LiveError("SESSION_LIMIT")
            fixture = json.loads((self.root / "fixtures/scenarios/bc-006/s12.json").read_text())
            environment = SyntheticEnvironment(fixture, utcnow)
            self.slot = {"environment": environment,
                         "service_view": observation(environment.snapshot()), "id": identifier(), "session_id": session["id"], "session": session,
                         "phase": "preparing", "run_id": None, "cancel": False}
            reservation_id = self.slot["id"]
            session["preparation_error"] = None
            session["current"] = None
            self.model_status = "preparing"
            self._spawn(self._prepare, self.slot)
        elif action == "start_run":
            slot = self.slot
            if not slot or slot["session_id"] != session["id"] or slot["id"] != body["reservation_id"]:
                raise LiveError("NOT_FOUND", 404)
            if slot["run_id"] or slot["cancel"]:
                raise LiveError("LIVE_BUSY")
            run_id, reservation_id = identifier(), slot["id"]
            run = {"run_id": run_id, "phase": "preparing", "runtime_state": None,
                   "goal": body["goal"], "service_view": deepcopy(slot["service_view"]), "pending_confirmation": None,
                   "stop_requested": False, "terminal": None, "events": [], "rt": None,
                   "model_status": self.model_status, "decision": None, "confirmation_deadline": None}
            self.runs[run_id] = run
            session["runs"].append(run_id)
            session["current"] = slot["run_id"] = run_id
            self._event(run, "goal_accepted", "operator", {"goal": body["goal"]})
            if slot["phase"] == "ready":
                slot["phase"] = "running"
                self._spawn(self._run, slot, run)
        elif action in {"decide", "stop"}:
            run_id = path.split("/")[3]
            run = self.owned_run(session, run_id)
            if action == "decide":
                pending = run["pending_confirmation"]
                records = run["rt"].confirmations if run["rt"] else []
                if not any(record["id"] == body["confirmation_id"] for record in records):
                    raise LiveError("NOT_FOUND", 404)
                if not pending or body["confirmation_id"] != pending["confirmation_id"]:
                    raise LiveError("ACTION_NOT_PENDING")
                if self.monotonic() >= run["confirmation_deadline"]:
                    raise LiveError("CONFIRMATION_EXPIRED")
                if run["decision"] is not None or run["stop_requested"]:
                    raise LiveError("ACTION_NOT_PENDING")
                run["decision"] = body["decision"]
                self._event(run, "operator_decision", "operator", {
                    "confirmation_id": body["confirmation_id"], "decision": body["decision"]})
            elif run["phase"] != "terminal" and not run["stop_requested"]:
                run["stop_requested"] = True
                self._event(run, "stop_requested", "operator", {})
                self._phase(run, "stopping")
            self.condition.notify_all()
        elif action == "release":
            if not self.slot or self.slot["session_id"] != session["id"] or (
                    body["reservation_id"] != self.slot["id"]):
                raise LiveError("NOT_FOUND", 404)
            if self.slot["run_id"]:
                raise LiveError("LIVE_BUSY")
            reservation_id = self.slot["id"]
            self.slot["cancel"] = True
            if self.slot["phase"] == "ready":
                self._release()
            else:
                self.slot["phase"] = "stopping"
        else:
            raise LiveError("INVALID_REQUEST", 400)
        ack = {"kind": "ack", "version": "live.v1", "command_id": command_id,
               "disposition": "accepted", "session_id": session["id"],
               "reservation_id": reservation_id, "run_id": run_id, "server_time": now()}
        session["commands"][command_id] = (key, deepcopy(ack))
        return ack

    def _provider_call(self, function, timeout):
        """Only one provider operation. Its thread never touches runtime or dispatches tools."""
        completed = threading.Event()
        result = {}
        # Atomic durable marker before dispatch, with no prompts or credentials.
        with self.marker.open("x") as file:
            os.chmod(self.marker, 0o600)
            file.write(canonical({"operation_id": identifier(), "status": "outstanding"}))
            file.flush()
            os.fsync(file.fileno())
        directory = os.open(self.evidence, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

        def invoke():
            try:
                result["value"] = function()
            except Exception:  # noqa: BLE001 - fail closed at provider boundary
                result["error"] = True
            finally:
                completed.set()

        self._spawn(invoke)
        if completed.wait(timeout):
            value = result.get("value")
            if isinstance(value, dict) and value.get("done") is True:
                self.marker.unlink()
                return value
        with self.condition:
            self.quarantined = True
            self.model_status = "unavailable"

        def reconcile():
            if completed.wait(self.reconciliation_seconds):
                value = result.get("value")
                if isinstance(value, dict) and value.get("done") is True:
                    with self.condition:
                        # Completion does not authorize replaying a cancelled goal.
                        self.marker.unlink(missing_ok=True)
                        self.quarantined = False
                        self.model_status = "ready"
                        self.condition.notify_all()

        self._spawn(reconcile)
        raise TimeoutError("Provider completion not established")

    def _prepare(self, slot):
        try:
            self._provider_call(self.provider.prepare, self.preparation_seconds)
            with self.condition:
                if self.slot is not slot:
                    return
                self.model_status = "ready"
                run = self.runs.get(slot["run_id"])
                if slot["cancel"] or self.closed or (run and run["stop_requested"]):
                    if run:
                        self._platform_terminal(run, "STOPPED_BEFORE_RUNTIME")
                    self._release()
                elif run:
                    slot["phase"] = "running"
                    self._spawn(self._run, slot, run)
                else:
                    slot["phase"] = "ready"
                    slot["deadline"] = self.monotonic() + self.ready_seconds
                    slot["expires_at"] = (datetime.now(UTC) + timedelta(
                        seconds=self.ready_seconds)).isoformat().replace("+00:00", "Z")
        except Exception as error:  # noqa: BLE001 - fail closed at provider boundary
            with self.condition:
                self.quarantined = self.marker.exists()
                self.model_status = "unavailable"
                reason = "PREPARATION_TIMEOUT" if isinstance(error, TimeoutError) else (
                    "PREPARATION_FAILED")
                slot["session"]["preparation_error"] = {
                    "code": reason, "message": "Не удалось подготовить имитатор"}
                run = self.runs.get(slot["run_id"])
                if run:
                    self._platform_terminal(run, reason)
                if self.slot is slot:
                    self._release()

    def _platform_terminal(self, run, reason):
        run["terminal"] = {"origin": "platform", "reason_code": reason,
                           "explanation": "Запрос не выполнен. Подготовка завершена без запуска.",
                           "runtime_outcome": None}
        run["model_status"] = self.model_status
        self._phase(run, "terminal")
        self._event(run, "run_finished", "platform", run["terminal"])

    def _trace(self, run, event):
        kind = event["kind"]
        if kind == "transition":
            run["runtime_state"] = event["current"]
        elif kind in {"started", "observation_applied"}:
            run["service_view"] = observation(event.get("observation", event.get("state")))
            self._event(run, "observation_accepted", "runtime", run["service_view"])
        elif kind in {"preflight", "revalidation"}:
            labels = {
                "G01_SCHEMA_VALIDITY": "Структура предложения",
                "G02_TARGET_RESOLUTION": "Цель действия",
                "G03_PHASE_PERMISSION": "Допустимость шага",
                "G04_ROLE_AUTHORIZATION": "Полномочия оператора",
                "G05_EVIDENCE_SUFFICIENCY": "Достаточность наблюдений",
                "G06_FRESHNESS_AND_CONSISTENCY": "Актуальность наблюдений",
                "G07_TECHNICAL_PRECONDITIONS": "Условия выполнения",
                "G08_CONFIRMATION": "Явное подтверждение",
                "G09_BUDGET_AND_REPETITION": "Бюджет выполнения",
                "G10_AUDIT_READINESS": "Готовность журнала",
            }
            self._event(run, "admission_checked", "runtime", {
                "stage": kind, "result": event["decision"],
                "explanation": event.get("details") or "Проверены условия допуска действия",
                "checks": [{"id": g["gate_id"], "label": labels.get(g["gate_id"], g["gate_id"]),
                            "status": g["status"],
                            "reason": g.get("reason_code"), "reference": {
                                "artifact": "specs/core/policy-spec.yaml", "anchor": g["gate_id"]}}
                           for g in event["gates"]]})
        elif kind == "tool_call_started":
            name = event["tool"]
            self._event(run, "tool_started", "runtime", {"tool_name": name, "summary": TOOLS[name]})
        elif kind in {"confirmation_status", "confirmation_consumed"}:
            record = event["record"]
            self._event(run, "confirmation_resolved", "runtime", {
                "confirmation_id": record["id"], "status": record["status"],
                "reason": record["status"]})

    def _confirm(self, run, request):
        run["decision"] = None
        run["confirmation_deadline"] = self.monotonic() + self.confirmation_seconds
        run["pending_confirmation"] = confirmation(request, now(), (
            datetime.now(UTC) + timedelta(seconds=self.confirmation_seconds)
        ).isoformat().replace("+00:00", "Z"))
        self._phase(run, "awaiting_confirmation")
        self._event(run, "confirmation_requested", "runtime", run["pending_confirmation"])
        while True:
            remaining = run["confirmation_deadline"] - self.monotonic()
            if run["stop_requested"] or self.closed:
                result = ConfirmationResult.STOPPED
                break
            if remaining <= 0:
                result = ConfirmationResult.EXPIRED
                break
            if run["decision"]:
                result = ConfirmationResult.APPROVED if run["decision"] == "approve" else (
                    ConfirmationResult.REJECTED)
                break
            self.condition.wait(min(remaining, 0.1))
        run["pending_confirmation"] = None
        self._phase(run, "running")
        return result

    def _run(self, slot, run):
        try:
            with self.condition:
                rt = RemediationRuntime(self.root, operator_goal=run["goal"],
                                        initial_environment=slot["environment"],
                                        session_id=slot["session_id"],
                                        evidence_dir=self.evidence / run["run_id"],
                                        event_sink=lambda event: self._trace(run, event))
                run["rt"] = rt
                run["runtime_state"] = rt.task_state
                self._phase(run, "running")
            while True:
                with self.condition:
                    if run["stop_requested"] or self.closed:
                        rt.stop("OPERATOR_REQUESTED_STOP")
                    if rt.terminal:
                        break
                    context = rt.issue_context()
                    if context is None:
                        break
                    self.model_status = run["model_status"] = "inference"
                    self._event(run, "model_status_changed", "platform", {"model_status": "inference"})
                response = self._provider_call(lambda ctx=context: self.provider.infer(ctx),
                                               self.inference_seconds)
                with self.condition:
                    self.model_status = run["model_status"] = "ready"
                    if run["stop_requested"] or self.closed:
                        rt.stop("OPERATOR_REQUESTED_STOP")
                        break
                    proposal = response["proposal"]
                    from jsonschema import Draft202012Validator
                    if Draft202012Validator(rt.schemas["proposal_schema"]).is_valid(proposal):
                        self._event(run, "proposal_recorded", "agent", {"proposal": proposal})
                    rt.submit(canonical(proposal), confirm=lambda req: self._confirm(run, req))
        except Exception:  # noqa: BLE001 - fail closed at provider boundary
            with self.condition:
                if run["rt"]:
                    run["rt"].stop("PROVIDER_OR_RUNNER_FAILURE", failed=True)
                else:
                    self._platform_terminal(run, "PREPARATION_FAILED")
        finally:
            with self.condition:
                rt = run["rt"]
                if rt:
                    run["model_status"] = self.model_status
                    run["runtime_state"] = rt.task_state
                    run["pending_confirmation"] = None
                    run["terminal"] = outcome(rt)
                    self._phase(run, "terminal")
                    self._event(run, "run_finished", "platform", run["terminal"])
                    (self.evidence / run["run_id"] / "outcome.json").write_text(
                        json.dumps(run["terminal"], ensure_ascii=False))
                    (self.evidence / run["run_id"] / "manifest.json").write_text(canonical({
                        "provider_kind": "deterministic_simulator", "real_inference": False,
                        "run_id": run["run_id"], "summary": rt.summary()}))
                if self.slot is slot:
                    self._release()
