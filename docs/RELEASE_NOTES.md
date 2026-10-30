# GridCAD 1.0.2

The app shows selected worksheet cells against expected samples before matching, identifies missing choices at their fields and keeps corrections recoverable. Recipe guidance states one cell per sample in C/M/Y/K/W/T order; malformed values name the worksheet and cell. Formula results are read from the saved workbook without a blanket recalculation checkbox or a false freshness claim.

Current label materials use their actual names and saved preview colors. Additional direct-material support is deferred to issue #3; a tray resin name is not treated as a complete assignment. Existing label meshes and supported varying grid dimensions are preserved.

Save opens in the last successful session destination, otherwise a writable normal source folder, with Documents as the fallback for examples/install/temp locations. The conversion report option lives in Diagnostics. Help contains only the short basics; the normal combined download has one first-level BAT, with the source fallback under Troubleshooting.

Existing no-overwrite, source-preservation, material/profile, setup-consent and Windows-security protections remain. This release is not native GrabCAD/printer acceptance certification.

## Earlier releases

# GridCAD 1.0.1

One complete Windows download now contains the EXE, source fallback and toolkit. `Start GridCAD.bat` copies verified included files into a versioned folder in your account and offers a Desktop shortcut that survives deletion of the download. Earlier versions and your project files are not overwritten.

The launcher waits for an actual visible GUI readiness record, distinguishes an exited app from a live but unconfirmed process, and avoids starting a duplicate. A source fallback retains explicit consent for verified Python/Pillow setup and remembers a successful source method for later offline use. Installation, cancellation, repeat launch, shortcut relocation, source recovery and preservation are exercised against the exact hosted Windows artifact; that evidence is not Smart App Control or native GrabCAD certification.

## Earlier release notes

# GridCAD 1.0.0

Named single-file PRINT exports, optional conversion reports, and a complete Windows source-launcher package. The advanced evidence-bundle interface remains available. Original files, identities, geometry and material validation retain the same protections. Native GrabCAD/printer acceptance remains a separate check; a stable app version does not certify a print job.

The source launcher shows setup progress and asks before installing its image library, then reuses a healthy installation without downloading or prompting again. Export diagnostics distinguish a filename collision from a mapping problem. An optional-report failure preserves the completed PRINT, and final output checks bind it to the validated conversion digest. Windows test discovery now fails directly rather than masking an earlier failed test command.

## Earlier release notes

### GridCAD 0.2.0-rc.7 usability candidate

The desktop preview lets you inspect samples before matching worksheet cells, including after an incomplete selection. Two controls choose the first cell corner and the direction of the next row. A valid mapping can be saved without review checkboxes or notes; the output records that physical label review has not been confirmed.

Material choices distinguish original source assignments, EcoFlex worksheet recipes and printed-label material. Copying a saved material is offered only when the project contains a compatible assignment. Help and normal app messages use task-based instructions.

This build remains a release candidate. Native GrabCAD validation and printing checks are separate; GridCAD outputs are not marked print-ready.

## GridCAD 0.2.0-rc.6 — Windows desktop candidate

This small follow-up adds manual project and release navigation. Download **GridCAD-Windows-x64-v0.2.0-rc.6.zip**, extract the entire folder, and open `GridCAD.exe`. Keep `_internal` and `GridCAD-core.exe` beside it. No installer, Python, account or first-run download is needed.

### Changes since RC5

- About shows the installed version, exact release source, and clickable GitHub project/releases URLs.
- Ordinary focusable **GitHub** and **Releases** buttons also appear in Help, including Tab/Enter keyboard access.
- Links open the default browser only when explicitly activated. There is no automatic update check, installer download, background network connection or self-updater. If a browser cannot open, a copyable URL is shown instead.

### Verification

Public regressions cover fixed URL targets, absence of browser calls while viewing Help/About, and missing-browser/error fallback. Packaged Windows acceptance uses real mouse clicks and Tab/Enter activation with a controlled local browser handler, recording exact requested URLs without opening external sites. The full existing Windows workflow also exercises worksheet selection, progress/event-loop responsiveness, minimum-window layout, mapping, guarded saving, error recovery and CLI operation. See the attached evidence for the exact tested build.

RC5's bounded shared/sampled preview, source snapshots, supported archive methods, worksheet selection and responsive background operations are retained. Exact conversion and its resource/preservation guards are unchanged. Earlier private production-fixture conversion checks remain relevant to that unchanged core; private inputs are not bundled or uploaded to public CI.

### Candidate and review limits

Unsigned prerelease. Native GrabCAD open/recompose/save and physical printing remain unverified; every output retains `print_ready=false`. Synthetic examples are software demonstrations and must not be printed. Follow your normal application-trust policy; do not bypass malware or administrator-policy blocks.

Security coverage remains partial: official Codex Security was unavailable for the preceding repair, and the manual review was stopped by a platform restriction. Narrow defensive fixes and ordinary regressions do not establish a completed independent security audit or clean certification. This follow-up does not restart or claim additional security review.

The Windows ZIP, portable core, GUI evidence and SHA256SUMS identify this exact release. Checksums establish integrity, not publisher authentication or print compatibility. RC5 and earlier releases remain unchanged. No private inputs or proprietary vendor software are included.
