"""Fake-provider boundary checks; no semantic-quality or real-inference claim."""
from threading import Event

import pytest
from starlette.testclient import TestClient

from governed_agent_runtime.live_dialogue import DialogueService
from governed_agent_runtime.live_http import create_app
from governed_agent_runtime.live_service import SimulatedModel
from tests.contract.test_bc011_live_http import HEADERS, ORIGIN, ROOT, pending, post, wait_for


class Scripted(SimulatedModel):
    def __init__(self, outcomes=('answer',)):
        self.outcomes = iter(outcomes)
        self.contexts = []
        self.entered, self.release = Event(), Event()
        self.block = False

    def converse(self, context, *, evidence_dir):
        self.contexts.append(context)
        self.entered.set()
        if self.block:
            self.release.wait(3)
        outcome = next(self.outcomes)
        if isinstance(outcome, dict):
            return {'done': True, 'proposal': outcome}
        return {'done': True, 'proposal': {'outcome': outcome, 'reply': 'Ответ по сценарию',
                'goal_message_ids': [m['id'] for m in context['messages'] if m['actor'] == 'operator']
                if outcome == 'start_remediation' else []}}


@pytest.fixture
def setup(tmp_path):
    services = []
    def make(provider=None, **kw):
        service = DialogueService(ROOT, tmp_path / str(len(services)), provider=provider or Scripted(), **kw)
        client = TestClient(create_app(service), base_url=ORIGIN)
        services.append((service, client))
        post(client, '/api/session/bootstrap', 'bootstrap')
        prepared = post(client, '/api/sessions', 'prepare').json()
        wait_for(lambda: client.get('/api/session').json(), lambda s: s['reservation']['phase'] == 'ready')
        return service, client, prepared['reservation_id']
    yield make
    for service, client in services:
        if hasattr(service.provider, 'release'):
            service.provider.release.set()
        client.close()
        service.close()


def say(client, reservation, text='Что ты умеешь?', **kw):
    return post(client, '/api/dialogue', 'dialogue', reservation_id=reservation, text=text, **kw)


def settled(client):
    return wait_for(lambda: client.get('/api/session').json(),
                    lambda s: s.get('dialogue', {}).get('state') in {'ready', 'admitted', 'terminal'}
                    and s['dialogue']['calls'] > 0)


def test_answer_has_no_remediation_or_tools_and_restores_read_only(setup):
    service, client, reservation = setup()
    assert say(client, reservation).status_code == 202
    s = settled(client)
    assert s['current_run_id'] is None and service.runs == {}
    assert [m['actor'] for m in s['dialogue']['messages']] == ['operator', 'agent']
    assert client.get('/api/session').json()['dialogue'] == s['dialogue']
    assert len(service.provider.contexts) == 1


def test_legacy_start_cannot_bypass_goal_admission(setup):
    _, client, reservation = setup()
    response = post(client, '/api/runs', 'start_run', reservation_id=reservation, goal='Do it')
    assert response.status_code == 409
    assert response.json()['code'] == 'GOAL_ADMISSION_REQUIRED'


def test_clarification_start_preserves_user_text_and_exact_confirmations(setup):
    service, client, reservation = setup(Scripted(('clarify', 'start_remediation')))
    say(client, reservation, 'Можешь помочь?')
    settled(client)
    say(client, reservation, 'Да, восстанови сервис')
    s = wait_for(lambda: client.get('/api/session').json(), lambda s: s['current_run_id'])
    run = pending(client, s['current_run_id'])
    assert run['phase'] == 'awaiting_confirmation'
    assert run['goal'] == 'Можешь помочь?\n\nДа, восстанови сервис'
    assert run['service_view']['desired'] == 6
    assert len(service.runs) == 1
    assert say(client, reservation).status_code == 409
    assert s['dialogue']['state'] == 'admitted'


@pytest.mark.parametrize('bad', [
    {'outcome':'answer','reply':' \n\t','goal_message_ids':[]},
    {'outcome':'answer','reply':'','goal_message_ids':[]},
    {'outcome':'start_remediation','reply':'ok','goal_message_ids':['foreign']},
    {'outcome':'answer','reply':'ok','goal_message_ids':[], 'tool':'scale_stable'},
    {'outcome':'start_remediation','reply':'ok','goal_message_ids':[]},
])
def test_invalid_model_output_never_defaults_to_execution(setup, bad):
    service, client, reservation = setup(Scripted((bad,)))
    say(client, reservation)
    s = settled(client)
    assert s['dialogue']['state'] == 'terminal'
    assert s['dialogue']['reason'] == 'DIALOGUE_INVALID_OUTPUT'
    assert not service.runs


