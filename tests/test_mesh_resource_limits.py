"""Bound instance-owned previews without allocating hostile-size test geometry."""
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

    def test_exact_instance_budget_preserves_every_preview(self):
        path = self.shared_project()
        expected = core.load_project(path)
        limit = self.body_count * self.mesh['triangles']
        with mock.patch.object(core, 'MAX_INSTANCE_TRIANGLES', limit):
            actual = core.load_project(path)
        self.assertEqual(set(actual['records']), set(expected['records']))
        for oid, record in expected['records'].items():
            self.assertEqual(actual['records'][oid], record)
        self.assertEqual(len({id(record['top']) for record in actual['records'].values()}), self.body_count)

    def test_cache_hits_reject_before_any_body_transform_or_array(self):
        path = self.shared_project()
        source_hash = core.op.digest(path)
        with mock.patch.object(core, 'MAX_INSTANCE_TRIANGLES', 3 * self.mesh['triangles']), \
                mock.patch.object(core, '_mesh', wraps=core._mesh) as mesh, \
                mock.patch.object(core.itertools, 'product', wraps=core.itertools.product) as transform_corners, \
                mock.patch.object(core, 'array', wraps=array) as allocate:
            with self.assertRaisesRegex(core.op.ValidationError, '^Resource limit:.*all body instances'):
                core.load_project(path)
        self.assertEqual(mesh.call_count, 1)
        self.assertEqual(transform_corners.call_count, 0)
        self.assertEqual(sum(call.args[0] == 'd' for call in allocate.call_args_list), 0)
        self.assertEqual(core.op.digest(path), source_hash)

    def test_distinct_tessellation_keys_and_path_aliases_still_charge_instances(self):
        path = self.shared_project(aliases=True)
        with mock.patch.object(core, 'MAX_INSTANCE_TRIANGLES', self.mesh['triangles']), \
                mock.patch.object(core, '_mesh', wraps=core._mesh) as mesh:
            with self.assertRaisesRegex(core.op.ValidationError, 'all body instances'):
                core.load_project(path)
        self.assertEqual(mesh.call_count, 1)

    def test_default_budget_rejects_amplification_of_one_large_declared_mesh(self):
        # A focused substitute for a 30 MiB / 600,000-triangle mesh. Keep its
        # valid tiny preview so the test exercises accounting, not exhaustion.
        path = self.shared_project()
        mesh = dict(self.mesh, triangles=600_000)
        self.assertEqual(core.MAX_INSTANCE_TRIANGLES, 8_000_000)
        with mock.patch.object(core, '_mesh', return_value=mesh) as parse, \
                mock.patch.object(core, 'array', wraps=array) as allocate:
            with self.assertRaisesRegex(core.op.ValidationError, '8,000,000 triangles'):
                core.load_project(path)
        self.assertEqual(parse.call_count, 1)
        self.assertEqual(sum(call.args[0] == 'd' for call in allocate.call_args_list), 0)

    def test_unique_mesh_guard_remains_independent(self):
        path = self.shared_project()
        mesh = dict(self.mesh, triangles=8_000_001)
        with mock.patch.object(core, 'MAX_INSTANCE_TRIANGLES', 16_000_000), \
                mock.patch.object(core, '_mesh', return_value=mesh), \
                mock.patch.object(core, 'array', wraps=array) as allocate:
            with self.assertRaisesRegex(core.op.ValidationError, 'Unique embedded meshes'):
                core.load_project(path)
        self.assertEqual(allocate.call_count, 0)


if __name__ == '__main__':
    unittest.main()
