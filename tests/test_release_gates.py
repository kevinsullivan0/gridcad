"""Regression gates for the actual Windows acceptance pipeline."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ReleaseGatesTests(unittest.TestCase):
    def test_windows_full_discovery_has_complete_test_dependencies(self):
        workflow=(ROOT/'.github/workflows/windows-desktop.yml').read_text()
        self.assertIn('-r requirements-test.txt',workflow)
        requirements=(ROOT/'requirements-test.txt').read_text()
        for package in ('openpyxl==3.1.5','et-xmlfile==2.0.0','defusedxml==0.7.1'):
            self.assertIn(package,requirements)

    def test_windows_regression_does_not_mask_earlier_failed_command(self):
        workflow=(ROOT/'.github/workflows/windows-desktop.yml').read_text()
        start=workflow.index('      - name: Rectangular desktop core regression')
        end=workflow.index('      - name:',start+1)
        block=workflow[start:end]
        commands=[line for line in block.splitlines() if 'python -m unittest' in line]
        self.assertEqual(len(commands),1,'Use one complete discovery, not a PowerShell sequence that can hide a failed first command.')

    def test_native_dialog_entry_pastes_complete_path(self):
        source=(ROOT/'tools/windows_gui_acceptance.py').read_text()
        start=source.index('    def dialog_path(path):')
        end=source.index('    def dismiss():',start)
        block=source[start:end]
        self.assertIn('SetClipboardText',block)
        self.assertIn("'^v'",block)
        self.assertNotIn('keyboard.send_keys(str(path)',block)


if __name__=='__main__':unittest.main()
