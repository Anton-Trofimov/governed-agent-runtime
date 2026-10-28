"""Local paired-listener boundary tests; no real provider calls."""
from uuid import uuid4

from starlette.testclient import TestClient

from governed_agent_runtime.live_dialogue import DialogueService
from governed_agent_runtime.live_dual_http import paired_apps
from tests.contract.test_bc011_live_http import ROOT

PUBLIC = 'http://127.0.0.1:8000'
OWNER = 'http://127.0.0.1:8001'


def send(client, path, command, **fields):
    return client.post(path, json={'command': command, 'command_id': uuid4().hex, **fields},
                       headers={'origin': str(client.base_url).rstrip('/'), 'x-gar-request': 'live.v1'})


def test_entrypoint_tokens_cannot_be_replayed_on_the_other_listener(tmp_path):
    service = DialogueService(ROOT, tmp_path)
    public_app, owner_app = paired_apps(service, PUBLIC, OWNER)
    try:
        with TestClient(public_app, base_url=PUBLIC) as public, TestClient(owner_app, base_url=OWNER) as owner:
            assert send(owner, '/api/session/bootstrap', 'bootstrap').status_code == 200
            stolen = next(iter(owner.cookies.values()))
            # Try both conventional and entry-specific names: scope must be checked server-side.
            for name in ('gar_local_session', 'gar_public_session', 'gar_owner_session'):
                public.cookies.set(name, stolen)
            assert public.get('/api/session').status_code == 401
    finally:
        service.close()


def test_shared_slot_profiles_pause_and_no_preemption(tmp_path):
    from tests.contract.test_bc011_live_http import wait_for
    service = DialogueService(ROOT, tmp_path)
    apps = paired_apps(service, PUBLIC, OWNER)
    try:
        with TestClient(apps[0], base_url=PUBLIC) as public, TestClient(apps[1], base_url=OWNER) as owner:
            assert public.get('/api/status').json()['availability'] == 'available'
            assert send(owner, '/api/admin/admissions', 'set_public_admissions', enabled=False).status_code == 200
            assert 'public_admissions_enabled' not in public.get('/api/status').json()
            assert owner.get('/api/status').json()['public_admissions_enabled'] is False
            assert service.preparations == 0 and service.slot is None
            for client in (public, owner):
                assert send(client, '/api/session/bootstrap', 'bootstrap').status_code == 200
            assert public.get('/api/session').json()['input_policy']['profile'] == 'preset-only'
            assert owner.get('/api/session').json()['input_policy']['profile'] == 'local-free-text'
            assert send(public, '/api/sessions', 'prepare').json()['code'] == 'PUBLIC_PAUSED'
            assert send(public, '/api/admin/admissions', 'set_public_admissions', enabled=True).status_code in (404, 405)
            assert send(owner, '/api/admin/admissions', 'set_public_admissions', enabled=True).status_code == 200
            started = send(public, '/api/sessions', 'prepare').json()
            reservation = started['reservation_id']
            wait_for(lambda: public.get('/api/session').json(), lambda s: s['reservation']['phase'] == 'ready')
            assert owner.get('/api/status').json()['availability'] == 'busy'
            assert send(owner, '/api/sessions', 'prepare').json()['code'] == 'LIVE_BUSY'
            assert send(public, '/api/dialogue', 'dialogue', reservation_id=reservation, text='override').status_code == 400
            assert send(public, '/api/dialogue', 'dialogue', reservation_id=reservation, choice_id='state', input_profile='local-free-text').status_code == 400
            assert send(owner, '/api/admin/admissions', 'set_public_admissions', enabled=False).status_code == 200
            # Existing admission continues after pause. Its profile cannot be selected through a URL.
            assert public.get('/api/session?input_profile=local-free-text').json()['input_policy']['profile'] == 'preset-only'
            assert send(public, '/api/dialogue', 'dialogue', reservation_id=reservation, choice_id='capabilities').status_code == 202
            wait_for(lambda: public.get('/api/session').json(), lambda s: s['dialogue']['calls'] == 1 and s['dialogue']['state'] == 'ready')
            assert owner.get('/api/session').json()['dialogue'] is None
            assert send(owner, '/api/session/release', 'release', reservation_id=reservation).status_code != 202
            assert service.slot['id'] == reservation
            assert send(public, '/api/session/release', 'release', reservation_id=reservation).status_code == 202
            assert public.get('/api/status').json()['unavailability_reason'] == 'PUBLIC_PAUSED'
            # Owner uses the released slot while public admission remains paused.
            private_reservation = send(owner, '/api/sessions', 'prepare').json()['reservation_id']
            wait_for(lambda: owner.get('/api/session').json(), lambda s: s['reservation']['phase'] == 'ready')
            assert send(owner, '/api/dialogue', 'dialogue', reservation_id=private_reservation, text='Что ты умеешь?').status_code == 202
            wait_for(lambda: owner.get('/api/session').json(), lambda s: s['dialogue']['calls'] == 1 and s['dialogue']['state'] == 'ready')
            assert owner.get('/api/session').json()['input_policy']['max_calls'] == 5
            assert send(owner, '/api/admin/admissions', 'set_public_admissions', enabled=True).status_code == 200
            assert send(public, '/api/sessions', 'prepare').json()['code'] == 'LIVE_BUSY'
            assert service.slot['id'] == private_reservation
            assert send(owner, '/api/session/release', 'release', reservation_id=private_reservation).status_code == 202
            assert public.get('/api/status').json()['availability'] == 'available'
    finally:
        service.close()


