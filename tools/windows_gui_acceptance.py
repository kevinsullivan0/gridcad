"""Operate the extracted Windows EXE through real controls and native dialogs.

The optional QA state channel reports control locations/status only. All actions
below are real OS keyboard/mouse events; no backend or dialog is replaced.
"""
from pathlib import Path
import argparse
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


def main():
    if sys.platform!='win32':raise SystemExit('This acceptance requires Windows desktop interaction.')
    from pywinauto import Application, Desktop, mouse, keyboard
    from PIL import ImageGrab
    parser=argparse.ArgumentParser();parser.add_argument('--zip',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    extracted=out/'extracted package with spaces'
    with zipfile.ZipFile(a.zip) as archive:archive.extractall(extracted)
    folder=extracted/'GridCAD';exe=folder/'GridCAD.exe';example=folder/'examples/rectangular'
    statepath=out/'gui-state.json';checks=[];process=None
    assert 'Copyright (c) 2026 Kevin Sullivan' in (folder/'LICENSE').read_text()
    assert 'Permission is hereby granted' in (folder/'LICENSE').read_text()
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
    def click(key):
        p=wait(lambda s:key in s.get('controls',{}),'Control visible: '+key)['controls'][key]
        mouse.click(coords=(p['x']+p['w']//2,p['y']+p['h']//2));time.sleep(.25)
    def select_combo(key,index):
        click(key);keyboard.send_keys('{ESC}');keyboard.send_keys('%{DOWN}');time.sleep(.3)
        keyboard.send_keys('{HOME}{UP 50}');keyboard.send_keys('{DOWN}'*index+'{ENTER}');time.sleep(.4)
        expected = (state()['label_choices'][index] if key == 'labels' else state()['reference_choices'][index] if key == 'label_reference' else ['Direct black','Copy from reference body'][index] if key == 'label_mode' else list(core.ORIENTATIONS)[index])
        wait(lambda s:s.get(key)==expected,'Explicit combobox selection: '+expected)
    def enter(key,text):
        click(key);keyboard.send_keys('^a');keyboard.send_keys(str(text),with_spaces=True,vk_packet=True);time.sleep(.2)
    def dialog_path(path):
        time.sleep(.7);keyboard.send_keys('%n');keyboard.send_keys('^a');keyboard.send_keys(str(path),with_spaces=True,vk_packet=True);keyboard.send_keys('{ENTER}');time.sleep(.5)
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
        process=subprocess.Popen([str(exe),'--qa-state',str(statepath)],cwd=out)
        wait(lambda s:'open_workbook' in s.get('controls',{}),'Extracted EXE launched without source cwd or Python installation dependency')
        app=Application(backend='win32').connect(process=process.pid)
        app.top_window().maximize();time.sleep(.7)
        screenshot('01-launched.png')
        p=state()['controls']['tabs'];mouse.click(coords=(p['x']+460,p['y']+12));time.sleep(.3)
        click('about');wait(lambda s:s.get('help_document')=='about','About/version view opens in extracted app')
        screenshot('01b-about.png');click('licenses')
        wait(lambda s:'Tcl-license.terms' in s.get('license_files',[]) and 'Python-LICENSE.txt' in s.get('license_files',[]) and 'OpenSSL-LICENSE.txt' in s.get('license_files',[]),'Bundled third-party license text opens without network')
        screenshot('01c-licenses.png')
        p=state()['controls']['tabs'];mouse.click(coords=(p['x']+70,p['y']+12));time.sleep(.3)
        source_hash=core.op.digest(example/'DO_NOT_PRINT.PRINT');workbook_hash=core.op.digest(example/'DO_NOT_PRINT.xlsx')
        load_book(example/'DO_NOT_PRINT.xlsx')
        assert state()['range']=='D4:I7';checks.append('Suggested exact recipe range excludes sidebars')
        click('check_recipes');wait(lambda s:'24 recipes valid' in s.get('status',''),'All exact recipe percentages validate through visible Check recipes button')
        longfile=out/'long sheet.xlsx';make_workbook(longfile,{'D501':'2/0/0/0/98/0','E501':'0/0/0/0/0/100'},1,2)
        load_book(longfile);enter('jump','D481');click('go');enter('range','D501:E501');click('check_recipes')
        wait(lambda s:'2 recipes valid' in s.get('status',''),'Long sheet address navigation and late rectangle selection')
        screenshot('02-long-sheet.png')
        cached=out/'cached formula.xlsx';make_workbook(cached,{'D4':'2/0/0/0/98/0'},1,1,formula_cache={'D4':'2/0/0/0/98/0'})
        load_book(cached);enter('range','D4:D4');click('check_recipes')
        wait(lambda s:s.get('diagnostic',{}).get('code')=='GCD101','Unconfirmed formula cache blocked by real UI')
        screenshot('03-formula-refusal.png')
        report=Path(state()['diagnostic']['report']);assert report.is_file()
        report_json=json.loads(report.read_text());assert 'settings' in report_json and 'traceback' in report_json
        click('diagnostic_details');screenshot('03b-technical-details.png');click('diagnostic_copy')
        import win32clipboard
        win32clipboard.OpenClipboard()
        try:prompt=win32clipboard.GetClipboardData()
        finally:win32clipboard.CloseClipboard()
        assert str(report) in prompt and 'grant file access' in prompt and 'nothing was uploaded' in prompt
        checks.append('Optional local report and copied debugging prompt expose no automatic upload or agent execution')
        dismiss();click('cache');click('check_recipes')
        wait(lambda s:'1 recipes valid' in s.get('status',''),'Explicit cache confirmation permits stored recipe')
        missing=out/'missing formula.xlsx';make_workbook(missing,{'D4':'2/0/0/0/98/0'},1,1,formula_cache={'D4':None})
        load_book(missing);enter('range','D4:D4');click('cache');click('check_recipes')
        wait(lambda s:s.get('diagnostic',{}).get('code')=='GCD102','Missing formula cache refused despite confirmation');dismiss()
        load_book(example/'DO_NOT_PRINT.xlsx')
        click('open_project');dialog_path(example/'DO_NOT_PRINT.PRINT')
        wait(lambda s:s.get('project')==str(example/'DO_NOT_PRINT.PRINT') and not s.get('busy'),'Project loaded by native file dialog')
        assert not state()['save_enabled'];checks.append('Save unavailable before orientation and physical review')
        # Explicit container and orientation choices through native comboboxes.
        label_index=next(i for i,v in enumerate(state()['label_choices']) if v.startswith('Printed labels '))
        select_combo('labels',label_index)
        select_combo('orientation',0)
        click('preview');wait(lambda s:s.get('proposal') and not s.get('busy'),'Actual geometry mapping preview created')
        screenshot('04-mapping-preview.png')
        click('zoom_in');time.sleep(.5);screenshot('05-zoomed-labels.png');click('fit')
        # Use the real tab control to return to worksheet and transpose.
        p=state()['controls']['tabs'];mouse.click(coords=(p['x']+70,p['y']+12));time.sleep(.3)
        click('transpose');click('preview')
        wait(lambda s:s.get('diagnostic',{}).get('code')=='GCD201','Dimension mismatch is visible after transpose');dismiss()
        p=state()['controls']['tabs'];mouse.click(coords=(p['x']+250,p['y']+12));time.sleep(.3)
        select_combo('orientation',1);click('preview')
        wait(lambda s:s.get('proposal') and not s.get('busy'),'Explicit transposed orientation builds correct map')
        assert not state()['save_enabled']
        click('reviewed');enter('evidence','Synthetic physical index corners 1/1, 1/6, 4/1, 4/6 and interior 2/3 checked.');click('material_ack')
        wait(lambda s:s.get('save_enabled'),'Save enables only after all review prerequisites')
        screenshot('06-reviewed.png')
        result=out/'new result bundle';click('save');dialog_path(result)
        wait(lambda s:(result/'audit.json').is_file() and not s.get('busy'),'Native save dialog writes a new separate result folder')
        screenshot('07-saved.png');dismiss()
        audit=json.loads((result/'audit.json').read_text());assert audit['changed_count']==24 and audit['nonmaterial_preservation_passed'] and not audit['print_ready']
        doc=core.op.project_document(result/'candidate_UNVERIFIED.PRINT');nodes,_,bodies=core.op.index(doc)
        for r in range(4):
            for c in range(6):
                oid=f'synthetic-sample-{r+1}-{c+1}';cyan=(r*7+c*3)%51;clear=(c*5)%31
                expected=core.op.validate_recipe([str(cyan),'0','0','0',str(100-cyan-clear),str(clear)])
                assert core.op.matches_mixer(nodes[oid]['material'],expected);assert nodes[oid]['material']==bodies[oid]['material']
        assert core.op.digest(example/'DO_NOT_PRINT.PRINT')==source_hash and core.op.digest(example/'DO_NOT_PRINT.xlsx')==workbook_hash
        checks.append('Saved candidate independently matches all known physical sample indices/recipes; original inputs unchanged')
        assert not state()['errors'];checks.append('No unhandled GUI callback errors')
        click('example')
        wait(lambda s:not s.get('busy') and not s.get('transpose') and s.get('orientation')=='Rows down; columns right','Load example resets previous transpose and review state')
        click('preview');wait(lambda s:s.get('proposal') and not s.get('busy'),'Example can be reopened after a completed transposed conversion')
        assert not state()['save_enabled'];checks.append('Reopened example requires fresh review before saving')
        # Real pyramid and mixed-shape file workflows, not just unit counts.
        for shape in ['pyramid','mixed']:
            fixture=create(out/('generated '+shape),rows=3,columns=5,pitch=16,size=9,sample_shape=shape,height=7)
            load_book(fixture/'DO_NOT_PRINT.xlsx')
            click('open_project');dialog_path(fixture/'DO_NOT_PRINT.PRINT')
            wait(lambda s:s.get('project')==str(fixture/'DO_NOT_PRINT.PRINT') and not s.get('busy'),'Loaded genuine '+shape+' mesh archive')
            select_combo('labels',next(i for i,v in enumerate(state()['label_choices']) if v.startswith('Printed labels ')))
            select_combo('orientation',0);click('preview')
            wait(lambda s:s.get('proposal') and not s.get('busy'),'Shape-independent '+shape+' grid preview')
            screenshot('08-'+shape+'-preview.png')
        fixture=create_reference_example(out/'reference material fixture')
        load_book(fixture/'DO_NOT_PRINT.xlsx')
        click('open_project');dialog_path(fixture/'DO_NOT_PRINT.PRINT')
        wait(lambda s:s.get('project')==str(fixture/'DO_NOT_PRINT.PRINT') and not s.get('busy'),'Reference-material fixture loaded')
        select_combo('labels',next(i for i,v in enumerate(state()['label_choices']) if v.startswith('Printed labels ')))
        select_combo('orientation',0);select_combo('label_mode',1)
        select_combo('label_reference',next(i for i,v in enumerate(state()['reference_choices']) if v.startswith('Reference white ')))
        click('preview');wait(lambda s:s.get('proposal') and not s.get('busy'),'Reference-copy conflict preview lists existing assignments')
        assert not state()['save_enabled'];click('replace_labels');screenshot('09-reference-conflict-review.png')
        click('label_review_cancel');assert not state()['save_enabled']
        click('preview');wait(lambda s:s.get('proposal') and not s.get('busy'),'Cancel conflict review keeps existing labels protected')
        click('replace_labels');click('label_review_confirm');click('preview')
        wait(lambda s:s.get('proposal') and not s.get('busy'),'Explicitly confirmed reference-material preview')
        click('reviewed');enter('evidence','Synthetic grid and all ten label replacements reviewed against Reference white.');click('material_ack')
        wait(lambda s:s.get('save_enabled'),'Reference-material save requires physical and replacement review')
        screenshot('10-reference-ready.png')
        destination=out/'reference copied result';click('save');dialog_path(destination)
        wait(lambda s:(destination/'audit.json').is_file() and not s.get('busy'),'Native UI saves explicit reference material copy');dismiss()
        original=core.op.project_document(fixture/'DO_NOT_PRINT.PRINT');saved=core.op.project_document(destination/'candidate_UNVERIFIED.PRINT')
        oldnodes,_,oldbodies=core.op.index(original);newnodes,_,newbodies=core.op.index(saved)
        reference=oldnodes[REFERENCE_ID]['material']
        for oid in core.load_project(fixture/'DO_NOT_PRINT.PRINT')['containers']['synthetic-labels']['leaves']:
            expected=dict(reference);expected['id']=oldnodes[oid]['material']['id']
            assert newnodes[oid]['material']==expected==newbodies[oid]['material']
        assert newnodes[REFERENCE_ID]==oldnodes[REFERENCE_ID]
        checks.append('Complete native reference metadata cloned; target identities and source reference preserved')
        command=[str(folder/'advanced/GridCAD-core.exe'),'inspect','--project',str(example/'DO_NOT_PRINT.PRINT'),'--workbook',str(example/'DO_NOT_PRINT.xlsx')]
        inspected=subprocess.run(command,cwd=out,capture_output=True,text=True,check=True)
        assert json.loads(inspected.stdout)['profile']==core.PROFILE;checks.append('Bundled agent CLI executes outside source tree')
        # A genuinely unwritable report root must not mask the original error.
        Application(backend='win32').connect(process=process.pid).top_window().close();process.wait(timeout=10)
        blocked_root=out/'not-a-report-directory';blocked_root.write_text('keep this file')
        statepath.unlink(missing_ok=True)
        environment=dict(os.environ,LOCALAPPDATA=str(blocked_root))
        process=subprocess.Popen([str(exe),'--qa-state',str(statepath)],cwd=out,env=environment)
        wait(lambda s:'open_workbook' in s.get('controls',{}),'App relaunch with unwritable diagnostics location')
        Application(backend='win32').connect(process=process.pid).top_window().maximize();time.sleep(.4)
        load_book(cached);enter('range','D4:D4');click('check_recipes')
        wait(lambda s:s.get('diagnostic',{}).get('code')=='GCD101','Original formula error remains visible when report writing fails')
        assert state()['diagnostic']['report'] is None
        assert not state()['controls']['diagnostic_copy']['enabled']
        screenshot('11-report-location-unwritable.png');dismiss()
        load_book(example/'DO_NOT_PRINT.xlsx');click('check_recipes')
        wait(lambda s:'24 recipes valid' in s.get('status',''),'Manual correction works without agent or writable report directory')
        assert blocked_root.read_text()=='keep this file' and not state()['errors']
        result_json={'status':'passed','platform':'GitHub-hosted Windows','artifact':a.zip.name,'checks':checks,
                     'native_grabcad_open_recompose_save_verified':False,'signed':False}
        (out/'acceptance.json').write_text(json.dumps(result_json,indent=2),encoding='utf-8');print(json.dumps(result_json,indent=2))
    except Exception as exc:
        screenshot('failure.png');(out/'acceptance.json').write_text(json.dumps({'status':'failed','error':str(exc),'checks':checks,'state':state()},indent=2),encoding='utf-8');raise
    finally:
        if process and process.poll() is None:
            try:Application(backend='win32').connect(process=process.pid).top_window().close();process.wait(timeout=10)
            except Exception:process.terminate()


if __name__=='__main__':main()
