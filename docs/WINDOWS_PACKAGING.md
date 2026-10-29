# Windows runtime packaging

`python tools/build_windows.py` uses the checked-in `tools/GridCAD.spec` with
our pinned PyInstaller version. Build on Windows; a Linux syntax/static check
is not Windows executable acceptance.

The frozen package has two entry points at its root:

- `GridCAD.exe`: windowed desktop launcher (no terminal window).
- `GridCAD-core.exe`: console CLI, including stdout/stderr and exit status.
- `_internal/`: one shared Python runtime, standard-library archive, extension
  modules, Tcl/Tk, Pillow/PNG support, and bundled resources.

The normal starting point is `Start GridCAD.bat`: it verifies and copies the complete app into a versioned per-user location, then offers a Desktop shortcut. See `docs/SOURCE_LAUNCHER.md` for setup, source fallback, upgrades and removal. Both EXEs include Explorer version metadata; this is not a publisher signature. For direct portable EXE or CLI use, keep the entire extracted folder together. The CLI is no longer under
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
For `base_library.zip`, equality means the exact same member names and uncompressed
member bytes; ZIP order and container metadata do not affect Python imports.
Duplicate ZIP members or changed/missing contents stop the build with member names.
All other shared files must be byte-identical. Differing duplicates stop the build
rather than silently selecting one copy.
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
does not establish a releasable candidate; all required application and distribution
journey gates must pass for the exact release artifact.

The combined distribution gate runs `tools/windows_distribution_acceptance.py` against the final Windows ZIP. It exercises per-user installation, consent/cancellation, duplicate launch refusal, Desktop shortcut after deleting the download, version preservation and source recovery. GUI screenshots/process records and launcher logs are attached as release evidence. Hosted tests are not Smart App Control, native GrabCAD or physical printer acceptance.
