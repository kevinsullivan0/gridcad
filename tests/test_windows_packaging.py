"""Static shared-runtime collision checks; not Windows executable acceptance."""
import ast
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import warnings
import zipfile


SPEC = Path(__file__).resolve().parents[1] / 'tools/GridCAD.spec'


class SharedRuntimeFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'base_library.zip'
        # Execute the actual spec helpers, without requiring PyInstaller or
        # creating executables on a non-Windows test host.
        tree = ast.parse(SPEC.read_text(encoding='utf-8'))
        helpers = ast.Module(body=[node for node in tree.body
                                   if isinstance(node, ast.FunctionDef)], type_ignores=[])
        self.namespace = dict(Path=Path, hashlib=hashlib, zipfile=zipfile, collected={})
        exec(compile(helpers, str(SPEC), 'exec'), self.namespace)
        self.check = self.namespace['check_shared_files']

    def archive(self, members, *, date=(2020, 1, 1, 0, 0, 0), compression=zipfile.ZIP_STORED):
        with zipfile.ZipFile(self.source, 'w') as archive:
            for name, content in members:
                info = zipfile.ZipInfo(name, date_time=date)
                info.compress_type = compression
                archive.writestr(info, content)

    def check_archive(self):
        self.check(SimpleNamespace(binaries=[], datas=[('base_library.zip', str(self.source), 'DATA')]))

    def baseline(self):
        self.archive([('encodings/__init__.pyc', b'encodings'), ('abc.pyc', b'abc')])
        self.check_archive()

    def test_reordered_members_and_changed_metadata_are_equivalent(self):
        self.baseline()
        before = self.source.read_bytes()
        self.archive([('abc.pyc', b'abc'), ('encodings/__init__.pyc', b'encodings')],
                     date=(2026, 2, 3, 4, 5, 6), compression=zipfile.ZIP_DEFLATED)
        self.assertNotEqual(before, self.source.read_bytes())
        self.check_archive()

    def test_same_source_overwrite_changed_member_is_rejected(self):
        self.baseline()
        self.archive([('encodings/__init__.pyc', b'encodings'), ('abc.pyc', b'changed')])
        with self.assertRaisesRegex(RuntimeError, 'changed/missing members: abc.pyc'):
            self.check_archive()

    def test_missing_member_is_rejected(self):
        self.baseline()
        self.archive([('abc.pyc', b'abc')])
        with self.assertRaisesRegex(RuntimeError, 'encodings/__init__.pyc'):
            self.check_archive()

    def test_zipimport_incompatible_compression_is_rejected(self):
        for compression in (zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA):
            self.archive([('module.pyc', b'unchanged')], compression=compression)
            with self.assertRaisesRegex(RuntimeError, 'Unsupported zipimport compression'):
                self.check(SimpleNamespace(binaries=[], datas=[('base_library.zip', str(self.source), 'DATA')]))

    def test_added_member_is_rejected(self):
        self.baseline()
        self.archive([('encodings/__init__.pyc', b'encodings'), ('abc.pyc', b'abc'), ('new.pyc', b'new')])
        with self.assertRaisesRegex(RuntimeError, 'new.pyc'):
            self.check_archive()

    def test_duplicate_members_are_rejected_even_when_bytes_match(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            self.archive([('abc.pyc', b'abc'), ('abc.pyc', b'abc')])
        with self.assertRaisesRegex(RuntimeError, 'Duplicate base_library.zip member: abc.pyc'):
            self.check_archive()

    def test_binary_requires_exact_bytes_including_same_source_overwrite(self):
        analysis = SimpleNamespace(binaries=[('python313.dll', str(self.source), 'BINARY')], datas=[])
        self.source.write_bytes(b'python runtime')
        self.check(analysis)
        self.check(analysis)
        self.source.write_bytes(b'different runtime')
        with self.assertRaisesRegex(RuntimeError, 'python313.dll'):
            self.check(analysis)

    def test_snapshots_are_taken_before_second_analysis(self):
        tree = ast.parse(SPEC.read_text(encoding='utf-8'))
        events = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id == 'Analysis':
                    events.append('analyze ' + node.targets[0].id)
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id == 'check_shared_files':
                    events.append('check ' + node.value.args[0].id)
        self.assertEqual(events, ['analyze gui', 'check gui', 'analyze cli', 'check cli'])


if __name__ == '__main__':
    unittest.main()


class ReleaseVersionTests(unittest.TestCase):
    def test_embedded_and_packaged_versions_match(self):
        import desktop_core
        import diagnostics
        from tools import build_windows
        root=SPEC.parents[1]
        self.assertEqual(desktop_core.VERSION,diagnostics.VERSION)
        self.assertEqual(desktop_core.VERSION,build_windows.VERSION)
        version=desktop_core.VERSION
        self.assertIn(f'GridCAD-Windows-x64-v{version}.zip',
                      (root/'.github/workflows/windows-desktop.yml').read_text(encoding='utf-8'))
        for name in ('README.md','docs/AGENT_INSTALL.md','docs/RELEASE_NOTES.md','gridcad_desktop.py'):
            self.assertIn(version,(root/name).read_text(encoding='utf-8'),name)
