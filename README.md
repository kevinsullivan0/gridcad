# GridCAD

**An offline Windows desktop converter for rectangular, labeled material grids.** Select an Excel recipe rectangle, inspect its mapping onto the project's actual geometry, and save a separate `.PRINT` candidate with a preservation audit. No LLM, account, browser or network service is used at runtime.

## Download and start

**[Download GridCAD 0.2.0-rc.1 for Windows x64](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.1/GridCAD-Windows-x64-v0.2.0-rc.1.zip)** · [Release notes and checksums](https://github.com/kevinsullivan0/gridcad/releases/tag/v0.2.0-rc.1)

1. Extract the **entire ZIP** into a fresh folder.
2. Open **`GridCAD.exe`**. Keep `_internal` and `advanced` beside it. Python and dependencies are bundled; no installation, administrator rights or first-launch download is required.
3. Choose **Load example**, then **Build mapping preview**.
4. For supported actual files, open the workbook and project, select the recipe range and sample/label groups, explicitly choose orientation/transpose, inspect physical labels and exact recipes, and save a **new result folder**.

**Unsigned release candidate: native GrabCAD open/recompose/save and physical printing remain unverified.** Follow your organization's normal application-trust policy; do not disable security protections. Every converted audit retains `print_ready=false`. Inspect candidates in native GrabCAD before printing. GridCAD never submits printer jobs.

[Short manual](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.1/docs/DESKTOP_MANUAL.md) · [Windows screenshots and GUI-test evidence](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.1/GridCAD-Windows-GUI-evidence.zip)

## Supported workflow

The desktop supports the documented **rectangular 2170 source profile**, not arbitrary `.PRINT` files. It derives a uniform lattice from embedded mesh geometry, checks occurrence/geometry agreement, and proposes cell-to-body assignments. Orientation and transpose are explicit choices. Users must check actual printed labels: a plausible grid or matching digest does not prove physical correspondence, and the app does not perform OCR.

Recipes contain six slash-separated **C/M/Y/K/W/T percentages**, including explicit zeros, totaling exactly 100. Saved formula results require confirmation; missing caches and invalid values are refused. GridCAD does not calculate Excel formulas, run macros, normalize percentages, repair unknown versions or force unsupported geometry through.

The guarded writer preserves nonmaterial geometry, transforms, identities, unrelated bodies and archive payloads. Originals and previous results are never overwritten. Each new result includes the candidate, exact assignments, reviewed plan and audit.

[Supported schema and adaptable examples](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.1/docs/RECTANGULAR_SCHEMA.md)

## Examples

The package includes an editable Excel template, synthetic demonstration archive, preview images, and ordinary STL sample/label bodies with shared millimetre coordinates and an import guide. Counts, pitch and sample size are configurable with the supplied generator.

**The synthetic `.PRINT` is a software-contract demonstration, not a native-generated print job. Do not print it.** The STL companion is a geometry starting point; native import and the resulting project profile still need verification. Private customer files and proprietary vendor software are not bundled.

## Structure and agent access

The small desktop UI sits on a reusable core:

| Layer | Purpose |
| --- | --- |
| `gridcad_desktop.py` | Tk/ttk desktop controls, worksheet selection, Pillow geometry preview and review/save flow. |
| `desktop_core.py` | Deterministic rectangular mapping, recipe validation and reviewed-plan construction. |
| `operator/gridcad_operator/` | Guarded material writer and preservation checks shared with the earlier reviewed-ID workflow. |
| `desktop_cli.py` | Scriptable interface to the same core, bundled as `advanced/GridCAD-core.exe` on Windows. |
| `AGENTS.md`, `docs/`, `tools/` | Agent contract, schema/API/manual, example generator, packaging and acceptance tests. |

**Advanced / Agent & help** provides documentation and a copyable prompt pointing an external agent at installed files or exact release source. The [portable core download](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.1/GridCAD-portable-core-v0.2.0-rc.1.zip) runs on Python 3.10+ with the standard library; its CLI was also checked on Linux.

Triangular, hexagonal and arbitrary 3D conversion are **not implemented**. Extensions need explicit adapters and evidence, not relaxed safety guards.

[Release source](https://github.com/kevinsullivan0/gridcad/tree/v0.2.0-rc.1) · [API and CLI](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.1/docs/DESKTOP_API.md) · [Agent instructions](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.1/AGENTS.md)

**Source layout:** the desktop implementation is at the release tag above. The default branch still contains the earlier browser implementation and operator; this README update does not merge the desktop branch.

## Verification and earlier work

The release passed **61 operator tests, 13 desktop-core tests and real extracted-package Windows GUI acceptance**: native dialogs, long worksheets, formula-cache refusals, mapping/transpose, guarded saving, repeated example loading and the bundled CLI. Two private actual-file conversions reproduced earlier independently reviewed candidates byte for byte. Independent mapping and usability/package reviews passed, and published asset checksums were verified after download. These checks do not establish native GrabCAD or printer acceptance.

The earlier browser alpha uses `launch-windows.cmd`, **not** the desktop launch route. Its [historical instructions and verification limits](https://github.com/kevinsullivan0/gridcad/blob/a81ccb2ed759d5fec6d609805230f467d03f5cf6/README.md) and old releases remain available. The [assistant-operated workflow](operator/README.md) and [reviewed-ID instructions](operator/REVIEWED_ID_MODE.md) remain useful when an operator independently establishes an explicit cell-to-body mapping.

Preserve third-party notices and private input boundaries. The repository adds no general project license grant. Checksums establish integrity, not signing or print readiness.