def test_five_calls_and_no_sixth_or_automatic_retry(setup):
    service, client, reservation = setup(Scripted(('answer',) * 5))
    for i in range(5):
        assert say(client, reservation, f'Вопрос {i}').status_code == 202
        wait_for(lambda: client.get('/api/session').json(), lambda s, index=i:
                 s['dialogue']['calls'] == index + 1 and s['dialogue']['state'] != 'thinking')
    s = settled(client)
    assert s['dialogue']['reason'] == 'DIALOGUE_LIMIT'
    assert say(client, reservation).status_code != 202
    assert len(service.provider.contexts) == 5 and not service.runs


def test_fifth_call_can_admit_goal(setup):
    _, client, reservation = setup(Scripted(('answer',)*4+('start_remediation',)))
    for i in range(5):
        say(client, reservation, f'Восстанови сервис {i}')
        wait_for(lambda: client.get('/api/session').json(), lambda s, index=i:
                 s['dialogue']['calls'] == index + 1 and s['dialogue']['state'] != 'thinking')
    assert settled(client)['current_run_id']


def test_duplicate_conflict_foreign_session_and_pending_input(setup):
    provider = Scripted()
    provider.block = True
    service, client, reservation = setup(provider)
    body = {'command':'dialogue','command_id':'same-command','reservation_id':reservation,'text':'Что ты умеешь?'}
    first = client.post('/api/dialogue', json=body, headers=HEADERS)
    assert first.status_code == 202
    assert provider.entered.wait(1)
    assert client.post('/api/dialogue', json=body, headers=HEADERS).json() == first.json()
    assert client.post('/api/dialogue', json={**body,'text':'changed'}, headers=HEADERS).status_code == 409
    assert say(client, reservation).status_code == 409
    other = TestClient(create_app(service), base_url=ORIGIN)
    post(other, '/api/session/bootstrap', 'bootstrap')
    assert say(other, reservation).status_code == 404
    assert other.get('/api/session').json()['dialogue'] is None
    assert client.get('/api/status').json()['availability'] == 'busy'
    provider.release.set()
    settled(client)
    assert len(provider.contexts) == 1
    other.close()


def test_expiry_discards_late_start_and_keeps_slot_until_completion(setup):
    clock = [0.]
    provider = Scripted(('start_remediation',)); provider.block = True
    service, client, reservation = setup(provider, monotonic=lambda:clock[0])
    say(client, reservation, 'Восстанови сервис')
    assert provider.entered.wait(1)
    clock[0] = 601
    assert client.get('/api/session').json()['dialogue']['reason'] == 'DIALOGUE_EXPIRED'
    assert client.get('/api/status').json()['availability'] == 'busy'
    provider.release.set()
    wait_for(lambda: client.get('/api/status').json(), lambda s: s['availability'] == 'available')
    assert not service.runs


def test_idle_polling_does_not_renew_or_admit_after_expiry(setup):
    clock = [0.]
    service, client, reservation = setup(monotonic=lambda:clock[0])
    clock[0] = 299
    client.get('/api/session')
    clock[0] = 300
    assert say(client, reservation).status_code != 202
    assert client.get('/api/session').json()['dialogue']['reason'] == 'DIALOGUE_EXPIRED'
    assert not service.runs


def test_unknown_completion_quarantines_until_actual_completion(setup):
    provider = Scripted(('start_remediation',)); provider.block = True
    service, client, reservation = setup(provider, inference_seconds=.02, reconciliation_seconds=1)
    say(client, reservation, 'Восстанови сервис')
    wait_for(lambda: client.get('/api/status').json(), lambda s: s['availability'] == 'unavailable')
    assert service.marker.exists() and not service.runs
    provider.release.set()
    wait_for(lambda: client.get('/api/status').json(), lambda s: s['availability'] == 'available')
    assert not service.marker.exists() and not service.runs


