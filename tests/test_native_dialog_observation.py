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

class NativeWindowReadiness(unittest.TestCase):
    class Window:
        def __init__(self,title,visible=True,enabled=True):
            self.title=title;self.visible=visible;self.enabled=enabled
        def window_text(self):return self.title
        def is_visible(self):return self.visible
        def is_enabled(self):return self.enabled

    def test_only_one_visible_enabled_expected_dialog_is_ready(self):
        expected=self.Window('Save PRINT as')
        for windows in ([],[self.Window('Other')],[self.Window('Save PRINT as',False)],
                        [self.Window('Save PRINT as',enabled=False)]):
            self.assertIsNone(gui.native_window_match(windows,{'Save PRINT as'}))
        self.assertIs(gui.native_window_match([self.Window('Other'),expected],{'Save PRINT as'}),expected)

    def test_multiple_expected_dialogs_are_not_an_unambiguous_action_target(self):
        with self.assertRaises(AssertionError):
            gui.native_window_match([self.Window('Save PRINT as'),self.Window('Save PRINT as')],{'Save PRINT as'})

class NativeEditRole(unittest.TestCase):
    def test_filename_and_address_are_distinct_observed_accessibility_labels(self):
        self.assertTrue(gui.native_edit_role('File name:','filename'))
        self.assertTrue(gui.native_edit_role('Address','address'))
        self.assertTrue(gui.native_edit_role('Address: Documents','address'))
        for name,role in [('File name:','address'),('Address: Documents','filename'),('','filename'),('DO_NOT_PRINT-materials','address')]:
            self.assertFalse(gui.native_edit_role(name,role))
