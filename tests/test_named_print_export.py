"""Named desktop output preserves the reviewed writer and ordinary files."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import desktop_core as core
from tools.make_desktop_examples import create


class NamedPrintExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.inputs=create(self.base/'inputs')
        self.project=self.inputs/'DO_NOT_PRINT.PRINT';self.book=self.inputs/'DO_NOT_PRINT.xlsx'
        self.proposal=core.propose(core.load_project(self.project),self.book,core.read_workbook(self.book),
            'Recipes','D4:I7','Sample','synthetic-labels','Rows down; columns right')
        self.folder=self.base/'results';self.folder.mkdir()
        self.output=self.folder/'My materials.PRINT'

    def save(self,**kwargs):
        return core.save_print(self.project,self.book,self.proposal,self.output,**kwargs)

    def test_normal_export_has_only_chosen_print_and_exact_validated_digest(self):
        originals=[core.op.digest(p) for p in (self.project,self.book)]
        audit=self.save()
        self.assertEqual([p.name for p in self.folder.iterdir()],['My materials.PRINT'])
        self.assertEqual(core.op.digest(self.output),audit['output_sha256'])
        self.assertFalse(audit['print_ready']);self.assertFalse(audit['physical_mapping_reviewed'])
        self.assertEqual(originals,[core.op.digest(p) for p in (self.project,self.book)])

    def test_optional_report_matches_named_result_and_never_creates_warning_text(self):
        audit=self.save(include_report=True)
        report=self.output.with_suffix('.gridcad-report.json')
        self.assertEqual({p.name for p in self.folder.iterdir()},{self.output.name,report.name})
        self.assertEqual(json.loads(report.read_text()),audit)

    def test_existing_print_or_report_is_untouched(self):
        for suffix in ('.PRINT','.gridcad-report.json'):
            with self.subTest(suffix=suffix):
                target=self.output if suffix=='.PRINT' else self.output.with_suffix(suffix)
                target.write_text('existing owner data')
                with self.assertRaises(core.op.ValidationError):self.save(include_report=True)
                self.assertEqual(target.read_text(),'existing owner data')
                target.unlink()

    def test_changed_destination_folder_is_refused_before_publication(self):
        real=core.save_candidate
        moved=self.base/'moved-results'
        def change_folder(*args,**kwargs):
            audit=real(*args,**kwargs)
            self.folder.rename(moved);self.folder.mkdir()
            return audit
        with mock.patch.object(core,'save_candidate',side_effect=change_folder):
            with self.assertRaisesRegex(core.op.ValidationError,'folder.*changed'):
                self.save()
        self.assertFalse(self.output.exists())
        self.assertFalse((moved/self.output.name).exists())

    def test_changed_validated_bytes_are_refused(self):
        real=core.save_candidate
        def change_candidate(*args,**kwargs):
            audit=real(*args,**kwargs)
            (Path(args[3])/'candidate_UNVERIFIED.PRINT').write_bytes(b'not validated')
            return audit
        with mock.patch.object(core,'save_candidate',side_effect=change_candidate):
            with self.assertRaisesRegex(core.op.ValidationError,'validated.*changed'):
                self.save()
        self.assertFalse(self.output.exists())

    def test_report_failure_preserves_completed_print_and_reports_warning(self):
        real=core.os.link
        def unavailable_report(source,target,*args,**kwargs):
            if str(target).endswith('.gridcad-report.json'):
                raise PermissionError('report is unavailable')
            return real(source,target,*args,**kwargs)
        with mock.patch.object(core.os,'link',side_effect=unavailable_report):audit=self.save(include_report=True)
        self.assertEqual(core.op.digest(self.output),audit['output_sha256'])
        self.assertNotIn('report_path',audit)
        self.assertIn('report_warning',audit)
        self.assertEqual([p.name for p in self.folder.iterdir()],[self.output.name])


if __name__=='__main__':unittest.main()
