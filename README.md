# GridCAD desktop 0.2 candidate

GridCAD is a deterministic Windows desktop converter for the documented rectangular labeled-grid / CMYKWT workflow. It uses native `ttk` controls, reads Excel recipe rectangles, previews embedded geometry and exact cell/body assignments, and writes a separate candidate with a complete preservation audit. No LLM, account, browser, vendor runtime or network service is used.

Download the Windows portable ZIP from [Releases](https://github.com/kevinsullivan0/gridcad/releases), extract the entire folder, and open **GridCAD.exe**. Keep `_internal` and `advanced` beside it. Python and dependencies are bundled; nothing is installed or downloaded at first launch. This candidate is unsigned.

Start with **Load example**, then **Build mapping preview**. The synthetic examples are newly invented archive contracts and **must not be printed**. For a supported actual project: open the workbook and project, select sheet/range and sample/label groups, explicitly choose orientation/transpose, inspect the actual printed-label geometry and exact recipes, record the review, and save a **new result folder**. Originals and previous outputs are preserved.

- [Short usable manual](docs/DESKTOP_MANUAL.md)
- [Supported source profile, schema and adaptable examples](docs/RECTANGULAR_SCHEMA.md)
- [Portable API and agent CLI](docs/DESKTOP_API.md)
- [Contributor/external-agent instructions](AGENTS.md)
- [Synthetic example files and preview](examples/rectangular/)
- [Reviewed exact-ID operator](operator/README.md)

The **Advanced / Agent & help** tab has documentation and a copyable prompt. The Windows package includes `advanced/GridCAD-core.exe`; the separate portable core source bundle runs with Python 3.10+ and the standard library. Other geometries need an explicit new adapter and evidence; triangular, hexagonal and arbitrary 3D automatic conversion are not implemented.

The new mesh-derived rectangular mapping was independently compared against two previously reviewed actual-file mappings. Both complete generated candidates reproduced the earlier deliveries byte for byte, with 1,404 and 693 material changes respectively and every non-project payload preserved. Those private inputs and mappings are excluded from the public repository/release. Twelve new synthetic core tests supplement the existing 61 operator tests. Hosted Windows package/GUI acceptance results are published separately with the release; a green component suite alone is not full usability evidence.

**Native GrabCAD open/recompose/save and physical print acceptance remain unverified.** The bounded source uses older 2170 serialization with a newer observed material serializer. Geometry display conventions and a source-bound digest do not establish native compose semantics or independently recognize glyph text. User physical-label review remains required. Every candidate audit retains `print_ready=false`; inspect exact channels, direct-black labels, geometry and process settings in native GrabCAD before printing. GridCAD never submits printer jobs.

The previous browser-based alpha source and releases remain available for history. The desktop package starts with `GridCAD.exe`; its launch route is different from the archived browser launcher. Preserve third-party notices. The repository adds no general project license grant and bundles no proprietary vendor software or private customer files.

Build and test the Windows distribution with `.github/workflows/windows-desktop.yml`. Core checks:

```sh
python -m unittest discover -s operator/tests -v
python -m unittest discover -s tests -p test_desktop_core.py -v
```
