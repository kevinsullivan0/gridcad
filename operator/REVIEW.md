> Historical snapshot of the earlier operator review; licensing and desktop release status below are not current. See the root README and LICENSE for the current release.

# Review status

Prepared source review package; **not published**. No new production conversion was performed during cleanup. The exact original conversion scripts and evidence are retained separately in the private workspace.

Validation:

- 61 standard-library synthetic tests pass: exact readback/payload preservation; unrelated nonempty identity-map preservation; source/workbook hash binding; source version, units, root scaling, orientation and affine layout checks; ancestor and preserved-body material aliases; ancestor active/missing feature state; all nonidentity compose transforms; serializer precision-domain refusal in preflight; rectangle cardinality, duplicate targets, axis direction and pitch; incomplete preservation declarations; missing/stored formula cache policy; exact percentages; heterogeneous picker work and conflicting mixer refusals; complete existing mixer/native black preservation; copying inherited native black metadata; shared material identity protection; existing output directories/symlinks and publication-race no-overwrite behavior.
- Revision 2 retains its strict identity-only lattice path. Revision 3 adds one explicit externally reviewed-ID material-only path for the observed finite pure-translation storage form. Both private audited source-bound mappings passed and were replayed only into isolated temporary outputs. Complete payload/nonmaterial audits passed; both whole candidate archives were byte-identical to the delivered candidates. Temporary project copies were removed after comparison. Private source files, plans, offsets and results are excluded. A separate source audit found no ancestor material aliases and exactly empty ancestor feature state in those actual inputs.
- The unchanged material converter and extracted numeric validator are traceable to the public commit in `PROVENANCE.md`.
- Only whitelisted source, instructions and synthetic tests enter the review ZIP. Its per-file manifest records byte counts and hashes; no generated `.PRINT`/XLSX, real labels, personal paths, private UUIDs, manifests or renders are included.

Limits and self-review:

- Plan review and independent expected percentages remain substantive operator work. A `geometry_and_labels_confirmed` boolean does not prove that work happened. This CLI cannot recognize text, resolve symmetric orientation without evidence, invent missing caches, create omitted geometry, or infer which prior assignments are intentional.
- Unknown versions/transforms fail rather than receiving a broad compatibility bypass. Reviewed-ID mode accepts a narrow raw storage form but never interprets compose semantics or certifies physical mapping; the independently reviewed mapping remains the operator's responsibility. The strict profile intentionally excludes other legitimate GrabCAD layouts. Two observed source cases do not prove a general native profile.
- Material serialization is a newer observed profile. No native Windows open/recompose/save tests occurred in this cleanup. The candidate warning and `print_ready=false` remain unconditional.
- Full native black metadata should be preserved or copied from an available reviewed reference. Missing optional native flags in a minimal object are a discrepancy with unknown native effect, not proof of failure or equivalence. Black evidence does not establish mixer compatibility.
- Tests ran on the existing Mac Python runtime. The CLI uses no installation or network APIs. Native Windows GrabCAD and other operating systems/filesystems were not acceptance-tested.
- No GitHub remote, commit, push, release, deployment or public upload was created. Review publication scope and licensing before publishing elsewhere.
