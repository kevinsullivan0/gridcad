# Reviewed-ID material-only mode

This mode reuses the exact-file operation: assign verified recipes to explicitly reviewed IDs and prove all unrelated content is preserved. It does not automatically discover geometry, read glyphs, or establish native composition semantics.

Profile: `reviewed-ids-2170-material-only-translation-compose-v1`.

## Required independent work

The assistant receives the actual files, records original hashes, inspects worksheet values/caches and project state, and independently establishes every cell/occurrence/tray-body correspondence from the actual labels/geometry. It verifies worksheet splits, corner and interior labels, omissions, symmetries and intentional prior assignments. Keep that private evidence tied to the source hash. Minimal end-user intervention means the assistant performs this work; it does not mean skipping it.

The plan must exhaustively and uniquely list cells, occurrence IDs and tray-body IDs, independent expected six-channel percentages, source-material fingerprints, target actions and preserved unrelated leaf IDs. The exact source/workbook hashes, selected sheet/range and mapping are bound by `mapping_digest(plan)` in `review.mapping_sha256`. The entire plan is also hashed in the audit. Do not set the review digest until the mapping is actually reviewed. A correctly computed digest of a wrong mapping remains wrong.

Do not include `axes` in this plan. The writer does not use stored translation ranks or pitch to prove physical correspondence. That inference is intentionally absent, not silently relaxed.

## Narrow storage-form gate

The unchanged source version, units/root/occurrence serialization and common tray linear block remain restricted as in the operator instructions. Every body must contain finite numeric compose entries with an exact identity linear block and affine bottom row. Only the observed common pure-translation form is accepted: raw translation entries at most 1 in absolute magnitude, with per-axis variation at most 1e-12 across all bodies. Those numeric bounds/tolerance are admission predicates, not inferred native units or a command to modify values. All original values are retained exactly. Missing state, compose rotation/scale, nonnumeric/nonfinite entries, different per-body offsets and unknown profiles are refused.

The compose fields are **not interpreted, composed or used as mapping evidence**. A common translation-looking field is not proof of native semantics. Absolute placement, native composition/recomposition, and physical readiness remain outside this material-only mode. Automatic lattice checking is still available only through the separate identity-compose profile; unknown/new automatic mapping needs actual geometry/composition evidence.

## Guards and output evidence

All occurrence and tray-body material references, including ancestors and preserved unrelated bodies, are counted before changing a UUID. Ancestors must have exactly passive feature state. Source materials must match their reviewed fingerprints and desired/actual objects. Conflicting prior work, heterogeneous picker state, unsupported serializer precision, incomplete mappings, duplicate IDs/cells and output collisions are refused. Native black metadata is preserved/copied in full where available.

Output audits report `mapping_mode=reviewed_exact_ids`, `placement_interpretation=not_interpreted_source_transforms_preserved`, and `physical_mapping_automatically_verified=false`. They include the mapping binding, complete preservation check, unchanged payload hashes, source version and unverified material profile. Existing native acceptance limits and `print_ready=false` remain unconditional.

The private regression demonstration runs both independently audited real mappings into isolated temporary outputs. Their full candidate archive bytes match the previously delivered candidates, including every geometry/transform field and material object. Temporary project copies are removed after comparison; private plans and complete audit sidecars are retained separately. This demonstrates reproduction of the checked operation, not arbitrary-geometry or native acceptance coverage.
