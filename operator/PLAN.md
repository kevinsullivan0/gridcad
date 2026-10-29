# Explicit private plan

`examples/make_synthetic_case.py` generates a complete working example plan for invented data. Generate it outside this source directory and inspect it before adapting the schema. Do not reuse its invented hashes/IDs or claimed label review for real files.

Required top-level keys:

| Key | Meaning |
|---|---|
| `plan_version` | Integer `1`. Unknown keys/versions are refused. |
| `archive_sha256`, `workbook_sha256` | Exact original bytes bound to this review. |
| `source_version` | Complete exact version object returned by inspection. The CLI also checks its narrow supported constant. |
| `placement_profile` | Either `conservative-2170-cm-quarterturn-identity-compose-v2` for the restricted lattice path, or `reviewed-ids-2170-material-only-translation-compose-v1` for externally reviewed exact IDs with uninterpreted preserved compose storage. Neither establishes universal native compatibility. |
| `material_profile` | `gridcad.ecoflex.5.119.0.v1`. This newer serializer is explicitly unverified against the older source version. |
| `allow_unverified_material_profile` | Boolean `true`, only after recording that limitation. |
| `review` | `geometry_and_labels_confirmed: true` and nonempty `evidence` describing actual independent glyph/geometry review and expected values. Reviewed-ID mode additionally requires `mapping_sha256` as defined below. Neither a flag nor a hash substitutes for doing the review. |
| `sheet`, `range` | Exact tab name and dense A1 rectangle, e.g. `Recipes`, `D4:E5`. |
| `formula_cache_policy` | `reject` or `confirmed_current_cache`; missing caches always fail. |
| `axes` | Required only in identity-compose lattice mode; **must be absent** in reviewed-ID material-only mode. Distinct `row_axis`/`column_axis` as `x` or `y`; integer directions `1` or `-1`; decimal-string `pitch_mm` and `cluster_tolerance_mm`. Tolerance is 0.000001..0.02 mm and less than one percent of pitch. Never use it to merge distinct bodies or conceal mapping discrepancies. |
| `expected_counts` | Integer `samples` equals rectangle area; `labels` equals label list length. |
| `samples`, `labels` | Explicit target records below. |
| `preserve_occurrence_ids` | Every other leaf, listed explicitly. Containers and all unrelated metadata remain untouched. |

Each sample record has exactly `cell`, `occurrence_id`, `tray_body_id`, `source_material_sha256`, `expected_percentages` (six independent C/M/Y/K/W/T decimal values), and `action`:

- `replace_uniform_color_picker`: only matching desired/actual picker state, fingerprint-bound and uniform across all replaced samples. The reviewed plan authorizes these targets; existing colors are not inferred to be uncompleted. Heterogeneous colors and existing mixer conflicts are refused.
- `preserve_exact_mixer`: complete object preserved only when its explicit recipe, native names, positive resin IDs, mode and appearance agree. This does not certify arbitrary optional native metadata.

Each label record has `occurrence_id`, `tray_body_id`, `source_material_sha256`, and `action`:

- `preserve_native_black`: retain the complete label occurrence/body/material/appearance unchanged, including shared UUIDs and every inherited optional field.
- `assign_from_picker_using_native_black`: additionally requires `reference_occurrence_id` of an existing matching native direct-black source leaf. Copy the full material; retain the target's unique UUID.
- `assign_from_picker_using_unverified_black`: explicitly constructs the minimal newer-profile black material only when no native black source template exists. It remains unverified. Do not use this to bypass a known available native reference in another project.

All prior material fingerprints include the complete source material object, including its ID, in exact JSON key order as returned by `inspect`. Original file hashes bind the entire project as well. Every occurrence (including ancestors) and every tray-body material reference is counted. Changing any shared material UUID is refused; there is no conflict-overwrite escape switch. A failed guard means inspect the evidence and resolve the actual ambiguity, not delete IDs, change units/version fields, or weaken the guard until it passes.

## Reviewed-ID binding and responsibility

The reviewed-ID material-only path does not use stored translation ranks to establish physical correspondence. Before selecting it, the assistant must independently inspect actual source geometry/printed labels and establish an exhaustive cell-to-occurrence-to-body mapping. Check actual corner and interior labels, number of cells/bodies, worksheet split and any symmetry; use native evidence when needed. Keep that evidence privately with its source hash. Do not relabel an unverified automatic guess as independently reviewed just because the automatic route refused it.

`gridcad_operator.operator.mapping_digest(plan)` defines the canonical binding: exact archive/workbook hashes, sheet/range, sorted explicit sample cells/IDs/expected channels, sorted label IDs and preserved leaf IDs. After review, record its result in `review.mapping_sha256`. The CLI recomputes it and rejects a stale or missing digest. Actions and complete source-material fingerprints are separately enforced and the entire plan is hashed in the audit. A user-authored wrong mapping can still have a valid digest: this mode is a preservation/material writer for verified mappings, not a text-recognition or native-placement proof.

All target uniqueness, dense cardinality, source-material, serializer-domain, ancestor-feature and complete material-reference guards remain mandatory in this mode. The source version and observed raw transform/storage profile remain restricted. The compose fields are copied untouched, not applied, normalized or used as evidence that physical positions are correct. Unknown automatic mapping or new composition semantics still requires actual geometry/native evidence.

## Explicit reference-material label policy

The desktop/CLI may now produce two additional label actions:

- `preserve_reference_material`: keep the complete target unchanged because its entire material definition, apart from its target-specific ID, already equals the reference.
- `copy_native_reference`: copy the complete compatible source assignment while retaining the target's unique ID. Replacing an intentional non-picker assignment requires explicit `replacement_confirmed: true` after reviewing that target; this is not a general conflict bypass.

Both require `reference_occurrence_id`, `reference_material_sha256`, and a boolean `replacement_confirmed`. Only consistent saved PolyJet EcoFlex direct materials or known valid six-channel mixers are admitted. The reference must not be changed by the same plan. Dangling references, malformed or incompatible definitions, conflicting aliases, changed fingerprints and shared mutable target IDs remain refused.

For plans using either new action, `mapping_digest` additionally binds every label's action, complete source fingerprint, reference ID/fingerprint and replacement-confirmation choice. Old black-only plan digest semantics remain unchanged. The full reference definition is verified again on archive readback; manifests retain reference identity/fingerprint and the recorded replacement decision. All native-acceptance limitations still apply.
