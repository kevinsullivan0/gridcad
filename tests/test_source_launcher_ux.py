"""Consent, visible diagnostics and real child-process launcher regressions."""
from contextlib import redirect_stdout
import importlib.util
import io
import locale
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


HELPER = Path(__file__).resolve().parents[1] / 'tools/source_launcher.py'


def load_launcher():
    spec = importlib.util.spec_from_file_location('launcher_ux', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LauncherConsentTests(unittest.TestCase):
    def test_decline_or_unavailable_input_preserves_existing_setup(self):
        # Asking after unlink/rename would destroy the user's ready/partial state.
        for answer in ('N', '', 'yes', EOFError(), KeyboardInterrupt()):
            with self.subTest(answer=type(answer).__name__ if isinstance(answer, BaseException) else answer):
                m = load_launcher()
                with tempfile.TemporaryDirectory() as td:
                    base = Path(td)
                    env = base / 'runtime'
                    env.mkdir()
                    (env / 'keep.txt').write_text('original', encoding='utf-8')
                    marker = base / 'ready.json'
                    marker.write_text('original readiness', encoding='utf-8')
                    prompt = {'side_effect': answer} if isinstance(answer, BaseException) else {'return_value': answer}
                    with patch('builtins.input', **prompt), redirect_stdout(io.StringIO()), \
                            patch.object(m, 'create_environment', side_effect=RuntimeError('installation reached without approval')):
                        with self.assertRaisesRegex(RuntimeError, 'canceled'):
                            m.ensure_environment(base)
                    self.assertEqual(marker.read_text(), 'original readiness')
                    self.assertEqual((env / 'keep.txt').read_text(), 'original')
                    self.assertEqual({p.name for p in base.iterdir()}, {'runtime', 'ready.json'})

    def test_first_setup_accepts_explicit_y_and_then_repeats_offline_without_prompt(self):
        m = load_launcher()
        with tempfile.TemporaryDirectory(prefix='GridCAD espace é ') as td:
            base = Path(td)
            with patch('builtins.input', return_value=' y '), redirect_stdout(io.StringIO()), \
                    patch.object(m, 'create_environment', side_effect=lambda p: p.mkdir()), \
                    patch.object(m, 'probe_environment', return_value=True):
                env = m.ensure_environment(base)
            marker = base / 'ready.json'
            before = marker.read_bytes(), marker.stat().st_mtime_ns
            with patch('builtins.input', side_effect=AssertionError('repeat must not prompt')), \
                    patch.object(m, 'create_environment', side_effect=AssertionError('repeat must not install')), \
                    patch.object(m, 'probe_environment', return_value=True), redirect_stdout(io.StringIO()):
                self.assertEqual(m.ensure_environment(base), env)
            self.assertEqual((marker.read_bytes(), marker.stat().st_mtime_ns), before)

    def test_batch_approval_does_not_prompt_again(self):
        m = load_launcher()
        with tempfile.TemporaryDirectory() as td:
            with patch('builtins.input', side_effect=AssertionError('already approved')), \
                    patch.object(m, 'create_environment', side_effect=lambda p: p.mkdir()), \
                    patch.object(m, 'probe_environment', return_value=True), redirect_stdout(io.StringIO()):
                env = m.ensure_environment(Path(td), setup_approved=True)
            self.assertTrue(env.is_dir())
            self.assertTrue((Path(td) / 'ready.json').is_file())

    def test_setup_lock_refuses_concurrent_access_and_releases_after_error(self):
        m = load_launcher()
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            with self.assertRaisesRegex(ValueError, 'interrupted'):
                with m.setup_lock(base):
                    with self.assertRaisesRegex(RuntimeError, 'Another GridCAD setup'):
                        with m.setup_lock(base):
                            self.fail('concurrent setup must not be admitted')
                    raise ValueError('interrupted')
            with m.setup_lock(base):
                self.assertTrue((base / 'setup.lock').is_file())

    def test_readiness_temporary_link_cannot_modify_an_unrelated_file(self):
        m = load_launcher()
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / 'state'
            base.mkdir()
            other = Path(td) / 'other.txt'
            other.write_text('keep', encoding='utf-8')
            try:
                (base / 'ready.tmp').symlink_to(other)
            except OSError:
                self.skipTest('This account cannot create symbolic links')
            with patch('builtins.input', return_value='Y'), \
                    patch.object(m, 'create_environment', side_effect=lambda p: p.mkdir()), \
                    patch.object(m, 'probe_environment', return_value=True), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'link'):
                    m.ensure_environment(base)
            self.assertEqual(other.read_text(), 'keep')
            self.assertFalse((base / 'runtime').exists())


