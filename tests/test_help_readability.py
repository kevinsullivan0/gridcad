import unittest
from gridcad_desktop import help_lines
class HelpReadabilityTests(unittest.TestCase):
    def test_local_help_has_headings_without_markdown_clutter(self):
        lines=list(help_lines('# Start\n\nUse **Open workbook** and `D4:I7`.\n[Guide](https://example.test/guide)\n```sh\npython --version\n```'))
        self.assertEqual(lines[0],('Start','heading'))
        self.assertIn(('Use Open workbook and D4:I7.','body'),lines)
        self.assertIn(('Guide (https://example.test/guide)','body'),lines)
        self.assertIn(('python --version','code'),lines)
        self.assertFalse(any('```' in text for text,_ in lines))
