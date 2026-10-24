"""Read-only, bounded geometry-assisted mapping proposals, never print authorization.

Only the explicitly named native GrabCAD row-major/metre placement profile is
accepted. STL itself has no units. This module does not guess them, infer text
from glyph shapes, read external mesh paths, or write a project. Eight discrete
XY orientations are proposed against the workbook's *complete* occupancy mask.
"""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import itertools
import json
import math
from pathlib import PurePosixPath
import struct
import sys
import zipfile

from .core import ValidationError, archive_inventory, project_index, transform_position, file_hash

PROFILE = 'grabcad-row-major-metres-v1'
MAX_STL_BYTES = 16 * 1024 * 1024
MAX_TRIANGLES = 200_000
MAX_TOTAL_TRIANGLES = 2_000_000
MAX_BODIES = 20_000
MAX_OVERLAP_CHECKS = 2_000_000
MAX_OVERLAP_DETAILS = 1000
MAX_MESH_CACHE_ENTRIES = 256
MAX_MESH_CACHE_BYTES = 2 * 1024 * 1024
IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
UNIT_MM = {'MM': 1.0, 'CM': 10.0, 'M': 1000.0, 'IN': 25.4}


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     default=str).encode()).hexdigest()


def _number(value, label):
    if isinstance(value, bool):
        raise ValidationError(label + ' must be finite numeric data.')
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValidationError(label + ' must be finite numeric data.') from exc
    if not math.isfinite(value) or abs(value) > 1e9:
        raise ValidationError(label + ' is nonfinite or outside supported magnitude.')
    return value


def _matrix(value, label, *, identity=False):
    if not isinstance(value, list) or len(value) != 16:
        raise ValidationError(label + ': expected a 16-value row-major matrix.')
    a = [_number(v, label) for v in value]
    if any(abs(a[i] - IDENTITY[i]) > 1e-9 for i in (12, 13, 14, 15)):
        raise ValidationError(label + ': not affine row-major; column-major/unknown layout refused.')
    if identity:
        if any(abs(v - target) > 1e-9 for v, target in zip(a, IDENTITY)):
            raise ValidationError(label + ': nonidentity occurrence/root transform needs native composition evidence.')
    else:
        # Refuse unknown scale/shear semantics rather than double-apply scale.factor.
        for r in range(3):
            for s in range(3):
                dot = sum(a[r*4+k] * a[s*4+k] for k in range(3))
                if abs(dot - (r == s)) > 1e-7:
                    raise ValidationError(label + ': nonrigid scale/shear is not supported by this profile.')
    return a


def _transform(point, matrix, factor_mm):
    return tuple(sum(matrix[r*4+c] * point[c] * factor_mm for c in range(3))
                 + 1000 * matrix[r*4+3] for r in range(3))


