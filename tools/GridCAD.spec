# -*- mode: python ; coding: utf-8 -*-
"""Two independent entry points, one supported PyInstaller onedir collection.

See docs/WINDOWS_PACKAGING.md. Do not replace this with post-build DLL deletion.
"""
from pathlib import Path
import sys
import hashlib
import zipfile
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).parent
operator_path = str(root / 'operator')
# collect_submodules uses the build interpreter's search path, unlike Analysis.
# The operator package is source-local, not installed in site-packages.
sys.path.insert(0, operator_path)
hiddenimports = collect_submodules('gridcad_operator', on_error='raise')

# Snapshot bytes before another Analysis can overwrite generated work files
# (notably base_library.zip, which has one workpath in PyInstaller 6.16).
collected = {}

def base_library_members(source):
    """Compare importable contents, not ZIP entry order or container metadata."""
    members = {}
    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            if member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise RuntimeError('Unsupported zipimport compression in base_library.zip: ' + member.filename)
            if member.filename in members:
                raise RuntimeError('Duplicate base_library.zip member: ' + member.filename)
            members[member.filename] = hashlib.sha256(archive.read(member)).digest()
    return members


def check_shared_files(analysis):
    for table in (analysis.binaries, analysis.datas):
        for destination, source, kind in table:
            key = destination.replace('\\', '/').casefold()
            is_base_library = key == 'base_library.zip' and kind == 'DATA'
            content = (base_library_members(source) if is_base_library
                       else hashlib.sha256(Path(source).read_bytes()).digest())
            fingerprint = (kind, content)
            previous = collected.setdefault(key, fingerprint)
            if previous != fingerprint:
                detail = ''
                if is_base_library and isinstance(previous[1], dict):
                    changed = sorted(name for name in previous[1].keys() | content.keys()
                                     if previous[1].get(name) != content.get(name))
                    detail = '; changed/missing members: ' + ', '.join(
                        name + ' [' + (previous[1][name].hex() if name in previous[1] else 'missing')
                        + ' -> ' + (content[name].hex() if name in content else 'missing') + ']'
                        for name in changed[:10])
                    if len(changed) > 10:
                        detail += ' (and %d more)' % (len(changed) - 10)
                raise RuntimeError('Conflicting shared runtime destination: ' + destination + detail)


common = dict(
    pathex=[str(root), operator_path],
    hiddenimports=hiddenimports,
    datas=[(str(root / 'operator/gridcad_operator/material_converter.py'),
            'gridcad_operator')],
)
gui = Analysis(
    [str(root / 'gridcad_desktop.py')],
    **{**common, 'datas': common['datas'] + [
        (str(root / name), name) for name in (
            'docs', 'examples/rectangular', 'examples/pyramid',
            'examples/mixed', 'resources')
    ]},
    # PNG resources/previews are required; the unused AVIF codec is not.
    excludes=['PIL.AvifImagePlugin', 'PIL._avif'],
)
check_shared_files(gui)
cli = Analysis([str(root / 'desktop_cli.py')], **common)
check_shared_files(cli)

gui_exe = EXE(
    PYZ(gui.pure), gui.scripts, [], exclude_binaries=True,
    name='GridCAD', console=False, icon=str(root / 'resources/gridcad.ico'),
    contents_directory='_internal', version=str(root / 'build/windows-version.txt'),
)
cli_exe = EXE(
    PYZ(cli.pure), cli.scripts, [], exclude_binaries=True,
    name='GridCAD-core', console=True, icon=str(root / 'resources/gridcad.ico'),
    contents_directory='_internal', version=str(root / 'build/windows-version.txt'),
)
# COLLECT combines/deduplicates both analyses' DLL and data tables. Each EXE
# retains its own Python module archive and bootloader mode; neither launches
# the other, and both resolve the same adjacent _internal independently of cwd.
COLLECT(
    gui_exe, cli_exe, gui.binaries, cli.binaries, gui.datas, cli.datas,
    name='GridCAD',
)
