"""Local personal showing; research approvals and recorded publication stay separate."""
import argparse
import asyncio
import hashlib
import json
import os
import shlex
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from governed_agent_runtime.live_dialogue import DialogueService
from governed_agent_runtime.live_dual_http import serve_pair
from governed_agent_runtime.live_ollama import LocalOllamaModel, load_profile

STAMP = '.personal-demo-build.json'


def confirm(message):
    while True:
        try:
            answer = input(message + ' [yes/no; Enter — no] ').strip().casefold()
        except (EOFError, KeyboardInterrupt):
            return False
        if answer in {'y', 'yes', 'да'}:
            return True
        if answer in {'', 'n', 'no', 'нет'}:
            return False
        print('Введите yes/да или no/нет (регистр не важен).')


def tree_digest(directory, *, excluded=()):
    digest = hashlib.sha256()
    for path in sorted(directory.rglob('*')):
        relative = path.relative_to(directory)
        if any(part in excluded for part in relative.parts) or not path.is_file():
            continue
        digest.update(relative.as_posix().encode() + b'\0')
        digest.update(path.read_bytes())
    return digest.hexdigest()


def build_identity(root):
    ui = root / 'ui'
    return {'source': tree_digest(ui, excluded=('node_modules', 'dist')),
            'output': tree_digest(ui / 'dist', excluded=(STAMP,))}


def prepare(root):
    subprocess.run(['npm', '--prefix', str(root / 'ui'), 'ci'], check=True)
    subprocess.run(['npm', '--prefix', str(root / 'ui'), 'run', 'build'], check=True)
    (root / 'ui/dist' / STAMP).write_text(json.dumps(build_identity(root)))
    print('UI подготовлен. Запуск: python -m governed_agent_runtime.personal_demo')


def check_build(root):
    try:
        saved = json.loads((root / 'ui/dist' / STAMP).read_text())
        valid = saved == build_identity(root) and (root / 'ui/dist/index.html').is_file()
    except (OSError, ValueError):
        valid = False
    if not valid:
        raise ValueError('UI не подготовлен или изменился. Выполните: '
                         'python -m governed_agent_runtime.personal_demo --prepare')


def check_ports():
    sockets = []
    try:
        for port in (8000, 8001):
            listener = socket.socket()
            sockets.append(listener)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('127.0.0.1', port))
    except OSError as error:
        raise ValueError('Порт 8000 или 8001 занят. Остановите предыдущий сервер '
                         'или другое приложение на этом порту.') from error
    finally:
        for listener in sockets:
            listener.close()


def recover(service):
    """Called only after acquiring the shared coordinator lock."""
    if not service.quarantined:
        return
    if not confirm('Предыдущий запрос не завершён достоверно. Перезапустить Ollama? '
                   'Это прервёт запросы WebUI и других клиентов'):
        raise ValueError('Восстановление отменено. Старый запрос не повторяется.')
    subprocess.run(['sudo', 'systemctl', 'stop', 'ollama'], check=True)
    status = subprocess.run(['systemctl', 'is-active', 'ollama'], capture_output=True, text=True, check=False)
    processes = subprocess.run(['pgrep', '-x', 'ollama'], capture_output=True, check=False)
    if status.stdout.strip() != 'inactive' or processes.returncode != 1:
        raise ValueError('Остановка Ollama не подтверждена. Маркер сохранён; запуск отменён.')
    archive = service.operation_dir / 'reconciled'
    archive.mkdir(mode=0o700, exist_ok=True)
    destination = archive / f'personal-{uuid4().hex}.json'
    os.replace(service.marker, destination)
    try:
        subprocess.run(['sudo', 'systemctl', 'start', 'ollama'], check=True)
        subprocess.run(['systemctl', 'is-active', '--quiet', 'ollama'], check=True)
    except BaseException:
        # Preserve fail-closed recovery state if restart did not finish.
        os.replace(destination, service.marker)
        raise
    service.quarantined = False
    print('Ollama перезапущена. Прежний сценарий не возобновляется.')


def clean_previous(base, current):
    """Only this launcher's private namespace; caller owns shared service lock."""
    for path in base.glob('session-*'):
        if path != current and path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)


def verify_provider(provider, *, restarted=False):
    # systemctl active can precede the HTTP listener; retry metadata only.
    for attempt in range(5 if restarted else 1):
        try:
            return provider._verify()
        except OSError:
            if not restarted or attempt == 4:
                raise
            time.sleep(0.25)