def test_listener_origin_and_control_body_are_strict(tmp_path):
    service = DialogueService(ROOT, tmp_path)
    apps = paired_apps(service, PUBLIC, OWNER)
    try:
        with TestClient(apps[0], base_url=PUBLIC) as public, TestClient(apps[1], base_url=OWNER) as owner:
            assert public.get('/api/status', headers={'host':'127.0.0.1:8001'}).status_code == 403
            assert owner.get('/api/admin/admissions', headers={'origin':PUBLIC}).status_code == 403
            assert owner.get('/api/admin/admissions', headers={'x-forwarded-for':'127.0.0.1'}).status_code == 403
            assert send(owner, '/api/admin/admissions', 'set_public_admissions', enabled=True, extra='x').status_code == 400
            assert send(owner, '/api/admin/admissions', 'set_public_admissions', enabled='true').status_code == 400
            assert owner.get('/api/status').json()['public_admissions_enabled'] is True
    finally:
        service.close()


def test_simultaneous_admission_has_one_winner(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    service = DialogueService(ROOT, tmp_path)
    apps = paired_apps(service, PUBLIC, OWNER)
    try:
        with TestClient(apps[0], base_url=PUBLIC) as public, TestClient(apps[1], base_url=OWNER) as owner:
            for client in (public, owner):
                send(client, '/api/session/bootstrap', 'bootstrap')
            send(owner, '/api/admin/admissions', 'set_public_admissions', enabled=True)
            barrier = Barrier(2)
            def start(client):
                barrier.wait()
                return send(client, '/api/sessions', 'prepare')
            with ThreadPoolExecutor(2) as pool:
                responses = list(pool.map(start, (public, owner)))
            assert sorted(r.status_code for r in responses) == [202, 409]
            assert next(r for r in responses if r.status_code == 409).json()['code'] == 'LIVE_BUSY'
            assert service.preparations == 1
    finally:
        service.close()


def test_foreign_run_trace_confirmation_and_stop_are_rejected(tmp_path):
    from tests.contract.test_bc011_live_http import wait_for
    service = DialogueService(ROOT, tmp_path)
    apps = paired_apps(service, PUBLIC, OWNER)
    try:
        with TestClient(apps[0], base_url=PUBLIC) as public, TestClient(apps[1], base_url=OWNER) as owner:
            for client in (public, owner):
                send(client, '/api/session/bootstrap', 'bootstrap')
            reservation = send(owner, '/api/sessions', 'prepare').json()['reservation_id']
            wait_for(lambda: owner.get('/api/session').json(), lambda s: s['reservation']['phase'] == 'ready')
            send(owner, '/api/dialogue', 'dialogue', reservation_id=reservation, text='Восстанови работу сервиса')
            state = wait_for(lambda: owner.get('/api/session').json(), lambda s: s['current_run_id'])
            run_id = state['current_run_id']
            run = wait_for(lambda: owner.get(f'/api/runs/{run_id}').json(), lambda r: r['pending_confirmation'])
            for path in (f'/api/runs/{run_id}', f'/api/runs/{run_id}/events?after=0'):
                assert public.get(path).status_code == 404
            assert send(public, f'/api/runs/{run_id}/decisions', 'decide',
                        confirmation_id=run['pending_confirmation']['confirmation_id'], decision='approve').status_code == 404
            assert send(public, f'/api/runs/{run_id}/stop', 'stop').status_code == 404
            assert owner.get(f'/api/runs/{run_id}').json()['phase'] == 'awaiting_confirmation'
            # Pausing public admission never prevents the owner from stopping its own run.
            assert send(owner, f'/api/runs/{run_id}/stop', 'stop').status_code == 202
    finally:
        service.close()


def test_admission_setting_survives_new_evidence_directory(tmp_path):
    settings = tmp_path / 'settings.json'
    for index, expected in enumerate((True, False, True)):
        service = DialogueService(ROOT, tmp_path / str(index))
        try:
            apps = paired_apps(service, PUBLIC, OWNER, settings_path=settings)
            with TestClient(apps[1], base_url=OWNER) as owner:
                assert owner.get('/api/status').json()['public_admissions_enabled'] is expected
                assert send(owner, '/api/admin/admissions', 'set_public_admissions', enabled=not expected).status_code == 200
        finally:
            service.close()


def test_invalid_saved_setting_prevents_startup(tmp_path):
    import pytest
    settings = tmp_path / 'settings.json'
    settings.write_text('{"enabled": "false"}')
    service = DialogueService(ROOT, tmp_path / 'evidence')
    try:
        with pytest.raises(ValueError):
            paired_apps(service, PUBLIC, OWNER, settings_path=settings)
    finally:
        service.close()


def test_failed_setting_write_preserves_current_admission(tmp_path, monkeypatch):
    service = DialogueService(ROOT, tmp_path)
    try:
        apps = paired_apps(service, PUBLIC, OWNER)
        def fail(*args):
            raise OSError('storage unavailable')
        monkeypatch.setattr('governed_agent_runtime.live_dual_http.save_setting', fail)
        with TestClient(apps[1], base_url=OWNER) as owner:
            assert send(owner, '/api/admin/admissions', 'set_public_admissions', enabled=False).status_code == 503
            assert owner.get('/api/status').json()['public_admissions_enabled'] is True
    finally:
        service.close()
