"""Bootstrap regressions: setup cannot claim ready early or reinstall each run."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/'tools/source_launcher.py'

class LauncherTests(unittest.TestCase):
    def load(self):
        self.assertTrue(PATH.is_file(), 'Source launcher implementation is missing')
        spec=importlib.util.spec_from_file_location('source_launcher',PATH)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_missing_app_fails_before_creating_state(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            with self.assertRaisesRegex(RuntimeError,'GridCAD'):
                m.validate_app(base)
            self.assertEqual(list(base.iterdir()),[])

    def test_ready_environment_is_reused_without_setup(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);env=base/'runtime';env.mkdir()
            (base/'ready.json').write_text(m.ready_record())
            with patch.object(m,'probe_environment',return_value=True),patch.object(m,'create_environment',side_effect=AssertionError('must not install')):
                self.assertEqual(m.ensure_environment(base),env)

    def test_failed_setup_never_writes_ready_record(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            with patch.object(m,'create_environment',side_effect=RuntimeError('offline')):
                with self.assertRaisesRegex(RuntimeError,'offline'):m.ensure_environment(base, setup_approved=True)
            self.assertFalse((base/'ready.json').exists())

    def test_incomplete_environment_is_preserved_and_rebuilt(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);env=base/'runtime';env.mkdir();(env/'partial').write_text('keep')
            def create(path):path.mkdir();(path/'new').write_text('new')
            with patch.object(m,'create_environment',side_effect=create),patch.object(m,'probe_environment',return_value=True):
                result=m.ensure_environment(base, setup_approved=True)
            self.assertTrue((result/'new').exists())
            self.assertEqual(len(list(base.glob('incomplete-*/partial'))),1)
            self.assertEqual((base/'ready.json').read_text(),m.ready_record())

    def test_failed_probe_never_marks_environment_ready(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            with patch.object(m,'create_environment',side_effect=lambda p:p.mkdir()),patch.object(m,'probe_environment',return_value=False):
                with self.assertRaisesRegex(RuntimeError,'verify'):m.ensure_environment(base, setup_approved=True)
            self.assertFalse((base/'ready.json').exists())

    def test_probe_requires_a_working_tk_window(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as td:
            env=Path(td);(env/'Scripts').mkdir();(env/'Scripts/python.exe').write_bytes(b'placeholder')
            class BrokenTk:
                @staticmethod
                def Tcl():return type('Tcl',(),{'eval':lambda self,text:'8.6.15'})()
                @staticmethod
                def Tk():raise RuntimeError('Tk GUI unavailable')
            class Pillow:
                __version__='13.0.0'
                __file__=str(env/'Lib/site-packages/PIL/__init__.py')
                Image=type('Image',(),{'new':staticmethod(lambda *a:type('Pixels',(),{'tobytes':lambda self:b''})())})
                ImageTk=object()
            def execute_probe(command,**kwargs):
                import sys
                from types import SimpleNamespace
                try:
                    with patch.dict(sys.modules,{'tkinter':BrokenTk,'PIL':Pillow}),patch.object(sys,'prefix',str(env)),patch.object(sys,'version_info',(3,13,16)):
                        exec(command[-1],{})
                    return SimpleNamespace(returncode=0)
                except RuntimeError:return SimpleNamespace(returncode=1)
            with patch.object(m.subprocess,'run',side_effect=execute_probe):
                self.assertFalse(m.probe_environment(env))
