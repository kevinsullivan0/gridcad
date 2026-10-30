"""Ordinary conversion mistakes, pinned before product changes with synthetic data."""
import copy
from pathlib import Path
import tempfile
import unittest

import desktop_core as core
import gridcad_desktop as gui
from tools.make_desktop_examples import create, make_workbook


class ConversionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = create(self.root/'synthetic')
        self.project_path = self.folder/'DO_NOT_PRINT.PRINT'
        self.book_path = self.folder/'DO_NOT_PRINT.xlsx'
        self.project = core.load_project(self.project_path)
        self.book = core.read_workbook(self.book_path)

    def feedback(self, **changes):
        self.assertTrue(hasattr(gui, 'selection_feedback'), 'Live, keyed selection feedback is missing')
        args = dict(book=self.book, sheet='Recipes', selected_range='D4:I7',
                    project=self.project, sample_name='Sample', label_id='synthetic-labels',
                    corner='Top left', direction='Down')
        args.update(changes)
        return gui.selection_feedback(**args)

    def test_counts_explain_range_and_recover_without_stale_errors(self):
        bad = self.feedback(selected_range='D4:H7')
        self.assertEqual((bad['selected_count'], bad['expected_count']), (20,24))
        for text in ('Recipes!D4:H7', '20', '24', 'Sample'):
            self.assertIn(text, bad['errors']['range'])
        self.assertFalse(self.feedback()['errors'])
        self.assertIn('range', self.feedback(selected_range='D4:H7')['errors'])

    def test_all_missing_choices_and_overlap_are_keyed_to_responsible_fields(self):
        missing = self.feedback(label_id=None,corner='',direction='')
        self.assertEqual(set(missing['errors']), {'labels','mapping_corner','orientation'})
        self.assertNotIn('labels',self.feedback(corner='',direction='')['errors'])
        overlap = self.feedback(label_id='synthetic-assembly')
        self.assertIn('labels', overlap['errors'])

    def test_no_recipes_does_not_fabricate_a_detected_range(self):
        self.assertEqual(core.suggest_range({'A1':{'value':'A heading, not a recipe'}}), '')
        self.assertIn('range',self.feedback(selected_range='')['errors'])

    def test_recipe_error_names_sheet_cell_and_expected_layout(self):
        self.book['Recipes']['D4']['value'] = 'not a recipe'
        with self.assertRaises(core.op.ValidationError) as error:
            core.read_rectangle(self.book,'Recipes','D4:D4')
        self.assertIn('Recipes!D4', str(error.exception))
        self.assertIn('C / M / Y / K / W / T', str(error.exception))

    def test_saved_formula_results_need_no_false_currentness_attestation(self):
        path=self.root/'formula.xlsx'
        make_workbook(path, {'D4':'2/0/0/0/98/0'}, 1,1,formula_cache={'D4':'2/0/0/0/98/0'})
        self.assertTrue('cache_policy' in __import__('inspect').signature(core.read_rectangle).parameters,
                        'Explicit saved-result policy is missing')
        cells, shape=core.read_rectangle(core.read_workbook(path),'Recipes','D4:D4',cache_policy='saved')
        self.assertEqual(shape,(1,1));self.assertEqual(len(cells),1)
        make_workbook(path, {'D4':'2/0/0/0/98/0'},1,1,formula_cache={'D4':None})
        with self.assertRaisesRegex(core.op.ValidationError,'Recipes!D4'):
            core.read_rectangle(core.read_workbook(path),'Recipes','D4:D4',cache_policy='saved')

    def test_saved_cache_plan_is_truthful_and_passes_unchanged_writer_guards(self):
        self.assertTrue('cache_policy' in __import__('inspect').signature(core.propose).parameters,
                        'Desktop saved-cache plan policy is missing')
        proposal=core.propose(self.project,self.book_path,self.book,'Recipes','D4:I7','Sample',
                             'synthetic-labels','Rows down; columns right',cache_policy='saved')
        self.assertEqual(proposal['plan']['formula_cache_policy'],'saved_cache')
        core.op.prepare(self.project_path,self.book_path,core.candidate_plan(proposal))
        self.assertFalse(proposal['plan']['review']['geometry_and_labels_confirmed'])

    def test_other_grid_dimensions_preserve_existing_label_meshes(self):
        folder=create(self.root/'other',rows=3,columns=9,pitch=18,size=11)
        p=core.load_project(folder/'DO_NOT_PRINT.PRINT');b=core.read_workbook(folder/'DO_NOT_PRINT.xlsx')
        state=self.feedback(project=p,book=b,selected_range='D4:L6')
        self.assertEqual((state['selected_count'],state['expected_count']),(27,27))
        self.assertFalse(state['errors'])
        proposal=core.propose(p,folder/'DO_NOT_PRINT.xlsx',b,'Recipes','D4:L6','Sample',
                             'synthetic-labels','Rows down; columns right')
        before=copy.deepcopy(p['document'])
        core.save_candidate(folder/'DO_NOT_PRINT.PRINT',folder/'DO_NOT_PRINT.xlsx',proposal,self.root/'out')
        after=core.op.project_document(self.root/'out/candidate_UNVERIFIED.PRINT')
        nodes,_,bodies=core.op.index(after)
        oldnodes,_,oldbodies=core.op.index(before)
        for oid in proposal['label_ids']:
            self.assertEqual(nodes[oid],oldnodes[oid]);self.assertEqual(bodies[oid],oldbodies[oid])


if __name__ == '__main__':unittest.main()
