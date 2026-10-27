# GridCAD operator

Desktop portability revision: staged files now use a writable handle for Windows `fsync`; frozen packages include the exact material-converter source so its integrity/provenance check remains active. Mapping/material/source guards are retained. The older review documents describe the original source-review snapshot; current Windows package acceptance evidence is published separately.

A small assistant-operated CLI for inspecting an XLSX and a GrabCAD `.PRINT`, checking an explicit mapping plan, and writing a separate **unverified** candidate with preservation evidence. Python 3.10+ standard library only. No installer, browser, LLM API, network access, or end-user dashboard.

This is a cleanup of an actual-file conversion method, not a universal importer. The source/storage profiles are narrowly limited to the observed GrabCAD 1.117.12.3985 / internal 2170 serialization described below. The material-only route consumes externally reviewed exact IDs rather than inferring their physical mapping. Two successful file-level conversions do not establish compatibility with all 2170 projects or native print readiness.

## Operator workflow

The ordinary desktop app needs none of these commands. For optional operator use on **Windows PowerShell**, open the extracted Windows package's `GridCAD` folder (the one containing `GridCAD.exe`, `GridCAD-core.exe` and `_internal`). The bundled core includes Python; no installation, activation script or execution-policy change is needed. Replace these illustrative paths with your own. Keep actual inputs, private plans, renders, reports and outputs **outside the app/source package**.

```powershell
Set-Location -LiteralPath "C:\Users\YourName\Downloads\GridCAD"
& ".\GridCAD-core.exe" operator inspect --project "C:\GridCAD work\input.print" --workbook "C:\GridCAD work\input.xlsx"
& ".\GridCAD-core.exe" operator check-plan --project "C:\GridCAD work\input.print" --workbook "C:\GridCAD work\input.xlsx" --plan "C:\GridCAD work\plan.json"
& ".\GridCAD-core.exe" operator apply --project "C:\GridCAD work\input.print" --workbook "C:\GridCAD work\input.xlsx" --plan "C:\GridCAD work\plan.json" --out-dir "C:\GridCAD work\new-result"
```

The leading `&` runs the quoted executable path. Keep quotes around paths with spaces. To run from the portable source instead, install Python 3.10+, open the source root and replace `& ".\GridCAD-core.exe"` with `python ".\desktop_cli.py"` in PowerShell. For a **POSIX shell** on macOS/Linux, use `python3 ./desktop_cli.py operator ...` from that root and quoted POSIX paths instead. Do not paste Windows drive-letter paths into a POSIX shell. Native GrabCAD acceptance remains separate from portable CLI operation.

1. Record original hashes; work on verified copies. `inspect` reads archive/XML content and lists cell values, formula/cache status, IDs, materials, fingerprints, and occurrence/tray matrices. It executes no formulas, macros or external links. Macro/external-link workbooks are refused.
2. Inspect the actual embedded geometry/printed labels with a trusted native viewer or a safe local geometry renderer. Establish which workbook rows and columns physically exist, orientation, cardinality and pitch. Compare corner recipes and interior labels. **Counts, prior color, repeated shape, or occurrence order alone do not establish a mapping.** This CLI does not render or recognize glyph text and never creates replacement label geometry.
3. Build a plan using `PLAN.md`. Bind the exact original file hashes and source material fingerprints. Include independently expected, label-derived percentages for every cell. Choose the explicit reviewed-ID material-only profile when the complete source-bound ID mapping has been independently audited; its review digest binds those assignments to the exact inputs. It deliberately does not check physical mapping through stored translation ranks. Do not copy workbook values into the expected list and describe that as independent evidence.
4. Declare every leaf as a sample, label, or explicitly preserved unrelated occurrence. Do not infer that colored equals completed. Preserve exact matching mixers only with the explicit preserve action; conflicting mixers and heterogeneous picker materials are refused.
5. Run `check-plan` before `apply`; it also runs the material serializer's numeric-domain validation, so decimal-valid but binary64-lossy percentages are refused during preflight. An entirely new output directory is required. `apply` writes only after plan, input, profile and preservation checks pass. It stages and audits the bundle, then reserves the output directory exclusively and hard-links new files without replacement. Filesystems without hard-link support are unsupported; do not disable no-overwrite checks. A concurrent foreign file is never removed during rollback.
6. Review `audit.json`, `assignments.json`, `preserved_payload_hashes.json`, and `reviewed_plan.json`. The audit identifies which mapping route ran; reviewed-ID output explicitly records that placement was not interpreted and physical mapping was not automatically verified. Independently reopen the saved ZIP and compare every assignment to workbook values and physical labels. Output JSON numbers are written exactly with Decimal; source geometry, IDs, transforms and schema are never rewritten to satisfy assumptions.
7. Complete the native acceptance checks below before treating a candidate as ready.

