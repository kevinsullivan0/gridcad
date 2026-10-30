# Ordinary conversion and recovery implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task. Checkboxes track executed evidence, not intentions.

**Goal:** Let an ordinary user correct selection/setup mistakes and save a separate PRINT without guessing.

**Architecture:** Keep the existing native Tk app and deterministic writer. Add coherent preflight state and contextual guidance; retain all source/material/output guards. New direct materials are deferred to GitHub issue #3.

**Tech stack:** Python, Tk/ttk, Pillow, current PowerShell/BAT launchers, unittest and hosted Windows GUI acceptance.

**Spec:** Approved direction from `2026-10-30-ordinary-conversion-design.md`; independent preimplementation matrix and addendum are retained privately and drive the acceptance journeys.

## Global constraints

- Cloud only, regular Sol; no user laptop, Squirrel or CCSS access.
- No new resin assignment, fabricated native evidence, OCR or label generation.
- One recipe cell per sample: C/M/Y/K/W/T slash-separated percentages; different rectangular dimensions and existing label bodies remain supported.
- Never overwrite inputs/existing outputs or silently normalize values; published tags/assets stay immutable.
- The owner explicitly authorized merging and publishing a new release for this fix set after regression, independent review and Windows evidence. Do not submit a review approval on the owner's behalf; preserve older releases.

## Review focus

- Partial/mismatched selection corrected and broken again must never revive an old mapping.
- Missing multiple choices must all be visible with text, useful focus and per-field clearing.
- No saved formula result, an Excel error or no detected recipe block must never masquerade as valid data.
- Material names/swatches must follow complete supported identities, not body names or guessed tray recipes.
- Source fallback, canceled/colliding saves, minimum-size windows and changed grid dimensions must remain usable.

### 1. Selection, schema and formula semantics

**Files:** `desktop_core.py`, `operator/gridcad_operator/operator.py`, `gridcad_desktop.py`, new `tests/test_conversion_recovery.py`.

- [x] Write failing cases for 20/24 counts, all missing fields, overlap, no detected range, malformed addressed recipe and saved-cache policy without freshness attestation. Run red.
- [x] Add pure selection/preflight state in the current GUI module, consuming current book/project and selector values; return counts plus keyed actionable messages. Wire live counts and field error text/styles/focus without doing costly material work on keystrokes.
- [x] Add explicit saved-cache policy for desktop use, leaving reviewed CLI confirmation behavior intact; missing/error caches still fail. Include sheet/range/cell in recipe/count/shape errors. Remove global checkbox and show conditional factual formula notice.
- [x] Run focused tests and full app/operator suites; commit.

### 2. Material display and basic workflow surface

**Files:** `gridcad_desktop.py`, `docs/DESKTOP_MANUAL.md`, existing help/material/UI tests.

- [x] Write failing UI cases for metadata-only names/deduplication, supported saved swatch, one short Help, diagnostics-only report, default output folder and cancel/retry. Run red against real Tk where available.
- [x] Keep current validated black/reference assignments, present one name-based list without body-name composites or “— labels”; show saved appearance with clear/translucent indication. No additional material constructors.
- [x] Keep one short Help tab; move report option to Diagnostics with a plain explanation. Default Save to last chosen session folder, otherwise source folder, otherwise Documents for examples/app paths. Preserve cancellation/no-overwrite behavior and visible actual save location.
- [ ] Run focused/full tests and an independent ordinary-user wording/interaction review; commit.

### 3. One normal launch entry and exact Windows acceptance

**Files:** `tools/build_windows.py`, `tools/windows_launcher.ps1`, authored source BAT, launcher/package tests, `tools/windows_gui_acceptance.py`, launcher/distribution acceptance, README/help.

- [x] Write failing distribution tests showing only the main BAT at the combined package root and a working nested troubleshooting fallback; retain source-only ZIP usability. Run red.
- [x] Package fallback under Troubleshooting and resolve its app root safely; update the primary launcher's internal path and explicit recovery instructions. Preserve signatures/hashes/consent/manifest/no-duplicate-process protections.
- [ ] Extend real Windows journeys: missing choices/focus, 20→24→20 recovery, addressed recipe errors, another grid dimension, save destination/cancel/collision/retry, current material preview, one Help, diagnostics report and nested fallback. Record exact artifact/hash, screenshots and output readback.
- [ ] Run all local app/operator tests and source packaging; push coherent tested branch and draft PR. Own hosted Windows workflow to terminal, repair failures and rerun the exact revised candidate.
- [ ] Report actual results and native GrabCAD limits; carry the explicitly authorized merge and exact-artifact release through verified readback.
