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
