## GridCAD 0.2.0-rc.2 — Windows desktop candidate

Download **GridCAD-Windows-x64-v0.2.0-rc.2.zip**, extract the complete folder and open `GridCAD.exe`. Keep `_internal` and `advanced` beside it. No Python installation, LLM, account, administrator rights or first-run downloads are required. This unsigned build follows your normal application-trust policy; it does not change security settings.

### New in this candidate

- Shape-agnostic samples on unambiguous rectangular layouts: generated pyramid and mixed-shape/size/height cases are tested. Meshes remain untouched; the UI displays sample footprints, not shaded 3D models. Overlaps, missing/duplicate positions, unsupported transforms and ambiguous correspondence are refused.
- Copy a compatible saved material from an unchanged reference body to selected labels. Existing different assignments require explicit review of the full replacement list, confirmation and a rebuilt preview. Full material metadata and target identities are preserved. Scope is existing PolyJet EcoFlex direct materials or validated CMYKWT mixers, not arbitrary printer families or new material synthesis.
- Plain-language errors with practical manual fixes and optional technical details. A local report and copyable debugging prompt can help an external agent; nothing is automatically uploaded or launched. Ordinary conversion needs no agent. Reports contain selected paths/names and traceback frames, not input file contents or Python locals.
- About/version and bundled third-party-license views. Original GridCAD code is now MIT licensed, copyright 2026 Kevin Sullivan. Third-party runtime licenses remain separate, including explicit OpenSSL notices.

Includes the portable Python core, offline Windows CLI, Excel templates, synthetic examples and ordinary STL geometry companions. Prior rc.1 remains available.

**Still a candidate, not native-print certification:** unsigned; native GrabCAD open/recompose/save and physical printing remain unverified. Synthetic `.PRINT` examples are software demonstrations, not native-generated print jobs, and must not be printed. STL companions are geometry starting points whose native import/profile compatibility needs checking. Every output retains `print_ready=false`; inspect in native GrabCAD before printing.

See the attached Windows GUI acceptance evidence and SHA256SUMS. Private customer files and proprietary vendor software are not bundled.
