"""BC-014 local lifecycle checks. No Ollama, system service or real model calls."""
import json
import socket
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from governed_agent_runtime import personal_demo as demo
from governed_agent_runtime.live_dialogue import DialogueService

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('answer', ['yes', 'YES', ' Yes ', 'y', 'Y', 'да', 'ДА'])
def test_confirmation_accepts_case_and_whitespace(monkeypatch, answer):
    monkeypatch.setattr('builtins.input', lambda _: answer)
    assert demo.confirm('Start?')


def test_invalid_input_reprompts_and_blank_cancels(monkeypatch):
    answers = iter(['start', 'typo', ''])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    assert not demo.confirm('Start?')


def test_prepared_build_detects_missing_stale_and_modified_assets(tmp_path):
    (tmp_path / 'ui/dist').mkdir(parents=True)
    (tmp_path / 'ui/source.ts').write_text('source')
    (tmp_path / 'ui/dist/index.html').write_text('built')
    with pytest.raises(ValueError, match='prepare'):
        demo.check_build(tmp_path)
    stamp = tmp_path / 'ui/dist' / demo.STAMP
    stamp.write_text(json.dumps(demo.build_identity(tmp_path)))
    demo.check_build(tmp_path)
    (tmp_path / 'ui/source.ts').write_text('changed')
    with pytest.raises(ValueError, match='prepare'):
        demo.check_build(tmp_path)
    stamp.write_text(json.dumps(demo.build_identity(tmp_path)))
    (tmp_path / 'ui/dist/index.html').write_text('tampered')
    with pytest.raises(ValueError, match='prepare'):
        demo.check_build(tmp_path)


def test_port_conflict_is_actionable(monkeypatch):
    listener = Mock()
    listener.bind.side_effect = OSError('busy')
    monkeypatch.setattr(socket, 'socket', Mock(return_value=listener))
    with pytest.raises(ValueError, match='Порт'):
        demo.check_ports()
    listener.close.assert_called_once()


@pytest.fixture
def service(tmp_path):
    instance = DialogueService(ROOT, tmp_path / 'records', operation_dir=tmp_path / 'coordinator',
                               input_profile='local-free-text', max_preparations=None)
    yield instance
    instance.close()


def mark(service):
    service.marker.write_text('{"status":"outstanding"}')
    service.quarantined = True


def test_shared_lock_prevents_second_demo_or_smoke(service, tmp_path):
    with pytest.raises(ValueError, match='active coordinator'):
        DialogueService(ROOT, tmp_path / 'other', operation_dir=service.operation_dir)


def test_recovery_refusal_never_touches_provider_or_marker(service, monkeypatch):
    mark(service)
    monkeypatch.setattr(demo, 'confirm', lambda _: False)
    command = Mock()
    monkeypatch.setattr(demo.subprocess, 'run', command)
    with pytest.raises(ValueError, match='отменено'):
        demo.recover(service)
    assert service.marker.exists() and service.quarantined
    command.assert_not_called()


def test_recovery_archives_only_after_stop_and_reuses_same_coordinator(service, monkeypatch):
    mark(service)
    original = service.marker.read_bytes()
    monkeypatch.setattr(demo, 'confirm', lambda _: True)
    command = Mock(side_effect=[None, SimpleNamespace(stdout='inactive\n'),
                               SimpleNamespace(returncode=1), None, None])
    monkeypatch.setattr(demo.subprocess, 'run', command)
    demo.recover(service)
    assert not service.marker.exists() and not service.quarantined
    assert next((service.operation_dir / 'reconciled').iterdir()).read_bytes() == original
    assert command.call_args_list[0].args[0] == ['sudo', 'systemctl', 'stop', 'ollama']
    assert service._provider_call(lambda: {'done': True}, 1) == {'done': True}
    assert not service.marker.exists()


@pytest.mark.parametrize('stage', ['stop', 'probe', 'start'])
def test_recovery_failure_preserves_quarantine(service, monkeypatch, stage):
    mark(service)
    monkeypatch.setattr(demo, 'confirm', lambda _: True)
    calls = [None, SimpleNamespace(stdout='inactive\n'), SimpleNamespace(returncode=1), None]
    if stage == 'stop':
        calls[0] = OSError('stop failed')
    elif stage == 'probe':
        calls[2] = SimpleNamespace(returncode=0)
    else:
        calls[3] = OSError('start failed')
    monkeypatch.setattr(demo.subprocess, 'run', Mock(side_effect=calls))
    with pytest.raises((OSError, ValueError)):
        demo.recover(service)
    assert service.marker.exists() and service.quarantined


def test_demo_cleanup_does_not_touch_research_or_symlinks(tmp_path):
    base = tmp_path / 'demo'
    current = base / 'session-current'
    old = base / 'session-old'
    research = tmp_path / 'research'
    for path in (current, old, research):
        path.mkdir(parents=True)
        (path / 'record').write_text('keep')
    (base / 'session-link').symlink_to(research, target_is_directory=True)
    demo.clean_previous(base, current)
    assert not old.exists()
    assert (current / 'record').exists() and (research / 'record').exists()


def test_no_two_preparation_quota_and_existing_dialogue_bounds(service):
    assert service.max_preparations is None
    assert service.input_profile == 'local-free-text'
    assert service.inference_seconds == 300
    assert service.confirmation_seconds == 300


