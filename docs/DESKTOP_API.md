# Portable core and external-agent access

The deterministic core needs Python 3.10+ and the standard library. No LLM, service, network or vendor runtime is called. The GUI additionally uses Tk and Pillow. On Windows the release includes `advanced/GridCAD-core.exe`, which bundles Python; replace `python desktop_cli.py` below with that executable path.

```sh
python desktop_cli.py inspect --project original.PRINT --workbook recipes.xlsx
python desktop_cli.py propose --project original.PRINT --workbook recipes.xlsx --sheet Recipes --range D4:I7 --samples Sample --labels "Printed labels" --orientation "Rows down; columns right"
```

`propose` prints a private JSON proposal and never writes a project. Add `--transpose` only when appropriate. `--confirm-current-formula-caches` explicitly admits saved formula values; it never calculates missing results. Inspect the actual geometry/labels independently before conversion. Reports can contain private source identities and must not be committed or uploaded publicly.

```sh
python desktop_cli.py convert --project original.PRINT --workbook recipes.xlsx --sheet Recipes --range D4:I7 --samples Sample --labels "Printed labels" --orientation "Rows down; columns right" --confirm-mapping --allow-unverified-material-profile --review-notes "Four corners and representative physical interior labels checked against requested recipes" --out-dir NEW-result
```

Required confirmations record actual review responsibility; fabricated notes are not verification. Output directories must not exist. This command recomputes the bounded proposal from actual inputs and uses the preserved operator writer. Native GrabCAD acceptance remains separate and unverified.

The original exact-ID operator is also exposed:

```sh
python desktop_cli.py operator inspect --project original.PRINT --workbook recipes.xlsx
python desktop_cli.py operator check-plan --project original.PRINT --workbook recipes.xlsx --plan private-reviewed-plan.json
python desktop_cli.py operator apply --project original.PRINT --workbook recipes.xlsx --plan private-reviewed-plan.json --out-dir NEW-result
```

Read `operator/PLAN.md` and `operator/REVIEWED_ID_MODE.md` before using externally reviewed IDs. That route does not create a mapping or waive native proof.

## Python API

```python
import desktop_core as core
project = core.load_project("original.PRINT")
book = core.read_workbook("recipes.xlsx")
# Inspect project['groups'] and project['containers']; choose explicitly.
proposal = core.propose(project, "recipes.xlsx", book, "Recipes", "D4:I7",
                        "Sample", "exact-label-container-id",
                        "Rows down; columns right", transpose=False)
# Review proposal['mapping'] against actual physical labels before this call.
audit = core.save("original.PRINT", "recipes.xlsx", proposal, "NEW-result",
                  "Actual corner/interior label review evidence")
assert audit["nonmaterial_preservation_passed"]
assert not audit["print_ready"]
```

Use `core.op.ValidationError` and a nonzero CLI exit to handle refusal. No overwrite/conflict-bypass API is provided. Preserve hashes and the complete private output audit. `load_project` supplies bounded binary-STL top-surface arrays for relative XY visualization; it does not recognize glyph text or implement native compose semantics.

For another geometry, supply a separate mapper with explicit source and numeric contracts, independently reviewed mapping evidence, preservation and round-trip tests, and native acceptance evidence when claiming native compatibility. Triangular, hexagonal, arbitrary rotation/scale and 3D automatic conversion are currently unsupported.

## Copy a saved material onto labels

The optional reference mode copies a complete compatible **existing assignment**; it does not synthesize arbitrary new materials or run GrabCAD. Use `inspect` to identify a reference leaf ID, then add:

```sh
--label-mode reference --label-reference EXACT-LEAF-ID
```

`propose` reports `label_material`: the reference's friendly name/material, `conflicts` (all target IDs, names and current materials), `conflict_count`, and `replacement_confirmed`. Review the complete list. If intentional label assignments would change, `convert` additionally requires `--confirm-label-replacement`; the ordinary physical-mapping review and unverified-profile acknowledgement remain required. A color-picker target can be replaced without that extra conflict confirmation. Already identical complete assignments are preserved.

Python callers pass `label_mode='reference'`, `label_reference=leaf_id`, and, only after reviewing conflicts, `confirm_label_replacement=True` to `core.propose`. `core.reference_material_info(project, leaf_id)` returns a validated, read-only description. The default remains `label_mode='black'`.

The reference must be a consistent saved PolyJet EcoFlex direct material (C/M/Y/K/W/T) or valid six-channel mixer in the supported profile. Unknown families, malformed definitions, desired/actual disagreements and conflicting material-ID aliases fail closed. Its complete material object is copied, retaining each target's existing unique ID and updating occurrence/tray/appearance consistently. The reference must remain unchanged. Shared mutable target IDs remain refused even with replacement confirmation; resolve that native ambiguity instead of deleting IDs or bypassing the guard. Source hashes, reference fingerprints, policy choices and replacement confirmation bind the reviewed plan. Native application and printer acceptance remain unverified.
