"""Ordinary regressions for the human-readable eight-way mapping controls."""
import unittest
import gridcad_desktop as gui
import desktop_core as core

class MappingControlsTests(unittest.TestCase):
    def test_all_eight_orientations_round_trip(self):
        choices = [gui.orientation_from_controls(corner, direction)
                   for corner, directions in gui.ROW_DIRECTIONS.items()
                   for direction in directions]
        self.assertEqual(set(choices), set(core.ORIENTATIONS))
        self.assertEqual(len(choices), 8)
        for orientation in choices:
            self.assertEqual(gui.orientation_from_controls(*gui.controls_from_orientation(orientation)), orientation)

    def test_top_left_has_both_normal_and_transposed_equivalent(self):
        self.assertEqual(gui.orientation_from_controls('Top left', 'Down'), 'Rows down; columns right')
        self.assertEqual(gui.orientation_from_controls('Top left', 'Right'), 'Rows right; columns down')

    def test_invalid_or_incomplete_selection_does_not_guess(self):
        for corner, direction in [('', ''), ('Top left', 'Up'), ('Bottom right', 'Right')]:
            self.assertEqual(gui.orientation_from_controls(corner, direction), '')
        self.assertEqual(gui.controls_from_orientation(''), ('', ''))

    def test_material_names_are_metadata_not_color_guesses(self):
        self.assertEqual(gui.material_display_name({'name':'internal', 'metadata':{'displayName':'Native name'}}), 'Native name')
        self.assertEqual(gui.material_display_name({'name':'rgba,1,2,3,255', 'metadata':{'materialType':'color_picker'}}), 'rgba,1,2,3,255')

    def test_reference_choices_exclude_picker_and_conflicting_aliases(self):
        from copy import deepcopy
        material=core.op.EcoFlexMaterialProvider().direct_black()
        def body(m): return {'material':deepcopy(m),'properties':{'threeDAppearance':{'value':deepcopy(m['threeDAppearance'])}}}
        project={'nodes':{'a':{'name':'native','material':material}},'bodies':{'a':body(material)},'leaves':{'a'}}
        self.assertEqual(list(gui.compatible_reference_info(project)), ['a'])
        picker=deepcopy(material);picker['metadata']['materialType']='color_picker'
        project['nodes']['picker']={'name':'picker','material':picker};project['bodies']['picker']=body(picker);project['leaves'].add('picker')
        self.assertEqual(gui.compatible_reference_info(project), {})
        picker['id']='other-id';project['bodies']['picker']=body(picker)
        self.assertEqual(list(gui.compatible_reference_info(project)), ['a'])
