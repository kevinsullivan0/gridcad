"""Distribution oracle/optional artifact contracts; never claim real Windows UI coverage."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('distribution_acceptance', ROOT / 'tools/windows_distribution_acceptance.py')
journey = importlib.util.module_from_spec(spec)
spec.loader.exec_module(journey)


class DistributionOracleTests(unittest.TestCase):
    def test_consent_feeder_waits_for_each_complete_displayed_prompt(self):
        feeder = journey.ConsentFeeder()
        first, second = journey.CONSENT_PROMPTS[:2]
        self.assertIsNone(feeder.next_reply(''))
        self.assertIsNone(feeder.next_reply(first[:-1]))
        self.assertEqual(feeder.next_reply(first), 'Y\n')
        self.assertIsNone(feeder.next_reply(first))
        self.assertIsNone(feeder.next_reply(first + '\nworking...'))
        self.assertEqual(feeder.next_reply(first + '\n' + second), 'Y\n')
        self.assertIsNone(feeder.next_reply(first + '\n' + second))
        self.assertEqual(feeder.answered_count, 2)

    def test_consent_feeder_handles_repeated_and_child_prompts_without_prefill(self):
        feeder = journey.ConsentFeeder()
        parent, child = journey.CONSENT_PROMPTS[2], journey.CONSENT_PROMPTS[-1]
        text = parent
        self.assertEqual(feeder.next_reply(text), 'Y\n')
        self.assertIsNone(feeder.next_reply(text))
        text += '\n' + child
        self.assertEqual(feeder.next_reply(text), 'Y\n')
        self.assertIsNone(feeder.next_reply(text))
        text += '\n' + child
        self.assertEqual(feeder.next_reply(text), 'Y\n')
        self.assertIsNone(feeder.next_reply(text))
        self.assertEqual(feeder.answered_count, 3)

    def test_no_evidence_is_not_acceptance(self):
        errors = journey.validate({}, ROOT)
        self.assertTrue(any('Windows' in e for e in errors))
        self.assertTrue(any('artifact_sha256' in e for e in errors))
        self.assertEqual(sum('not passed' in e for e in errors), len(journey.CASES))

    def test_not_run_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / 'evidence.txt').write_text('synthetic validator fixture, not Windows evidence')
            report = {'platform': 'Windows', 'artifact_sha256': 'a' * 64,
                      'cases': {key: {'status': 'pass', 'evidence': ['evidence.txt']}
                                for key in journey.CASES}}
            self.assertEqual(journey.validate(report, base), [])
            report['cases']['slow_live_exe']['status'] = 'not-run'
            self.assertTrue(any('slow_live_exe' in e for e in journey.validate(report, base)))
            report['cases']['slow_live_exe']['status'] = 'pass'
            (base / 'evidence.txt').unlink()
            self.assertEqual(len(journey.validate(report, base)), len(journey.CASES))

    def test_inert_exe_fixture_changes_only_its_manifest_entry(self):
        import hashlib
        import json
        with tempfile.TemporaryDirectory() as td:
            app = Path(td)
            (app / 'GridCAD.exe').write_bytes(b'synthetic executable bytes')
            other = {'path': 'keep.txt', 'size': 4, 'sha256': 'a' * 64}
            manifest = {'version': '1.0.1', 'files': [
                {'path': 'GridCAD.exe', 'size': 26, 'sha256': 'b' * 64}, other]}
            (app / 'keep.txt').write_bytes(b'keep')
            (app / 'INSTALL_MANIFEST.json').write_text(json.dumps(manifest))
            journey.make_nonexecutable_fixture(app)
            updated = json.loads((app / 'INSTALL_MANIFEST.json').read_text())
            content = (app / 'GridCAD.exe').read_bytes()
            self.assertFalse(content.startswith(b'MZ'))
            self.assertEqual(updated['files'][0]['size'], len(content))
            self.assertEqual(updated['files'][0]['sha256'], hashlib.sha256(content).hexdigest())
            self.assertEqual(updated['files'][1], other)
            self.assertEqual(updated['version'], manifest['version'])
            self.assertEqual((app / 'keep.txt').read_bytes(), b'keep')

    @unittest.skipUnless(os.environ.get('GRIDCAD_DISTRIBUTION_ZIP'), 'Set GRIDCAD_DISTRIBUTION_ZIP for exact built-artifact contract')
    def test_exact_combined_artifact_contents(self):
        with zipfile.ZipFile(os.environ['GRIDCAD_DISTRIBUTION_ZIP']) as archive:
            names = set(archive.namelist())
            for name in ('Start GridCAD.bat', 'Start GridCAD from source.bat',
                         'tools/windows_launcher.ps1', 'tools/source_launcher.py',
                         'gridcad_desktop.py', 'desktop_core.py', 'GridCAD.exe',
                         'GridCAD-core.exe', 'VERSION.txt', 'LICENSE',
                         'resources/gridcad.ico', 'docs/SOURCE_LAUNCHER.md'):
                self.assertIn('GridCAD/' + name, names)
            self.assertTrue(any(n.startswith('GridCAD/operator/gridcad_operator/') for n in names))
            self.assertTrue(any(n.startswith('GridCAD/_internal/') for n in names))
            for source in ('Start GridCAD.bat', 'Start GridCAD from source.bat',
                           'tools/windows_launcher.ps1', 'tools/source_launcher.py'):
                self.assertEqual(archive.read('GridCAD/' + source), (ROOT / source).read_bytes())


if __name__ == '__main__':
    unittest.main()