def read_stl(data, *, max_triangles=MAX_TRIANGLES):
    """Parse bounded strict ASCII or binary STL; report native-unit mesh facts.

    Surface centroid is area-weighted, not a solid-volume centroid. The shape
    signature is translation/triangle-order/winding invariant, not a proof of
    identity and not rotation invariant. No geometry leaves this process.
    """
    if not isinstance(data, bytes) or len(data) > MAX_STL_BYTES:
        raise ValidationError('STL exceeds bounded byte limit or is not bytes.')
    if type(max_triangles) is not int or not 1 <= max_triangles <= MAX_TRIANGLES:
        raise ValidationError('Invalid STL triangle limit.')
    triangles = []
    count = struct.unpack_from('<I', data, 80)[0] if len(data) >= 84 else None
    if count is not None and 84 + 50 * count == len(data):
        if not 0 < count <= max_triangles:
            raise ValidationError('Binary STL triangle count exceeds limit or is empty.')
        encoding = 'binary'
        for offset in range(84, len(data), 50):
            vals = struct.unpack_from('<12fH', data, offset)
            for v in vals[:12]:
                _number(v, 'Binary STL value')
            triangles.append(tuple(tuple(vals[3+3*r:6+3*r]) for r in range(3)))
    else:
        encoding = 'ascii'
        try:
            lines = [line.strip() for line in data.decode('ascii').splitlines() if line.strip()]
        except UnicodeDecodeError as exc:
            raise ValidationError('Invalid binary STL length or non-ASCII STL.') from exc
        if not lines or lines[0].split()[0] != 'solid' or lines[-1].split()[0] != 'endsolid':
            raise ValidationError('ASCII STL must have solid/endsolid framing; binary length may be corrupt.')
        if len(lines) > max_triangles * 7 + 2 or any(len(line) > 4096 for line in lines):
            raise ValidationError('ASCII STL record/line limit exceeded.')
        i = 1
        while i < len(lines) - 1:
            if i + 6 >= len(lines) - 1:
                raise ValidationError('Incomplete ASCII STL facet.')
            normal = lines[i].split()
            if len(normal) != 5 or normal[:2] != ['facet', 'normal']:
                raise ValidationError('Invalid ASCII STL facet normal.')
            [_number(v, 'ASCII STL normal') for v in normal[2:]]
            if lines[i+1] != 'outer loop' or lines[i+5:i+7] != ['endloop', 'endfacet']:
                raise ValidationError('Invalid ASCII STL facet structure.')
            tri = []
            for line in lines[i+2:i+5]:
                parts = line.split()
                if len(parts) != 4 or parts[0] != 'vertex':
                    raise ValidationError('Invalid ASCII STL vertex.')
                tri.append(tuple(_number(v, 'ASCII STL vertex') for v in parts[1:]))
            triangles.append(tuple(tri)); i += 7
            if len(triangles) > max_triangles:
                raise ValidationError('STL triangle limit exceeded.')
        if not triangles:
            raise ValidationError('STL contains no triangles.')
    lo = [min(v[k] for tri in triangles for v in tri) for k in range(3)]
    hi = [max(v[k] for tri in triangles for v in tri) for k in range(3)]
    area = 0.0; weighted = [0.0, 0.0, 0.0]; canonical = []
    for tri in triangles:
        a, b, c = tri
        u = [b[k]-a[k] for k in range(3)]; v = [c[k]-a[k] for k in range(3)]
        cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        surface = math.sqrt(sum(x*x for x in cross))/2
        if surface == 0:
            raise ValidationError('Degenerate STL triangle; geometry proposal refused.')
        area += surface
        for k in range(3):
            weighted[k] += surface * sum(vertex[k] for vertex in tri)/3
        canonical.append(sorted(tuple(round(vertex[k]-lo[k], 9) for k in range(3)) for vertex in tri))
    return {'encoding': encoding, 'triangle_count': len(triangles), 'bounds': [lo, hi],
            'surface_centroid': [v/area for v in weighted], 'surface_area': area,
            'shape_signature': _hash(sorted(canonical)),
            'payload_sha256': hashlib.sha256(data).hexdigest()}


def _mesh_member(node, project, entry_names, basenames):
    references = []
    key = node.get('tessellationKey')
    if key is not None:
        tess_map = project.get('tessellationMap', {})
        if not isinstance(tess_map, dict) or not isinstance(key, str):
            raise ValidationError('Unrecognized tessellation map structure.')
        tess = tess_map.get(key)
        if not isinstance(tess, dict) or not isinstance(tess.get('representations'), dict):
            raise ValidationError('Unresolved tessellation map reference for ' + node['id'])
        references.append(tess['representations'].get('stl'))
    references.append(node.get('filePath'))
    candidates = set()
    for ref in references:
        if ref is None:
            continue
        if not isinstance(ref, str) or not ref.lower().endswith('.stl'):
            raise ValidationError('Unrecognized mesh representation/reference for ' + node['id'])
        if ref in entry_names:
            candidates.add(ref)
        else:
            # Native absolute paths are identifiers, never filesystem authority.
            # Resolve only a unique archive basename; never open the external path.
            base = PurePosixPath(ref.replace('\\', '/')).name
            matches = basenames.get(base, [])
            if len(matches) != 1:
                raise ValidationError('External mesh reference has no unique embedded STL: ' + node['id'])
            candidates.add(matches[0])
    if len(candidates) != 1:
        raise ValidationError('Ambiguous or missing embedded STL reference for ' + node['id'])
    return candidates.pop()


