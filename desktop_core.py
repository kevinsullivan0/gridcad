"""Deterministic, bounded rectangular proposals over the reviewed 2170 storage form.

The display convention is regression-tested against independently reviewed source
cases. It is not a native GrabCAD compose interpreter or glyph recognizer.
"""
from __future__ import annotations

import copy
from array import array
from bisect import bisect_left
from collections.abc import Sequence
import hashlib
import itertools
import math
import os
import stat
import tempfile
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'operator'))
from gridcad_operator import operator as op

VERSION = '1.0.1'
PROFILE = 'rectangular-2170-mesh-review-v1'
TOLERANCE = 0.0001  # mm, fixed; never enlarged to make an input fit.
MAX_PROJECT_BYTES = 2 * 1024**3
MAX_UNIQUE_TRIANGLES = 8_000_000
MAX_PREVIEW_TRIANGLES = 200_000
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


def read_rectangle(book, sheet, selected_range, *, cache_confirmed=False, cache_policy="reject"):
    if cache_policy not in ("reject", "saved"):
        op.fail("Unknown saved-formula result policy.")
    lo, hi = op.rectangle(selected_range.upper())
    if sheet not in book:
        op.fail('Choose an existing worksheet.')
    cells = []
    provider = None
    for row in range(lo[0], hi[0] + 1):
        for col in range(lo[1], hi[1] + 1):
            addr = address(row, col)
            value = book[sheet].get(addr)
            if not value or value['value'] is None or value['type'] == 'e':
                op.fail(sheet + '!' + addr + ': missing value, saved formula result, or worksheet error. Recalculate and save in Excel, or select a values-only copy.')
            if value['formula'] and not cache_confirmed and cache_policy != 'saved':
                op.fail(sheet + '!' + addr + ': formula uses a saved result. Recalculate in Excel, save, and confirm the cache, or use values only.')
            try:
                recipe = op.recipe(value['value'])
                if provider is None:
                    provider = op.EcoFlexMaterialProvider()
                provider.sample(recipe)  # Keep per-cell precision and source-integrity checks.
            except op.ValidationError as exc:
                op.fail(sheet + '!' + addr + ': ' + str(exc) + ' Put one sample recipe in each cell: C / M / Y / K / W / T percentages, for example 20 / 0 / 0 / 0 / 30 / 50.')
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
        return ''
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
    for values in struct.iter_unpack('<12fH', memoryview(raw)[84:]):
        if any(not math.isfinite(v) or abs(v) > 1e6 for v in values[:12]):
            op.fail('Nonfinite or excessive STL coordinate.')
        for k in range(3):
            # All coordinates were checked finite above. Scalar comparisons
            # avoid six temporary tuple slices and min/max calls per triangle.
            low, high = lo[k], hi[k]
            for offset in (3, 6, 9):
                coordinate = values[offset + k]
                if coordinate < low:
                    low = coordinate
                if coordinate > high:
                    high = coordinate
            lo[k], hi[k] = low, high
    if any(hi[k] - lo[k] <= 1e-8 for k in range(3)):
        op.fail('STL must describe a nonflat bounded 3D body.')
    # Surface triangles render real label geometry; do not replace it with names.
    top = array('f')
    for v in struct.iter_unpack('<12fH', memoryview(raw)[84:]):
        if min(v[5], v[8], v[11]) >= hi[2] - 0.0001:
            top.extend((v[3],v[4],v[6],v[7],v[9],v[10]))
    return {'bounds': [lo, hi], 'top': top, 'triangles': count,
            'sha256': hashlib.sha256(raw).hexdigest()}


