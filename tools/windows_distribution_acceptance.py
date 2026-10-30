"""Independent Windows distribution journey automation and acceptance oracle.

With --zip/--out, run the actual BAT and desktop shortcut on a disposable Windows
desktop. Without arguments, print the full acceptance checklist. --report checks
recorded manual evidence structure, not execution. windows_gui_acceptance.py
supplies separate real-control/open/preview/save evidence.
Report shape: {"platform": "Windows", "artifact_sha256": "...", "cases":
{"first_run_exe": {"status": "pass", "evidence": ["path/to/log-or-image"]}, ...}}.
Evidence must be existing nonempty files relative to the report directory. The
operator remains responsible for their content; file existence is not proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

CASES = {
    'download_extract': 'Download the single EXE+source ZIP; compare its published SHA256; extract with Explorer to a path containing spaces and nonASCII. Clearly identify Start GridCAD.bat without requiring a command prompt.',
    'first_run_exe': 'As an ordinary Windows user without Python on PATH, double-click Start GridCAD.bat. No administrator/security-policy changes. One responsive real GUI, truthful EXE readiness, version and installed path recorded; no Python install for healthy EXE.',
    'shortcut_opt_in': 'Accept desktop shortcut creation. Inspect actual .lnk target, arguments, working directory and icon; all resolve inside the completed per-user installation, never the download folder.',
    'shortcut_opt_out': 'Decline optional shortcut. App still opens and no new desktop shortcut appears.',
    'real_open_preview_save': 'Use actual controls and native dialogs to open generated synthetic inputs, inspect preview, and save a NEW candidate outside installation. Reopen the saved candidate; original inputs/prior outputs remain byte-identical. Retain windows_gui_acceptance.py evidence.',
    'download_relocated_deleted': 'Close app; move then delete only extracted download. Open shortcut after each operation. Installed app/source/resources/help still work; saving does not depend on deleted download.',
    'repeat_setup': 'Close and repeat setup from same archive. Existing complete version reused or safely verified; shortcut remains usable, no duplicate runtime installation, no unexpected dependency consent or user-file changes.',
    'concurrent_setup': 'Start setup twice normally. Second instance waits or explains retry; no partial final app, broken shortcut, duplicate fallback GUI, or uncontrolled competing dependency installs.',
    'interrupted_setup': 'In a disposable test account, cancel/close setup during ordinary copying, then retry. Only complete tree becomes active, retry recovers, and any pre-existing working version stays usable. Do not inject races or modify another user installation.',
    'slow_live_exe': 'Observe a legitimately slow but live EXE startup. A readiness timeout identifies alive-but-not-ready and offers wait/retry/diagnostics; source must not auto-launch beside it.',
    'exe_failure_truthful': 'Use a documented ordinary unavailable/corrupt-EXE fixture. Failure distinguishes exit-before-ready, missing EXE, timeout and actual observed Windows block; arbitrary crash is not called a security block. No protection bypass advice.',
    'fallback_consent_cancel': 'With EXE genuinely unavailable and no usable Python, choose source fallback then cancel dependency consent. Nothing installed; explicit canceled result and usable retry instructions, no spurious success.',
    'fallback_first_repeat': 'Approve source dependency setup in disposable account, launch responsive source GUI, close, and repeat offline. Verify source resources load and subsequent launch needs no redundant installation. Record dependency download/source/checksum and result.',
    'fallback_failure_recovery': 'Ordinary offline/download failure during consented dependency setup produces visible actionable error plus log, not false security diagnosis. Reconnect and retry successfully without damaging working app or user projects.',
    'upgrade_preserves': 'Keep previous released app and synthetic saved project; install newer candidate side by side/versioned. Verify old app and project hashes preserved, new shortcut launches new complete version, current-version identity is truthful. Never modify immutable v1.0.0 release assets.',
    'removal_preserves': 'Follow documented removal in disposable account. Remove only explicitly named GridCAD-owned app/shortcut/cache components. Preserve synthetic projects, prior outputs and independently installed Python; explain separately any retained GridCAD-owned Python.',
    'diagnostics': 'Retain artifact hash, OS/build, user mode, EXE/source/version/path, startup ready/exit/timeout result, dependency consent/result, actionable log location and screenshots. Logs contain no private project contents or secrets.',
}


def validate(report: dict, base: Path) -> list[str]:
    errors = []
    if report.get('platform') != 'Windows':
        errors.append('platform must be Windows; static/non-Windows tests are insufficient')
    if not re.fullmatch(r'[0-9a-fA-F]{64}', str(report.get('artifact_sha256', ''))):
        errors.append('artifact_sha256 must identify the exact tested ZIP')
    cases = report.get('cases', {})
    if not isinstance(cases, dict):
        return errors + ['cases must be an object']
    for key in CASES:
        item = cases.get(key, {})
        if not isinstance(item, dict) or item.get('status') != 'pass':
            errors.append(f'{key}: not passed (not-run is not acceptance)')
            continue
        evidence = item.get('evidence')
        if not isinstance(evidence, list) or not evidence:
            errors.append(f'{key}: requires evidence files')
            continue
        for name in evidence:
            if not isinstance(name, str):
                errors.append(f'{key}: invalid evidence path')
                continue
            path = base / name
            if not path.is_file() or not path.stat().st_size:
                errors.append(f'{key}: missing/empty evidence {name}')
    return errors


CONSENT_PROMPTS = (
    'Press Enter to set up and open GridCAD, or type N to cancel',
    'Create or update a GridCAD shortcut on your Desktop? Press Enter for Yes, or type N',
    'Try the source launch method now? Type Y to continue, or press Enter to cancel',
    'Install these free components now? Type Y to continue, or press Enter to cancel',
    'Set up GridCAD now? Type Y to continue, or press Enter to cancel:',
)


class ConsentFeeder:
    """One ordinary reply per newly displayed public prompt, never read-ahead.

    Input is the complete append-only observed stdout log. Do not prefill a
    parent shell's stdin: its buffered reader can consume a child's future reply.
    """
    def __init__(self):
        self.cursor = 0
        self.answered_count = 0

    def next_reply(self, observed_text):
        matches = [(position, prompt) for prompt in CONSENT_PROMPTS
                   if (position := observed_text.find(prompt, self.cursor)) >= 0]
        if not matches:
            return None
        position, prompt = min(matches)
        self.cursor = position + len(prompt)
        self.answered_count += 1
        return 'Y\n'


def make_nonexecutable_fixture(app: Path) -> None:
    """Alter only a disposable extracted copy, preserving integrity verification."""
    import hashlib
    exe = app / 'GridCAD.exe'
    manifest_path = app / 'INSTALL_MANIFEST.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    entries = [entry for entry in manifest['files'] if entry['path'] == 'GridCAD.exe']
    if len(entries) != 1:
        raise ValueError('Fixture requires exactly one GridCAD.exe manifest entry')
    content = b'GridCAD ordinary functional fixture: deliberately not an executable.\r\n'
    exe.write_bytes(content)
    entries[0]['size'] = len(content)
    entries[0]['sha256'] = hashlib.sha256(content).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')


def acceptance(args):
    """Operate only a fresh disposable Windows artifact installation."""
    import hashlib
    import os
    import shutil
    import subprocess
    import time
    import zipfile
    from pywinauto import Desktop
    from PIL import ImageGrab, PngImagePlugin  # explicit encoder registration

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    extracted = out / "download with spaces é & !"
    local = out / "local app data é & !"
    if extracted.exists() or local.exists():
        raise RuntimeError('Use a fresh --out directory; existing installations are never removed')
    with zipfile.ZipFile(args.zip) as archive:
        archive.extractall(extracted)
    app = extracted / 'GridCAD'
    for name in ('Start GridCAD.bat', 'Troubleshooting/Start GridCAD from source.bat',
                 'tools/windows_launcher.ps1', 'tools/source_launcher.py',
                 'GridCAD.exe', 'gridcad_desktop.py'):
        assert (app / name).is_file(), name
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('PYTHON')}
    env['LOCALAPPDATA'] = str(local)
    system = Path(os.environ['SystemRoot']) / 'System32'
    env['PATH'] = str(system) + os.pathsep + str(system.parent)
    powershell = str(system / 'WindowsPowerShell/v1.0/powershell.exe')

    def ps(code):
        code = '[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); ' + code
        result = subprocess.run([powershell, '-NoProfile', '-Command', code],
                                env=env, capture_output=True, text=True, encoding='utf-8',
                                errors='strict', check=True, timeout=30)
        return result.stdout.strip()

    desktop = Path(ps("[Environment]::GetFolderPath('Desktop')"))
    shortcut = desktop / 'GridCAD.lnk'
    if shortcut.exists():
        raise RuntimeError('Refusing to overwrite an existing GridCAD desktop shortcut; use disposable CI')
    if any(w.class_name() == 'TkTopLevel' for w in Desktop(backend='uia').windows(title_re=r'GridCAD.*', visible_only=True)):
        raise RuntimeError('Close existing GridCAD windows before disposable acceptance')
    checks = []
    active = []
    observed_gui_pids = set()
    version = (app / 'VERSION.txt').read_text(encoding='utf-8').strip()
    installed = local / 'GridCAD/Apps' / version

    def batch(path, *flags):
        # cmd /s strips exactly the outer quote pair. Avoid list2cmdline's C
        # runtime quoting rules, which are not CMD's parsing rules. Only fixed
        # public switch names are appended; the actual path stays quoted.
        assert all(flag in ('-NoShortcut', '-Source') for flag in flags)
        return f'"{os.environ["COMSPEC"]}" /d /v:off /s /c ""{path}" {" ".join(flags)}"'

    def shortcut_command(path):
        return f'"{os.environ["COMSPEC"]}" /d /v:off /s /c "start "" /wait "{path}""'

    def launch(label, command, expected_mode, consent=True):
        logpath = out / (label + '.log')
        log = logpath.open('w', encoding='utf-8')
        process = subprocess.Popen(command, cwd=out, env=env, stdin=subprocess.PIPE,
                                   stdout=log, stderr=subprocess.STDOUT, text=True)
        active.append(process)
        # Observe public prompts and reply only when each actually appears.
        # Parent PowerShell and child Python must not share prefilled replies.
        feeder = ConsentFeeder() if consent else None
        if not consent:
            process.stdin.close()
        window = None
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            if feeder is not None:
                observed = logpath.read_text(encoding='utf-8', errors='replace')
                reply = feeder.next_reply(observed)
                if reply is not None:
                    try:
                        process.stdin.write(reply)
                        process.stdin.flush()
                    except (BrokenPipeError, OSError) as exc:
                        raise AssertionError(label + ': input closed while answering displayed prompt') from exc
            matches = [w for w in Desktop(backend='uia').windows(title_re=r'GridCAD.*', visible_only=True)
                       if w.class_name() == 'TkTopLevel']
            if matches:
                assert len(matches) == 1, 'Unexpected duplicate GridCAD GUI'
                window = matches[0]
                break
            if process.poll() not in (None, 0):
                raise AssertionError(f'{label}: launcher exited {process.returncode}; {logpath}')
            time.sleep(.3)
        assert window is not None, f'{label}: no real GUI; see {logpath}'
        pid = window.process_id()
        info = json.loads(ps(f"Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" | Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"))
        executable = Path(info['ExecutablePath'])
        observed_gui_pids.add(pid)
        if expected_mode == 'exe':
            assert executable.resolve() == (installed / 'GridCAD.exe').resolve(), info
        else:
            assert executable.name.lower() in ('python.exe', 'pythonw.exe'), info
            assert 'gridcad_desktop.py' in info['CommandLine'], info
        if label == '00-shortcut-declined':
            contender = subprocess.run(batch(installed / 'Start GridCAD.bat', '-NoShortcut'),
                                       cwd=out, env=env, input='Y\n\n', capture_output=True,
                                       text=True, timeout=30)
            (out / 'concurrent-launch.log').write_text(contender.stdout + contender.stderr, encoding='utf-8')
            assert contender.returncode == 0 and 'already open or starting' in contender.stdout, contender.stdout
            windows = [w for w in Desktop(backend='uia').windows(title_re=r'GridCAD.*', visible_only=True)
                       if w.class_name() == 'TkTopLevel']
            assert len(windows) == 1 and windows[0].process_id() == pid
            checks.append('Concurrent ordinary BAT launch reports already open and does not start second GUI')
        window.maximize()
        window.set_focus()
        time.sleep(.5)
        ImageGrab.grab().save(out / (label + '.png'), format='PNG')
        (out / (label + '-process.json')).write_text(json.dumps(info, indent=2), encoding='utf-8')
        window.close()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            remaining = [w for w in Desktop(backend='uia').windows(visible_only=True)
                         if w.process_id() == pid and w.class_name() == 'TkTopLevel']
            if not remaining:
                break
            time.sleep(.2)
        assert not remaining, label + ': GUI did not close normally'
        process.wait(timeout=30)
        assert process.returncode == 0, f'{label}: launcher exit {process.returncode}'
        log.close()
        (out / (label + '-consent.json')).write_text(json.dumps({'displayed_prompts_answered': feeder.answered_count if feeder else 0, 'stdin_closed': not consent}), encoding='utf-8')
        checks.append(label + ': actual responsive GUI and expected process mode; normal close')

    def expect_refusal(label, expected_code, expected_text):
        result = subprocess.run(batch(app / 'Start GridCAD.bat', '-NoShortcut'),
                                cwd=out, env=env, input='N\n\n', capture_output=True,
                                text=True, timeout=120)
        (out / (label + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
        assert result.returncode == expected_code, (label, result.returncode, result.stdout, result.stderr)
        assert expected_text in result.stdout, (label, result.stdout)
        checks.append(label + ': truthful refusal and expected exit status')

    def offline_source_repeat(label):
        preference = local / ('GridCAD/Launcher/' + version + '-mode.txt')
        assert preference.read_text(encoding='ascii').strip() == 'source'
        saved_preference = preference.read_bytes()
        env['HTTP_PROXY'] = env['HTTPS_PROXY'] = 'http://127.0.0.1:1'
        try:
            launch(label, batch(installed / 'Start GridCAD.bat', '-NoShortcut'), 'source', consent=False)
        finally:
            env.pop('HTTP_PROXY', None)
            env.pop('HTTPS_PROXY', None)
        text = (out / (label + '.log')).read_text(encoding='utf-8', errors='replace')
        assert 'Opening the included Windows app' not in text, text
        assert 'Try the source launch method now?' not in text, text
        assert 'Install these free components now?' not in text, text
        assert 'Set up GridCAD now?' not in text, text
        assert 'No downloads or installation needed' in text, text
        assert preference.read_bytes() == saved_preference
        checks.append('Default offline launch reuses persisted source preference without EXE retry or dependency consent')

    try:
        if args.exe_failure_fixture:
            make_nonexecutable_fixture(app)
            launch('fixture-actual-exe-failure-source', batch(app / 'Start GridCAD.bat', '-NoShortcut'), 'source')
            text = (out / 'fixture-actual-exe-failure-source.log').read_text(encoding='utf-8', errors='replace')
            assert 'The Windows app did not start:' in text, text
            assert 'Try the source launch method now?' in text, text
            assert 'Opening the source launch method' in text, text
            assert 'Windows security blocked' not in text and 'was blocked by Windows' not in text, text
            checks.append('Inert non-executable EXE fixture triggers actual launch failure then ordinary consented source fallback')
            offline_source_repeat('fixture-default-source-offline')
            report = {'status': 'passed', 'fixture': 'extracted EXE replaced by inert text; matching install manifest entry updated',
                      'artifact_sha256': hashlib.sha256(args.zip.read_bytes()).hexdigest(),
                      'version': version, 'checks': checks,
                      'limits': ['Disposable fixture only; original published ZIP unchanged.',
                                 'Functional launch-failure recovery, not Windows security compatibility certification.']}
            (out / 'acceptance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps(report, indent=2))
            return
        manifest_path = app / 'INSTALL_MANIFEST.json'
        manifest_bytes = manifest_path.read_bytes()
        try:
            invalid = json.loads(manifest_bytes)
            invalid['version'] = 'unsupported-fixture'
            manifest_path.write_text(json.dumps(invalid), encoding='utf-8')
            expect_refusal('invalid-manifest', 1, 'unsupported installation manifest')
            assert not installed.exists(), 'Invalid manifest unexpectedly installed an app'
        finally:
            manifest_path.write_bytes(manifest_bytes)
        expect_refusal('setup-canceled', 2, 'Setup canceled')
        assert not installed.exists(), 'Canceled setup unexpectedly installed an app'
        prior = local / 'GridCAD/Apps/1.0.0/keep.txt'
        prior.parent.mkdir(parents=True)
        prior.write_bytes(b'synthetic previous version sentinel; do not remove')
        launch('00-shortcut-declined', batch(app / 'Start GridCAD.bat', '-NoShortcut'), 'exe')
        assert not shortcut.exists(), 'NoShortcut unexpectedly created desktop shortcut'
        checks.append('NoShortcut opt-out opens app without desktop mutation')
        launch('01-first-bat-exe', batch(app / 'Start GridCAD.bat'), 'exe')
        assert prior.read_bytes() == b'synthetic previous version sentinel; do not remove'
        checks.append('Current-version setup preserves previous-version synthetic sentinel')
        # An ordinary edited installed file must not be silently replaced.
        installed_version = installed / 'VERSION.txt'
        saved_version = installed_version.read_bytes()
        try:
            installed_version.write_bytes(b'synthetic local change')
            expect_refusal('changed-install-preserved', 1, 'incomplete or changed')
            assert installed_version.read_bytes() == b'synthetic local change'
            assert prior.read_bytes() == b'synthetic previous version sentinel; do not remove'
        finally:
            installed_version.write_bytes(saved_version)
        assert shortcut.is_file(), 'Consented desktop shortcut not created'
        env['GRIDCAD_ACCEPTANCE_SHORTCUT'] = str(shortcut)
        link = json.loads(ps("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:GRIDCAD_ACCEPTANCE_SHORTCUT); @{target=$s.TargetPath;arguments=$s.Arguments;working_directory=$s.WorkingDirectory;icon=$s.IconLocation}|ConvertTo-Json -Compress"))
        assert Path(link['target']).resolve() == (installed / 'Start GridCAD.bat').resolve(), link
        assert Path(link['working_directory']).resolve() == installed.resolve(), link
        assert str(extracted).lower() not in json.dumps(link).lower(), link
        (out / 'shortcut.json').write_text(json.dumps(link, indent=2), encoding='utf-8')
        checks.append('Desktop shortcut uses installed launcher and working directory, not download')
        assert not (local / 'GridCAD/Python313').exists(), 'Healthy EXE installed source Python unnecessarily'
        launch('02-repeat-bat-exe', batch(app / 'Start GridCAD.bat', '-NoShortcut'), 'exe')
        shutil.rmtree(extracted)
        launch('03-deleted-download-shortcut', shortcut_command(shortcut), 'exe')
        if args.source:
            launch('04-installed-forced-source', batch(installed / 'Start GridCAD.bat', '-Source', '-NoShortcut'), 'source')
            offline_source_repeat('05-default-source-offline')
        report = {'status': 'passed', 'artifact_sha256': hashlib.sha256(args.zip.read_bytes()).hexdigest(),
                  'version': version, 'checks': checks,
                  'limits': ['Hosted Windows functional evidence is not user-device or Smart App Control acceptance.',
                             'Full native open/preview/save suite is separately required via windows_gui_acceptance.py.',
                             'Interrupted install, slow live EXE, full prior-version execution/removal and dependency recovery remain manual CASES unless separately evidenced.',
                             'Forced source branch executed.' if args.source else 'Source dependency branch not requested.']}
        (out / 'acceptance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
    finally:
        # Only clean the shortcut created by this fresh run; test installation
        # and logs remain for diagnosis. Never remove arbitrary user projects.
        if shortcut.exists():
            shortcut.unlink()
        for pid in observed_gui_pids:
            # A known GUI may outlive a launcher that already returned. Ask its
            # actual window to close; do not kill unrelated system processes.
            for window in Desktop(backend='uia').windows(visible_only=True):
                if window.process_id() == pid and window.class_name() == 'TkTopLevel':
                    window.close()
        for process in active:
            if process.poll() is None:
                subprocess.run([str(system / 'taskkill.exe'), '/PID', str(process.pid), '/T', '/F'],
                               capture_output=True, timeout=30)
                process.wait(timeout=30)


def main() -> int:
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, help='combined Windows artifact to exercise')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--source', action='store_true', help='also exercise consented forced source startup')
    parser.add_argument('--exe-failure-fixture', action='store_true', help='separate disposable extracted-package EXE launch-failure/source-recovery journey')
    parser.add_argument('--report', type=Path, help='validate an existing full manual matrix report')
    args = parser.parse_args()
    if args.zip:
        if sys.platform != 'win32':
            parser.error('Real distribution acceptance requires Windows desktop interaction')
        if not args.out:
            parser.error('--out is required with --zip')
        acceptance(args)
        return 0
    if args.report is None:
        print(json.dumps({'acceptance_cases': CASES, 'notice': 'Checklist only; no Windows tests were executed.'}, indent=2))
        return 0
    try:
        report = json.loads(args.report.read_text(encoding='utf-8'))
        if not isinstance(report, dict):
            raise ValueError('report must be an object')
        errors = validate(report, args.report.resolve().parent)
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    print(json.dumps({'report_structure_accepted': not errors, 'errors': errors,
                      'notice': 'Evidence existence checked, not evidence contents.'}, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
