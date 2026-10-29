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
                self.assertEqual(set(z.namelist()),{'Start GridCAD.bat','tools/source_launcher.py','docs/SOURCE_LAUNCHER.md'})
                for name in z.namelist():self.assertEqual(z.read(name),(root/name).read_bytes())