def test_release_during_reply_discards_late_start(setup):
    provider = Scripted(('start_remediation',)); provider.block = True
    service, client, reservation = setup(provider)
    say(client, reservation, 'Восстанови сервис')
    assert provider.entered.wait(1)
    assert post(client, '/api/session/release', 'release', reservation_id=reservation).status_code == 202
    assert client.get('/api/status').json()['availability'] == 'busy'
    provider.release.set()
    wait_for(lambda: client.get('/api/status').json(), lambda s: s['availability'] == 'available')
    assert not service.runs
    assert settled(client)['dialogue']['reason'] == 'DIALOGUE_RELEASED'


def test_next_answer_does_not_reset_absolute_window(setup):
    clock = [0.]
    _, client, reservation = setup(Scripted(('answer',)*3), monotonic=lambda:clock[0])
    for tick in (250, 500):
        clock[0] = tick
        say(client, reservation)
        wait_for(lambda: client.get('/api/session').json(), lambda s, expected=tick//250:
                 s['dialogue']['state'] == 'ready' and s['dialogue']['calls'] == expected)
    clock[0] = 600
    assert say(client, reservation).status_code != 202
    assert client.get('/api/session').json()['dialogue']['reason'] == 'DIALOGUE_EXPIRED'


def test_user_references_cannot_point_only_to_an_earlier_goal(setup):
    class Earlier(Scripted):
        def converse(self, context, *, evidence_dir):
            reply = super().converse(context, evidence_dir=evidence_dir)
            if len(context['messages']) > 1:
                reply['proposal']['goal_message_ids'] = [context['messages'][0]['id']]
            return reply
    service, client, reservation = setup(Earlier(('clarify', 'start_remediation')))
    say(client, reservation, 'Восстанови сервис')
    settled(client)
    say(client, reservation, 'Нет, не надо')
    s = wait_for(lambda: client.get('/api/session').json(), lambda s: s['dialogue']['state'] == 'terminal')
    assert s['dialogue']['reason'] == 'DIALOGUE_INVALID_OUTPUT'
    assert not service.runs


def test_original_goal_limit_is_not_silently_truncated(setup):
    service, client, reservation = setup(Scripted(('clarify', 'start_remediation')))
    say(client, reservation, 'x'*1500)
    settled(client)
    say(client, reservation, 'y'*1500)
    s = wait_for(lambda: client.get('/api/session').json(), lambda s: s['dialogue']['state'] == 'terminal')
    assert s['dialogue']['reason'] == 'DIALOGUE_GOAL_TOO_LONG' and not service.runs


def test_queue_before_preparation_and_failure_never_starts_runtime(tmp_path):
    class Slow(Scripted):
        def prepare(self):
            self.entered.set()
            self.release.wait(2)
            return {'done': True, 'error': 'FAILED'}
    provider = Slow()
    service = DialogueService(ROOT, tmp_path/'queued', provider=provider)
    with TestClient(create_app(service), base_url=ORIGIN) as client:
        post(client, '/api/session/bootstrap', 'bootstrap')
        reservation = post(client, '/api/sessions', 'prepare').json()['reservation_id']
        assert provider.entered.wait(1)
        assert say(client, reservation).status_code == 202
        assert say(client, reservation).status_code == 409
        provider.release.set()
        s = wait_for(lambda: client.get('/api/session').json(), lambda s: s['dialogue']['state'] == 'terminal')
        assert s['dialogue']['messages'][0]['text'] == 'Что ты умеешь?'
        assert not provider.contexts and not service.runs


def test_queue_before_preparation_starts_one_dialogue_not_a_run(tmp_path):
    class Slow(Scripted):
        def prepare(self):
            self.entered.set()
            self.release.wait(2)
            return {'done': True}
    provider = Slow()
    service = DialogueService(ROOT, tmp_path/'queued', provider=provider)
    with TestClient(create_app(service), base_url=ORIGIN) as client:
        post(client, '/api/session/bootstrap', 'bootstrap')
        reservation = post(client, '/api/sessions', 'prepare').json()['reservation_id']
        assert provider.entered.wait(1)
        assert say(client, reservation).status_code == 202
        provider.release.set()
        assert settled(client)['dialogue']['state'] == 'ready'
        assert len(provider.contexts) == 1 and not service.runs


