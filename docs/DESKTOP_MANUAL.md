# GridCAD basics

1. Extract the complete Windows ZIP and double-click **Start GridCAD.bat**. Use the Desktop shortcut after setup. The BAT inside **Troubleshooting** is the alternate source method, not the normal starting point.
2. Open your `.xlsx` workbook. Each sample uses **one cell** containing **C / M / Y / K / W / T** percentages: cyan, magenta, yellow, black, white, clear. For example, `20/0/0/0/30/50` totals 100. Select the recipe rectangle by dragging, Shift-clicking or editing its range. A suggested range is a starting point, not a fixed required location.
3. Open the original `.PRINT`. Choose the sample group and the group containing its existing printed labels. Compare **selected cells** with **expected samples**. Labels can contain several bodies per printed number; their count need not equal sample count.
4. Choose where the first selected cell appears in the preview and which way the next worksheet row moves. Click **Match cells to samples**. Red field messages explain missing choices or a mismatch; correct them and retry without restarting. Click a sample to inspect its source material and requested recipe. Preview inspection also works before matching.
5. Choose **Save PRINT** and an unused filename. The dialog starts in the last successful folder this session, otherwise the writable source folder; examples, installation and temporary folders use Documents instead. You can change it. Originals and existing outputs are never overwritten.
6. Open and check the result in GrabCAD before printing. GridCAD does not print or certify native acceptance.

## Formula cells

GridCAD reads the last results saved by Excel; it never calculates formulas or proves those results are current. If inputs changed, recalculate and save in Excel first. A missing saved result or worksheet error must be corrected in Excel or replaced by a values-only copy. No checkbox can repair missing results.

## Materials and existing labels

Worksheet recipes use the supported six EcoFlex channels. Printed labels have a separate material choice, shown by its real name and preview swatch. Compatible complete assignments already saved in the project can be copied; conflicting existing assignments require deliberate replacement review. Preview colors are not physical color measurements.

The presence of a resin name in a tray is not enough to construct its complete material assignment. Additional direct materials are tracked in [issue #3](https://github.com/kevinsullivan0/gridcad/issues/3), not silently guessed. GridCAD preserves existing label meshes for supported projects with different rectangular dimensions; it does not read label text or generate new labels.

## Diagnostics and help

The app has one short **Help** tab. **Diagnostics** contains an optional conversion-report setting and explains what the report records. A normal save creates only the named PRINT. If an optional report fails, the valid PRINT remains and the app explains the report failure. Error dialogs offer technical details and a local report for a developer or your optional agent; nothing is uploaded automatically.

Wait for loading, matching or saving to finish. Large previews may omit detail, as stated on screen; saved geometry is unchanged. If a selected group overlaps the samples or the rectangle has a different shape, correct the indicated choice. Do not guess unclear labels from a simplified preview.
