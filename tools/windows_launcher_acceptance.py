"""Exercise the real BAT, isolated setup/reuse and actual source GUI on Windows."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import zipfile


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--zip',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.zip) as z:z.extractall(out/'package with spaces')
    app=out/'package with spaces/GridCAD'
    root=Path(__file__).resolve().parents[1]
    shutil.copy2(root/'Start GridCAD.bat',app/'Start GridCAD.bat')
    shutil.copy2(root/'tools/source_launcher.py',app/'tools/source_launcher.py')
    env=os.environ.copy();env['LOCALAPPDATA']=str(out/'local app data')
    state=Path(env['LOCALAPPDATA'])/'GridCAD/SourceLauncher'
    checks=[]
    from pywinauto import Desktop
    from PIL import ImageGrab

    def run(label):
        log=(out/(label+'.log')).open('w',encoding='utf-8')
        process=subprocess.Popen([os.environ['COMSPEC'],'/d','/c',str(app/'Start GridCAD.bat')],
                                 cwd=app,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True)
        # Explicit consent is supplied only in this disposable CI acceptance run.
        # The real launcher still displays and requires its normal consent prompt.
        process.stdin.write('Y\n');process.stdin.flush()
        deadline=time.monotonic()+240
        window=None
        while time.monotonic()<deadline:
            if process.poll() is not None:raise AssertionError(f'{label}: launcher exited {process.returncode}; see log')
            matches=Desktop(backend='uia').windows(title_re=r'GridCAD.*',visible_only=True)
            matches=[w for w in matches if w.class_name()=='TkTopLevel']
            if matches:window=matches[-1];break
            time.sleep(.5)
        if window is None:
            process.kill();raise AssertionError(label+': source GUI did not open; see log')
        window.set_focus();ImageGrab.grab().save(out/(label+'.png'))
        window.close();process.wait(timeout=30);log.close()
        assert process.returncode==0,label
        checks.append(label+' opens and closes the real source GUI through the BAT')

    run('01-first-setup')
    marker=state/'ready.json';assert marker.is_file()
    before=marker.read_bytes();mtime=marker.stat().st_mtime_ns
    env['HTTPS_PROXY']='http://127.0.0.1:1';env['HTTP_PROXY']='http://127.0.0.1:1'
    run('02-repeat-offline')
    assert marker.read_bytes()==before and marker.stat().st_mtime_ns==mtime
    assert 'No downloads or installation needed' in (out/'02-repeat-offline.log').read_text()
    checks.append('Offline repeat does not reinstall or rewrite readiness')
    env.pop('HTTPS_PROXY');env.pop('HTTP_PROXY')
    marker.unlink();(state/'runtime/partial-setup-proof.txt').write_text('preserve')
    run('03-recover-partial')
    assert len(list(state.glob('incomplete-*/partial-setup-proof.txt')))==1
    checks.append('Interrupted environment is preserved and a working environment is rebuilt')
    # A second setup cannot enter the same state directory concurrently.
    helper=app/'tools/source_launcher.py'
    code="import importlib.util,sys,time;from pathlib import Path;s=importlib.util.spec_from_file_location('launcher',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);\nwith m.setup_lock(Path(sys.argv[2])):\n print('locked',flush=True);time.sleep(15)"
    holder=subprocess.Popen([str(state/'runtime/Scripts/python.exe'),'-I','-c',code,str(helper),str(state)],stdout=subprocess.PIPE,text=True)
    assert holder.stdout.readline().strip()=='locked'
    contender=subprocess.run([str(state/'runtime/Scripts/python.exe'),'-I',str(helper)],env=env,capture_output=True,text=True,timeout=10)
    holder.terminate();holder.wait(timeout=10)
    assert contender.returncode!=0 and 'Another GridCAD setup' in contender.stdout
    checks.append('Concurrent setup refuses cleanly without corrupting the ready environment')
    (out/'acceptance.json').write_text(json.dumps({'status':'passed','checks':checks,'installer_path_exercised':'Installing or repairing verified Python' in (out/'01-first-setup.log').read_text(),
        'limits':['Installer branch coverage depends on whether the runner needed Python; see installer_path_exercised and first-run log.',
                  'Hosted Windows is not Smart App Control compatibility proof.']},indent=2),encoding='utf-8')
    print(json.dumps(checks,indent=2))

if __name__=='__main__':main()
