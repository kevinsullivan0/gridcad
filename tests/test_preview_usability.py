"""Ordinary regressions for inspection and candidate-only desktop saving."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
import desktop_core as core
from gridcad_desktop import App
import test_desktop_core

class CandidateSaveTests(unittest.TestCase):
    setUp=test_desktop_core.DesktopCoreTests.setUp
    tearDown=test_desktop_core.DesktopCoreTests.tearDown
    proposal=test_desktop_core.DesktopCoreTests.proposal
    def test_candidate_save_does_not_attest_physical_review(self):
        proposal=self.proposal()
        audit=core.save_candidate(self.project_path,self.book_path,proposal,self.base/'candidate')
        self.assertFalse(audit['physical_mapping_reviewed'])
        self.assertFalse(audit['print_ready'])
        self.assertTrue(audit['nonmaterial_preservation_passed'])
        self.assertFalse(proposal['plan']['review']['geometry_and_labels_confirmed'])
    def test_candidate_mode_cannot_claim_review(self):
        plan=core.candidate_plan(self.proposal())
        plan['review']['geometry_and_labels_confirmed']=True
        with self.assertRaises(core.op.ValidationError):
            core.op.prepare(self.project_path,self.book_path,plan)

class PreviewInspectionTests(unittest.TestCase):
    def test_unmapped_sample_can_be_inspected(self):
        app=SimpleNamespace(canvas_ids={},canvas=Mock(),project={'nodes':{'a':{'name':'Sample','material':{'name':'Original','metadata':{'displayName':'Actual source'}}}},'records':{'a':{'center':[1,2,3]}}},proposal=None,detail=Mock(),sheet=Mock())
        App.inspect_geometry(app,'a')
        self.assertIn('Actual source',app.detail.set.call_args.args[0])
        self.assertIn('not mapped',app.detail.set.call_args.args[0].lower())
    def test_blank_canvas_does_not_pick_nearest_sample(self):
        app=SimpleNamespace(canvas=Mock(),canvas_ids={3:'a'},inspect_geometry=Mock())
        app.canvas.canvasx.return_value=10;app.canvas.canvasy.return_value=10
        app.canvas.find_overlapping.return_value=()
        App.click_geometry(app,SimpleNamespace(x=10,y=10))
        app.inspect_geometry.assert_not_called()

    def test_missing_reference_cannot_open_replacement_dialog(self):
        app=SimpleNamespace(replace_labels=Mock(),proposal={'label_material':{'conflicts':[{'name':'label'}]}},
                            reference_ids={},label_reference=Mock(),project={'leaves':[]},label_mode=Mock(),status=Mock())
        app.replace_labels.get.return_value=True
        App.review_label_replacements(app)
        app.replace_labels.set.assert_called_once_with(False)
        self.assertIn('Choose a saved material',app.status.set.call_args.args[0])
