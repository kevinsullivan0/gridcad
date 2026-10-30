"""Mapping completion must refresh visible selected-sample information."""
import unittest
from unittest.mock import Mock
from gridcad_desktop import App


class MappingDetailRefreshTests(unittest.TestCase):
    def app(self, selected):
        app = App.__new__(App)
        app.future = None
        app.book = {'Recipes': {}}
        app.project = {'nodes': {'sample': {'name': 'Sample', 'material': {'name': 'Source'}}}}
        app.workbook_path = 'example.xlsx'
        for name in ('sheet', 'cell_range', 'sample', 'labels', 'orientation', 'transpose',
                     'cache', 'label_mode', 'label_reference', 'replace_labels', 'summary', 'status', 'detail'):
            setattr(app, name, Mock())
        app.sheet.get.return_value = 'Recipes'
        app.container_ids = {}; app.reference_ids = {}; app.revision = 1
        app.invalidate = Mock(); app.sync_material_controls = Mock(); app.refresh_feedback=Mock(return_value={})
        app.notebook = Mock(); app.geotab = Mock(); app.mapping_tree = Mock()
        app.draw_geometry = Mock(); app.run = Mock(); app.canvas_ids = {}; app.canvas = Mock()
        app.inspected_oid = selected
        app.proposal = None
        return app

    def complete(self, app):
        app.preview()
        proposal = {'plan': {'samples': [{'action': 'replace_uniform_color_picker'}], 'labels': []},
                    'mapping': [{'id': 'sample', 'cell': 'D4', 'percentages': [2, 0, 0, 0, 98, 0],
                                 'action': 'replace_uniform_color_picker'}], 'preserved_count': 0}
        app.run.call_args.args[2](proposal)
        return proposal

    def test_selected_sample_detail_refreshes_when_mapping_completes(self):
        app = self.app('sample'); proposal = self.complete(app)
        self.assertIn('Recipes!D4 requested', app.detail.set.call_args.args[0])
        self.assertEqual(app.mapping_tree.insert.call_args.kwargs['values'][-2], 'Apply worksheet recipe')
        self.assertEqual(proposal['mapping'][0]['action'], 'replace_uniform_color_picker')

    def test_no_selected_sample_gets_current_mapping_hint(self):
        app = self.app(None); self.complete(app)
        self.assertIn('Click a sample', app.detail.set.call_args.args[0])
        self.assertNotIn('build a new mapping', app.detail.set.call_args.args[0])
