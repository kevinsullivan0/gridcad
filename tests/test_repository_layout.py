"""The maintained checkout exposes one desktop/core product, not retired alphas."""
import ast
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.build_windows import package_source

ROOT = Path(__file__).resolve().parents[1]
LEGACY_PATHS = (
    'grabcad_grid_ui.py', 'gridcad', 'ui', 'bootstrap',
    'launch-windows.cmd', 'setup-windows.cmd', 'requirements.txt',
    'README-REVIEW.md', 'ACCEPTANCE-AND-LIMITS.md',
    'COMPATIBILITY_GATES.md', 'REVIEW-MANIFEST.json',
)
CURRENT_MODULES = (
    'gridcad_desktop.py', 'desktop_core.py', 'desktop_cli.py',
    'diagnostics.py', 'agent_help.py',
)


class RepositoryLayoutTests(unittest.TestCase):
    def test_retired_browser_product_is_not_presented_as_current_source(self):
        for name in LEGACY_PATHS:
            with self.subTest(name=name):
                self.assertFalse((ROOT / name).exists(), name + ' belongs to tagged history')

    def test_current_modules_do_not_import_retired_browser_product(self):
        for name in CURRENT_MODULES:
            tree = ast.parse((ROOT / name).read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                           else [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
                self.assertFalse(any(module.split('.')[0] in ('gridcad', 'grabcad_grid_ui')
                                     for module in modules), name)

    def test_real_source_package_preserves_current_desktop_and_toolkit_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = package_source(ROOT, Path(temporary) / 'source.zip')
            with zipfile.ZipFile(target) as archive:
                names = set(archive.namelist())
                for name in CURRENT_MODULES + ('Start GridCAD from source.bat',
                        'tools/source_launcher.py', 'operator/gridcad_operator/operator.py',
                        'docs/DESKTOP_MANUAL.md', 'LICENSE'):
                    self.assertIn('GridCAD/' + name, names)
                for name in names:
                    self.assertFalse(name.startswith(('GridCAD/gridcad/', 'GridCAD/ui/', 'GridCAD/bootstrap/')))

    def test_ci_tracks_main_and_pull_requests_not_retired_task_branches(self):
        workflow = (ROOT / '.github/workflows/windows-desktop.yml').read_text()
        self.assertIn('    branches: [main]', workflow)
        self.assertFalse((ROOT / '.github/workflows/publish-approved.yml').exists(),
                         'The completed version-specific publisher must not remain active.')
        for old in ('windows-desktop,', 'repair/bounded-preview-cell-selection', 'release/v1.0-polish'):
            self.assertNotIn(old, workflow)


if __name__ == '__main__':
    unittest.main()
