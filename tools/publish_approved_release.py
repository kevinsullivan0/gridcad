"""Publish only exact, passing, hash-bound Windows artifacts; never rebuild."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

REPOSITORY='kevinsullivan0/gridcad'
TAG='v1.0.2'
BRANCH='main'
REQUIRED_ASSETS={
    'GridCAD-Windows-x64-v1.0.2.zip',
    'GridCAD-Source-Windows-v1.0.2.zip',
    'GridCAD-portable-core-v1.0.2.zip',
    'GridCAD-Windows-GUI-evidence.zip',
    'GridCAD-launcher-evidence.zip',
    'GridCAD-distribution-evidence.zip',
}


def gh(*args):
    return subprocess.check_output(['gh',*args],text=True)


def validate_release(record,run,folder):
    """Validate a frozen release record without network or publication."""
    folder=Path(folder)
    if record.get('tag')!=TAG or record.get('verification_passed') is not True:
        raise ValueError('This publication path requires a verified GridCAD 1.0.2 record.')
    if (run.get('id')!=record.get('run_id')
            or run.get('path')!='.github/workflows/windows-desktop.yml'
            or run.get('status')!='completed' or run.get('conclusion')!='success'
            or run.get('head_sha')!=record.get('source_sha')
            or run.get('head_branch')!=BRANCH):
        raise ValueError('The exact source revision must have a passing Windows run.')
    assets=record.get('assets',{})
    if set(assets)!=REQUIRED_ASSETS:
        raise ValueError('Release assets must be the complete, explicit 1.0.2 set.')
    for name,digest in assets.items():
        if Path(name).name!=name or not re.fullmatch(r'[0-9a-f]{64}',digest):
            raise ValueError('Invalid asset filename or SHA256.')
        path=folder/name
        if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Asset digest mismatch: '+name)
    for name in ('GridCAD-Windows-GUI-evidence.zip','GridCAD-launcher-evidence.zip','GridCAD-distribution-evidence.zip'):
        with zipfile.ZipFile(folder/name) as archive:
            members=[n for n in archive.namelist() if Path(n).name=='acceptance.json']
            expected=({'distribution-qa/acceptance.json','fallback-qa/acceptance.json'}
                      if name=='GridCAD-distribution-evidence.zip' else None)
            if ((expected is not None and set(members)!=expected)
                    or (expected is None and len(members)!=1)
                    or any(json.loads(archive.read(member)).get('status')!='passed' for member in members)):
                raise ValueError('Missing or failed Windows acceptance: '+name)
            if expected is not None:
                combined=assets['GridCAD-Windows-x64-v1.0.2.zip']
                if any(json.loads(archive.read(member)).get('artifact_sha256')!=combined for member in members):
                    raise ValueError('Windows distribution evidence belongs to another ZIP.')



def main():
    repo=os.environ.get('GH_REPO')
    if repo!=REPOSITORY:
        raise ValueError('Publication destination is not the authorized GridCAD repository.')
    record=json.loads(Path('.github/release-approved.json').read_text())
    run=json.loads(gh('api',f'repos/{repo}/actions/runs/{record["run_id"]}'))
    # Refuse a failed/wrong build before any artifact download.
    if run.get('conclusion')!='success' or run.get('head_sha')!=record.get('source_sha'):
        raise ValueError('The recorded Windows build is not passing at the exact revision.')
    refs=json.loads(gh('api',f'repos/{repo}/git/matching-refs/tags/{TAG}'))
    if any(r['ref']=='refs/tags/'+TAG for r in refs):
        raise ValueError('Tag already exists; inspect instead of replacing it.')
    with tempfile.TemporaryDirectory(prefix='gridcad-publish-') as temporary:
        folder=Path(temporary)
        gh('run','download',str(record['run_id']),'--repo',repo,
           '--name','GridCAD-Windows-desktop-candidate','--dir',str(folder))
        validate_release(record,run,folder)
        sums=''.join(digest+'  '+name+'\n' for name,digest in sorted(record['assets'].items()))
        (folder/'SHA256SUMS.txt').write_text(sums,encoding='utf-8')
        notes=Path('docs/RELEASE_NOTES.md').read_text(encoding='utf-8').split('\n## Earlier releases',1)[0]
        recommended=f'GridCAD-Windows-x64-{TAG}.zip'
        notes=('## Download\n\n'
               f'**Windows users: download [{recommended}](https://github.com/{repo}/releases/download/{TAG}/{recommended}).** '
               'Extract the whole ZIP and open **Start GridCAD.bat**. It includes the app, source fallback and toolkit; no second ZIP is needed.\n\n'
               'Other attachments are optional:\n'
               f'- `GridCAD-Source-Windows-{TAG}.zip`: source-only launch/setup, for people who specifically prefer that route.\n'
               f'- `GridCAD-portable-core-{TAG}.zip`: advanced scripting toolkit, not the ordinary desktop download.\n'
               '- The three `evidence.zip` files contain software-test records/screenshots, not another app.\n'
               '- `SHA256SUMS.txt` contains integrity checksums. They do not authenticate the publisher.\n'
               '- GitHub-generated **Source code (zip/tar.gz)** archives are repository snapshots, not the ready-to-use Windows package.\n\n'
               '## Changes\n\n'+notes)

        notes+=f'\nSource commit: `{record["source_sha"]}`. Verified Windows run: https://github.com/{repo}/actions/runs/{record["run_id"]}.\n'
        notes_path=folder/'release-notes.txt';notes_path.write_text(notes,encoding='utf-8')
        gh('release','create',TAG,'--repo',repo,'--target',record['source_sha'],
           '--title','GridCAD 1.0.2 — clearer conversion and error recovery',
           '--notes-file',str(notes_path),
           *[str(folder/name) for name in sorted(record['assets'])],str(folder/'SHA256SUMS.txt'))


if __name__=='__main__':main()
