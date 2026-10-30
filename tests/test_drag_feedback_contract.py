"""Frozen 2026-10-30: no feedback row collapse under an active worksheet drag.

Callback-level sentinel, not a substitute for the actual Windows OS drag. A
future permanently reserved row implementation may replace this with its
pixel-bound invariant; it must never merely delete the original OS assertion.
"""
import sys, unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gridcad_desktop as gui

class DragFeedbackContract(unittest.TestCase):
    def test_error_to_valid_does_not_collapse_feedback_during_drag(self):
        app=gui.App.__new__(gui.App)
        app.book={}; app.project={}; app.container_ids={}; app.controls={}
        for name in ('sheet','cell_range','sample','labels','mapping_corner','mapping_direction',
                     'selection_summary','formula_notice','status','worksheet_error','selection_problem',
                     'book_label','project_label'):
            setattr(app,name,Mock())
        app.operation_errors={}; app.validation_errors={'range':'20 cells selected; 24 expected'}
        app.validation_active=True; app.field_error_labels={}; app.dragging_cells=True
        with patch.object(gui,'selection_feedback',return_value={'summary':'24 selected', 'formula_count':0,'errors':{}}):
            app.refresh_feedback()
        app.worksheet_error.grid_remove.assert_not_called()
        app.worksheet_error.configure.assert_not_called()
        app.formula_notice.set.assert_not_called()
        self.assertEqual(app.validation_errors,{},'Logical validation should remain current during dragging')

    def test_release_publishes_final_feedback_after_drag(self):
        app=gui.App.__new__(gui.App)
        app.dragging_cells=True; app.drag_cells=Mock();app.refresh_feedback=Mock()
        app.release_cells(Mock())
        self.assertFalse(app.dragging_cells)
        app.refresh_feedback.assert_called_once()

    def test_escape_publishes_feedback_and_clears_drag_anchor(self):
        app=gui.App.__new__(gui.App)
        app.dragging_cells=True; app.selection_start=(4,4); app.refresh_feedback=Mock()
        app.cancel_cell_drag()
        self.assertFalse(app.dragging_cells)
        self.assertIsNone(app.selection_start)
        app.refresh_feedback.assert_called_once()

if __name__=='__main__':unittest.main()
