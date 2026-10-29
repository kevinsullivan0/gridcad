"""Performance regressions retain validation, isolation, and payload preservation."""
import copy
import hashlib
import math
import random
from array import array
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import desktop_core as core
from tools.make_desktop_examples import create


class PerformanceContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        create(self.root / 'input')
        self.path = self.root / 'input/DO_NOT_PRINT.PRINT'
        self.xlsx = self.root / 'input/DO_NOT_PRINT.xlsx'

    def proposal(self):
        project = core.load_project(self.path)
        reference = sorted(project['containers']['synthetic-labels']['leaves'])[0]
        proposal = core.propose(project, self.xlsx, core.read_workbook(self.xlsx),
            'Recipes', 'D4:I7', 'Sample', 'synthetic-labels',
            'Rows down; columns right', label_mode='reference', label_reference=reference)
        return core.confirm(proposal, 'Synthetic labels and corners reviewed.')

    def test_one_provider_still_checks_each_recipe(self):
        book = core.read_workbook(self.xlsx)
        provider = core.op.EcoFlexMaterialProvider()
        with mock.patch.object(core.op, 'EcoFlexMaterialProvider', return_value=provider) as ctor, \
                mock.patch.object(provider, 'sample', wraps=provider.sample) as sample:
            core.read_rectangle(book, 'Recipes', 'D4:I7')
        self.assertEqual(ctor.call_count, 1)
        self.assertEqual(sample.call_count, 24)

    def test_reference_validation_is_local_and_assignments_are_independent(self):
        plan = self.proposal()
        with mock.patch.object(core.op, 'native_reference_material', wraps=core.op.native_reference_material) as validate:
            result = core.op.prepare(self.path, self.xlsx, plan)
            self.assertEqual(validate.call_count, 1)
            core.op.prepare(self.path, self.xlsx, plan)
            self.assertEqual(validate.call_count, 2)  # No stale cache between operations.
        labels = [x for x in result[2] if x['role'] == 'label']
        self.assertGreater(len(labels), 1)
        before = copy.deepcopy(labels[1]['reference_material'])
        labels[0]['reference_material']['metadata']['displayName'] = 'test mutation'
        self.assertEqual(labels[1]['reference_material'], before)

    def test_each_reference_fingerprint_still_checked(self):
        plan = self.proposal()
        plan['labels'][1]['reference_material_sha256'] = '0' * 64
        with self.assertRaisesRegex(core.op.ValidationError, 'reference material changed'):
            core.op.prepare(self.path, self.xlsx, plan)

    def test_payloads_stream_and_preserve_metadata_and_bytes(self):
        payload = bytes(range(256)) * 32768  # 8 MiB, deliberately beyond chunk size.
        info = zipfile.ZipInfo('opaque/unchanged.bin', date_time=(2020, 2, 3, 4, 5, 6))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.comment = b'preserve member comment'
        info.external_attr = 0o100600 << 16
        with zipfile.ZipFile(self.path, 'a') as archive:
            archive.comment = b'preserve archive comment'
            archive.writestr(info, payload)
        plan = self.proposal()
        original_read = zipfile.ZipFile.read
        def bounded_read(archive, member, *args, **kwargs):
            name = member.filename if isinstance(member, zipfile.ZipInfo) else member
            self.assertNotEqual(name, info.filename, 'Opaque payload must never be read all at once')
            return original_read(archive, member, *args, **kwargs)
        with mock.patch.object(zipfile.ZipFile, 'read', bounded_read):
            core.op.apply(self.path, self.xlsx, plan, self.root/'result')
        with zipfile.ZipFile(self.path) as source, zipfile.ZipFile(self.root/'result/candidate_UNVERIFIED.PRINT') as output:
            self.assertEqual(source.namelist(), output.namelist())
            self.assertEqual(source.comment, output.comment)
            a, b = source.getinfo(info.filename), output.getinfo(info.filename)
            for name in ('date_time', 'compress_type', 'comment', 'extra', 'external_attr', 'internal_attr', 'create_system', 'file_size', 'CRC'):
                self.assertEqual(getattr(a, name), getattr(b, name), name)
            self.assertEqual(hashlib.sha256(output.read(info.filename)).digest(), hashlib.sha256(payload).digest())

    def test_stored_member_crc_failure_cleans_staging_without_touching_inputs(self):
        with zipfile.ZipFile(self.path, 'a') as archive:
            archive.writestr('opaque/stored.bin', b'A' * (2 * 1024 * 1024),
                             compress_type=zipfile.ZIP_STORED)
        with zipfile.ZipFile(self.path) as archive:
            info = archive.getinfo('opaque/stored.bin')
        with self.path.open('r+b') as stream:
            stream.seek(info.header_offset + 26)
            name_length, extra_length = struct.unpack('<HH', stream.read(4))
            stream.seek(info.header_offset + 30 + name_length + extra_length)
            stream.write(b'B')  # Deliberately wrong CRC, not an unsafe ZIP member.
        plan = self.proposal()
        original_hash = core.op.digest(self.path)
        with self.assertRaises(zipfile.BadZipFile):
            core.op.apply(self.path, self.xlsx, plan, self.root/'failed-result')
        self.assertEqual(core.op.digest(self.path), original_hash)
        self.assertFalse((self.root/'failed-result').exists())
        self.assertEqual(list(self.root.glob('.gridcad-operator-*')), [])

    def test_mesh_bounds_and_top_match_original_scalar_order(self):
        rng = random.Random(517)
        triangles = [(0., 0., 1., -0., 0., 0., 1., 0., 2., 0., 1., 2.)]
        for _ in range(500):
            triangles.append(tuple(rng.choice((-0., 0., 1e-40, -1e-40, 1e6, -1e6, rng.uniform(-100, 100))) for _ in range(12)))
        raw = bytes(80) + struct.pack('<I', len(triangles)) + b''.join(struct.pack('<12fH', *t, 0) for t in triangles)
        lo, hi = [math.inf]*3, [-math.inf]*3
        for values in struct.iter_unpack('<12fH', raw[84:]):
            for k in range(3):
                lo[k] = min(lo[k], *values[3+k:12:3])
                hi[k] = max(hi[k], *values[3+k:12:3])
        top = array('f')
        for v in struct.iter_unpack('<12fH', raw[84:]):
            if min(v[5], v[8], v[11]) >= hi[2] - 0.0001:
                top.extend((v[3], v[4], v[6], v[7], v[9], v[10]))
        actual = core._mesh(raw)
        self.assertEqual(struct.pack('<6d', *actual['bounds'][0], *actual['bounds'][1]), struct.pack('<6d', *lo, *hi))
        self.assertEqual(actual['top'].tobytes(), top.tobytes())

    def test_mesh_accepts_original_numeric_contract(self):
        with zipfile.ZipFile(self.path) as archive:
            name = next(n for n in archive.namelist() if n.endswith('.stl'))
            raw = archive.read(name)
        mesh = core._mesh(raw)
        self.assertEqual(mesh['sha256'], hashlib.sha256(raw).hexdigest())
        bad = bytearray(raw)
        struct.pack_into('<f', bad, 84, float('nan'))
        with self.assertRaisesRegex(core.op.ValidationError, 'Nonfinite'):
            core._mesh(bad)
        with self.assertRaises(core.op.ValidationError):
            core._mesh(raw[:-1])


if __name__ == '__main__':
    unittest.main()
