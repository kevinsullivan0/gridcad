"""Directory evidence must come from the native address, not filename/list text."""
from pathlib import Path
import tempfile
import unittest
from tools import windows_gui_acceptance as gui


class NativeDialogObservation(unittest.TestCase):
    def test_absolute_directory_and_os_resolved_documents_alias(self):
        with tempfile.TemporaryDirectory() as folder:
            documents=Path(folder)/'redirected user documents';documents.mkdir()
            self.assertEqual(gui.directory_from_native_address(str(documents),documents),documents.resolve())
            self.assertEqual(gui.directory_from_native_address('Documents',documents),documents.resolve())

    def test_ambiguous_labels_files_and_missing_os_folder_are_not_availability(self):
        with tempfile.TemporaryDirectory() as folder:
            documents=Path(folder)/'documents';documents.mkdir()
            for value in ('Downloads','Visual Studio 18','DO_NOT_PRINT-materials',''):
                with self.subTest(value=value),self.assertRaises(AssertionError):
                    gui.directory_from_native_address(value,documents)
            with self.assertRaises(AssertionError):
                gui.directory_from_native_address('Documents',Path(folder)/'not present')
            file=Path(folder)/'file';file.write_text('not a directory')
            with self.assertRaises(AssertionError):gui.directory_from_native_address(str(file),documents)
