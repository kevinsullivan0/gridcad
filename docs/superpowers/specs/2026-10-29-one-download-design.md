# GridCAD one-download setup

The distribution should provide near-automatic per-user setup, both launch methods in one download, an optional Desktop shortcut, and a real EXE-start check. Review the complete distribution journey, not just the application screens.

## Choice

Use the existing complete Windows ZIP, which already contains the EXE, shared runtime, source GUI and toolkit. Make its single `Start GridCAD.bat` entry install a verified copy into `%LOCALAPPDATA%\GridCAD\Apps\1.0.1` and offer a per-user Desktop shortcut. Preserve the independent source-only launcher under an explicit name. Do not add an MSI, background updater, administrator requirement or Windows-policy bypass.

A versioned folder avoids overwriting older versions or user data. An installed shortcut points to that stable folder, not Downloads or a temporary ZIP extraction. Upgrade is downloading and running the next version; previous folders remain for manual rollback. Uninstall is explicit, documented removal of the shortcut and selected version; no recursive cleanup of unknown user files.

## Startup contract

Try the included EXE and wait for a fresh nonce-bearing GUI-ready record produced only after the visible interface is initialized. A launch denial is not the same as an application crash. If startup fails or exits before readiness, explain the observed failure and offer the source method; do not claim that it is certainly a security block. If the EXE remains alive without readiness, do not automatically open another instance or kill an unknown process. Give actionable instructions instead. Keep a per-user launcher lock through startup/use so repeated clicks cannot create duplicate instances.

The existing source method retains explicit approval for verified Python/Pillow downloads, progress and recovery. A completed healthy setup works offline. No security controls, PATH, file associations or system-wide settings are changed. Internal launch/setup records live under LocalAppData, never beside PRINT exports.

## Release gates

Write failing tests before product code. Verify manifest/copy, repeat launch, cancellation, partial setup preservation, live-but-unready process refusal, EXE startup failure vs crash, source fallback, shortcut after extraction removal, spaces/non-ASCII paths, and ordinary save/reopen behavior on hosted Windows. Re-run complete application/operator/launcher regressions and existing extracted-EXE acceptance. Preserve v1.0.0; publish an immutable patch release only from an exact passing build. Do not claim native GrabCAD or printer validation.