class SharedTopSurface(Sequence):
    """Exact XY coordinates, transformed on access instead of copied per instance.

    A shared mesh owns one compact float array. Each body stores only its matrix;
    indexing performs the same arithmetic as the former expanded double array.
    Bounds and conversion never use preview sampling.
    """
    __slots__ = ('_coordinates', '_matrix')

    def __init__(self, coordinates, matrix):
        self._coordinates = coordinates
        self._matrix = tuple(matrix)

    def __len__(self):
        return len(self._coordinates)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return array('d', (self[i] for i in range(*index.indices(len(self)))))
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError('top-surface coordinate index out of range')
        offset = index - index % 2
        point = (self._coordinates[offset], self._coordinates[offset + 1], 0)
        row = index % 2
        m = self._matrix
        return sum(m[row * 4 + k] * point[k] * 10 for k in range(3)) + m[row * 4 + 3] * 1000

    def __eq__(self, other):
        if not isinstance(other, Sequence):
            return NotImplemented
        return len(self) == len(other) and all(a == b for a, b in zip(self, other))


def preview_render_plan(records, excluded_ids=()):
    """Allocate a fixed polygon budget fairly, including every nonempty body.

    The plan counts drawable top faces, not total mesh faces. Sampling is purely
    a display decision: all source faces are validated and source bytes preserved.
    Sorted IDs make allocation independent of dictionary insertion order.
    """
    excluded = set(excluded_ids)
    counts = {oid: len(records[oid]['top']) // 6 for oid in sorted(records)
              if oid not in excluded}
    total = sum(counts.values())
    if total <= MAX_PREVIEW_TRIANGLES:
        return counts
    nonempty = sum(count > 0 for count in counts.values())
    # The body limit is 10,000, below the normal 200,000-polygon budget.
    if nonempty > MAX_PREVIEW_TRIANGLES:
        op.fail('Resource limit: too many bodies for the bounded preview.')
    remaining = MAX_PREVIEW_TRIANGLES - nonempty
    extra_faces = total - nonempty
    return {oid: (1 + (count - 1) * remaining // extra_faces if count else 0)
            for oid, count in counts.items()}


def preview_triangles(record, max_triangles):
    """Yield at most the assigned number of evenly spaced, actual source faces."""
    top = record['top']
    count = len(top) // 6
    limit = min(count, max(0, max_triangles))
    for sample in range(limit):
        # Include both ends when possible. No unbounded traversal of skipped faces.
        face = sample * (count - 1) // (limit - 1) if limit > 1 else 0
        offset = face * 6
        yield tuple((top[offset + j], top[offset + j + 1]) for j in (0, 2, 4))


def _bounded_project_digest(path, destination=None):
    """Hash/copy a regular project file with bounded buffers and total bytes."""
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode):
            op.fail('Project source must be a regular file.')
        if info.st_size > MAX_PROJECT_BYTES:
            op.fail('Archive exceeds 2 GiB.')
        copied = 0
        while True:
            block = source.read(min(1024 * 1024, MAX_PROJECT_BYTES - copied + 1))
            if not block:
                break
            copied += len(block)
            if copied > MAX_PROJECT_BYTES:
                op.fail('Archive exceeds 2 GiB.')
            digest.update(block)
            if destination is not None:
                destination.write(block)
    return digest.hexdigest()


def load_project(path):
    """Bind the displayed document, meshes and digest to one private snapshot.

    The temporary copy is removed on success or failure. The public identity
    remains the original path; later conversion still rechecks its source hash.
    """
    with tempfile.TemporaryDirectory(prefix='gridcad-preview-') as directory:
        snapshot = Path(directory) / 'source.print'
        with snapshot.open('xb') as destination:
            source_hash = _bounded_project_digest(path, destination)
        project = _load_project_snapshot(snapshot)
        if project['sha256'] != source_hash or _bounded_project_digest(path) != source_hash:
            op.fail('Source changed while loading. Reopen the original project before mapping.')
        project['path'] = str(path)
        return project


