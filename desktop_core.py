"""Deterministic, bounded rectangular proposals over the reviewed 2170 storage form.

The display convention is regression-tested against independently reviewed source
cases. It is not a native GrabCAD compose interpreter or glyph recognizer.
"""
from __future__ import annotations

import copy
from array import array
import hashlib
import itertools
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'operator'))
from gridcad_operator import operator as op

VERSION = '0.2.0rc1'
PROFILE = 'rectangular-2170-mesh-review-v1'
TOLERANCE = 0.0001  # mm, fixed; never enlarged to make an input fit.
ORIENTATIONS = {
    'Rows down; columns right': (1, -1, 0, 1),
    'Rows right; columns down': (0, 1, 1, -1),
    'Rows up; columns right': (1, 1, 0, 1),
    'Rows down; columns left': (1, -1, 0, -1),
    'Rows up; columns left': (1, 1, 0, -1),
    'Rows right; columns up': (0, 1, 1, 1),
    'Rows left; columns down': (0, -1, 1, -1),
    'Rows left; columns up': (0, -1, 1, 1),
}


def address(row, column):
    letters = ''
    while column:
        column, n = divmod(column - 1, 26)
        letters = chr(65 + n) + letters
    return letters + str(row)


def read_workbook(path):
    result = op.workbook(path)
    if not result:
        op.fail('Workbook has no readable worksheets.')
    return result


def read_rectangle(book, sheet, selected_range, *, cache_confirmed=False):
    lo, hi = op.rectangle(selected_range.upper())
    if sheet not in book:
        op.fail('Choose an existing worksheet.')
    cells = []
    for row in range(lo[0], hi[0] + 1):
        for col in range(lo[1], hi[1] + 1):
            addr = address(row, col)
            value = book[sheet].get(addr)
            if not value or value['value'] is None or value['type'] == 'e':
                op.fail(addr + ': missing value, formula cache, or worksheet error. Save a calculated values-only copy.')
            if value['formula'] and not cache_confirmed:
                op.fail(addr + ': formula uses a saved result. Recalculate in Excel, save, and confirm the cache, or use values only.')
            try:
                recipe = op.recipe(value['value'])
                op.EcoFlexMaterialProvider().sample(recipe)  # Admit serializer precision domain now.
            except op.ValidationError as exc:
                op.fail(addr + ': ' + str(exc))
            cells.append({'cell': addr, 'row': row - lo[0], 'column': col - lo[1],
                          'percentages': [recipe['channels'][c] for c in op.CHANNELS]})
    return cells, (hi[0] - lo[0] + 1, hi[1] - lo[1] + 1)


def suggest_range(cells):
    """Suggest the first contiguous recipe block; selection remains visible/editable."""
    recipes = set()
    for addr, value in cells.items():
        try:
            op.recipe(value['value'])
            recipes.add(op.cell_position(addr))
        except (op.ValidationError, TypeError):
            pass
    if not recipes:
        return 'A1:B2'
    r, c = min(recipes)
    endc = c
    while (r, endc + 1) in recipes:
        endc += 1
    endr = r
    while all((endr + 1, col) in recipes for col in range(c, endc + 1)):
        endr += 1
    return address(r, c) + ':' + address(endr, endc)


def _mesh(raw):
    if len(raw) < 84 or len(raw) > 32 * 1024**2:
        op.fail('Expected bounded binary STL (maximum 32 MiB).')
    count = struct.unpack_from('<I', raw, 80)[0]
    if not 0 < count <= 600000 or len(raw) != 84 + 50 * count:
        op.fail('Unsupported or corrupt binary STL. ASCII and other geometry need an explicit adapter.')
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for values in struct.iter_unpack('<12fH', raw[84:]):
        if any(not math.isfinite(v) or abs(v) > 1e6 for v in values[:12]):
            op.fail('Nonfinite or excessive STL coordinate.')
        for k in range(3):
            lo[k] = min(lo[k], *values[3+k:12:3])
            hi[k] = max(hi[k], *values[3+k:12:3])
    if any(hi[k] - lo[k] <= 1e-8 for k in range(3)):
        op.fail('STL must describe a nonflat bounded 3D body.')
    # Surface triangles render real label geometry; do not replace it with names.
    top = array('f')
    for v in struct.iter_unpack('<12fH', raw[84:]):
        if min(v[5], v[8], v[11]) >= hi[2] - 0.0001:
            top.extend((v[3],v[4],v[6],v[7],v[9],v[10]))
    return {'bounds': [lo, hi], 'top': top, 'triangles': count,
            'sha256': hashlib.sha256(raw).hexdigest()}


