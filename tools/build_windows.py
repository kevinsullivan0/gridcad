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
VERSION='0.2.0-rc.1'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def zip_folder(folder,destination):
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(folder.rglob('*')):
            if path.is_file():z.write(path,Path(folder.name)/path.relative_to(folder))


def main():
    if sys.platform!='win32':raise SystemExit('Build this distribution on Windows; no cross-build claims.')
    for name,script,console in [('GridCAD','gridcad_desktop.py',False),('GridCAD-core','desktop_cli.py',True)]:
        args=[sys.executable,'-m','PyInstaller','--clean','--noconfirm','--onedir','--name',name,'--icon','resources/gridcad.ico','--paths','operator','--collect-submodules','gridcad_operator',
              '--add-data','operator/gridcad_operator/material_converter.py;gridcad_operator']
        if not console:args+=['--windowed','--add-data','docs;docs','--add-data','examples/rectangular;examples/rectangular','--add-data','resources;resources']
        subprocess.run(args+[script],cwd=ROOT,check=True)
    folder=ROOT/'dist/GridCAD';companion=ROOT/'dist/GridCAD-core'
    shutil.copytree(companion,folder/'advanced',dirs_exist_ok=True)
    for source in ['docs','examples/rectangular','operator']:
        shutil.copytree(ROOT/source,folder/source,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ['README.md','AGENTS.md','desktop_core.py','desktop_cli.py','gridcad_desktop.py']:
        shutil.copy2(ROOT/name,folder/name)
    shutil.copytree(ROOT/'tools',folder/'tools',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    notices=folder/'THIRD_PARTY_NOTICES';notices.mkdir(exist_ok=True)
    for package in ['pillow','pyinstaller']:
        dist=importlib.metadata.distribution(package)
        for item in dist.files or []:
            if any(k in str(item).lower() for k in ('license','copying','notice')) and dist.locate_file(item).is_file():
                target=notices/package/Path(str(item)).name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dist.locate_file(item),target)
    prefix=Path(sys.base_prefix)
    for source in [prefix/'LICENSE.txt',prefix/'tcl/tcl8.6/license.terms',prefix/'tcl/tk8.6/license.terms']:
        if source.exists():shutil.copy2(source,notices/(source.parent.name+'-'+source.name))
    packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata['Name']}
    (folder/'BUILD_PROVENANCE.json').write_text(json.dumps({'python':sys.version,'platform':sys.platform,'packages':packages,'runtime_download_at_first_launch':False,'signed':False},indent=2),encoding='utf-8')
    entries=[{'path':str(p.relative_to(folder)).replace('\\','/'),'size':p.stat().st_size,'sha256':digest(p)} for p in sorted(folder.rglob('*')) if p.is_file()]
    (folder/'PACKAGE_MANIFEST.json').write_text(json.dumps(entries,indent=2),encoding='utf-8')
    destination=ROOT/f'dist/GridCAD-Windows-x64-v{VERSION}.zip';zip_folder(folder,destination)
    portable=ROOT/'dist/GridCAD-portable-core';portable.mkdir(exist_ok=True)
    for name in ['desktop_core.py','desktop_cli.py','AGENTS.md']:
        shutil.copy2(ROOT/name,portable/name)
    for source in ['operator','docs','examples/rectangular']:
        shutil.copytree(ROOT/source,portable/source,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (portable/'tools').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'tools/make_desktop_examples.py',portable/'tools/make_desktop_examples.py')
    zip_folder(portable,ROOT/f'dist/GridCAD-portable-core-v{VERSION}.zip')
    sums=''.join(digest(p)+'  '+p.name+'\n' for p in sorted((ROOT/'dist').glob('*.zip')))
    (ROOT/'dist/SHA256SUMS.txt').write_text(sums,encoding='utf-8')
    print(sums)


if __name__=='__main__':main()