def _overlap_observations(records, tolerance):
    """Bounded source AABB facts, never a mesh-intersection/printability verdict.

    The sample lattice is checked separately and exhaustively. Exhausting this
    optional layout diagnostic cannot turn an otherwise unique mapping invalid.
    """
    active = []; checks = 0; contacts = 0; details = []
    def result(complete):
        return {'scope':'source_layout_only', 'complete':complete, 'pairs_checked':checks,
                'bounds_contact_count':contacts, 'overlap_facts':details,
                'details_truncated':contacts>len(details), 'centroid_tolerance_mm':tolerance}
    axis = max(range(3), key=lambda k: max(b['bounds_mm'][1][k] for b in records)-min(b['bounds_mm'][0][k] for b in records))
    for body in sorted(records, key=lambda b: (b['bounds_mm'][0][axis], b['occurrence_id'])):
        low, high = body['bounds_mm']
        active = [a for a in active if a['bounds_mm'][1][axis] >= low[axis] - 1e-9]
        for other in active:
            if checks >= MAX_OVERLAP_CHECKS:
                return result(False)
            checks += 1
            ol, oh = other['bounds_mm']
            depths = [min(high[k],oh[k])-max(low[k],ol[k]) for k in range(3)]
            if all(depth >= -1e-9 for depth in depths):
                contacts += 1
                if len(details) < MAX_OVERLAP_DETAILS:
                    details.append({'occurrence_ids':sorted([other['occurrence_id'],body['occurrence_id']]),
                                    'bounds_contact_depth_mm':[max(0.0,d) for d in depths],
                                    'centroid_distance_mm':math.dist(body['centroid_mm'],other['centroid_mm']),
                                    'centroids_coincident_within_tolerance':math.dist(body['centroid_mm'],other['centroid_mm'])<=tolerance})
        active.append(body)
    return result(True)


def _layout_warnings(observations, roles):
    classified = {}
    for fact in observations['overlap_facts']:
        pair_roles = tuple(sorted(roles.get(oid,'unclassified') for oid in fact['occurrence_ids']))
        item = classified.setdefault(pair_roles, {'code':'source_bounds_contact', 'roles':list(pair_roles),
            'reported_pair_count':0, 'example_occurrence_pairs':[],
            'message':'Pre-existing conservative bounding boxes overlap or touch. This is not proof of mesh intersection or a printability verdict; source geometry is not changed by the proposal.'})
        item['reported_pair_count'] += 1
        if len(item['example_occurrence_pairs']) < 5:
            item['example_occurrence_pairs'].append(fact['occurrence_ids'])
    warnings = [classified[key] for key in sorted(classified)]
    if observations['details_truncated'] or not observations['complete']:
        warnings.append({'code':'source_layout_diagnostic_bounded',
            'message':'Source-layout overlap diagnostics reached a detail/comparison limit; reported contacts are not exhaustive. Sample centroid/lattice validation is separate and complete.',
            'bounds_contact_count':observations['bounds_contact_count'],
            'comparison_complete':observations['complete'], 'details_truncated':observations['details_truncated']})
    return warnings


def _coincident_sample_pair(records, tolerance):
    """Reject sample identity ambiguity independent of bounded AABB diagnostics."""
    bins = {}
    for record in records:
        x,y = record['centroid_mm'][:2]
        key = (math.floor(x/tolerance),math.floor(y/tolerance))
        for dx,dy in itertools.product((-1,0,1),repeat=2):
            for other in bins.get((key[0]+dx,key[1]+dy),()):
                if math.dist(record['centroid_mm'][:2],other['centroid_mm'][:2]) <= tolerance:
                    return [other['occurrence_id'],record['occurrence_id']]
        bins.setdefault(key,[]).append(record)
    return None


def _mesh_facts_cache_weight(digest, facts):
    """Conservative retained Python-object weight plus per-entry LRU overhead."""
    seen = set()
    def weight(value):
        if id(value) in seen:
            return 0
        seen.add(id(value)); size = sys.getsizeof(value)
        if isinstance(value,dict):
            size += sum(weight(k)+weight(v) for k,v in value.items())
        elif isinstance(value,(list,tuple)):
            size += sum(weight(v) for v in value)
        return size
    # Shared/interned keys are deliberately charged independently per entry.
    return weight(facts) + sys.getsizeof(digest) + 512


