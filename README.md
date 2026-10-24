# GridCAD | Windows x64 portable candidate-copy tool

**Known launch limitation: Windows Smart App Control can block the downloaded launch-windows.cmd file. This prerelease is not currently verified usable on machines enforcing that policy. Do not disable security protection to run it. A supported alternative distribution is under investigation.**

## Start here

1. Extract the ENTIRE ZIP into a normal writable folder. Do not launch from inside the ZIP.
2. Double-click **launch-windows.cmd**. A console and your default browser should open.
3. Keep the console open while working. If the browser does not open, copy the complete local link printed in the console, including its session fragment. Keep that link private.
4. When finished, press Ctrl+C in the console. Closing/crashing the console may leave temporary files for normal OS cleanup.

No install, administrator rights, PATH changes, pip, network download or Python setup is needed. The included official Python runtime is for Windows x64, not 32-bit or native ARM64. The tool uses a local browser page, no external assets or telemetry. This is an unsigned custom tool; source is included for inspection and official runtime hashes/provenance are included. Do not bypass Windows or organizational security warnings. If blocked, ask your IT/support contact rather than weakening security settings.

**Successful Windows execution remains unverified.** Linux checks of the bundled Python dependencies and application do not prove that the Windows launcher or browser workflow works on your computer.

## Make a candidate copy

1. Choose your `.xlsx` grid and saved `.PRINT` project. Keep the original project.
2. Select the worksheet, cell rectangle and six-channel recipe schema. The order is C/M/Y/K/W/T; T is clear. Blank cells are holes. Each occupied cell needs six percentages summing exactly to 100.
3. Inspect. On the XY tray view, drag separate enclosing regions for samples, row-label glyphs and column-label glyphs; all chosen bodies must be wholly enclosed. Update mapping proposals.
4. Explicitly choose and review orientation. Check cell-to-body recipes, sample positions, labels, preserved objects and warnings. Labels receive direct EcoFlex Black, not a K=100 mixer.
5. Confirm the role/orientation selection and replacement of selected materials, then preview exact changes. Complete exact material matches are skipped; existing colors are not proof that manual work is complete.
6. Save and download the new **unverified candidate**. If asked where to save, choose a new path, never your original. Use Download again if the browser missed the first download.
7. Open that copy in normal GrabCAD Print. Inspect representative sample recipes and label material mode, then recompose before considering a print.

The tool never connects to a printer or submits jobs. It does not certify print readiness. Previewing performs checks with a disposable private candidate; saving repeats checks before publishing a new candidate. Changes to inputs invalidate review. Recipe/project data in exported review reports should be kept private.

## Exact support boundary

- Stored Print internal schema 2191 / PolyJet 2190; descriptive patch strings are preserved. Unknown active schemas fail closed.
- Recognized PolyJet / Stratasys J850 TechStyle, PrintOnFabric, job type 0, HighMix mode 3, required six EcoFlex channels. Optional EcoContactFlex, separate FullCure705 support, and valid existing adhesion settings are preserved. No live printer configuration or material feasibility is fabricated.
- Flat independent plain STL parts with supported transforms/material structures. Active core/coating/hollow/anatomy/grid/FlexTouch and unsupported assemblies or inheritance are rejected. Passive nesting may be inspectable without being writable.
- XLSX only; slash, semicolon and whitespace can be proposed; commas require explicit selection. Decimal-comma values, formulas, merged grid cells and XLS are unsupported. Empty channel positions require an explicit zero policy; five-value bundles are rejected.
- No silent normalization or rounding. Exact native numeric round-trip determines admission. Four-decimal recipes are extensively tested, but there is no blanket decimal-place rule. Rejected precision is identified by workbook cell/channel.
- Geometry payloads, transforms, non-material JSON and non-project archive files are checked for preservation. Original files and existing writer output paths are not overwritten. Orientation must still be reviewed by you; geometric mapping is not proof of intended physical orientation.

See `docs/UI.md` for the full workflow, `COMPATIBILITY_GATES.md` for boundaries, and `ACCEPTANCE-AND-LIMITS.md` for tests and remaining gaps. `bootstrap/artifacts.json` records official runtime/dependency URLs and hashes; license notices remain with the runtime. No proprietary GrabCAD application code, database, installers, Wine runtime or per-recipe material catalog is distributed.

## If something fails

- Missing runtime: extract the whole ZIP, not just the launcher.
- Unsupported source: read the displayed reason. Do not edit version or resin IDs to bypass it.
- Invalid recipe: correct the workbook, reselect it and inspect again. The program will not guess or silently round.
- Failed/stale save: preview again before retrying. No print job was sent.
- Browser download: use Download again while the session is open. Starting a new session does not recover prior private session data.

GrabCAD GUI reopening/recomposition, the user's real project/version and complex features, service-derived feasibility and printing remain unverified. This is a small offline candidate-preparation tool, not a replacement for GrabCAD Print validation.
