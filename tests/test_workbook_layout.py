"""Layout allocation contracts, not a substitute for Windows screenshot review."""
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import desktop_core as core
import gridcad_desktop as gui
from tools.windows_gui_acceptance import make_progress_workbook, PROGRESS_RECIPE_COUNT


class WorkbookLayoutTests(unittest.TestCase):
    def test_navigation_and_cache_consent_have_reserved_rows(self):
        app=gui.App.__new__(gui.App)
        app.worktab=mock.Mock();app.controls={}
        for name in ('sheet','cell_range','transpose','cache'):setattr(app,name,mock.Mock())
        app.button=mock.Mock(side_effect=lambda *args,**kwargs:mock.Mock())
        frames=[]
        def frame(*args,**kwargs):
            widget=mock.Mock();frames.append(widget);return widget
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(gui.ttk,'Frame',side_effect=frame))
            for name in ('Label','Combobox','Entry','Checkbutton','Scrollbar'):
                stack.enter_context(mock.patch.object(gui.ttk,name,side_effect=lambda *a,**k:mock.Mock()))
            stack.enter_context(mock.patch.object(gui.tk,'Canvas',side_effect=lambda *a,**k:mock.Mock()))
            app.build_workbook()
        app.worktab.rowconfigure.assert_called_once_with(2,weight=1)
        self.assertEqual(frames[1].grid.call_args.kwargs['row'],2)
        self.assertEqual(frames[2].grid.call_args.kwargs['row'],3)
        self.assertEqual(app.controls['cache'].grid.call_args.kwargs['row'],4)
        for frame in frames:frame.pack.assert_not_called()
        app.controls['cache'].pack.assert_not_called()

    def test_geometry_review_controls_have_reserved_rows(self):
        app=gui.App.__new__(gui.App)
        app.geotab=mock.Mock();app.controls={}
        labels=[]
        for name in ('sample','labels','orientation','label_mode','label_reference',
                     'replace_labels','summary','preview_notice','reviewed','material_ack'):
            setattr(app,name,mock.Mock())
        app.button=mock.Mock(side_effect=lambda *args,**kwargs:mock.Mock())
        frames=[]
        def frame(*args,**kwargs):
            widget=mock.MagicMock();frames.append(widget);return widget
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(gui.ttk,'Frame',side_effect=frame))
            def label(*args,**kwargs):
                labels.append((args,kwargs));return mock.MagicMock()
            stack.enter_context(mock.patch.object(gui.ttk,'Label',side_effect=label))
            for name in ('Combobox','Entry','Checkbutton','Scrollbar'):
                stack.enter_context(mock.patch.object(gui.ttk,name,side_effect=lambda *a,**k:mock.MagicMock()))
            stack.enter_context(mock.patch.object(gui.tk,'Canvas',side_effect=lambda *a,**k:mock.Mock()))
            app.build_geometry()
        app.geotab.rowconfigure.assert_called_once_with(0,weight=1)
        self.assertEqual(frames[0].grid.call_args.kwargs['row'],0)
        self.assertEqual(frames[7].grid.call_args.kwargs['row'],1)
        self.assertEqual(app.controls['geometry_settings'].grid.call_args.kwargs['row'],0)
        self.assertEqual(app.controls['reviewed'].grid.call_args.kwargs['row'],1)
        self.assertEqual(frames[8].grid.call_args.kwargs['row'],2)
        self.assertEqual(app.controls['material_ack'].grid.call_args.kwargs['row'],3)
        for frame in frames:frame.pack.assert_not_called()
        app.controls['material_ack'].pack.assert_not_called()
        # Arbitrarily long normal summaries/notices grow only scroll content,
        # never the outer geometry or the reserved review rows.
        for value in (app.summary,app.preview_notice):
            matching=[(args,kw) for args,kw in labels if kw.get('textvariable') is value]
            self.assertEqual(len(matching),1)
            self.assertIs(matching[0][0][0],frames[2])
            self.assertEqual(matching[0][1]['wraplength'],345)
        configuration=frames[2]
        focus=next(call.args[1] for call in configuration.bind.call_args_list if call.args[0]=='<FocusIn>')
        configuration.winfo_rooty.return_value=100
        configuration.winfo_height.return_value=900
        viewport=app.controls['geometry_settings']
        viewport.canvasy.return_value=0;viewport.winfo_height.return_value=200
        widget=mock.Mock();widget.winfo_rooty.return_value=500;widget.winfo_height.return_value=20
        focus(mock.Mock(widget=widget))
        viewport.yview_moveto.assert_called_once_with(220/900)



    def test_progress_workbook_is_valid_under_unchanged_xml_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'progress.xlsx'
            make_progress_workbook(path)
            book=core.read_workbook(path)
            self.assertEqual(len(book['Recipes']),PROGRESS_RECIPE_COUNT)
            self.assertEqual(core.suggest_range(book['Recipes']),f'A1:A{PROGRESS_RECIPE_COUNT}')
            values,shape=core.read_rectangle(book,'Recipes','A1:A10')
            self.assertEqual(shape,(10,1));self.assertEqual(len(values),10)