def _load_project_snapshot(path):
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
    records, cache, body_meshes = {}, {}, {}
    total_triangles, instance_triangles = 0, 0
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
                # Preflight the header before allocating/decoding another mesh.
                with archive.open(member) as stream:
                    header = stream.read(84)
                if len(header) != 84:
                    op.fail('Unsupported or corrupt binary STL.')
                declared = struct.unpack_from('<I', header, 80)[0]
                if not 0 < declared <= 600000 or archive.getinfo(member).file_size != 84 + 50 * declared:
                    op.fail('Unsupported or corrupt binary STL. ASCII and other geometry need an explicit adapter.')
                if total_triangles + declared > MAX_UNIQUE_TRIANGLES:
                    op.fail('Unique embedded meshes exceed eight million triangles.')
                mesh = _mesh(archive.read(member))
                total_triangles += mesh['triangles']
                cache[member] = mesh
            mesh = cache[member]
            # Shared source geometry is decoded once. Instance amplification adds
            # only a matrix/view, never a transformed face array or a face loop.
            instance_triangles += mesh['triangles']
            body_meshes[oid] = member
        for oid, body in bodies.items():
            node = nodes[oid]
            mesh = cache[body_meshes[oid]]
            m = [float(v) for v in body['transform']]
            def transform(v):
                # Observed CM / 0.1-quarter-turn display convention: actual
                # mesh coordinates, not occurrence order or material color.
                return tuple(sum(m[r*4+k] * v[k] * 10 for k in range(3)) + m[r*4+3] * 1000 for r in range(3))
            corners = [transform(v) for v in itertools.product(*zip(*mesh['bounds']))]
            bounds = [[min(v[k] for v in corners) for k in range(3)],
                      [max(v[k] for v in corners) for k in range(3)]]
            top = SharedTopSurface(mesh['top'], m)
            records[oid] = {'id': oid, 'name': node.get('name', ''), 'bounds': bounds,
                            'center': [(bounds[0][k] + bounds[1][k]) / 2 for k in range(3)],
                            'mesh_sha256': mesh['sha256'],
                            'top': top}
    return {'path': str(path), 'sha256': op.digest(path), 'document': document,
            'nodes': nodes, 'leaves': leaves, 'bodies': bodies, 'groups': groups,
            'containers': containers, 'records': records, 'profile': PROFILE,
            'preview_resources': {'unique_triangles': total_triangles,
                                  'instance_triangles': instance_triangles,
                                  'shared_top_bytes': sum(len(mesh['top']) * mesh['top'].itemsize for mesh in cache.values()),
                                  'max_render_triangles': MAX_PREVIEW_TRIANGLES}}


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



def _nearest_rank(axis, value, *, finite_axis=True):
    """Sorted-axis nearest index, preserving the original first-minimum tie rule."""
    if not finite_axis or not math.isfinite(value):
        return min(range(len(axis)), key=lambda j: abs(axis[j] - value))
    if not axis:
        raise ValueError('min() arg is an empty sequence')
    i = bisect_left(axis, value)
    if i == len(axis) or (i and abs(axis[i-1] - value) <= abs(axis[i] - value)):
        i -= 1
    distance = abs(axis[i] - value)
    # Floating subtraction can round several distances to the same value,
    # even away from a midpoint. Find the earliest equal minimum, not just
    # the immediate lower neighbor. This also handles overflow to infinity.
    lo, hi = 0, i
    while lo < hi:
        mid = (lo + hi) // 2
        if abs(axis[mid] - value) > distance:
            lo = mid + 1
        else:
            hi = mid
    return lo


