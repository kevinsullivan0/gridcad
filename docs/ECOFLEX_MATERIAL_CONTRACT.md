# EcoFlex material conversion contract

Profile: `gridcad.ecoflex.5.119.0.v1`.

This small, independently authored Python converter computes complete material
objects for arbitrary recipes in the supported numeric domain. It is not a
finite recipe lookup table and requires no GrabCAD installation, JavaScript
runtime, vendor source, material database, or other vendor resource at runtime.
It implements a bounded observed serialization contract, not printer feasibility
or a physical model of printed color.

## Version and material scope

Only GrabCAD Print 5.119.0, Print internal 2191, PolyJet internal 2190 / external
1.119, and this exact ordered EcoFlex profile are admitted. Unknown profiles,
versions, resin identities/classes, or channel assignments fail closed.

| Channel | Resin ID | Internal identity | Display name | Preview RGB |
|---|---:|---|---|---|
| C | 11934 | VEcoFlxCyn | EcoFlexCyan | 0,137,166 |
| M | 11932 | VEcoFlxMgn | EcoFlexMagenta | 198,0,88 |
| Y | 11933 | VEcoFlxYlw | EcoFlexYellow | 240,197,0 |
| K | 11936 | VEcoFlxBlk | EcoFlexBlack | 26,26,29 |
| W | 11935 | VEcoFlxWht | EcoFlexWhite | 240,240,240 |
| T | 11931 | VEcoFlxClr | EcoFlexClear | 192,192,206 |

These are the small catalog facts needed for interoperability, not a copy of a
vendor database. Metadata follows the minimal observed Color-resin profile,
with resin ID 2916 for mixer output. It does not claim equivalence to every
possible native tray's optional metadata or to an installed printer profile.

## Exact percentages and native number behavior

The provider accepts the existing recipe object with exactly `channels`,
`total`, and `sum_tolerance`; `channels` must contain C/M/Y/K/W/T exactly once.

- Each channel must be an integer, Decimal, or decimal string, finite and in
  0..100. Booleans and raw Python floats are rejected.
- The actual six decimal values must total exactly 100. The declared total must
  also be 100 and the declared sum tolerance must be zero.
- Each input must retain the same numerical decimal value after conversion to
  binary64 and shortest-decimal serialization. No changed value is accepted.
  For example, 0.1, 1.005, and 0.0000001 are supported; 0.10000000000000001 is
  rejected because native binary64 serialization would change it to 0.1.
- The existing parser bounds each value to 64 digits and absolute exponent 64;
  decimal text is additionally bounded to 512 characters. There is no separate
  fixed decimal-place limit. A recipe still must satisfy every rule above.
- Trailing zeroes and signed zero are numerical formatting, not different
  recipes. Their canonical native name representation is used.
- Native binary64 summation may differ infinitesimally from 100 for an admitted
  decimal-exact recipe. Conversely, a binary64 sum of 100 does not excuse a
  non-100 exact decimal total. Neither case is silently normalized.

Percentages remain exact numeric JSON fields, using Python int/Decimal, not
strings or floats. Names use native shortest-decimal notation, including its
small-number exponent threshold. Tooltip text alone is rounded to two decimal
places using native binary64 multiplication and half-up rounding behavior;
this does not modify recipe percentages. A nonzero 0.0000001 channel therefore
remains in the used-resin IDs even if its tooltip displays 0%.

## Full output, not a metadata patch

Every conversion constructs fresh properties, names, appearance, UI color, and
metadata with mode `cmykwt_dm_mixer`. It never carries forward picker flags,
Pantone fields, or any prior material state.

- The internal name and vendorMaterialId list all six internal resin identities
  in C/M/Y/K/W/T order, including zero percentages.
- Tooltip Name/displayName lists only numerically nonzero channels, in that
  same order, with the observed display names.
- `cmykwt_dm_used_materials_id` contains precisely the positive channels' actual
  integer resin IDs in that order.
- Preview RGB is the ordered product of resin-swatch tint contributions, with
  binary64 arithmetic and final floor to bytes. It is not textbook CMYK.
- Appearance alpha is the native binary64 result of `255 - T`, not
  `255 * (1 - T / 100)`. Fractional alpha is retained as a JSON number. In this
  valid input domain alpha is 155..255, above the native minimum-opacity clamp.
- UUID id is fresh for each material. It is the only field excluded from exact
  semantic differential comparisons. No other field is ignored.

Labels use a distinct direct base material: name/vendorMaterialId VEcoFlxBlk,
resinId 11936, mode base_material, RGB 26/26/29. A K=100 mixer is not substituted:
its identity and metadata differ, and its native multiplicative preview happens
to floor to 25/25/29 because of binary64 arithmetic.

## Provider API

`EcoFlexMaterialProvider` provides `sample(recipe)`, `direct_black()`,
`check_integrity()`, and `evidence()`; the instance is also callable for a sample.
Constructor overrides for profile/version/channel IDs/resin names are validated
against the fixed contract, not used to extend it. Each operation rechecks the
contract and whether its source file changed since provider creation. This is
an operation-consistency check, not authentication or tamper-proof enforcement.

Use the package's exact JSON writer for project output. Generic report JSON
helpers that stringify Decimal are not a project serialization path.

## Evidence and boundaries

The implementation was written before inspection of its independent batch
oracle outputs. All admitted full-material objects matched unmodified native
converter results exactly except for fresh UUID id:

- 485 admitted vectors out of 517, covering pure channels and integer/1/2/3/6
  decimal partitions, zeros, display rounding, and fractional alpha. The other
  32 were deliberately refused because the native-generated input decimal
  values did not total exactly 100. They were not normalized or counted passes.
- 337 separately held-out cases, including 250 seeded random four-decimal
  mixtures and targeted pure/zero-heavy/fractional/rounding/signed-zero cases.
- A direct black material matched its native full object.
- 50,000 additional binary64 number-format samples matched JavaScript number
  strings, across 0..255 and small magnitudes. This is focused format coverage,
  not a proof of the entire numeric domain.

Unit tests include malformed recipes, precision loss, altered versions/resins,
fresh-state isolation, exact JSON round trips, and direct black versus K=100.
Optional external native vector tests can be run by setting
`GRIDCAD_ECOFLEX_ORACLE` to an externally supplied test-vector JSON file; those
vendor-derived fixtures are not runtime dependencies and are not distributed.

Material conversion does not validate a user's printer, loaded cartridges,
tray/template, supports, material availability, printability, native
recomposition, GUI reopening, or real-project safety. The candidate writer's
separate admission and production gates remain mandatory. Passing these tests
does not make a candidate file print-ready.
