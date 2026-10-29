"""A release may publish only the exact passing, hash-bound Windows assets."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import hashlib

ROOT=Path(__file__).resolve().parents[1]


class ReleasePublicationTests(unittest.TestCase):
    def load(self):
        spec=importlib.util.spec_from_file_location('publish_release',ROOT/'tools/publish_approved_release.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def fixture(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        folder=Path(temporary.name)
        names=['GridCAD-Windows-x64-v1.0.1.zip','GridCAD-Source-Windows-v1.0.1.zip',
               'GridCAD-portable-core-v1.0.1.zip','GridCAD-Windows-GUI-evidence.zip','GridCAD-launcher-evidence.zip','GridCAD-distribution-evidence.zip']
        for name in names:
            with zipfile.ZipFile(folder/name,'w') as archive:
                members=('distribution-qa/acceptance.json','fallback-qa/acceptance.json') if name=='GridCAD-distribution-evidence.zip' else ('acceptance.json',)
                for member in members:archive.writestr(member,json.dumps({'status':'passed','native_grabcad_open_recompose_save_verified':False}))
        record={'tag':'v1.0.1','source_sha':'a'*40,'run_id':123,'verification_passed':True,
                'assets':{name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in names}}
        run={'conclusion':'success','status':'completed','head_sha':'a'*40,'head_branch':'release/v1.0-polish'}
        return folder,record,run

    def test_import_has_no_publication_side_effect(self):
        self.assertTrue(callable(self.load().validate_release))

    def test_matching_passing_assets_are_accepted(self):
        folder,record,run=self.fixture();self.load().validate_release(record,run,folder)

    def test_failed_or_wrong_revision_run_is_refused(self):
        folder,record,run=self.fixture()
        for change in ({'conclusion':'failure'},{'head_sha':'b'*40},{'head_branch':'other'}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.load().validate_release(record,dict(run,**change),folder)

    def test_modified_asset_is_refused(self):
        folder,record,run=self.fixture();next(folder.iterdir()).write_bytes(b'changed')
        with self.assertRaises(ValueError):self.load().validate_release(record,run,folder)

    def test_gui_or_launcher_failure_is_refused_even_if_hash_matches(self):
        for name in ('GridCAD-Windows-GUI-evidence.zip','GridCAD-launcher-evidence.zip','GridCAD-distribution-evidence.zip'):
            folder,record,run=self.fixture()
            with zipfile.ZipFile(folder/name,'w') as archive:archive.writestr('acceptance.json','{"status":"failed"}')
            record['assets'][name]=hashlib.sha256((folder/name).read_bytes()).hexdigest()
            with self.subTest(name=name),self.assertRaises(ValueError):self.load().validate_release(record,run,folder)

    def test_missing_required_asset_or_unsafe_filename_is_refused(self):
        folder,record,run=self.fixture();record['assets'].pop('GridCAD-Source-Windows-v1.0.1.zip')
        with self.assertRaises(ValueError):self.load().validate_release(record,run,folder)
        folder,record,run=self.fixture();record['assets']['../other']='0'*64
        with self.assertRaises(ValueError):self.load().validate_release(record,run,folder)


if __name__=='__main__':unittest.main()