The output bundle contains `candidate_UNVERIFIED.PRINT`, the reviewed private plan, assignment manifest, payload hashes, audit, and an explicit warning. No input files are changed or copied into the source package. CLI failures return exit code 2. Diagnostics and generated plans can contain private identities and must not be committed publicly.

## Source and transform assumptions

- Exactly one tray; every leaf has exactly one tray body. Every occurrence, including ancestor containers and preserved unrelated occurrences, must declare exactly empty `featureManager.uniqueFeatures` and `currentStateIndices`. Active, unknown or missing feature state is refused. Instanced/duplicate leaves, missing desired/actual agreement, or an incomplete plan are refused.
- Exact source version object: application 1.117.12.3985, five provider schemas at internal 2170 / external 1.117. A plan acknowledgement does **not** admit a different source version.
- Stored occurrence `units=CM`, `occurrenceScaling=.001`, `rootScaling=.1`, percentage scale properties at 100; root occurrence transform `.1` diagonal; descendant occurrence transforms identity linear components with translations; orientation properties at the observed XY quarter turn; tray-body linear transform `.1` times that turn. Affine row-major layout is checked. Unknown units, scaling, rotation/shear, root translation or orientation translation are refused. Nothing is silently normalized.
- The identity-compose lattice profile requires an explicit exactly identity `composeTransform` on every body. The separate reviewed-ID material-only profile admits only the observed exact pure-translation storage form: finite values, raw translation magnitude at most 1, common across all bodies within 1e-12, exact identity compose linear blocks, and the already stated common tray linear block. These are storage-form restrictions, not interpreted units or native composition semantics. Every matrix value is preserved exactly; the tolerance never rewrites a value. Rotation, scale, differential offsets, missing state and other forms are refused.
- Only the identity-compose lattice profile uses **stored tray translation indices 3/7** in metres to check declared X/Y ranks and pitch. The reviewed-ID material-only profile performs no rank/pitch inference and must omit `axes`. Its exhaustive cell/occurrence/body assignments, expected recipes and independent review digest are bound to the exact source/workbook hashes. Neither route composes unknown native transforms or certifies effective native geometry. Raw matrices and nonmaterial geometry remain unchanged.
- Dense rectangular six-channel slash strings in the explicit sheet/range. Values must be in 0..100 and total exactly 100; every zero must be present. No blank-to-zero inference, hole filling, normalization, or formula evaluation. Formula caches require explicit confirmation of a real current calculation source; missing caches always fail. Prefer an existing verified values-only tab.
- Material assignment changes only enumerated material objects and their tray RGBA preview leaves. Optional rendering metadata and all other JSON are preserved. Every non-project archive payload must hash identically, and the saved ZIP/readback must pass.
- All occurrence material references, including ancestor containers, and all tray-body material references are counted. Changing a shared material UUID is refused. UUIDs are retained, not split or deleted. Shared native black labels can be preserved completely.

Two routes are intentionally distinct. `conservative-2170-cm-quarterturn-identity-compose-v2` retains its identity-only lattice restriction. `reviewed-ids-2170-material-only-translation-compose-v1` writes a mapping already established by an independent actual-label/geometry review and bound to the exact source; it does not interpret compose fields or automatically verify physical mapping. The historical exact-file workflow is reproduced through this second route, with complete preservation checks. This is not a general force/geometry-bypass option: source shape, hashes, exhaustive unique IDs, expected recipes, material fingerprints, shared-identity/ancestor-feature guards, and the narrow storage form remain mandatory. A digest proves binding, not that the operator did the review.

