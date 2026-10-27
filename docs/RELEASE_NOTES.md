## GridCAD 0.2.0-rc.4 — Windows desktop candidate

Download **GridCAD-Windows-x64-v0.2.0-rc.4.zip**, extract the complete folder and open `GridCAD.exe`. Keep `_internal` and `advanced` beside it. No Python installation, LLM, account, administrator rights or first-run downloads are required. This unsigned build follows your normal application-trust policy; it does not change security settings.

### New in RC4

- Bounded input loading: shared meshes count toward the preview budget for every body, and workbook bytes, XML structure, cells and text are limited while opening. Oversized files get a clear smaller-input remedy, never silent truncation or a bypass switch. Workbook DTD/entity declarations and duplicate worksheet targets are refused. Exact ceilings are in the supported schema.

- Lower transient memory for large preserved archive payloads through bounded streaming, with independent CRC/hash readback and original-file protection retained.
- Faster shared-reference label validation, recipe preparation and sorted-grid ranking, retaining all per-object safety and precision checks.
- Lower STL allocation overhead and more efficient finite-coordinate bound scanning. No geometry is changed.
- Read-only nonmaterial comparison avoids discarded full-project copies while retaining exact target-path preservation checks.
- Smaller Windows distribution by excluding an unused AVIF image codec; supported inputs, PNG previews, icons, offline help, licenses and optional agent toolkit remain.
- Parallelism was measured rather than enabled by default: processes can help very large multi-mesh workloads but add memory and startup overhead; threads showed no consistent scalable gain. Ordinary conversion remains deterministic and sequential within its existing background worker.
- Measured synthetic Linux comparisons and exact-output equivalence tests are documented in `docs/PERFORMANCE.md`. Improvements depend on input size/layout and are not native GrabCAD performance claims.

### Security review status

The original official Codex Security scan reported two low-severity local input-resource issues (repeated-mesh preview allocation and workbook loading). Resource guards were implemented and regression-tested. Independent Codex Security post-fix verification was unavailable because of a platform restriction; this release does not claim a clean security certification.

### Retained from RC3

- Original geometric GridCAD mark, with editable SVG and crisp multi-size Windows icons embedded in both executables.

- Ordinary top-level Help, scrollable offline guides and a compact optional agent-help/settings panel. Basic conversion is still self-contained.
- User-triggered, metadata-only discovery of known local agent command names; no execution, credential inspection, connection or upload. Detection is not proof of identity or authentication.
- Windows PowerShell-first advanced commands with quoted paths, clearer personal-PC versus managed-device warning guidance, and a short separate agent download/checksum guide.
- Tested help/detection close-and-reopen flows and a packaged PowerShell invocation from paths with spaces.

### Retained from RC2

- Shape-agnostic samples on unambiguous rectangular layouts: generated pyramid and mixed-shape/size/height cases are tested. Meshes remain untouched; the UI displays sample footprints, not shaded 3D models. Overlaps, missing/duplicate positions, unsupported transforms and ambiguous correspondence are refused.
- Copy a compatible saved material from an unchanged reference body to selected labels. Existing different assignments require explicit review of the full replacement list, confirmation and a rebuilt preview. Full material metadata and target identities are preserved. Scope is existing PolyJet EcoFlex direct materials or validated CMYKWT mixers, not arbitrary printer families or new material synthesis.
- Plain-language errors with practical manual fixes and optional technical details. A local report and copyable debugging prompt can help an external agent; nothing is automatically uploaded or launched. Ordinary conversion needs no agent. Reports contain selected paths/names and traceback frames, not input file contents or Python locals.
- About/version and bundled third-party-license views. Original GridCAD code is now MIT licensed, copyright 2026 Kevin Sullivan. Third-party runtime licenses remain separate, including explicit OpenSSL notices.

Includes the portable Python core, offline Windows CLI, Excel templates, synthetic examples and ordinary STL geometry companions. Prior RC1, RC2 and RC3 remain available.

**Still a candidate, not native-print certification:** unsigned; native GrabCAD open/recompose/save and physical printing remain unverified. Synthetic `.PRINT` examples are software demonstrations, not native-generated print jobs, and must not be printed. STL companions are geometry starting points whose native import/profile compatibility needs checking. Every output retains `print_ready=false`; inspect in native GrabCAD before printing.

See the attached Windows GUI acceptance evidence and SHA256SUMS. Private customer files and proprietary vendor software are not bundled.
