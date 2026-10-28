## GridCAD 0.2.0-rc.5 — Windows desktop candidate

Download **GridCAD-Windows-x64-v0.2.0-rc.5.zip**, extract the complete folder and open `GridCAD.exe`. Keep `_internal` and `GridCAD-core.exe` beside it. No installer, Python, account, LLM or first-run downloads are needed. This unsigned candidate follows your normal application-trust policy; it does not change security settings.

### Changes since RC4

- Large repeated-mesh projects use lazy shared preview geometry rather than rejecting otherwise supported inputs solely because instanced triangle counts exceed the former preview ceiling. Rendering has bounded sampling and honest detail notices; exact conversion retains the original source geometry, transforms and complete preserved payloads.
- Worksheet click, drag and Shift-click select actual cells and rectangular ranges across columns, with visible highlighting and cross-page range extension.
- Honest activity indicators and stage text accompany background loading, recipe checks, rendering and saving. Expensive raster work no longer runs on the Tk event loop. Superseded results are discarded; errors clear stale views and progress safely.
- Worksheet navigation and formula acknowledgment remain visible. Geometry settings and notices scroll independently of a useful preview canvas; review notes and required acknowledgments remain reachable at the minimum window size.
- Project loading uses a bounded temporary snapshot and verifies source identity, avoiding a stale preview paired with a different source digest. Archive loading accepts only the supported STORED/DEFLATED compression methods before member decompression. Existing byte, structure, mesh, cell and render limits remain in force; there is no unchecked bypass.

### Verification and limits

The attached evidence records the exact final Windows build and real extracted-package GUI acceptance. Coverage includes native file dialogs, individual-cell/rectangular mouse selection, responsive recipe progress and event-loop heartbeat, all four tabs at the minimum window size, mapping/transpose, review-gated saving, reference-material replacement cancel/confirm, error recovery, and packaged CLI operation. Public regressions and independent acceptance checks also passed before publication.

Two original production PRINT fixtures were separately loaded and converted in the cloud without changing non-material data; repeated outputs were byte-identical. Those private files were not uploaded to CI or included in this release. This is not a claim that the private originals were exercised through the packaged Windows GUI.

### Security review status

Official Codex Security was unavailable for this repair. A partial manual review identified source-snapshot and archive-compression issues, which received narrow defensive repairs and ordinary functional regressions. That review was stopped by a platform restriction; no completed independent security audit or clean security certification is claimed.

### Still a release candidate

Unsigned; native GrabCAD open/recompose/save and physical printing remain unverified. Every output retains `print_ready=false`. Synthetic PRINT examples are software demonstrations, not native-generated print jobs, and must not be printed. Geometry companions and output candidates require validation in the intended native printer workflow. Supported input versions, material profiles and resource limits are documented in the bundled schema guide.

The Windows ZIP, portable core, GUI evidence and SHA256SUMS belong to this exact release. Checksums establish download integrity, not publisher authentication or print compatibility. Private inputs and proprietary vendor software are not bundled. Prior releases remain available.
