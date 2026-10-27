# GridCAD

**An offline Windows desktop converter for rectangular, labeled material grids.** Select an Excel recipe rectangle, inspect its mapping onto the project's actual geometry, and save a separate `.PRINT` candidate with a preservation audit. No LLM, account, browser or network service is used at runtime.

## Download and start

**[Download GridCAD 0.2.0-rc.2 for Windows x64](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.2/GridCAD-Windows-x64-v0.2.0-rc.2.zip)** · [Release notes and checksums](https://github.com/kevinsullivan0/gridcad/releases/tag/v0.2.0-rc.2)

**No installer, Python, terminal commands or agent required.**

1. **Download the Windows ZIP using the button above.** On the release page, choose `GridCAD-Windows-x64-v0.2.0-rc.2.zip`—**not** “Source code (zip)” or the portable-core ZIP.
2. In File Explorer, right-click the downloaded ZIP and choose **Extract All…**, then **Extract**. **Do not run the app from inside the ZIP.**
3. Open the extracted **GridCAD** folder and double-click **`GridCAD.exe`** (it may display as **GridCAD** if file extensions are hidden). Keep the whole folder together, including `_internal` and `advanced`; do not move the EXE out by itself.
4. Click **Load example**, then **Build mapping preview** for a first try. **The synthetic example is a software demonstration—do not print it.**
5. For your own supported files, open the workbook and project, select the recipe range and sample/label groups, choose orientation/transpose, check the physical labels and recipes, and save into a **new result folder**. Keep your originals; the app writes separate candidate copies.

**If Windows shows a warning:** this candidate is unsigned, so its publisher is not verified by a code-signing certificate. Windows or your organization may block it. Do not disable security protections; if blocked, stop and ask your IT/support contact. A matching checksum is not proof of publisher identity.

**Before printing:** native GrabCAD open/recompose/save and physical printing remain unverified. Every converted audit retains `print_ready=false`; inspect candidates in native GrabCAD first. GridCAD never submits printer jobs.

[Short manual](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.2/docs/DESKTOP_MANUAL.md) · [Windows screenshots and GUI-test evidence](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.2/GridCAD-Windows-GUI-evidence.zip)

### Verify the download

SHA256 values from the release's [SHA256SUMS.txt](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.2/SHA256SUMS.txt):

```text
a22f1a36216ae6a24722afb39164d1871770dae129c2cb9c4e221215c9cca435  GridCAD-Windows-x64-v0.2.0-rc.2.zip
3ac6b4a0934d08c1fc5f8d83d96ee6a0a82a3ff4a91da86980ad91c85430fdaf  GridCAD-portable-core-v0.2.0-rc.2.zip
```

**Optional integrity check—not an installation step:** on Windows, run `Get-FileHash .\GridCAD-Windows-x64-v0.2.0-rc.2.zip -Algorithm SHA256` in PowerShell and compare the value above. Matching hashes establish file integrity, not a signed publisher or native print compatibility.

## Compatibility and prerequisites

**What is tested, and what is not:** RC2's file conversion and extracted Windows app were tested. Opening, recomposing and saving its output in native GrabCAD—and physical printing—remain **unverified**. A successful conversion is not a promise that every GrabCAD version or printer will accept the result.

| Component | Intended support and evidence |
| --- | --- |
| GridCAD desktop | **Windows x64** portable app. Packaged with Python 3.13.16; actual GUI acceptance ran on GitHub's **Windows Server 2025** runner, including a 1024 × 768 desktop. That is not testing across every Windows desktop version. No 32-bit, ARM-native, macOS or Linux GUI build is supplied. |
| Input `.PRINT` files | The strict reviewed source profile is **GrabCAD Print 1.117.12.3985**, with internal schema **2170** for all five stored providers. Matching that header alone is insufficient: geometry, transforms, identities and materials must also pass the documented checks. |
| Other GrabCAD file versions | **Not automatically supported or claimed likely to work.** RC2 checks the saved file's profile, not whichever GrabCAD application you have installed. Different saved versions are refused; they need a tested adapter, not edited version numbers or a forced import. |
| Generated material serialization | Based on a separately observed **5.119.0** material profile: Print schema **2191**, PJ schema **2190**. These numbers describe material serialization—not extra accepted input versions, a recommendation to install that version, or proof of native compatibility with the older source format. |
| Workbook | `.xlsx` with the documented six-channel recipes. Excel is not needed to read saved values. For formula cells, recalculate and save current results in Excel or supply a values-only copy; GridCAD does not calculate formulas. |
| Portable source core | Python **3.10+**, standard library. The downloaded core CLI was exercised on **Linux with Python 3.12**. This is a source/CLI option, not a macOS or Linux desktop-app claim. |

**GrabCAD is not required to run the converter.** Conversion is local and offline; no vendor runtime or printer connection is called. You do need an appropriate native GrabCAD installation and your actual printer/material setup to perform the separate output-validation step before printing. Do not downgrade software or change project version fields simply to satisfy GridCAD's checks.

GrabCAD has its own requirements, separate from GridCAD's tests. The [official Stratasys English requirements page](https://support.stratasys.com/en/software/grabcad-print/about/system-requirements-for-grabcad-print), checked October 27, 2026, specifies 64-bit Windows 11 or newer, or Windows Server 2016 or newer, with an Intel/AMD AVX-capable processor; ARM is excluded. Consult that page for current installation, graphics and printer-network requirements.

See the [exact supported schema](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.2/docs/RECTANGULAR_SCHEMA.md) and [user manual](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.2/docs/DESKTOP_MANUAL.md). If a file is refused, follow the specific correction shown; keep the original and use the optional diagnostic report for a compatibility investigation rather than bypassing the guard.

## Supported workflow

The desktop supports the documented **rectangular 2170 source profile**, not arbitrary `.PRINT` files. It supports different sample shapes, sizes and heights on a common base plane—including tested pyramids and mixed shapes—when separated footprints and corroborated placements define an unambiguous rectangular grid. It proposes cell-to-body assignments without replacing the source meshes. Orientation and transpose are explicit choices. Users must check actual printed labels: a plausible grid or matching digest does not prove physical correspondence, and the app does not perform OCR.

Recipes contain six slash-separated **C/M/Y/K/W/T percentages**, including explicit zeros, totaling exactly 100. Saved formula results require confirmation; missing caches and invalid values are refused. GridCAD does not calculate Excel formulas, run macros, normalize percentages, repair unknown versions or force unsupported geometry through.

The guarded writer preserves nonmaterial geometry, transforms, identities, unrelated bodies and archive payloads. Originals and previous results are never overwritten. Each new result includes the candidate, exact assignments, reviewed plan and audit.

[Supported schema and adaptable examples](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.2/docs/RECTANGULAR_SCHEMA.md)


**Label materials:** keep the default direct-black policy or copy a complete compatible saved assignment from an unchanged reference body. Supported references are existing PolyJet EcoFlex direct materials or validated CMYKWT mixers—not arbitrary printer families or newly invented materials. Replacing an existing different label assignment requires reviewing the complete list, explicit confirmation and a rebuilt preview; shared or inconsistent identities remain refused.

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

**Advanced / Agent & help** provides documentation and a copyable prompt pointing an external agent at installed files or exact release source. The [portable core download](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.2/GridCAD-portable-core-v0.2.0-rc.2.zip) runs on Python 3.10+ with the standard library; its CLI was also checked on Linux.

Nonrectangular lattice layouts (such as triangular or hexagonal layouts), grids stacked in 3D and unsupported transforms are **not implemented**. That restriction concerns layout, not whether an individual sample is a pyramid or another 3D shape. Extensions need explicit adapters and evidence, not relaxed safety guards.

[Release source](https://github.com/kevinsullivan0/gridcad/tree/v0.2.0-rc.2) · [API and CLI](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.2/docs/DESKTOP_API.md) · [Agent instructions](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.2/AGENTS.md)

**Source layout:** the desktop implementation is at the release tag above. The default branch still contains the earlier browser implementation and operator; this README update does not merge the desktop branch.


### Helpful errors, with optional agent assistance

Errors explain the problem and a practical manual correction first. Optional controls reveal technical details, open a local diagnostic report, or copy a prompt to paste into an agent you already use. Nothing is automatically uploaded or launched; an external agent needs deliberate file access or an attachment. Reports contain selected paths/names and traceback frames, not project/workbook contents or Python locals. Ordinary conversion needs no agent.

**Advanced / Agent & help** also includes About/version and an offline view of bundled third-party licenses. See [licensing scope](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.2/docs/LICENSING.md).

## Verification and earlier work

The release passed **81 operator tests, 13 desktop-core tests, seven shape tests, seven diagnostics tests and real extracted-package Windows GUI acceptance**: native dialogs, long worksheets, formula-cache refusals, mapping/transpose, guarded saving, repeated example loading, pyramid/mixed grids, explicit label replacement review/cancel/rebuild, local diagnostic copying and recovery, About/licenses, and the bundled CLI. Two private actual-file conversions reproduced earlier independently reviewed candidates byte for byte. Independent mapping and usability/package reviews passed, and published asset checksums were verified after download. These checks do not establish native GrabCAD or printer acceptance.

The earlier browser alpha uses `launch-windows.cmd`, **not** the desktop launch route. Its [historical instructions and verification limits](https://github.com/kevinsullivan0/gridcad/blob/a81ccb2ed759d5fec6d609805230f467d03f5cf6/README.md) and old releases remain available. The [assistant-operated workflow](operator/README.md) and [reviewed-ID instructions](operator/REVIEWED_ID_MODE.md) remain useful when an operator independently establishes an explicit cell-to-body mapping.

Preserve third-party notices and private input boundaries. Original GridCAD code is licensed under the [MIT License](LICENSE), copyright 2026 Kevin Sullivan. Third-party runtime components retain their own licenses and notices; this does not relicense the entire bundled binary. Checksums establish integrity, not signing or print readiness.
