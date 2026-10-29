import unittest
from unittest.mock import Mock
from gridcad_desktop import App
class PreviewReadinessTests(unittest.TestCase):
    def test_scheduled_resize_counts_as_work_until_callback_runs(self):
        app=App.__new__(App);app.root=Mock();app.root.after.return_value='timer'
        app.resize_after=None;app.draw_geometry=Mock();app.refresh_activity=Mock();app.update_save=Mock()
        app.schedule_geometry_draw()
        self.assertTrue(app.geometry_busy())
        callback=app.root.after.call_args.args[1];callback()
        self.assertIsNone(app.resize_after);app.draw_geometry.assert_called_once()
    def test_direct_draw_cancels_old_scheduled_callback(self):
        app=App.__new__(App);app.root=Mock();app.resize_after='old'
        app.draw_geometry()
        app.root.after_cancel.assert_called_once_with('old')
        self.assertIsNone(app.resize_after)
