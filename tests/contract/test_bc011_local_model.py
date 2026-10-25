"""Offline checks only: no requests to a real provider."""
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest

from governed_agent_runtime.bc006_runtime import SYSTEM, RemediationRuntime
from governed_agent_runtime.live_ollama import LocalOllamaModel, load_profile

ROOT = Path(__file__).resolve().parents[2]


def model(tmp_path):
    return LocalOllamaModel(ROOT, tmp_path, load_profile(ROOT))


def metadata(provider):
    config = provider.profile['model_config']
    return [{'version': config['provider']['version']}, {'models': [{
        'name': config['model_identity'], 'digest': config['model_artifact_identity']}]}]


def test_metadata_mismatch_never_preloads(tmp_path):
    provider = model(tmp_path)
    provider._json = Mock(side_effect=[{'version': 'wrong'}])
    result = provider.prepare()
    assert result == {'done': True, 'error': 'PROFILE_MISMATCH'}
    assert provider._json.call_count == 1


def test_preload_and_chat_use_pinned_profile_and_runtime_context(tmp_path):
    provider = model(tmp_path)
    name = provider.profile['model_config']['model_identity']
    provider._json = Mock(side_effect=metadata(provider) + [
        {'done': True, 'model': name, 'response': ''}])
    assert provider.prepare() == {'done': True}
    path, payload, timeout = provider._json.call_args.args
    assert path == '/api/generate' and payload['prompt'] == ''
    assert payload['keep_alive'] == '10m' and payload['stream'] is False
    context = RemediationRuntime(ROOT, operator_goal='Восстанови сервис').issue_context()
    provider._json = Mock(side_effect=metadata(provider) + [{
        'done': True, 'model': name, 'message': {'role': 'assistant', 'content': 'not json'}}])
    result = provider.infer(context, evidence_dir=tmp_path / 'run')
    assert result == {'done': True, 'raw_proposal': 'not json'}
    path, payload, timeout = provider._json.call_args.args
    assert path == '/api/chat'
    assert payload['messages'] == [{'role': 'system', 'content': SYSTEM},
                                   {'role': 'user', 'content': provider.serialize(context)}]
    assert payload['options']['num_ctx'] == 32768
    assert payload['options']['num_predict'] == 8192
    assert timeout <= 300
    evidence = json.loads(next((tmp_path / 'run').glob('provider-*.json')).read_text())
    assert evidence['request'] == payload
    assert evidence['response']['message']['content'] == 'not json'
    assert evidence['duration_seconds'] >= 0


def test_incomplete_provider_response_does_not_claim_completion(tmp_path):
    provider = model(tmp_path)
    provider._json = Mock(side_effect=metadata(provider) + [{'done': False}])
    with pytest.raises(ValueError):
        provider.prepare()


def test_unapproved_or_changed_profile_is_not_executable(tmp_path):
    from governed_agent_runtime.live_ollama import profile_hash, validate_approval
    profile = load_profile(ROOT)
    approval = {'approved': False, 'revision': 'a' * 40,
                'profile_sha256': profile_hash(profile), 'evidence_dir': str(tmp_path),
                'exclusive_provider': True, 'no_outstanding_work': True,
                'reviewer': 'operator', 'approval_id': 'b' * 32}
    with pytest.raises(ValueError):
        validate_approval(approval, profile, 'a' * 40, tmp_path)
    approval['approved'] = True
    validate_approval(approval, profile, 'a' * 40, tmp_path)
    changed = deepcopy(profile)
    changed['model_config']['invocation_parameters']['num_predict'] = 1
    with pytest.raises(ValueError):
        validate_approval(approval, changed, 'a' * 40, tmp_path)
    with pytest.raises(ValueError):
        validate_approval(approval, profile, 'c' * 40, tmp_path)


def test_transport_disables_proxy_redirects_and_caps_response(tmp_path, monkeypatch):
    from governed_agent_runtime.live_ollama import MAX_RESPONSE, NoRedirect
    provider = model(tmp_path)
    with pytest.raises(ValueError, match='redirect'):
        NoRedirect().redirect_request(None, None, 302, '', {}, 'https://foreign.invalid')
    monkeypatch.setenv('HTTP_PROXY', 'http://foreign.invalid:80')
    monkeypatch.setenv('HTTPS_PROXY', 'http://foreign.invalid:80')
    provider = model(tmp_path)
    assert not any(getattr(h, 'proxies', {}) for h in provider.opener.handlers)
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = b'x' * (MAX_RESPONSE + 1)
    provider.opener.open = Mock(return_value=response)
    with pytest.raises(ValueError, match='limit'):
        provider._json('/api/version', None, 5)
    response.read.assert_called_once_with(MAX_RESPONSE + 1)
    assert provider.opener.open.call_args.args[0].full_url == 'http://127.0.0.1:11434/api/version'
    with pytest.raises(ValueError):
        provider._json('https://foreign.invalid', None, 5)


