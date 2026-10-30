# GridCAD: straightforward conversion and recoverable mistakes

**Direction approved; additional direct materials deferred to GitHub issue #3.** Base: current `main`, `c88336df465cc7efe3b89c73da7b1b8a968f1467`.

## Outcome and boundary

An ordinary user can start GridCAD, select files and samples, understand what is missing or mismatched, correct it without restarting, and save the intended separate PRINT file. The existing deterministic conversion, source-preservation checks, portable toolkit and Windows protections remain. This is a focused usability revision, not a new converter, installer or settings system.

## Approach

Improve the existing Tk desktop workflow rather than add a wizard or another application. A wizard adds navigation without solving the counts/material/validation gaps; copy-only changes leave those gaps intact. Keep the worksheet, preview and assignments views, but remove duplicated help and unnecessary normal-path controls.

### Before matching

- The supported spreadsheet layout is **one cell per sample**, containing six slash-separated percentages in **C / M / Y / K / W / T** order (cyan, magenta, yellow, black, white, clear), not six separate spreadsheet columns. Both the supplied workbook and synthetic example use this format. Put one unobtrusive format line with a short example beside the range selector, expanding channel names in the basic help. Suggest a genuinely detected recipe rectangle and keep it visibly editable/click-selectable. If no valid block is found, say so and ask for a selection rather than call the old A1:B2 fallback a detected recipe block. Identify invalid values by sheet and cell address. Do not add a six-column mapping system or pretend D4:I7 is mandatory.
- Show the selected sheet/range and **selected recipe cells / expected sample bodies** continuously, including before a valid mapping. Distinguish rectangle size from missing/invalid recipe values; do not count a blank cell as a valid recipe.
- Validate the whole set of required choices together. Missing sample/label selections and orientation choices receive a visible red indicator **and plain text**. Move keyboard focus and scroll to the first problem. Correcting a field clears its own warning; fixing a mismatch restores the normal path without reloading files. Invalid inputs cannot enable Save.
- Keep preview inspection independent of matching: source samples remain clickable when the worksheet range is incomplete or mismatched.

### Materials and label geometry

Use one label-material chooser with the material's actual display name and an appropriate swatch. Keep source material distinct from requested worksheet recipes and selection highlighting. Prefer complete parsed material definitions and their saved appearance; resolve duplicates by identity/definition, not by body names or RGB alone. Clear/translucent appearances need an explanatory checkerboard/opacity treatment, not a misleading solid gray square.

The supplied blank PRINT stores tray resin identifiers but not complete selectable direct-material definitions or tray swatches. Current evidence supports direct EcoFlexBlack and validated six-channel mixers. A pure-channel mixer is not the same serialized material as a direct resin. Additional complete compatible assignments found in a project can be copied through the existing validation path. **Additional direct material choices are a separable dependency:** enable them only after a native saved assignment/reference establishes the complete definition. EcoContactFlex adhesion and FullCure705 support are not automatically model/label choices merely because the tray lists them. Unsupported/unavailable materials must be explained, not fabricated.

The user clarified that different labels means **different PRINT files with different grid dimensions and existing labels**, not generating new labels. Adapt counts, ranges, group selection and previews to each loaded file. Preserve existing descendant meshes in the chosen label container rather than OCR-read, rename, resize or regenerate them. Do not assume a fixed row/column count, label-body count, group name, printed-number length or one label body per sample. Different existing text/glyph geometry can be shown within supported mesh/transform limits, but its meaning is not interpreted. Rectangular sample placement, supported transforms, separated footprints and existing resource limits remain; preview sampling can omit visual detail but never modifies saved geometry.

### Save, diagnostics, help and startup

- Default the Save dialog to the original PRINT's folder; use the last chosen output folder for the rest of the session. For bundled examples or an unwritable app folder, use the user's Documents folder. Keep a sensible editable `-materials.PRINT` name and no-overwrite behavior.
- Remove conversion-report controls from the normal footer. Put the optional report in Diagnostics, explained as a local record of conversion checks useful for troubleshooting; normal saves create only the chosen PRINT. A report failure must not delete the valid output.
- Remove the global workbook-recalculation attestation checkbox. Detect selected formula cells, explain that GridCAD reads Excel's last saved results and never calculates formulas, refuse missing/error results, and record saved-cache use truthfully. Do not silently label it user-confirmed freshness. Literal-only selections need no warning or extra step.
- Keep one **short Help tab**: start with the main BAT, open files, select/match, save, and check in GrabCAD. Remove the duplicate Help button and long in-app manual navigation. Keep version/licenses/diagnostics and optional agent tools discoverable without turning the basic guide into a manual; fuller repository documentation can remain separate.
- Keep `Start GridCAD.bat` as the single obvious normal entry. Clearly mark the source BAT as recovery-only in the folder/start instructions; do not remove the working fallback or security checks.

## Implementation and evidence gates

1. Freeze the independent behavioral acceptance cases before product edits. Cover 20 selected cells versus 24 sample bodies, missing dropdowns, per-field correction/re-breaking, unmapped preview clicks, formula/literal cases, material identity/swatch distinctions, save cancellation/collision/retry/default folder, and one short Help.
2. Implement against those cases without weakening the existing app/operator guards or tests. Use only synthetic public fixtures; private files and their contents stay out of commits/releases.
3. Run all maintained app/operator regressions plus genuine source-package checks. Include packed-cell format examples/invalid cells and several grid dimensions/ranges with different existing label meshes; never satisfy this by hard-coding the current file. An independent critic reviews the actual ordinary-user flow and plain, self-contained wording.
4. Run the **exact built package on hosted Windows**. Operate real controls, dropdowns, mouse selection, native Save dialogs and recovery paths at the supported minimum window size and a normal larger window. Read back saved recipes, materials and preserved geometry; retain screenshots/logs. Source setup/shortcut/fallback must still work.
5. Publish or merge only after the reviewed result and exact checks are clear and the parent confirms authority. Never claim native GrabCAD opening/recomposition, printer acceptance or physical color accuracy from archive tests or UI screenshots.

## Native material acceptance: separate evidence gate

The current cloud checkout has no verified native GrabCAD installation. Existing hosted Windows CI exercises GridCAD and its output structure, **not GrabCAD**. A screenshot, complete parsed assignment, or successful archive round trip alone cannot establish that GrabCAD will accept a newly written material.

- Current cloud path: complete app/launcher/UI regression and exact output/preservation checks can run now, labeled as such.
- Genuine native cloud path: requires an authorized Windows cloud machine/image with a legitimate compatible GrabCAD installation and access. If such an environment becomes available, open the emitted PRINT in GrabCAD, inspect material identity/appearance, recompose/save/reopen and compare the relevant assignments. Availability, licensing and automation are not currently established; do not promise or install this implicitly. No Squirrel, Mac or CCSS access is part of this plan.
- A small user-supplied native PRINT with the desired materials actually assigned can establish serializer/reference data. It does **not** by itself prove that new output was tested in native GrabCAD. Additional direct-material options stay evidence-gated until their definitions and appropriate native checks are available. Existing supported black/reference behavior remains separately described.

## Decision/input still pending

- Native assigned-material evidence and a verified native cloud test path for additional direct resin choices. These do not block counts, validation, save, diagnostics, Help, launcher clarity or variable existing-file dimensions.
