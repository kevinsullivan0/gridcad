# Selecting and checking an Excel recipe grid

## Start with the actual recipe cells

1. Choose your .xlsx workbook. The Excel tab picker lists its real worksheet names.
2. Choose the tab containing the recipe grid. The displayed used area may also contain headings, instructions and sidebar inputs; it is not automatically selected.
3. Drag from the first to last recipe cell. Alternatively enter a rectangle such as B2:F4. Keep blank positions inside the rectangle: removing them would move the remaining recipes to different sample positions.
4. For a long selection, click its first cell, page or jump to another address, then Shift-click its last cell. The address and row/column count above the preview show the complete selected rectangle.
5. Leave sidebar inputs and headings outside the recipe rectangle, but keep them in the workbook. Formulas may depend on them. Excel sidebars are not the printed row/column labels in the .PRINT project.

The selector is a bounded data grid, not an Excel renderer. It shows at most 40 rows × 30 columns at a time and does not reproduce Excel formatting or merged-cell layout. Page controls and “Preview starts at” reach other addresses. The recipe inspection limit is 100,000 cells; selections above the limit are refused, not silently shortened. Merged cells intersecting the recipe rectangle are refused.

## Expected recipe value

Each occupied cell must contain all six channel percentages. Default order:

Cyan / Magenta / Yellow / Black / White / Clear

Example: 20 / 0 / 0 / 0 / 30 / 50

Spaces around slashes are accepted. Consistent semicolons or whitespace also work. Decimal points and percentage signs are accepted. Commas need an explicit separator choice; decimal commas and mixed separators are not inferred. Values must total exactly 100. No normalization or silent rounding is performed.

Use explicit zeros for unused channels. The optional empty-channel setting permits empty positions only within a complete six-position bundle. A blank cell is a hole, never an all-zero recipe.

A scalar such as 20 is not a bundle. It may be a sidebar input, a formula returning just one component, or a different worksheet layout. GridCAD does not guess the other five channels or combine adjacent cells automatically. Check the raw value and the selected rectangle.

## Formula cells

The original release rejects every formula cell, even if Excel saved its calculated result. Its workaround is to copy the workbook and paste the evaluated recipe cells as values.

This review build can read Excel's saved formula results after an explicit confirmation that the workbook was recalculated and saved. It never runs formulas, macros or external links. It shows the original formula, saved result, parsed channels and exact total. A saved result may be stale: GridCAD cannot verify freshness.

If no readable saved result exists, open the workbook in Excel, recalculate, save and select that saved file again. Alternatively paste the evaluated recipes as values in a copy. A missing/unreadable cache, including an indistinguishable empty formula cache, is not silently treated as a grid hole. Saved Excel errors remain errors. A saved numeric scalar still needs a six-channel bundle. Array/spill ranges, data tables and other structured formula types are not supported; a selection touching one of these ranges is refused even if its anchor lies outside the selection. Paste their evaluated recipes as values in a copy. Ordinary per-cell formulas with readable saved results remain supported.

## Transpose and orientation

“Transpose the selected recipe grid” swaps the sample grid's rows and columns in GridCAD, without modifying the workbook. The source addresses and recipes are retained. The recipe preview shows both source dimensions and transposed dimensions, and only geometric orientations matching the explicit transpose choice are offered.

Choose an orientation yourself and compare the original Excel addresses drawn on the tray. Mirroring is separate from transposing. Blank positions move with their original row/column positions.

Physical row-label and column-label regions remain where you selected them. Their glyph text and association with source rows or columns are not inferred, swapped or rewritten. Check those regions explicitly. Selected glyphs receive direct EcoFlex Black, not a K=100 mixer recipe. Unselected bodies are preserved.

## What previews mean

- Worksheet selector: raw data and saved formula results, before recipe validation.
- Recipe inspection: exact parsed channels, total and errors for all selected cells, not just the visible page.
- Tray view: bounding boxes, not rendered meshes or simulated printed colors.
- Exact-change preview: reviewed cell-to-body assignments, selected label changes, complete exact matches skipped and unselected bodies preserved.

Inspection and preview do not change either original. Only the separate-copy save produces a candidate .PRINT. Normal GrabCAD reopen/recompose and print validation are still required.
