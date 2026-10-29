import tkinter as tk
import unittest
from unittest.mock import Mock
from gridcad_desktop import App
class TabMetadataTests(unittest.TestCase):
    def test_tabs_with_different_top_edges_are_all_reported(self):
        app=App.__new__(App);app.notebook=Mock()
        app.notebook.winfo_width.return_value=400;app.notebook.winfo_height.return_value=300
        app.notebook.winfo_rootx.return_value=10;app.notebook.winfo_rooty.return_value=20
        app.notebook.select.return_value='help'
        def index(point):
            x,y=map(int,point[1:].split(','));i=x//100
            if not 0<=i<4 or not (0 if i==0 else 4)<=y<24:raise tk.TclError('not a tab')
            return i
        app.notebook.index.side_effect=index
        result=app.tab_qa_positions()
        self.assertEqual(set(result),{'worktab','geotab','maptab','helptab'})
        for i,key in enumerate(('worktab','geotab','maptab','helptab')):
            point=result[key]
            self.assertEqual(index(f"@{point['x']-10},{point['y']-20}"),i)
