import asyncio
import time
from pathlib import Path
from uuid import uuid4

import pytest
from starlette.requests import Request
from starlette.testclient import TestClient

from governed_agent_runtime.live_dialogue import DialogueService
from governed_agent_runtime.live_http import create_app

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = 'https://demo.example'
HEADERS = {'origin': ORIGIN, 'x-gar-request': 'live.v1'}


def post(client, path, command, **fields):
    return client.post(path, json={'command': command, 'command_id': uuid4().hex, **fields},
                       headers=HEADERS)


@pytest.fixture
def public(tmp_path):
    from governed_agent_runtime.public_simulator import create_public_simulator
    app = create_public_simulator(ROOT, tmp_path, ORIGIN, 'https://site.example')
    with TestClient(app, base_url=ORIGIN) as client:
        yield app, client


def test_unreviewed_local_factory_rejects_public_origin(tmp_path):
    service = DialogueService(ROOT, tmp_path)
    try:
        with pytest.raises(ValueError):
            create_app(service, 'https://demo.example')
    finally:
        service.close()


def test_public_factory_secure_cookie_and_status_without_session(tmp_path):
    # The entry point is deliberately separate from the existing local factory.
    from governed_agent_runtime import public_simulator
    app = public_simulator.create_public_simulator(ROOT, tmp_path, 'https://demo.example',
                                                   'https://site.example')
    with TestClient(app, base_url='https://demo.example') as client:
        status = client.get('/public/status', headers={'origin': 'https://site.example',
                                                      'sec-fetch-site': 'cross-site'})
        assert status.json() == {'availability': 'available', 'provider': 'simulator'}
        assert status.headers['access-control-allow-origin'] == 'https://site.example'
        assert 'set-cookie' not in status.headers
        response = client.post('/api/session/bootstrap', json={
            'command': 'bootstrap', 'command_id': 'first'}, headers={
            'origin': 'https://demo.example', 'x-gar-request': 'live.v1'})
        assert response.status_code == 200
        assert 'Secure' in response.headers['set-cookie']
        assert 'HttpOnly' in response.headers['set-cookie']
        assert 'SameSite=strict' in response.headers['set-cookie']


def test_cors_only_for_public_status_and_no_admin(public):
    app, client = public
    for path in ['/api/status', '/api/session/bootstrap', '/api/admin/admissions']:
        response = client.get(path, headers={'origin': 'https://site.example'})
        assert response.status_code in {403, 404, 405}
        assert 'access-control-allow-origin' not in response.headers
    assert client.get('/public/status', headers={'origin': 'https://evil.example'}).status_code == 403
    assert client.options('/public/status').status_code == 405
    assert client.get('/api/status', headers={'host': 'wrong.example'}).status_code == 403
    assert client.get('/api/status', headers={'x-forwarded-host': 'wrong.example'}).status_code == 200
    assert not app.service.sessions
    assert app.service.preparations == 0
    assert not hasattr(app.service.provider, 'client')


def test_session_isolation_fixed_input_and_single_slot(public):
    app, client = public
    assert post(client, '/api/session/bootstrap', 'bootstrap').status_code == 200
    first_cookie = dict(client.cookies)
    prepared = post(client, '/api/sessions', 'prepare')
    reservation = prepared.json()['reservation_id']
    assert post(client, '/api/dialogue', 'dialogue', reservation_id=reservation,
                text='arbitrary free text').status_code == 400
    assert post(client, '/api/runs', 'start_run', reservation_id=reservation,
                goal='Восстанови сервис').status_code == 409
    client.cookies.clear()
    assert client.get('/api/session').status_code == 401
    assert post(client, '/api/session/bootstrap', 'bootstrap').status_code == 200
    assert post(client, '/api/sessions', 'prepare').json()['code'] == 'LIVE_BUSY'
    assert post(client, '/api/session/release', 'release', reservation_id=reservation).status_code != 202
    client.cookies.clear()
    client.cookies.update(first_cookie)
    view = client.get('/api/session').json()
    assert view['input_policy']['profile'] == 'preset-only'
    assert view['provider']['kind'] == 'simulator'
    assert app.service.preparations == 1