## Native black and mixer evidence are separate

Prefer `preserve_native_black` for already-black labels. For gray labels, `assign_from_picker_using_native_black` copies an explicitly referenced existing source material **in full**, retains the target's unique UUID, and preserves its native optional metadata. It does not reconstruct a handpicked subset. A minimal converter fallback is explicitly named `assign_from_picker_using_unverified_black`; it is refused if a native black object is already available in that source. External reference projects are not ingested by this compact CLI: if one is available, review/extend that reference route rather than choosing the fallback for convenience.

The reused own material serializer has observed profile **5.119.0 / Print 2191 / PJ 2190**. Source projects here are older. Native black evidence can establish black resin/mode metadata but cannot establish CMYKWT mixer compatibility. All conversions require `allow_unverified_material_profile=true`; every audit remains `print_ready=false`. This acknowledgement records a limitation, not evidence that it is safe. Native optional core-suitability flags, grid settings, or other missing metadata must not be assumed equivalent to defaults.

## Native acceptance checklist

- Open a separate candidate in ordinary Windows GrabCAD; record application/version and loader warnings. Verify geometry, body count, orientation, source scale, tray/printer/fabric settings and support/adhesion state.
- Inspect all four mapped corners and representative interior/zero-heavy/clear-heavy recipes. Verify actual percentages, resin identities and material mode, not only preview color. Verify the chosen label assignment in full: direct EcoFlex Black in default mode (not a K=100 mixer), or the explicitly reviewed compatible reference material in reference mode.
- Recompose and save a separate native copy. Check for errors and preserve the evidence. Compare saved assignments and unrelated state against the independent manifest; native reserialization can change metadata and must be reviewed, not blanket-ignored.
- Confirm loaded printer materials and appropriate process settings using the native application. File-level equality does not establish process suitability or physical print quality.
- Record the outcome explicitly. A file opening, looking plausible, or passing synthetic tests alone does not close all checks. Never change an already-delivered file under validation without coordination.

## Synthetic demonstration and tests

These developer tests require Python 3.10+; they are not needed to install or use the app. From the **source root**, enter its `operator` subfolder in PowerShell, then use new temporary directories:

```powershell
Set-Location -LiteralPath ".\operator"
$case = Join-Path $env:TEMP ("gridcad-invented-" + [guid]::NewGuid().ToString())
$result = Join-Path $env:TEMP ("gridcad-result-" + [guid]::NewGuid().ToString())
python ".\examples\make_synthetic_case.py" "$case"
python -m gridcad_operator check-plan --project "$case\DO_NOT_PRINT.print" --workbook "$case\DO_NOT_PRINT.xlsx" --plan "$case\synthetic_plan.json"
python -m gridcad_operator apply --project "$case\DO_NOT_PRINT.print" --workbook "$case\DO_NOT_PRINT.xlsx" --plan "$case\synthetic_plan.json" --out-dir "$result"
python -m unittest discover -s tests -v
```

For a **POSIX shell**, enter the source's `operator` directory and use this separate alternative:

```sh
case_dir="$(mktemp -d)/case"
result_dir="$(mktemp -d)/result"
python3 ./examples/make_synthetic_case.py "$case_dir"
python3 -m gridcad_operator check-plan --project "$case_dir/DO_NOT_PRINT.print" --workbook "$case_dir/DO_NOT_PRINT.xlsx" --plan "$case_dir/synthetic_plan.json"
python3 -m gridcad_operator apply --project "$case_dir/DO_NOT_PRINT.print" --workbook "$case_dir/DO_NOT_PRINT.xlsx" --plan "$case_dir/synthetic_plan.json" --out-dir "$result_dir"
python3 -m unittest discover -s tests -v
```

Choose fresh temporary names. The invented fixtures are mathematical contract tests, not native GrabCAD outputs and never print files. They include a shared synthetic black material with extra metadata and an unrelated nonempty identity map to test preservation. No actual workbook, project, glyph render, identity-bearing private plan, or private path is included in this package. See `PROVENANCE.md` and `REVIEW.md`.
