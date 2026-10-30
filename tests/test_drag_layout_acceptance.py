"""Real-Tk pointer/cell bounds while feedback changes; OS EXE journey is separate."""
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).with_name('test_gui_recovery_acceptance.py')
spec=importlib.util.spec_from_file_location('recovery_fixture',path)
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


class DragLayoutAcceptance(unittest.TestCase):
    def setUp(self):
        self.f=fixture.RecoveryAcceptance(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp();self.f.configured()
        self.app=self.f.app;self.grid=self.app.sheet_grid
        self.app.notebook.select(self.app.worktab)
        # Show the same bounded page as the real OS corrective-drag journey.
        # The default A:H page cannot expose column I on any screen size.
        self.app.page_row=self.app.page_col=4;self.app.render_sheet();self.f.pump()

    def bounds(self):
        return (self.grid.winfo_rootx(),self.grid.winfo_rooty(),
                {key:self.app.worksheet_qa_cells()[key] | {'selected':False}
                 for key in ('D4','I7')})

    def drag(self,last,expected):
        cells=self.app.worksheet_qa_cells()
        x0,y0=self.grid.winfo_rootx(),self.grid.winfo_rooty()
        def point(address):
            cell=cells[address]
            return dict(x=cell['x']+cell['w']//2-x0,y=cell['y']+cell['h']//2-y0)
        start=self.bounds()
        self.grid.event_generate('<ButtonPress-1>',**point('D4'));self.f.pump(.05)
        self.assertEqual(self.bounds(),start)
        for address in ('E4','F5','H6',last):
            self.grid.event_generate('<B1-Motion>',**point(address));self.f.pump(.05)
            self.assertEqual(self.bounds(),start,'Feedback moved the active worksheet drag')
        self.grid.event_generate('<ButtonRelease-1>',**point(last));self.f.pump(.1)
        self.assertEqual(self.app.cell_range.get(),expected)
        self.assertFalse(self.app.dragging_cells)
        self.assertFalse(self.app.proposal)
        self.assertEqual(str(self.app.save_button.cget('state')),'disabled')

    def test_error_to_valid_and_valid_to_error_keep_cells_stationary_until_release(self):
        self.f.range('D4:H7');self.f.match()
        self.app.notebook.select(self.app.worktab);self.f.pump()
        self.assertTrue(self.app.worksheet_error.winfo_ismapped())
        self.drag('I7','D4:I7')
        self.assertNotIn('range',self.app.validation_errors)
        self.assertFalse(self.app.worksheet_error.winfo_ismapped())
        self.drag('H7','D4:H7')
        self.assertIn('range',self.app.validation_errors)
        self.assertTrue(self.app.worksheet_error.winfo_ismapped())

    def test_formula_notice_does_not_resize_cells_during_pointer_selection(self):
        self.app.book['Recipes']['D4']['formula']='=saved_example'
        self.f.range('E4:I7');self.app.refresh_feedback(activate=True);self.f.pump()
        self.assertEqual(self.app.formula_notice.get(),'')
        self.drag('I7','D4:I7')
        self.assertIn('last results saved by Excel',self.app.formula_notice.get())
        # Escape flushes any deferred feedback without changing the rectangle.
        self.grid.event_generate('<ButtonPress-1>',x=80,y=40);self.f.pump(.05)
        self.app.cancel_cell_drag();self.f.pump(.1)
        self.assertFalse(self.app.dragging_cells)
        self.assertIsNone(self.app.selection_start)


if __name__=='__main__':unittest.main()
