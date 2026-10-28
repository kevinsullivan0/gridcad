"""Build explicit public deliverables; never glob private workspaces into a release."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSION='0.2.0-rc.5'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def zip_folder(folder,destination):
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(folder.rglob('*')):
            if path.is_file():z.write(path,Path(folder.name)/path.relative_to(folder))


def main():
    if sys.platform!='win32':raise SystemExit('Build this distribution on Windows; no cross-build claims.')
    subprocess.run([sys.executable,'tools/make_desktop_examples.py','examples/rectangular'],cwd=ROOT,check=True)
    for shape in ['pyramid','mixed']:
        subprocess.run([sys.executable,'tools/make_desktop_examples.py','examples/'+shape,'--shape',shape],cwd=ROOT,check=True)
    # Supported multi-entry onedir bundle: both launchers share one _internal.
    subprocess.run([sys.executable,'-m','PyInstaller','--clean','--noconfirm',
                    'tools/GridCAD.spec'],cwd=ROOT,check=True)
    folder=ROOT/'dist/GridCAD'
    if any(p.name.lower().startswith('_avif') for p in folder.rglob('*') if p.is_file()):
        raise RuntimeError('Unused AVIF codec unexpectedly bundled; review the exclusion before release.')
    for source in ['resources','docs','examples/rectangular','examples/pyramid','examples/mixed','operator']:
        shutil.copytree(ROOT/source,folder/source,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ['README.md','AGENTS.md','LICENSE','desktop_core.py','desktop_cli.py','diagnostics.py','gridcad_desktop.py','agent_help.py']:
        shutil.copy2(ROOT/name,folder/name)
    shutil.copytree(ROOT/'tools',folder/'tools',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    notices=folder/'THIRD_PARTY_NOTICES';notices.mkdir(exist_ok=True)
    for package in ['pillow','pyinstaller']:
        dist=importlib.metadata.distribution(package)
        for item in dist.files or []:
            if any(k in str(item).lower() for k in ('license','copying','notice')) and dist.locate_file(item).is_file():
                target=notices/package/Path(str(item)).name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dist.locate_file(item),target)
    prefix=Path(sys.base_prefix)
    import tkinter, ssl
    if not ssl.OPENSSL_VERSION.startswith('OpenSSL 3.5.9 '):
        raise RuntimeError('Review bundled OpenSSL notices for runtime version '+ssl.OPENSSL_VERSION)
    interp=tkinter.Tcl()
    tcl_version=interp.call('info','patchlevel')
    if tcl_version!='8.6.15':
        raise RuntimeError('Review bundled Tcl license for runtime version '+str(tcl_version))
    required_notices=[(prefix/'LICENSE.txt','Python-LICENSE.txt'),
                      (prefix/'tcl/tk8.6/license.terms','Tk-license.terms'),
                      (ROOT/'resources/licenses/tcl8.6.15-license.terms','Tcl-license.terms'),
                      (ROOT/'resources/licenses/openssl-3.5.9-LICENSE.txt','OpenSSL-LICENSE.txt'),
                      (ROOT/'resources/licenses/openssl-3.5.9-AUTHORS.md','OpenSSL-AUTHORS.md')]
    for source,target in required_notices:
        if not source.is_file():raise RuntimeError('Required runtime license missing: '+str(source))
        shutil.copy2(source,notices/target)
    (notices/'SOURCES.txt').write_text('Tcl 8.6.15 license: https://github.com/tcltk/tcl/blob/core-8-6-15/license.terms\nPython and Tk notices copied from the pinned official Python runtime.\nOpenSSL 3.5.9: https://github.com/openssl/openssl/tree/openssl-3.5.9 (LICENSE.txt and AUTHORS.md; no NOTICE file in this tagged source root).\n',encoding='utf-8')
    packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata['Name']}
    (folder/'BUILD_PROVENANCE.json').write_text(json.dumps({'python':sys.version,'platform':sys.platform,'packages':packages,'runtime_download_at_first_launch':False,'signed':False},indent=2),encoding='utf-8')
    entries=[{'path':str(p.relative_to(folder)).replace('\\','/'),'size':p.stat().st_size,'sha256':digest(p)} for p in sorted(folder.rglob('*')) if p.is_file()]
    (folder/'PACKAGE_MANIFEST.json').write_text(json.dumps(entries,indent=2),encoding='utf-8')
    destination=ROOT/f'dist/GridCAD-Windows-x64-v{VERSION}.zip';zip_folder(folder,destination)
    portable=ROOT/'dist/GridCAD-portable-core';portable.mkdir(exist_ok=True)
    for name in ['desktop_core.py','desktop_cli.py','diagnostics.py','AGENTS.md','LICENSE']:
        shutil.copy2(ROOT/name,portable/name)
    for source in ['operator','docs','examples/rectangular','examples/pyramid','examples/mixed']:
        shutil.copytree(ROOT/source,portable/source,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (portable/'tools').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'tools/make_desktop_examples.py',portable/'tools/make_desktop_examples.py')
    zip_folder(portable,ROOT/f'dist/GridCAD-portable-core-v{VERSION}.zip')
    sums=''.join(digest(p)+'  '+p.name+'\n' for p in sorted((ROOT/'dist').glob('*.zip')))
    (ROOT/'dist/SHA256SUMS.txt').write_text(sums,encoding='utf-8')
    print(sums)


if __name__=='__main__':main()