def test_normal_start_has_no_preflight_or_inference(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, 'check_build', lambda root: None)
    monkeypatch.setattr(demo, 'check_ports', lambda: None)
    monkeypatch.setattr(demo, 'confirm', lambda _: True)
    monkeypatch.setattr(demo.LocalOllamaModel, '_verify', lambda self: True)
    forbidden = Mock(side_effect=AssertionError('No process/preload/inference at startup'))
    monkeypatch.setattr(demo.subprocess, 'run', forbidden)
    monkeypatch.setattr(demo.LocalOllamaModel, '_operation', forbidden)
    async def server(service, *args, **kwargs):
        assert service.max_preparations is None
        assert not service.quarantined
    monkeypatch.setattr(demo, 'serve_pair', server)
    demo.run(ROOT, tmp_path / 'demo', tmp_path / 'coordinator')
    assert not list((tmp_path / 'demo').iterdir())
    demo.run(ROOT, tmp_path / 'demo', tmp_path / 'coordinator')
    assert not list((tmp_path / 'demo').iterdir())
    forbidden.assert_not_called()


def test_missing_provider_cleans_session_and_releases_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, 'check_build', lambda root: None)
    monkeypatch.setattr(demo, 'check_ports', lambda: None)
    monkeypatch.setattr(demo, 'confirm', lambda _: True)
    monkeypatch.setattr(demo.LocalOllamaModel, '_verify', Mock(side_effect=OSError('unavailable')))
    with pytest.raises(OSError):
        demo.run(ROOT, tmp_path / 'demo', tmp_path / 'coordinator')
    assert not list((tmp_path / 'demo').iterdir())
    replacement = DialogueService(ROOT, tmp_path / 'new', operation_dir=tmp_path / 'coordinator')
    replacement.close()


def test_install_preserves_original_research_readme_and_launcher(tmp_path, monkeypatch):
    root, home = tmp_path / 'checkout', tmp_path / 'home'
    (root / '.venv/bin').mkdir(parents=True)
    (root / '.venv/bin/python').touch()
    (root / 'docs').mkdir()
    (root / 'docs/personal-demo.md').write_text('Demo instructions')
    command = home / '.local/bin/gar-local'
    command.parent.mkdir(parents=True)
    command.write_text('research launcher')
    folder = home / '.local/gov-agent-local'
    folder.mkdir()
    original = home / 'research-readme'
    original.write_text('Research instructions')
    (folder / 'README.md').symlink_to(original)
    (folder / 'run').symlink_to(command)
    monkeypatch.setattr(demo, 'check_build', lambda root: None)
    demo.install(root, home)
    assert original.read_text() == 'Research instructions'
    assert (folder / 'README.md').read_text() == 'Demo instructions'
    assert 'personal_demo' in command.read_text()
    assert next(command.parent.glob('gar-local-backup-*')).read_text() == 'research launcher'
    assert (folder / 'run').resolve() == command


def test_interrupted_process_restart_retains_uncertainty_until_recovery(tmp_path, monkeypatch):
    import subprocess
    import sys
    coordinator = tmp_path / 'coordinator'
    script = '''
import sys, threading
from pathlib import Path
from governed_agent_runtime.live_dialogue import DialogueService
service = DialogueService(Path(sys.argv[1]), Path(sys.argv[2]), operation_dir=Path(sys.argv[3]))
def pending():
    print('in-flight', flush=True)
    threading.Event().wait(60)
service._provider_call(pending, 60)
'''
    child = subprocess.Popen([sys.executable, '-c', script, str(ROOT),
                              str(tmp_path / 'first'), str(coordinator)], stdout=subprocess.PIPE,
                             text=True)
    try:
        import select
        assert select.select([child.stdout], [], [], 10)[0], 'child did not start'
        assert child.stdout.readline().strip() == 'in-flight'
        with pytest.raises(ValueError, match='active coordinator'):
            DialogueService(ROOT, tmp_path / 'blocked', operation_dir=coordinator)
    finally:
        child.terminate()
        child.wait(timeout=10)
        child.stdout.close()
    replacement = DialogueService(ROOT, tmp_path / 'next', operation_dir=coordinator)
    try:
        assert replacement.quarantined
        monkeypatch.setattr(demo, 'confirm', lambda _: True)
        monkeypatch.setattr(demo.subprocess, 'run', Mock(side_effect=[
            None, SimpleNamespace(stdout='inactive'), SimpleNamespace(returncode=1), None, None]))
        demo.recover(replacement)
        assert replacement._provider_call(lambda: {'done': True}, 1) == {'done': True}
    finally:
        replacement.close()


def test_metadata_startup_retry_does_not_invoke_model(monkeypatch):
    provider = Mock()
    provider._verify.side_effect = [OSError('not listening yet'), True]
    monkeypatch.setattr(demo.time, 'sleep', lambda _: None)
    assert demo.verify_provider(provider, restarted=True)
    assert provider._verify.call_count == 2
    provider.prepare.assert_not_called()
    provider.infer.assert_not_called()


def test_port_probe_allows_reuse_after_connection_close(monkeypatch):
    listener = Mock()
    monkeypatch.setattr(socket, 'socket', Mock(return_value=listener))
    demo.check_ports()
    listener.setsockopt.assert_called_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
