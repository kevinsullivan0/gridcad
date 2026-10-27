# Windows runtime packaging

`python tools/build_windows.py` uses the checked-in `tools/GridCAD.spec` with
our pinned PyInstaller version. Build on Windows; a Linux syntax/static check
is not Windows executable acceptance.

The frozen package has two entry points at its root:

- `GridCAD.exe`: windowed desktop launcher (no terminal window).
- `GridCAD-core.exe`: console CLI, including stdout/stderr and exit status.
- `_internal/`: one shared Python runtime, standard-library archive, extension
  modules, Tcl/Tk, Pillow/PNG support, and bundled resources.

Keep the entire extracted folder together. The CLI is no longer under
`advanced/`; scripts referring to that previous path must use the root-level
`GridCAD-core.exe`. Neither launcher requires installed Python, downloads a
runtime, or starts the other launcher. Sharing files does not mean sharing a
Python process: they can run independently or simultaneously.

The spec uses separate `Analysis`, `PYZ`, and `EXE` objects, followed by one
`COLLECT` containing both analyses' binary and data tables. This is the
[PyInstaller-supported multi-application onedir layout](https://pyinstaller.org/en/stable/spec-files.html#multipackage-bundles).
PyInstaller collects/deduplicates shared dependencies; we do not delete Python
DLLs or rewrite bootloader paths after building. Each executable keeps its own
small Python module archive. Shared destination bytes are fingerprinted immediately
after each analysis, before a later analysis can overwrite a generated work file.
Any differing duplicate stops the build rather than silently selecting one copy.
GUI resources, PNG preview support, source/agent
files, help documents, and third-party notices remain packaged. The portable
source core remains a separate stdlib-only deliverable requiring Python 3.10+.

## Acceptance gate

Run the hosted Windows workflow and `tools/windows_gui_acceptance.py` against
the extracted final ZIP, not a source checkout. Require one Python runtime
under `_internal`, no old `advanced` runtime, and console CLI success before,
during, and after the GUI session. Use paths containing spaces and an unrelated
working directory, with installed Python removed from the launch environment.
Check real dialogs, PNG previews, saving, local help, license display, and
optional agent tools as well as executable exit codes. Runtime sharing alone
does not establish a releasable candidate; RC4 remains held until all required
release gates have passed.
