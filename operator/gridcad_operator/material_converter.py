"""Own versioned EcoFlex material converter, without vendor runtime/resources.

This is a narrow serialized-material interoperability profile, not a printer
capability or physical-color model. See docs/ECOFLEX_MATERIAL_CONTRACT.md.
"""
from __future__ import annotations

import copy
import hashlib
import math
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from .core import CHANNELS, FIELDS, ValidationError, validate_recipe

PROFILE = 'gridcad.ecoflex.5.119.0.v1'
VERSION = {'applicationName': 'GrabCAD Print', 'applicationVersion': '5.119.0',
           'versionNumbers': {'print': {'internal': 2191},
                              'pj': {'internal': 2190, 'external': '1.119'}}}
# Observed catalog facts required for this profile, not a bundled vendor DB.
# channel, resin id, internal name, display name, preview RGB
_RESINS = (
    ('C', 11934, 'VEcoFlxCyn', 'EcoFlexCyan', (0, 137, 166)),
    ('M', 11932, 'VEcoFlxMgn', 'EcoFlexMagenta', (198, 0, 88)),
    ('Y', 11933, 'VEcoFlxYlw', 'EcoFlexYellow', (240, 197, 0)),
    ('K', 11936, 'VEcoFlxBlk', 'EcoFlexBlack', (26, 26, 29)),
    ('W', 11935, 'VEcoFlxWht', 'EcoFlexWhite', (240, 240, 240)),
    ('T', 11931, 'VEcoFlxClr', 'EcoFlexClear', (192, 192, 206)),
)
CHANNEL_RESIN_IDS = {r[0]: str(r[1]) for r in _RESINS}
RESIN_NAMES = tuple(r[2] for r in _RESINS)
_BASE_FLAGS = (
    ('canAssignToModel', True), ('canBeHollowed', True),
    ('HollowForced', False), ('canBeCoated', True),
    ('canUseAsCoating', True), ('shoreA', 0),
    ('IsTranslucent', False), ('canChangeMaterialCore', True),
)


def _number_text(value: float) -> str:
    """Shortest binary64 decimal with ECMAScript's decimal/exponent layout.

    Python and ECMAScript choose shortest round-trip decimal significands;
    their fixed-notation thresholds and exponent padding differ. The range
    here is bounded to nonnegative percentages/display values (0..255).
    """
    if not math.isfinite(value) or not 0 <= value <= 255:
        raise ValidationError('Internal material number is outside the supported finite range.')
    if value == 0:
        return '0'
    shortest = repr(float(value)).lower()
    if 1e-6 <= value < 1e21:
        fixed = format(Decimal(shortest), 'f')
        return fixed.rstrip('0').rstrip('.') if '.' in fixed else fixed
    coefficient, exponent = shortest.split('e')
    coefficient = coefficient.rstrip('0').rstrip('.') if '.' in coefficient else coefficient
    n = int(exponent)
    return coefficient + 'e' + ('+' if n >= 0 else '-') + str(abs(n))


def _json_number(value: float):
    decimal = Decimal(_number_text(value))
    return int(decimal) if decimal == decimal.to_integral_value() else decimal


def _round_display(value: float) -> str:
    scaled = value * 100.0
    lower = math.floor(scaled)
    # Do not use Python round (ties-to-even), decimal rounding, or floor(x+.5)
    # (the addition can round a value just below the tie up to it).
    rounded = lower + (scaled - lower >= 0.5)
    return _number_text(rounded / 100.0)


def _percentages(recipe):
    if not isinstance(recipe, dict) or set(recipe) != {'channels', 'total', 'sum_tolerance'}:
        raise ValidationError('Material recipe requires channels, total, and sum_tolerance only.')
    channels = recipe['channels']
    if not isinstance(channels, dict) or set(channels) != set(CHANNELS):
        raise ValidationError('Material recipe needs exactly the six C M Y K W T channels.')
    # Parsed workbook recipes carry strings. Decimal/int are also safe caller
    # inputs; raw float provenance is ambiguous and must be made explicit.
    if any(type(channels[c]) not in (str, int, Decimal) for c in CHANNELS):
        raise ValidationError('Material percentages must be decimal strings, Decimal, or integer, not float/bool.')
    if any(isinstance(channels[c], str) and len(channels[c]) > 512 for c in CHANNELS):
        raise ValidationError('Channel decimal text exceeds the supported length limit.')
    checked = validate_recipe([channels[c] for c in CHANNELS])
    try:
        declared_total = Decimal(str(recipe['total']))
        declared_tolerance = Decimal(str(recipe['sum_tolerance']))
    except Exception as exc:
        raise ValidationError('Invalid declared recipe total/tolerance.') from exc
    if (not declared_total.is_finite() or not declared_tolerance.is_finite()
            or declared_total != 100 or declared_tolerance != 0):
        raise ValidationError('Material profile requires exact total 100 and zero sum tolerance; no normalization.')
    numbers = [Decimal(checked['channels'][c]) for c in CHANNELS]
    floats = [float(x) for x in numbers]
    for channel, decimal, number in zip(CHANNELS, numbers, floats):
        if Decimal(_number_text(number)) != decimal:
            raise ValidationError(f'{channel} percentage cannot survive native binary64 decimal serialization exactly; no rounding.')
    return numbers, floats