class LauncherProcessTests(unittest.TestCase):
    def run_package_fixture(self, folder, child_code):
        # Replace the external installer, retaining real subprocess output/error
        # semantics. No wheels, network or native runtime are used by this test.
        harness = """
import importlib.util, pathlib, subprocess, sys
s=importlib.util.spec_from_file_location('launcher', sys.argv[1])
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Builder:
    def __init__(self, **kwargs): pass
    def create(self, folder): folder.mkdir()
m.venv.EnvBuilder=Builder
real_run=subprocess.run
def install(command, **kwargs):
    required=['--isolated','--no-index','--no-deps','--only-binary=:all:','--require-hashes']
    assert all(flag in command for flag in required)
    requirement=pathlib.Path(command[command.index('-r')+1]).read_text()
    assert 'Pillow @ https://files.pythonhosted.org/' in requirement
    assert '--hash=sha256:9dda0788a9932776a75d8bcc020076edc308ce2508b51f6739a45e3158b3fc42' in requirement
    return real_run([sys.executable,'-c',sys.argv[3]], **kwargs)
m.subprocess.run=install
try: m.create_environment(pathlib.Path(sys.argv[2]))
except (RuntimeError, subprocess.SubprocessError) as exc:
    print(str(exc));raise SystemExit(1)
"""
        return subprocess.run([sys.executable, '-c', harness, str(HELPER), str(folder), child_code],
                              capture_output=True, text=True, timeout=15)

    def test_successful_package_setup_shows_progress_without_pip_chatter(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / 'runtime'
            result = self.run_package_fixture(folder, "print('PACKAGE-NOISE')")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('Pillow', result.stdout)
            self.assertNotIn('PACKAGE-NOISE', result.stdout + result.stderr)
            self.assertFalse((folder / 'gridcad-requirements.txt').exists())

    def test_package_failure_preserves_complete_diagnostic_output(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / 'runtime'
            result = self.run_package_fixture(folder,
                "import sys;print('network diagnostic');print('checksum diagnostic',file=sys.stderr);sys.exit(7)")
            self.assertEqual(result.returncode, 1)
            self.assertIn('network diagnostic', result.stdout + result.stderr)
            self.assertIn('checksum diagnostic', result.stdout + result.stderr)
            self.assertIn('try again', result.stdout)
            self.assertFalse((folder / 'gridcad-requirements.txt').exists())

    def test_package_timeout_preserves_partial_bytes_and_removes_setup_file(self):
        m = load_launcher()
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / 'runtime'
            def create(path): path.mkdir()
            captured = io.StringIO()
            with patch.object(m.venv.EnvBuilder, 'create', side_effect=create), \
                    patch.object(m.subprocess, 'run', side_effect=subprocess.TimeoutExpired('pip', 600, output=b'partial download diagnostic\n')), \
                    redirect_stdout(captured):
                with self.assertRaisesRegex(RuntimeError, 'try again'):
                    m.create_environment(folder)
            self.assertIn('partial download diagnostic', captured.getvalue())
            self.assertFalse((folder / 'gridcad-requirements.txt').exists())

    def test_package_diagnostics_preserve_windows_filenames_and_unknown_bytes(self):
        for encoding, diagnostic, expected in (
                ('cp1252', b'Path: Andr\xe9\n', 'Path: André'),
                ('utf-8', b'Unknown diagnostic: \xff\n', r'Unknown diagnostic: \xff')):
            with self.subTest(encoding=encoding), tempfile.TemporaryDirectory() as td:
                m = load_launcher()
                output = io.StringIO()
                with patch.object(m.venv.EnvBuilder, 'create', side_effect=lambda p: p.mkdir()), \
                        patch.object(m.subprocess, 'run', side_effect=subprocess.TimeoutExpired('pip', 600, output=diagnostic)), \
                        patch.object(locale, 'getencoding', return_value=encoding), redirect_stdout(output):
                    with self.assertRaisesRegex(RuntimeError, 'try again'):
                        m.create_environment(Path(td) / 'runtime')
                self.assertIn(expected, output.getvalue())

    def test_actual_gui_child_uses_app_directory_waits_and_preserves_errors(self):
        # Bypass only Windows setup discovery. main still invokes an actual Python
        # child with its normal argument list, cwd and inherited diagnostic stream.
        harness = """
import importlib.util, os, pathlib, sys, types
s=importlib.util.spec_from_file_location('launcher', sys.argv[1])
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
app=pathlib.Path(sys.argv[2]);interpreter=pathlib.Path(sys.executable)
approved=sys.argv[3]=='yes'
m.__file__=str(app/'tools/source_launcher.py')
m.os=types.SimpleNamespace(name='nt',environ={'LOCALAPPDATA':str(app/'local data')})
m.sys.version_info=(3,13,16)
from contextlib import nullcontext
m.setup_lock=lambda base:nullcontext()
def ensure(base, *, setup_approved=False):
    assert setup_approved == approved
    return app/'runtime'
m.ensure_environment=ensure
m.environment_python=lambda env:interpreter
sys.argv=[str(app/'tools/source_launcher.py')]+(['--setup-approved'] if approved else [])
raise SystemExit(m.main())
"""
        for status in (0, 7):
            with self.subTest(status=status), tempfile.TemporaryDirectory(prefix='GridCAD spaces é 漢 ') as td:
                app = Path(td)
                for name in ('desktop_core.py', 'diagnostics.py', 'agent_help.py',
                             'resources/gridcad.png', 'operator/gridcad_operator/operator.py'):
                    target = app / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.touch()
                (app / 'gridcad_desktop.py').write_text(
                    "from pathlib import Path\nimport sys,time\n"
                    "assert len(sys.argv)==1\n"
                    "print('GUI diagnostic',file=sys.stderr,flush=True)\n"
                    "time.sleep(.1)\nPath('child completed.txt').write_text('done')\n"
                    f"raise SystemExit({status})\n", encoding='utf-8')
                result = subprocess.run([sys.executable, '-c', harness, str(HELPER), str(app), 'yes' if status else 'no'],
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, status, result.stderr + result.stdout)
                self.assertEqual((app / 'child completed.txt').read_text(), 'done')
                self.assertIn('GUI diagnostic', result.stderr)
                if status:
                    self.assertIn('closed unexpectedly', result.stdout)


if __name__ == '__main__':
    unittest.main()
