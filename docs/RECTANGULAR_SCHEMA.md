# Rectangular schema and supported profile

Desktop profile: `rectangular-2170-mesh-review-v1`. Material writer: `gridcad.ecoflex.5.119.0.v1`. This is a bounded candidate-producing converter, not a universal CAD importer.

| Input | Contract |
| --- | --- |
| Workbook | `.xlsx`, exact selected sheet and dense A1 rectangle, at most 100,000 cells; six explicit plain decimal percentages separated by `/`, order C/M/Y/K/W/T, each 0–100, exact total 100. No normalization. Serializer precision limits also apply. |
| Formulas | Stored values only, with explicit current-cache confirmation after Excel recalculation/save. Missing/error caches fail. Macros/external links refused. |
| Source | Exact observed GrabCAD Print 1.117.12.3985 / five provider schemas 2170, one tray, one body per leaf, passive empty feature state. All existing operator version, unit, scale, orientation, ancestor, material-reference and storage-form checks remain in force. |
| Placement | CM metadata, observed `.001` occurrence scaling, `.1` root scaling and quarter-turn tray linear block. Compose must have the observed common bounded pure-translation storage form. It is preserved, not interpreted or multiplied into the display. Rotation/shear/scale/differential compose offsets are refused. |
| Geometry | Embedded binary STL only; every body needs an unambiguous archive member. No external paths are followed. 32 MiB / 600,000 triangles per STL; eight million unique triangles total; at most 10,000 bodies. No source geometry is rewritten. |
| Sample selection | Explicit exact leaf-name group, identical mesh payloads, one complete planar XY rectangular lattice. Uniform spacing checked at fixed 0.0001 mm tolerance; no holes, duplicate positions, tilted grids or automatic tolerance inflation. Separately stored occurrence position differences must corroborate the quarter-turn relation. |
| Labels | One explicitly chosen container with all its descendant leaves; sample/label overlap refused. Existing consistent direct black is preserved in full. Gray labels use a complete available native black template, otherwise the explicitly unverified minimal serialized black profile. |
| Mapping | Explicit eight-way XY direction choice, optional transpose, actual mesh-derived relative centers and an exhaustive cell/body assignment. User must inspect visible glyph geometry and confirm corners/interior labels. No OCR, automatic text interpretation, absolute native compose semantics or automatic physical proof is claimed. |
| Existing materials | Uniform picker sample replacements only; existing exact mixers preserved; conflicting mixers, heterogeneous picker samples, shared mutable identities, desired/actual disagreements and unsafe prior work refused. Unselected leaves and ancestor state remain unchanged. |
| Output | New directory only, candidate and source-bound audit/plan/assignments. Every non-project payload hashes identically; all nonmaterial JSON, existing identities and untouched material objects are preserved. Saved archive/recipes are independently read back. `print_ready=false` and native acceptance false are unconditional. |

The existing reviewed-ID writer receives an explicit user-confirmed mapping. Its `expected_percentages` field binds the worksheet-derived request and is **not** an independent OCR/transcription result in this UI. The plan evidence states that distinction. `mapping_sha256` binds a mapping to inputs; it cannot prove the mapping is physically correct. The display convention is regression-tested against two independently reviewed actual cases; that evidence does not establish arbitrary transform or native composition behavior.

## Synthetic examples and adaptable dimensions

`examples/rectangular/` contains a newly generated `.PRINT` archive contract, `.xlsx` template, guide and preview illustration. No customer files, private mappings, vendor runtime, font or material database are used. These are not native-generated or natively verified printable projects. The build also includes `import-geometry/`: individual, newly generated binary STL bodies in shared millimetre coordinates, a manifest and import guide. Those are ordinary geometry templates, not proof that a newly imported native project matches this converter profile.

To generate another invented example using the portable source:

```sh
python tools/make_desktop_examples.py /new/example --rows 3 --columns 9 --pitch 18 --size 11
```

Rows/columns are 2–100, dimensions are millimetres, and `0 < size < pitch <= 100`. The generated sample name is `Sample`; the label container is `Printed labels`; the recipe block starts at `D4`. Physical index labels start at 1. Use Rows down; columns right, without transpose. Changing these examples does not create a vendor-authenticated printable project.

The recipe schema is independent of rectangular counts and sample dimensions, but project compatibility remains bounded by the above source profile. Additional geometries require a new independently tested mapping adapter, never a `force` switch.