def _shape_grid(records, bodies):
    """Resolve positions from geometry, with a strictly contained anchor fallback.

    Shape/mesh equality is irrelevant. Different heights are allowed on a shared
    base plane. An anchor fallback is admitted only if every footprint contains
    its own stored anchor and lies strictly inside that anchor's rectangular
    half-pitch cell, so asymmetric geometry cannot drift into another cell.
    """
    for record in records:
        expected = [(record['bounds'][0][i] + record['bounds'][1][i]) / 2 for i in range(3)]
        if any(abs(a-b)>TOLERANCE for a,b in zip(expected,record['center'])):
            op.fail('A sample preview has inconsistent geometry bounds. Reopen the original project before mapping.')
    bases=[r['bounds'][0][2] for r in records]
    if max(bases)-min(bases)>TOLERANCE:
        op.fail('The samples do not share one base plane. Place the sample bottoms on one level before exporting the project.')

    def candidate(points, anchors=False):
        axes=[_clusters([p[i] for p in points.values()]) for i in (0,1)]
        if len(axes[0])*len(axes[1])!=len(records):
            op.fail('The samples do not fill a complete rectangular grid. Check for missing samples, duplicates, or a wrong sample group.')
        finite_axes = [all(math.isfinite(c) for c in axis) for axis in axes]
        ranks={}; occupied=set()
        for r in records:
            point=points[r['id']]
            rank=tuple(_nearest_rank(axes[i], point[i], finite_axis=finite_axes[i]) for i in (0,1))
            if rank in occupied:op.fail('Two samples occupy the same grid position. Separate them or select the correct sample group.')
            occupied.add(rank);ranks[r['id']]=rank
            if anchors:
                for axis in (0,1):
                    lo,hi=r['bounds'][0][axis],r['bounds'][1][axis]
                    if not lo-TOLERANCE<=point[axis]<=hi+TOLERANCE:
                        op.fail('A sample is offset from its stored grid position. Center its geometry on its placement origin before exporting.')
                    if len(axes[axis])>1:
                        half=(axes[axis][1]-axes[axis][0])/2
                        if lo<=point[axis]-half+TOLERANCE or hi>=point[axis]+half-TOLERANCE:
                            op.fail('A sample extends into a neighboring grid cell. Increase the spacing or align sample centers before exporting.')
        # Separation is determined from the real footprints, not mesh identity
        # or one global width. Neighbor rows/columns may have different sizes.
        by_id={r['id']:r for r in records}
        by_rank={rank:by_id[oid] for oid,rank in ranks.items()}
        for rank,r in by_rank.items():
            for axis in (0,1):
                other=list(rank);other[axis]+=1;other=by_rank.get(tuple(other))
                if other and r['bounds'][1][axis]>=other['bounds'][0][axis]-TOLERANCE:
                    op.fail('Neighboring sample footprints overlap or touch. Increase the grid spacing or choose separated sample bodies.')
        for rank,r in by_rank.items():
            for dx,dy in ((1,1),(1,-1)):
                other=by_rank.get((rank[0]+dx,rank[1]+dy))
                if other and all(r['bounds'][0][i]<=other['bounds'][1][i]+TOLERANCE and other['bounds'][0][i]<=r['bounds'][1][i]+TOLERANCE for i in (0,1)):
                    op.fail('Diagonal sample footprints overlap or touch. Increase the grid spacing before exporting.')
        return axes,ranks

    points={r['id']:r['center'][:2] for r in records}
    try:
        axes,ranks=candidate(points)
        return axes,ranks,'mesh-footprint-centers'
    except op.ValidationError as geometry_error:
        anchors={r['id']:[float(bodies[r['id']]['transform'][i])*1000 for i in (3,7)] for r in records}
        try:
            axes,ranks=candidate(anchors,True)
            return axes,ranks,'contained-placement-anchors'
        except op.ValidationError:
            # Prefer the directly observed geometry diagnosis to a confusing
            # secondary origin explanation; neither route guesses a mapping.
            raise geometry_error


def reference_material_info(project, reference):
    """Read-only, validated description for a visible reference-object selector."""
    material = op.native_reference_material(project['nodes'], project['bodies'], project['leaves'], reference)
    return {'id': reference, 'name': project['nodes'][reference].get('name', ''),
            'material_name': material.get('metadata', {}).get('displayName', material['name']),
            'material_sha256': op.fingerprint(material)}