def test_body_limit_and_exact_origin(public):
    _, client = public
    for origin in ['', 'null', 'https://site.example']:
        assert client.post('/api/session/bootstrap', json={}, headers={**HEADERS, 'origin': origin}).status_code == 403
    assert client.post('/api/session/bootstrap', content='x'*16385,
                       headers={**HEADERS, 'content-type': 'application/json'}).status_code == 413


def test_global_limits_and_admission_deadline(public):
    app, client = public
    assert post(client, '/api/session/bootstrap', 'bootstrap').status_code == 200
    app.service.preparations = 20
    assert client.get('/public/status').json()['availability'] == 'unavailable'
    assert post(client, '/api/sessions', 'prepare').json()['code'] == 'SMOKE_LIMIT'
    app.service.preparations = 0
    app.service.admission_deadline = 0
    assert client.get('/public/status').json()['availability'] == 'unavailable'
    assert post(client, '/api/sessions', 'prepare').json()['code'] == 'PUBLIC_PAUSED'
    app.requests.tokens = 0
    response = client.get('/public/status')
    assert response.status_code == 429 and response.headers['retry-after'] == '15'


def test_prepare_replay_does_not_spend_allowance_twice(public):
    app, client = public
    post(client, '/api/session/bootstrap', 'bootstrap')
    body = {'command': 'prepare', 'command_id': 'same'}
    first = client.post('/api/sessions', json=body, headers=HEADERS)
    app.service.admission_deadline = 0
    second = client.post('/api/sessions', json=body, headers=HEADERS)
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    assert app.service.preparations == 1


def test_public_nominal_path_and_run_ownership(public):
    app, client = public
    post(client, '/api/session/bootstrap', 'bootstrap')
    prepared = post(client, '/api/sessions', 'prepare').json()
    def wait(read, condition):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            value = read()
            if condition(value):
                return value
            time.sleep(.01)
        raise AssertionError(value)
    wait(lambda: client.get('/api/session').json(),
         lambda s: s['reservation'] and s['reservation']['phase'] == 'ready')
    assert post(client, '/api/dialogue', 'dialogue', reservation_id=prepared['reservation_id'],
                choice_id='recover').status_code == 202
    session = wait(lambda: client.get('/api/session').json(), lambda s: s['current_run_id'])
    run_id = session['current_run_id']
    cookie = dict(client.cookies)
    client.cookies.clear()
    post(client, '/api/session/bootstrap', 'bootstrap')
    assert client.get(f'/api/runs/{run_id}').status_code == 404
    assert post(client, f'/api/runs/{run_id}/stop', 'stop').status_code == 404
    client.cookies.clear()
    client.cookies.update(cookie)
    previous = None
    for _ in range(3):
        snap = wait(lambda: client.get(f'/api/runs/{run_id}').json(),
                    lambda s, previous=previous: s['pending_confirmation'] and s['pending_confirmation']['confirmation_id'] != previous)
        previous = snap['pending_confirmation']['confirmation_id']
        assert post(client, f'/api/runs/{run_id}/decisions', 'decide',
                    confirmation_id=previous, decision='approve').status_code == 202
    snap = wait(lambda: client.get(f'/api/runs/{run_id}').json(), lambda s: s['phase'] == 'terminal')
    assert snap['terminal']['runtime_outcome']['task_state'] == 'COMPLETED'
    assert app.service.provider_info == {'kind': 'simulator', 'model_name': None}


def test_body_read_deadline_before_any_session(public, monkeypatch):
    app, _ = public
    real_timeout = asyncio.timeout
    deadlines = []
    def timeout(seconds):
        deadlines.append(seconds)
        return real_timeout(.01)
    monkeypatch.setattr('governed_agent_runtime.live_http.asyncio.timeout', timeout)
    async def receive():
        await asyncio.sleep(1)
        return {'type': 'http.request', 'body': b'{}'}
    scope = {'type': 'http', 'method': 'POST', 'path': '/api/session/bootstrap',
             'headers': [(b'host', b'demo.example'), (b'origin', ORIGIN.encode()),
                         (b'x-gar-request', b'live.v1'), (b'content-type', b'application/json')]}
    endpoint = next(r.endpoint for r in app.app.routes if getattr(r, 'path', '') == '/api/session/bootstrap')
    response = asyncio.run(endpoint(Request(scope, receive)))
    assert response.status_code == 408
    assert deadlines == [5]
    assert not app.service.sessions
