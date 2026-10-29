import importlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import agent_help


class DetectionTests(unittest.TestCase):
    def test_import_does_not_scan(self):
        with patch('pathlib.Path.lstat', side_effect=AssertionError('scanned')):
            importlib.reload(agent_help)

    def test_known_filename_spaces_no_execution(self):
        with tempfile.TemporaryDirectory(prefix='GridCAD agent paths ') as root:
            folder = Path(root)
            candidate = folder / ('codex.exe' if os.name == 'nt' else 'codex')
            candidate.write_text('this is deliberately not an executable')
            with patch.dict(os.environ, {'PATH': str(folder)}), patch('agent_help._registered_paths', return_value=iter(())):
                result = agent_help.detect_agents()
            self.assertEqual(result['matches'], [{'name': 'Codex', 'path': str(candidate), 'source': 'PATH filename'}])
            self.assertIn('not verified', result['notes'][0])

    def test_relative_current_network_and_missing_skipped(self):
        for value in ('', '.', 'relative/bin', os.getcwd(), '\\\\server\\share\\codex.exe', '//server/share/codex', '/no-such-gridcad-folder'):
            self.assertIsNone(agent_help._local_path(value), value)

    def test_no_arbitrary_filename_or_registry_commands(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            (folder / 'other.exe').write_text('')
            with patch.dict(os.environ, {'PATH': str(folder)}), patch('agent_help._registered_paths', return_value=iter([('Codex', 'codex.exe', str(folder / 'other.exe'))])):
                self.assertEqual(agent_help.detect_agents()['matches'], [])

    def test_links_not_followed(self):
        if os.name == 'nt':
            self.skipTest('Windows symlink creation may require privilege; reparse flags tested separately')
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            real = folder / 'real'
            real.mkdir()
            (real / 'codex').write_text('')
            link = folder / 'link'
            link.symlink_to(real, target_is_directory=True)
            self.assertIsNone(agent_help._local_path(str(link / 'codex')))

    def test_unreadable_metadata_and_duplicate_paths(self):
        with patch('pathlib.Path.lstat', side_effect=PermissionError('denied')):
            self.assertIsNone(agent_help._local_path(str(Path.cwd() / 'codex')))
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            candidate = folder / ('codex.exe' if os.name == 'nt' else 'codex')
            candidate.write_text('')
            with patch.dict(os.environ, {'PATH': os.pathsep.join([str(folder), str(folder)])}), patch('agent_help._registered_paths', return_value=iter(())):
                self.assertEqual(len(agent_help.detect_agents()['matches']), 1)

    def test_reparse_metadata_rejected(self):
        fake = type('Info', (), {'st_mode': 0, 'st_file_attributes': 0x400})()
        with patch('pathlib.Path.lstat', return_value=fake):
            self.assertIsNone(agent_help._local_path(str(Path.cwd() / 'codex')))


if __name__ == '__main__':
    unittest.main()
