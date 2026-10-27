# Rectangular schema and supported profile

Desktop profile: `rectangular-2170-mesh-review-v1`. Material writer: `gridcad.ecoflex.5.119.0.v1`. This is a bounded candidate-producing converter, not a universal CAD importer.

| Input | Contract |
| --- | --- |
| Workbook | `.xlsx`, exact selected sheet and dense A1 rectangle, at most 100,000 cells; six explicit plain decimal percentages separated by `/`, order C/M/Y/K/W/T, each 0–100, exact total 100. No normalization. Serializer precision limits also apply. |
| Formulas | Stored values only, with explicit current-cache confirmation after Excel recalculation/save. Missing/error caches fail. Macros/external links refused. |
| Source | Exact observed GrabCAD Print 1.117.12.3985 / five provider schemas 2170, one tray, one body per leaf, passive empty feature state. All existing operator version, unit, scale, orientation, ancestor, material-reference and storage-form checks remain in force. |
| Placement | CM metadata, observed `.001` occurrence scaling, `.1` root scaling and quarter-turn tray linear block. Compose must have the observed common bounded pure-translation storage form. It is preserved, not interpreted or multiplied into the display. Rotation/shear/scale/differential compose offsets are refused. |
| Geometry | Embedded binary STL only; every body needs an unambiguous archive member. No external paths are followed. 32 MiB / 600,000 triangles per STL; eight million triangles total across all body instances (shared meshes count once per body), with the unique-mesh limit also retained; at most 10,000 bodies. No source geometry is rewritten. |
| Sample selection | Explicit exact leaf-name group, any supported nonflat binary-STL sample shape, one complete XY rectangular lattice on a shared bottom plane. Uniform spacing checked at fixed 0.0001 mm tolerance; no holes, duplicate positions, tilted grids or automatic tolerance inflation. Separately stored occurrence position differences must corroborate the quarter-turn relation. |
| Labels | One explicitly chosen container with all its descendant leaves; sample/label overlap refused. Default black mode preserves matching direct black or uses a complete native black template, otherwise the explicitly unverified serialized black profile. Reference mode copies a selected compatible existing PolyJet EcoFlex direct material or validated CMYKWT mixer, retaining target identities. Existing different label assignments require explicit replacement review; inconsistent or shared mutable identities remain refused. |
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

## Shape-agnostic rectangular layouts

Pyramids, boxes and mixed sample shapes/sizes/heights are exercised by generated tests. The layout remains rectangular: footprints must be separated and lie on a common base plane. Mapping uses uniformly spaced footprint centres, or a bounded placement-anchor fallback only when each footprint contains its corroborated anchor and fits strictly inside that anchor's grid cell. Holes, duplicate positions, touching/overlapping footprints, raised samples and unsupported transforms are refused. The preview draws sample bounding footprints, not a shaded 3D model; actual label glyph surfaces remain visible. Source meshes are never replaced.

Generate examples with `--shape pyramid` or `--shape mixed`, optionally `--height 7`. The package includes `examples/pyramid` and `examples/mixed` alongside the original box example. These remain synthetic, non-native print demonstrations.

## Input resource ceilings

The desktop app and portable operator refuse oversized inputs before unbounded preview/workbook allocation. They never truncate a file to fit. Workbook ceilings are **64 MiB expanded ZIP content**, **16 MiB per parsed XML part**, **128 sheets**, **100,000 stored cells across the sheets read**, and **100,000 shared strings**. XML parsing also has an aggregate **1,000,000-element / 128-level** ceiling and **16,777,216 characters** of XML text/attribute content and expanded element/attribute names; resulting cell values have a separate aggregate limit of the same size, including repeated shared-string values. To prevent namespace expansion from bypassing these budgets, XML also allows at most **128 attributes per element** and **1,024 characters per name or namespace URI**, checked before namespace expansion. Selected-sheet operator reads still validate sheet identities and reject aliased targets. DTD/entity declarations are refused regardless of supported XML encoding. Sparse coordinates do not allocate empty cells.

Project preview counts shared geometry for **every body instance**, not just each unique STL. The eight-million-triangle instance budget bounds transformed preview storage; existing per-STL, unique-mesh, body-count and source-profile guards also remain. No source geometry is changed.

If a limit is exceeded, export a smaller project or a values-only workbook with just the needed sheets from your original application. Keep the original. There is no ordinary-app override: genuinely larger use needs a separately measured and reviewed capacity change, not a bypass switch.
