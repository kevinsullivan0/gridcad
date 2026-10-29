"""About navigation is explicit and never performs an update check."""
import unittest
import webbrowser
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
        for error in (OSError('unavailable'),webbrowser.Error('no browser')):
            with patch('gridcad_desktop.webbrowser.open_new_tab',side_effect=error):
                app.open_help_link(url)
            self.assertIn('Copy',app.status.set.call_args.args[0])

    def test_qa_link_points_are_actual_visible_text_not_synthetic_actions(self):
        app=self.app();app.help_document='about'
        app.help_text.winfo_ismapped.return_value=True
        app.help_text.tag_ranges.return_value=('5.16','5.58')
        app.help_text.bbox.return_value=(30,70,9,18)
        app.help_text.winfo_rootx.return_value=100
        app.help_text.winfo_rooty.return_value=200
        app.help_text.get.return_value='https://github.com/kevinsullivan0/gridcad'
        with patch('gridcad_desktop.webbrowser.open_new_tab') as browser:
            links=app.about_link_qa_points()
            self.assertEqual(links['about_project']['x'],134)
            self.assertEqual(links['about_project']['y'],279)
            self.assertEqual(links['about_project']['url'],app.help_text.get.return_value)
            browser.assert_not_called()
            app.help_text.bbox.return_value=None
            self.assertEqual(app.about_link_qa_points(),{})
            app.help_document='licenses'
            self.assertEqual(app.about_link_qa_points(),{})

    def test_help_buttons_share_manual_urls_and_do_not_open_during_build(self):
        from contextlib import ExitStack
        import gridcad_desktop as gui
        app=self.app();app.helptab=Mock();app.controls={};app.show_help=Mock()
        buttons={}
        def button(*args,**kwargs):
            widget=Mock();widget.invoke.side_effect=args[2]
            if len(args)>3:buttons[args[3]]=widget
            return widget
        app.button=Mock(side_effect=button)
        with ExitStack() as stack:
            for name in ('Frame','Label','Scrollbar'):
                stack.enter_context(patch.object(gui.ttk,name,side_effect=lambda *a,**k:Mock()))
            stack.enter_context(patch.object(gui.tk,'Text',return_value=Mock()))
            browser=stack.enter_context(patch('gridcad_desktop.webbrowser.open_new_tab',return_value=True))
            app.build_help();browser.assert_not_called()
            calls={call.args[3]:call for call in app.button.call_args_list if len(call.args)>3}
            for key,url in [('project_link','https://github.com/kevinsullivan0/gridcad'),
                            ('releases_link','https://github.com/kevinsullivan0/gridcad/releases')]:
                calls[key].args[2]();browser.assert_called_with(url)
                self.assertTrue(calls[key].kwargs['takefocus'])
                binding=buttons[key].bind.call_args
                self.assertEqual(binding.args[0],'<Return>')
                before=browser.call_count
                self.assertEqual(binding.args[1](Mock()),'break')
                buttons[key].invoke.assert_called_once()
                browser.assert_called_with(url)
                self.assertEqual(browser.call_count,before+1)
                buttons[key].bind.assert_called_once()  # Space class binding remains untouched
