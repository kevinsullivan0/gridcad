# GridCAD v0.1.0-alpha.2 | Windows x64 portable prerelease

**Known launch limitation: Windows Smart App Control can block the downloaded launch-windows.cmd file. This prerelease is not currently verified usable on machines enforcing that policy. Do not disable security protection to run it. A supported alternative distribution is under investigation.**

## Start here

Extract the entire ZIP into a new writable folder. Do not replace alpha.1 or run from inside the ZIP. Double-click launch-windows.cmd and keep its console open. If the browser does not open, copy the full local link printed in the console, including its private session fragment. Press Ctrl+C when finished.

The Windows x64 embedded runtime, dependencies and launcher are byte-for-byte unchanged from alpha.1. No install, administrator access, PATH changes, pip or network download is required by design. This is not a signed application. Windows downloaded-file protection or Smart App Control may block an unsigned downloaded CMD launcher. No automatic unblock, trust changes or security-policy changes are included. Do not disable Windows or organizational protection to run it; stop and consult your IT/support contact if blocked.

Alpha.2 has not been executed on Windows. The user's reported alpha.1 launcher success does not validate this prerelease's full workflow.

## Workbook workflow

1. Choose the .xlsx and saved .PRINT files. Keep originals unchanged.
2. Choose the actual Excel tab. Select only the recipe rectangle, not headings or sidebar inputs. Keep blank positions inside the rectangle.
3. Drag in the addressed data preview, type the range, or select the first cell and Shift-click the last after paging. Long sheets are paginated, not silently truncated. The inspection limit is 100,000 selected cells.
4. Each occupied cell needs six percentages summing exactly to 100. Default CMYKWT means cyan, magenta, yellow, black, white, clear. Example: 20 / 0 / 0 / 0 / 30 / 50. Spaces around slashes work. Adjust channel order or separator explicitly when needed.
5. For ordinary per-cell formulas, first recalculate and save in Excel, reselect the file and confirm use of saved results. GridCAD never calculates formulas and cannot prove cache freshness. Missing/error caches remain errors. Array/spill and data-table ranges need evaluated values pasted into a workbook copy. Numeric scalars are not silently expanded into six channels.
6. Optionally transpose the selected sample grid in GridCAD. This does not change Excel; source addresses and holes remain attached. Review the resulting dimensions and orientation explicitly.
7. Inspect. Select physical sample, row-label and column-label regions on the .PRINT tray separately. Excel sidebars are not these printed glyphs. Check cell addresses on the tray. Label text associations are not inferred or rewritten.
8. Confirm exact material replacement and preview changes. Selected labels receive direct EcoFlex Black, not K=100. Complete exact matches are skipped, unselected objects are preserved and no silent rounding occurs.
9. Save a separate unverified candidate. Open it in normal GrabCAD Print, inspect recipes/material modes and recompose before considering any print. This tool never connects to a printer or submits a job.

See docs/WORKBOOK_INPUT.md for selection, formulas, scalar errors, long sheets and transpose; docs/UI.md for the complete review/save workflow.

## Validation and limits

72 new Python tests and 23 Node minimal-DOM contract checks pass on Linux. Independent review reran them. The original 134-test suite could not be recovered; these are new checks, not a claim of 134 passes. Real-browser visual QA was blocked before checks. No representative user workbook has been supplied. Windows execution, Excel recalculation, GrabCAD GUI/recomposition and physical output remain unverified.

The .PRINT profile, material, geometry and writing rules are unchanged. See COMPATIBILITY_GATES.md and docs/ECOFLEX_MATERIAL_CONTRACT.md. Unknown profiles/features still fail closed. Geometry/nonmaterial archive preservation and new-copy output safeguards remain in place.

Official runtime/dependency provenance and licenses remain in bootstrap/artifacts.json and runtime. SHA-256 manifests provide integrity checks, not code signing or trust certification. Synthetic demos and test fixtures are explicitly DO_NOT_PRINT. No personal workbook data, proprietary GrabCAD runtime or external browser assets are included.
