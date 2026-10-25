# Provenance and publication boundary

This package is prepared for source review only; it has not been pushed or published.

`gridcad_operator/material_converter.py` is an unchanged copy of the independently authored converter in the public repository [kevinsullivan0/gridcad](https://github.com/kevinsullivan0/gridcad), tag `v0.1.0-alpha.3`, commit `0c56790409ed066ac2448f273c9349846d1ece97`. The `validate_recipe` function in `core.py` is extracted unchanged from that commit. The exact-number JSON writer follows the same reviewed Decimal serialization contract. No vendor code, material database, Windows runtime or external native oracle fixtures are bundled.

The converter's profile explicitly concerns observed newer serialized materials. It does not authenticate vendor origin or establish older-version native acceptance. The operator adds a separate narrow source placement profile; that separation must remain visible in any future reuse or documentation.

The package contains code, instructions, synthetic generators and tests only. Actual input/output archives, workbooks, personal names/paths, identity-bearing plans, manifests, raw geometry, renders, transfer records, and native material comparison evidence are intentionally excluded. Keep them in the private task workspace. Do not add them to a commit, release asset or public test corpus.

Before any proposed GitHub publication, review the explicit package manifest, inspect the archive contents, run the tests, scan for private identifiers/paths and generated binaries, confirm repository licensing/publication scope, and obtain the requested publication decision. Do not infer permission to push from creation of this package.

No upstream LICENSE file was present in the inspected checkout. This package adds no LICENSE and invents no new license grant. Source attribution and owner-directed publication do not establish a broader third-party license. The parent workflow coordinates the user-authorized repository publication; this executor has not pushed anything.
