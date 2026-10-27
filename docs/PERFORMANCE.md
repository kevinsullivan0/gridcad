# Measured core performance pass (2026-10-27)

Baseline: immutable `v0.2.0-rc.3`, commit `341accf315e9eecedca4e7ee054a0f6ef450d735`.
This pass changes implementation work, not the supported source/geometry/material contract or the UI.
The released RC3 archive is not replaced by this report.

## First-pass measurements

Five alternating baseline/candidate runs in isolated Python processes on the same Linux x86-64 cloud executor, Python 3.12.14. Values below are medians. All inputs are newly generated synthetic data, not private projects or native GrabCAD acceptance evidence. Wall time on a shared cloud CPU is variable; these are workload-specific observations, not universal speed guarantees.

| Workload | RC3 time | Optimized time | RC3 peak RSS | Optimized peak RSS |
| --- | ---: | ---: | ---: | ---: |
| 33 × 21 mixed-shape grid, load/workbook/propose/save, reference labels | 1.497 s | 1.213 s | 54.89 MiB | 54.88 MiB |
| 4 × 6 grid plus preserved 64 MiB compressed opaque payload, whole workflow | 0.693 s | 0.510 s | 206.83 MiB | 25.91 MiB |
| 600,000-triangle STL, including 300,000 visible top triangles, mesh parsing | 2.506 s | 2.244 s | 76.67 MiB | 55.00 MiB |
| 1 × 5,000 grid, position validation/ranking only | 2.653 s | 0.033 s | 25.91 MiB | 25.91 MiB |

RSS is the process high-water mark, including imports and input allocation, not a Python-only allocation estimate. The last case isolates an algorithmic edge case: it does not mean an entire conversion became 80× faster. The ordinary mixed-grid workflow improved about 19% in this measurement; it did not materially reduce memory.

Raw samples and exact output identities: [qa/performance/2026-10-27-linux.json](../qa/performance/2026-10-27-linux.json).
Every compared workflow produced the same complete candidate archive SHA-256 and mapping SHA-256. The mesh comparison checks exact bounds, triangle count, source hash and full top-projection array hash. Grid-rank outputs match exactly.

## Second bounded pass

A final STL-only pass replaces temporary three-value slices and generic min/max calls with finite scalar comparisons in the same coordinate order. Five alternating fresh-process comparisons against first-pass commit `b3a3666c72c8229f85a9a260ab0cbddb1a1565b6` measured the 600,000-triangle workload at **2.321 → 1.601 seconds wall time** (2.320 → 1.601 seconds process CPU time), about **31% faster for this parsing stage**. Peak memory is unchanged at this stage. This is not a whole-app speed claim. Source/bounds/top-array identities match exactly, and new tests compare the original scalar order over signed zeros, tiny/large finite values and seeded random coordinates.

Raw samples: [second-pass Linux measurements](../qa/performance/2026-10-27-second-pass-linux.json). The benchmark now records process CPU time as well as wall time to distinguish computation from scheduling noise. Other full-workflow timings in the second exploratory run were noisy, so no additional whole-workflow speed claim is made beyond the first-pass table.

## Changes and retained safeguards

- Stream untouched archive payloads through 1 MiB chunks instead of allocating entire members twice. ZIP metadata, order, comments, payload hashes, source CRC checks, independent destination CRC/hash readback, final input hashes and atomic no-overwrite publication remain.
- Validate a shared label-material reference once within each immutable preparation call. Each label still has its own source fingerprint, action/conflict/appearance checks and independent returned material copy. Nothing is cached across operations. Fallback black-material existence is likewise scoped to one preparation.
- Reuse the already-read candidate document for later material checks. The candidate is still independently parsed and compared against intended content before those checks.
- Reuse one recipe provider per rectangle, retaining every per-cell precision check and source-integrity recheck. This also keeps one implementation-integrity snapshot throughout that operation.
- Inspect STL bytes through a read-only view rather than copying the triangle payload twice. No numerical, bounds, finite-value, triangle-count or top-surface checks change.
- Locate sorted-grid positions using binary search rather than scanning every axis center for every sample. Preserve the original first-minimum rule even for floating-point rounded-distance ties and overflow; use the original scan for nonfinite inputs. Cluster formation, spacing tolerances, footprint/anchor gates and neighbor checks are unchanged.

## Regression checks and limits

New tests cover per-call cache lifetime, independent material copies, every-label fingerprint refusal, per-cell provider checks, streamed metadata/payload preservation, corrupt stored-member CRC refusal and staged-file cleanup, STL refusal behavior, exact floating-point ranking equivalence, nonfinite fallback, logarithmic lookup work and skinny-grid mappings. All 81 operator and 145 desktop/legacy Python tests passed after the second pass, together with the legacy JS DOM-contract/HTTP integration checks from the first pass. Existing tests remain in the suite. The Windows workflow includes both new test modules.

This Linux pass does not rerun the previous private source files, which are not present on this executor. It does not claim Windows packaged-GUI validation, native GrabCAD reopen/recompose/save, printer compatibility or print readiness. Those remain separate gates. No guard is removed to obtain a timing improvement.

## Reproduce

Check out the baseline and candidate into separate folders. Run the candidate's benchmark tool with an output folder that does not yet exist. The tool creates only synthetic inputs and new outputs, and refuses an existing output folder.

PowerShell, from the candidate checkout:

```powershell
python .\tools\benchmark_performance.py --baseline "C:\work\gridcad-rc3" --candidate "C:\work\gridcad-candidate" --output "C:\work\new-benchmark" --repeats 5
```

POSIX shell, from the candidate checkout:

```sh
python3 ./tools/benchmark_performance.py --baseline /work/gridcad-rc3 --candidate /work/gridcad-candidate --output /work/new-benchmark --repeats 5
```

Linux/macOS report peak RSS; Windows reports timings and exact equivalence but leaves RSS null. The benchmark is an optional developer tool, not required for ordinary app use. Generated `.PRINT` fixtures are non-native contract examples and must not be printed.
