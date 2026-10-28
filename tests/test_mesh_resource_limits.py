"""Bound shared preview storage and drawing work without altering source geometry."""
from array import array
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import desktop_core as core
from tools.make_desktop_examples import create


class MeshResourceLimits(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = create(self.root / 'input')
        self.original = self.folder / 'DO_NOT_PRINT.PRINT'
        self.document = core.op.project_document(self.original)
        nodes, _, bodies = core.op.index(self.document)
        first = nodes[next(iter(bodies))]
        self.mesh_key = first['tessellationKey']
        self.mesh_ref = self.document['project']['tessellationMap'][self.mesh_key]['representations']['stl']
        with zipfile.ZipFile(self.original) as archive:
            basename = self.mesh_ref.replace('\\', '/').rsplit('/', 1)[-1]
            member = next(n for n in archive.namelist() if n.rsplit('/', 1)[-1] == basename)
            self.mesh = core._mesh(archive.read(member))
        self.body_count = len(bodies)

    def shared_project(self, *, aliases=False):
        document = copy.deepcopy(self.document)
        nodes, _, bodies = core.op.index(document)
        tess = document['project']['tessellationMap']
        basename = self.mesh_ref.replace('\\', '/').rsplit('/', 1)[-1]
        if aliases:
            tess['synthetic-preview-alias'] = {'representations': {'stl': 'stored\\path\\' + basename}}
        for i, oid in enumerate(bodies):
            nodes[oid]['tessellationKey'] = 'synthetic-preview-alias' if aliases and i % 2 else self.mesh_key
        path = self.root / ('aliases.PRINT' if aliases else 'shared.PRINT')
        with zipfile.ZipFile(self.original) as source, zipfile.ZipFile(path, 'x') as output:
            for info in source.infolist():
                output.writestr(info, core.op.exact_json(document) if info.filename == 'project.json' else source.read(info))
        return path

    def test_shared_instances_keep_exact_coordinates_without_expanded_arrays(self):
        path = self.shared_project(aliases=True)
        with mock.patch.object(core, '_mesh', wraps=core._mesh) as parse, \
                mock.patch.object(core, 'array', wraps=array) as allocate:
            project = core.load_project(path)
        self.assertEqual(parse.call_count, 1)
        self.assertFalse(any(call.args[0] == 'd' for call in allocate.call_args_list))
        surfaces = [record['top'] for record in project['records'].values()]
        self.assertEqual(len({id(top._coordinates) for top in surfaces}), 1)
        for oid, record in project['records'].items():
            matrix = [float(v) for v in project['bodies'][oid]['transform']]
            expected = array('d')
            raw_top = self.mesh['top']
            for i in range(0, len(raw_top), 2):
                point = (raw_top[i], raw_top[i + 1], 0)
                expected.extend(sum(matrix[r*4+k]*point[k]*10 for k in range(3)) + matrix[r*4+3]*1000 for r in (0, 1))
            self.assertEqual(record['top'][:].tobytes(), expected.tobytes())
            self.assertEqual(record['top'][-1], expected[-1])
            with self.assertRaises(IndexError):
                _ = record['top'][len(expected)]

    def test_real_shared_geometry_above_old_instance_limit_is_bounded(self):
        path = self.shared_project(aliases=True)
        with zipfile.ZipFile(path) as source:
            members = {i.filename: source.read(i) for i in source.infolist()}
        basename = self.mesh_ref.replace('\\', '/').rsplit('/', 1)[-1]
        member = next(name for name in members if name.rsplit('/', 1)[-1] == basename)
        raw = members[member]
        # A real valid binary STL, not mocked triangle accounting. Extra top
        # faces amplify preview work without changing the exact bounds.
        import struct
        face = next(raw[i:i+50] for i in range(84, len(raw), 50)
                    if min(struct.unpack('<12fH', raw[i:i+50])[j] for j in (5, 8, 11)) == self.mesh['bounds'][1][2])
        count = 300_000
        members[member] = raw[:80] + struct.pack('<I', count) + raw[84:] + face * (count - self.mesh['triangles'])
        large = self.root / 'large-shared.PRINT'
        with zipfile.ZipFile(large, 'x', compression=zipfile.ZIP_DEFLATED) as output:
            for name, data in members.items():
                output.writestr(name, data)
        before = core.op.digest(large)
        project = core.load_project(large)
        self.assertGreater(project['preview_resources']['instance_triangles'], 8_000_000)
        self.assertLessEqual(project['preview_resources']['shared_top_bytes'], count * 24)
        budgets = core.preview_render_plan(project['records'])
        self.assertLessEqual(sum(budgets.values()), core.MAX_PREVIEW_TRIANGLES)
        self.assertTrue(all(budgets.values()))
        self.assertEqual(budgets, core.preview_render_plan(dict(reversed(list(project['records'].items())))))
        self.assertEqual(core.op.digest(large), before)

    def test_malformed_face_is_validated_even_when_not_used_for_preview(self):
        import struct
        with zipfile.ZipFile(self.original) as source:
            member = next(n for n in source.namelist() if n.endswith('.stl'))
            raw = bytearray(source.read(member))
        # The final face normal is never part of the top XY preview, but it
        # remains subject to the exact finite-coordinate source contract.
        struct.pack_into('<f', raw, len(raw) - 50, float('nan'))
        with self.assertRaisesRegex(core.op.ValidationError, 'Nonfinite'):
            core._mesh(raw)

    def test_unique_guard_fails_before_decoding_or_allocating(self):
        path = self.shared_project()
        with mock.patch.object(core, 'MAX_UNIQUE_TRIANGLES', self.mesh['triangles'] - 1), \
                mock.patch.object(core, '_mesh', wraps=core._mesh) as parse:
            with self.assertRaisesRegex(core.op.ValidationError, 'Unique embedded meshes'):
                core.load_project(path)
        parse.assert_not_called()

    def test_sampling_never_traverses_skipped_faces(self):
        class CountedSurface:
            def __init__(self):
                self.reads = []
            def __len__(self):
                return 600_000 * 6
            def __getitem__(self, i):
                self.reads.append(i)
                return i
        surface = CountedSurface()
        triangles = list(core.preview_triangles({'top': surface}, 7))
        self.assertEqual(len(triangles), 7)
        self.assertEqual(len(surface.reads), 42)
        self.assertEqual(triangles[0][0], (0, 1))
        self.assertEqual(triangles[-1][-1][-1], len(surface) - 1)
        self.assertEqual(list(core.preview_triangles({'top': surface}, 0)), [])

    def test_small_preview_is_exact_and_selected_samples_cost_nothing(self):
        project = core.load_project(self.original)
        excluded = set(project['groups']['Sample'])
        budgets = core.preview_render_plan(project['records'], excluded)
        self.assertFalse(excluded & budgets.keys())
        for oid, budget in budgets.items():
            top = project['records'][oid]['top']
            self.assertEqual(budget, len(top) // 6)
            flattened = [v for triangle in core.preview_triangles(project['records'][oid], budget)
                         for point in triangle for v in point]
            self.assertEqual(flattened, list(top))


if __name__ == '__main__':
    unittest.main()