def inspect_geometry(archive_path, *, tray_id=None, profile=PROFILE, tolerance_mm=0.02):
    """Read and bind geometry for one native tray; fail closed on unknown layout."""
    tolerance = _number(tolerance_mm, 'Tolerance')
    if not 1e-6 <= tolerance <= 0.5:
        raise ValidationError('Tolerance must be between 0.000001 and 0.5 mm.')
    inv = archive_inventory(archive_path)
    doc = inv['project_document']; project, nodes, refs = project_index(doc)
    if profile != PROFILE or not isinstance(doc.get('version'), dict) or doc['version'].get('applicationName') != 'GrabCAD Print':
        raise ValidationError('Unrecognized native placement/units profile; synthetic column-major layouts are not interchangeable.')
    trays = project['trays']
    if tray_id is None:
        if len(trays) != 1:
            raise ValidationError('Select one tray explicitly for geometry proposal.')
        tray_id = trays[0]['id']
    if tray_id not in {t['id'] for t in trays}:
        raise ValidationError('Unknown selected tray.')
    tray = next(t for t in trays if t['id'] == tray_id)
    if not 0 < len(tray['trayBodies']) <= MAX_BODIES:
        raise ValidationError('Selected tray is empty or exceeds body limit.')
    names = {e['name'] for e in inv['entries'] if not e['directory']}
    sizes = {e['name']: e['size'] for e in inv['entries']}
    expected_hashes = {e['name']: e['sha256'] for e in inv['entries']}
    basenames = {}
    for name in names:
        basenames.setdefault(PurePosixPath(name).name, []).append(name)
    parents = {}
    def visit(children, ancestors=()):
        for n in children:
            parents[n['id']] = ancestors
            visit(n.get('children', []), ancestors+(n['id'],))
    visit(project['rootOccurrences'])
    # Per-inspection only: content-addressed mesh-LOCAL facts, not placements,
    # units, IDs, role decisions, bindings or approval. No STL bytes/triangles
    # remain in this bounded LRU. The verified-member set is archive-bounded.
    mesh_cache = OrderedDict(); mesh_cache_bytes = 0; verified_members = set()
    records = []; total_triangles = 0; transform_records = []
    with zipfile.ZipFile(archive_path) as z:
        for body in tray['trayBodies']:
            oid = body['occurrence']; node = nodes[oid]
            if node.get('children') or len(refs[oid]) != 1:
                raise ValidationError('Instanced/group tray-body geometry needs explicit native resolution: ' + oid)
            unit = node.get('units')
            if not isinstance(unit, str) or unit not in UNIT_MM:
                raise ValidationError('Missing or unrecognized explicit STL units for ' + oid)
            factor = UNIT_MM[unit]
            if abs(_number(node.get('occurrenceScaling'), 'occurrenceScaling') - factor/1000) > 1e-12:
                raise ValidationError('Units/occurrenceScaling conflict for ' + oid)
            prop = node.get('properties', {})
            if not isinstance(prop, dict) or not isinstance(prop.get('info.units', {}), dict) or not isinstance(prop.get('scale.factor', {}), dict):
                raise ValidationError('Unrecognized occurrence properties for ' + oid)
            unit_prop = prop.get('info.units', {}).get('value', unit)
            if unit_prop != unit:
                raise ValidationError('Conflicting units properties for ' + oid)
            scale_prop = prop.get('scale.factor', {}).get('value', {'x':100, 'y':100, 'z':100})
            if scale_prop != {'x':100, 'y':100, 'z':100}:
                raise ValidationError('Unresolved scale.factor semantics for ' + oid)
            ancestor_transforms = []; ancestor_orientation_properties = []
            for parent_id in parents[oid] + (oid,):
                n = nodes[parent_id]
                parent_properties = n.get('properties', {})
                if not isinstance(parent_properties, dict):
                    raise ValidationError('Unrecognized ancestor properties.')
                orientation = parent_properties.get('orientation')
                if orientation is not None:
                    if not isinstance(orientation, dict):
                        raise ValidationError('Unrecognized orientation property for ' + parent_id)
                    _matrix(orientation.get('value'), 'Orientation property ' + parent_id, identity=True)
                ancestor_orientation_properties.append(orientation)
                ancestor_scale = parent_properties.get('scale.factor', {})
                if not isinstance(ancestor_scale, dict) or ancestor_scale.get('value', {'x':100,'y':100,'z':100}) != {'x':100,'y':100,'z':100}:
                    raise ValidationError('Unresolved ancestor scale.factor for ' + parent_id)
                ancestor_transforms.append(_matrix(n.get('transform', IDENTITY), 'Occurrence ' + parent_id, identity=True))
                if 'rootScaling' in n:
                    _matrix(n['rootScaling'], 'rootScaling ' + parent_id, identity=True)
            if 'occurrenceTransform' in body:
                _matrix(body['occurrenceTransform'], 'Tray occurrenceTransform ' + oid, identity=True)
            matrix = _matrix(body.get('transform'), 'Tray body ' + oid)
            # composeTransform is stored/hashed but is not silently multiplied into
            # body.transform. The native fixture includes a separate composition offset.
            if 'composeTransform' in body:
                _matrix(body['composeTransform'], 'composeTransform ' + oid)
            member = _mesh_member(node, project, names, basenames)
            digest = expected_hashes[member]
            if member not in verified_members or digest not in mesh_cache:
                if sizes[member] > MAX_STL_BYTES:
                    raise ValidationError('Embedded STL exceeds geometry reader byte limit.')
                payload = z.read(member)
                if hashlib.sha256(payload).hexdigest() != digest:
                    raise ValidationError('Archive mesh changed after inventory.')
                # A hash hit never skips integrity checking of a new member.
                if digest in mesh_cache:
                    mesh, _ = mesh_cache[digest]
                    mesh_cache.move_to_end(digest)
                else:
                    mesh = read_stl(payload)
                    weight = _mesh_facts_cache_weight(digest,mesh)
                    if MAX_MESH_CACHE_ENTRIES > 0 and weight <= MAX_MESH_CACHE_BYTES:
                        while mesh_cache and (len(mesh_cache) >= MAX_MESH_CACHE_ENTRIES or
                                              mesh_cache_bytes + weight > MAX_MESH_CACHE_BYTES):
                            _, (_, old_weight) = mesh_cache.popitem(last=False)
                            mesh_cache_bytes -= old_weight
                        mesh_cache[digest] = (mesh,weight)
                        mesh_cache_bytes += weight
                if member not in verified_members:
                    # Preserve the previous per-archive-member triangle budget,
                    # including identical payloads under different filenames.
                    total_triangles += mesh['triangle_count']
                    if total_triangles > MAX_TOTAL_TRIANGLES:
                        raise ValidationError('Total unique STL triangle budget exceeded.')
                    verified_members.add(member)
            else:
                mesh, _ = mesh_cache[digest]
                mesh_cache.move_to_end(digest)
            corners = [_transform(v, matrix, factor) for v in itertools.product(*zip(*mesh['bounds']))]
            bounds = [[min(v[k] for v in corners) for k in range(3)], [max(v[k] for v in corners) for k in range(3)]]
            # Unit-qualified signature is conservative: scaled encodings may form
            # separate groups, never silently the same group.
            signature = _hash({'shape':mesh['shape_signature'], 'unit_mm':factor,
                               'linear_transform':[matrix[r*4+c] for r in range(3) for c in range(3)]})
            transform_record = {'occurrence_id':oid, 'body_id':body['id'], 'body_transform':body.get('transform'),
                                'compose_transform':body.get('composeTransform'), 'occurrence_transform':body.get('occurrenceTransform'),
                                'ancestor_transforms':ancestor_transforms, 'ancestor_orientation_properties':ancestor_orientation_properties, 'units':unit,
                                'occurrence_scaling':node.get('occurrenceScaling'), 'scale_factor':scale_prop}
            transform_records.append(transform_record)
            records.append({'occurrence_id':oid, 'body_id':body['id'], 'ancestors':list(parents[oid]),
                            'member':member, 'mesh_sha256':mesh['payload_sha256'], 'triangle_count':mesh['triangle_count'],
                            'shape_signature':signature, 'bounds_mm':bounds,
                            'centroid_mm':list(_transform(mesh['surface_centroid'], matrix, factor)),
                            'transform_sha256':_hash(transform_record)})
    layout_observations = _overlap_observations(records, tolerance)
    if inv['sha256'] != file_hash(archive_path):
        raise ValidationError('Archive changed during geometry inspection.')
    records.sort(key=lambda r:r['occurrence_id'])
    return {'profile':PROFILE, 'tray_id':tray_id, 'units':'mm', 'bodies':records, 'layout_observations':layout_observations,
            'binding':{'archive_sha256':inv['sha256'],
                       'geometry_sha256':_hash([(r['occurrence_id'],r['member'],r['mesh_sha256']) for r in records]),
                       'transforms_sha256':_hash(sorted(transform_records, key=lambda r:r['occurrence_id']))},
            'limitations':['Bounds conservatively enclose meshes; pre-existing bounding-box contacts are source-layout warnings, not mesh-intersection or printability findings.',
                           'Placement uses native body.transform only; composeTransform is separately checked and bound, not applied a second time.',
                           'Only identity occurrence/ancestor/root/orientation-property transforms and rigid tray transforms are supported.']}


