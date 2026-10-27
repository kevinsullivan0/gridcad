# GridCAD desktop quick start

Extract the entire Windows ZIP into a fresh folder. Open `GridCAD.exe`. Keep `_internal` and the `advanced` folder beside it. No Python installation, administrator rights, browser, LLM, account, or first-run download is needed. This candidate is unsigned; organizational trust policies may restrict it. The app does not change security settings or send files anywhere.

## Try the included example

Click **Load example**, then **Build mapping preview**. This newly invented 4 × 6 archive has simple extruded index labels, 12 mm pitch and 8 mm samples. Its worksheet is `Recipes!D4:I7`. It is a software demonstration, not a native GrabCAD-generated print project. **Do not print it.**

## Convert a supported project

1. **Open workbook** (`Ctrl+O`). Choose the exact tab and recipe rectangle. Each cell must contain six slash-separated percentages in **C/M/Y/K/W/T** order, for example `2/0/0/0/98/0`. Include every zero; the total must be exactly 100. Scalar values, holes and Excel errors are refused. The range initially suggested by the app is editable and must be checked.
2. Use **Go to** or the row/column page buttons for long sheets. Click a first cell and a last cell, even across pages, or type an exact range such as `D4:X36`. **Check recipes** works without a project. A `ƒ` mark indicates a saved formula result. Recalculate and save in Excel before explicitly confirming such results; missing caches always fail. GridCAD does not run Excel formulas, macros or external links.
3. **Open .PRINT** (`Ctrl+P`). Choose the repeated sample group and the complete printed-label container. These choices determine which bodies can change. Every other leaf is explicitly preserved. A gray or colored object is never treated as unfinished merely because of its color.
4. Choose how worksheet rows and columns run across the XY geometry. The display has +X to the right and +Y upward. Use **Transpose mapping** when worksheet rows correspond to physical columns. For the recovered 33 × 21 workflow, the tested orientation is **Rows down; columns right**, with **Transpose mapping enabled**. This is not automatically selected for arbitrary files.
5. **Build mapping preview** (`Ctrl+Enter`). Inspect the actual embedded black glyph surfaces and blue sample outlines. Zoom and scroll to read labels. Click samples for exact six-channel percentages; the **Exact assignments** tab lists every mapped cell and body. Check all four corners, representative interior labels, zero-heavy and clear-heavy recipes. The app does not recognize glyph text or infer orientation from symmetric grids.
6. Record the label/corner checks in **Review notes**, confirm the mapping, and acknowledge the unverified native material profile. Any input change discards the mapping and confirmations. These confirmations are required because physical label meaning cannot be established by a hash or a plausible grid alone.
7. **Save separate result** (`Ctrl+S`). The native dialog names a **new result folder**, rather than overwriting a project file. Inside it are `candidate_UNVERIFIED.PRINT`, `audit.json`, `assignments.json`, `reviewed_plan.json`, payload hashes and a warning. Existing output folders are refused. Keep original inputs and previous outputs.

## Inspect in GrabCAD before printing

Open the separate candidate in the ordinary Windows GrabCAD application. Check source scale, geometry/body count, tray settings and orientation, exact recipes at corners/interior samples, and direct-black labels. Recompose and save another native copy; compare it to the assignment manifest. File-level preservation and archive readback do not establish native material compatibility, loaded printer materials, process suitability or physical print quality. GridCAD never submits a print job.

## If an input is refused

Read the specific message. Choose a matching recipe rectangle, sample group, label container, transpose and orientation. Recalculate formula workbooks in Excel and save a values-only copy if needed. Existing conflicting materials, unknown versions, unsupported transforms, duplicate/instanced bodies, nonuniform sample meshes, missing embedded STLs or irregular grids need separate investigation. Do not change version/unit fields or disable guards to force a file through. A failed save leaves originals untouched and attempts to remove only its own staged files.

The **Advanced / Agent & help** tab contains the schema, API and a copyable external-agent prompt. `advanced/GridCAD-core.exe` exposes the deterministic core on a Windows machine without installing Python. The portable source bundle runs on Python 3.10+ with the standard library. Other geometries require an explicit new adapter and evidence; triangular, hexagonal and 3D conversion are not implemented.
