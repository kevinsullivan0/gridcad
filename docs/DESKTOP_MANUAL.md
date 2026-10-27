# GridCAD desktop quick start

Extract the entire Windows ZIP into a fresh folder. Open `GridCAD.exe`. Keep `_internal` and the `advanced` folder beside it. No Python installation, administrator rights, browser, LLM, account, or first-run download is needed. This candidate is unsigned; organizational trust policies may restrict it. The app does not change security settings or send files anywhere.

## Try the included example

Click **Load example**, then **Build mapping preview**. This newly invented 4 × 6 archive has simple extruded index labels, 12 mm pitch and 8 mm samples. Its worksheet is `Recipes!D4:I7`. It is a software demonstration, not a native GrabCAD-generated print project. **Do not print it.** For a vendor-neutral geometry starting point, the adjacent `import-geometry` folder contains individually named STL sample/label bodies, a shared-coordinate manifest and an import guide. Keep their relative millimetre positions; native import and the resulting project profile still need checking.

## Convert a supported project

1. **Open workbook** (`Ctrl+O`). Choose the exact tab and recipe rectangle. Each cell must contain six slash-separated percentages in **C/M/Y/K/W/T** order, for example `2/0/0/0/98/0`. Include every zero; the total must be exactly 100. Scalar values, holes and Excel errors are refused. The range initially suggested by the app is editable and must be checked.
2. Use **Go to** or the row/column page buttons for long sheets. Click a first cell and a last cell, even across pages, or type an exact range such as `D4:X36`. **Check recipes** works without a project. A `ƒ` mark indicates a saved formula result. Recalculate and save in Excel before explicitly confirming such results; missing caches always fail. GridCAD does not run Excel formulas, macros or external links.
3. **Open .PRINT** (`Ctrl+P`). Choose the repeated sample group and the complete printed-label container. These choices determine which bodies can change. Every other leaf is explicitly preserved. A gray or colored object is never treated as unfinished merely because of its color.
4. Choose how worksheet rows and columns run across the XY geometry. The display has +X to the right and +Y upward. Use **Transpose mapping** when worksheet rows correspond to physical columns. For the recovered 33 × 21 workflow, the tested orientation is **Rows down; columns right**, with **Transpose mapping enabled**. This is not automatically selected for arbitrary files.
5. **Build mapping preview** (`Ctrl+Enter`). Inspect the actual embedded black glyph surfaces and blue sample outlines. Zoom and scroll to read labels. Click samples for exact six-channel percentages; the **Exact assignments** tab lists every mapped cell and body. Check all four corners, representative interior labels, zero-heavy and clear-heavy recipes. The app does not recognize glyph text or infer orientation from symmetric grids.
6. Record the label/corner checks in **Review notes**, confirm the mapping, and acknowledge the unverified native material profile. Any input change discards the mapping and confirmations. These confirmations are required because physical label meaning cannot be established by a hash or a plausible grid alone.
7. **Save separate result** (`Ctrl+S`). The native dialog names a **new result folder**, rather than overwriting a project file. Inside it are `candidate_UNVERIFIED.PRINT`, `audit.json`, `assignments.json`, `reviewed_plan.json`, payload hashes and a warning. Existing output folders are refused. Keep original inputs and previous outputs.

## Inspect in GrabCAD before printing

Open the separate candidate in the ordinary Windows GrabCAD application. Check source scale, geometry/body count, tray settings and orientation, exact recipes at corners/interior samples, and the chosen label material. Recompose and save another native copy; compare it to the assignment manifest. File-level preservation and archive readback do not establish native material compatibility, loaded printer materials, process suitability or physical print quality. GridCAD never submits a print job.

## If an input is refused

Read the specific message. Choose a matching recipe rectangle, sample group, label container, transpose and orientation. Recalculate formula workbooks in Excel and save a values-only copy if needed. Existing conflicting materials, unknown versions, unsupported transforms, duplicate/instanced bodies, missing embedded STLs or irregular grids need separate investigation. Do not change version/unit fields or disable guards to force a file through. A failed save leaves originals untouched and attempts to remove only its own staged files.

The **Advanced / Agent & help** tab contains the schema, API and a copyable external-agent prompt. `advanced/GridCAD-core.exe` exposes the deterministic core on a Windows machine without installing Python. The portable source bundle runs on Python 3.10+ with the standard library. Other geometries require an explicit new adapter and evidence; nonrectangular lattice layouts and grids stacked in 3D are not implemented. Sample shapes such as pyramids can be used on supported rectangular layouts.

## Copy a compatible existing material onto labels

In Geometry & review, choose **Copy from reference body**, then an unchanged reference body with the desired saved material. This supports existing PolyJet EcoFlex direct resins and validated CMYKWT mixers—not arbitrary printer families or invented materials. Build the preview. If labels already have different intentional assignments, use the replacement-review checkbox to inspect the full list and confirm; then build the preview again. Cancel or any input change removes that approval. Physical-label review and native-validation acknowledgment are still required before saving. Shared identities and inconsistent assignments are refused rather than silently repaired.

## Understand an error or ask your own agent

Errors lead with a plain-language explanation, location and suggested correction. **View technical details** reveals the diagnostic code and original validation detail. **Copy debugging prompt** points your external agent to a local JSON report and matching source/agent instructions. **Open report folder** reveals that report. The app does not start an agent or upload anything. The report includes selected paths/object names, app version and traceback frames, but no workbook/project contents, cell values, local variables or environment dump. Review it before sharing; a remote agent cannot read the path unless you grant access or attach the report. If report saving or clipboard access fails, the original error remains visible with a manual fallback.

### If you have not used an agent before

You do not need one to open files, convert a grid or follow an error's suggested correction. Agent help is an optional extra. Open the assistant/coding agent you already use, click **Copy external-agent prompt** (or **Copy debugging prompt** on an error), and paste it into that conversation. If it cannot access your computer, attach the named report or grant file access deliberately; do not upload your whole project by default. Review paths and object names before sharing. Ask it to explain its proposed changes before modifying your original files.
