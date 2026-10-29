import tempfile
import unittest
import zipfile
from pathlib import Path
from tools import build_windows as build

class SourceDistributionTests(unittest.TestCase):
    def test_source_package_is_complete_and_excludes_private_runtime_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'source';root.mkdir()
            files=['Start GridCAD.bat','gridcad_desktop.py','desktop_core.py','desktop_cli.py','diagnostics.py','agent_help.py','README.md','AGENTS.md','LICENSE','VERSION.txt','tools/source_launcher.py','resources/gridcad.ico','docs/DESKTOP_MANUAL.md','operator/gridcad_operator/operator.py','examples/rectangular/DO_NOT_PRINT.PRINT']
            for name in files:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture')
            for name in ['private/customer.PRINT','.gridcad-launcher/secret.json','operator/__pycache__/a.pyc','tools/secret.py','GridCAD.exe']:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('private')
            target=Path(temp)/'bundle.zip'
            self.assertTrue(hasattr(build,'package_source'),'Missing complete source package builder')
            build.package_source(root,target)
            with zipfile.ZipFile(target) as z:
                names=set(z.namelist())
                for name in files:self.assertIn('GridCAD/'+name,names)
                self.assertFalse(any('secret' in n or '__pycache__' in n or '/private/' in n or n.endswith('.exe') for n in names))
