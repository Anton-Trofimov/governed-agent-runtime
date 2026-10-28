"""Two loopback-only simulator listeners with a shared execution slot."""
import argparse
import asyncio
import json
import os
import signal
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from governed_agent_runtime.live_dialogue import DialogueService
from governed_agent_runtime.live_http import create_app
from governed_agent_runtime.live_ollama import private_json
from governed_agent_runtime.live_service import LiveError


class EntryPoint:
    """Trusted listener binding; never selected by request contents."""

    def __init__(self, service, owner, control):
        self.service = service
        self.owner_control = owner
        self.entry = 'owner' if owner else 'public'
        self.input_profile = 'local-free-text' if owner else 'preset-only'
        self.cookie_name = f'gar_{self.entry}_session'
        self.control = control

    def __getattr__(self, name):
        return getattr(self.service, name)

    @property
    def public_enabled(self):
        return self.control['enabled']

    def set_public_admissions(self, enabled):
        if not self.owner_control or type(enabled) is not bool:
            raise LiveError('NOT_FOUND', 404)
        with self.condition:
            try:
                save_setting(self.control['path'], enabled)
            except OSError:
                raise LiveError('LIVE_UNAVAILABLE', 503) from None
            self.control['enabled'] = enabled

    def bootstrap(self, token=None):
        if token:
            try:
                self.authenticate(token)
            except LiveError:
                token = None
        token, session = self.service.bootstrap(token)
        session['_entry'] = self.entry
        session['_input_profile'] = self.input_profile
        return token, session

    def authenticate(self, token):
        session = self.service.authenticate(token)
        if session.get('_entry') != self.entry:
            raise LiveError('SESSION_REQUIRED', 401)
        return session

    def status(self):
        result = self.service.status()
        if self.owner_control:
            result['public_admissions_enabled'] = self.public_enabled
        elif not self.public_enabled and result['availability'] == 'available':
            result.update(availability='unavailable', unavailability_reason='PUBLIC_PAUSED')
        return result

    def session_view(self, session):
        result = self.service.session_view(session)
        if self.owner_control:
            result['public_admissions_enabled'] = self.public_enabled
        return result

    def command(self, session, path, body):
        if session.get('_entry') != self.entry:
            raise LiveError('SESSION_REQUIRED', 401)
        if (not self.owner_control and not self.public_enabled
                and body.get('command') == 'prepare'
                and body.get('command_id') not in session['commands']):
            raise LiveError('PUBLIC_PAUSED', 503)
        return self.service.command(session, path, body)

    def close(self):
        # The paired runner owns shutdown; one app must not close the shared provider.
        pass


def save_setting(path, enabled):
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    try:
        private_json(temporary, {'enabled': enabled})
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def paired_apps(service, public_origin, owner_origin, settings_path=None):
    if urlsplit(public_origin).port == urlsplit(owner_origin).port:
        raise ValueError('Entry points require distinct listener ports')
    path = Path(settings_path) if settings_path is not None else service.evidence / 'admissions.json'
    try:
        saved = json.loads(path.read_text())
    except FileNotFoundError:
        saved = {'enabled': True}
        save_setting(path, True)
    if not isinstance(saved, dict) or set(saved) != {'enabled'} or type(saved['enabled']) is not bool:
        raise ValueError('Invalid saved admission setting')
    control = {**saved, 'path': path}
    return (create_app(EntryPoint(service, False, control), public_origin),
            create_app(EntryPoint(service, True, control), owner_origin))


async def serve_pair(service, public_port, owner_port, settings_path=None, *, close_service=True):
    import uvicorn

    class PairedServer(uvicorn.Server):
        @contextmanager
        def capture_signals(self):
            # One process-level handler owns both listeners and provider cleanup.
            yield

    try:
        apps = paired_apps(service, f'http://127.0.0.1:{public_port}',
                           f'http://127.0.0.1:{owner_port}', settings_path=settings_path)
    except Exception:
        if close_service:
            service.close()
        raise
    servers = [PairedServer(uvicorn.Config(app, host='127.0.0.1', port=port,
                workers=1, proxy_headers=False, access_log=False))
               for app, port in zip(apps, (public_port, owner_port), strict=True)]
    def stop(signum, frame):
        for server in servers:
            server.should_exit = True

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    tasks = [asyncio.create_task(server.serve()) for server in servers]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        for server in servers:
            server.should_exit = True
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            if close_service:
                service.close()
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


def main():
    parser = argparse.ArgumentParser(description='Paired loopback simulator; no real LLM calls')
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--public-port', type=int, default=8000)
    parser.add_argument('--owner-port', type=int, default=8001)
    parser.add_argument('--settings-file', type=Path,
                        default=Path.home() / '.local/state/gar-ui-simulator/admissions.json')
    args = parser.parse_args()
    if (args.public_port == args.owner_port or
            any(port < 1024 or port > 65535 for port in (args.public_port, args.owner_port))):
        parser.error('Choose two distinct unprivileged ports')
    root = Path(__file__).resolve().parents[2]
    if args.evidence_dir.resolve().is_relative_to(root):
        parser.error('Keep evidence outside the repository')
    if args.settings_file.resolve().is_relative_to(root):
        parser.error('Keep settings outside the repository')
    service = DialogueService(root, args.evidence_dir)
    print('Paired simulator: restoring public admission setting (first startup: enabled).')
    asyncio.run(serve_pair(service, args.public_port, args.owner_port, args.settings_file))


if __name__ == '__main__':
    main()
