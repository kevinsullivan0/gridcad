"""Ordinary input/cleanup contracts for private preview snapshots and ZIP methods."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import desktop_core as core
from tools.make_desktop_examples import create


class ProjectSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        create(self.root/'example')
        self.source=self.root/'example/DO_NOT_PRINT.PRINT'

    def test_legitimate_source_reads_one_private_snapshot_and_keeps_original_identity(self):
        original_hash=core.op.digest(self.source);read_paths=[]
        original=core.op.project_document
        def record(path):
            read_paths.append(Path(path))
            return original(path)
        with mock.patch.object(core.op,'project_document',side_effect=record):
            result=core.load_project(self.source)
        self.assertEqual(result['path'],str(self.source))
        self.assertEqual(result['sha256'],original_hash)
        self.assertEqual(core.op.digest(self.source),original_hash)
        self.assertTrue(read_paths)
        self.assertTrue(all(path!=self.source for path in read_paths))
        self.assertTrue(all(not path.exists() for path in read_paths))

    def test_private_snapshot_is_removed_after_ordinary_validation_failure(self):
        read_paths=[]
        def refused(path):
            read_paths.append(Path(path))
            raise core.op.ValidationError('unsupported source profile')
        with mock.patch.object(core.op,'project_document',side_effect=refused):
            with self.assertRaisesRegex(core.op.ValidationError,'unsupported source profile'):
                core.load_project(self.source)
        self.assertTrue(all(path!=self.source and not path.exists() for path in read_paths))
        self.assertTrue(self.source.exists())

    def test_stored_and_deflated_archives_remain_supported(self):
        for method in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):
            path=self.root/f'{method}.zip'
            with zipfile.ZipFile(path,'w',compression=method) as z:z.writestr('project.json','{}')
            with core.op.archive(path) as z:self.assertEqual(z.read('project.json'),b'{}')

    def test_other_benign_zip_methods_are_refused_before_member_read(self):
        for method in (zipfile.ZIP_BZIP2,zipfile.ZIP_LZMA):
            path=self.root/f'{method}.zip'
            with zipfile.ZipFile(path,'w',compression=method) as z:z.writestr('project.json','{}')
            with mock.patch.object(zipfile.ZipFile,'open',side_effect=AssertionError('member read not permitted')):
                with self.assertRaisesRegex(core.op.ValidationError,'compression'):
                    core.op.archive(path)
