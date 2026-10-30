"""Independent real-Tk recovery contract, frozen 2026-10-30.

Run with GRIDCAD_CHECKOUT pointing at checkout and DISPLAY configured.
No production edits. No native GrabCAD/printer acceptance claimed. Save dialog
boundary is intercepted to inspect safe defaults and exercise cancellation;
actual OS-dialog acceptance remains a separate Windows release gate.
"""
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import unittest
from unittest import mock

CHECKOUT = Path(os.environ.get('GRIDCAD_CHECKOUT', str(Path(__file__).resolve().parents[1])))
sys.path.insert(0, str(CHECKOUT))
import tkinter as tk
from tkinter import ttk
import gridcad_desktop as gui
from tools.make_desktop_examples import create


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def widget_text(widget):
    try:
        value = str(widget.cget('text'))
        variable = str(widget.cget('textvariable')) if 'textvariable' in widget.keys() else ''
        return str(widget.getvar(variable)) if variable else value
    except tk.TclError:
        return ''


class RecoveryAcceptance(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest('Real Tk display unavailable: ' + str(exc))
        self.tmp = tempfile.TemporaryDirectory(prefix='GridCAD acceptance ')
        self.addCleanup(self.tmp.cleanup)
        self.app = gui.App(self.root)
        self.root.geometry('1200x850+0+0')
        self.root.update()
        self.dialog_text = []
        self.watch = True
        self.root.after(40, self.close_dialogs)
        self.addCleanup(self.shutdown)

    def shutdown(self):
        self.watch = False
        try:
            self.app.pool.shutdown(wait=True, cancel_futures=True)
            self.root.destroy()
        except tk.TclError:
            pass

    def close_dialogs(self):
        # Exercise validation itself rather than replacing show_error; capture
        # and dismiss modal recovery dialogs so baseline failures cannot hang.
        if not self.watch:
            return
        for w in list(self.root.winfo_children()):
            if isinstance(w, tk.Toplevel):
                self.dialog_text.append('\n'.join(widget_text(c) for c in descendants(w)))
                w.destroy()
        self.root.after(40, self.close_dialogs)

    def pump(self, seconds=.15):
        stop = time.monotonic() + seconds
        while time.monotonic() < stop:
            self.root.update()
            time.sleep(.01)

    def settle(self, timeout=20):
        stop = time.monotonic() + timeout
        while time.monotonic() < stop:
            self.pump(.05)
            if self.app.future is None and not self.app.geometry_busy():
                self.pump(.1)
                return
        self.fail('App did not finish file/render activity within 20 seconds')

    def visible_text(self):
        return '\n'.join(widget_text(w) for w in descendants(self.root) if w.winfo_viewable())

    def show_preview(self):
        self.app.notebook.select(self.app.geotab)
        self.pump()

    def load(self):
        self.inputs = create(Path(self.tmp.name) / 'inputs')
        self.app.load_workbook(self.inputs / 'DO_NOT_PRINT.xlsx')
        self.settle()
        self.app.load_project(self.inputs / 'DO_NOT_PRINT.PRINT')
        self.settle()
        self.show_preview()

    def choose(self, key, value):
        widget = self.app.controls[key]
        widget.set(value)
        widget.event_generate('<<ComboboxSelected>>')
        self.pump()

    def configured(self):
        self.load()
        labels = self.app.controls['labels']['values']
        self.choose('labels', next(str(v) for v in labels if 'Printed labels' in str(v)))
        self.choose('mapping_corner', 'Top left')
        self.choose('orientation', 'Down')

    def range(self, value):
        entry = self.app.controls['range']
        entry.delete(0, 'end')
        entry.insert(0, value)
        entry.event_generate('<KeyRelease>')
        self.pump()

    def match(self):
        self.app.controls['preview'].invoke()
        self.settle()

    def test_no_recalculation_checkbox(self):
        checks = [widget_text(w).lower() for w in descendants(self.root)
                  if isinstance(w, (ttk.Checkbutton, tk.Checkbutton))]
        self.assertFalse(any('recalculat' in t or 'formula results' in t for t in checks), checks)

    def test_exactly_one_help_entry(self):
        entries = [widget_text(w).strip().lower() for w in descendants(self.root)
                   if isinstance(w, (ttk.Button, tk.Button)) and widget_text(w).strip().lower() == 'help']
        for w in descendants(self.root):
            if isinstance(w, ttk.Notebook):
                entries += [str(w.tab(tab, 'text')).strip().lower() for tab in w.tabs()
                            if str(w.tab(tab, 'text')).strip().lower() == 'help']
        self.assertEqual(entries, ['help'], 'One Help entry, not button plus tab')

    def test_report_not_in_normal_footer(self):
        footer = self.app.controls['save'].master
        visible = ' '.join(widget_text(w) for w in descendants(footer) if w.winfo_viewable())
        self.assertNotIn('report', visible.lower(), visible)

    def test_schema_guidance_is_adjacent_and_explicit(self):
        self.app.notebook.select(self.app.worktab)
        self.pump()
        text = ' '.join(widget_text(w) for w in descendants(self.app.worktab) if w.winfo_viewable())
        self.assertRegex(text.lower(), r'(each|per|one) cell|cell (contains|holds)')
        self.assertRegex(text, r'C\s*/\s*M\s*/\s*Y\s*/\s*K\s*/\s*W\s*/\s*T')
        self.assertRegex(text, r'\d+(?:/\d+){5}')
        self.assertIn('100', text)

    def test_live_counts_mismatch_correction_and_recurrence(self):
        self.configured()
        self.range('D4:H7')
        self.show_preview()
        before = self.visible_text()
        self.assertRegex(before, r'\b20\b', 'Selected count must be visible before Match')
        self.assertRegex(before, r'\b24\b', 'Expected sample count must be visible before Match')
        self.match()
        text = self.visible_text()
        for token in ('20', '24', 'D4:H7', 'Recipes'):
            self.assertIn(token, text, 'Persistent actionable mismatch context missing')
        self.assertRegex(text.lower(), r'(select|choose|expand|match|range)')
        self.assertEqual(str(self.app.controls['save']['state']), 'disabled')
        self.range('D4:I7')
        self.match()
        self.assertNotEqual(str(self.app.controls['save']['state']), 'disabled')
        self.assertNotIn('D4:H7', self.visible_text(), 'Stale error after correction')
        self.range('D4:H7')
        self.assertEqual(str(self.app.controls['save']['state']), 'disabled')
        self.match()
        self.assertIn('D4:H7', self.visible_text())

    def red_is_visible(self, widget):
        # Inspect real themed colors, not implementation-specific style names.
        colors = []
        for option in ('foreground', 'background', 'fieldbackground', 'bordercolor', 'lightcolor'):
            try:
                colors.append(widget.cget(option))
            except tk.TclError:
                pass
            if isinstance(widget, ttk.Widget):
                style = widget.cget('style') or widget.winfo_class()
                colors.append(ttk.Style(self.root).lookup(style, option, widget.state()))
        for color in colors:
            if color:
                try:
                    r, g, b = self.root.winfo_rgb(str(color))
                    if r > g * 1.4 and r > b * 1.4 and r > 16000:
                        return True
                except tk.TclError:
                    pass
        # A red adjacent field label is also an accessible valid treatment.
        for peer in widget.master.winfo_children():
            if peer is widget or not peer.winfo_viewable() or not isinstance(peer, (ttk.Label, tk.Label)):
                continue
            try:
                style = peer.cget('style') or peer.winfo_class()
                color = peer.cget('foreground') or ttk.Style(self.root).lookup(style, 'foreground')
                r, g, b = self.root.winfo_rgb(color)
                if r > g * 1.4 and r > b * 1.4 and r > 16000:
                    return True
            except tk.TclError:
                pass
        return False

    def test_missing_selectors_have_text_red_and_focus_then_clear(self):
        self.load()
        keys = ('labels', 'mapping_corner', 'orientation')
        for key in keys:
            self.choose(key, '')
        self.match()
        self.show_preview()
        text = self.visible_text().lower()
        for pattern in (r'label', r'(corner|first.*cell)', r'(direction|next.*row)'):
            self.assertRegex(text, pattern)
        self.assertRegex(text, r'(choose|select|required|missing)')
        for key in keys:
            self.assertTrue(self.red_is_visible(self.app.controls[key]), key + ' has no red field treatment')
        self.assertIn(self.root.focus_get(), [self.app.controls[k] for k in keys], 'Focus must reach a missing input')
        self.assertTrue(self.root.focus_get().winfo_viewable())
        labels = self.app.controls['labels']['values']
        self.choose('labels', next(str(v) for v in labels if 'Printed labels' in str(v)))
        self.choose('mapping_corner', 'Top left')
        self.choose('orientation', 'Down')
        self.match()
        self.assertNotEqual(str(self.app.controls['save']['state']), 'disabled')
        for key in keys:
            self.assertFalse(self.red_is_visible(self.app.controls[key]), key + ' retains stale error')

    def test_current_black_choice_has_native_name_no_label_suffix_and_swatch(self):
        self.load()
        choice = self.app.controls['label_mode']
        expected = gui.material_display_name(gui.core.op.EcoFlexMaterialProvider().direct_black())
        self.assertEqual(choice.get(), expected)
        self.assertNotIn('— labels', choice.get())
        # A visible compact painted swatch next to this picker; geometry canvas
        # black label pixels do not count as a material-selection swatch.
        region = choice.master
        swatches = []
        for w in descendants(region):
            if not w.winfo_viewable():
                continue
            if isinstance(w, tk.Canvas) and w.winfo_width() <= 120 and w.winfo_height() <= 80:
                swatches += [w.itemcget(item, 'fill') for item in w.find_all()
                             if w.type(item) in ('rectangle', 'oval', 'polygon')]
            elif isinstance(w, (tk.Label, tk.Frame)) and 5 <= w.winfo_width() <= 120 and 5 <= w.winfo_height() <= 80:
                swatches.append(w.cget('background'))
        dark = []
        for color in swatches:
            if color:
                try:
                    dark.append(max(self.root.winfo_rgb(color)) < 20000)
                except tk.TclError:
                    pass
        self.assertTrue(any(dark), 'Visible black material swatch missing next to picker')

    def test_save_has_safe_default_folder_and_cancel_writes_nothing(self):
        self.configured()
        self.match()
        self.assertNotEqual(str(self.app.controls['save']['state']), 'disabled')
        before = {p: p.read_bytes() for p in self.inputs.rglob('*') if p.is_file()}
        with mock.patch.object(gui.filedialog, 'asksaveasfilename', return_value='') as dialog:
            self.app.controls['save'].invoke()
            self.pump()
        dialog.assert_called_once()
        options = dialog.call_args.kwargs
        self.assertTrue(options.get('initialdir'), 'No explicit default output folder')
        folder = Path(options['initialdir']).expanduser().resolve()
        self.assertTrue(folder.is_dir(), 'Suggested folder must exist')
        self.assertTrue(os.access(folder, os.W_OK), 'Suggested folder must be writable')
        self.assertNotEqual(folder, CHECKOUT.resolve())
        self.assertNotEqual(folder, Path.cwd().resolve())
        self.assertNotEqual(folder, self.inputs.resolve())
        self.assertNotEqual(options.get('initialfile'), 'DO_NOT_PRINT.PRINT')
        self.assertEqual(before, {p: p.read_bytes() for p in self.inputs.rglob('*') if p.is_file()})
        self.assertIsNone(self.app.future)


if __name__ == '__main__':
    unittest.main(verbosity=2)