def _region(records, region, tolerance):
    if not isinstance(region, (tuple, list)) or len(region) != 4:
        raise ValidationError('Region must be [xmin, ymin, xmax, ymax] in tray millimetres.')
    xmin, ymin, xmax, ymax = [_number(x, 'Region') for x in region]
    if xmin >= xmax or ymin >= ymax:
        raise ValidationError('Region bounds are reversed or empty.')
    selected = []
    for record in records:
        lo, hi = record['bounds_mm']
        intersects = hi[0] > xmin and lo[0] < xmax and hi[1] > ymin and lo[1] < ymax
        if intersects:
            if not (lo[0] >= xmin-tolerance and hi[0] <= xmax+tolerance and lo[1] >= ymin-tolerance and hi[1] <= ymax+tolerance):
                raise ValidationError('Region cuts through a body; move its boundary to select whole objects.')
            selected.append(record)
    return selected


def _clusters(values, tolerance):
    clusters = []
    for value in sorted(values):
        if clusters and value-clusters[-1][0] <= tolerance:
            clusters[-1].append(value)
        else:
            clusters.append([value])
    return [sum(c)/len(c) for c in clusters]


def _fit_axis(observed, indices, tolerance):
    indices = sorted(set(indices))
    if len(observed) != len(indices):
        return None
    if len(observed) == 1:
        return {'origin_mm':observed[0], 'pitch_mm':None, 'single_index':indices[0], 'residual_mm':0.0}
    pitch = (observed[-1]-observed[0])/(indices[-1]-indices[0])
    if pitch <= tolerance * 4:
        return None
    origin = observed[0]-indices[0]*pitch
    residual = max(abs(obs-(origin+i*pitch)) for obs,i in zip(observed,indices))
    if residual > tolerance:
        return None
    return {'origin_mm':origin, 'pitch_mm':pitch, 'single_index':None, 'residual_mm':residual}