def propose(project, workbook_path, book, sheet, selected_range, sample_name,
            label_container, orientation, *, transpose=False, cache_confirmed=False,
            label_mode="black", label_reference=None, confirm_label_replacement=False, cache_policy="reject"):
    if orientation not in ORIENTATIONS:
        op.fail('Choose how worksheet rows and columns run across the geometry preview.')
    cells, shape = read_rectangle(book, sheet, selected_range, cache_confirmed=cache_confirmed, cache_policy=cache_policy)
    samples = project['groups'].get(sample_name, [])
    if len(samples) != len(cells):
        op.fail(f'{sheet}!{selected_range}: {len(cells)} cells selected, but sample group {sample_name!r} has {len(samples)} sample bodies. Select {len(samples)} recipe cells or choose a matching sample group.')
    if label_container not in project['containers']:
        op.fail('Choose the complete printed-label container explicitly.')
    labels = project['containers'][label_container]['leaves']
    if set(samples) & labels:
        op.fail('Sample and label selections overlap. Choose the label-only container.')
    records = [project['records'][oid] for oid in samples]
    axes, grid_ranks, grid_basis = _shape_grid(records, project['bodies'])
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
        op.fail(f'{sheet}!{selected_range}: worksheet is {h} rows × {w} columns; sample group {sample_name!r} is {len(axes[ra])} × {len(axes[ca])} in this orientation. Choose the first-cell corner and next-row direction to match the project, or select the correct rectangle.')
    positions, used = {}, set()
    for r in records:
        ranks = grid_ranks[r['id']]
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
            'formula_cache_policy': 'saved_cache' if cache_policy == 'saved' else 'confirmed_current_cache' if cache_confirmed else 'reject',
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
    if label_mode not in ('black','reference'):
        op.fail('Choose black labels or copy the material from an existing reference object.')
    label_info = {'mode': label_mode, 'reference_id': None, 'conflicts': [],
                  'replacement_confirmed': confirm_label_replacement is True}
    if label_mode == 'reference':
        reference_material = op.native_reference_material(nodes, bodies, project['leaves'], label_reference)
        label_info.update(reference_id=label_reference, reference_name=nodes[label_reference].get('name', ''),
                          material_name=reference_material.get('metadata', {}).get('displayName', reference_material['name']))
    black_refs = [oid for oid in sorted(project['leaves']) if op.black(nodes[oid]['material'])]
    for oid in sorted(labels):
        material = nodes[oid]['material']
        entry = {'occurrence_id': oid, 'tray_body_id': bodies[oid]['id'],
                 'source_material_sha256': op.fingerprint(material), 'action': 'preserve_native_black'}
        if label_mode == 'reference':
            unchanged = op.same_material_definition(material, reference_material)
            entry.update(action='preserve_reference_material' if unchanged else 'copy_native_reference',
                         reference_occurrence_id=label_reference,
                         reference_material_sha256=op.fingerprint(reference_material),
                         replacement_confirmed=confirm_label_replacement is True)
            if not unchanged and material.get('metadata', {}).get('materialType') != 'color_picker':
                label_info['conflicts'].append({'id': oid, 'name': nodes[oid].get('name',''),
                    'current_material': material.get('metadata',{}).get('displayName',material.get('name',''))})
        elif not op.black(material):
            entry['action'] = 'assign_from_picker_using_native_black' if black_refs else 'assign_from_picker_using_unverified_black'
            if black_refs:
                entry['reference_occurrence_id'] = black_refs[0]
        plan['labels'].append(entry)
    label_info['conflict_count'] = len(label_info['conflicts'])
    return {'plan': plan, 'mapping': mapping, 'orientation': orientation, 'transpose': transpose,
            'profile': PROFILE, 'shape': shape, 'grid_basis': grid_basis, 'label_ids': sorted(labels),
            'preserved_count': len(plan['preserve_occurrence_ids']), 'label_material': label_info}


def confirm(proposal, evidence):
    if not isinstance(evidence, str) or not evidence.strip():
        op.fail('Record the corner/interior label checks used to confirm this mapping.')
    plan = copy.deepcopy(proposal['plan'])
    plan['review'] = {'geometry_and_labels_confirmed': True,
        'evidence': (f"{PROFILE}; mesh-derived relative XY, occurrence corroboration; "
                     f"orientation={proposal['orientation']}; transpose={proposal['transpose']}; grid_basis={proposal.get('grid_basis','mesh-footprint-centers')}. "
                     'Expected percentages are worksheet-derived requests, not OCR or independent label transcription. '
                     'Preview may sample top-surface triangles; it is not proof of label correspondence. User confirms physical labels/corners from sufficient geometry or source/native inspection: ' + evidence.strip())}
    plan['review']['mapping_sha256'] = op.mapping_digest(plan)
    return plan