def run(root, base, coordinator):
    check_build(root)
    check_ports()
    if not confirm('Запустить личную демонстрацию? '
                   'Убедитесь, что WebUI и другие клиенты не отправляют запросы к Ollama'):
        print('Запуск отменён.')
        return
    base.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(base, 0o700)
    session = Path(tempfile.mkdtemp(prefix='session-', dir=base))
    service = None
    try:
        profile = load_profile(root)
        provider = LocalOllamaModel(root, session, profile)
        service = DialogueService(root, session, provider=provider, operation_dir=coordinator,
                                  input_profile='local-free-text', max_preparations=None,
                                  startup_metadata={'purpose': 'personal-demo-not-evaluation'})
        restarted = service.quarantined
        recover(service)
        clean_previous(base, session)
        if not verify_provider(provider, restarted=restarted):
            raise ValueError('Версия Ollama или модель не соответствует профилю проекта. '
                             'Автоматическая замена модели не выполняется.')
        print('Личный вход: http://127.0.0.1:8001\n'
              'Посетительский вход: http://127.0.0.1:8000\n'
              'Остановка: Ctrl+C. Временные результаты не являются evidence эксперимента.',
              flush=True)
        asyncio.run(serve_pair(service, 8000, 8001,
                    settings_path=coordinator.parent / 'public-admissions.json', close_service=False))
    finally:
        if service is not None:
            service.close()
        if service is None or not any(thread.is_alive() for thread in service.threads):
            shutil.rmtree(session)
        else:
            print('Прерывание обращения к модели: при следующем запуске может '
                  'потребоваться подтверждение перезапуска Ollama.')


def install(root, home):
    """Install the local shortcut without moving research records or their README."""
    check_build(root)
    python = root / '.venv/bin/python'
    if not python.is_file():
        raise ValueError('Создайте .venv в корне checkout и установите зависимости проекта.')
    command = home / '.local/bin/gar-local'
    folder = home / '.local/gov-agent-local'
    command.parent.mkdir(parents=True, exist_ok=True)
    folder.mkdir(parents=True, exist_ok=True)
    wrapper = ('#!/usr/bin/env bash\nset -euo pipefail\n'
               f'cd {shlex.quote(str(root))}\n'
               f'exec {shlex.quote(str(python))} -m governed_agent_runtime.personal_demo "$@"\n')
    if command.exists() and command.read_text() != wrapper:
        backup = command.with_name('gar-local-backup-' + uuid4().hex)
        shutil.copy2(command, backup)
        print(f'Предыдущая команда сохранена: {backup}')
    command.write_text(wrapper)
    command.chmod(0o700)
    shortcut = folder / 'run'
    if shortcut.is_symlink():
        shortcut.unlink()
    elif shortcut.exists():
        raise ValueError('run уже существует и не является ссылкой; файл не заменён.')
    shortcut.symlink_to(command)
    readme = folder / 'README.md'
    if readme.is_symlink():
        readme.unlink()  # Keep the research README at its original location.
    elif readme.exists():
        shutil.copy2(readme, folder / ('README-backup-' + uuid4().hex + '.md'))
    instructions = (root / 'docs/personal-demo.md').read_text()
    instructions = instructions.replace(
        '.venv/bin/python -m governed_agent_runtime.personal_demo',
        '~/.local/gov-agent-local/run')
    readme.write_text(instructions)
    print('Установлено: ~/.local/gov-agent-local/run')


def main():
    parser = argparse.ArgumentParser(description='Личный показ: одна команда и подтверждение')
    parser.add_argument('--install', action='store_true', help='Установить локальную команду и README')
    parser.add_argument('--prepare', action='store_true', help='Один раз собрать UI после обновления')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        if args.install and args.prepare:
            parser.error('Выберите --prepare или --install')
        if args.prepare:
            prepare(root)
        elif args.install:
            install(root, Path.home())
        else:
            run(root, Path.home() / '.local/state/gar-personal-demo',
                Path.home() / '.local/state/governed-agent-runtime/ollama-coordinator')
    except KeyboardInterrupt:
        print('\nОстановлено.')
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Запуск не выполнен: {error}\n')


if __name__ == '__main__':
    main()
