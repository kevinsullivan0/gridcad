"""INTERNAL controlled-fixture copy proof. Not a general or production adapter."""
import copy, json, os, tempfile, zipfile
from decimal import Decimal
from pathlib import Path
from .core import *

APPROVED_CAPABILITY_SHA256 = "854fdb9851b1ccd89754f698d057121c7a678da82518de2f68bdaa9e6f325698"  # Set only after independent controlled-fixture review.

def exact_json(value):
    """Preserve JSON numbers as numbers without binary-float conversion."""
    if value is None:return 'null'
    if type(value) is bool:return 'true' if value else 'false'
    if isinstance(value,str):return json.dumps(value,ensure_ascii=False)
    if type(value) is int:return str(value)
    if isinstance(value,Decimal):
        if not value.is_finite():raise ValidationError('Nonfinite JSON number.')
        return str(value)
    if isinstance(value,list):return '['+','.join(exact_json(v) for v in value)+']'
    if isinstance(value,dict):return '{'+','.join(json.dumps(k)+':'+exact_json(v) for k,v in value.items())+'}'
    raise ValidationError('Unsupported JSON type for exact writer.')

def recipe_key(recipe):
    def canonical(x):
        s=format(Decimal(x),'f')
        return s.rstrip('0').rstrip('.') if '.' in s else s
    return '|'.join(canonical(recipe['channels'][c]) for c in CHANNELS)

