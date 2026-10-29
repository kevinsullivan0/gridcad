# GridCAD guide

GridCAD applies the material recipes in an Excel worksheet to a rectangular group of samples in a supported GrabCAD PRINT project. It saves a new result and keeps your original files unchanged.

## Open the app

Download the complete Windows ZIP, choose **Extract All…**, then double-click **Start GridCAD.bat** in its GridCAD folder. Setup copies the included app into your account and offers a Desktop shortcut. Use that shortcut afterward; the installed copy does not depend on keeping your Downloads folder. Both the EXE and alternate source interface are in the same download. The EXE needs no Python installation; if it cannot start, the alternate method asks before installing verified Python and the image library. No administrator rights, account or AI assistant are required.

See [Setup and recovery](SOURCE_LAUNCHER.md) for installed locations, manual updates, source startup and removal. Keep the progress window open while using the app.
This release is unsigned. If Windows or your organization blocks it, follow the applicable security policy. Do not disable protection to run GridCAD. A checksum can confirm that a download is complete, but it does not prove that software is safe.

## Try an example

Choose **Load example**, then **Match cells to samples**. The example contains 24 samples and recipes in `Recipes!D4:I7`. Click a blue sample to inspect it. The example is generated test data. Do not print it.

## Convert your project

1. **Open workbook** (`Ctrl+O`). Choose the worksheet and the cells containing your recipes. Each cell needs six percentages in this order: cyan, magenta, yellow, black, white, clear (**C/M/Y/K/W/T**). For example, `2/0/0/0/98/0` means 2% cyan and 98% white. Include zero values; the total must be exactly 100.
2. Select cells by dragging, by clicking the first cell and Shift-clicking the last, or by typing a range such as `D4:X36`. Use **Go to** and the row/column buttons to reach cells outside the current view. **Check recipes** checks their format and totals without needing a project.
3. **Open .PRINT** (`Ctrl+P`). Choose the sample group and label group. Only the selected samples and labels can change; other objects stay unchanged. You can click samples in the preview before choosing a matching worksheet range.
4. Match the worksheet to the preview. Choose the corner where the **first selected cell** belongs, then the direction in which the **next worksheet row** runs. These directions refer to the preview on screen. Check the corners and some interior samples against the labels in your original project. GridCAD cannot read the meaning of the printed labels for you.
5. **Match cells to samples** (`Ctrl+Enter`). The worksheet must contain one recipe for each sample. Click a sample to see its current material and, when mapped, its requested worksheet recipe. The **Cell assignments** tab lists every cell and target sample. Changing an input clears the old mapping so it cannot be saved by mistake.
6. **Save PRINT** (`Ctrl+S`). Choose a new `.PRINT` filename. GridCAD checks the recipes, source files, material assignments and preserved project data before writing.

A normal save creates only the PRINT file you named. Select **Include conversion report** beside Save if you also want a JSON record of the checks and remaining validation limits. Existing files are never overwritten. If only the optional report cannot be saved, GridCAD keeps the completed PRINT and tells you the report was not saved. Naming a file does not validate it in GrabCAD: the native checks below still apply.

## Understand the preview

Blue outlines are samples. Dark shapes are the selected printed labels. Gray shapes are other objects that will be preserved. **Zoom +**, **Zoom −** and **Fit** help you inspect the view; scroll to reach enlarged areas.

Clicking a sample works even when no mapping exists or the selected cell count does not match. In that case GridCAD shows the source material and marks the sample as unmapped. To see requested percentages, select a complete matching range and build the mapping.

Large projects may show fewer surface details to keep the preview responsive. The notice explains any omitted detail. This affects only the display—not the original geometry or the saved result. Check unclear labels in the original project rather than guessing from a simplified preview.

## Materials

Sample recipes use the supported EcoFlex cyan, magenta, yellow, black, white and clear channels. A source sample may have a color-picker placeholder. GridCAD shows that source assignment separately from the requested recipe.

Printed labels have a separate material choice. The default uses EcoFlex Black through the supported material profile, preserving a matching saved black material when available. GridCAD uses the material definition to display its name.

If the project contains a compatible saved material, you can choose it as the source for label material. This copies the complete assignment from that object; it does not require a separate reference file. If no compatible object exists, this option is unavailable. If labels already have a different intentional material, review and approve those replacements before rebuilding the mapping. Canceling keeps the existing assignments.

## Formula cells

A `ƒ` mark means that a cell contains a formula. GridCAD reads the last result saved by Excel; it does not calculate formulas. Recalculate and save the workbook in Excel before confirming that its saved results are current. A missing result or Excel error cannot be fixed by confirming it. A values-only copy avoids this extra step.

## While GridCAD is working

The activity bar and status text show what GridCAD is doing: reading files, checking recipes, building a mapping, drawing the preview or saving. The bar does not show a percentage or predict when work will finish. You can change the view while it is drawing; the latest view replaces older requests.

Wait for a file operation to finish before starting another. Closing during an operation asks you to wait so that a save is not interrupted. If loading fails, the previous file's preview is cleared. Choose a valid file to try again.

## If you cannot save

- Open both files, select the sample and label groups, and choose the mapping directions.
- Select one recipe cell per sample and build the mapping. Use the message shown if the count or shape does not match.
- Resolve any listed material conflict. Rebuild the mapping after changing an input.
- Wait for validation and preview activity to finish. A failed check must be corrected before saving.
- Choose a new output filename. GridCAD will not replace an existing file.

Saving records the selected mapping and the file checks. It does not record a physical-label review.

## Check the result in GrabCAD

Before printing, open the new result in the Windows GrabCAD application. Check the geometry, size, placement, sample count, corner and interior recipes, and label material. Recompose and save a separate native copy. Confirm the loaded printer materials and process settings.

GridCAD's file checks do not establish GrabCAD compatibility, physical label correspondence or print quality. Every GridCAD result reports `print_ready=false`. Any native or printing validation must be recorded separately. GridCAD does not submit print jobs.

## When a file is not supported

GridCAD supports a specific rectangular-grid project format, not every CAD file or GrabCAD version. The **Supported files** guide lists the exact requirements and resource limits. Unsupported transforms, irregular grids, conflicting materials or oversized inputs are refused rather than silently changed.

Keep the original. For a large file, export a smaller project or a values-only workbook containing just the sheets you need. Do not edit version numbers, units or material identities to force a file through.

## Help and support

The **Help** tab works offline. It includes this guide, supported-file requirements, a developer guide, version information and bundled licenses. **About** shows the installed version and links to GitHub and releases. Those links open your browser only when you choose them; GridCAD does not check for or install updates automatically.

An error message explains what happened and what to try next. **View technical details** shows the diagnostic code and original validation detail. **Copy debugging prompt** creates text you can give to an assistant or developer. **Open report folder** shows the local report.

Reports can contain file paths and selected object names. They do not include workbook or project contents, cell values, passwords or environment settings. Review a report before sharing it. GridCAD does not upload reports or launch an assistant.

The optional assistant settings let you include the app folder path in copied support text and look for known installed assistants. Detection checks filenames and registration information only; it does not run those programs, connect accounts or prove that they are configured. You can use GridCAD without any assistant.
