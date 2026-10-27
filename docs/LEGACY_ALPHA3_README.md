# Archived GridCAD alpha.3 input-flow review

This is the alpha.3 prerelease. Its frozen package retains the input-flow review build label. Keep alpha.2 and your original files.

Extract the entire ZIP into a new folder and double-click launch-windows.cmd. Keep the console open; use the local browser link it opens. Do not open ui/index.html directly. No install, PATH change, pip or dependency download is required by design. The embedded runtime and launcher are unchanged from alpha.2.

This unsigned downloaded CMD may be blocked by Windows downloaded-file or Smart App Control protection. No automatic unblock, trust change or security-policy change is included. Do not disable protection; consult IT/support if blocked.

The visible page should say alpha.3 input-flow-review and Connected. Choose an .xlsx to immediately see its saved active tab and cell addresses. Drag the recipe rectangle here, or choose its first and last cells across pages. Optional sidebar/header marks and Inspect-only mode make roles explicit. Manual addresses are optional. Check selected recipes without a .PRINT first. Then choose the project and select sample bodies plus BOTH complete physical printed label regions before saving.

See docs/WORKBOOK_INPUT.md for the complete flow and recovery states, and docs/INPUT_FLOW_CHECKPOINT.md for evidence and remaining acceptance work.

Verification: 96 Python tests, 23 Node contracts and 49 production-JavaScript/real-HTTP checks (123 requests) pass. The synthetic candidate save/download was audited for source/archive/nonmaterial preservation. The DOM test double is not a real browser. Windows execution, actual workbook compatibility, browser rendering/real dragging, Excel recalculation, GrabCAD GUI/recomposition and printing remain unverified.

Saved formula results require explicit confirmation and may still be stale. The app never calculates formulas, guesses six channels from a scalar, silently omits overlapping regions, normalizes percentages, or submits printer jobs. Save only separate unverified candidates; normal GrabCAD inspection/recomposition remains required. Do not print synthetic fixtures.

Runtime/dependency licenses and provenance remain unchanged. Checksums provide integrity, not signing or print-readiness certification. No public release or email accompanies this review build.

## Assistant-operated workflow

For reusable, assistant-operated material-only work, see [operator/README.md](operator/README.md) and [the reviewed-ID instructions](operator/REVIEWED_ID_MODE.md). Given the actual files, the operator must independently review and explicitly bind every workbook-cell/project-ID mapping to the actual labels and geometry. This is a narrowly bounded route, not a universal automatic importer or a new Windows UI release. Native GrabCAD acceptance remains unverified; keep private inputs, plans and outputs outside the repository.

The operator package is preserved exactly from the reviewed source; its manifest status describes the pre-publication review snapshot.