def load_project(path):
    document = op.project_document(path)
    nodes, leaves, bodies = op.index(document)
    if not bodies or len(bodies) > 10000:
        op.fail('Supported projects contain 1–10,000 bodies.')
    # Preserve every original gate. Common compose storage is admitted only by
    # the reviewed material writer; it is never composed into displayed geometry.
    op.placement(document, nodes, bodies, op.REVIEWED_ID_PROFILE)
    groups = {}
    for oid in sorted(leaves):
        groups.setdefault(nodes[oid].get('name', ''), []).append(oid)
    containers = {}
    def descendants(node):
        if not node.get('children'):
            return {node['id']}
        return set().union(*(descendants(n) for n in node['children']))
    for oid, node in nodes.items():
        if node.get('children'):
            containers[oid] = {'name': node.get('name', oid), 'leaves': descendants(node)}
    records, cache, total_triangles = {}, {}, 0
    with op.archive(path) as archive:
        basenames = {}
        for member in archive.namelist():
            basenames.setdefault(member.replace('\\', '/').rsplit('/', 1)[-1], []).append(member)
        tess = document['project'].get('tessellationMap', {})
        for oid, body in bodies.items():
            node = nodes[oid]
            ref = tess.get(node.get('tessellationKey'), {}).get('representations', {}).get('stl')
            if not isinstance(ref, str):
                op.fail('Every body needs an embedded STL reference for the supported preview.')
            base = ref.replace('\\', '/').rsplit('/', 1)[-1]
            matches = basenames.get(base, [])
            if len(matches) != 1:
                op.fail('Missing or ambiguous embedded STL. External paths are never followed.')
            member = matches[0]
            if member not in cache:
                if archive.getinfo(member).file_size > 32 * 1024**2:
                    op.fail('Embedded STL exceeds preview limit.')
                mesh = _mesh(archive.read(member))
                total_triangles += mesh['triangles']
                if total_triangles > 8000000:
                    op.fail('Unique embedded meshes exceed eight million triangles.')
                cache[member] = mesh
            mesh = cache[member]
            m = [float(v) for v in body['transform']]
            def transform(v):
                # Observed CM / 0.1-quarter-turn display convention: actual
                # mesh coordinates, not occurrence order or material color.
                return tuple(sum(m[r*4+k] * v[k] * 10 for k in range(3)) + m[r*4+3] * 1000 for r in range(3))
            corners = [transform(v) for v in itertools.product(*zip(*mesh['bounds']))]
            bounds = [[min(v[k] for v in corners) for k in range(3)],
                      [max(v[k] for v in corners) for k in range(3)]]
            top = array('d')
            for i in range(0,len(mesh['top']),2):
                top.extend(transform((mesh['top'][i],mesh['top'][i+1],0))[:2])
            records[oid] = {'id': oid, 'name': node.get('name', ''), 'bounds': bounds,
                            'center': [(bounds[0][k] + bounds[1][k]) / 2 for k in range(3)],
                            'mesh_sha256': mesh['sha256'],
                            'top': top}
    return {'path': str(path), 'sha256': op.digest(path), 'document': document,
            'nodes': nodes, 'leaves': leaves, 'bodies': bodies, 'groups': groups,
            'containers': containers, 'records': records, 'profile': PROFILE}


def _clusters(values):
    clusters = []
    for value in sorted(values):
        if not clusters or value - clusters[-1][0] > TOLERANCE:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    centers = [sum(c) / len(c) for c in clusters]
    if len(centers) > 1:
        pitch = (centers[-1] - centers[0]) / (len(centers) - 1)
        if pitch < TOLERANCE * 100 or any(abs(b - a - pitch) > TOLERANCE for a, b in zip(centers, centers[1:])):
            op.fail('Samples do not form a uniform rectangular lattice at fixed 0.0001 mm tolerance.')
    return centers


