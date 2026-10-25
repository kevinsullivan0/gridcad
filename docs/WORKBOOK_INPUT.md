# Workbook input, without switching back to Excel for cell addresses

## View and select

1. Start the app through its launcher, not by opening index.html. Check the visible build and Connected status.
2. Choose an .xlsx. Its saved active tab opens immediately at its first populated cell. The tab picker contains all actual worksheets. Showing a tab does not select any recipe range.
3. With “Recipe grid” selected, drag across the recipe cells. Keep blank positions inside the rectangle. The displayed selection shows the exact tab, addresses and dimensions.
4. For a range spanning pages, click the first cell, choose “Choose last cell next”, navigate, and click the last cell. Shift-click also works. Previous/next row and column buttons and First used cells avoid external address lookup. Optional exact addresses allow a precise typed adjustment or jump.
5. If useful, mark sidebar/reference or heading rectangles separately. These marks do not supply recipe data, alter formulas, or represent printed project labels. Multiple marks are allowed; remove unwanted marks individually. Overlaps with recipes or other marks are rejected rather than silently dropping cells.
6. Choose Inspect a cell to see original content, formula, saved result and checked percentages without changing the selection.

The grid is a bounded data view, not Excel formatting or a calculation engine. It renders 40 rows × 30 columns per page. Up to 100,000 selected cells are checked, including every blank position, not only the visible page. Larger selections and merged cells intersecting a recipe grid are rejected.

## Check recipes before loading a project

Choose Check selected recipes. No .PRINT is required. The result reports valid recipes, blank positions, formula cells and errors. Show cell buttons navigate directly to errors. Correct the selection or schema here before project mapping.

Each occupied cell must contain six percentages. Default CMYKWT order means Cyan / Magenta / Yellow / Black / White / Clear. Example: 20 / 0 / 0 / 0 / 30 / 50. Spaces around slashes, consistent semicolons or whitespace, decimal points and percentage signs are supported. Commas require an explicit separator choice. No mixed separators, inferred decimal commas, silent normalization or rounding.

Use explicit 0 for unused channels. An optional policy permits empty positions inside a six-position bundle. A blank cell remains a grid hole, not an all-zero recipe. A scalar such as 20 may be a sidebar input or one formula component; it is never expanded into six channels automatically.

## Formula results

The data view shows original formula text and any saved result. GridCAD never evaluates formulas. After recalculating/saving the workbook, explicitly confirm use of its saved results. Freshness cannot be verified automatically.

Missing caches, Excel errors, non-finite values and scalar results remain invalid recipes. Array/spill and data-table ranges are unsupported, including selected cells whose formula anchor is outside the selection. For those cases, recalculate/save in Excel or paste evaluated recipes as values into a workbook copy. Keep originals unchanged.

If a saved-value cache is unreadable, the viewer still shows raw addressed cells with a warning. Valid literal regions remain checkable; unreadable formula results do not become recipes. File streams close even when cache parsing fails.

## Transpose, map and save

Transpose explicitly swaps sample-grid rows and columns in GridCAD, preserving original Excel addresses and holes. The selected shape updates before mapping. The workbook is never edited. Mirroring and orientation still require an explicit choice.

For saving, the current supported project workflow requires a sample region plus BOTH complete physical printed row-label and column-label regions. These are project bodies, not Excel sidebars. Label text associations are not inferred or rewritten. Selected glyphs receive direct EcoFlex Black, not a K=100 mixer. Other objects are preserved.

Review the cell addresses drawn on the tray, confirm orientation and exact material replacement, then preview changes. A preview can prepare a private disposable candidate to check preservation. Only Save produces a downloadable separate candidate. Changing selection/options or checking the workbook invalidates the previous save review. The original files are never overwritten.

Open a saved candidate in normal GrabCAD Print, inspect recipes/label modes and recompose before considering a print. The app never connects to a printer or submits a job.

## Visible recovery states

- Starting interface never changes: scripts have not initialized. The build label and startup guidance remain visible.
- HTML file opened directly: launch the app and use its local browser link.
- Session missing/expired: reopen the complete current launcher link; keep its private session fragment private.
- Workbook upload failed: choose a readable .xlsx or retry that file. Originals remain unchanged.
- Workbook loaded, preview failed: real tabs remain available. Change tabs or Reload this view.
- Empty worksheet: choose another tab; this is not an upload failure.
- Empty page on a nonempty worksheet: use First used cells or navigate. No selected region is inferred.

## Acceptance limits

Synthetic parser/API/event-to-HTTP/save tests are not real-browser rendering, Windows execution or actual-file acceptance. The user's representative workbook and a normal GrabCAD review remain necessary to establish their particular end-to-end workflow.
