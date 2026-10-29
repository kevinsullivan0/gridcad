"""End-to-end proposal/UI contract tests for reference-label assignments."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import desktop_core as core
from tools.make_reference_example import create_reference_example,REFERENCE_ID

class DesktopReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.folder=create_reference_example(self.root/'input');self.path=self.folder/'DO_NOT_PRINT.PRINT';self.bookpath=self.folder/'DO_NOT_PRINT.xlsx'
        self.project=core.load_project(self.path);self.book=core.read_workbook(self.bookpath)
    def tearDown(self):self.temp.cleanup()
    def propose(self,**kw):
        return core.propose(self.project,self.bookpath,self.book,'Recipes','D4:I7','Sample','synthetic-labels','Rows down; columns right',
                            label_mode='reference',label_reference=REFERENCE_ID,**kw)
    def test_conflicts_visible_before_confirmation_and_writer_blocks(self):
        q=self.propose();info=q['label_material']
        self.assertEqual(info['reference_name'],'Reference white');self.assertEqual(info['material_name'],'EcoFlexWhite')
        self.assertEqual(info['conflict_count'],10);self.assertFalse(info['replacement_confirmed'])
        self.assertTrue(all(x['name'].startswith('Printed index') for x in info['conflicts']))
        with self.assertRaisesRegex(core.op.ValidationError,'explicitly confirm'):
            core.save(self.path,self.bookpath,q,self.root/'refused','Generated physical indices checked')
        self.assertFalse((self.root/'refused').exists())
    def test_confirmed_copy_uses_entire_definition_and_preserves_reference(self):
        q=self.propose(confirm_label_replacement=True)
        report=core.save(self.path,self.bookpath,q,self.root/'saved','Generated physical indices checked')
        n,_,b=core.op.index(core.op.project_document(self.root/'saved/candidate_UNVERIFIED.PRINT'))
        original=self.project['nodes']
        for oid in q['label_ids']:
            self.assertTrue(core.op.same_material_definition(n[oid]['material'],original[REFERENCE_ID]['material']))
            self.assertEqual(n[oid]['material']['id'],original[oid]['material']['id'])
            self.assertEqual(n[oid]['material'],b[oid]['material'])
        self.assertEqual(n[REFERENCE_ID],original[REFERENCE_ID]);self.assertEqual(report['changed_count'],34)
    def test_reference_description_is_validated_readonly(self):
        before=core.op.digest(self.path)
        self.assertEqual(core.reference_material_info(self.project,REFERENCE_ID)['material_name'],'EcoFlexWhite')
        with self.assertRaises(core.op.ValidationError):core.reference_material_info(self.project,'synthetic-sample-1-1')
        self.assertEqual(core.op.digest(self.path),before)
    def test_review_digest_binds_label_policy_not_only_target_ids(self):
        proposal=self.propose(confirm_label_replacement=True)
        for field,value in [('reference_occurrence_id','synthetic-row-label-1'),
                            ('reference_material_sha256','0'*64),
                            ('source_material_sha256','0'*64),
                            ('action','preserve_native_black'),('replacement_confirmed',False)]:
            with self.subTest(field=field):
                plan=core.confirm(proposal,'Generated indices checked')
                original=plan['review']['mapping_sha256'];plan['labels'][0][field]=value
                self.assertNotEqual(core.op.mapping_digest(plan),original)
                with self.assertRaises(core.op.ValidationError):
                    core.op.apply(self.path,self.bookpath,plan,self.root/'tampered')
                self.assertFalse((self.root/'tampered').exists())
    def test_unknown_mode_and_dangling_reference_refused(self):
        args=(self.project,self.bookpath,self.book,'Recipes','D4:I7','Sample','synthetic-labels','Rows down; columns right')
        with self.assertRaises(core.op.ValidationError):core.propose(*args,label_mode='other')
        with self.assertRaises(core.op.ValidationError):core.propose(*args,label_mode='reference',label_reference='missing')

if __name__=='__main__':unittest.main()
