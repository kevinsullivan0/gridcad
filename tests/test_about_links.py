"""About navigation is explicit and never performs an update check."""
import unittest
from unittest.mock import Mock, patch
import diagnostics
from gridcad_desktop import App


class AboutLinksTests(unittest.TestCase):
    def app(self):
        app=App.__new__(App)
        app.help_text=Mock();app.help_text.search.return_value='7.0'
        app.set_help_text=Mock();app.status=Mock()
        return app

    def test_about_keeps_version_and_source_and_only_opens_on_click(self):
        app=self.app()
        with patch('gridcad_desktop.webbrowser.open_new_tab',return_value=True) as browser:
            app.show_about()
            browser.assert_not_called()
            text=app.set_help_text.call_args.args[0]
            self.assertIn(diagnostics.VERSION,text)
            self.assertIn(diagnostics.SOURCE_URL,text)
            expected=['https://github.com/kevinsullivan0/gridcad',
                      'https://github.com/kevinsullivan0/gridcad/releases']
            for url in expected:self.assertIn(url+'\n',text)
            clicks=[call.args[2] for call in app.help_text.tag_bind.call_args_list
                    if call.args[1]=='<Button-1>']
            self.assertEqual(len(clicks),2)
            for callback,url in zip(clicks,expected):
                callback(Mock());browser.assert_called_with(url)

    def test_missing_browser_offers_copyable_url_without_crashing(self):
        app=self.app()
        url='https://github.com/kevinsullivan0/gridcad/releases'
        with patch('gridcad_desktop.webbrowser.open_new_tab',return_value=False):
            app.open_help_link(url)
        self.assertIn(url,app.status.set.call_args.args[0])
        with patch('gridcad_desktop.webbrowser.open_new_tab',side_effect=OSError('unavailable')):
            app.open_help_link(url)
        self.assertIn('Copy',app.status.set.call_args.args[0])
