# Local candidate-copy interface

## Start on Windows

Extract the complete portable ZIP to a normal folder, then double-click `launch-windows.cmd`. It uses the included official Python runtime directly: no Python installation, PATH change, administrator rights, pip or network download is needed. `setup-windows.cmd` is an alias for launching, not an installer. Keep the terminal open. Close it or press Ctrl+C to stop and remove session uploads and candidate downloads.

Packaged execution on Windows has not yet been tested. The Python/HTTP integration tests run on Linux against the included pure-Python dependencies. If the browser does not open, copy the full local link printed in the terminal, including the fragment session code. Source users on other systems can install the pinned requirements in their own environment and run `python grabcad_grid_ui.py`.

## Workflow

1. Choose the `.xlsx` and saved `.PRINT` files. Choose worksheet/range and slash-separated CMYKWT schema as needed. Blank cells remain holes, not zero recipes.
2. Inspect, then drag aggregate sample, row-label and column-label regions on the XY tray view. All bodies must be wholly enclosed. Update mapping proposals. No per-object IDs or manual JSON editing is required. Both complete label regions are required for candidate saving.
3. Choose an orientation explicitly. The tray overlays workbook cell coordinates, using edge anchors for dense grids. Review exact recipes, preserved objects and any layout warnings. Labels are direct EcoFlex Black, not K=100.
4. Confirm the complete role/orientation selection and explicitly choose replacement of selected materials. Existing colors are not proof of completion. Full exact material matches are skipped. This UI does not expose partial-fill mode.
5. Preview exact changes. The server prepares, checks and deletes a private disposable candidate to verify numeric admission, exact change counts and preservation before enabling Save. Nothing is downloaded during this check. Expand the correspondence details for exact cell → body recipes.
6. Save an unverified candidate copy. This repeats the public backend checks against the bound source, then offers a token-protected download with a distinct candidate filename. Do not replace the source if your browser asks where to save. A download-again button recovers a missed download without repeating candidate generation.
7. Open the new copy in normal GrabCAD Print, inspect representative recipes and label material mode, and recompose. Python checks are not a print-ready certification. This tool never connects to a printer or submits jobs.

## Compatibility and accuracy

The actual source gate is shown. Unknown profiles or unsupported features remain preview-only and cannot be enabled by a checkbox or user-entered resin IDs. The backend admits the recognized J850 TechStyle/Fabric/HighMix profile, six EcoFlex channels, optional EcoContactFlex adhesion and separate FullCure705 support. See the compatibility document for the precise boundary.

Recipe decimal strings, not RGB swatches, are authoritative. Four-decimal inputs are extensively tested; native round-trip admission is authoritative and no silent rounding occurs. Errors identify workbook cells and channels when relevant. Correct an invalid recipe in the workbook, select it again and inspect afresh.

## Local safety

The server binds only IPv4 loopback at a random port. Requests require the exact Host and same Origin if supplied, reject cross-site Fetch Metadata, and use a secret fragment-derived session token for API calls and downloads. No telemetry or external browser assets are used. CSP disallows remote scripts and embedding. Filenames supplied by the browser never become server paths.

HTTP work is serialized, including concurrent uploads. Input changes revoke the review; files, analysis IDs, candidate IDs and one-use save review IDs are checked. A failed save consumes its review and cannot silently be retried. A new preview is required. Outputs use the backend's atomic new-path publication and are never the source path. Unknown or cross-session download identifiers cannot access files. Stopping the process removes temporary data, though an OS crash may leave a temporary directory for normal OS cleanup. Exported review JSON contains recipe/project data and should be kept private.

## QA boundary

Local HTTP tests exercise real candidate generation, source preservation, exact previews, protected downloads, stale/replayed IDs, concurrent uploads, changed options/files, revoked confirmations and failed requests. JavaScript syntax and five client state-contract groups (save gating, explicit orientation, review invalidation, request serialization and hash-change reload) are checked locally with Node, not a real browser. The empty state was visually checked in a cloud browser without uploading files. Full browser workflow interaction, actual Windows execution and normal GrabCAD GUI reopen/recomposition remain unverified; no browser upload approval was bypassed to perform them.
