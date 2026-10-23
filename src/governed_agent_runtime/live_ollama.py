"""Pinned local demonstration provider. No public or browser-configurable transport."""
import hashlib
import json
import os
import re
import time
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import uuid4

from governed_agent_runtime.bc006_runtime import SYSTEM, canonical
from governed_agent_runtime.ollama_model_adapter import OllamaChatModel

PROFILE = 'specs/core/live-model-profile.json'
ENDPOINT = 'http://127.0.0.1:11434'
MAX_RESPONSE = 2 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Provider redirects are forbidden')


def private_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('x', encoding='utf-8') as file:
        os.chmod(path, 0o600)
        file.write(canonical(value) + '\n')
        file.flush()
        os.fsync(file.fileno())


def load_profile(root):
    profile = json.loads((Path(root) / PROFILE).read_text())
    if (profile['profile_id'] != 'BC011-local-ollama-v1'
            or profile['fixture'] != 'fixtures/scenarios/bc-006/s12.json'
            or profile['max_preparations'] != 2
            or any(profile[k] != 300 for k in ('preparation_seconds', 'inference_seconds',
                                              'ready_seconds', 'confirmation_seconds'))
            or profile['metadata_seconds'] != 5 or profile['reconciliation_seconds'] != 30):
        raise ValueError('Unsupported local profile')
    return profile


def profile_hash(profile):
    return hashlib.sha256(canonical(profile).encode()).hexdigest()


def validate_approval(approval, profile, revision, evidence):
    if (approval.get('approved') is not True or approval.get('revision') != revision
            or approval.get('profile_sha256') != profile_hash(profile)
            or approval.get('evidence_dir') != str(Path(evidence).resolve())
            or approval.get('exclusive_provider') is not True
            or approval.get('no_outstanding_work') is not True
            or not isinstance(approval.get('reviewer'), str) or not approval['reviewer'].strip()
            or not re.fullmatch('[a-f0-9]{32}', approval.get('approval_id', ''))):
        raise ValueError('Explicit approval must match revision, profile and private evidence')


class LocalOllamaModel:
    serialize = staticmethod(canonical)

    def __init__(self, root, evidence, profile):
        self.profile = deepcopy(profile)
        self.evidence = Path(evidence)
        self.inference_attempts = {}
        config = profile['model_config']
        params = deepcopy(config['invocation_parameters'])
        if params.pop('stream') is not False:
            raise ValueError('Streaming is not permitted')
        self.adapter = OllamaChatModel(
            base_url=ENDPOINT, model_identity=config['model_identity'],
            model_artifact_identity=config['model_artifact_identity'], system_message=SYSTEM,
            model_schema=json.loads((Path(root) / 'schemas/bc006-proposal.schema.json').read_text()),
            request_timeout_seconds=profile['inference_seconds'], **params)
        self.provider_info = {'kind': 'ollama', 'model_name': config['model_identity']}
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def _json(self, path, payload, timeout):
        if path not in {'/api/version', '/api/tags', '/api/generate', '/api/chat'}:
            raise ValueError('Unsupported provider operation')
        request = Request(ENDPOINT + path,
                          data=None if payload is None else canonical(payload).encode(),
                          headers={'Content-Type': 'application/json'},
                          method='GET' if payload is None else 'POST')
        with self.opener.open(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError('Provider response limit exceeded')
        return json.loads(raw)

    def _verify(self):
        config = self.profile['model_config']
        version = self._json('/api/version', None, self.profile['metadata_seconds'])
        if version.get('version') != config['provider']['version']:
            return False
        inventory = self._json('/api/tags', None, self.profile['metadata_seconds'])
        matches = [m for m in inventory.get('models', []) if config['model_identity'] in
                   (m.get('name'), m.get('model'))]
        return len(matches) == 1 and matches[0].get('digest') == config['model_artifact_identity']

    def _operation(self, path, payload, directory, timeout):
        started = time.monotonic()
        record = {'started_at': datetime.now(UTC).isoformat(),
                  'profile_sha256': profile_hash(self.profile), 'request': payload,
                  'model_config': self.profile['model_config']}
        try:
            # Failed metadata checks dispatch no inference and are safe to retry explicitly.
            if not self._verify():
                record['error'] = 'PROFILE_MISMATCH'
                return {'done': True, 'error': 'PROFILE_MISMATCH'}
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError('Provider deadline expired')
            if path == '/api/chat':
                key = str(Path(directory))
                self.inference_attempts[key] = self.inference_attempts.get(key, 0) + 1
            response = self._json(path, payload, remaining)
            record['response'] = response
            if (response.get('done') is not True
                    or response.get('model') != self.adapter.model_identity):
                raise ValueError('Provider completion not established')
            if path == '/api/generate':
                if response.get('response', '') != '':
                    raise ValueError('Unexpected preload output')
                return {'done': True}
            content = response.get('message', {}).get('content')
            # A completed response with invalid content is a known failure, not unknown GPU work.
            if not isinstance(content, str):
                return {'done': True, 'error': 'INVALID_PROVIDER_CONTENT'}
            return {'done': True, 'raw_proposal': content}
        except Exception:
            record['error'] = 'PROVIDER_OPERATION_FAILED'
            raise
        finally:
            record['duration_seconds'] = time.monotonic() - started
            private_json(Path(directory) / f'provider-{uuid4().hex}.json', record)

    def prepare(self):
        payload = {'model': self.adapter.model_identity, 'prompt': '', 'stream': False,
                   'keep_alive': self.adapter.invocation_parameters['keep_alive'],
                   'options': self.adapter._request_options()}
        return self._operation('/api/generate', payload, self.evidence / 'preparations',
                               self.profile['preparation_seconds'])

    def infer(self, context, *, evidence_dir):
        payload = {'model': self.adapter.model_identity,
                   'messages': [{'role': 'system', 'content': SYSTEM},
                                {'role': 'user', 'content': canonical(context)}],
                   'stream': False, 'think': self.adapter.invocation_parameters['think'],
                   'format': self.adapter.model_schema,
                   'keep_alive': self.adapter.invocation_parameters['keep_alive'],
                   'options': self.adapter._request_options()}
        return self._operation('/api/chat', payload, evidence_dir,
                               self.profile['inference_seconds'])
