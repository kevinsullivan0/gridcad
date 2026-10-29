# GridCAD

**Turn Excel recipes into material assignments in a GrabCAD PRINT project.** Open your workbook and project, match the cells to the samples, inspect the preview, and save a new `.PRINT` file with a name you choose. Your originals stay unchanged. No account or AI assistant is required.

## Download and start

**[Download GridCAD 1.0.1 for Windows](https://github.com/kevinsullivan0/gridcad/releases/download/v1.0.1/GridCAD-Windows-x64-v1.0.1.zip)** · [Release and checksums](https://github.com/kevinsullivan0/gridcad/releases/tag/v1.0.1)

1. Download the ZIP and choose **Extract All…** in File Explorer.
2. Open the extracted **GridCAD** folder and double-click **Start GridCAD.bat**.
3. Follow the short setup prompts. GridCAD copies the included app into your account and offers a Desktop shortcut. No administrator rights are needed.
4. Use the shortcut next time. Once setup finishes, you may delete the downloaded ZIP and extracted folder; the installed copy stays in place.

This **one download includes both launch methods**. GridCAD first checks that its included Windows app actually opens. If Windows cannot start it, the launcher offers the same interface through verified Python; it asks before downloading any required Python or image-library components. Once either method is set up, it works offline. Keep the progress window open while using the app.

The EXE is unsigned. GridCAD does not disable Windows protections or bypass an organization's policy. [Setup, recovery, updates and removal](https://github.com/kevinsullivan0/gridcad/blob/v1.0.1/docs/SOURCE_LAUNCHER.md).

## Convert a project

- Open your Excel `.xlsx` workbook and select the recipe cells.
- Open the `.PRINT` project. Choose the sample and label groups, then match the worksheet directions to the preview.
- Choose **Match cells to samples**. Click a sample to inspect its current material and requested recipe.
- Choose **Save PRINT as…** and name the new file. A conversion report is optional; normal saves create only the PRINT file.
- Open the result in GrabCAD and check its geometry, labels, recipes and printer settings before printing. GridCAD checks the file conversion, but does not certify native GrabCAD acceptance or submit print jobs.

**Load example** lets you try the interface without your files. These are synthetic demonstration files, not a production print job.

## What it supports

- Windows x64. The included EXE has its own runtime; the alternate source method uses verified official Python 3.13 with Tk.
- Rectangular grids with distinguishable samples, including mixed shapes and heights. Irregular, triangular, hexagonal and stacked 3D layouts need other adapters.
- Six-channel C/M/Y/K/W/T worksheet recipes totaling exactly 100%. Formula cells need current results saved by Excel.
- The reviewed GrabCAD Print 1.117.12.3985 storage profile, schema 2170, with validated geometry, identities and materials. A matching version header alone is not sufficient.
- Supported EcoFlex sample recipes and complete compatible label-material assignments already present in the project.

Unsupported inputs are explained rather than silently changed. Large previews may omit display detail; the saved geometry is not simplified. [User guide](https://github.com/kevinsullivan0/gridcad/blob/v1.0.1/docs/DESKTOP_MANUAL.md) · [Supported files and limits](https://github.com/kevinsullivan0/gridcad/blob/v1.0.1/docs/RECTANGULAR_SCHEMA.md).

## Help, updates and verification

The app's **Help** tab includes the offline guide, version, licenses, and links to this repository and releases. Updates are manual. Errors explain what happened and what to try next; optional local diagnostic reports can help a developer or your agent investigate. Nothing is uploaded automatically.

Compare a download's SHA256 with its exact filename in [SHA256SUMS.txt](https://github.com/kevinsullivan0/gridcad/releases/download/v1.0.1/SHA256SUMS.txt). A matching checksum confirms download consistency, not publisher identity or safety. If you prefer your agent to download and verify it, point it to [the installation guide for agents](https://github.com/kevinsullivan0/gridcad/blob/v1.0.1/docs/AGENT_INSTALL.md).

## Advanced toolkit

The release includes the deterministic Python core, command-line tools, examples, schema and agent instructions. The ordinary GUI needs no agent. An agent can use the toolkit for more specialized work, but new geometries or material profiles require their own validation rather than assuming the GUI already supports them. [Developer guide](https://github.com/kevinsullivan0/gridcad/blob/v1.0.1/docs/DESKTOP_API.md) · [Contributor contract](https://github.com/kevinsullivan0/gridcad/blob/v1.0.1/AGENTS.md) · [Exact release source](https://github.com/kevinsullivan0/gridcad/tree/v1.0.1).

The desktop implementation is at the release tag linked above. The default branch retains the earlier browser implementation; this README update does not merge the desktop branch. Earlier releases remain available.

GridCAD's original code is MIT licensed, copyright 2026 Kevin Sullivan. Dependencies retain their own licenses. Private inputs and vendor software are not bundled.
