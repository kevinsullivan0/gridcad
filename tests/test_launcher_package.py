import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

class LauncherPackageTests(unittest.TestCase):
    def test_addon_keeps_helper_path_and_does_not_replace_app(self):
        root=Path(__file__).resolve().parents[1]
        path=root/'tools/package_source_launcher.py'
        self.assertTrue(path.is_file(),'Add-on packaging is missing')
        spec=importlib.util.spec_from_file_location('package_launcher',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as td:
            result=module.package(root,Path(td)/'addon.zip')
            with zipfile.ZipFile(result) as z:
                self.assertEqual(set(z.namelist()),{'Start GridCAD from source.bat','tools/source_launcher.py','docs/SOURCE_LAUNCHER.md'})
                for name in z.namelist():self.assertEqual(z.read(name),(root/name).read_bytes())

    def test_combined_package_has_only_one_normal_bat_at_root(self):
        from tools import build_windows
        self.assertTrue(hasattr(build_windows,'copy_recovery_launcher'),'Combined recovery packaging missing')
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/'GridCAD';folder.mkdir()
            target=build_windows.copy_recovery_launcher(root,folder)
            self.assertEqual(target,folder/'Troubleshooting/Start GridCAD from source.bat')
            self.assertEqual(target.read_bytes(),(root/'Start GridCAD from source.bat').read_bytes())
            self.assertFalse((folder/'Start GridCAD from source.bat').exists())
            self.assertIn('GRIDCAD_SOURCE_ROOT',target.read_text())
