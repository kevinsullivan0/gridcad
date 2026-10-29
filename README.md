# GridCAD

**An offline Windows converter for rectangular, labeled material grids.** Select an Excel recipe rectangle, inspect its mapping onto the project's geometry, and save a separate `.PRINT` candidate with a preservation audit. No account, LLM, browser or network service is required at runtime.

## Download and start

**[Download GridCAD 0.2.0-rc.7 for Windows x64](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.7/GridCAD-Windows-x64-v0.2.0-rc.7.zip)** · [Release notes, checksums and test evidence](https://github.com/kevinsullivan0/gridcad/releases/tag/v0.2.0-rc.7)

1. Download the **Windows x64 ZIP**, not “Source code” or the portable-core ZIP.
2. In File Explorer choose **Extract All…**. Open the extracted **GridCAD** folder and double-click **GridCAD.exe**. No installer, Python or terminal commands are needed.
3. Keep the whole folder together, including `_internal` and `GridCAD-core.exe`; do not run from inside the ZIP or move the EXE out by itself.
4. Try **Load example**, then **Match cells to samples**. The synthetic example is a software demonstration—**do not print it**.
5. For your files, open the workbook and project; click, drag or Shift-click the recipe cells; choose sample and label groups, the starting corner and the next-row direction. Click any preview sample to inspect its material; choose **Match cells to samples** to see its worksheet recipe. Save a valid mapping to a **new result folder**, then check the result and physical labels before printing. Originals remain unchanged.

### Source launcher

**[Download the RC7 source launcher](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.7/GridCAD-RC7-source-launcher.zip)** · [Launcher checksum](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.7/GridCAD-source-launcher-SHA256.txt)

Extract All, open **GridCAD-source-launcher**, and double-click **Start GridCAD.bat**. It runs the same RC7 interface from Python source instead of the packaged EXE. If compatible official Python is missing, setup asks permission to download and verify it before installing it for your account. First setup needs internet; later launches reuse the environment and work offline. Keep the console window open while using GridCAD.

Installation, offline reuse and recovery were tested on hosted Windows. This does not disable security protections or guarantee compatibility with Smart App Control.

**Unsigned release candidate:** follow your normal application-trust policy. Do not disable security protection, bypass malware/policy blocks or change administrator settings to run it. On a managed device, follow your administrator's policy. A checksum proves download consistency, not safety or publisher identity.

**Before printing:** native GrabCAD open/recompose/save and physical printing remain unverified. Every output retains `print_ready=false`; inspect and validate it in native GrabCAD first. GridCAD never submits printer jobs.

## Supported workflow

- **Windows x64 portable desktop.** Tested as an extracted package on GitHub-hosted Windows, including a 1024 × 768 desktop and the minimum window size—not every Windows version. No macOS/Linux GUI or ARM-native build is supplied.
- **Excel `.xlsx` recipes:** explicit C / M / Y / K / W / T percentages totaling exactly 100. Formula results require recalculation/saving in Excel and explicit acknowledgment; missing results fail.
- **Reviewed `.PRINT` source profile:** GrabCAD Print **1.117.12.3985**, internal schema **2170**. Matching a header is not enough: geometry, transforms, identities and materials must pass the documented checks. Other saved versions require a tested adapter, not edited headers or an override.
- **Unambiguous rectangular layouts.** Individual samples may have different shapes or heights; triangular/hexagonal lattices, stacked 3D grids and unsupported transforms are not implemented.
- **Existing supported material profiles only.** Preserve complete matching materials and identities; replacing conflicting label assignments requires explicit review. This is not universal CAD or arbitrary printer/material conversion.

Preview work is bounded and may be sampled; its notice explains reduced detail. Exact conversion does not use the sampled display. Resource limits and unsupported inputs are refused rather than silently truncated or repaired.

[Supported schema](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.7/docs/RECTANGULAR_SCHEMA.md) · [User manual](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.7/docs/DESKTOP_MANUAL.md)

## Verify and get help

For the packaged EXE download, compare its SHA256 with the exact filename in [SHA256SUMS.txt](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.7/SHA256SUMS.txt). On Windows, an optional check is:

```powershell
Get-FileHash ".\GridCAD-Windows-x64-v0.2.0-rc.7.zip" -Algorithm SHA256
```

**Help** opens the offline guide. Errors offer manual remedies and optional local diagnostics. Optional agent tools do not launch an agent, connect an account or upload files; sharing a report or local path remains your choice. [Agent download/checksum guide](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.7/docs/AGENT_INSTALL.md).

The release includes [Windows GUI evidence](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.7/GridCAD-Windows-GUI-evidence.zip). Testing covers conversion preservation, real mouse selection, responsive activity feedback and guarded saving; it is not native printer certification. Security review coverage is partial, not a clean security certification; see release notes.

## Source and advanced use

[Exact release source](https://github.com/kevinsullivan0/gridcad/tree/v0.2.0-rc.7) · [API / CLI](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.7/docs/DESKTOP_API.md) · [Portable Python core](https://github.com/kevinsullivan0/gridcad/releases/download/v0.2.0-rc.7/GridCAD-portable-core-v0.2.0-rc.7.zip) · [Contributor instructions](https://github.com/kevinsullivan0/gridcad/blob/v0.2.0-rc.7/AGENTS.md)

The desktop implementation is at the release tag. The default branch retains the earlier browser implementation; updating this README does not merge the desktop branch. Earlier releases remain available.

Original GridCAD code: [MIT License](LICENSE), copyright 2026 Kevin Sullivan. Bundled third-party runtime components retain their own licenses and notices. Private inputs and vendor software are not bundled.