def test_local_provider_with_real_coordinator_requires_human_consent(tmp_path):
    from starlette.testclient import TestClient

    from governed_agent_runtime.live_http import create_app
    from governed_agent_runtime.live_service import LiveService, SimulatedModel
    from tests.contract.test_bc011_live_http import ORIGIN, pending, post, start, wait_for

    provider = model(tmp_path)
    name = provider.provider_info['model_name']
    calls = []

    def respond(path, payload, timeout):
        calls.append(path)
        if path == '/api/version':
            return metadata(provider)[0]
        if path == '/api/tags':
            return metadata(provider)[1]
        if path == '/api/generate':
            return {'model': name, 'done': True, 'response': ''}
        context = json.loads(payload['messages'][1]['content'])
        proposal = SimulatedModel().infer(context)['proposal']
        return {'model': name, 'done': True, 'message': {'content': json.dumps(proposal)}}

    provider._json = respond
    service = LiveService(ROOT, tmp_path / 'evidence', provider=provider, max_preparations=2,
                          operation_dir=tmp_path / 'shared')
    with TestClient(create_app(service), base_url=ORIGIN) as client:
        status = client.get('/api/status')
        assert status.json()['provider']['kind'] == 'ollama'
        assert calls == []  # Polling does not preload or infer.
        run_id = start(client)
        snap = pending(client, run_id)
        assert snap['phase'] == 'awaiting_confirmation'
        assert service.runs[run_id]['rt'].adapter_calls == []
        post(client, f'/api/runs/{run_id}/decisions', 'decide', decision='reject',
             confirmation_id=snap['pending_confirmation']['confirmation_id'])
        wait_for(lambda: client.get(f'/api/runs/{run_id}').json(), lambda s: s['phase'] == 'terminal')
        manifest = json.loads((service.evidence / run_id / 'manifest.json').read_text())
        assert manifest['real_inference'] is True
        assert calls.count('/api/chat') == 1
        assert post(client, '/api/sessions', 'prepare', model='other').status_code == 400


def test_shared_quarantine_cannot_be_bypassed_by_new_evidence_directory(tmp_path):
    from governed_agent_runtime.live_service import LiveService
    shared = tmp_path / 'shared'
    first = LiveService(ROOT, tmp_path / 'one', operation_dir=shared)
    try:
        with pytest.raises(ValueError, match='active coordinator'):
            LiveService(ROOT, tmp_path / 'two', operation_dir=shared)
        first.marker.write_text('{}')
    finally:
        first.close()
    second = LiveService(ROOT, tmp_path / 'two', operation_dir=shared)
    try:
        assert second.status()['availability'] == 'unavailable'
    finally:
        second.close()


def test_failed_preparations_consume_smoke_budget(tmp_path):
    from governed_agent_runtime.live_service import LiveError, LiveService, SimulatedModel
    from tests.contract.test_bc011_live_http import wait_for

    class Failed(SimulatedModel):
        def prepare(self):
            return {'done': True, 'error': 'PROFILE_MISMATCH'}

    service = LiveService(ROOT, tmp_path / 'evidence', provider=Failed(), max_preparations=2)
    try:
        _, session = service.bootstrap()
        for n in range(2):
            with service.condition:
                service.command(session, '/api/sessions', {'command': 'prepare', 'command_id': str(n)})
            wait_for(lambda: service.slot, lambda slot: slot is None)
        assert service.status()['availability'] == 'unavailable'
        assert service.status()['unavailability_reason'] == 'SMOKE_LIMIT'
        with service.condition, pytest.raises(LiveError, match='SMOKE_LIMIT'):
            service.command(session, '/api/sessions', {'command': 'prepare', 'command_id': 'third'})
    finally:
        service.close()


def test_offline_template_cannot_approve_itself(tmp_path, monkeypatch):
    from governed_agent_runtime import live_ollama_http
    path = tmp_path / 'approval.json'
    monkeypatch.setattr('sys.argv', ['local-smoke', '--evidence-dir', str(tmp_path / 'runs'),
                                   '--write-approval-template', str(path)])
    monkeypatch.setattr(LocalOllamaModel, '_json', Mock(side_effect=AssertionError('No network')))
    live_ollama_http.main()
    approval = json.loads(path.read_text())
    assert approval['approved'] is False
    assert approval['exclusive_provider'] is False
    assert approval['no_outstanding_work'] is False
    assert path.stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):
        live_ollama_http.main()


