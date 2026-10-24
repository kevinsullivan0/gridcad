# Runtime provenance

This offline Windows x64 runtime contains official embedded CPython 3.13.17, openpyxl 3.1.5, et-xmlfile 2.0.0 and defusedxml 0.7.1. No vendor GrabCAD or Wine runtime is included.

Exact official source URLs, download sizes and SHA-256 values are in artifacts.json. Saved official source metadata is in provenance/. Download hashes were checked before extraction; Authenticode/Sigstore signatures were not independently verified. runtime/bundle-sha256.json records assembled runtime contents. Only Python's python313._pth configuration was changed: it restricts imports to the bundled standard library, extensions, dependencies and application root, without import site.

Keep all runtime licenses, including runtime/LICENSE.txt, openpyxl LICENCE.rst, et-xmlfile LICENSE/AUTHORS and defusedxml LICENSE notices under their dist-info directories.

Extract the whole bundle and use launch-windows.cmd. No install, pip, PATH, administrator rights or first-run download is required. Windows execution is unverified; the included dependency smoke test was run using Linux Python, not this Windows executable. Never bypass a security warning. See the root README and acceptance report.
