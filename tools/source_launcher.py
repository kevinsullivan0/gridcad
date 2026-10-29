"""Set up once and run the existing GridCAD GUI with official Python.

Invoked by Start GridCAD.bat after publisher validation. Never changes Windows
security policy, app files, PATH, file associations, or the user's inputs.
"""
from contextlib import contextmanager
import argparse
import json
import locale
import os
from pathlib import Path
import struct
import subprocess
import sys
import uuid
import venv

PILLOW_VERSION = '13.0.0'
PILLOW_WHEEL = 'https://files.pythonhosted.org/packages/d7/ed/1b16fb66a37e1b9e41370b93b2c614c7da761a5b2a41dc333f7af4639962/pillow-13.0.0-cp313-cp313-win_amd64.whl'
PILLOW_SHA256 = '9dda0788a9932776a75d8bcc020076edc308ce2508b51f6739a45e3158b3fc42'


class SetupCancelled(RuntimeError):
    """No installation was approved; leave any existing setup untouched."""


def say(message):
    print(message, flush=True)


def validate_app(folder):
    for name in ('gridcad_desktop.py', 'desktop_core.py', 'diagnostics.py',
                 'agent_help.py', 'resources/gridcad.png',
                 'operator/gridcad_operator/operator.py'):
        if not (folder / name).is_file():
            raise RuntimeError('Keep the launcher inside the complete extracted GridCAD folder. Missing: ' + name)


def ready_record():
    return json.dumps({'python': str(Path(sys.executable).resolve()),
                       'version': list(sys.version_info[:3]),
                       'pillow': PILLOW_VERSION, 'wheel_sha256': PILLOW_SHA256}, sort_keys=True)


def environment_python(folder):
    return folder / 'Scripts' / 'python.exe'


