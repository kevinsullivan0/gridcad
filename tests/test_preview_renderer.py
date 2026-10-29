"""Pure raster and controlled-event-loop tests, not native GUI acceptance."""
from concurrent.futures import Future
from pathlib import Path
import sys
import threading
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gridcad_desktop as gui


class Value:
    def __init__(self, value=''):self.value=value
    def get(self):return self.value
    def set(self, value):self.value=value


class EventLoop:
    def __init__(self):self.callbacks=[]
    def after(self, delay, callback):self.callbacks.append(callback)
    def tick(self):self.callbacks.pop(0)()
    def drain(self):
        for _ in range(100):
            if not self.callbacks:return
            self.tick()
        raise AssertionError('Event loop failed to become idle')


class ControlledPool:
    def __init__(self):self.jobs=[]
    def submit(self, fn, *args):
        future=Future();future.set_running_or_notify_cancel()
        self.jobs.append((future,fn,args));return future
    def finish(self, index=0):
        future,fn,args=self.jobs[index]
        future.set_result(fn(*args))


class PreviewRendererTests(unittest.TestCase):
    def app(self, faces=1):
        app=gui.App.__new__(gui.App)
        app.root=EventLoop();app.pool=ControlledPool()
        app.canvas=mock.Mock();app.canvas.winfo_width.return_value=900;app.canvas.winfo_height.return_value=500
        app.preview_notice=Value();app.refresh_activity=mock.Mock();app.update_save=mock.Mock();app.show_error=mock.Mock()
        record={'id':'label','bounds':[[0,0,0],[10,10,2]],'center':[5,5,1],
                'top':[0,0,10,0,10,10]*faces}
        app.project={'sha256':'synthetic','records':{'label':record},'groups':{},
                     'containers':{'labels':{'leaves':{'label'}}}}
        app.sample=Value('Sample');app.labels=Value('Printed labels');app.container_ids={'Printed labels':'labels'}
        app.proposal=None;app.zoom=1;app.image_key=None;app.geometry_image=None
        app.render_future=app.render_pending=app.render_request=None
        app.render_cancel=app.render_target_key=None;app.render_stage='';app.render_failed=False
        app.render_paint_pending=False;app.render_paint_token=0
        return app

    def request(self, app):
        return {'records':app.project['records'],'selected':set(),'label_ids':{'label'},
                'size':(900,500),'requested':(900,500)}

    def test_dimensions_bounded_for_zoom_and_large_displays(self):
        for width,height in ((1,1),(1920,1080),(7680,4320),(1_000_000,100),(100,1_000_000)):
            for zoom in (1,2,4):
                w,h=gui.preview_image_size(width,height,zoom)
                self.assertGreaterEqual(min(w,h),100)
                self.assertLessEqual(max(w,h),gui.MAX_PREVIEW_DIMENSION)
                self.assertLessEqual(w*h,gui.MAX_PREVIEW_PIXELS)
        self.assertEqual(gui.preview_image_size(900,500,2),(1800,1000))

    def test_sampling_notice_and_only_budgeted_polygons(self):
        app=self.app(3)
        with mock.patch.object(gui.core,'preview_render_plan',return_value={'label':1}), \
                mock.patch.object(gui.ImageDraw,'Draw') as draw:
            result=gui.raster_geometry(self.request(app),threading.Event())
        self.addCleanup(result['image'].close)
        self.assertEqual(draw.return_value.polygon.call_count,1)
        self.assertIn('Sampled top-surface preview: 1 of 3 triangles',result['notice'])
        self.assertIn('Check unclear labels in the original project',result['notice'])

    def test_large_overlapping_faces_obey_pixel_work_budget(self):
        with mock.patch.object(gui,'MAX_PREVIEW_PIXEL_WORK',400_000), \
                mock.patch.object(gui.ImageDraw,'Draw') as draw:
            result=gui.raster_geometry(self.request(self.app(100)),threading.Event())
        self.addCleanup(result['image'].close)
        self.assertEqual(draw.return_value.polygon.call_count,2)
        self.assertEqual(result['shown'],2)
        self.assertIn('keep the preview responsive',result['notice'])

    def test_empty_surfaces_and_capped_raster_are_disclosed(self):
        request=self.request(self.app(0));request['requested']=(3600,2000)
        result=gui.raster_geometry(request,threading.Event());self.addCleanup(result['image'].close)
        self.assertIn('1 objects have no top-facing surface',result['notice'])
        self.assertIn('image size is limited',result['notice'])

    def test_cancel_before_allocation_and_during_raster_closes_image(self):
        event=threading.Event();event.set()
        with mock.patch.object(gui.Image,'new') as create:
            self.assertIsNone(gui.raster_geometry(self.request(self.app()),event))
            create.assert_not_called()
        event.clear();image=mock.Mock()
        def cancel(*args,**kwargs):event.set()
        with mock.patch.object(gui.Image,'new',return_value=image), \
                mock.patch.object(gui.ImageDraw,'Draw') as draw:
            draw.return_value.polygon.side_effect=cancel
            self.assertIsNone(gui.raster_geometry(self.request(self.app(1000)),event))
        image.close.assert_called_once()
        self.assertLessEqual(draw.return_value.polygon.call_count,128)

    def test_loading_keeps_notice_height_stable_until_new_pixels_arrive(self):
        app=self.app();previous='Previous completed preview details. '*12
        app.preview_notice.set(previous);app.draw_geometry()
        self.assertEqual(app.preview_notice.get(),previous)
        app.zoom=4;app.draw_geometry()
        self.assertEqual(app.preview_notice.get(),previous)
        app.pool.finish();app.root.tick();app.pool.finish(1)
        with mock.patch.object(gui.ImageTk,'PhotoImage'):app.root.drain()
        self.assertNotEqual(app.preview_notice.get(),previous)
        self.assertIn('All available',app.preview_notice.get())

    def test_scheduling_is_async_coalesces_and_discards_stale_success(self):
        app=self.app();app.draw_geometry()
        self.assertEqual(len(app.pool.jobs),1)
        app.canvas.create_image.assert_not_called()
        for zoom in (2,4,1,2,4):app.zoom=zoom;app.draw_geometry()
        self.assertEqual(len(app.pool.jobs),1)
        self.assertEqual(app.render_pending['size'],(3600,2000))
        stale={'image':mock.Mock()}
        app.pool.jobs[0][0].set_result(stale)
        app.root.tick()
        stale['image'].close.assert_called_once()
        self.assertEqual(len(app.pool.jobs),2)
        app.pool.finish(1)
        with mock.patch.object(gui.ImageTk,'PhotoImage') as photo:
            app.root.drain()
            photo.assert_called_once()
        self.assertEqual(app.image_key[1:3],(3600,2000))
        self.assertFalse(app.render_paint_pending)
        self.assertIsNone(app.render_future)
        self.assertIsNone(app.render_pending)
        self.assertIn('All available',app.preview_notice.get())
        app.show_error.assert_not_called()

    def test_stale_errors_ignored_current_errors_reported_and_activity_clears(self):
        app=self.app();app.draw_geometry();app.zoom=2;app.draw_geometry()
        app.pool.jobs[0][0].set_exception(ValueError('stale'))
        app.root.tick();app.show_error.assert_not_called()
        app.pool.jobs[1][0].set_exception(ValueError('current'))
        app.root.drain();app.show_error.assert_called_once()
        self.assertIsNone(app.render_future);self.assertFalse(app.render_paint_pending)
        self.assertEqual(app.render_stage,'')
        self.assertIn('preview failed',app.preview_notice.get())
        app.update_save.assert_called()

    def test_photo_failure_cleans_state_before_modal_and_retry_clears_failure(self):
        app=self.app();app.draw_geometry();app.pool.finish()
        def modal(exc):
            self.assertTrue(app.render_failed)
            self.assertIsNone(app.image_key);self.assertIsNone(app.geometry_image)
            self.assertFalse(app.render_paint_pending);self.assertIsNone(app.render_future)
            app.refresh_activity.assert_called();app.update_save.assert_called()
        app.show_error.side_effect=modal
        with mock.patch.object(gui.ImageTk,'PhotoImage',side_effect=RuntimeError('upload failed')):
            app.root.drain()
        self.assertTrue(app.render_failed)
        app.draw_geometry();app.pool.finish(1)
        with mock.patch.object(gui.ImageTk,'PhotoImage'):app.root.drain()
        self.assertFalse(app.render_failed)

    def test_paint_failure_invalidates_cache_and_activity(self):
        app=self.app();app.project['groups']['Sample']=['label'];app.draw_geometry();app.pool.finish()
        app.canvas.create_rectangle.side_effect=RuntimeError('canvas failed')
        with mock.patch.object(gui.ImageTk,'PhotoImage'):app.root.drain()
        self.assertTrue(app.render_failed);self.assertFalse(app.render_paint_pending)
        self.assertIsNone(app.image_key);self.assertIsNone(app.geometry_image)
        self.assertIn('outlines could not finish',app.preview_notice.get())
        app.show_error.assert_called_once()

    def test_cached_canvas_install_failure_also_invalidates_preview(self):
        app=self.app();app.draw_geometry();app.pool.finish()
        with mock.patch.object(gui.ImageTk,'PhotoImage'):app.root.drain()
        app.canvas.create_image.side_effect=RuntimeError('cached canvas install failed')
        app.draw_geometry()
        self.assertTrue(app.render_failed);self.assertIsNone(app.image_key)
        self.assertFalse(app.render_paint_pending);app.show_error.assert_called_once()

    def test_failed_project_reload_clears_previous_pixels_and_choices(self):
        app=self.app();app.future=None;app.project_path=Path('old.print')
        app.controls={name:{} for name in ('samples','labels','label_reference')}
        app.reference_ids={'old':'reference'};app.label_reference=Value('old')
        app.orientation=Value('old');app.detail=Value();app.project_label=mock.Mock()
        app.invalidate=mock.Mock();jobs=[]
        app.run=lambda description,work,done,failed:jobs.append((work,done,failed))
        after=mock.Mock();app.load_project('bad.print',after=after)
        jobs[0][2](ValueError('malformed'))
        self.assertIsNone(app.project);self.assertIsNone(app.project_path)
        self.assertIsNone(app.image_key);self.assertIsNone(app.geometry_image)
        self.assertFalse(app.container_ids);self.assertFalse(app.reference_ids)
        for control in app.controls.values():self.assertEqual(control['values'],())
        self.assertEqual(app.sample.get(),'');self.assertEqual(app.labels.get(),'')
        self.assertEqual(app.preview_notice.get(),'');after.assert_not_called()
        app.project_label.configure.assert_called_with(text='Project not loaded — choose a supported source to retry.')

    def test_clear_project_cancels_pending_and_never_installs_old_pixels(self):
        app=self.app();app.draw_geometry();app.zoom=2;app.draw_geometry()
        app.project=None;app.draw_geometry()
        app.pool.finish();app.root.drain()
        self.assertIsNone(app.image_key);self.assertIsNone(app.render_pending)
        app.canvas.create_image.assert_not_called()
        self.assertEqual(app.preview_notice.get(),'')

    def test_cached_redraw_uses_batched_main_thread_overlays_only(self):
        app=self.app();app.project['groups']['Sample']=['label'];app.draw_geometry();app.pool.finish()
        with mock.patch.object(gui.ImageTk,'PhotoImage'):
            app.root.tick()
            self.assertTrue(app.render_paint_pending)
            app.canvas.create_rectangle.assert_not_called()
            app.root.drain()
            self.assertEqual(app.canvas.create_rectangle.call_count,1)
            app.draw_geometry();app.root.drain()
        self.assertEqual(len(app.pool.jobs),1)
        self.assertEqual(app.canvas.create_rectangle.call_count,2)

    def test_invalidation_clears_mapping_once_and_tracks_geometry_inputs(self):
        app=self.app();app.image_key=('synthetic',900,500,'Sample','Printed labels')
        app.revision=0;app.reviewed=Value(True);app.material_ack=Value(True)
        app.replace_labels=Value(True);app.summary=Value();app.detail=Value();app.draw_geometry=mock.Mock()
        app.proposal={'mapping':[{'cell':'A1'}]};app.invalidate()
        self.assertIsNone(app.proposal);app.draw_geometry.assert_called_once()
        self.assertFalse(app.reviewed.get());app.invalidate();app.draw_geometry.assert_called_once()
        app.sample.set('Other samples');app.invalidate();self.assertEqual(app.draw_geometry.call_count,2)
        app.sample.set('Sample');app.labels.set('Other labels');app.invalidate()
        self.assertEqual(app.draw_geometry.call_count,3)
        app.labels.set('Printed labels');app.project['sha256']='different source';app.invalidate()
        self.assertEqual(app.draw_geometry.call_count,4)


if __name__=='__main__':unittest.main()
