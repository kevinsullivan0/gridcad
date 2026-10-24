# Acceptance and self-critique | 2026-10-24

## What the tested file pipeline achieves

The literal requested automation is implemented and exercised at the file-pipeline level: occupied two-dimensional Excel cells become geometry-matched sample-body material assignments in one batch, selected row/column glyph bodies receive direct EcoFlexBlack, and geometry, transforms, support, adhesion and unrelated settings remain unchanged. Inputs support holes, shifted ranges, delimiter choices and explicit orientation transforms, without a manually typed list of thousands of object IDs. Exact material matches can be skipped. Source files remain untouched and new outputs are unverified candidates, never printer jobs.

A small independent Python converter was checked against 485 admitted native reference recipes and 337 independently held-out recipes, comparing full material semantics except fresh UUIDs. Different synthetic native layouts, actual XLSX pipelines, the source-constructed recognized profile, and seven-resin adhesion cases were independently reopened using the native archive loader and actual Print/PolyJet schema validators. Those proprietary validators are not included in this distribution. Generated fixtures do not establish a universal contract or live-printer capabilities.

Safety tests cover hostile archive/XML structure, expansion/cell limits, path traversal/reserved names/collisions/symlinks, duplicate JSON keys/non-finite values, stale source/mapping identities, no-overwrite publication, review invalidation, request serialization and protected downloads. Numerical values are never silently normalized/rounded. Existing colors are not interpreted as completed work.

## Speed evidence, not an end-to-end promise

A synthetic 1,000-sample / 195-label-glyph workload (1,195 total bodies, curved 432-triangle meshes) took about 6.88 seconds for the Python workbook-to-candidate-and-preservation workflow on the development Linux host. Independent native archive/schema loading took about 3.16 seconds separately. Human interaction, Windows startup, full GUI loading and composition/slicing were excluded. No measured reduction of an 18-hour real workflow is claimed.

## Delivery design

The package includes the complete official Windows x64 embedded CPython 3.13.17 runtime and pinned pure-Python openpyxl 3.1.5, et-xmlfile 2.0.0 and defusedxml 0.7.1. It is designed for unzip and double-click without install, administrator rights, PATH/pip/network steps. It excludes proprietary GrabCAD code/database/installers and development material catalogs. Official download hashes and licensing notices are preserved. Checksums are integrity records, not a signature verification.

## What is not proved

- Actual execution of this packaged Windows runtime/launcher or a complete real-browser upload-to-download interaction. Browser empty-state appearance and client-state contracts are narrower checks.
- Full normal GrabCAD GUI reopening, saving, recomposition/slicing, live-service material feasibility or printing. Native archive/schema readback is not equivalent to these.
- Compatibility with the user's actual project/version, arbitrary complex features, assemblies/inheritance, every printer/profile or future schemas.
- End-to-end usability and elapsed time on a representative user project.

Self-critique: this closes the tested batch file-transformation and lightweight distribution portions, not the full production-readiness goal. The remaining acceptance step is a representative real Windows/project trial: launch the package, prepare a separate candidate, inspect recipes/labels and preservation in ordinary GrabCAD, and recompose successfully. Do not print the synthetic demo or treat an unverified candidate as print-ready.