def _axis_index(value, fit, tolerance):
    if fit['pitch_mm'] is None:
        return fit['single_index'] if abs(value-fit['origin_mm']) <= tolerance else None
    index = round((value-fit['origin_mm'])/fit['pitch_mm'])
    return index if abs(value-(fit['origin_mm']+index*fit['pitch_mm'])) <= tolerance else None


def _grid_cells(grid):
    rows, cols = grid.get('rows'), grid.get('columns')
    if type(rows) is not int or type(cols) is not int or min(rows,cols) < 1 or rows*cols > 100000:
        raise ValidationError('Workbook grid dimensions are invalid or exceed limits.')
    if grid.get('errors'):
        raise ValidationError('Workbook contains invalid recipe cells; resolve them before mapping.')
    cells = grid.get('cells')
    if not isinstance(cells,list) or len(cells) != rows*cols:
        raise ValidationError('Workbook must include every cell, including blank holes.')
    lookup = {}
    for cell in cells:
        if not isinstance(cell,dict):
            raise ValidationError('Invalid workbook cell record.')
        r,c = cell.get('grid_row'),cell.get('grid_column')
        if type(r) is not int or type(c) is not int or not (0 <= r < rows and 0 <= c < cols):
            raise ValidationError('Workbook cell position is outside the rectangle.')
        if (r,c) in lookup or cell.get('role') not in ('sample','hole'):
            raise ValidationError('Duplicate/invalid workbook occupancy.')
        lookup[r,c] = cell
    if not any(c['role']=='sample' for c in cells):
        raise ValidationError('Workbook has no occupied sample cells.')
    return rows, cols, lookup


def _label_targets(label_records):
    """One material assignment per explicit role collection, not one per text.

    Every selected glyph in either label role receives the same direct material.
    Inferring which row a punctuation mark belongs to is neither necessary nor
    reliable, and must not obstruct this aggregate material assignment.
    """
    return [{'role':role, 'role_collection':True,
             'occurrence_ids':sorted(record['occurrence_id'] for record in records),
             'grouping_confirmed':False, 'label_text':None, 'text_association':'not_inferred',
             'material':{'mode':'base_material', 'name':'VEcoFlxBlk',
                         'vendor_material_id':'VEcoFlxBlk', 'resin_id':'11936'}}
            for role, records in sorted(label_records.items())]