def probe_environment(folder):
    executable = environment_python(folder)
    if not executable.is_file() or executable.is_symlink():
        return False
    code = ("import sys, pathlib, tkinter, PIL; from PIL import Image, ImageTk; "
            "assert PIL.__version__ == '13.0.0'; "
            "assert pathlib.Path(PIL.__file__).resolve().is_relative_to(pathlib.Path(sys.prefix).resolve()); "
            "assert sys.version_info[:2] == (3,13); "
            "Image.new('RGB',(1,1)).tobytes(); root=tkinter.Tk(); root.withdraw(); root.update_idletasks(); root.destroy()")
    try:
        result = subprocess.run([str(executable), '-I', '-c', code],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def create_environment(folder):
    requirement = folder / 'gridcad-requirements.txt'
    try:
        say('Step 1 of 3: preparing your private GridCAD environment...')
        venv.EnvBuilder(with_pip=True).create(folder)
        requirement.write_text(f'Pillow @ {PILLOW_WHEEL} --hash=sha256:{PILLOW_SHA256}\n', encoding='ascii')
        say('Step 2 of 3: downloading and verifying Pillow. This may take a few minutes...')
        command = [str(environment_python(folder)), '-I', '-m', 'pip', '--isolated', 'install',
                   '--disable-pip-version-check', '--no-input', '--no-index', '--no-deps',
                   '--only-binary=:all:', '--require-hashes', '--timeout', '30', '--retries', '1',
                   '-r', str(requirement)]
        subprocess.run(command, check=True, timeout=600,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        if exc.output:
            say(exc.output.decode(locale.getencoding(), errors='backslashreplace')
                if isinstance(exc.output, bytes) else exc.output)
        reason = ('timed out' if isinstance(exc, subprocess.TimeoutExpired)
                  else f'failed with code {exc.returncode}')
        raise RuntimeError(f'GridCAD environment setup {reason}. Check the details above, then try again.') from exc
    finally:
        requirement.unlink(missing_ok=True)


def ensure_environment(base, *, setup_approved=False):
    base.mkdir(parents=True, exist_ok=True)
    env = base / 'runtime'
    marker = base / 'ready.json'
    temporary = base / 'ready.tmp'
    if env.is_symlink() or marker.is_symlink() or temporary.is_symlink():
        raise RuntimeError('GridCAD setup paths must be ordinary local files, not links.')
    try:
        ready = marker.read_text(encoding='utf-8') == ready_record()
    except (OSError, UnicodeError):
        ready = False
    if ready and probe_environment(env):
        say('GridCAD is ready. No downloads or installation needed.')
        return env
    if not setup_approved:
        say('GridCAD needs to set up or repair its private image-library environment.')
        say('This installs the verified Pillow library for GridCAD in your account. Internet is needed.')
        say('Your app and input files are kept unchanged. No administrator rights or Windows settings changes are needed.')
        try:
            setup_approved = input('Set up GridCAD now? Type Y to continue, or press Enter to cancel: ').strip().lower() == 'y'
        except (EOFError, KeyboardInterrupt):
            setup_approved = False
        if not setup_approved:
            raise SetupCancelled('Setup canceled. Your existing environment was kept unchanged.')
    marker.unlink(missing_ok=True)
    if env.exists():
        # Never delete a partial directory that might contain user-added files.
        previous = base / ('incomplete-' + uuid.uuid4().hex)
        env.rename(previous)
        say('An incomplete setup was preserved. Preparing a fresh environment...')
    create_environment(env)
    say('Step 3 of 3: checking Python, Tk and Pillow...')
    if not probe_environment(env):
        raise RuntimeError('Could not verify Python, Tk and Pillow. Windows may have blocked a component; check the displayed warning.')
    temporary.write_text(ready_record(), encoding='utf-8')
    temporary.replace(marker)
    return env


@contextmanager
def setup_lock(base):
    """The OS releases this lock if setup is interrupted or the window closes."""
    base.mkdir(parents=True, exist_ok=True)
    path = base / 'setup.lock'
    if path.is_symlink():
        raise RuntimeError('The setup lock must not be a link.')
    with path.open('a+b') as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('Another GridCAD setup is running. Let it finish, then double-click again.') from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def main():
    parser = argparse.ArgumentParser(description='Set up and open the included GridCAD source interface.')
    parser.add_argument('--setup-approved', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    app = Path(__file__).resolve().parents[1]
    validate_app(app)
    if os.name != 'nt' or sys.version_info[:2] != (3, 13) or struct.calcsize('P') != 8:
        raise RuntimeError('This launcher needs official Windows x64 Python 3.13.')
    local = os.environ.get('LOCALAPPDATA')
    if not local or not Path(local).is_absolute():
        raise RuntimeError('Windows did not provide a valid per-user application-data folder.')
    base = Path(local) / 'GridCAD' / 'SourceLauncher'
    if base.is_symlink():
        raise RuntimeError('The GridCAD setup folder must not be a link.')
    with setup_lock(base):
        env = ensure_environment(base, setup_approved=args.setup_approved)
    say('Opening GridCAD. Keep this window open while you use the app.')
    command=[str(environment_python(env)), '-E', '-s', str(app / 'gridcad_desktop.py')]
    ready=os.environ.get('GRIDCAD_LAUNCH_READY_FILE')
    token=os.environ.get('GRIDCAD_LAUNCH_TOKEN')
    if ready and token:
        command.extend(['--launch-ready',ready,'--launch-token',token])
    result = subprocess.call(command, cwd=app)
    if result:
        say(f'\nGridCAD closed unexpectedly (code {result}). Keep the details above for troubleshooting, then try again.')
    return result


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SetupCancelled as exc:
        say(str(exc))
        raise SystemExit(2)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        say('\nGridCAD could not start: ' + str(exc))
        say('For setup/download errors, check your connection and try again. A completed setup works offline.')
        say('If Windows reports a security block, keep protections enabled and report the blocked file name.')
        raise SystemExit(1)
