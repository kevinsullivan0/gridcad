# Working on GridCAD

The current product is the native desktop app and its deterministic portable toolkit. `main` is the maintained source; release tags identify the exact source of published downloads.

## Source map

- `gridcad_desktop.py`: Tk desktop interface.
- `desktop_core.py`: rectangular-grid conversion and named output API.
- `desktop_cli.py`: optional command line and operator access.
- `operator/gridcad_operator/`: reviewed file/material writer used by both.
- `agent_help.py`, `diagnostics.py`: optional local agent help and error reports.
- `Start GridCAD.bat`, `tools/windows_launcher.ps1`, `tools/source_launcher.py`: one-download setup and source fallback.
- `tests/`, `operator/tests/`: maintained regression suites; `tools/windows_*_acceptance.py`: real Windows package journeys.
- `resources/`, `examples/`, `docs/`: app assets, synthetic examples and guides. `qa/performance/` contains dated measurements, not current pass claims.

Do not commit customer files, local diagnostics, build output or installed dependencies. Read [the contributor contract](../AGENTS.md) before changing conversion behavior.

## Tests

Use an isolated Python environment. With Python available as `python`, these commands work from the repository root in PowerShell or a POSIX shell:

```text
python -m pip install -r requirements-test.txt Pillow==13.0.0
python -m unittest discover -s tests -v
python -m unittest discover -s operator/tests -v
```

The portable CLI itself uses the standard library; those additional packages are test/GUI dependencies. On macOS/Linux, use `python3` if that is the interpreter's command. Native package/UI acceptance runs in the Windows workflow on pushes to `main` and pull requests into it. The exact-built-artifact contract is skipped locally unless its distribution ZIP is supplied; a local pass is not a Windows/GrabCAD acceptance claim.

Changes should use short-lived branches and a pull request into `main`, not a permanent competing app branch. Keep releases immutable. The completed version-specific publication workflow has been retired. `tools/publish_approved_release.py` and `.github/release-approved.json` retain the historical hash-bound 1.0.1 recipe for inspection; the script refuses an existing tag. They are not a generic automatic publisher. A new release requires a new explicit version/approval record and exact passing artifact.

## Retired browser prototype

The earlier local HTTP/browser interface, its separate `gridcad/` implementation, embedded-runtime bootstrap, alpha review documents, synthetic fixtures and browser-only tests were retired from the maintained checkout after 1.0.1. They are still available, byte-for-byte, at [tag v1.0.1](https://github.com/kevinsullivan0/gridcad/tree/v1.0.1) and in Git history. For example, the prior suite and its limitations are recorded in [REGRESSION_PROVENANCE.md at that tag](https://github.com/kevinsullivan0/gridcad/blob/v1.0.1/tests/REGRESSION_PROVENANCE.md).

Retiring that implementation also retires its tests from the current discovery count; it does not turn them into desktop coverage or recover the earlier missing original test suite. Current desktop/operator regressions are retained unchanged. Historical performance and operator provenance records describe their dated experiments and are not silently relabeled as current evidence.

Published 1.0.1 downloads, checksums, tags and evidence assets are unchanged by this repository cleanup. The current app, core and launchers retain the same runtime behavior.