def propose_grid_mapping(grid, archive_path, *, selection=None, tray_id=None, tolerance_mm=0.02, anchor=None):
    """Return review-only proposals without requesting a manual per-object ID list.

    selection may intersect region_mm, group_id (one occurrence subtree), and
    geometry_signature. Optional role_regions_mm maps row_label/column_label to
    separate aggregate rectangles. Every glyph in a selected label role shares
    direct black; text-to-row association is not inferred or required. anchor is {'cell':[row,column],
    'centroid_mm':[x,y]} for ONE visual sample anchor, not a per-ID mapping.
    Even one unique hypothesis remains unconfirmed and cannot enable a writer.
    """
    rows, cols, cells = _grid_cells(grid)
    tolerance = _number(tolerance_mm, 'Tolerance')
    inspection = inspect_geometry(archive_path, tray_id=tray_id, tolerance_mm=tolerance)
    records = inspection['bodies']; occupied = [p for p,c in cells.items() if c['role']=='sample']
    selection = {} if selection is None else selection
    if not isinstance(selection,dict) or set(selection)-{'region_mm','group_id','geometry_signature','role_regions_mm'}:
        raise ValidationError('Unknown selection; choose region_mm, group_id, geometry_signature or role_regions_mm.')
    groups = {}
    for record in records:
        groups.setdefault(record['shape_signature'], []).append(record)
    candidates = [{'geometry_signature':sig, 'body_count':len(group),
                   'bounds_mm':[[min(r['bounds_mm'][0][k] for r in group) for k in range(3)],
                                [max(r['bounds_mm'][1][k] for r in group) for k in range(3)]]}
                  for sig,group in sorted(groups.items())]
    binding = dict(inspection['binding'], workbook_sha256=grid.get('sha256'),
                   workbook_occupancy_sha256=_hash({'rows':rows,'columns':cols,'cells':[(r,c,cells[r,c]['role']) for r,c in sorted(cells)]}),
                   selection_sha256=_hash(selection), anchor_sha256=_hash(anchor), tolerance_mm=tolerance,
                   label_assignment_policy='aggregate-explicit-role-regions-v1',
                   source_layout_policy='aabb-observations-sample-centroid-validation-v1')
    report = {'schema':'gridcad.geometry-proposal.v1', 'mapping_confirmed':False, 'writer_enabled':False,
              'status':'blocked', 'tray_id':inspection['tray_id'], 'binding':binding,
              'coordinate_profile':PROFILE, 'units':'mm', 'grid_dimensions':[rows,cols],
              'expected_sample_count':len(occupied), 'candidate_groups':candidates, 'orientation_candidates':[],
              'geometry_bodies':[{'occurrence_id':r['occurrence_id'], 'centroid_mm':r['centroid_mm'],
                                  'bounds_mm':r['bounds_mm'], 'geometry_signature':r['shape_signature']} for r in records],
              'issues':[], 'layout_observations':inspection['layout_observations'],
              'source_layout_warnings':_layout_warnings(inspection['layout_observations'],{}),
              'uncertainties':inspection['limitations']+[
                  'Geometry cannot distinguish a sample from a glyph of the same shape. IDs, names and materials are not role evidence.',
                  'Confirm the aggregate sample selection, sample row/column orientation and selected label-role collections before downstream mapping.',
                  'Label text/readability and native reopen/resave/physical print validation are not established by this proposal.']}
    selected = records
    explicit_sample = any(k in selection for k in ('region_mm','group_id','geometry_signature'))
    if 'region_mm' in selection:
        selected = _region(selected, selection['region_mm'], tolerance)
    if 'group_id' in selection:
        group_id = selection['group_id']
        if not isinstance(group_id, str) or not group_id:
            raise ValidationError('Group ID must be one nonempty occurrence ID.')
        selected = [r for r in selected if group_id == r['occurrence_id'] or group_id in r['ancestors']]
    if 'geometry_signature' in selection:
        if not isinstance(selection['geometry_signature'], str):
            raise ValidationError('Geometry signature must be a string.')
        selected = [r for r in selected if r['shape_signature'] == selection['geometry_signature']]
    if not explicit_sample:
        matches = [group for group in groups.values() if len(group)==len(occupied)]
        if len(matches) != 1:
            report['issues'].append('No unique geometry group matches workbook occupancy. Select the sample region/group explicitly; glyphs will not be silently counted as samples.')
            return report
        selected = matches[0]
        report['uncertainties'].append('Sample role is only a repeated-geometry candidate, not confirmed by an explicit role mask.')
    report['selected_sample_count'] = len(selected)
    report['selection_explicit'] = explicit_sample
    if len(selected) != len(occupied):
        report['issues'].append(f'Selected {len(selected)} bodies but workbook has {len(occupied)} occupied cells; refine the aggregate sample selection.')
        return report
    if len({r['shape_signature'] for r in selected}) != 1:
        report['issues'].append('Selected bodies have differing geometry/rigid orientations; a repeated-sample group is not established.')
        return report
    if max(r['centroid_mm'][2] for r in selected)-min(r['centroid_mm'][2] for r in selected) > tolerance:
        report['issues'].append('Selected bodies are not in one XY centroid plane.')
        return report
    label_records = {}; assigned = {r['occurrence_id'] for r in selected}
    role_regions = selection.get('role_regions_mm', {})
    if not isinstance(role_regions,dict) or set(role_regions)-{'row_label','column_label'}:
        raise ValidationError('Role regions allow row_label and column_label only.')
    for role, region in role_regions.items():
        label_records[role] = _region(records, region, tolerance)
        ids = {r['occurrence_id'] for r in label_records[role]}
        if not ids or ids & assigned:
            raise ValidationError('Role regions are empty or overlap sample/label roles.')
        assigned |= ids
    roles = {r['occurrence_id']:'sample' for r in selected}
    for role, role_records in label_records.items():
        roles.update({r['occurrence_id']:role for r in role_records})
    roles.update({r['occurrence_id']:'preserved_other' for r in records if r['occurrence_id'] not in assigned})
    report['source_layout_warnings'] = _layout_warnings(inspection['layout_observations'],roles)
    report['selected_label_counts'] = {role:len(records) for role,records in sorted(label_records.items())}
    report['preserved_other_ids'] = sorted(r['occurrence_id'] for r in records if r['occurrence_id'] not in assigned)
    coincident_pair = _coincident_sample_pair(selected,tolerance)
    if coincident_pair:
        report['issues'].append('Selected sample centroids coincide within tolerance; source-cell identity is ambiguous: ' + ' / '.join(coincident_pair))
        return report
    xobs = _clusters([r['centroid_mm'][0] for r in selected], tolerance)
    yobs = _clusters([r['centroid_mm'][1] for r in selected], tolerance)
    if anchor is not None:
        if not isinstance(anchor,dict) or set(anchor) != {'cell','centroid_mm'}:
            raise ValidationError('Anchor must contain cell:[row,column] and centroid_mm:[x,y].')
        if not isinstance(anchor['cell'],list) or len(anchor['cell']) != 2 or any(type(v) is not int for v in anchor['cell']) or tuple(anchor['cell']) not in occupied:
            raise ValidationError('Anchor must identify one occupied source grid cell.')
        if not isinstance(anchor['centroid_mm'],list) or len(anchor['centroid_mm']) != 2:
            raise ValidationError('Anchor centroid must contain x,y millimetres.')
        anchor_xy = [_number(v,'Anchor coordinate') for v in anchor['centroid_mm']]
    for transpose, mr, mc in itertools.product((False,True), repeat=3):
        transform = {'transpose':transpose, 'mirror_rows':mr, 'mirror_columns':mc, 'row_offset':0, 'column_offset':0}
        expected = {transform_position(r,c,rows,cols,transform):(r,c) for r,c in occupied}
        xfit = _fit_axis(xobs, [c for r,c in expected], tolerance)
        yfit = _fit_axis(yobs, [r for r,c in expected], tolerance)
        if xfit is None or yfit is None:
            continue
        by_position = {}; invalid = False
        for record in selected:
            pos = (_axis_index(record['centroid_mm'][1], yfit, tolerance), _axis_index(record['centroid_mm'][0], xfit, tolerance))
            if None in pos or pos not in expected or pos in by_position:
                invalid = True; break
            by_position[pos] = record
        if invalid or set(by_position) != set(expected):
            continue
        if anchor is not None:
            pos = transform_position(*anchor['cell'], rows, cols, transform)
            if math.dist(by_position[pos]['centroid_mm'][:2], anchor_xy) > tolerance:
                continue
        targets = []; assignments = []; holes = []
        for (r,c), cell in sorted(cells.items()):
            pos = transform_position(r,c,rows,cols,transform)
            if cell['role']=='hole':
                holes.append({'source_grid':[r,c], 'target_grid':list(pos), 'occurrence_ids':[]})
            else:
                record = by_position[pos]
                targets.append({'role':'sample','grid_row':pos[0], 'grid_column':pos[1], 'occurrence_ids':[record['occurrence_id']]})
                assignments.append({'source_grid':[r,c], 'target_grid':list(pos), 'cell':cell.get('cell'),
                                    'occurrence_id':record['occurrence_id'], 'centroid_mm':record['centroid_mm']})
        targets.extend(_label_targets(label_records))
        report['orientation_candidates'].append({'candidate_id':_hash({'transform':transform,'binding':binding})[:20],
            'mapping_confirmed':False, 'transform':transform, 'axes':{'x':xfit,'y':yfit},
            'assignments':assignments, 'targets':targets, 'holes':holes,
            'label_grouping_issues':[], 'label_grouping_confirmed':False,
            'label_assignment_policy':'aggregate-explicit-role-regions-v1', 'label_text_association':'not_inferred'})
    if report['orientation_candidates']:
        report['status'] = 'proposal_requires_confirmation'
        if len(report['orientation_candidates']) > 1:
            report['uncertainties'].append('Multiple orientations fit; confirm one orientation or provide one visual cell/centroid anchor.')
    else:
        report['issues'].append('No axis-aligned centroid lattice matches workbook dimensions and holes under supported orientations/anchor.')
    return report
