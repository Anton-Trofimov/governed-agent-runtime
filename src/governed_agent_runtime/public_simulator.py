"""Finite, preset-only synthetic PoC. No provider or host-management switches."""

import argparse
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from starlette.responses import JSONResponse

from governed_agent_runtime.live_dialogue import DialogueService, DialogueSimulator
from governed_agent_runtime.live_http import create_app
from governed_agent_runtime.live_service import LiveError


def https_origin(value):
    parsed = urlsplit(value)
    return (parsed.scheme == 'https' and bool(parsed.hostname) and
            not parsed.username and not parsed.password and
            not parsed.path and not parsed.query and not parsed.fragment and
            value == f'https://{parsed.netloc}')


class PublicSimulator(DialogueService):
    cookie_name = 'gar_public_simulator'

    def __init__(self, root, evidence):
        self.admission_deadline = time.monotonic() + 3600
        super().__init__(root, evidence, provider=DialogueSimulator(), input_profile='preset-only',
                         max_preparations=20, preparation_seconds=30, inference_seconds=30,
                         ready_seconds=120, confirmation_seconds=120)

    def status(self):
        result = super().status()
        if self.monotonic() >= self.admission_deadline:
            result.update(availability='unavailable', unavailability_reason='PUBLIC_PAUSED')
        return result

    def command(self, session, path, body):
        if (body.get('command') == 'prepare' and body.get('command_id') not in session['commands']
                and self.monotonic() >= self.admission_deadline):
            raise LiveError('PUBLIC_PAUSED', 503)
        return super().command(session, path, body)


class Bucket:
    def __init__(self, capacity, per_second):
        self.capacity, self.per_second = capacity, per_second
        self.tokens, self.updated = float(capacity), time.monotonic()

    def take(self):
        current = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (current-self.updated)*self.per_second)
        self.updated = current
        if self.tokens < 1:
            return False
        self.tokens -= 1
        return True


class PublicBoundary:
    """Global constant-memory bounds; forwarded client identity is never trusted."""
    def __init__(self, app, service, origin, site_origin):
        self.app, self.service = app, service
        self.host, self.site_origin = urlsplit(origin).netloc, site_origin
        self.requests = Bucket(120, 30)
        self.bootstraps = Bucket(10, 1/6)
        self.active = 0

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        status, body = 403, {'code': 'ORIGIN_REJECTED'}
        response_headers = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                            'Referrer-Policy': 'no-referrer'}
        if headers.get(b'host', b'').decode() != self.host:
            pass
        elif self.active >= 8 or not self.requests.take():
            status, body = 429, {'code': 'RATE_LIMITED'}
            response_headers['Retry-After'] = '15'
        elif scope['path'] == '/public/status':
            sent = headers.get(b'origin', b'').decode()
            if scope['method'] != 'GET':
                status, body = 405, {'code': 'METHOD_NOT_ALLOWED'}
            elif sent and sent != self.site_origin:
                pass
            else:
                status, body = 200, {'availability': self.service.status()['availability'],
                                    'provider': 'simulator'}
                if sent:
                    response_headers.update({'Access-Control-Allow-Origin': self.site_origin,
                                             'Vary': 'Origin'})
        elif scope['path'] == '/api/session/bootstrap' and not self.bootstraps.take():
            status, body = 429, {'code': 'RATE_LIMITED'}
            response_headers['Retry-After'] = '15'
        elif scope['path'] == '/app-config.json':
            status, body = 200, {'mode': 'live-enabled'}
        else:
            self.active += 1
            try:
                return await self.app(scope, receive, send)
            finally:
                self.active -= 1
        await JSONResponse(body, status_code=status, headers=response_headers)(scope, receive, send)


def create_public_simulator(root, evidence, origin, site_origin):
    if not https_origin(origin) or not https_origin(site_origin):
        raise ValueError('Exact HTTPS origins are required')
    service = PublicSimulator(root, evidence)
    try:
        return PublicBoundary(create_app(service, origin, _public_profile=True), service,
                              origin, site_origin)
    except Exception:
        service.close()
        raise


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description='Bounded public simulator; no LLM or real tools')
    parser.add_argument('--origin', required=True)
    parser.add_argument('--site-origin', required=True)
    parser.add_argument('--port', type=int, default=8002)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if not (root / 'ui/dist/index.html').is_file():
        parser.error('Build the UI first')
    with TemporaryDirectory(prefix='gar-public-simulator-') as evidence:
        app = create_public_simulator(root, evidence, args.origin, args.site_origin)
        uvicorn.run(app, host='127.0.0.1', port=args.port, workers=1, proxy_headers=False,
                    access_log=False, limit_concurrency=16, timeout_keep_alive=5)


if __name__ == '__main__':
    main()
