"""Headless callback tests, not a substitute for native Windows GUI acceptance."""
import unittest
from unittest import mock
from types import SimpleNamespace
from gridcad_desktop import App


class Value:
    def __init__(self, value=''):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class Grid:
    def __init__(self):
        self.items = {}; self.offset = (0, 0)
    def canvasx(self, x):
        return x + self.offset[0]
    def canvasy(self, y):
        return y + self.offset[1]
    def itemconfigure(self, item, **options):
        self.items[item] = options
    def focus_set(self):
        pass
    def delete(self, tag):
        self.items.clear()
    def create_rectangle(self, *coords, **options):
        item=len(self.items)+1
        self.items[item]=options
        return item
    def create_text(self, *args, **kwargs):
        pass
    def configure(self, **options):
        self.options=options
    def xview_moveto(self, value):
        pass
    def yview_moveto(self, value):
        pass


class CellSelectionTests(unittest.TestCase):
    def setUp(self):
        self.app = App.__new__(App)
        self.app.book = {'Sheet': {'B2': {'value': '0/0/0/0/100/0'}}}
        self.app.sheet = Value('Sheet')
        self.app.cell_range = Value('')
        self.app.detail = Value(); self.app.status = Value()
        self.app.selection_start = None; self.app.dragging_cells = False
        self.app.refresh_feedback=mock.Mock()
        self.app.page_row = self.app.page_col = 1
        self.app.sheet_grid = Grid()
        self.app.cell_boxes = {(r,c):(r,c) for r in range(1,31) for c in range(1,9)}

    def event(self, row, col, shift=False):
        app = self.app
        return SimpleNamespace(x=app.ROW_HEADER+(col-app.page_col)*app.CELL_WIDTH+5,
                               y=app.ROW_HEIGHT+(row-app.page_row)*app.ROW_HEIGHT+5,
                               state=1 if shift else 0)

    def test_click_selects_only_one_cell_and_next_plain_click_restarts(self):
        self.app.click_cell(self.event(2,2)); self.app.release_cells(self.event(2,2))
        self.assertEqual(self.app.cell_range.get(), 'B2:B2')
        self.assertIn('0/0/0/0/100/0', self.app.detail.get())
        self.app.click_cell(self.event(4,5))
        self.assertEqual(self.app.cell_range.get(), 'E4:E4')

    def test_shift_click_extends_rectangular_across_rows_and_columns(self):
        self.app.click_cell(self.event(4,5)); self.app.release_cells(self.event(4,5))
        self.app.click_cell(self.event(2,2,shift=True))
        self.assertEqual(self.app.cell_range.get(), 'B2:E4')
        self.app.refresh_cell_selection()
        selected = {cell for cell,style in self.app.sheet_grid.items.items() if style['fill']=='#b7d9ff'}
        self.assertEqual(selected, {(r,c) for r in range(2,5) for c in range(2,6)})

    def test_drag_and_release_stop_extending(self):
        self.app.click_cell(self.event(2,2))
        self.app.drag_cells(self.event(5,7))
        self.assertEqual(self.app.cell_range.get(), 'B2:G5')
        self.app.release_cells(self.event(6,8))
        self.app.drag_cells(self.event(9,1))
        self.assertEqual(self.app.cell_range.get(), 'B2:H6')

    def test_heading_and_row_header_are_not_cells(self):
        for x,y in [(2,40),(100,2),(5000,80),(100,5000)]:
            self.app.click_cell(SimpleNamespace(x=x,y=y,state=0))
        self.assertEqual(self.app.cell_range.get(), '')

    def test_scrolled_hit_testing_uses_canvas_coordinates(self):
        self.app.sheet_grid.offset = (150,27)
        self.app.click_cell(self.event(1,1))
        self.assertEqual(self.app.cell_range.get(), 'B2:B2')

    def test_shift_selection_across_pages(self):
        self.app.click_cell(self.event(2,2)); self.app.release_cells(self.event(2,2))
        self.app.page_row,self.app.page_col = 31,9
        self.app.cell_boxes = {(r,c):(r,c) for r in range(31,61) for c in range(9,17)}
        self.app.click_cell(self.event(33,12,shift=True))
        self.assertEqual(self.app.cell_range.get(), 'B2:L33')

    def test_typed_range_visible_and_invalid_range_clears_highlight(self):
        self.app.cell_range.set('C3:D4'); self.app.refresh_cell_selection()
        self.assertEqual(self.app.sheet_grid.items[(3,3)]['fill'], '#b7d9ff')
        self.assertEqual(self.app.sheet_grid.items[(3,2)]['fill'], 'white')
        for invalid in ('C3:', 'D4:C3', 'not a range'):
            self.app.cell_range.set(invalid); self.app.refresh_cell_selection()
            self.assertTrue(all(style['fill']=='white' for style in self.app.sheet_grid.items.values()))

    def test_manual_range_edit_replaces_stale_pointer_anchor(self):
        self.app.click_cell(self.event(7,7))
        self.app.cell_range.set('B2:D4')
        self.app.refresh_cell_selection('variable', '', 'write')
        self.assertEqual(self.app.selection_start, (2,2))
        self.assertFalse(self.app.dragging_cells)
        self.app.click_cell(self.event(6,5,shift=True))
        self.assertEqual(self.app.cell_range.get(), 'B2:E6')

    def test_last_excel_page_draws_only_bounded_valid_cells(self):
        self.app.page_row,self.app.page_col=1048547,16377
        self.app.page_info=SimpleNamespace(configure=lambda **kwargs:None)
        self.app.render_sheet()
        self.assertEqual(len(self.app.cell_boxes),240)
        self.assertEqual(max(self.app.cell_boxes),(1048576,16384))
        self.assertEqual(min(self.app.cell_boxes),(1048547,16377))

    def test_escape_clears_drag_anchor_but_keeps_rectangle(self):
        self.app.click_cell(self.event(2,2)); self.app.cancel_cell_drag()
        self.app.drag_cells(self.event(5,5))
        self.assertEqual(self.app.cell_range.get(), 'B2:B2')
        self.assertIsNone(self.app.selection_start)


    def test_large_nonrecipe_cell_detail_is_bounded_without_changing_value(self):
        original='x'*10000
        self.app.book['Sheet']['B2']['value']=original
        self.app.click_cell(self.event(2,2))
        self.assertLess(len(self.app.detail.get()),700)
        self.assertIn('display shortened',self.app.detail.get())
        self.assertEqual(self.app.book['Sheet']['B2']['value'],original)


    def test_qa_reports_clickable_intersection_for_partially_visible_cells(self):
        grid=mock.Mock()
        grid.winfo_ismapped.return_value=True
        grid.canvasx.return_value=0;grid.canvasy.return_value=0
        grid.winfo_width.return_value=955;grid.winfo_height.return_value=267
        grid.winfo_rootx.return_value=25;grid.winfo_rooty.return_value=265
        grid.coords.side_effect=lambda box: {
            'partial_right':(808,27,958,54),
            'outside':(958,27,1108,54),
            'partial_bottom':(58,243,208,270),
            'one_pixel_edge':(954,81,1104,108),
        }[box]
        grid.itemcget.return_value='white'
        self.app.sheet_grid=grid
        self.app.cell_boxes={(1,6):'partial_right',(1,7):'outside',(9,1):'partial_bottom',(3,6):'one_pixel_edge'}
        cells=self.app.worksheet_qa_cells()
        self.assertEqual(cells['F1'],{'x':833,'y':292,'w':147,'h':27,'selected':False})
        self.assertEqual(cells['A9']['h'],24)
        self.assertNotIn('G1',cells)
        self.assertNotIn('F3',cells)
        grid.canvasx.return_value=75;grid.canvasy.return_value=35
        scrolled=self.app.worksheet_qa_cells()
        self.assertEqual(scrolled['F1']['y'],265)
        self.assertEqual(scrolled['F1']['h'],19)
        self.assertEqual(scrolled['A9']['x'],25)
        self.assertEqual(scrolled['A9']['w'],133)


if __name__ == '__main__':
    unittest.main()
