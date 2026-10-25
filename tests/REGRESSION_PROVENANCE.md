# Preserved safeguards: new regression suite

`test_preserved_safeguards.py` was newly written on 2026-10-24 for the workbook UX repair. **It is not the original 134-test suite and does not reproduce that suite's entire verification scope.** No application source was changed while creating these tests.

## Recovery outcome

- The published source commit `40c85b969593a1080d8ee9d9bcfc4a8803076478` has no tests or development fixtures. This was checked using the connected GitHub read-only recursive tree API.
- Local source staging records identify the former development tree as `/workspace/shared/grabcad_grid_tool_20261024`; that tree is absent. Searches of available workspace paths and relevant archives found no original test source. Two Library searches also returned no matches; this is not a claim that every possible external copy is absent.
- `grabcad_delivery/source-freeze.json` preserves hashes for seven Python test modules and one JavaScript test file. `grabcad_delivery/staged-tests.log` preserves the 134 historical Python test IDs and pass results, not their implementations.
- `original-suite-inventory.json` retains those original file hashes and test IDs as an exact recovery inventory, not runnable coverage or a current pass claim.
- The packaged source matches the published release code. After testing, all 288 release payload files were byte-compared with the sealed ZIP and matched; generated Python bytecode caches were removed. The release ZIP was not changed.

Source tree: https://github.com/kevinsullivan0/gridcad/tree/40c85b969593a1080d8ee9d9bcfc4a8803076478

## Synthetic input provenance

The two `fixtures/DO_NOT_PRINT_*` files are exact copies of the sealed release's `demo_DO_NOT_PRINT` examples. The release explicitly describes them as source-constructed contract fixtures, not user projects, usable printer configurations, or printable glyphs. They contain no private workbook data.

- `DO_NOT_PRINT_synthetic.PRINT`: SHA-256 `76973f60dc4a77e698e074c39ecf78bfe16253302235e122ad076a6c4e04dff0`
- `DO_NOT_PRINT_grid.xlsx`: SHA-256 `3efba8b6aaec3098d30351bf7708631e1a0671c49c9c464b4cf3ede239e50c21`

The pair contains a 2-by-4 workbook rectangle with one hole, seven sample bodies, and twelve geometric label stand-ins. Other workbooks, malformed archives, and mutated projects are generated in temporary directories during tests. Nothing is sent to a printer or external service. Candidate files are temporary, explicitly unverified copies and are removed after each test.

## Current execution

42 tests pass against both the unchanged sealed-release Python source and the workbook UX development source. Baseline runtime was 0.810 seconds; development runtime was 0.785 seconds. Logs are `baseline-preserved-safeguards.log` and `ux-preserved-safeguards.log`. These logs are snapshots; rerun after any subsequent edits.

The run used the host Linux Python with `-B -S` and the release's pinned pure-Python dependencies on `PYTHONPATH`: openpyxl 3.1.5, et-xmlfile 2.0.0, defusedxml 0.7.1. No installation, Windows runtime execution, or native vendor code was needed.

Run from outside the source directory so the selected source is unambiguous:

```sh
BASE=/workspace/scratch/561510fd74d4/grabcad_delivery/GridCAD-Windows-x64-2026-10-24
WORK=/workspace/scratch/561510fd74d4/gridcad_workbook_ux
cd /tmp
PYTHONPATH="$WORK:$BASE/runtime/site-packages" python -B -S -m unittest discover \
  -s "$WORK/tests" -p test_preserved_safeguards.py -v
# Baseline: replace "$WORK:" with "$BASE:" in PYTHONPATH.
```

At the development run, `gridcad/core.py` SHA-256 was `72552526895f84c159e0a346eb10e3d60e28a870d120a1f9869179d60fca3461`. Geometry, candidate writer, and material converter retained the sealed source-freeze hashes.

## Coverage and precise limits

This new suite covers:

