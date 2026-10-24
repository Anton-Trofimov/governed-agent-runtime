"""Loopback-only live HTTP server. Only the deterministic provider is executable."""

import argparse
import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from governed_agent_runtime.live_service import LiveError, now

COOKIE = "gar_local_session"


def create_app(service, origin="http://127.0.0.1:8000"):
    parsed = urlsplit(origin)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Only a loopback HTTP origin is supported")
    schema = json.loads((service.root / "schemas/bc011-live.schema.json").read_text())

    def validate(name, value):
        validator = Draft202012Validator({"$defs": schema["$defs"],
                                         "$ref": f"#/$defs/{name}"})
        if not validator.is_valid(value):
            raise LiveError("INVALID_REQUEST", 400)

    def response(value, status=200):
        data = JSONResponse(value, status_code=status, headers={
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "X-GAR-Provider": service.provider_info["kind"]})
        if len(data.body) > 1024 * 1024:
            raise LiveError("LIVE_UNAVAILABLE", 503)
        return data

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate key")
            result[key] = value
        return result

    async def endpoint(request: Request):
        body = {}
        try:
            if request.headers.get("host") != parsed.netloc or request.headers.get(
                    "sec-fetch-site") in {"cross-site", "same-site"}:
                raise LiveError("ORIGIN_REJECTED", 403)
            # GETs do not require Origin, but an explicit foreign Origin is rejected.
            sent_origin = request.headers.get("origin")
            if sent_origin is not None and sent_origin != origin:
                raise LiveError("ORIGIN_REJECTED", 403)
            if request.method == "POST":
                if sent_origin != origin or request.headers.get("x-gar-request") != "live.v1":
                    raise LiveError("ORIGIN_REJECTED", 403)
                if request.headers.get("content-type", "").split(";")[0] != "application/json":
                    raise LiveError("INVALID_REQUEST", 400)
                raw = bytearray()
                async for chunk in request.stream():
                    raw.extend(chunk)
                    if len(raw) > 16384:
                        raise LiveError("REQUEST_TOO_LARGE", 413)
                try:
                    body = json.loads(raw, object_pairs_hook=pairs,
                                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                except (ValueError, UnicodeError):
                    raise LiveError("INVALID_REQUEST", 400) from None
                if not isinstance(body, dict):
                    raise LiveError("INVALID_REQUEST", 400)
            path = request.url.path
            token = request.cookies.get(COOKIE)
            with service.condition:
                if path == "/api/status" and request.method == "GET":
                    return response(service.status())
                if path == "/api/session/bootstrap" and request.method == "POST":
                    validate("bootstrap", body)
                    token, session = service.bootstrap(token)
                    result = response({"kind": "ack", "version": "live.v1",
                        "command_id": body["command_id"], "disposition": "completed",
                        "session_id": session["id"], "reservation_id": None, "run_id": None,
                        "server_time": now()})
                    result.set_cookie(COOKIE, token, httponly=True, samesite="strict", path="/api")
                    return result
                session = service.authenticate(token)
                if path == "/api/session" and request.method == "GET":
                    return response(service.session_view(session))
                run_id = request.path_params.get("run_id")
                if request.method == "GET" and run_id:
                    run = service.owned_run(session, run_id)
                    if path.endswith("/events"):
                        if len(set(request.query_params.keys())) != len(request.query_params.multi_items()):
                            raise LiveError("INVALID_REQUEST", 400)
                        try:
                            query = {k: int(v) for k, v in request.query_params.items()}
                        except ValueError:
                            raise LiveError("INVALID_REQUEST", 400) from None
                        validate("event_query", query)
                        return response(service.events(run, query["after"], query.get("limit", 100)))
                    return response(service.snapshot(run))
                commands = {"/api/sessions": "prepare", "/api/runs": "start_run",
                            "/api/session/release": "release", "/api/dialogue": "dialogue"}
                command = commands.get(path)
                if run_id:
                    command = "decide" if path.endswith("/decisions") else "stop"
                if request.method != "POST" or command is None:
                    raise LiveError("NOT_FOUND", 404)
                validate(command, body)
                return response(service.command(session, path, body), 202)
        except LiveError as error:
            command_id = body.get("command_id") if isinstance(body, dict) else None
            if not isinstance(command_id, str) or len(command_id) > 80:
                command_id = None
            return response({"kind": "error", "version": "live.v1", "command_id": command_id,
                             "code": error.code, "message": error.code, "server_time": now()},
                            error.status)

    routes = [Route(path, endpoint, methods=methods) for path, methods in [
        ("/api/status", ["GET"]), ("/api/session", ["GET"]),
        ("/api/session/bootstrap", ["POST"]), ("/api/session/release", ["POST"]),
        ("/api/dialogue", ["POST"]), ("/api/sessions", ["POST"]), ("/api/runs", ["POST"]),
        ("/api/runs/{run_id}", ["GET"]), ("/api/runs/{run_id}/events", ["GET"]),
        ("/api/runs/{run_id}/decisions", ["POST"]), ("/api/runs/{run_id}/stop", ["POST"])]]
    if (service.root / "ui/dist/index.html").exists():
        routes.append(Mount("/", app=StaticFiles(directory=service.root / "ui/dist", html=True)))

    @asynccontextmanager
    async def lifespan(app):
        yield
        service.close()

    app = Starlette(routes=routes, lifespan=lifespan)

    async def local_boundary(request, call_next):
        # Apply Host protection and framing restrictions to static UI as well as APIs.
        if (request.headers.get("host") != parsed.netloc
                or any(name in request.headers for name in
                       ("forwarded", "x-forwarded-for", "x-forwarded-host"))):
            return JSONResponse({"code": "ORIGIN_REJECTED"}, status_code=403)
        result = await call_next(request)
        result.headers["Content-Security-Policy"] = (
            "default-src 'self'; connect-src 'self'; script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        result.headers["X-Frame-Options"] = "DENY"
        result.headers["Referrer-Policy"] = "no-referrer"
        result.headers["X-Content-Type-Options"] = "nosniff"
        return result

    app.add_middleware(BaseHTTPMiddleware, dispatch=local_boundary)
    return app


def main():
    import subprocess

    import uvicorn

    parser = argparse.ArgumentParser(description="BC-012 local dialogue simulator; no LLM calls")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    import sys
    for command in ([sys.executable, "-m", "ruff", "check", "."],
                    [sys.executable, "-m", "pytest", "-q"], ["git", "diff", "--check"]):
        subprocess.run(command, cwd=root, check=True)
    from governed_agent_runtime.live_dialogue import DialogueService
    service = DialogueService(root, args.evidence_dir)
    app = create_app(service, f"http://127.0.0.1:{args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port, workers=1, proxy_headers=False,
                access_log=False)


if __name__ == "__main__":
    main()
