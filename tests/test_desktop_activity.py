"""Headless activity lifecycle checks; native animation is Windows acceptance."""
from concurrent.futures import Future
from queue import SimpleQueue
from unittest import TestCase, mock
from gridcad_desktop import App


class Value:
    def __init__(self, value=''): self.value = value
    def get(self): return self.value
    def set(self, value): self.value = value


class ActivityTests(TestCase):
    def app(self):
        app = App.__new__(App)
        app.root = mock.Mock(); app.pool = mock.Mock()
        app.future = None; app.file_stage = ''; app.stage_updates = SimpleQueue()
        app.render_future = None; app.render_pending = None
        app.render_paint_pending = False; app.render_stage = ''
        app.operation_context = {}; app.status = Value(); app.activity = Value()
        app.progress = mock.Mock(); app.activity_label = mock.Mock()
        app.progress_active = False; app.save_button = mock.Mock()
        app.update_save = mock.Mock(); app.show_error = mock.Mock()
        return app

    def poll(self, app):
        app.root.after.call_args.args[1]()

    def test_worker_stage_delivery_and_completion_remain_busy(self):
        app = self.app(); future = Future(); app.pool.submit.return_value = future
        seen = []
        self.assertTrue(app.run('Reading source…', lambda: None,
                                lambda result: seen.append((result, app.future is future, app.progress_active))))
        self.assertTrue(app.progress_active)
        app.report_stage('Validating geometry…')
        self.assertEqual(app.activity.get(), 'Reading source…')
        self.poll(app)
        self.assertEqual(app.activity.get(), 'Validating geometry…')
        future.set_result(17); self.poll(app)
        self.assertEqual(seen, [(17, True, True)])
        self.assertIsNone(app.future); self.assertFalse(app.progress_active)
        self.assertEqual(app.activity.get(), '')

    def test_repeat_admission_does_not_enqueue_more_work(self):
        app = self.app(); app.pool.submit.return_value = Future()
        app.run('First', lambda: None, lambda result: None)
        self.assertFalse(app.run('Second', lambda: None, lambda result: None))
        self.assertEqual(app.pool.submit.call_count, 1)
        self.assertEqual(app.file_stage, 'First')

    def test_failure_cleans_activity_before_showing_original_error(self):
        app = self.app(); future = Future(); app.pool.submit.return_value = future
        error = ValueError('bad input'); cleanup = mock.Mock()
        app.show_error.side_effect = lambda exc: self.assertFalse(app.progress_active)
        app.run('Reading', lambda: None, lambda result: None, cleanup)
        future.set_exception(error); self.poll(app)
        cleanup.assert_called_once_with(error); app.show_error.assert_called_once_with(error)
        self.assertIsNone(app.future)

    def test_completion_callback_exception_also_cleans_activity(self):
        app = self.app(); future = Future(); app.pool.submit.return_value = future
        error = RuntimeError('delivery failed')
        app.run('Reading', lambda: None, mock.Mock(side_effect=error))
        future.set_result(None); self.poll(app)
        self.assertIsNone(app.future); self.assertFalse(app.progress_active)
        app.show_error.assert_called_once_with(error)

    def test_submit_failure_is_not_stuck_busy(self):
        app = self.app(); error = RuntimeError('executor unavailable')
        app.pool.submit.side_effect = error; cleanup = mock.Mock()
        self.assertFalse(app.run('Reading', lambda: None, lambda result: None, cleanup))
        self.assertIsNone(app.future); self.assertFalse(app.progress_active)
        cleanup.assert_called_once_with(error); app.show_error.assert_called_once_with(error)

    def test_render_and_paint_keep_indicator_after_file_completion(self):
        app = self.app(); future = Future(); app.pool.submit.return_value = future
        app.run('Reading', lambda: None, lambda result: None)
        app.render_future = Future(); app.render_stage = 'Rendering sampled geometry…'
        future.set_result(None); self.poll(app)
        self.assertTrue(app.progress_active)
        self.assertEqual(app.activity.get(), 'Rendering sampled geometry…')
        app.render_future = None; app.render_paint_pending = True; app.refresh_activity()
        self.assertTrue(app.progress_active)
        app.render_paint_pending = False; app.refresh_activity()
        self.assertFalse(app.progress_active)

    def test_close_refuses_completed_worker_until_delivery_and_render_finish(self):
        for kind in ('file', 'render', 'paint'):
            app = self.app(); completed = Future(); completed.set_result(None)
            if kind == 'file': app.future = completed
            elif kind == 'render': app.render_future = completed
            else: app.render_paint_pending = True
            with mock.patch('gridcad_desktop.messagebox.showinfo') as notice:
                app.close()
            notice.assert_called_once(); app.root.destroy.assert_not_called()
            app.pool.shutdown.assert_not_called()

    def test_save_captures_paths_and_defers_success_dialog_until_delivery_finishes(self):
        app = self.app(); app.save_button = {'state': 'normal'}
        app.include_report = Value(False)
        app.proposal = {'plan': 'captured'}; app.evidence = Value('review notes')
        app.project_path = 'original.print'; app.workbook_path = 'original.xlsx'
        app.run = mock.Mock()
        with mock.patch('gridcad_desktop.filedialog.asksaveasfilename', return_value='new-result.PRINT'):
            app.save()
        _, work, done = app.run.call_args.args
        app.project_path = 'different.print'; app.workbook_path = 'different.xlsx'
        with mock.patch('gridcad_desktop.core.save_print') as save:
            work()
        save.assert_called_once_with('original.print', 'original.xlsx', {'plan': 'captured'}, 'new-result.PRINT', include_report=False)
        with mock.patch('gridcad_desktop.messagebox.showinfo') as notice:
            done({'changed_count': 3, 'unchanged_nonproject_payloads': 5})
            notice.assert_not_called()
            app.root.after_idle.call_args.args[0]()
            notice.assert_called_once()
