"""Read-only inspection and explicit-plan conversion for one reviewed source profile.

Never interprets occurrenceScaling as a replacement for stored geometry, never
guesses glyph text, never normalizes percentages, and never claims print readiness.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
from decimal import Decimal as D
import xml.etree.ElementTree as ET
import zipfile

from .core import CHANNELS, FIELDS, ValidationError, validate_recipe
from .material_converter import EcoFlexMaterialProvider, PROFILE as MATERIAL_PROFILE

PLACEMENT_PROFILE = 'conservative-2170-cm-quarterturn-identity-compose-v2'
REVIEWED_ID_PROFILE = 'reviewed-ids-2170-material-only-translation-compose-v1'
SOURCE_VERSION = {
    'applicationName': 'GrabCAD Print', 'applicationVersion': '1.117.12.3985',
    'versionNumbers': {k: {'internal': 2170, 'external': '1.117'}
                       for k in ('print', 'fdm', 'pbf', 'origin', 'pj')},
}
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
RESIN_IDS = (11934, 11932, 11933, 11936, 11935, 11931)
RESIN_NAMES = ('VEcoFlxCyn', 'VEcoFlxMgn', 'VEcoFlxYlw', 'VEcoFlxBlk', 'VEcoFlxWht', 'VEcoFlxClr')


def fail(message):
    raise ValidationError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def exact_json(v):
    if v is None: return 'null'
    if type(v) is bool: return 'true' if v else 'false'
    if isinstance(v, str): return json.dumps(v, ensure_ascii=False)
    if type(v) is int: return str(v)
    if isinstance(v, D) and v.is_finite(): return str(v)
    if isinstance(v, list): return '[' + ','.join(exact_json(x) for x in v) + ']'
    if isinstance(v, dict): return '{' + ','.join(json.dumps(k) + ':' + exact_json(x) for k, x in v.items()) + '}'
    fail('Unsupported/nonfinite JSON number; binary float conversion is not allowed.')


def read_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: fail('Duplicate JSON key: ' + key)
            out[key] = value
        return out
    return json.loads(raw, parse_float=D, object_pairs_hook=pairs,
                      parse_constant=lambda value: fail('Nonfinite JSON: ' + value))


def fingerprint(value):
    return hashlib.sha256(exact_json(value).encode()).hexdigest()


def report_json(value):
    return json.dumps(value, indent=2, default=str, allow_nan=False) + '\n'


def archive(path):
    if Path(path).stat().st_size > 2 * 1024**3: fail('Archive exceeds 2 GiB.')
    z = zipfile.ZipFile(path)
    try:
        infos = z.infolist()
        if len(infos) > 20000 or len({i.filename for i in infos}) != len(infos):
            fail('Archive has too many or duplicate entries.')
        if sum(i.file_size for i in infos) > 2 * 1024**3: fail('Expanded archive exceeds 2 GiB.')
        for i in infos:
            name = PurePosixPath(i.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in i.filename:
                fail('Unsafe archive member name.')
            if i.flag_bits & 1 or stat.S_ISLNK(i.external_attr >> 16): fail('Encrypted/symlink member refused.')
            if i.file_size > 512 * 1024**2: fail('Archive member exceeds 512 MiB.')
        return z
    except Exception:
        z.close()
        raise


def project_document(path):
    with archive(path) as z:
        if z.getinfo('project.json').file_size > 32 * 1024**2: fail('Project JSON exceeds 32 MiB.')
        return read_json(z.read('project.json'))


def index(document):
    nodes, leaves, bodies = {}, set(), {}
    def visit(node, depth=0):
        if depth > 32: fail('Occurrence hierarchy exceeds 32 levels.')
        oid = node['id']
        if oid in nodes: fail('Duplicate occurrence ID.')
        nodes[oid] = node
        if not node.get('children'): leaves.add(oid)
        for child in node.get('children', []): visit(child, depth + 1)
    p = document['project']
    for root in p['rootOccurrences']: visit(root)
    if len(p['trays']) != 1: fail('This operator requires exactly one explicitly inspected tray.')
    body_ids = set()
    for body in p['trays'][0]['trayBodies']:
        oid = body['occurrence']
        if oid in bodies or body['id'] in body_ids: fail('Instanced/duplicate tray body is unsupported.')
        if oid not in leaves: fail('Tray body does not reference a known leaf.')
        bodies[oid] = body
        body_ids.add(body['id'])
    if set(bodies) != leaves: fail('Every leaf must have exactly one tray body.')
    return nodes, leaves, bodies


def xml(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): fail('DTD/entities refused.')
    return ET.fromstring(raw)


def workbook(path, selected=None):
    """Read stored XML only; never execute macros, formulas, links, or a calculation engine."""
    with archive(path) as z:
        names = z.namelist()
        if any('vbaproject' in n.lower() or n.startswith('xl/externalLinks/') for n in names):
            fail('Macro/external-link workbook refused; supply a values-only copy.')
        book = xml(z.read('xl/workbook.xml'))
        tabs = book.find('m:sheets', NS)
        rels = {r.get('Id'): r for r in xml(z.read('xl/_rels/workbook.xml.rels'))}
        strings = [''.join(n.itertext()) for n in xml(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in names else []
        result = {}
        for tab in tabs:
            title = tab.get('name')
            if selected is not None and title != selected: continue
            rel = rels[tab.get(REL)]
            if rel.get('TargetMode') == 'External': fail('External worksheet refused.')
            target = PurePosixPath(rel.get('Target'))
            member = str(target).lstrip('/') if target.is_absolute() else str(PurePosixPath('xl') / target)
            if '..' in PurePosixPath(member).parts: fail('Parent-relative worksheet target refused.')
            cells = {}
            for c in xml(z.read(member)).findall('m:sheetData/m:row/m:c', NS):
                address = c.get('r')
                if address in cells: fail('Duplicate worksheet address.')
                v = c.find('m:v', NS)
                value = v.text if v is not None else None
                kind = c.get('t')
                if kind == 's' and value is not None: value = strings[int(value)]
                if kind == 'inlineStr': value = ''.join(c.find('m:is', NS).itertext())
                cells[address] = {'value': value, 'formula': c.find('m:f', NS) is not None, 'type': kind}
            result[title] = cells
        if selected is not None and selected not in result: fail('Exact worksheet name not found.')
        return result


def cell_position(value):
    match = re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]{0,6})', value)
    if not match: fail('Use an explicit A1 cell address.')
    col = 0
    for c in match[1]: col = col * 26 + ord(c) - 64
    return int(match[2]), col


def rectangle(value):
    if not isinstance(value, str) or value.count(':') != 1: fail('Use an explicit rectangular range A1:B2.')
    lo, hi = map(cell_position, value.split(':'))
    if hi[0] < lo[0] or hi[1] < lo[1]: fail('Reversed rectangle refused.')
    if (hi[0]-lo[0]+1)*(hi[1]-lo[1]+1) > 100000: fail('Plan exceeds 100,000 cells.')
    return lo, hi


def recipe(value):
    if not isinstance(value, str): fail('Each recipe must be stored as a six-position slash string.')
    tokens = value.split('/')
    if len(tokens) != 6 or any(not t.strip() for t in tokens): fail('Exactly six explicit percentages required.')
    if any(not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)', t.strip()) for t in tokens):
        fail('Only plain decimal percentages are supported.')
    return validate_recipe([t.strip() for t in tokens])


def black(material):
    meta = material.get('metadata', {})
    return (material.get('name') == material.get('vendorMaterialId') == 'VEcoFlxBlk'
            and meta.get('materialType') == 'base_material' and type(meta.get('resinId')) is int
            and meta['resinId'] == 11936 and not any(k.startswith('cmykwt_dm_') for k in meta))


def matches_mixer(material, requested):
    meta = material.get('metadata', {})
    if meta.get('materialType') != 'cmykwt_dm_mixer' or meta.get('resinId') != 2916: return False
    if any(k in meta for k in ('pickerSelectedColor', 'pantone_materials', 'dmCategoryName')): return False
    values = [D(requested['channels'][c]) for c in CHANNELS]
    try:
        if any(type(meta['cmykwt_dm_'+f]) not in (int, D) for f in FIELDS): return False
        if [D(meta['cmykwt_dm_' + f]) for f in FIELDS] != values: return False
        if any(type(v) is not int for v in meta['cmykwt_dm_used_materials_id']): return False
        if meta['cmykwt_dm_used_materials_id'] != [rid for rid, v in zip(RESIN_IDS, values) if v > 0]: return False
        tokens = material['vendorMaterialId'].removeprefix('CMYKWT DM Mixer: ').split(', ')
        if len(tokens) != 6 or [t.split('=')[0] for t in tokens] != list(RESIN_NAMES): return False
        if [D(t.split('=')[1].removesuffix('%')) for t in tokens] != values: return False
        return material['name'] == material['vendorMaterialId']
    except (KeyError, ValueError, TypeError, IndexError):
        return False


def appearance_matches(body, material):
    appearance = body.get('properties', {}).get('threeDAppearance', {}).get('value', {})
    return all(k in material.get('threeDAppearance', {}) and appearance.get(k) == material['threeDAppearance'][k]
               for k in ('r','g','b','a'))


def matrix(value, linear):
    if not isinstance(value, list) or len(value) != 16: fail('Expected 16-value row-major transform.')
    if any(type(x) not in (int, D) or not D(x).is_finite() for x in value): fail('Nonfinite/non-numeric transform refused.')
    for r in range(3):
        for c in range(3):
            if abs(D(value[r*4+c])-D(linear[r*3+c])) > D('1e-12'): fail('Unknown transform scale/rotation/shear profile.')
    if value[12:] != [0, 0, 0, 1]: fail('Non-affine/column-major transform refused.')


def placement(document, nodes, bodies, profile=PLACEMENT_PROFILE):
    if profile not in (PLACEMENT_PROFILE, REVIEWED_ID_PROFILE): fail('Unknown placement/storage profile.')
    if document['version'] != SOURCE_VERSION: fail('Source version is outside the reviewed source profile.')
    identity = [1, 0, 0, 0, 1, 0, 0, 0, 1]
    tenth = [D('.1'), 0, 0, 0, D('.1'), 0, 0, 0, D('.1')]
    quarter = [0, 1, 0, -1, 0, 0, 0, 0, 1]
    tray_linear = [D(x)/10 for x in quarter]
    roots = {n['id'] for n in document['project']['rootOccurrences']}
    for oid, node in nodes.items():
        if node.get('featureManager') != {'uniqueFeatures':[], 'currentStateIndices':[]}:
            fail('Active/unknown occurrence or ancestor features are outside the passive-container profile.')
        if node.get('units') != 'CM' or node.get('occurrenceScaling') != D('.001'):
            fail('Unknown occurrence units/scaling profile; never repair source metadata.')
        matrix(node.get('rootScaling'), tenth)
        if any(node['rootScaling'][i] != 0 for i in (3, 7, 11)): fail('Translated rootScaling refused.')
        matrix(node.get('transform'), tenth if oid in roots else identity)
        if oid in roots and any(node['transform'][i] != 0 for i in (3,7,11)):
            fail('Translated root placement is outside this reviewed profile.')
        props = node.get('properties', {})
        if props.get('info.units', {}).get('value') != 'CM': fail('Units properties disagree.')
        if props.get('scale.factor', {}).get('value') != {'x':100, 'y':100, 'z':100}: fail('Unknown percentage scale.')
        if 'orientation' in props:
            matrix(props['orientation']['value'], quarter)
            if any(props['orientation']['value'][i] != 0 for i in (3,7,11)):
                fail('Translated orientation property is outside this reviewed profile.')
    common_linear = None
    compose_translations = []
    for body in bodies.values():
        matrix(body['transform'], tray_linear)
        linear = tuple(body['transform'][r*4+c] for r in range(3) for c in range(3))
        if common_linear is None: common_linear = linear
        elif linear != common_linear:
            fail('Tray bodies do not share the same reviewed linear transform.')
        compose = body.get('composeTransform')
        matrix(compose, identity)
        if profile == PLACEMENT_PROFILE and compose != [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]:
            fail('Nonidentity composeTransform is unsupported without native composition semantics; no translation-looking-field inference.')
        if profile == REVIEWED_ID_PROFILE:
            # Storage-form admission only. Never use this field to derive a
            # position, grid rank, unit conversion or native composition claim.
            if any(compose[r*4+c] != identity[r*3+c] for r in range(3) for c in range(3)):
                fail('Reviewed-ID mode admits only the observed exact pure-translation compose form.')
            translation = tuple(D(compose[i]) for i in (3,7,11))
            if any(abs(v)>1 for v in translation):
                fail('Reviewed-ID compose translation exceeds its bounded storage profile.')
            compose_translations.append(translation)
    if profile == REVIEWED_ID_PROFILE:
        for axis in range(3):
            values = [v[axis] for v in compose_translations]
            if max(values)-min(values)>D('1e-12'):
                fail('Reviewed-ID mode requires the observed common compose storage form.')


def inspect(project, xlsx):
    document = project_document(project)
    nodes, leaves, bodies = index(document)
    with archive(project) as z:
        entries = [{'name':i.filename, 'bytes':i.file_size} for i in z.infolist()]
    return {
        'archive_sha256':digest(project), 'workbook_sha256':digest(xlsx), 'source_version':document['version'],
        'placement_profile_supported': _placement_supported(document, nodes, bodies),
        'reviewed_id_storage_form_supported': _placement_supported(document, nodes, bodies, REVIEWED_ID_PROFILE),
        'warning':'Inspection is not a mapping decision or native application acceptance. Review actual printed glyph geometry.',
        'workbook':workbook(xlsx), 'archive_entries':entries,
        'leaves':[{'occurrence_id':oid, 'tray_body_id':bodies[oid]['id'], 'name':nodes[oid].get('name'),
                   'occurrence_transform':nodes[oid].get('transform'), 'tray_transform':bodies[oid].get('transform'),
                   'material':nodes[oid].get('material'), 'source_material_sha256':fingerprint(nodes[oid].get('material')),
                   'desired_actual_match':nodes[oid].get('material') == bodies[oid].get('material'),
                   'tessellation_key':nodes[oid].get('tessellationKey')}
                  for oid in sorted(leaves)],
    }


def _placement_supported(doc, nodes, bodies, profile=PLACEMENT_PROFILE):
    try:
        placement(doc, nodes, bodies, profile)
        return True
    except ValidationError:
        return False


def keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value)-set(required)-set(optional):
        fail('Plan has missing or unknown keys.')


def mapping_digest(plan):
    """Bind reviewed assignments to exact source/workbook, never to inferred ranks.

    A hash proves binding, not that label/geometry review occurred. The operator
    must independently establish the expected recipes and IDs before using it.
    """
    return fingerprint({
        'archive_sha256':plan['archive_sha256'], 'workbook_sha256':plan['workbook_sha256'],
        'sheet':plan['sheet'], 'range':plan['range'],
        'samples':[{'cell':s['cell'], 'occurrence_id':s['occurrence_id'], 'tray_body_id':s['tray_body_id'],
                    'expected_channels':validate_recipe(s['expected_percentages'])['channels']}
                   for s in sorted(plan['samples'], key=lambda s:cell_position(s['cell']))],
        'labels':[{'occurrence_id':s['occurrence_id'], 'tray_body_id':s['tray_body_id']}
                  for s in sorted(plan['labels'], key=lambda s:s['occurrence_id'])],
        'preserve_occurrence_ids':sorted(plan['preserve_occurrence_ids']),
    })


def prepare(project, xlsx, plan):
    keys(plan, ('plan_version','archive_sha256','workbook_sha256','source_version','placement_profile',
                'material_profile','allow_unverified_material_profile','review','sheet','range',
                'formula_cache_policy','expected_counts','samples','labels','preserve_occurrence_ids'), ('axes',))
    if plan['plan_version'] != 1 or type(plan['plan_version']) is not int: fail('Unknown plan version.')
    if plan['archive_sha256'] != digest(project) or plan['workbook_sha256'] != digest(xlsx): fail('Source hash differs from reviewed plan.')
    if plan['placement_profile'] not in (PLACEMENT_PROFILE, REVIEWED_ID_PROFILE) or plan['material_profile'] != MATERIAL_PROFILE: fail('Unknown explicit profile.')
    reviewed_ids = plan['placement_profile'] == REVIEWED_ID_PROFILE
    if reviewed_ids and 'axes' in plan: fail('Reviewed-ID material-only plans must omit axes; no translation-rank mapping proof is used.')
    if not reviewed_ids and 'axes' not in plan: fail('Identity-compose lattice mode requires explicit axes.')
    if plan['allow_unverified_material_profile'] is not True: fail('Explicit unverified material-profile acknowledgement required.')
    keys(plan['review'], ('geometry_and_labels_confirmed','evidence'), ('mapping_sha256',))
    if plan['review']['geometry_and_labels_confirmed'] is not True or not isinstance(plan['review']['evidence'], str) or not plan['review']['evidence'].strip():
        fail('Actual geometry/printed labels must be reviewed before conversion.')
    if reviewed_ids and not re.fullmatch(r'[0-9a-f]{64}', str(plan['review'].get('mapping_sha256',''))):
        fail('Reviewed-ID mode needs the source-bound independently reviewed mapping digest.')
    if plan['formula_cache_policy'] not in ('reject', 'confirmed_current_cache'): fail('Unknown formula cache policy.')
    doc = project_document(project)
    if doc['version'] != plan['source_version']: fail('Source version changed.')
    original = copy.deepcopy(doc)
    nodes, leaves, bodies = index(doc)
    placement(doc, nodes, bodies, plan['placement_profile'])
    lo, hi = rectangle(plan['range'])
    height, width = hi[0]-lo[0]+1, hi[1]-lo[1]+1
    keys(plan['expected_counts'], ('samples','labels'))
    if any(type(v) is not int or v < 0 for v in plan['expected_counts'].values()): fail('Counts must be nonnegative integers.')
    if plan['expected_counts'] != {'samples':height*width, 'labels':len(plan['labels'])}: fail('Plan cardinality differs from rectangle.')
    if len(plan['samples']) != height*width: fail('Plan needs exactly one sample per rectangular cell.')
    sheet = workbook(xlsx, plan['sheet'])[plan['sheet']]
    if not reviewed_ids:
        keys(plan['axes'], ('row_axis','row_direction','column_axis','column_direction','pitch_mm','cluster_tolerance_mm'))
        axes = plan['axes']
        if {axes['row_axis'], axes['column_axis']} != {'x','y'}: fail('Choose distinct explicit X/Y axes.')
        if any(type(axes[k]) is not int or axes[k] not in (-1,1) for k in ('row_direction','column_direction')): fail('Axis directions must be integer -1 or 1.')
        pitch, tolerance = D(axes['pitch_mm']), D(axes['cluster_tolerance_mm'])
        if not pitch.is_finite() or pitch <= 0 or not D('0.000001') <= tolerance <= D('.02'): fail('Invalid pitch/cluster tolerance.')
        if tolerance >= pitch/100: fail('Cluster tolerance must be less than one percent of pitch.')
    seen, cells, prepared, uniform, changed = set(), set(), [], set(), set()
    provider = EcoFlexMaterialProvider()
    original_material_users = {}
    # Include ancestor/container definitions as well as tray-body definitions.
    # A leaf-only ledger can miss inherited/shared UUID aliases and create two
    # different definitions of the same material ID after changing a sample.
    for oid, node in nodes.items():
        if node.get('material') is not None:
            material = node['material']
            if not isinstance(material, dict) or not isinstance(material.get('id'), str):
                fail('Unknown occurrence/ancestor material identity representation.')
            original_material_users.setdefault(material['id'], set()).add(('occurrence',oid))
    for oid, body in bodies.items():
        material = body.get('material')
        if not isinstance(material, dict) or not isinstance(material.get('id'), str):
            fail('Unknown tray-body material identity representation.')
        original_material_users.setdefault(material['id'], set()).add(('tray_body',oid))
    def target(entry, required):
        keys(entry, required)
        oid = entry['occurrence_id']
        if oid not in leaves or oid in seen: fail('Unknown/duplicate planned occurrence.')
        seen.add(oid)
        node, body = nodes[oid], bodies[oid]
        if entry['tray_body_id'] != body['id']: fail('Plan tray-body identity mismatch.')
        if node['material'] != body['material']: fail('Desired/actual material conflict; resolve externally.')
        if fingerprint(node['material']) != entry['source_material_sha256']: fail('Source material differs from reviewed state.')
        if node.get('featureManager', {}) != {'uniqueFeatures':[], 'currentStateIndices':[]}:
            fail('Active/unknown part features need separate native review.')
        return oid, node, body
    for entry in plan['samples']:
        oid, node, body = target(entry, ('cell','occurrence_id','tray_body_id','source_material_sha256','expected_percentages','action'))
        pos = cell_position(entry['cell'])
        if pos in cells or not lo[0] <= pos[0] <= hi[0] or not lo[1] <= pos[1] <= hi[1]: fail('Duplicate/out-of-range planned cell.')
        cells.add(pos)
        stored = sheet.get(entry['cell'])
        if not stored or stored['value'] is None or stored['type'] == 'e': fail('Missing cache/value or worksheet error.')
        if stored['formula'] and plan['formula_cache_policy'] != 'confirmed_current_cache': fail('Formula needs confirmed current calculation cache or values-only copy.')
        requested = recipe(stored['value'])
        independent = validate_recipe(entry['expected_percentages'])
        if any(D(requested['channels'][c]) != D(independent['channels'][c]) for c in CHANNELS):
            fail('Worksheet disagrees with independently expected label-derived recipe.')
        # Preflight must admit exactly the serializer's numeric domain, not just
        # decimal sum/range validity. This computes/discards a material without
        # modifying any source state. Precision-loss refusal happens here too.
        provider.sample(requested)
        action = entry['action']
        if action == 'replace_uniform_color_picker':
            if node['material']['metadata'].get('materialType') != 'color_picker': fail('Refusing overwrite of prior sample material work.')
            uniform.add(fingerprint({k:v for k,v in node['material'].items() if k != 'id'}))
            changed.add(oid)
        elif action == 'preserve_exact_mixer':
            if not matches_mixer(node['material'], requested) or not appearance_matches(body, node['material']):
                fail('Existing mixer recipe/appearance conflicts with requested state.')
        else: fail('Unknown sample action; no conflict overwrite action is provided.')
        prepared.append({'role':'sample', 'cell':entry['cell'], 'occurrence_id':oid,
                         'tray_body_id':body['id'], 'recipe':requested, 'action':action})
    if len(uniform) > 1: fail('Heterogeneous color-picker assignments need explicit external resolution.')
    for entry in plan['labels']:
        keys(entry, ('occurrence_id','tray_body_id','source_material_sha256','action'), ('reference_occurrence_id',))
        minimal = {k:v for k,v in entry.items() if k != 'reference_occurrence_id'}
        oid, node, body = target(minimal, ('occurrence_id','tray_body_id','source_material_sha256','action'))
        action = entry['action']
        item = {'role':'label','occurrence_id':oid,'tray_body_id':body['id'],'action':action}
        if action == 'preserve_native_black':
            if not black(node['material']) or not appearance_matches(body, node['material']):
                fail('Planned preserved label is not consistent direct EcoFlex Black.')
        elif action in ('assign_from_picker_using_native_black','assign_from_picker_using_unverified_black'):
            if node['material']['metadata'].get('materialType') != 'color_picker': fail('Refusing overwrite of intentional label assignment.')
            if action == 'assign_from_picker_using_native_black':
                reference = entry.get('reference_occurrence_id')
                if reference not in leaves or nodes[reference]['material'] != bodies[reference]['material'] or not black(nodes[reference]['material']):
                    fail('Native black reference must be an existing matching direct-black leaf.')
                item['reference_material'] = copy.deepcopy(nodes[reference]['material'])
            elif any(black(nodes[reference]['material']) for reference in leaves):
                fail('Native black is available: reference its complete object instead of the minimal converter.')
            changed.add(oid)
        else: fail('Unknown label action.')
        prepared.append(item)
    preserved = plan['preserve_occurrence_ids']
    if len(set(preserved)) != len(preserved) or set(preserved)&seen or seen|set(preserved) != leaves:
        fail('Plan must explicitly cover every leaf as sample, label, or preserved unrelated object.')
    for oid in changed:
        if original_material_users[nodes[oid]['material']['id']] != {('occurrence',oid),('tray_body',oid)}:
            fail('Changing a shared material identity requires native resolution; no UUID deletion or replacement.')
    if 'mapping_sha256' in plan['review'] and plan['review']['mapping_sha256'] != mapping_digest(plan):
        fail('Independent reviewed mapping binding differs from this exact source/assignment plan.')
    if reviewed_ids:
        # Exhaustive unique cell/occurrence/body membership, independent recipes,
        # source/material fingerprints and all safety guards above still apply.
        # Explicitly do NOT derive physical mapping from tray translations here.
        return original, doc, prepared, changed
    # Rank the actual tray translations in metres; do not multiply occurrence/root scales.
    sample_items = [p for p in prepared if p['role']=='sample']
    def cluster(axis, direction, count):
        offset = {'x':3,'y':7}[axis]
        values = sorted(D(bodies[p['occurrence_id']]['transform'][offset])*1000 for p in sample_items)
        groups = []
        for value in values:
            if not groups or value-groups[-1][0] > tolerance: groups.append([value])
            else: groups[-1].append(value)
        centers = [sum(group)/len(group) for group in groups]
        if len(centers) != count or any(abs(centers[i+1]-centers[i]-pitch)>tolerance for i in range(count-1)):
            fail('Actual lattice cardinality/pitch differs from reviewed plan.')
        return centers if direction == 1 else list(reversed(centers))
    row_centers = cluster(axes['row_axis'], axes['row_direction'], height)
    col_centers = cluster(axes['column_axis'], axes['column_direction'], width)
    for item in sample_items:
        body = bodies[item['occurrence_id']]
        pos = cell_position(item['cell'])
        for axis, centers, expected_index in ((axes['row_axis'],row_centers,pos[0]-lo[0]), (axes['column_axis'],col_centers,pos[1]-lo[1])):
            value = D(body['transform'][{'x':3,'y':7}[axis]])*1000
            matches = [i for i,c in enumerate(centers) if abs(c-value)<=tolerance]
            if matches != [expected_index]: fail('Explicit cell/body mapping disagrees with physical lattice.')
    return original, doc, prepared, changed


def stripped(document, changed):
    d = copy.deepcopy(document)
    nodes, _, bodies = index(d)
    for oid in changed:
        nodes[oid].pop('material')
        bodies[oid].pop('material')
        appearance = bodies[oid]['properties']['threeDAppearance']['value']
        for k in ('r','g','b','a'): appearance.pop(k)
    return d


def apply(project, xlsx, plan, out_dir):
    out_dir = Path(out_dir)
    if out_dir.exists() or out_dir.is_symlink(): fail('Output directory must not exist; nothing is overwritten.')
    before, after, assignments, changed = prepare(project, xlsx, plan)
    nodes, _, bodies = index(after)
    provider = EcoFlexMaterialProvider()
    for item in assignments:
        oid = item['occurrence_id']
        if oid not in changed: continue
        if item['role']=='sample': material = provider.sample(item['recipe'])
        elif 'reference_material' in item: material = copy.deepcopy(item['reference_material'])
        else: material = provider.direct_black()
        material['id'] = nodes[oid]['material']['id']
        nodes[oid]['material'] = copy.deepcopy(material)
        bodies[oid]['material'] = copy.deepcopy(material)
        bodies[oid]['properties']['threeDAppearance']['value'].update(material['threeDAppearance'])
    if stripped(before, changed) != stripped(after, changed): fail('Unexpected non-material mutation.')
    temp = Path(tempfile.mkdtemp(prefix='.gridcad-operator-', dir=out_dir.parent))
    published, owns_dir = [], False
    try:
        candidate = temp/'candidate_UNVERIFIED.PRINT'
        payloads = []
        with archive(project) as src, zipfile.ZipFile(candidate, 'x') as dst:
            dst.comment = src.comment
            for info in src.infolist():
                raw = exact_json(after).encode() if info.filename=='project.json' else src.read(info)
                dst.writestr(info, raw)
                if info.filename!='project.json': payloads.append({'name':info.filename,'sha256':hashlib.sha256(raw).hexdigest()})
        if project_document(candidate) != after: fail('Saved project readback mismatch.')
        with archive(project) as src, archive(candidate) as dst:
            if src.namelist()!=dst.namelist() or src.comment!=dst.comment or dst.testzip() is not None: fail('Archive structure/CRC differs.')
            for p in payloads:
                if hashlib.sha256(dst.read(p['name'])).hexdigest()!=p['sha256']: fail('Non-project payload changed.')
        saved_nodes, _, saved_bodies = index(project_document(candidate))
        for item in assignments:
            oid = item['occurrence_id']
            if saved_nodes[oid]['material'] != saved_bodies[oid]['material']: fail('Saved desired/actual mismatch.')
            if item['role']=='sample' and not matches_mixer(saved_nodes[oid]['material'], item['recipe']): fail('Saved recipe mismatch.')
            if item['role']=='label' and not black(saved_nodes[oid]['material']): fail('Saved label is not direct black.')
            if not appearance_matches(saved_bodies[oid], saved_nodes[oid]['material']): fail('Saved material/appearance mismatch.')
        if digest(project)!=plan['archive_sha256'] or digest(xlsx)!=plan['workbook_sha256']: fail('Input changed during conversion.')
        audit = {'status':'UNVERIFIED_CANDIDATE', 'source_sha256':plan['archive_sha256'],
                 'workbook_sha256':plan['workbook_sha256'], 'plan_sha256':fingerprint(plan),
                 'output_sha256':digest(candidate), 'source_version':before['version'],
                 'changed_occurrence_ids':sorted(changed),'changed_count':len(changed),
                 'unchanged_nonproject_payloads':len(payloads), 'nonmaterial_preservation_passed':True,
                 'all_existing_ids_preserved':True, 'native_open_recompose_save_verified':False,
                 'print_ready':False, 'material_provider':provider.evidence(),
                 'mapping_mode':'reviewed_exact_ids' if plan['placement_profile']==REVIEWED_ID_PROFILE else 'identity_compose_lattice_check',
                 'mapping_sha256':mapping_digest(plan),
                 'placement_interpretation':'not_interpreted_source_transforms_preserved' if plan['placement_profile']==REVIEWED_ID_PROFILE else 'restricted_identity_compose_lattice',
                 'physical_mapping_automatically_verified':False}
        manifest = [{k:v for k,v in item.items() if k!='reference_material'} for item in assignments]
        (temp/'audit.json').write_text(report_json(audit))
        (temp/'assignments.json').write_text(report_json(manifest))
        (temp/'preserved_payload_hashes.json').write_text(report_json(payloads))
        (temp/'reviewed_plan.json').write_text(exact_json(plan)+'\n')
        (temp/'UNVERIFIED.txt').write_text('DO NOT PRINT YET. File-level audit passed; native material semantics and GrabCAD open/recompose/save acceptance remain unverified. See audit.json and operator instructions.\n')
        for path in temp.iterdir():
            # Windows FlushFileBuffers requires a writable handle. The staged
            # files are ours; opening r+b preserves their bytes and fsync guard.
            with path.open('r+b') as f: os.fsync(f.fileno())
        out_dir.mkdir()  # Exclusive directory reservation; even an empty existing directory is refused.
        owns_dir = True
        for path in sorted(temp.iterdir()):
            destination = out_dir/path.name
            os.link(path, destination)  # Atomic create, never replace a race-created target.
            published.append(destination)
        return audit
    except Exception:
        for path in published:
            original = temp/path.name
            if path.exists() and original.exists() and os.path.samestat(path.stat(), original.stat()): path.unlink()
        if owns_dir:
            try: out_dir.rmdir()
            except OSError: pass
        raise
    finally:
        shutil.rmtree(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('inspect','check-plan','apply'):
        p = sub.add_parser(command)
        p.add_argument('--project', required=True, type=Path)
        p.add_argument('--workbook', required=True, type=Path)
        if command!='inspect': p.add_argument('--plan', required=True, type=Path)
        if command=='apply': p.add_argument('--out-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command=='inspect': result = inspect(args.project, args.workbook)
        else:
            plan = read_json(args.plan.read_bytes())
            if args.command=='check-plan':
                _, _, assignments, changed = prepare(args.project, args.workbook, plan)
                result = {'valid':True, 'assignments':len(assignments),'changes':len(changed),'native_acceptance':False}
            else: result = apply(args.project, args.workbook, plan, args.out_dir)
        print(report_json(result), end='')
    except (ValidationError, ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile, ET.ParseError) as error:
        parser.exit(2, 'Refused: '+str(error)+'\n')


if __name__=='__main__': main()