def write_fixture_copy(grid,source,mapping,capability,output):
    """Only a manifest-bound model-contract fixture can enter this path."""
    source=Path(source);output=Path(output)
    if output.exists() or output.is_symlink() or output.resolve()==source.resolve():
        raise ValidationError('Copy output must be a new path, never the input.')
    if APPROVED_CAPABILITY_SHA256 is None or sha256_bytes(exact_json(capability).encode())!=APPROVED_CAPABILITY_SHA256:
        raise ValidationError('Capability is not the explicitly approved internal fixture contract.')
    if capability.get('scope')!='CONTROLLED_FIXTURE_ONLY_NOT_PRINT_READY':
        raise ValidationError('Not an explicit controlled fixture capability.')
    inv=archive_inventory(source);doc=inv['project_document']
    if inv['sha256']!=capability.get('source_sha256'):raise ValidationError('Input is not the exact controlled baseline. General projects are unsupported.')
    if doc['version']!=capability.get('version'):raise ValidationError('Unsupported project version.')
    p,occ,bodies=project_index(doc)
    if p.get('selectedPrinter') != {}:raise ValidationError('This fixture path must not target a printer.')
    report=mapping_preview(grid,source,mapping)
    if not report['input_validation_passed']:raise ValidationError('Preview has unresolved input/mapping issues.')
    expected=capability.get('objects',[]);byid={x['id']:x for x in expected}
    if len(byid)!=len(expected) or set(byid)!=set(occ):raise ValidationError('Independent fixture object manifest incomplete or duplicated.')
    assigned={oid:a for a in report['assignments'] for oid in a['occurrence_ids']}
    if set(assigned)!=set(byid):raise ValidationError('Every required sample and label glyph must be assigned exactly once.')
    tray=[t for t in p['trays'] if t['id']==mapping['tray_id']][0]
    if set((tray.get('pluginParameters') or {}).get('pj.tray.resins',[]))!=set(capability['tray_resin_names']):
        raise ValidationError('Selected tray resin identities differ from the verified fixture.')
    if mapping['channel_resin_ids']!=capability['channel_resin_ids']:raise ValidationError('Channel resin identity mismatch.')
    for oid,e in byid.items():
        node=occ[oid];a=assigned[oid];refs=[b for t,b in bodies.get(oid,[]) if t['id']==tray['id']]
        if node.get('children') or node.get('occurrenceType')!='part' or len(refs)!=1:
            raise ValidationError('Only simple independently addressed leaf parts are supported.')
        b=refs[0]
        if node.get('featureManager')!={'uniqueFeatures':[],'currentStateIndices':[]}:
            raise ValidationError('Features/core/coating/hollow/assemblies are not supported.')
        if a['role']!=e['role']:raise ValidationError('Object role differs from independent fixture manifest.')
        if a['role']=='sample':
            if a['target_grid']!=[e['grid_row'],e['grid_column']]:raise ValidationError('Sample ID/grid mapping mismatch.')
            # Native Transform serialization is row-major: translation indices 3/7/11.
            m=b.get('transform',[])
            if len(m)!=16 or any(Decimal(str(m[i]))!=Decimal(v) for i,v in zip((3,7,11),e['translation_m'])):
                raise ValidationError('Independent physical placement witness differs from actual tray-body transform.')
        if b['id']!=e['body_id']:raise ValidationError('Actual tray body identity differs from witness.')
    changed=copy.deepcopy(doc);cp,co,cb=project_index(changed)
    for oid,a in assigned.items():
        if a['role']=='sample':
            key=recipe_key(a['recipe']);material=capability['materials_by_recipe'].get(key)
            if material is None:raise ValidationError('Recipe has no exact externally verified vendor material object. No approximation.')
            summary=material_summary(material)
            if summary['mode']!='cmykwt_dm_mixer' or not summary['recipe'] or any(Decimal(summary['recipe']['channels'][c])!=Decimal(a['recipe']['channels'][c]) for c in CHANNELS):
                raise ValidationError('External material catalog recipe/mode mismatch.')
            if set(summary['resin_ids'])!=set(a['expected_nonzero_resin_ids']):raise ValidationError('External material catalog resin mismatch.')
        else:
            material=capability['label_material'];summary=material_summary(material)
            if summary['mode']!='base_material' or summary['vendor_material_id']!='VEcoFlxBlk' or str(summary.get('resin_id'))!='11936':
                raise ValidationError('External direct-black material is invalid.')
        if any(k in material.get('metadata',{}) for k in ('pickerSelectedColor','pantone_materials','dmCategoryName')):
            raise ValidationError('Stale conflicting material mode metadata.')
        co[oid]['material']=copy.deepcopy(material)
        for t,b in cb[oid]:
            if t['id']==tray['id']:b['material']=copy.deepcopy(material)
    # Independent semantic preservation: remove precisely the approved material leaves.
    stripped_before=copy.deepcopy(doc);stripped_after=copy.deepcopy(changed)
    for d in (stripped_before,stripped_after):
        _,o,bs=project_index(d)
        for oid in assigned:
            o[oid].pop('material',None)
            for t,b in bs[oid]:
                if t['id']==tray['id']:b.pop('material',None)
    if semantic_differences(stripped_before,stripped_after):raise ValidationError('Unexpected non-material changes.')
    fd,temp=tempfile.mkstemp(prefix='.gridcad-fixture-',suffix='.zip',dir=output.parent);os.close(fd)
    try:
        with zipfile.ZipFile(source) as src,zipfile.ZipFile(temp,'w') as dst:
            dst.comment=src.comment
            for info in src.infolist():
                dst.writestr(info,exact_json(changed).encode('utf-8') if info.filename=='project.json' else src.read(info))
        audit=audit_projects(source,temp)
        if audit['added_archive_entries'] or audit['removed_archive_entries'] or audit['changed_nonproject_payloads']:
            raise ValidationError('Archive preservation failed.')
        verified=mapping_preview(grid,temp,mapping)
        if not all(c['serialized_request_matches'] for a in verified['assignments'] for c in a['current']):
            raise ValidationError('Saved copy did not preserve requested materials.')
        if file_hash(source)!=capability['source_sha256']:
            raise ValidationError('Source changed during copy; no output published.')
        # Publish without replacing an existing destination, even after a race.
        os.link(temp,output)
        return {'status':'CONTROLLED_FIXTURE_COPY_ONLY','output':str(output),'output_sha256':file_hash(output),
                'assigned_objects':len(assigned),'nonmaterial_preservation_passed':True,
                'independent_fixture_mapping_passed':True,'vendor_loader_reopen_validated':False,
                'gui_validated':False,'print_ready':False,'audit':audit}
    finally:
        os.unlink(temp)