def _preview_rgb(percentages):
    """Ordered multiplicative tints using the six observed preview swatches."""
    components = [1.0, 1.0, 1.0]
    for percentage, resin in zip(percentages, _RESINS):
        if percentage > 0:
            fraction = percentage / 100.0
            for component, byte in enumerate(resin[4]):
                attenuation = (1.0 - byte / 255.0) * fraction
                components[component] *= 1.0 - attenuation
    return tuple(math.floor(x * 255.0) for x in components)


def _material(name, display, rgb, alpha, resin_id, mode, extra=None):
    metadata = dict(extra or ())
    metadata.update(_BASE_FLAGS)
    metadata.update(displayName=display, resinId=resin_id, materialType=mode)
    red, green, blue = rgb
    return {'id': str(uuid4()), 'properties': {}, 'name': name,
            'printerFamily': 'PolyJet', 'vendorMaterialId': name,
            'threeDAppearance': {'r': red, 'g': green, 'b': blue, 'a': alpha},
            'uiColor': f'rgb({red}, {green}, {blue})', 'metadata': metadata}


def _validate_profile(profile, version, channel_resin_ids, resin_names):
    if profile != PROFILE:
        raise ValidationError('Unknown EcoFlex material conversion profile.')
    # JSON document equality must not accept booleans in numeric version slots.
    if version != VERSION or any(type(version['versionNumbers'][name]['internal']) is not int
                                 for name in ('print', 'pj')):
        raise ValidationError('Unsupported application/Print/PJ material converter version.')
    if channel_resin_ids != CHANNEL_RESIN_IDS or any(type(x) is not str for x in channel_resin_ids.values()):
        raise ValidationError('Unknown resin classes or channel resin IDs; only the exact EcoFlex profile is supported.')
    if tuple(resin_names) != RESIN_NAMES:
        raise ValidationError('Unknown tray resin identities/order; only the exact EcoFlex profile is supported.')


class EcoFlexMaterialProvider:
    """Portable provider for candidate_writer; emits new complete material state.

    Any recipe in the supported numeric domain is computed, not looked up in a
    finite palette. Fresh UUIDs are the only nonsemantic/nondeterministic field.
    """
    def __init__(self, *, profile=PROFILE, version=None,
                 channel_resin_ids=None, resin_names=None):
        self.profile = profile
        self.version = copy.deepcopy(VERSION if version is None else version)
        self.channel_resin_ids = copy.deepcopy(CHANNEL_RESIN_IDS if channel_resin_ids is None else channel_resin_ids)
        self.resin_names = tuple(RESIN_NAMES if resin_names is None else resin_names)
        self._source_path = Path(__file__)
        self._source_sha256 = hashlib.sha256(self._source_path.read_bytes()).hexdigest()
        self.check_integrity()

    def check_integrity(self):
        _validate_profile(self.profile, self.version, self.channel_resin_ids, self.resin_names)
        if hashlib.sha256(self._source_path.read_bytes()).hexdigest() != self._source_sha256:
            raise ValidationError('Material converter implementation changed during this operation.')

    def sample(self, recipe):
        self.check_integrity()
        numbers, percentages = _percentages(recipe)
        native_name = 'CMYKWT DM Mixer: ' + ', '.join(
            f'{resin[2]}={_number_text(value)}%' for resin, value in zip(_RESINS, percentages))
        display = ', '.join(f'{resin[3]}={_round_display(value)}%'
                            for resin, value in zip(_RESINS, percentages) if value > 0)
        metadata = {'Name': display}
        metadata.update(('cmykwt_dm_' + field, int(number) if number == number.to_integral_value() else number)
                        for field, number in zip(FIELDS, numbers))
        metadata['cmykwt_dm_used_materials_id'] = [resin[1] for resin, value in zip(_RESINS, percentages) if value > 0]
        # 0 <= T <= 100 makes this 155..255: the native minimum-opacity
        # clamp cannot change it. Alpha is NOT percentage opacity * 255.
        alpha = _json_number(255.0 - percentages[-1])
        return _material(native_name, display, _preview_rgb(percentages), alpha,
                         2916, 'cmykwt_dm_mixer', metadata)

    __call__ = sample

    def direct_black(self):
        self.check_integrity()
        return _material('VEcoFlxBlk', 'EcoFlexBlack', (26, 26, 29), 255,
                         11936, 'base_material')

    def evidence(self):
        self.check_integrity()
        return {'provider': 'own_versioned_python_converter', 'profile': self.profile,
                'version': copy.deepcopy(self.version),
                'channel_resin_ids': copy.deepcopy(self.channel_resin_ids),
                'implementation_sha256': self._source_sha256,
                'provenance': 'Own implementation of observed serialized-material behavior; no vendor code, database, or runtime bundled.',
                'numeric_policy': 'Exact decimal total 100; each percentage must round-trip through binary64 shortest-decimal representation unchanged; never normalize.',
                'comparison_contract': 'Every serialized material field compared; only fresh UUID id excluded.',
                'profile_scope': 'Known minimal EcoFlex material metadata profile; not arbitrary native tray metadata or printer feasibility.',
                'vendor_origin_authenticated': False, 'print_ready': False}


def create_ecoflex_material(recipe, *, profile=PROFILE, version=None):
    return EcoFlexMaterialProvider(profile=profile, version=version).sample(recipe)
