# Alpha.2 verification and remaining acceptance work

This portable prerelease contains the independently reviewed workbook-input changes only: actual tab selection; addressed, paginated data grid and cross-page range selection; expected schema/raw/cache/parsed diagnostics; explicit saved-result confirmation; structured-formula rejection; long-grid and transpose controls; and clearer exact-change/physical-label guidance.

Current evidence: 72 newly written Python tests and 23 Node minimal-DOM checks pass on Linux. The reviewed source was independently checked. The historical 134-test source suite was not recoverable. Historical native-reference/benchmark evidence from alpha.1 is not newly reproduced evidence for this build. See test-results.txt, qa/dom-contract-results.json and tests/REGRESSION_PROVENANCE.md.

Package verification checks ZIP CRC, safe relative paths, every per-file SHA-256 entry and an allowlisted diff from alpha.1. Runtime, dependencies, launchers, geometry.py, candidate_writer.py and material_converter.py must match alpha.1 byte-for-byte. No source ZIP or original package is overwritten.

Not established: real-browser visual/interaction behavior, alpha.2 Windows execution, actual-user-workbook compatibility, Excel recalculation, GrabCAD GUI reopen/save/recompose/slicing, live printer/material feasibility or physical output. Browser checks did not start due to the test environment. A user's alpha.1 launcher success is not an alpha.2 end-to-end test.

Before production use: test a representative copy of the user's workbook/project on Windows; verify selected recipe boundaries, cached/formula results and explicit transpose/orientation; save a separate candidate; inspect representative recipe/label material modes and preserved objects in normal GrabCAD; recompose. Do not print synthetic fixtures or treat this candidate as print-ready.

No trust/security settings are changed automatically. Do not bypass Windows or organizational security blocks. This unsigned package and its checksums are not a security certificate.
