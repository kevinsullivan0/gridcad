import copy
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import desktop_core as core
from tools.make_desktop_examples import create,make_workbook


class DesktopCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.folder=create(self.base/'example')
        self.project_path=self.folder/'DO_NOT_PRINT.PRINT';self.book_path=self.folder/'DO_NOT_PRINT.xlsx'
        self.project=core.load_project(self.project_path);self.book=core.read_workbook(self.book_path)
    def tearDown(self):self.temp.cleanup()
    def proposal(self,**kw):
        args=dict(sheet='Recipes',selected_range='D4:I7',sample_name='Sample',label_container='synthetic-labels',orientation='Rows down; columns right')
        args.update(kw);return core.propose(self.project,self.book_path,self.book,**args)
    def test_known_physical_indices_exactly_mapped(self):
        proposal=self.proposal()
        self.assertEqual({x['cell']:x['id'] for x in proposal['mapping']},
            {core.address(r+4,c+4):f'synthetic-sample-{r+1}-{c+1}' for r in range(4) for c in range(6)})
        self.assertFalse(proposal['plan']['review']['geometry_and_labels_confirmed'])
    def test_orientation_and_transpose_are_explicit(self):
        with self.assertRaises(core.op.ValidationError):self.proposal(orientation='')
        with self.assertRaises(core.op.ValidationError):self.proposal(transpose=True)
        p=self.proposal(orientation='Rows right; columns down',transpose=True)
        self.assertEqual(p['mapping'][0]['id'],'synthetic-sample-1-1')
        self.assertEqual(p['mapping'][-1]['id'],'synthetic-sample-4-6')
    def test_flips_change_physical_targets_without_source_mutation(self):
        p=self.proposal(orientation='Rows up; columns left')
        self.assertEqual(p['mapping'][0]['id'],'synthetic-sample-4-6')
        self.assertEqual(core.op.digest(self.project_path),self.project['sha256'])
    def test_save_preserves_geometry_material_ids_black_and_payloads(self):
        p=self.proposal();before=self.project['document'];source_hash=core.op.digest(self.project_path);book_hash=core.op.digest(self.book_path)
        audit=core.save(self.project_path,self.book_path,p,self.base/'new-result','Known generated four corners and index labels inspected.')
        after=core.op.project_document(self.base/'new-result/candidate_UNVERIFIED.PRINT')
        a=core.op.index(after);b=core.op.index(before)
        self.assertEqual(audit['changed_count'],24);self.assertFalse(audit['print_ready']);self.assertFalse(audit['native_open_recompose_save_verified'])
        self.assertEqual(core.op.stripped(before,set(audit['changed_occurrence_ids'])),core.op.stripped(after,set(audit['changed_occurrence_ids'])))
        for oid in p['label_ids']:self.assertEqual(a[0][oid],b[0][oid])
        for oid in a[2]:self.assertEqual(a[0][oid]['material']['id'],b[0][oid]['material']['id'])
        self.assertEqual(source_hash,core.op.digest(self.project_path));self.assertEqual(book_hash,core.op.digest(self.book_path))
        with self.assertRaises(core.op.ValidationError):core.save(self.project_path,self.book_path,p,self.base/'new-result','Reviewed')
    def test_formula_cache_needs_confirmation_and_missing_never_passes(self):
        make_workbook(self.base/'cached.xlsx',{'D4':'2/0/0/0/98/0'},1,1,formula_cache={'D4':'2/0/0/0/98/0'})
        book=core.read_workbook(self.base/'cached.xlsx')
        with self.assertRaises(core.op.ValidationError):core.read_rectangle(book,'Recipes','D4:D4')
        core.read_rectangle(book,'Recipes','D4:D4',cache_confirmed=True)
        make_workbook(self.base/'missing.xlsx',{'D4':'2/0/0/0/98/0'},1,1,formula_cache={'D4':None})
        with self.assertRaises(core.op.ValidationError):core.read_rectangle(core.read_workbook(self.base/'missing.xlsx'),'Recipes','D4:D4',cache_confirmed=True)
    def test_occurrence_geometry_disagreement_refused(self):
        p=copy.deepcopy(self.project);p['nodes']['synthetic-sample-2-2']['transform'][7]+=1
        self.project=p
        with self.assertRaises(core.op.ValidationError):self.proposal()
    def test_holes_duplicate_centers_and_bad_cardinality_refused(self):
        with self.assertRaises(core.op.ValidationError):self.proposal(selected_range='D4:H7')
        self.project['records']['synthetic-sample-2-2']['center']=self.project['records']['synthetic-sample-1-1']['center']
        with self.assertRaises(core.op.ValidationError):self.proposal()
    def test_unrelated_coverage_and_no_silent_normalization(self):
        self.assertEqual(self.proposal()['preserved_count'],0)
        self.book['Recipes']['D4']['value']='2/0/0/0/99/0'
        with self.assertRaises(core.op.ValidationError):self.proposal()
    def test_dimension_count_pitch_and_size_variants(self):
        create(self.base/'other',rows=3,columns=9,pitch=18,size=11)
        path=self.base/'other/DO_NOT_PRINT.PRINT';bookpath=self.base/'other/DO_NOT_PRINT.xlsx'
        p=core.propose(core.load_project(path),bookpath,core.read_workbook(bookpath),'Recipes','D4:L6','Sample','synthetic-labels','Rows down; columns right')
        self.assertEqual(len(p['mapping']),27)
    def test_long_sheet_late_selection_and_exact_addresses(self):
        make_workbook(self.base/'long.xlsx',{'D501':'2/0/0/0/98/0','E501':'0/0/0/0/0/100'},1,2)
        rows,shape=core.read_rectangle(core.read_workbook(self.base/'long.xlsx'),'Recipes','D501:E501')
        self.assertEqual([r['cell'] for r in rows],['D501','E501']);self.assertEqual(shape,(1,2))
    def test_unknown_version_and_compose_are_not_repaired(self):
        doc=core.op.project_document(self.project_path);doc['version']['applicationVersion']='unknown'
        nodes,_,bodies=core.op.index(doc)
        with self.assertRaises(core.op.ValidationError):core.op.placement(doc,nodes,bodies,core.op.REVIEWED_ID_PROFILE)
    def test_user_review_notes_required_and_request_origin_honest(self):
        p=self.proposal()
        with self.assertRaises(core.op.ValidationError):core.confirm(p,' ')
        confirmed=core.confirm(p,'Four generated corners and interior indices matched.')
        self.assertIn('not OCR',confirmed['review']['evidence'])
        self.assertEqual(confirmed['review']['mapping_sha256'],core.op.mapping_digest(confirmed))


if __name__=='__main__':unittest.main()