def propose(project, workbook_path, book, sheet, selected_range, sample_name,
            label_container, orientation, *, transpose=False, cache_confirmed=False):
    if orientation not in ORIENTATIONS:
        op.fail('Choose how worksheet rows and columns run across the geometry preview.')
    cells, shape = read_rectangle(book, sheet, selected_range, cache_confirmed=cache_confirmed)
    samples = project['groups'].get(sample_name, [])
    if len(samples) != len(cells):
        op.fail(f'Selected group has {len(samples)} bodies; the worksheet rectangle has {len(cells)} recipes. Select matching ranges/groups.')
    if label_container not in project['containers']:
        op.fail('Choose the complete printed-label container explicitly.')
    labels = project['containers'][label_container]['leaves']
    if set(samples) & labels:
        op.fail('Sample and label selections overlap. Choose the label-only container.')
    records = [project['records'][oid] for oid in samples]
    if len({r['mesh_sha256'] for r in records}) != 1:
        op.fail('Samples must share exactly the same embedded mesh payload in this profile.')
    axes = [_clusters([r['center'][i] for r in records]) for i in range(3)]
    if len(axes[2]) != 1 or len(axes[0]) * len(axes[1]) != len(samples):
        op.fail('Samples must fill one complete planar rectangular lattice without holes or duplicates.')
    # Independently stored occurrence positions corroborate relative geometry:
    # observed profile quarter-turn maps occurrence +Y to tray +X and +X to -Y.
    first = samples[0]
    n0 = project['nodes'][first]['transform']; b0 = project['bodies'][first]['transform']
    for oid in samples:
        n = project['nodes'][oid]['transform']; b = project['bodies'][oid]['transform']
        if abs(float(n[7]-n0[7]) - float(b[3]-b0[3])*1000) > TOLERANCE or abs(float(n[3]-n0[3]) + float(b[7]-b0[7])*1000) > TOLERANCE:
            op.fail('Occurrence positions do not corroborate the observed tray/mesh lattice convention.')
    ra, rd, ca, cd = ORIENTATIONS[orientation]
    h, w = shape[::-1] if transpose else shape
    if (len(axes[ra]), len(axes[ca])) != (h, w):
        op.fail(f'Geometry has {len(axes[ra])} × {len(axes[ca])} positions in this orientation; worksheet is {h} × {w}. Check transpose and orientation.')
    positions, used = {}, set()
    for r in records:
        ranks = [min(range(len(axes[i])), key=lambda j: abs(axes[i][j]-r['center'][i])) for i in (0,1)]
        row = ranks[ra] if rd == 1 else h-1-ranks[ra]
        col = ranks[ca] if cd == 1 else w-1-ranks[ca]
        if (row, col) in positions:
            op.fail('Multiple sample bodies occupy one grid position.')
        positions[row, col] = r['id']
    nodes, bodies = project['nodes'], project['bodies']
    plan = {'plan_version': 1, 'archive_sha256': project['sha256'],
            'workbook_sha256': op.digest(workbook_path), 'source_version': copy.deepcopy(op.SOURCE_VERSION),
            'placement_profile': op.REVIEWED_ID_PROFILE, 'material_profile': op.MATERIAL_PROFILE,
            'allow_unverified_material_profile': True,
            'review': {'geometry_and_labels_confirmed': False, 'evidence': ''},
            'sheet': sheet, 'range': selected_range.upper(),
            'formula_cache_policy': 'confirmed_current_cache' if cache_confirmed else 'reject',
            'expected_counts': {'samples': len(samples), 'labels': len(labels)},
            'samples': [], 'labels': [],
            'preserve_occurrence_ids': sorted(project['leaves'] - set(samples) - labels)}
    mapping = []
    for cell in cells:
        rc = (cell['column'], cell['row']) if transpose else (cell['row'], cell['column'])
        oid = positions[rc]; used.add(oid)
        material = nodes[oid]['material']; recipe = op.validate_recipe(cell['percentages'])
        action = 'preserve_exact_mixer' if op.matches_mixer(material, recipe) else 'replace_uniform_color_picker'
        plan['samples'].append({'cell': cell['cell'], 'occurrence_id': oid, 'tray_body_id': bodies[oid]['id'],
                                'source_material_sha256': op.fingerprint(material),
                                'expected_percentages': cell['percentages'], 'action': action})
        mapping.append({**cell, 'id': oid, 'center': project['records'][oid]['center'], 'action': action})
    black_refs = [oid for oid in sorted(project['leaves']) if op.black(nodes[oid]['material'])]
    for oid in sorted(labels):
        material = nodes[oid]['material']
        entry = {'occurrence_id': oid, 'tray_body_id': bodies[oid]['id'],
                 'source_material_sha256': op.fingerprint(material), 'action': 'preserve_native_black'}
        if not op.black(material):
            entry['action'] = 'assign_from_picker_using_native_black' if black_refs else 'assign_from_picker_using_unverified_black'
            if black_refs:
                entry['reference_occurrence_id'] = black_refs[0]
        plan['labels'].append(entry)
    return {'plan': plan, 'mapping': mapping, 'orientation': orientation, 'transpose': transpose,
            'profile': PROFILE, 'shape': shape, 'label_ids': sorted(labels),
            'preserved_count': len(plan['preserve_occurrence_ids'])}


def confirm(proposal, evidence):
    if not isinstance(evidence, str) or not evidence.strip():
        op.fail('Record the corner/interior label checks used to confirm this mapping.')
    plan = copy.deepcopy(proposal['plan'])
    plan['review'] = {'geometry_and_labels_confirmed': True,
        'evidence': (f"{PROFILE}; mesh-derived relative XY, occurrence corroboration; "
                     f"orientation={proposal['orientation']}; transpose={proposal['transpose']}. "
                     'Expected percentages are worksheet-derived requests, not OCR or independent label transcription. '
                     'User inspected actual displayed glyph geometry and confirms the requested mapping: ' + evidence.strip())}
    plan['review']['mapping_sha256'] = op.mapping_digest(plan)
    return plan


def save(project_path, workbook_path, proposal, output_directory, evidence):
    plan = confirm(proposal, evidence)
    return op.apply(project_path, workbook_path, plan, output_directory)
