"""Operate the extracted Windows EXE through real controls and native dialogs.

The optional QA state channel reports control locations/status only. All actions
below are real OS keyboard/mouse events; no backend or dialog is replaced.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.make_desktop_examples import make_workbook, create
from tools.make_reference_example import create_reference_example, REFERENCE_ID
import desktop_core as core


PROGRESS_RECIPE_COUNT = 40_000


def directory_from_native_address(value, documents):
    """Resolve only an observed native absolute address or standard shell alias.

    Windows may show its Documents known-folder name instead of its redirected
    filesystem path. The latter must come from Windows, never a guessed home.
    """
    candidate=Path(value) if value else None
    if candidate is not None and candidate.is_absolute() and candidate.is_dir():
        return candidate.resolve()
    if value=='Documents' and Path(documents).is_dir():
        return Path(documents).resolve()
    raise AssertionError('Native Save address is not an observed directory: '+repr(value))


def make_progress_workbook(path):
    # Keep real validation work, but stay below expanded XML-name/text limits.
    # 100k inline-string cells exceeded that independent guard on Windows.
    make_workbook(path,{f'A{row}':'2/0/0/0/98/0'
                        for row in range(1,PROGRESS_RECIPE_COUNT+1)},rows=0,columns=0)


def make_picker_only_example(folder):
    """Legitimate generated source with no saved direct/mixer reference."""
    folder=create(folder)
    path=folder/'DO_NOT_PRINT.PRINT'
    doc=core.op.project_document(path);nodes,leaves,bodies=core.op.index(doc)
    picker=nodes['synthetic-sample-1-1']['material']
    for oid in leaves:
        material=copy.deepcopy(picker);material['id']='picker-'+oid
        nodes[oid]['material']=material;bodies[oid]['material']=copy.deepcopy(material)
        bodies[oid]['properties']['threeDAppearance']['value']=copy.deepcopy(material['threeDAppearance'])
    temporary=folder/'picker-temp.PRINT'
    with zipfile.ZipFile(path) as source,zipfile.ZipFile(temporary,'x',compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info,core.op.exact_json(doc) if info.filename=='project.json' else source.read(info))
    temporary.replace(path)
    return folder


def main():
    if sys.platform!='win32':raise SystemExit('This acceptance requires Windows desktop interaction.')
    from pywinauto import Application, Desktop, mouse, keyboard
    from PIL import ImageGrab
    parser=argparse.ArgumentParser();parser.add_argument('--zip',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    extracted=out/'extracted package with spaces'
    with zipfile.ZipFile(a.zip) as archive:archive.extractall(extracted)
    folder=extracted/'GridCAD';exe=folder/'GridCAD.exe';example=folder/'examples/rectangular'
    statepath=out/'gui-state.json';checks=[];process=None;main_window_handle=None
    # Neither launcher may accidentally borrow the CI machine's Python install.
    packaged_environment={k:v for k,v in os.environ.items() if not k.upper().startswith('PYTHON')}
    system32=Path(os.environ['SystemRoot'])/'System32'
    packaged_environment['PATH']=str(system32)+os.pathsep+str(system32.parent)
    # Exercise the standard webbrowser handoff with a local default-browser
    # handler. Real link clicks launch cmd.exe through webbrowser; no external
    # site is contacted, and no product callback/backend is replaced.
    browser_log=out/'browser-links.txt'
    browser_handler=out/'browser-link-handler.cmd'
    browser_handler.write_text('@echo off\n>>"'+str(browser_log)+'" echo %~1\n',encoding='ascii')
    packaged_environment['BROWSER']='"'+str(system32/'cmd.exe')+'" /d /c "'+str(browser_handler)+'" "%s"'
    runtime=list(folder.rglob('python313.dll'))
    assert runtime==[folder/'_internal/python313.dll'],runtime
    assert not (folder/'advanced/_internal').exists()
    checks.append('GUI and CLI share exactly one bundled Python runtime; no separate advanced runtime')
    command=[str(folder/'GridCAD-core.exe'),'inspect','--project',str(example/'DO_NOT_PRINT.PRINT'),'--workbook',str(example/'DO_NOT_PRINT.xlsx')]
    def inspect_cli():
        result=subprocess.run(command,cwd=out,env=packaged_environment,capture_output=True,text=True,check=True,timeout=60)
        data=json.loads(result.stdout);assert data['profile']==core.PROFILE
        return data

    assert 'Copyright (c) 2026 Kevin Sullivan' in (folder/'LICENSE').read_text()
    assert 'Permission is hereby granted' in (folder/'LICENSE').read_text()
    from PIL import Image
    assert Image.open(folder/'resources/gridcad.ico').ico.sizes()=={(n,n) for n in (16,24,32,48,64,128,256)}
    import pefile
    for executable in (exe,folder/'GridCAD-core.exe'):
        pe=pefile.PE(str(executable))
        ids={entry.id for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries}
        assert 3 in ids and 14 in ids  # RT_ICON and RT_GROUP_ICON
        strings={}
        for group in getattr(pe,'FileInfo',[]):
            for entry in group:
                if entry.Key==b'StringFileInfo':
                    for table in entry.StringTable:
                        strings.update({k.decode('utf-8'):v.decode('utf-8') for k,v in table.entries.items()})
        assert strings.get('ProductVersion')==core.VERSION,strings
        assert strings.get('FileVersion')==core.VERSION+'.0',strings
        assert strings.get('CompanyName')=='Kevin Sullivan',strings
        pe.close()
    checks.append('Original multi-size Windows icon embedded in GUI and CLI PE resources; editable SVG bundled')

    def state():
        try:return json.loads(statepath.read_text(encoding='utf-8'))
        except (OSError,ValueError):return {}
    def wait(predicate,description,timeout=60):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            s=state()
            if predicate(s):checks.append(description);return s
            if process and process.poll() is not None:raise AssertionError('Application exited during '+description)
            time.sleep(.2)
        raise AssertionError(description+' timed out. Last state: '+str(state()))
    settings_keys={'samples','labels','mapping_corner','orientation','label_mode','label_reference','replace_labels'}
    def click(key):
        # Scroll the real configuration pane with OS scrollbar clicks. No synthetic
        # widget invocation or acknowledgment bypass is used for clipped items.
        for attempt in range(30):
            controls=wait(lambda s:key in s.get('controls',{}),'Control mapped: '+key)['controls']
            p=controls[key]
            if key not in settings_keys:break
            viewport=controls['geometry_settings']
            if p['y']>=viewport['y'] and p['y']+p['h']<=viewport['y']+viewport['h']:break
            scrollbar=controls['geometry_settings_scroll']
            y=scrollbar['y']+7 if p['y']<viewport['y'] else scrollbar['y']+scrollbar['h']-7
            mouse.click(coords=(scrollbar['x']+scrollbar['w']//2,y))
            time.sleep(.3)
        else:raise AssertionError('Configuration control could not be scrolled into view: '+key)
        assert p['w']>=8 and p['h']>=16,(key,p)
        # Closing a transient Tk panel can leave Windows without an active
        # child focus. Activate the owning top-level before the one action
        # click, rather than letting that click be consumed by activation or
        # retrying a command whose outcome could be uncertain.
        import win32gui, win32process
        point=(p['x']+p['w']//2,p['y']+p['h']//2)
        target=win32gui.GetAncestor(win32gui.WindowFromPoint(point),2)
        assert win32process.GetWindowThreadProcessId(target)[1]==process.pid,(key,target)
        Application(backend='win32').connect(process=process.pid).window(handle=target).set_focus()
        wait(lambda s:win32gui.GetForegroundWindow()==target,
             'Owning window foreground before one OS action click: '+key)
        mouse.click(coords=point);time.sleep(.25)
    def check_tab_bounds(keys,minimums=None):
        controls=state()['controls'];tab=controls['tabs']
        for key in keys:
            p=controls[key]
            assert p['x']>=tab['x'] and p['y']>=tab['y']+20,(key,p,tab)
            assert p['x']+p['w']<=tab['x']+tab['w'] and p['y']+p['h']<=tab['y']+tab['h'],(key,p,tab)
            width,height=(minimums or {}).get(key,(8,16))
            assert p['w']>=width and p['h']>=height,(key,p)
        checks.append('Fully visible usable tab controls: '+', '.join(keys))
    def cell_point(address):
        cell=wait(lambda s:address in s.get('worksheet_cells',{}),
                  'Worksheet cell visible: '+address)['worksheet_cells'][address]
        return (cell['x']+cell['w']//2,cell['y']+cell['h']//2)
    def click_cell(address,shift=False):
        point=cell_point(address)
        if shift:keyboard.send_keys('{VK_SHIFT down}')
        try:mouse.click(coords=point)
        finally:
            if shift:keyboard.send_keys('{VK_SHIFT up}')
        time.sleep(.3)
    def drag_cells(first,last):
        start,end=cell_point(first),cell_point(last)
        mouse.press(coords=start)
        try:
            for step in range(1,11):
                mouse.move(coords=(start[0]+(end[0]-start[0])*step//10,
                                   start[1]+(end[1]-start[1])*step//10))
                time.sleep(.05)
        finally:mouse.release(coords=end)
        time.sleep(.3)
    def selected_cells():
        return {address for address,cell in state().get('worksheet_cells',{}).items() if cell['selected']}
    def select_combo(key,index):
        click(key);keyboard.send_keys('{ESC}');keyboard.send_keys('%{DOWN}');time.sleep(.3)
        keyboard.send_keys('{HOME}{UP 50}');keyboard.send_keys('{DOWN}'*index+'{ENTER}');time.sleep(.4)
        snapshot=state()
        if key=='labels':expected=snapshot['label_choices'][index]
        elif key=='label_reference':expected=snapshot['reference_choices'][index]
        elif key=='label_mode':expected=snapshot['material_choices'][index]
        elif key=='mapping_corner':expected=['Top left','Top right','Bottom left','Bottom right'][index]
        else:expected={'Top left':['Down','Right'],'Top right':['Down','Left'],
                       'Bottom left':['Up','Right'],'Bottom right':['Up','Left']}[snapshot['mapping_corner']][index]
        state_key='mapping_direction' if key=='orientation' else 'material_choice' if key=='label_mode' else key
        wait(lambda s:s.get(state_key)==expected,'Explicit combobox selection: '+expected)
    def choose_top_left_rows_down():
        select_combo('mapping_corner',0);select_combo('orientation',0)
    def click_sample(oid):
        sample=wait(lambda s:not s.get('busy') and oid in s.get('geometry_samples',{}),
                    'Preview sample visible: '+oid)['geometry_samples'][oid]
        point=(sample['x']+sample['w']//2,sample['y']+sample['h']//2)
        checks.append(f'Preview OS click target: {oid} at {point}; ready rectangle {sample}')
        mouse.click(coords=point)
        time.sleep(.3)
    def select_tab(key):
        point=wait(lambda s:key in s.get('tab_positions',{}),'Visible notebook tab: '+key)['tab_positions'][key]
        mouse.click(coords=(point['x'],point['y']));time.sleep(.4)
    def geometry_tab():select_tab('geotab')
    def worksheet_tab():select_tab('worktab')
    def enter(key,text):
        click(key);keyboard.send_keys('^a',vk_packet=False);keyboard.send_keys(str(text),with_spaces=True,vk_packet=True);time.sleep(.2)
    def focused_native_edit():
        import ctypes
        from ctypes import wintypes
        import win32gui, win32process
        class GUIThreadInfo(ctypes.Structure):
            _fields_=[('cbSize',wintypes.DWORD),('flags',wintypes.DWORD),
                      ('hwndActive',wintypes.HWND),('hwndFocus',wintypes.HWND),
                      ('hwndCapture',wintypes.HWND),('hwndMenuOwner',wintypes.HWND),
                      ('hwndMoveSize',wintypes.HWND),('hwndCaret',wintypes.HWND),
                      ('rcCaret',wintypes.RECT)]
        info=GUIThreadInfo();info.cbSize=ctypes.sizeof(info)
        get_info=ctypes.windll.user32.GetGUIThreadInfo
        get_info.argtypes=[wintypes.DWORD,ctypes.POINTER(GUIThreadInfo)]
        get_info.restype=wintypes.BOOL
        if not get_info(0,ctypes.byref(info)) or not info.hwndFocus:
            raise AssertionError('Native file dialog has no observable foreground focus')
        assert win32process.GetWindowThreadProcessId(info.hwndFocus)[1]==process.pid
        assert win32gui.GetClassName(info.hwndFocus)=='Edit',win32gui.GetClassName(info.hwndFocus)
        return Desktop(backend='uia').window(handle=info.hwndFocus).wrapper_object()
    def dialog_path(path):
        # Real filename paste and read-back, never a mocked file chooser.
        import win32clipboard
        time.sleep(.7)
        keyboard.send_keys('%n',vk_packet=False);time.sleep(.2)
        edit=focused_native_edit()
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(str(path))
        finally:win32clipboard.CloseClipboard()
        observed=[]
        for attempt in range(2):
            edit.click_input()
            keyboard.send_keys('^a',vk_packet=False)
            keyboard.send_keys('^v',vk_packet=False)
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                value=edit.get_value()
                if value==str(path):break
                time.sleep(.1)
            observed.append(value)
            if value==str(path):break
        checks.append('Native filename field read-back before Enter: '+repr(observed))
        assert value==str(path),'Native filename input did not receive complete clipboard path: '+repr(observed)
        keyboard.send_keys('{ENTER}',vk_packet=False);time.sleep(.5)
    def dialog_folder():
        from win32com.shell import shell, shellcon
        time.sleep(.6);keyboard.send_keys('%d',vk_packet=False);time.sleep(.3)
        # Read the keyboard-focused native ADDRESS edit, not arbitrary list
        # or filename edits that could happen to contain a directory name.
        value=focused_native_edit().get_value()
        documents=shell.SHGetFolderPath(0,shellcon.CSIDL_PERSONAL,None,0)
        location=directory_from_native_address(value,documents)
        checks.append('Native Save address read-back: '+repr(value)+
                      '; Windows-known-folder resolution: '+str(location))
        keyboard.send_keys('{ESC}',vk_packet=False);keyboard.send_keys('%n',vk_packet=False)
        return location

    def dismiss():
        time.sleep(.3)
        if 'diagnostic_close' in state().get('controls',{}):
            click('diagnostic_close');wait(lambda s:'diagnostic_close' not in s.get('controls',{}),'Diagnostic dialog closes and ordinary workflow resumes')
        else:keyboard.send_keys('{ENTER}');time.sleep(.3)
    def screenshot(name):ImageGrab.grab().save(out/name)
    def load_book(path):
        click('open_workbook');dialog_path(path)
        wait(lambda s:s.get('workbook')==str(path) and not s.get('busy'),'Workbook loaded by native file dialog: '+path.name)
    try:
        initial_cli=inspect_cli()
        checks.append('Bundled CLI works before GUI launch with Python paths removed, outside package cwd and with spaces')
        process=subprocess.Popen([str(exe),'--qa-state',str(statepath)],cwd=out,env=packaged_environment)
        wait(lambda s:'open_workbook' in s.get('controls',{}),'Extracted EXE launched without source cwd or Python installation dependency')
        app=Application(backend='win32').connect(process=process.pid)
        main_window_handle=app.top_window().handle
        app.top_window().maximize();time.sleep(.7)
        import ctypes
        checks.append('Observed native display DPI: '+str(ctypes.windll.user32.GetDpiForWindow(main_window_handle)))
        screenshot('01-launched.png')
        select_tab('helptab');wait(lambda s:s.get('help_document')=='quick-start','One Help tab opens the short offline basics')
        assert 'general_help' not in state()['controls']
        check_tab_bounds(['about','licenses','agent_settings','diagnostics_settings','help_content'],{'help_content':(400,100)})
        screenshot('01a-ordinary-help.png')
        click('about');wait(lambda s:s.get('help_document')=='about','About/version view opens in extracted app')
        assert state()['app_version']==core.VERSION
        wait(lambda s:len(s.get('about_links',{}))==2,'About displays both manual links')
        assert not browser_log.exists(),'Opening About must not open a browser or check for updates'
        screenshot('01b-about.png')
        expected_links=[]
        for key,url in [('about_project','https://github.com/kevinsullivan0/gridcad'),
                        ('about_releases','https://github.com/kevinsullivan0/gridcad/releases')]:
            # The real browser-handler child can take foreground focus. A
            # click on an inactive Tk Text may only activate its window, so
            # restore and verify the OS foreground before every link click.
            import win32gui
            window=app.top_window();window.set_focus()
            wait(lambda s:win32gui.GetForegroundWindow()==window.handle,
                 'GridCAD is the foreground window before hyperlink click: '+key)
            point=state()['about_links'][key]
            assert point['url']==url
            mouse.click(coords=(point['x'],point['y']))
            expected_links.append(url)
            wait(lambda s:browser_log.exists() and browser_log.read_text(encoding='utf-8').splitlines()==expected_links,
                 'Actual About hyperlink hands exact fixed URL to configured browser: '+url)
        click('about');time.sleep(.3)
        assert browser_log.read_text(encoding='utf-8').splitlines()==expected_links
        checks.append('Current version visible; reopening About performs no update check or browser launch')
        click('project_link')
        expected_links.append('https://github.com/kevinsullivan0/gridcad')
        wait(lambda s:browser_log.read_text(encoding='utf-8').splitlines()==expected_links,
             'Keyboard-focusable GitHub button invokes only its fixed URL')
        # A real browser handoff may change foreground windows. Return to
        # GridCAD through the OS, then prove actual Tab focus before Enter.
        app.top_window().set_focus()
        wait(lambda s:s.get('focused_control')=='project_link','GitHub button retains keyboard focus after returning from browser handoff')
        keyboard.send_keys('{TAB}')
        wait(lambda s:s.get('focused_control')=='releases_link','Real Tab moves focus to Releases button')
        keyboard.send_keys('{ENTER}')
        expected_links.append('https://github.com/kevinsullivan0/gridcad/releases')
        wait(lambda s:browser_log.read_text(encoding='utf-8').splitlines()==expected_links,
             'Tab then Enter activates the ordinary Releases button')

        click('licenses')
        wait(lambda s:'Tcl-license.terms' in s.get('license_files',[]) and 'Python-LICENSE.txt' in s.get('license_files',[]) and 'OpenSSL-LICENSE.txt' in s.get('license_files',[]),'Bundled third-party license text opens without network')
        screenshot('01c-licenses.png')
        assert state()['agent_detection'] is None;checks.append('No agent detection occurs at launch or ordinary Help')
        click('agent_settings');wait(lambda s:'agent_detect' in s.get('controls',{}),'Optional agent settings opens')
        app.window(title='Optional agent help & settings').move_window(width=810,height=480)
        time.sleep(.4);screenshot('01d-agent-help.png')
        click('agent_include_path');wait(lambda s:not s.get('agent_include_path'),'Local app path disclosure can be disabled')
        click('agent_copy');wait(lambda s:'Prompt copied' in s.get('status',''),'Optional prompt copied without launching an agent')
        from pywinauto import clipboard
        assert str(folder) not in clipboard.GetData()
        click('agent_detect');wait(lambda s:s.get('agent_detection') is not None,'User-triggered local metadata detection completes')
        click('agent_detect');time.sleep(.3);screenshot('01e-agent-detection.png')
        click('agent_links');time.sleep(.3);screenshot('01f-agent-information.png')
        click('agent_close');wait(lambda s:'agent_close' not in s.get('controls',{}),'Agent panel closes without blocking ordinary use')
        click('agent_settings');wait(lambda s:'agent_detect' in s.get('controls',{}),'Agent help reopens cleanly')
        click('agent_close');wait(lambda s:'agent_close' not in s.get('controls',{}),'Repeated help closes')

        select_tab('worktab')
        source_hash=core.op.digest(example/'DO_NOT_PRINT.PRINT');workbook_hash=core.op.digest(example/'DO_NOT_PRINT.xlsx')
        load_book(example/'DO_NOT_PRINT.xlsx')
        assert state()['range']=='D4:I7';checks.append('Suggested exact recipe range excludes sidebars')
        click_cell('D4')
        wait(lambda s:s.get('range')=='D4:D4','Actual cell click selects one cell, not its row')
        assert selected_cells()=={'D4'}
        click_cell('F6',shift=True)
        wait(lambda s:s.get('range')=='D4:F6','Actual Shift-click selects a rectangle across columns and rows')
        assert selected_cells()=={f'{c}{r}' for c in 'DEF' for r in range(4,7)}
        screenshot('02a-cell-range-highlight.png')
        click_cell('E5')
        wait(lambda s:s.get('range')=='E5:E5','Ordinary click restarts a one-cell selection')
        assert selected_cells()=={'E5'}
        drag_cells('F6','D4')
        wait(lambda s:s.get('range')=='D4:F6','Actual reversed mouse drag selects the intended rectangle')
        assert selected_cells()=={f'{c}{r}' for c in 'DEF' for r in range(4,7)}
        click_cell('D4');click('next_rows');click_cell('D34',shift=True)
        wait(lambda s:s.get('range')=='D4:D34','Actual Shift-click extends an anchor across row pages')
        load_book(example/'DO_NOT_PRINT.xlsx')
        enter('jump','D4');click('go')
        drag_cells('D4','I7')
        wait(lambda s:s.get('range')=='D4:I7','Actual mouse drag chooses the complete synthetic recipe grid')
        check_tab_bounds(['worksheet','next_rows','jump','go'],{'worksheet':(400,100)})
        screenshot('02b-full-cell-selection.png')
        click('check_recipes');wait(lambda s:'24 recipes valid' in s.get('status',''),'All exact recipe percentages validate through visible Check recipes button')
        longfile=out/'long sheet.xlsx';make_workbook(longfile,{'D501':'2/0/0/0/98/0','E501':'0/0/0/0/0/100'},1,2)
        load_book(longfile);enter('jump','D501');click('go');click_cell('D501');click_cell('E501',shift=True);click('check_recipes')
        wait(lambda s:'2 recipes valid' in s.get('status',''),'Long sheet address navigation and late rectangle selection')
        screenshot('02-long-sheet.png')
        # Real bounded work, not a delayed/mock worker: exercise the visible
        # progress indicator and prove Tk keeps publishing state during it.
        progressbook=out/'large progress workbook.xlsx'
        make_progress_workbook(progressbook)
        load_book(progressbook);enter('range',f'A1:A{PROGRESS_RECIPE_COUNT}');click('check_recipes')
        wait(lambda s:s.get('busy') and s.get('progress_visible') and bool(s.get('activity')),
             'Large recipe validation displays an honest animated activity indicator')
        stamp=statepath.stat().st_mtime_ns
        wait(lambda s:s.get('busy') and statepath.stat().st_mtime_ns>stamp,
             'Tk event loop keeps updating QA state while recipe worker runs')
        screenshot('02c-active-recipe-validation.png')
        wait(lambda s:not s.get('busy') and f'{PROGRESS_RECIPE_COUNT} recipes valid' in s.get('status',''),
             'Large recipe validation completes without UI freeze',timeout=120)
        assert not state().get('progress_visible')
        checks.append('Activity indicator clears after recipe completion')
        malformed=out/'bad packed-cell recipe.xlsx';make_workbook(malformed,{'D4':'20/0/0'},1,1)
        load_book(malformed)
        assert state()['range']=='', 'No valid recipe block must not invent A1:B2'
        enter('range','D4:D4');click('check_recipes')
        wait(lambda s:s.get('diagnostic',{}).get('code')=='GCD103','Bad per-cell recipe identifies the required six-value format')
        malformed_report=json.loads(Path(state()['diagnostic']['report']).read_text())
        assert 'Recipes' in malformed_report['where'] and 'D4' in malformed_report['where']
        assert 'C/M/Y/K/W/T' in malformed_report['remedy']
        screenshot('02d-addressed-recipe-error.png');dismiss()
        cached=out/'cached formula.xlsx';make_workbook(cached,{'D4':'2/0/0/0/98/0'},1,1,formula_cache={'D4':'2/0/0/0/98/0'})
        load_book(cached);enter('range','D4:D4');click('check_recipes')
        wait(lambda s:'1 recipes valid' in s.get('status',''),'Saved formula result works without a blanket attestation checkbox')
        assert 'cache' not in state()['controls'] and 'last results saved by Excel' in state()['formula_notice']
        screenshot('03-saved-formula-notice.png')
        missing=out/'missing formula.xlsx';make_workbook(missing,{'D4':'2/0/0/0/98/0'},1,1,formula_cache={'D4':None})
        load_book(missing);enter('range','D4:D4');click('check_recipes')
        wait(lambda s:s.get('diagnostic',{}).get('code')=='GCD102','Missing saved formula result remains refused without a bypass checkbox')
        screenshot('03a-missing-saved-result.png')
        report=Path(state()['diagnostic']['report']);assert report.is_file()
        report_json=json.loads(report.read_text());assert 'Recipes' in report_json['where'] and 'D4' in report_json['where']
        assert 'Excel' in report_json['remedy'] and 'traceback' in report_json
        click('diagnostic_details');screenshot('03b-technical-details.png');click('diagnostic_copy')
        import win32clipboard
        win32clipboard.OpenClipboard()
        try:prompt=win32clipboard.GetClipboardData()
        finally:win32clipboard.CloseClipboard()
        assert str(report) in prompt and 'grant file access' in prompt and 'nothing was uploaded' in prompt
        checks.append('Optional local report and copied debugging prompt expose no automatic upload or agent execution')
        dismiss()
        wait(lambda s:s.get('focused_control')=='range','Closing the recipe error restores focus to its highlighted range')
        load_book(example/'DO_NOT_PRINT.xlsx')
        click('open_project');dialog_path(example/'DO_NOT_PRINT.PRINT')
        wait(lambda s:s.get('project')==str(example/'DO_NOT_PRINT.PRINT') and not s.get('busy'),'Project loaded by native file dialog')
        assert not state()['save_enabled'];checks.append('Save unavailable until an actual complete mapping validates')
        assert not any(key in state()['controls'] for key in ('reviewed','evidence','material_ack','transpose'))
        click('preview')
        wait(lambda s:all(key in s.get('validation_errors',{}) for key in ('labels','mapping_corner','orientation')),'All missing selectors have actionable inline field messages')
        wait(lambda s:s.get('focused_control')=='labels','First missing selector receives actual keyboard focus')
        assert 'diagnostic_close' not in state()['controls']
        screenshot('03c-required-selections.png')
        click_sample('synthetic-sample-1-1')
        wait(lambda s:'Source material:' in s.get('detail','') and 'Not mapped' in s.get('detail',''),
             'Actual preview click inspects a sample before any mapping exists')
        source_document=core.op.project_document(example/'DO_NOT_PRINT.PRINT')
        source_nodes,_,_=core.op.index(source_document)
        source_material=source_nodes['synthetic-sample-1-1']['material']
        source_name=source_material.get('metadata',{}).get('displayName') or source_material['name']
        assert source_name in state()['detail']
        assert 'EcoFlexBlack' in state()['material_choice']
        checks.append('Source material name remains distinct from the metadata-derived EcoFlex label target')
        screenshot('03c-unmapped-sample-inspection.png')
        # Clicking blank space must not select the nearest sample. This point
        # is inside the canvas margin, outside every actual sample rectangle.
        canvas=state()['controls']['geometry'];prior_detail=state()['detail']
        mouse.click(coords=(canvas['x']+5,canvas['y']+5));time.sleep(.3)
        assert state()['detail']==prior_detail
        checks.append('Blank preview space does not inspect a distant nearest sample')
        label_index=next(i for i,v in enumerate(state()['label_choices']) if v.startswith('Printed labels '))
        select_combo('labels',label_index);choose_top_left_rows_down()
        worksheet_tab();enter('range','D4:H7');geometry_tab();click('preview')
        wait(lambda s:all(token in s.get('validation_errors',{}).get('range','') for token in ('20','24','Recipes','D4:H7')),'20 selected cells versus24samples is explained inline with exact range')
        assert 'diagnostic_close' not in state()['controls']
        screenshot('03d-count-mismatch.png')
        geometry_tab()
        assert not state()['save_enabled'] and not state()['proposal']
        click_sample('synthetic-sample-1-2')
        wait(lambda s:s.get('selected_sample')=='synthetic-sample-1-2' and 'Not mapped' in s.get('detail',''),
             'Actual preview remains inspectable after a count-mismatch error')
        worksheet_tab();enter('jump','D4');click('go');drag_cells('D4','I7');geometry_tab()
        click('preview');wait(lambda s:s.get('proposal') and not s.get('busy'),'Actual geometry mapping preview created')
        wait(lambda s:s.get('save_enabled'),'Valid mapping enables Save without review checkboxes or notes')
        assert not state()['validation_errors']
        worksheet_tab();enter('range','D4:H7');geometry_tab()
        wait(lambda s:not s.get('save_enabled') and not s.get('proposal'),'Breaking the corrected range immediately revokes the old mapping')
        click('preview');wait(lambda s:'range' in s.get('validation_errors',{}),'A repeated mismatch has current actionable feedback')
        worksheet_tab();enter('range','D4:I7');geometry_tab();click('preview')
        wait(lambda s:s.get('save_enabled') and not s.get('busy'),'Correcting again restores a fresh valid mapping')
        click_sample('synthetic-sample-1-1')
        wait(lambda s:'Recipes!D4' in s.get('detail','') and 'requested C/M/Y/K/W/T' in s.get('detail',''),
             'Mapped preview click shows exact requested recipe separately from source material')
        screenshot('04-mapping-preview.png')
        click('zoom_in');wait(lambda s:not s.get('busy'),'Zoomed preview finishes')
        click_sample('synthetic-sample-2-3')
        wait(lambda s:s.get('selected_sample')=='synthetic-sample-2-3' and 'Recipes!F5' in s.get('detail',''),
             'Actual zoomed preview click inspects the corresponding cell, not a stale-size hitbox')
        screenshot('05-zoomed-labels.png');click('fit')
        wait(lambda s:not s.get('busy'),'Fit preview finishes')
        select_combo('orientation',1)
        assert not state()['save_enabled']
        click('preview');wait(lambda s:s.get('diagnostic',{}).get('code')=='GCD201','Incompatible row direction refuses export clearly');dismiss()
        wait(lambda s:s.get('focused_control')=='range','Shape error returns to its highlighted worksheet range')
        geometry_tab()
        click_sample('synthetic-sample-1-1')
        wait(lambda s:'Not mapped' in s.get('detail',''),'Changing directions keeps source inspection available')
        choose_top_left_rows_down();click('preview')
        wait(lambda s:s.get('proposal') and not s.get('busy') and s.get('save_enabled'),'Correcting directions restores valid Save')
        assert 'Recipes!D4 requested' in state()['detail']
        checks.append('Rebuilding a mapping refreshes the selected sample recipe without another click')
        check_tab_bounds(['geometry'],{'geometry':(300,140)})
        # Exercise the declared minimum window as well as the runner desktop.
        app.top_window().restore();app.top_window().move_window(x=0,y=0,width=960,height=680)
        time.sleep(1)
        wait(lambda s:not s.get('busy'),'Minimum-window geometry repaint completes')
        check_tab_bounds(['geometry'],{'geometry':(300,100)})
        click_sample('synthetic-sample-3-4')
        wait(lambda s:s.get('selected_sample')=='synthetic-sample-3-4' and 'Recipes!G6' in s.get('detail',''),
             'Actual minimum-window preview click uses the resized geometry coordinates')
        assert 'include_report' not in state()['controls']
        checks.append('Normal minimum-size workflow has no conversion-report clutter')
        screenshot('05a-minimum-geometry.png')
        select_tab('worktab')
        check_tab_bounds(['worksheet','next_rows','jump','go'],{'worksheet':(400,100)})
        screenshot('05a-minimum-worksheet.png')
        select_tab('helptab')
        if 'help_basics' in state()['controls']:click('help_basics')
        wait(lambda s:s.get('help_document')=='quick-start','Short basics remain recoverable after About or Licenses')
        check_tab_bounds(['about','licenses','agent_settings','diagnostics_settings','help_content'],{'help_content':(400,100)})
        click('diagnostics_settings');wait(lambda s:'include_report' in s['controls'],'Optional report is discoverable in Diagnostics')
        screenshot('05a-diagnostics-report.png');click('diagnostics_settings_close')
        screenshot('05a-minimum-help.png')
        select_tab('maptab')
        check_tab_bounds(['assignments'],{'assignments':(600,100)})
        screenshot('05a-minimum-assignments.png')
        select_tab('geotab')
        app.top_window().maximize();time.sleep(1)
        wait(lambda s:not s.get('busy'),'Maximized geometry repaint completes')
        select_tab('maptab')
        check_tab_bounds(['assignments'],{'assignments':(600,100)})
        screenshot('05b-exact-assignments.png')
        select_tab('geotab')
        wait(lambda s:s.get('save_enabled'),'Valid Save remains available after tab and window changes')
        screenshot('06-ready-to-save.png')
        click('save');initial_folder=dialog_folder()
        assert not initial_folder.is_relative_to(folder.resolve()) and initial_folder!=out.resolve()
        screenshot('06a-save-default-folder.png');keyboard.send_keys('{ESC}');time.sleep(.4)
        assert state()['save_enabled'] and state()['proposal']
        checks.append('Canceling the save dialog keeps the valid mapping ready')
        export_folder=out/'export';export_folder.mkdir()
        result=export_folder/'My materials.PRINT';click('save');dialog_path(result)
        wait(lambda s:result.is_file() and not s.get('busy'),'Native save dialog writes the chosen PRINT filename')
        screenshot('07-saved.png');dismiss()
        assert sorted(p.name for p in export_folder.iterdir())==['My materials.PRINT']
        audit=state()['last_save_audit'];assert audit['changed_count']==24 and audit['nonmaterial_preservation_passed'] and not audit['print_ready']
        assert audit['physical_mapping_reviewed'] is False
        checks.append('Saved audit truthfully records no physical-review attestation')
        doc=core.op.project_document(result);nodes,_,bodies=core.op.index(doc)
        for r in range(4):
            for c in range(6):
                oid=f'synthetic-sample-{r+1}-{c+1}';cyan=(r*7+c*3)%51;clear=(c*5)%31
                expected=core.op.validate_recipe([str(cyan),'0','0','0',str(100-cyan-clear),str(clear)])
                assert core.op.matches_mixer(nodes[oid]['material'],expected);assert nodes[oid]['material']==bodies[oid]['material']
        assert core.op.digest(example/'DO_NOT_PRINT.PRINT')==source_hash and core.op.digest(example/'DO_NOT_PRINT.xlsx')==workbook_hash
        checks.append('Saved candidate independently matches all known physical sample indices/recipes; original inputs unchanged')
        original_output_hash=core.op.digest(result)
        click('save');assert dialog_folder()==export_folder.resolve();dialog_path(result)
        wait(lambda s:s.get('diagnostic',{}).get('code')=='GCD401','Existing output refuses overwrite with an actionable recovery dialog')
        assert core.op.digest(result)==original_output_hash
        screenshot('07a-existing-output-refused.png');dismiss()
        wait(lambda s:s.get('save_enabled'),'Save remains ready after filename collision')
        select_tab('helptab');click('diagnostics_settings');click('include_report');click('diagnostics_settings_close')
        geometry_tab();retry=export_folder/'Retry with report.PRINT';click('save');dialog_path(retry)
        wait(lambda s:retry.is_file() and not s.get('busy'),'Choosing another name succeeds in the same session');dismiss()
        assert (export_folder/'Retry with report.gridcad-report.json').is_file()
        assert core.op.digest(result)==original_output_hash
        select_tab('helptab');click('diagnostics_settings');click('include_report');click('diagnostics_settings_close');geometry_tab()
        checks.append('Optional diagnostic report is deliberate; normal output and source bytes remain unchanged through collision/retry')
        assert not state()['errors'];checks.append('No unhandled GUI callback errors')
        click('example')
        wait(lambda s:not s.get('busy') and not s.get('transpose') and s.get('orientation')=='Rows down; columns right','Load example resets mapping direction state')
        click('preview');wait(lambda s:s.get('proposal') and not s.get('busy'),'Example can be reopened after a completed conversion')
        assert state()['save_enabled'];checks.append('Reopened example validates again without redundant review gates')
        # Real pyramid and mixed-shape file workflows, not just unit counts.
        for shape,columns in [('pyramid',9),('mixed',12)]:
            fixture=create(out/('generated '+shape),rows=3,columns=columns,pitch=16,size=9,sample_shape=shape,height=7)
            load_book(fixture/'DO_NOT_PRINT.xlsx')
            click('open_project');dialog_path(fixture/'DO_NOT_PRINT.PRINT')
            wait(lambda s:s.get('project')==str(fixture/'DO_NOT_PRINT.PRINT') and not s.get('busy'),'Loaded genuine '+shape+' mesh archive')
            select_combo('labels',next(i for i,v in enumerate(state()['label_choices']) if v.startswith('Printed labels ')))
            choose_top_left_rows_down();click('preview')
            wait(lambda s:s.get('proposal') and not s.get('busy'),'Shape-independent '+shape+' grid preview')
            screenshot('08-'+shape+'-preview.png')
            assert f'{3*columns} cells selected' in state()['selection_summary']
            shaped_output=out/(shape+' different dimensions.PRINT');click('save');dialog_path(shaped_output)
            wait(lambda s:shaped_output.is_file() and not s.get('busy'),'Different-dimension '+shape+' conversion saves through the real dialog');dismiss()
            before=core.op.project_document(fixture/'DO_NOT_PRINT.PRINT');after=core.op.project_document(shaped_output)
            changed=set(state()['last_save_audit']['changed_occurrence_ids'])
            assert len(changed)==3*columns
            assert core.op.stripped(before,changed)==core.op.stripped(after,changed)
            checks.append('Different grid dimensions preserve existing multi-body/multidigit label geometry and unrelated data')
        fixture=create_reference_example(out/'reference material fixture')
        load_book(fixture/'DO_NOT_PRINT.xlsx')
        click('open_project');dialog_path(fixture/'DO_NOT_PRINT.PRINT')
        wait(lambda s:s.get('project')==str(fixture/'DO_NOT_PRINT.PRINT') and not s.get('busy'),'Reference-material fixture loaded')
        select_combo('labels',next(i for i,v in enumerate(state()['label_choices']) if v.startswith('Printed labels ')))
        choose_top_left_rows_down();select_combo('label_mode',1)
        assert state()['material_choice'] in state()['reference_choices']
        assert 'label_reference' not in state()['controls']
        click('preview');wait(lambda s:s.get('proposal') and not s.get('busy'),'Reference-copy conflict preview lists existing assignments')
        assert not state()['save_enabled'];click('replace_labels');screenshot('09-reference-conflict-review.png')
        click('label_review_cancel');assert not state()['save_enabled']
        click('preview');wait(lambda s:s.get('proposal') and not s.get('busy'),'Cancel conflict review keeps existing labels protected')
        click('replace_labels');click('label_review_confirm');click('preview')
        wait(lambda s:s.get('proposal') and not s.get('busy'),'Explicitly confirmed reference-material preview')
        wait(lambda s:s.get('save_enabled'),'Reference-material Save enables after actual conflict consent, without redundant review gates')
        assert 'build a new mapping' not in state()['detail']
        assert 'Not mapped' not in state()['detail']
        screenshot('10-reference-ready.png')
        destination=out/'Reference copied.PRINT';click('save');dialog_path(destination)
        wait(lambda s:destination.is_file() and not s.get('busy'),'Native UI saves explicit reference material copy');dismiss()
        original=core.op.project_document(fixture/'DO_NOT_PRINT.PRINT');saved=core.op.project_document(destination)
        oldnodes,_,oldbodies=core.op.index(original);newnodes,_,newbodies=core.op.index(saved)
        reference=oldnodes[REFERENCE_ID]['material']
        for oid in core.load_project(fixture/'DO_NOT_PRINT.PRINT')['containers']['synthetic-labels']['leaves']:
            expected=dict(reference);expected['id']=oldnodes[oid]['material']['id']
            assert newnodes[oid]['material']==expected==newbodies[oid]['material']
        assert newnodes[REFERENCE_ID]==oldnodes[REFERENCE_ID]
        checks.append('Complete native reference metadata cloned; target identities and source reference preserved')
        # Switching away from an approved reference must clear both the source
        # choice and its prior consent. This fixture contains only picker values.
        picker_fixture=make_picker_only_example(out/'picker only fixture')
        load_book(picker_fixture/'DO_NOT_PRINT.xlsx')
        click('open_project');dialog_path(picker_fixture/'DO_NOT_PRINT.PRINT')
        wait(lambda s:s.get('project')==str(picker_fixture/'DO_NOT_PRINT.PRINT') and not s.get('busy'),
             'Picker-only source opens after a reference-material conversion')
        assert not state()['proposal'] and not state()['save_enabled']
        assert not state()['reference_choices'] and not state()['label_reference']
        assert 'label_reference' not in state()['controls'] and 'replace_labels' not in state()['controls']
        checks.append('No reference chooser or replacement action is offered when source has no saved compatible material')
        click_sample('synthetic-sample-1-1')
        wait(lambda s:'Source material:' in s.get('detail','') and 'Not mapped' in s.get('detail',''),
             'New source inspection is independent of stale reference and mapping state')
        screenshot('10a-no-reference-source.png')
        select_combo('labels',next(i for i,v in enumerate(state()['label_choices']) if v.startswith('Printed labels ')))
        choose_top_left_rows_down();click('preview')
        wait(lambda s:s.get('proposal') and not s.get('busy') and s.get('save_enabled'),
             'Default label workflow validates without requiring a nonexistent reference')
        # A corrupt replacement is an ordinary file-open failure, not a stress
        # payload. No old source/material/mapping may survive as active state.
        broken=out/'not a print project.PRINT';broken.write_text('not a project archive',encoding='utf-8')
        click('open_project');dialog_path(broken)
        wait(lambda s:'diagnostic_close' in s.get('controls',{}) and not s.get('busy'),
             'Invalid replacement project shows recoverable error')
        dismiss()
        assert state()['project'] is None and not state()['proposal'] and not state()['save_enabled']
        assert not state()['reference_choices'] and not state().get('geometry_samples')
        screenshot('10b-failed-project-cleared.png')
        # Load example uses PyInstaller's bundled resources, not the separate
        # top-level copies provided for manual/CLI use. Require the exact bundled
        # path and identical public example bytes before exercising recovery.
        bundled_example=folder/'_internal/examples/rectangular/DO_NOT_PRINT.PRINT'
        assert hashlib.sha256(bundled_example.read_bytes()).digest()==hashlib.sha256(
            (example/'DO_NOT_PRINT.PRINT').read_bytes()).digest()
        click('example');wait(lambda s:s.get('project')==str(bundled_example) and not s.get('busy'),
                              'Valid example reloads after failed source replacement')
        click('preview');wait(lambda s:s.get('proposal') and not s.get('busy') and s.get('save_enabled'),
                              'Save becomes available again after source error recovery')
        assert inspect_cli()==initial_cli
        assert process.poll() is None
        checks.append('CLI and GUI run concurrently against the shared runtime with identical inspection output')
        cli_output=out/'separate CLI result'
        conversion=[str(folder/'GridCAD-core.exe'),'convert','--project',str(example/'DO_NOT_PRINT.PRINT'),
                    '--workbook',str(example/'DO_NOT_PRINT.xlsx'),'--sheet','Recipes','--range','D4:I7',
                    '--samples','Sample','--labels','Printed labels','--orientation','Rows down; columns right',
                    '--confirm-mapping','--allow-unverified-material-profile',
                    '--review-notes','Synthetic example corner/interior labels checked against generated indices.',
                    '--out-dir',str(cli_output)]
        converted=subprocess.run(conversion,cwd=out,env=packaged_environment,capture_output=True,text=True,check=True,timeout=60)
        cli_audit=json.loads(converted.stdout)
        assert cli_audit['changed_count']==24 and cli_audit['nonmaterial_preservation_passed'] and not cli_audit['print_ready']
        assert core.op.project_document(cli_output/'candidate_UNVERIFIED.PRINT')==core.op.project_document(result)
        assert inspect_cli()==initial_cli
        checks.append('Frozen CLI conversion preserves exact GUI candidate content and originals while GUI remains open')
        def ps_quote(value):return "'"+str(value).replace("'","''")+"'"
        ps='& '+ps_quote(folder/'GridCAD-core.exe')+' inspect --project '+ps_quote(example/'DO_NOT_PRINT.PRINT')+' --workbook '+ps_quote(example/'DO_NOT_PRINT.xlsx')
        inspected_ps=subprocess.run([str(system32/'WindowsPowerShell/v1.0/powershell.exe'),'-NoProfile','-NonInteractive','-Command',ps],cwd=out,env=packaged_environment,capture_output=True,text=True,check=True,timeout=60)
        assert json.loads(inspected_ps.stdout)['profile']==core.PROFILE
        checks.append('Documented PowerShell call operator and quoted paths with spaces work without policy changes')

        # A genuinely unwritable report root must not mask the original error.
        Application(backend='win32').connect(process=process.pid).top_window().close();process.wait(timeout=10)
        assert inspect_cli()==initial_cli
        checks.append('Bundled CLI remains independent after GUI shutdown; shared files are not locked or removed')
        blocked_root=out/'not-a-report-directory';blocked_root.write_text('keep this file')
        statepath.unlink(missing_ok=True)
        environment=dict(packaged_environment,LOCALAPPDATA=str(blocked_root))
        process=subprocess.Popen([str(exe),'--qa-state',str(statepath)],cwd=out,env=environment)
        wait(lambda s:'open_workbook' in s.get('controls',{}),'App relaunch with unwritable diagnostics location')
        relaunched_window=Application(backend='win32').connect(process=process.pid).top_window()
        main_window_handle=relaunched_window.handle
        relaunched_window.maximize();time.sleep(.4)
        load_book(missing);enter('range','D4:D4');click('check_recipes')
        # Keep one complete observed snapshot: a second read may transiently
        # return {} while the optional state file is atomically replaced.
        diagnostic_state=wait(lambda s:s.get('diagnostic',{}).get('code')=='GCD102' and 'diagnostic_copy' in s.get('controls',{}),'Original missing-result error remains visible when report writing fails')
        assert diagnostic_state['diagnostic']['report'] is None
        assert not diagnostic_state['controls']['diagnostic_copy']['enabled']
        screenshot('11-report-location-unwritable.png');dismiss()
        load_book(example/'DO_NOT_PRINT.xlsx');click('check_recipes')
        wait(lambda s:'24 recipes valid' in s.get('status',''),'Manual correction works without agent or writable report directory')
        assert blocked_root.read_text()=='keep this file' and not state()['errors']
        result_json={'status':'passed','platform':'GitHub-hosted Windows','artifact':a.zip.name,'checks':checks,
                     'native_grabcad_open_recompose_save_verified':False,'signed':False}
        (out/'acceptance.json').write_text(json.dumps(result_json,indent=2),encoding='utf-8');print(json.dumps(result_json,indent=2))
    except Exception as exc:
        # Read-only failure evidence distinguishes a missing handoff from a
        # duplicate/wrong URL and records foreground ownership without another
        # click or focus change. Diagnostic collection must not hide the error.
        browser_evidence={'browser_log':None,'foreground_hwnd':None,
                          'main_hwnd':main_window_handle}
        try:
            browser_evidence['browser_log']=browser_log.read_text(encoding='utf-8') if browser_log.exists() else ''
        except Exception as diagnostic_error:
            browser_evidence['browser_log_error']=str(diagnostic_error)
        try:
            import win32gui
            browser_evidence['foreground_hwnd']=win32gui.GetForegroundWindow()
        except Exception as diagnostic_error:
            browser_evidence['foreground_error']=str(diagnostic_error)
        screenshot('failure.png')
        (out/'acceptance.json').write_text(json.dumps({'status':'failed','error':str(exc),
            'checks':checks,'state':state(),'browser_handoff_evidence':browser_evidence},indent=2),encoding='utf-8')
        raise
    finally:
        if process and process.poll() is None:
            try:Application(backend='win32').connect(process=process.pid).top_window().close();process.wait(timeout=10)
            except Exception:process.terminate()


if __name__=='__main__':main()
