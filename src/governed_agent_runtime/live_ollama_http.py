"""Explicitly approved, loopback-only station smoke; template creation is offline."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from governed_agent_runtime.live_dialogue import DialogueService
from governed_agent_runtime.live_http import create_app
from governed_agent_runtime.live_ollama import (
    LocalOllamaModel,
    load_profile,
    private_json,
    profile_hash,
    validate_approval,
)


def revision(root, *, clean=False):
    if clean:
        dirty = subprocess.check_output(
            ['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=root, text=True)
        if dirty.strip():
            raise ValueError('Commit or isolate local changes before the approved smoke')
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description='BC-012 local Ollama smoke; explicit approval')
    parser.add_argument('--evidence-dir', type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write-approval-template', type=Path)
    group.add_argument('--approval-file', type=Path)
    parser.add_argument('--input-profile', choices=['preset-only', 'local-free-text'],
                        default='preset-only')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    evidence = args.evidence_dir.resolve()
    approval_path = (args.write_approval_template or args.approval_file).resolve()
    if evidence.is_relative_to(root) or approval_path.is_relative_to(root):
        parser.error('Keep approval and evidence outside the repository')
    profile = load_profile(root)
    if args.write_approval_template:
        private_json(approval_path, {
            'input_profile': args.input_profile, 'approved': False, 'reviewer': '', 'approval_id': uuid4().hex,
            'revision': revision(root), 'profile_sha256': profile_hash(profile),
            'evidence_dir': str(evidence), 'exclusive_provider': False,
            'no_outstanding_work': False})
        print('Unapproved template created. No provider requests were made.')
        return
    approved_revision = revision(root, clean=True)
    approval = json.loads(approval_path.read_text())
    validate_approval(approval, profile, approved_revision, evidence)
    state = Path.home() / '.local/state/governed-agent-runtime/ollama-coordinator'
    consumption = state / f"approval-{approval['approval_id']}.json"
    if consumption.exists():
        parser.error('Approval already used. Preserve evidence and create a new explicitly approved test package.')
    if approval.get('input_profile') != args.input_profile:
        parser.error('Approval must match the server input profile')
    for command in ([sys.executable, '-m', 'ruff', 'check', '.'],
                    [sys.executable, '-m', 'pytest', '-q'], ['git', 'diff', '--check'],
                    ['npm', '--prefix', 'ui', 'test'], ['npm', '--prefix', 'ui', 'run', 'build']):
        subprocess.run(command, cwd=root, check=True)
    if revision(root, clean=True) != approved_revision:
        raise ValueError('Revision changed during preflight')
    # Stable per-local-account state; changing evidence directories cannot bypass quarantine.
    provider = LocalOllamaModel(root, evidence, profile)
    service = DialogueService(root, evidence, provider=provider, operation_dir=state,
                          input_profile=args.input_profile,
                          max_preparations=profile['max_preparations'],
                          startup_metadata={'revision': approved_revision,
                                            'profile_sha256': profile_hash(profile),
                                            'model_config': profile['model_config']})
    try:
        if service.quarantined:
            raise ValueError('Outstanding provider work requires operator reconciliation')
        try:
            private_json(consumption, {
                'revision': approved_revision, 'profile_sha256': profile_hash(profile)})
        except FileExistsError:
            parser.error('Approval already used. Preserve evidence and create a new explicitly approved test package.')
        private_json(evidence / 'startup.json', {
            'approval': approval, 'profile': profile, 'revision': approved_revision})
        import uvicorn
        uvicorn.run(create_app(service), host='127.0.0.1', port=8000, workers=1,
                    proxy_headers=False, access_log=False)
    finally:
        service.close()


if __name__ == '__main__':
    main()