def test_http_schema_bounds_and_session_projection(setup):
    import json

    from jsonschema import Draft202012Validator

    service, client, reservation = setup()
    for text in ('', '  ', 'a'*2001):
        assert say(client, reservation, text).status_code == 400
    assert say(client, reservation, target='real-service').status_code == 400
    assert not service.provider.contexts
    say(client, reservation)
    view = settled(client)
    schema = json.loads((ROOT/'schemas/bc011-live.schema.json').read_text())
    Draft202012Validator(schema).validate(view)


def test_local_ollama_dialogue_uses_separate_schema_and_evidence_without_network(tmp_path, monkeypatch):
    from governed_agent_runtime.live_ollama import LocalOllamaModel, load_profile

    provider = LocalOllamaModel(ROOT, tmp_path, load_profile(ROOT))
    seen = []
    monkeypatch.setattr(provider, '_operation', lambda *args: seen.append(args) or {'done':True})
    context = {'messages':[{'actor':'operator','text':'Что ты умеешь?'}]}
    provider.converse(context, evidence_dir=tmp_path/'dialogue')
    path, payload, directory, timeout = seen[0]
    assert path == '/api/chat' and directory == tmp_path/'dialogue' and timeout == 300
    assert payload['format']['properties']['outcome']['enum'] == ['answer','clarify','unsupported','start_remediation']
    assert 'tool_name' not in payload['format']['properties']
    assert payload['model'] == provider.adapter.model_identity


def test_dialogue_provider_projection_preserves_authoritative_validation(tmp_path, monkeypatch):
    import json
    from copy import deepcopy

    from jsonschema import Draft202012Validator

    from governed_agent_runtime.live_ollama import LocalOllamaModel, load_profile

    authoritative = json.loads((ROOT / 'schemas/bc012-dialogue.schema.json').read_text())
    expected = deepcopy(authoritative)
    del expected['properties']['reply']['pattern']
    provider = LocalOllamaModel(ROOT, tmp_path, load_profile(ROOT))
    captured = []
    monkeypatch.setattr(provider, '_operation', lambda *args: captured.append(args) or {'done': True})
    provider.converse({}, evidence_dir=tmp_path / 'dialogue')
    assert captured[0][1]['format'] == expected
    assert json.loads((ROOT / 'schemas/bc012-dialogue.schema.json').read_text()) == authoritative
    validator = Draft202012Validator(authoritative)
    for text in ('', ' ', '\n\t', '\u00a0'):
        assert not validator.is_valid({'outcome': 'answer', 'reply': text, 'goal_message_ids': []})
    assert validator.is_valid({'outcome': 'answer', 'reply': 'Первая строка.\nВторая строка.', 'goal_message_ids': []})


def test_dialogue_context_exposes_only_contracted_execution_capabilities(setup):
    import yaml

    service, client, reservation = setup()
    say(client, reservation)
    settled(client)
    context = service.provider.contexts[0]
    contract = yaml.safe_load((ROOT / 'specs/core/bounded-remediation.yaml').read_text())
    fields = ('tool_name', 'category', 'preconditions', 'confirmation_required')
    assert context['remediation_capabilities'] == [
        {key: tool[key] for key in fields} for tool in contract['tools']]
    assert context['capacity_rule'] == next(r for r in contract['rules'] if r['constraint_id'] == 'BC006-capacity')
    assert context['observation_scope']['healthy'] == 'stable_version_id'
    assert context['observation_scope']['desired'] == 'stable_version_id'
    assert context['observation_scope']['candidate_count'] == 'candidate_version_id; health not established'
    assert not service.runs


@pytest.mark.parametrize('outcome', ['answer', 'clarify', 'unsupported'])
def test_non_start_with_real_user_reference_is_rejected_without_retry(setup, outcome):
    class ReferencingAnswer(Scripted):
        def converse(self, context, *, evidence_dir):
            self.contexts.append(context)
            return {'done': True, 'proposal': {
                'outcome': outcome, 'reply': 'Информационный ответ',
                'goal_message_ids': [context['messages'][-1]['id']]}}

    provider = ReferencingAnswer()
    service, client, reservation = setup(provider)
    say(client, reservation)
    view = settled(client)
    assert view['dialogue']['state'] == 'terminal'
    assert view['dialogue']['reason'] == 'DIALOGUE_INVALID_OUTPUT'
    assert [m['actor'] for m in view['dialogue']['messages']] == ['operator']
    assert len(provider.contexts) == 1
    assert not service.runs
