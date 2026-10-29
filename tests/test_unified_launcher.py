"""Executable contracts, not a claim of native Windows acceptance."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class StartupReadinessTests(unittest.TestCase):
    def load(self):
        spec=importlib.util.spec_from_file_location('readiness_app',ROOT/'gridcad_desktop.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_ready_is_not_written_for_hidden_interface(self):
        app=self.load()
        self.assertTrue(hasattr(app,'write_launch_ready'),'Visible GUI readiness is not implemented')
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'ready.json'
            hidden=type('Root',(),{'winfo_viewable':lambda self:False})()
            self.assertFalse(app.write_launch_ready(hidden,path,'nonce'))
            self.assertFalse(path.exists())

    def test_ready_contains_live_pid_version_and_fresh_token(self):
        import os
        app=self.load()
        self.assertTrue(hasattr(app,'write_launch_ready'),'Visible GUI readiness is not implemented')
        with tempfile.TemporaryDirectory(prefix='GridCAD é ') as td:
            path=Path(td)/'ready.json'
            visible=type('Root',(),{'winfo_viewable':lambda self:True})()
            self.assertTrue(app.write_launch_ready(visible,path,'fresh-token'))
            self.assertEqual(json.loads(path.read_text()),{'pid':os.getpid(),'version':app.diagnostics.VERSION,'token':'fresh-token'})
            self.assertEqual([p.name for p in Path(td).iterdir()],['ready.json'])

    def test_no_readiness_path_does_not_create_files(self):
        app=self.load()
        self.assertTrue(hasattr(app,'write_launch_ready'),'Visible GUI readiness is not implemented')
        self.assertFalse(app.write_launch_ready(None,None,None))


class CombinedLauncherContractTests(unittest.TestCase):
    def test_primary_entrypoint_and_independent_source_launcher_are_distinct(self):
        primary=(ROOT/'Start GridCAD.bat').read_text()
        self.assertIn('windows_launcher.ps1',primary)
        self.assertTrue((ROOT/'Start GridCAD from source.bat').is_file())
        source=(ROOT/'Start GridCAD from source.bat').read_text()
        self.assertIn('source_launcher.py',source)
        self.assertNotIn('windows_launcher.ps1',source)

    def test_installer_does_not_disable_policy_and_offers_shortcut(self):
        path=ROOT/'tools/windows_launcher.ps1'
        self.assertTrue(path.is_file(),'Unified Windows launcher is missing')
        text=path.read_text()
        for forbidden in ('Set-ExecutionPolicy','-ExecutionPolicy Bypass','Unblock-File','Add-MpPreference','RunAs'):
            self.assertNotIn(forbidden,text)
        self.assertIn('CreateShortcut',text)
        self.assertIn('LocalApplicationData',text)
        self.assertIn('INSTALL_MANIFEST.json',text)
        self.assertIn('WaitForExit',text)

    def test_loaded_scriptblock_helpers_use_their_invocation_scope(self):
        # The BAT invokes Create(...), not -File. $script: targets its outer
        # -Command script and loses the launcher's version/log variables.
        source=(ROOT/'tools/windows_launcher.ps1').read_text()
        self.assertNotIn('$script:Version',source)
        self.assertNotIn('$script:log',source)


if __name__=='__main__':unittest.main()
