"""Worker-boundary regressions without a Tk display or private fixtures."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from gridcad_desktop import App


class Value:
    def __init__(self,value=''):
        self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value


class WorkbookActivityTests(unittest.TestCase):
    def setUp(self):
        self.app=App.__new__(App)
        app=self.app
        app.future=None;app.revision=7
        app.book={'Sheet':{}};app.workbook_path=Path('original.xlsx')
        app.sheet=Value('Sheet');app.cell_range=Value('A1:B2');app.cache=Value(False)
        app.status=Value();app.detail=Value();app.operation_context={}
        app.controls={'sheet':{}}
        app.sheet_grid=Mock();app.page_info=Mock();app.book_label=Mock()
        app.notebook=Mock();app.worktab=object();app.root=Mock()
        app.invalidate=Mock();app.render_sheet=Mock();app.report_stage=Mock();app.show_error=Mock()
        self.jobs=[]
        def run(description,work,done,on_error=None):
            self.jobs.append((work,done,on_error));return True
        app.run=run

    def test_recipe_work_is_deferred_and_never_reads_tk_variables(self):
        with patch('gridcad_desktop.core.read_rectangle',return_value=([1,2],(1,2))) as read:
            self.assertTrue(self.app.check_recipes());read.assert_not_called()
            work,done,_=self.jobs.pop()
            # Capture is already complete: background work cannot access Tk.
            for variable in (self.app.sheet,self.app.cell_range,self.app.cache):
                variable.get=Mock(side_effect=AssertionError('worker touched Tk'))
            result=work()
            self.assertEqual(result,(2,(1,2)))
            read.assert_called_once_with(self.app.book,'Sheet','A1:B2',cache_confirmed=False)

    def test_recipe_result_rejects_changed_inputs(self):
        self.app.check_recipes();_,done,_=self.jobs.pop()
        self.app.revision+=1
        done((4,(2,2)))
        self.assertIn('changed',self.app.status.get())
        self.assertNotIn('recipes valid',self.app.status.get())

    def test_recipe_success_reports_exact_count(self):
        self.app.check_recipes();_,done,_=self.jobs.pop();done((4,(2,2)))
        self.assertIn('4 recipes valid',self.app.status.get())

    def test_busy_rejections_preserve_existing_state(self):
        original=self.app.book;self.app.future=object()
        self.assertFalse(self.app.load_workbook('other.xlsx'))
        self.assertFalse(self.app.check_recipes())
        self.app.load_example()
        self.assertIs(self.app.book,original);self.assertFalse(self.jobs)
        self.app.invalidate.assert_not_called();self.app.sheet_grid.delete.assert_not_called()

    def test_suggestions_are_computed_in_worker_and_sheet_switch_uses_cache(self):
        book={'One':{},'Two':{}}
        with patch('gridcad_desktop.core.read_workbook',return_value=book) as read, patch('gridcad_desktop.core.suggest_range',side_effect=['D4:I7','B2:C3']) as suggest:
            self.app.load_workbook('new.xlsx');read.assert_not_called();suggest.assert_not_called()
            work,done,_=self.jobs.pop();result=work()
            self.assertEqual(suggest.call_count,2);done(result)
            self.assertEqual(self.app.cell_range.get(),'D4:I7')
            self.app.sheet.set('Two');self.app.change_sheet()
            self.assertEqual(self.app.cell_range.get(),'B2:C3');self.assertEqual(suggest.call_count,2)

    def test_failed_reload_clears_stale_display_and_does_not_continue(self):
        after=Mock();self.app.load_workbook('bad.xlsx',after=after)
        _,_,failed=self.jobs.pop();failed(ValueError('malformed'))
        self.assertIsNone(self.app.book);self.assertIsNone(self.app.workbook_path)
        self.assertEqual(self.app.sheet.get(),'');self.assertEqual(self.app.cell_range.get(),'')
        self.assertEqual(self.app.controls['sheet']['values'],[])
        self.assertEqual(self.app.cell_boxes,{})
        self.app.book_label.configure.assert_called_with(text='Workbook could not be loaded. Choose another file to retry.')
        after.assert_not_called()

    def test_successful_project_load_replaces_loading_detail(self):
        app=self.app
        app.project_label=Mock();app.draw_geometry=Mock();app.geotab=object()
        for name in ('sample','labels','label_reference','orientation','label_mode'):
            setattr(app,name,Value())
        app.controls.update({key:Mock() for key in ('samples','labels','label_reference')})
        # Combobox item assignment must remain distinct from its configure call.
        from unittest.mock import MagicMock
        for key in ('samples','labels','label_reference'):app.controls[key]=MagicMock()
        app.load_project('new.print')
        self.assertIn('Reading',app.detail.get())
        _,done,_=self.jobs.pop()
        done({'groups':{'Sample':['one']},'containers':{},'leaves':[], 'nodes':{}})
        self.assertIn('Project loaded',app.detail.get())
        self.assertNotIn('Reading',app.detail.get())
        self.assertEqual(app.project_path,Path('new.print'))

    def test_example_continues_only_after_matching_success_and_idle(self):
        self.app.load_workbook=Mock();self.app.load_project=Mock()
        self.app.load_example()
        self.app.load_project.assert_not_called();self.app.root.after_idle.assert_not_called()
        path=self.app.load_workbook.call_args.args[0]
        callback=self.app.load_workbook.call_args.kwargs['after']
        book={'Recipes':{}};self.app.book=book;self.app.workbook_path=path
        callback(book)
        continuation=self.app.root.after_idle.call_args.args[0]
        self.app.load_project.assert_not_called();continuation()
        self.app.load_project.assert_called_once()

    def test_example_superseded_workbook_drops_pending_continuation(self):
        self.app.load_workbook=Mock();self.app.load_project=Mock()
        self.app.load_example()
        callback=self.app.load_workbook.call_args.kwargs['after']
        callback(self.app.book)
        continuation=self.app.root.after_idle.call_args.args[0]
        self.app.book={'Different':{}};continuation()
        self.app.load_project.assert_not_called();self.app.root.after.assert_not_called()


if __name__=='__main__':unittest.main()
