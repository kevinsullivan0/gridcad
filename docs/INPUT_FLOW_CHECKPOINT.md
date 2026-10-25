# Alpha.3 input-flow checkpoint

This checkpoint fixes functional alpha.2 failure paths rather than substituting a static demonstration:

- Multi-sheet uploads now immediately display the saved active worksheet, with actual tabs and addressed data.
- Tab changes reset unrelated late-page positions and recipe/reference selections.
- Upload success is separated from preview failure, preserving the tab picker and allowing retry.
- Session/build status is checked before file loading. Direct HTML, missing/expired session and uninitialized scripts have distinct messages.
- Bad saved-value caches cannot terminate the preview response or emit non-JSON Infinity/NaN. Raw-cell fallback is explicit, and invalid formula results cannot become recipes.
- Workbook-only checking is independent of project files and malformed/unfinished physical region coordinates.
- Reference/headings can be visually marked and removed without silently modifying the recipe rectangle. Inspect-only mode preserves selections.
- Long selections can use first/last clicks across pages without manually reading coordinates in Excel. Transpose remains explicit.
- Old save reviews are revoked after range, transpose, reference-region or workbook-check changes.
- Workbook input streams close deterministically even on cache failures.

## Setup burden

For a workbook whose saved active tab contains the grid, no tab-selection click or coordinate transcription is needed: choose the file, drag the recipe rectangle, adjust/confirm only the applicable schema/formula options, then check recipes. Reference marking is optional, not another mandatory setup stage. Long ranges add navigation and an explicit endpoint choice. Mapping still requires the supported physical regions and explicit orientation/material review.

This describes interaction steps, not a measured time saving. No claim is made that the user's hours-long manual workflow has been replaced successfully until their representative workbook/project completes acceptance.

## Evidence and remaining checks

Current logs: test-results.txt (96 Python tests), qa/dom-contract-results.json (23 Node contracts), qa/input-flow-http-results.json (49 production-JavaScript/real-HTTP assertions, 123 requests and downloaded-candidate preservation audit).

The event runner uses production app.js and real Python endpoints with synthetic files. Its DOM is a test double, so layout, real drag hit-testing, browser behavior and Windows are not established. The normal GrabCAD GUI, recomposition and print output are also unverified. No new browser security workaround or local-computer test was used for this checkpoint.

The alpha.2 release is preserved. No public release, push or email is part of this checkpoint.
