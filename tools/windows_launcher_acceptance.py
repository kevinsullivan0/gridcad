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
from contextlib import contextmanager


@contextmanager
def missing_python_discovery(out):
    """Disposable CI only: hide discovery registrations, never installed files.

    Preserve/restore each complete 3.13 registry subtree even if the official
    installer creates or changes it. This does not touch Windows security policy.
    """
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("The missing-Python fixture is only for disposable GitHub Actions runners")
    import winreg
    key_name=r"Software\Python\PythonCore\3.13"
    def read_tree(hive, path):
        try:key=winreg.OpenKey(hive,path,0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY)
        except FileNotFoundError:return None
        with key:
            children,values,_=winreg.QueryInfoKey(key)
            return ([winreg.EnumValue(key,i) for i in range(values)],
                    {winreg.EnumKey(key,i):read_tree(hive,path+"\\"+winreg.EnumKey(key,i)) for i in range(children)})
    def remove_tree(hive,path):
        try:key=winreg.OpenKey(hive,path,0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY)
        except FileNotFoundError:return
        with key:children=[winreg.EnumKey(key,i) for i in range(winreg.QueryInfoKey(key)[0])]
        for child in children:remove_tree(hive,path+"\\"+child)
        winreg.DeleteKeyEx(hive,path,winreg.KEY_WOW64_64KEY)
    def restore_tree(hive,path,snapshot):
        remove_tree(hive,path)
        if snapshot is None:return
        values,children=snapshot
        with winreg.CreateKeyEx(hive,path,0,winreg.KEY_WRITE|winreg.KEY_WOW64_64KEY) as key:
            for name,value,kind in values:winreg.SetValueEx(key,name,0,kind,value)
        for name,child in children.items():restore_tree(hive,path+"\\"+name,child)
    # No ordinary Python installation is renamed, deleted or modified.
    local=Path(os.environ["LOCALAPPDATA"])
    assert not (local/"GridCAD/Python313").exists(),"fixture requires an unused dedicated installer target"
    assert not (local/"Programs/Python/Python313/python.exe").exists(),"fixture would still find an ordinary per-user install"
    snapshots={h:read_tree(h,key_name) for h in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE)}
    try:
        for hive in snapshots:
            with winreg.CreateKeyEx(hive,key_name+r"\InstallPath",0,winreg.KEY_WRITE|winreg.KEY_WOW64_64KEY) as key:
                winreg.SetValueEx(key,"",0,winreg.REG_SZ,str(out/"no Python installed here"))
        yield
    finally:
        errors=[]
        for hive,snapshot in snapshots.items():
            try:
                restore_tree(hive,key_name,snapshot)
                assert read_tree(hive,key_name)==snapshot
            except Exception as exc:errors.append(str(exc))
        if errors:raise RuntimeError('Could not restore Python discovery fixture: '+'; '.join(errors))


def acceptance(args):
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
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
        try:
            # Explicit consent is supplied only in this disposable CI acceptance run.
            # The real launcher still displays and requires its normal consent prompt.
            process.stdin.write('Y\n');process.stdin.flush()
            deadline=time.monotonic()+240
            window=None
            while time.monotonic()<deadline:
                if process.poll() is not None:
                    log.flush();print((out/(label+'.log')).read_text(encoding='utf-8',errors='replace'),flush=True)
                    raise AssertionError(f'{label}: launcher exited {process.returncode}; see log')
                matches=Desktop(backend='uia').windows(title_re=r'GridCAD.*',visible_only=True)
                matches=[w for w in matches if w.class_name()=='TkTopLevel']
                if matches:window=matches[-1];break
                time.sleep(.5)
            if window is None:
                raise AssertionError(label+': source GUI did not open; see log')
            window.maximize();window.set_focus();time.sleep(.5)
            # Import explicitly so an unavailable encoder reports its real import
            # error rather than Pillow's generic 'unknown extension' fallback.
            from PIL import PngImagePlugin
            ImageGrab.grab().save(out/(label+'.png'), format='PNG')
            window.close();process.wait(timeout=30)
            assert process.returncode==0,label
            checks.append(label+' opens and closes the real source GUI through the BAT')
        finally:
            if process.poll() is None:
                subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/taskkill.exe'),'/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=30)
                process.wait(timeout=30)
            log.close()

    if args.install_fixture:
        before=Path(os.environ['LOCALAPPDATA'])/'GridCAD/Python313'
        declined=subprocess.run([os.environ['COMSPEC'],'/d','/c',str(app/'Start GridCAD.bat')],cwd=app,env=env,input='N\n\n',capture_output=True,text=True,timeout=30)
        (out/'00-install-declined.log').write_text(declined.stdout+declined.stderr,encoding='utf-8')
        assert declined.returncode==2 and not before.exists()
        checks.append('Declining Python installation leaves the dedicated runtime absent')
    run('01-first-setup')
    if args.install_fixture:
        assert 'Installing or repairing verified Python' in (out/'01-first-setup.log').read_text()
        checks.append('Explicit consent downloads, verifies and installs official per-user Python before real GUI startup')
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

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--zip',required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--install-fixture',action='store_true');args=parser.parse_args()
    if args.install_fixture:
        with missing_python_discovery(Path(args.out).resolve()):acceptance(args)
    else:acceptance(args)

if __name__=='__main__':main()