def test_consumed_approval_record_cannot_be_overwritten(tmp_path):
    from governed_agent_runtime.live_ollama import private_json
    path = tmp_path / 'approval-consumed.json'
    private_json(path, {'revision': 'a' * 40})
    with pytest.raises(FileExistsError):
        private_json(path, {'revision': 'b' * 40})
    assert json.loads(path.read_text())['revision'] == 'a' * 40


def test_summary_uses_actual_proposed_count():
    from governed_agent_runtime.live_projection import action_summary
    assert '7' in action_summary('scale_stable', {'desired_replicas': 7})
    assert '8' not in action_summary('scale_stable', {'desired_replicas': 7})
    assert action_summary('unrecognized', {}) == 'Неизвестное действие'
    assert '8' not in action_summary('scale_stable', {})


def test_consumed_approval_is_explained_before_preflight(tmp_path, monkeypatch, capsys):
    from governed_agent_runtime import live_ollama_http
    from governed_agent_runtime.live_ollama import profile_hash

    revision = 'a' * 40
    evidence = tmp_path / 'runs'
    approval = tmp_path / 'approval.json'
    approval_id = 'b' * 32
    approval.write_text(json.dumps({
        'approved': True, 'reviewer': 'Test operator', 'approval_id': approval_id,
        'revision': revision, 'profile_sha256': profile_hash(load_profile(ROOT)),
        'evidence_dir': str(evidence), 'exclusive_provider': True, 'no_outstanding_work': True}))
    state = tmp_path / '.local/state/governed-agent-runtime/ollama-coordinator'
    state.mkdir(parents=True)
    marker = state / f'approval-{approval_id}.json'
    marker.write_text('{}')
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.setattr(live_ollama_http, 'revision', lambda *a, **kw: revision)
    preflight = Mock(side_effect=AssertionError('Preflight must not run'))
    monkeypatch.setattr(live_ollama_http.subprocess, 'run', preflight)
    monkeypatch.setattr('sys.argv', ['local-smoke', '--evidence-dir', str(evidence),
                                   '--approval-file', str(approval)])
    with pytest.raises(SystemExit) as error:
        live_ollama_http.main()
    assert error.value.code == 2
    assert 'Approval already used' in capsys.readouterr().err
    assert marker.read_text() == '{}'
    preflight.assert_not_called()


def test_http_failure_keeps_bounded_private_diagnostics_and_quarantine(tmp_path):
    from io import BytesIO
    from urllib.error import HTTPError

    from governed_agent_runtime.live_service import LiveService

    provider = model(tmp_path)
    provider._verify = Mock(return_value=True)
    body = BytesIO(b'{"error":"invalid format"}' + b' ' * 5000)
    provider.opener.open = Mock(side_effect=HTTPError(
        'http://example.invalid/private', 400, 'private reason',
        {'Authorization': 'private-header'}, body))
    service = LiveService(ROOT, tmp_path / 'service', provider=provider,
                          reconciliation_seconds=0.01)
    try:
        with pytest.raises(TimeoutError):
            service._provider_call(lambda: provider.converse(
                {'messages': []}, evidence_dir=tmp_path / 'dialogue'), 1)
        assert service.quarantined and service.marker.exists()
        record_path = next((tmp_path / 'dialogue').glob('provider-*.json'))
        record = json.loads(record_path.read_text())
        diagnostic = record['failure']
        assert diagnostic['exception_type'] == 'HTTPError'
        assert diagnostic['http_status'] == 400
        assert diagnostic['api_path'] == '/api/chat'
        assert diagnostic['body_truncated'] is True
        assert len(diagnostic['body_excerpt'].encode()) <= 4096
        assert 'invalid format' in diagnostic['body_excerpt']
        assert 'private-header' not in record_path.read_text()
        assert 'example.invalid' not in record_path.read_text()
        assert record_path.stat().st_mode & 0o077 == 0
        assert 'failure' not in service.status()
        assert provider.opener.open.call_count == 1
    finally:
        service.close()


def test_http_error_body_read_failure_preserves_original_exception(tmp_path):
    from urllib.error import HTTPError

    provider = model(tmp_path)
    provider._verify = Mock(return_value=True)
    body = Mock()
    body.read.side_effect = OSError('private path')
    error = HTTPError('http://example.invalid', 500, 'failure', {}, body)
    provider.opener.open = Mock(side_effect=error)
    with pytest.raises(HTTPError) as caught:
        provider.converse({}, evidence_dir=tmp_path / 'dialogue')
    assert caught.value is error
    record = json.loads(next((tmp_path / 'dialogue').glob('provider-*.json')).read_text())
    assert record['failure']['body_read_failed'] is True
    assert record['failure']['body_excerpt'] == ''
    assert 'private path' not in json.dumps(record)
