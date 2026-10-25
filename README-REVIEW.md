# GridCAD alpha.3 input-flow review candidate

Unpublished development checkpoint. The alpha.2 portable package and public release are unchanged.

## What is functional

Choose an .xlsx and immediately see its saved active worksheet and real cell addresses. No .PRINT is needed to browse or check recipes. No recipe range is inferred. Select the recipe rectangle here by dragging, or click its first cell, choose “Choose last cell next”, page and click the last. Manual address entry is optional.

Optional sidebar/reference and heading marks are visible and removable. They never silently subtract cells from the recipe rectangle: overlapping roles are rejected. Inspect-only mode reads cell details without changing a selection. Explicit transpose changes mapping dimensions, not the workbook or physical label identities.

The interface displays build/session state before file loading. It distinguishes direct HTML opening, missing/expired sessions, upload failure, preview failure, empty worksheets and empty pages. Tab switching resets unrelated page/selection state. Preview failures retain the actual tab choices and can be retried. Unreadable formula caches fall back to raw addressed data, not fabricated results.

Saved formula use still requires explicit freshness confirmation. Missing, non-finite, erroneous, scalar and unsupported structured results remain invalid. The app does not run spreadsheet formulas. Existing exact arithmetic/material/archive/new-copy safeguards remain unchanged.

## Current verification

- 96 Python checks pass, including new state/API/cache/resource-lifecycle cases.
- 23 Node minimal-DOM contract checks pass.
- 49 production-JavaScript event-to-real-HTTP checks pass across 123 requests, ending with an actual synthetic candidate save/download.
- Independent audit of that download verifies original source bytes, all non-project archive payloads and nonmaterial JSON are preserved.
- Independent source review reruns the checks. Geometry, candidate writer, material converter and fixture writer are unchanged from alpha.2.

These are current synthetic checks, not the unrecovered original 134-test suite. Node uses a minimal DOM test double, not a browser renderer. Real pointer hit-testing, visual layout, Windows embedded-runtime execution, actual-user-workbook behavior, Excel recalculation, GrabCAD GUI/recomposition and printing remain unverified.

## Run

Install/use the unchanged pinned requirements in an appropriate Python environment:

    python -m unittest discover -s tests -v
    node --check ui/app.js
    node tests/test_ui_contract.js
    python tests/run_input_flow_http.py

The completed Linux runs used the existing package's pure-Python dependencies. No Windows executable was run. The event-to-HTTP runner generates temporary synthetic workbooks and a temporary synthetic project output; it does not use personal files.

See docs/WORKBOOK_INPUT.md for the workflow and docs/INPUT_FLOW_CHECKPOINT.md for the changes and remaining acceptance steps. Do not overwrite alpha.2 or publish this checkpoint without review.