def save(project_path, workbook_path, proposal, output_directory, evidence):
    plan = confirm(proposal, evidence)
    return op.apply(project_path, workbook_path, plan, output_directory)


def candidate_plan(proposal):
    """Bind a desktop candidate without inventing a physical-label attestation.

    The same exhaustive writer validation applies. This mode records the limit
    explicitly rather than treating a checkbox or free-text note as proof.
    """
    plan = copy.deepcopy(proposal['plan'])
    plan['review'] = {
        'mode': 'desktop_unverified_candidate',
        'geometry_and_labels_confirmed': False,
        'evidence': (f"{PROFILE}; worksheet-derived mapping; "
                     f"orientation={proposal['orientation']}; transpose={proposal['transpose']}. "
                     'Physical label correspondence has not been independently verified. '
                     'Save requested for a separate candidate; native validation remains required.'),
    }
    plan['review']['mapping_sha256'] = op.mapping_digest(plan)
    return plan


def save_candidate(project_path, workbook_path, proposal, output_directory):
    return op.apply(project_path, workbook_path, candidate_plan(proposal), output_directory)


def save_print(project_path, workbook_path, proposal, output_path, include_report=False):
    """Publish one named PRINT, optionally its report, after full writer checks.

    The advanced evidence bundle is kept private in a temporary directory. No
    existing destination is replaced, including files created during validation.
    A failed optional report never deletes an already completed PRINT.
    """
    import json
    output = Path(output_path)
    name = output.name
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                *(f'LPT{i}' for i in range(1, 10))}
    if (output.suffix.lower() != '.print' or name.endswith((' ', '.'))
            or any(ord(c) < 32 or c in '<>:"/\\|?*' for c in name)
            or name.split('.')[0].upper() in reserved):
        op.fail('Choose a valid Windows filename ending in .PRINT.')
    if not output.parent.is_dir():
        op.fail('Choose an existing folder for the saved PRINT file.')
    parent_identity = output.parent.stat()
    def check_folder():
        try:
            current = output.parent.stat()
        except OSError:
            current = None
        if current is None or (current.st_dev, current.st_ino) != (parent_identity.st_dev, parent_identity.st_ino):
            op.fail('The destination folder changed during saving. Choose the folder again and use another name.')
    report = output.with_name(output.stem + '.gridcad-report.json')
    destinations = [output] + ([report] if include_report else [])
    for target in destinations:
        if target.exists() or target.is_symlink():
            op.fail(f'A file already exists at {target}. Choose another name; existing files are never replaced.')
    with tempfile.TemporaryDirectory(prefix='.gridcad-save-', dir=output.parent) as temp:
        stage = Path(temp)
        audit = save_candidate(project_path, workbook_path, proposal, stage / 'validated')
        check_folder()
        audit = dict(audit, output_path=str(output))
        if include_report:
            audit['report_path'] = str(report)
        candidate = stage / 'validated' / 'candidate_UNVERIFIED.PRINT'
        if candidate.is_symlink() or op.digest(candidate) != audit['output_sha256']:
            op.fail('The validated result changed before saving. No PRINT was published; try again in a private local folder.')
        if include_report:
            staged_report = stage / 'report.json'
            with staged_report.open('x', encoding='utf-8') as handle:
                json.dump(audit, handle, indent=2, sort_keys=True)
                handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
        check_folder()
        identity = candidate.stat()
        os.link(candidate, output)
        check_folder()
        current = output.lstat()
        if ((current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino)
                or not stat.S_ISREG(current.st_mode)
                or op.digest(output) != audit['output_sha256']):
            op.fail('The saved result did not pass its final preservation check. Do not use this file; choose another name in a private local folder.')
        if include_report:
            try:
                os.link(staged_report, report)
                check_folder()
            except OSError:
                # Never roll back by deleting a pathname another process may
                # have replaced. The completed PRINT remains independently
                # validated; an optional report is not part of that validity.
                audit.pop('report_path', None)
                audit['report_warning'] = 'The PRINT was saved, but its optional report could not be saved. No existing file was replaced.'
    return audit
