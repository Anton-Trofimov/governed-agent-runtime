"""Reach real coordinator limits, without seeding counters or replacing limit logic.

Direct service calls isolate these limits from the separate HTTP ingress buckets.
All preparations/dialogues/runs use the actual bounded public simulator provider.
"""
import hashlib
import json
import time
from pathlib import Path
from uuid import uuid4

import pytest

from governed_agent_runtime.live_service import LiveError
from governed_agent_runtime.public_simulator import PublicSimulator

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def services(tmp_path):
    instances = []

    def make():
        service = PublicSimulator(ROOT, tmp_path / str(len(instances)))
        instances.append(service)
        return service

    yield make
    for service in instances:
        service.close()


def dispatch(service, session, path, action, **fields):
    body = {'command': action, 'command_id': uuid4().hex, **fields}
    with service.condition:
        return service.command(session, path, body)


def wait_for(service, read, predicate):
    deadline = time.monotonic() + 5
    with service.condition:
        while time.monotonic() < deadline:
            value = read()
            if predicate(value):
                return value
            service.condition.wait(.01)
    raise AssertionError('Synthetic state transition did not finish')


def rejected_run(service, session):
    ack = dispatch(service, session, '/api/sessions', 'prepare')
    wait_for(service, lambda: service.slot, lambda s: s and s['phase'] == 'ready')
    dispatch(service, session, '/api/dialogue', 'dialogue',
             reservation_id=ack['reservation_id'], choice_id='recover')
    run = wait_for(service, lambda: session['current'], bool)
    pending = wait_for(service, lambda: service.snapshot(service.runs[run]),
                       lambda s: s['pending_confirmation'])
    dispatch(service, session, f'/api/runs/{run}/decisions', 'decide',
             confirmation_id=pending['pending_confirmation']['confirmation_id'], decision='reject')
    wait_for(service, lambda: service.runs[run]['phase'], lambda s: s == 'terminal')
    assert service.slot is None
    return run


def state_digest(service):
    """Compare mutations without printing cookies, session IDs or raw evidence on failure."""
    with service.condition:
        value = {'sessions': service.sessions, 'preparations': service.preparations,
                 'slot_empty': service.slot is None,
                 'runs': {key: {'snapshot': stable_snapshot(service, run), 'events': run['events']}
                          for key, run in service.runs.items()},
                 'files': {str(p.relative_to(service.evidence)):
                           hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in service.evidence.rglob('*') if p.is_file()}}
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def stable_snapshot(service, run):
    value = service.snapshot(run)
    # Response generation time is not a mutation of the run or coordinator.
    value.pop('server_time')
    return value


def test_sixteen_sessions_are_service_wide_and_seventeenth_is_side_effect_free(services):
    service = services()
    tokens = []
    for count in range(1, 17):
        token, _ = service.bootstrap()
        tokens.append(token)
        assert len(service.sessions) == count
    assert len(set(tokens)) == 16
    # Existing sessions can still restore at capacity without allocating another.
    token, session = service.bootstrap(tokens[0])
    assert token == tokens[0]
    assert service.authenticate(token) is session
    before = state_digest(service)
    with pytest.raises(LiveError) as rejected:
        service.bootstrap()
    assert (rejected.value.code, rejected.value.status) == ('SESSION_CAPACITY', 503)
    assert state_digest(service) == before
    # The cap is per service/process, not shared between independent instances.
    other = services()
    other.bootstrap()
    assert len(other.sessions) == 1
    assert len(service.sessions) == 16


def test_eight_runs_are_per_session_and_ninth_admission_has_no_effect(services):
    service = services()
    _, session = service.bootstrap()
    for count in range(1, 9):
        rejected_run(service, session)
        assert len(session['runs']) == count
        assert service.preparations == count
    assert len(service.runs) == 8
    before = state_digest(service)
    with pytest.raises(LiveError) as rejected:
        dispatch(service, session, '/api/sessions', 'prepare')
    assert rejected.value.code == 'SESSION_LIMIT'
    assert state_digest(service) == before
    # The 20-preparation process allowance is not exhausted; another session works.
    _, other = service.bootstrap()
    rejected_run(service, other)
    assert len(other['runs']) == 1
    assert len(session['runs']) == 8
    assert service.preparations == 9


def test_command_cap_reserves_stop_capacity_and_preserves_replay_at_512(services):
    service = services()
    _, session = service.bootstrap()
    run = rejected_run(service, session)
    path = f'/api/runs/{run}/stop'
    snapshot = stable_snapshot(service, service.runs[run])
    events = len(service.runs[run]['events'])
    # Each distinct stop is a real accepted command record. Terminal stops must
    # not rerun tools, emit stop events or mutate the terminal run.
    while len(session['commands']) < 480:
        dispatch(service, session, path, 'stop')
    before = state_digest(service)
    with pytest.raises(LiveError) as ordinary:
        dispatch(service, session, '/api/sessions', 'prepare')
    assert ordinary.value.code == 'SESSION_LIMIT'
    assert state_digest(service) == before
    assert len(session['commands']) == 480
    while len(session['commands']) < 511:
        dispatch(service, session, path, 'stop')
    body = {'command': 'stop', 'command_id': uuid4().hex}
    with service.condition:
        ack = service.command(session, path, body)
    assert len(session['commands']) == 512
    assert stable_snapshot(service, service.runs[run]) == snapshot
    assert len(service.runs[run]['events']) == events
    before = state_digest(service)
    with pytest.raises(LiveError) as overflow:
        dispatch(service, session, path, 'stop')
    assert overflow.value.code == 'SESSION_LIMIT'
    assert state_digest(service) == before
    with service.condition:
        assert service.command(session, path, body) == ack
    assert state_digest(service) == before
    with pytest.raises(LiveError) as conflict, service.condition:
        service.command(session, path, {**body, 'command': 'decide',
                                      'confirmation_id': 'unknown', 'decision': 'approve'})
    assert conflict.value.code == 'COMMAND_CONFLICT'
    assert state_digest(service) == before
    # Another session has its own command ledger and can still admit a run.
    _, other = service.bootstrap()
    rejected_run(service, other)
    assert len(session['commands']) == 512
    assert len(other['commands']) < 480
