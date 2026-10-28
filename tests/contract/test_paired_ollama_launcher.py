"""Approval/topology wiring checks, with no provider/network calls."""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from governed_agent_runtime import live_ollama_http as launcher
from governed_agent_runtime.live_ollama import LocalOllamaModel


def template(tmp_path, monkeypatch, paired=True):
    path = tmp_path / 'approval.json'
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.setattr(launcher, 'revision', lambda *a, **kw: 'a' * 40)
    args = ['smoke', '--evidence-dir', str(tmp_path / 'runs'), '--write-approval-template', str(path)]
    monkeypatch.setattr('sys.argv', args + (['--paired'] if paired else []))
    monkeypatch.setattr(LocalOllamaModel, '_json', Mock(side_effect=AssertionError('No network')))
    launcher.main()
    return path, args[:3]


def approve(path):
    data = json.loads(path.read_text())
    data.update(approved=True, reviewer='Test operator', exclusive_provider=True, no_outstanding_work=True)
    path.write_text(json.dumps(data))


def test_paired_template_is_offline_and_binds_both_profiles(tmp_path, monkeypatch):
    path, _ = template(tmp_path, monkeypatch)
    data = json.loads(path.read_text())
    assert data['approved'] is False
    assert data['entrypoints'] == {'public': {'port':8000, 'profile':'preset-only'},
                                  'owner': {'port':8001, 'profile':'local-free-text'}}
    LocalOllamaModel._json.assert_not_called()


@pytest.mark.parametrize('template_paired', [True, False])
def test_topology_mismatch_rejected_before_preflight(tmp_path, monkeypatch, template_paired):
    path, args = template(tmp_path, monkeypatch, paired=template_paired)
    approve(path)
    preflight = Mock(side_effect=AssertionError('No preflight'))
    monkeypatch.setattr(launcher.subprocess, 'run', preflight)
    monkeypatch.setattr('sys.argv', args + ['--approval-file', str(path)] + ([] if template_paired else ['--paired']))
    with pytest.raises(SystemExit):
        launcher.main()
    preflight.assert_not_called()
    LocalOllamaModel._json.assert_not_called()
