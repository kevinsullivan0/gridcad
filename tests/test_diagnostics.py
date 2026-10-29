from pathlib import Path
import json
import tempfile
import unittest
import diagnostics as d

class DiagnosticsTests(unittest.TestCase):
    def test_plain_language_cell_and_action(self):
        x=d.describe(ValueError('D12: formula uses a saved result.'),{'workbook':'/private/Recipes.xlsx','sheet':'Mixes'})
        self.assertEqual(x.code,'GCD101');self.assertEqual(x.where,'Recipes.xlsx → Mixes → D12')
        self.assertIn('Recalculate',x.remedy);self.assertNotIn('GCD101',x.text());self.assertIn('GCD101',x.text(details=True))
    def test_dimension_expected_actual_and_recovery(self):
        x=d.describe(ValueError('Geometry has 6 × 4 positions in this orientation; worksheet is 4 × 6. Check transpose and orientation.'))
        self.assertEqual(x.code,'GCD201');self.assertIn('6 × 4',x.actual);self.assertIn('first-cell corner',x.remedy);self.assertIn('next worksheet row',x.remedy);self.assertNotIn('Transpose',x.remedy)
    def test_report_minimizes_input_data_and_prompt_explains_access(self):
        with tempfile.TemporaryDirectory() as t:
            try:raise ValueError('D4: private recipe value SENTINEL_PRIVATE_CONTENT')
            except ValueError as exc:
                report=d.create_report(exc,d.describe(exc),{'workbook':'private.xlsx','sheet':'Recipes','password':'SECRET_TOKEN','recipe':'SECRET_CELL'},directory=t)
            raw=report.read_text();saved=json.loads(raw)
            self.assertNotIn('SENTINEL_PRIVATE_CONTENT',raw);self.assertNotIn('SECRET_',raw)
            self.assertEqual(saved['settings'],{'workbook':'private.xlsx','sheet':'Recipes'})
            self.assertTrue(saved['traceback']);self.assertNotIn('locals',raw)
            prompt=d.debugging_prompt(report);self.assertIn(str(report),prompt);self.assertIn('grant file access',prompt);self.assertIn('nothing was uploaded',prompt)
    def test_unwritable_report_location_does_not_replace_error(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'a-file';path.write_text('untouched')
            exc=ValueError('Output directory must not exist; nothing is overwritten.')
            info=d.describe(exc)
            with self.assertRaises(OSError):d.create_report(exc,info,directory=path)
            self.assertEqual(info.code,'GCD401');self.assertEqual(path.read_text(),'untouched')
    def test_count_and_integrity_errors_do_not_suggest_recipe_edits(self):
        info=d.describe(ValueError('Selected group has 24 bodies; the worksheet rectangle has 20 recipes. Select matching ranges/groups.'))
        self.assertEqual(info.code,'GCD205');self.assertIn('24',info.expected);self.assertIn('20',info.actual)
        for message in ['Saved recipe mismatch.','Worksheet disagrees with independently expected label-derived recipe.']:
            self.assertEqual(d.describe(ValueError(message)).code,'GCD403')
        self.assertEqual(d.describe(ValueError('Input changed during conversion')).code,'GCD402')
    def test_clipboard_failure_remains_local_and_recoverable(self):
        class Broken:
            def clipboard_clear(self):raise PermissionError('busy')
        class Working:
            def clipboard_clear(self):self.text=''
            def clipboard_append(self,text):self.text=text
        self.assertFalse(d.try_copy_prompt(Broken(),'prompt'))
        good=Working();self.assertTrue(d.try_copy_prompt(good,'prompt'));self.assertEqual(good.text,'prompt')
    def test_no_unsafe_security_or_force_recommendation(self):
        x=d.describe(PermissionError('Access denied'))
        self.assertIn('Do not change security protections',x.remedy)
        y=d.describe(ValueError('Unknown version'))
        self.assertIn('do not edit version',y.remedy)

if __name__=='__main__':unittest.main()
