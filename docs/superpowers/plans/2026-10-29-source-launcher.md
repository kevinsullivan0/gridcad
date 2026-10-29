# GridCAD source launcher implementation plan

> For agentic workers: use superpowers:executing-plans task by task, with tests before implementation.

**Goal:** Double-click a launcher beside the existing RC7 source; set up once and open the same GUI thereafter.

**Architecture:** A readable BAT uses fixed Windows PowerShell commands to discover and validate official Python, or request consent to install the hash-pinned official x64 installer per user. A Python bootstrap owns an isolated per-user environment, installs a hash-pinned Pillow wheel, verifies readiness and launches the existing GUI. No application changes or RC7 asset replacement.

**Tech stack:** Windows BAT, Windows PowerShell, official CPython3.13, standard-library venv, Pillow13.0.0.

**Spec:** User requests a permanent BAT that can install Python if needed and says it just needs to work. Further design questions were explicitly declined. Existing RC7 source is complete in the Windows package; the portable-core package lacks the GUI.

## Global constraints

- Windows x64 only; no administrator request, PATH/file-association changes or security-policy changes.
- No execution-policy bypass, encoded/evaluated downloaded scripts, unblock commands, antivirus exclusions or renamed blocked executable.
- Verify Python Software Foundation Authenticode before executing a discovered interpreter; never search arbitrary PATH.
- Download only official pinned installer; require matching SHA256 and valid PSF Authenticode before execution, following explicit consent.
- Pin Pillow13.0.0 and its official cp313-win_amd64 wheel hash; no source builds or unchecked dependency downloads.
- Keep original app/input files untouched. First setup needs internet; healthy repeats require none.
- Actual Windows first/repeat/recovery/decline tests; Linux unit checks do not prove SAC compatibility.

## Review focus

Paths with spaces/Unicode; interrupted or concurrent setup; offline first setup versus offline repeat; missing Tcl/Tk or untrusted interpreter; failed download/hash/signature/installer/package process. Each is covered by bootstrap unit boundaries and native Windows acceptance. SAC may block the launcher or dependencies; fail plainly rather than weaken policy.

## Tasks

- [ ] Write visible failing bootstrap tests for reuse, incomplete state, failed setup and app-path validation; independent acceptance already frozen03:07:15UTC.
- [ ] Implement `tools/source_launcher.py`: owned per-user state, lock, readiness probe, venv+hash-pinned Pillow setup, GUI subprocess and actionable errors.
- [ ] Implement `Start GridCAD.bat`: source presence, fixed PowerShell executable, trusted Python discovery, consent and verified per-user install, bootstrap invocation.
- [ ] Add concise setup/removal/offline instructions and additive launcher ZIP packaging; leave published RC7 unchanged.
- [ ] Add native Windows tests using real launcher and actual GUI; installation only on disposable hosted runner. Cover first/repeat/interrupted/decline, paths and blocked/failed setup without modifying security policy.
- [ ] Run full ordinary tests, independent gates, publish only approved branch changes, monitor exact Windows run to completion, inspect evidence and deliver separately verified launcher artifact.
