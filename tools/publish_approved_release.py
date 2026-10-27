"""Publish only the exact previously audited passing CI artifact. No rebuild."""
import hashlib,json,os,pathlib,subprocess,zipfile

def gh(*args):return subprocess.check_output(['gh',*args],text=True)
a=json.loads(pathlib.Path('.github/release-approved.json').read_text())
repo=os.environ['GH_REPO']
assert repo=='kevinsullivan0/gridcad'
assert a['tag']=='v0.2.0-rc.2' and a['independent_audit_approved'] is True
run=json.loads(gh('api',f'repos/{repo}/actions/runs/{a["run_id"]}'))
assert run['conclusion']=='success' and run['head_sha']==a['source_sha'] and run['head_branch']=='windows-desktop'
pathlib.Path('release-assets').mkdir()
gh('run','download',str(a['run_id']),'--repo',repo,'--name','GridCAD-Windows-desktop-candidate','--dir','release-assets')
folder=pathlib.Path('release-assets')
for name,sha in a['assets'].items():
    path=folder/name
    assert path.name==name and hashlib.sha256(path.read_bytes()).hexdigest()==sha,name
with zipfile.ZipFile(folder/'GridCAD-Windows-GUI-evidence.zip') as z:
    member=next(n for n in z.namelist() if pathlib.PurePosixPath(n).name=='acceptance.json')
    assert json.loads(z.read(member))['status']=='passed'
sums=''.join(sha+'  '+name+'\n' for name,sha in sorted(a['assets'].items()))
(folder/'SHA256SUMS.txt').write_text(sums)
notes=pathlib.Path('docs/RELEASE_NOTES.md').read_text()+f'\nSource commit: `{a["source_sha"]}`. Verified Windows run: https://github.com/{repo}/actions/runs/{a["run_id"]}.\n'
pathlib.Path('release-notes.txt').write_text(notes)
# Never reuse or move a preexisting tag or replace a release.
refs=json.loads(gh('api',f'repos/{repo}/git/matching-refs/tags/{a["tag"]}'))
assert not any(r['ref']=='refs/tags/'+a['tag'] for r in refs), 'Tag already exists; inspect rather than overwrite'
gh('release','create',a['tag'],'--repo',repo,'--target',a['source_sha'],'--prerelease','--title','GridCAD 0.2.0-rc.2 — Windows desktop candidate','--notes-file','release-notes.txt',*[str(folder/n) for n in a['assets']],str(folder/'SHA256SUMS.txt'))