- Exact decimal parsing, no normalization, explicit channel order/delimiter/empty-channel handling, invalid scalar distinction, and uncompacted blank rows/columns.
- Merged-grid and XML entity rejection; unsafe/colliding/Windows-reserved ZIP paths, symlinks, expansion/count limits, strict JSON, duplicate occurrence and dangling body rejection.
- Material channel IDs and fractional alpha, direct label EcoFlexBlack versus K100 mixer, loss-of-precision refusal, fresh non-aliased state, provider integrity/profile checks, and no print-ready claims.
- All eight typed coordinate transforms, asymmetric-hole orientation, explicit review even for a unique candidate, label/sample role separation, cut-region rejection, stale and swapped mappings, unsupported units/transforms/schema/profile refusal.
- Actual synthetic candidate creation; source, archive payload, and nonmaterial state preservation; no-overwrite/no-input-output writes; explicit assignment policy; exact-repeat skipping with refreshed review.

Not recovered or re-established by this suite:

- The original Python modules: candidate writer (32 tests), core (18), fixture writer (6), geometry (35), material converter (11), HTTP/UI (27), and workbook XML parts (5). All original individual IDs are recorded in `original-suite-inventory.json`; similar new checks do not establish source recovery or full equivalence.
- The original JavaScript five client-state groups and nine bootstrap checks.
- The 485 native reference recipes and 337 independent held-out material vectors, proprietary native archive/schema loaders, additional native fixture variants, seven-resin adhesion scenarios, large/thousands-of-body geometry/cache budgets, ancestor/container variants, and performance benchmarks.
- Full original HTTP security/session/token/origin/concurrency/replay/download protection tests, atomic-publication race/failure-injection cases, and full original XML renamed/relocated relationship/content-type adversarial cases.
- Original diagnostic fixture-writer integration, every unselected-object preservation scenario, and every native profile/feature combination.
- Windows execution/launcher/security behavior, full browser interaction, normal GrabCAD GUI reopen/recomposition/slicing, real projects, physical output, or live-printer feasibility.

## Transpose and long-sheet extension

`test_transpose_mapping.py` adds 11 new tests. A temporary 4-by-2 workbook at `C5:D8` is constructed by transposing the shipped 2-by-4 synthetic recipe rectangle. Its original source cell addresses map to the correct physical bodies; source hole `C7` maps to physical position `[0, 2]`. Physical row-label and column-label regions retain their roles and direct EcoFlexBlack, with no inferred label text. An actual unverified candidate copy is checked for recipe/material semantics, source immutability, archive payload preservation, and all nonmaterial fields.

The extension also covers a 500-by-4 selected rectangle, wholly blank internal rows/columns, validation at the end of the worksheet, the last bounded workbook-preview page retaining original cell addresses, rejection above 100,000 selected cells, explicit HTTP transpose filtering without source-grid mutation, and rejection of non-boolean transpose flags.

All 11 extension tests passed in 0.860 seconds. The combined current suite of 42 preserved-safeguard, 11 transpose/long-sheet, and 14 workbook UX/API tests passed: **67 tests in 3.833 seconds**, zero failures/skips. Logs: `transpose-mapping.log`, `combined-python-tests.log`. This combined run occurred on 2026-10-24 around 23:02 UTC. It is not a rerun or recovery of the historical 134-test suite and does not establish actual browser layout behavior, Windows execution, or printer acceptance.


## Current alpha.3 input-flow checkpoint (2026-10-25)

The current root test-results.txt records 96 passing Python checks. qa/dom-contract-results.json records 23 contracts. qa/input-flow-http-results.json records 49 production-JavaScript/real-HTTP checks over 123 requests and an audited synthetic save/download. Older per-suite logs in this directory describe earlier alpha.2 runs, not the current total. Two independent reviews reran current checks. No browser rendering, real pointer hit-testing, Windows or actual-user-file acceptance is inferred.
