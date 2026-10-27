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
from tools.make_desktop_examples import make_workbook
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
        keyboard.send_keys('{UP 20}');keyboard.send_keys('{DOWN}'*index+'{ENTER}');time.sleep(.4)
        expected = state()['label_choices'][index] if key == 'labels' else list(core.ORIENTATIONS)[index]
        wait(lambda s:s.get(key)==expected,'Explicit combobox selection: '+expected)
    def enter(key,text):
        click(key);keyboard.send_keys('^a');keyboard.send_keys(str(text),with_spaces=True,vk_packet=True);time.sleep(.2)
    def dialog_path(path):
        time.sleep(.7);keyboard.send_keys('%n');keyboard.send_keys('^a');keyboard.send_keys(str(path),with_spaces=True,vk_packet=True);keyboard.send_keys('{ENTER}');time.sleep(.5)
    def dismiss():
        time.sleep(.3);keyboard.send_keys('{ENTER}');time.sleep(.3)
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
        wait(lambda s:'formula uses a saved result' in s.get('status',''),'Unconfirmed formula cache blocked by real UI')
        screenshot('03-formula-refusal.png');dismiss();click('cache');click('check_recipes')
        wait(lambda s:'1 recipes valid' in s.get('status',''),'Explicit cache confirmation permits stored recipe')
        missing=out/'missing formula.xlsx';make_workbook(missing,{'D4':'2/0/0/0/98/0'},1,1,formula_cache={'D4':None})
        load_book(missing);enter('range','D4:D4');click('cache');click('check_recipes')
        wait(lambda s:'missing value, formula cache' in s.get('status',''),'Missing formula cache refused despite confirmation');dismiss()
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
        wait(lambda s:'Check transpose and orientation' in s.get('status',''),'Dimension mismatch is visible after transpose');dismiss()
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
        command=[str(folder/'advanced/GridCAD-core.exe'),'inspect','--project',str(example/'DO_NOT_PRINT.PRINT'),'--workbook',str(example/'DO_NOT_PRINT.xlsx')]
        inspected=subprocess.run(command,cwd=out,capture_output=True,text=True,check=True)
        assert json.loads(inspected.stdout)['profile']==core.PROFILE;checks.append('Bundled agent CLI executes outside source tree')
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
