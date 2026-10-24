"""Bounded diagnostic/unverified candidate copy adapter. Never a print authorizer.

Admission is a versioned plain-solid capability contract, not an allowlisted
archive hash. Dynamic hashes bind a witness/catalog to the bytes being checked;
they do not authenticate the witness author, vendor origin, or printer support.
Proprietary converters/catalogs must remain external to the shipped package.
"""
from __future__ import annotations

import copy
import os
import tempfile
import time
import zipfile
from decimal import Decimal
from pathlib import Path

from .core import (CHANNELS, FIELDS, ValidationError, archive_inventory,
                   audit_projects, file_hash, mapping_preview, material_summary,
                   parse_bundle, project_index, semantic_differences, sha256_bytes, strict_json,
                   validate_recipe)
from .fixture_writer import exact_json, recipe_key
from .geometry import IDENTITY, inspect_geometry, propose_grid_mapping
from .material_converter import EcoFlexMaterialProvider

CONTRACT = 'gridcad.plain-solid-diagnostic.5.119.0.v1'
VERSION = {'applicationName':'GrabCAD Print', 'applicationVersion':'5.119.0',
           'versionNumbers':{'print':{'internal':2191}, 'pj':{'internal':2190, 'external':'1.119'}}}
CHANNEL_RESINS = dict(zip(CHANNELS, ('11934','11932','11933','11936','11935','11931')))
RESIN_NAMES = ['VEcoFlxCyn','VEcoFlxMgn','VEcoFlxYlw','VEcoFlxBlk','VEcoFlxWht','VEcoFlxClr']
OPTIONAL_ADHESION_RESIN = 'VEcoContact'  # ID11937; never a CMYKWT channel.
MATERIAL_FIELDS = {'id','properties','name','printerFamily','vendorMaterialId','threeDAppearance','uiColor','metadata'}
BASE_METADATA = {'canAssignToModel':True, 'canBeHollowed':True, 'HollowForced':False,
                 'canBeCoated':True, 'canUseAsCoating':True, 'shoreA':0,
                 'IsTranslucent':False, 'canChangeMaterialCore':True}
LABEL_MANAGER = {'labels':[], 'templates':[], 'numberingOrder':[], 'labelIdToTemplateIdMap':{},
                 'templateIdToLabelIdsMap':{}, 'occurrenceIdToLabelIdsMap':{},
                 'physicalInstanceIdManager':{'occurrenceToGuidMap':{}}}
WAM_MANAGER = {'iterations':[], 'iterationIdsByOccId':{}, 'referenceModels':[],
               'featureAssociationsByOccId':{}, 'wamPropertiesByOccId':{},
               'associatedMeasurementGroups':[], 'associatedMeasurementGroupIdsByOccId':{}}
FEATURES = {'uniqueFeatures':[], 'currentStateIndices':[]}
PROFILE_CONTRACT = 'gridcad.plain-solid-techstyle-highmix.5.119.0.v1'
# Source-derived serialized identity, not a live printer/material inventory.
PROFILE_VALUES = {'pj.tray.printOnFabric':True, 'pj.tray.jobTypeId':'0', 'pj.tray.printMode':3}
# These recorded tray settings are preserved byte-for-byte semantically, never
# interpreted as permission, proof of loaded resin, or a reason to change geometry.
TRAY_CONTEXT_FIELDS = {'pj.tray.supportResins','pj.tray.materialInfo',
                      'pj.tray.inputcolorProfilesFileName','pj.tray.estimationResolution',
                      'pj.tray.calibrationData','pj.tray.minimumDelayBetweenSlicesData',
                      'pj.tray.delayedPrintingData','pj.tray.waveSmoothing','pj.tray.typeId'}
TRAY_BOOLEAN_FEATURES = {'pj.tray.printOnNet','pj.tray.useAdvancedTextureProcessing',
                         'pj.tray.useBlueNoiseProfile','pj.tray.useTransparencyProfile',
                         'pj.tray.transparentVrmlClearMaterial'}
TRAY_NULL_FEATURES = {'pj.tray.gridMaterial'}
TRAY_CHECKED_FEATURES = {'pj.tray.compressAlgoData','pj.tray.optimizedPlacementData'}
TRAY_EMPTY_FEATURES = {'pj.tray.colorProfilesData'}


def _profile_context(project):
    gender=project.get('gender'); trays=project.get('trays')
    if not isinstance(gender,dict) or not isinstance(trays,list) or len(trays)!=1:
        raise ValidationError('A single explicit printer/tray profile is required.')
    plugin=trays[0].get('pluginParameters')
    if not isinstance(plugin,dict): raise ValidationError('Tray plugin parameters must be an object.')
    if gender.get('model')=='Stratasys J850 TechStyle' and gender.get('vendor')=='PolyJet':
        allowed_gender={'id','vendor','isCustomPrinterTemplate','model','name','buildVolume','capabilities','properties','trayParameterMetadata'}
        if set(gender)-allowed_gender:
            raise ValidationError('Unknown native gender fields: '+', '.join(sorted(set(gender)-allowed_gender)))
        _string(gender.get('id'),'Gender ID')
        if 'name' in gender and (not isinstance(gender['name'],str) or len(gender['name'])>4096):
            raise ValidationError('Gender descriptive name must be a bounded string.')
        if 'buildVolume' in gender and not isinstance(gender['buildVolume'],dict):
            raise ValidationError('Gender buildVolume must be a preserved object.')
        if 'isCustomPrinterTemplate' in gender and type(gender['isCustomPrinterTemplate']) is not bool:
            raise ValidationError('Gender custom template flag must be boolean when present.')
        for key,expected in PROFILE_VALUES.items():
            value=plugin.get(key)
            valid=(type(value) in (int,Decimal) and Decimal(value).is_finite() and value==expected) if type(expected) is int else (type(value) is type(expected) and value==expected)
            if not valid:
                raise ValidationError('Unsupported TechStyle profile: '+key+' must explicitly equal '+str(expected)+'. High Speed/unknown modes are not supported.')
        if gender.get('isCustomPrinterTemplate') is not None and gender.get('isCustomPrinterTemplate') is not False:
            raise ValidationError('Custom printer templates need a separate material/geometry contract.')
        for key in ('properties','capabilities'):
            if not isinstance(gender.get(key),dict): raise ValidationError('Gender '+key+' must be an object.')
        if not isinstance(project.get('selectedPrinter'),dict):
            raise ValidationError('Serialized selectedPrinter must be an object; it is preserved, not contacted.')
        for key,expected in {'model':'Stratasys J850 TechStyle','vendor':'PolyJet','printerFamily':'PolyJet'}.items():
            if key in project['selectedPrinter'] and project['selectedPrinter'][key]!=expected:
                raise ValidationError('Explicit selectedPrinter '+key+' contradicts the recognized gender profile.')
        parameters=trays[0].get('printerParameters')
        if not isinstance(parameters,dict): raise ValidationError('Serialized printerParameters must be an object.')
        metadata=gender.get('trayParameterMetadata')
        if not isinstance(metadata,str) or len(metadata)>1024*1024 or not isinstance(strict_json(metadata),list):
            raise ValidationError('Gender trayParameterMetadata must be a bounded serialized array.')
        for key in set(PROFILE_VALUES)|{'pj.tray.resins'}:
            if key in parameters and semantic_differences(parameters[key],plugin.get(key)):
                raise ValidationError('Conflicting duplicate profile setting in printerParameters: '+key)
        for key in TRAY_BOOLEAN_FEATURES & set(plugin):
            if plugin[key] is not False: raise ValidationError('Active/unknown tray feature is unsupported: '+key)
        for key in TRAY_NULL_FEATURES & set(plugin):
            if plugin[key] is not None: raise ValidationError('Active/unknown tray material feature is unsupported: '+key)
        for key in TRAY_CHECKED_FEATURES & set(plugin):
            value=plugin[key]
            if value is not None and not (isinstance(value,dict) and value.get('checked') is False):
                raise ValidationError('Active/unknown tray composition feature is unsupported: '+key)
        for key in TRAY_EMPTY_FEATURES & set(plugin):
            if plugin[key] not in (None,{},[]): raise ValidationError('Active/unknown color profile is unsupported: '+key)
        adhesion=plugin.get('pj.tray.adhesionLayer',False)
        if type(adhesion) is not bool: raise ValidationError('Stored adhesionLayer must be boolean; no default is inserted.')
        carpet=plugin.get('pj.tray.AdhesiveCarpetMaterial')
        thickness=plugin.get('pj.tray.AdhesiveCarpetThickness')
        loaded=plugin.get('pj.tray.resins',[])
        if carpet is not None and (not isinstance(carpet,str) or carpet not in set(RESIN_NAMES)|{OPTIONAL_ADHESION_RESIN} or carpet not in loaded):
            raise ValidationError('Existing adhesive carpet must name a selected EcoFlex base resin or selected VEcoContact; support material is not an adhesive/mixer channel.')
        if thickness is not None and (type(thickness) not in (int,Decimal) or not Decimal(thickness).is_finite() or not Decimal('.03')<=thickness<=Decimal('3')):
            raise ValidationError('Stored adhesive carpet thickness must be finite 0.03..3 mm, unchanged.')
        if adhesion and (carpet is None or thickness is None):
            raise ValidationError('Enabled adhesion needs an explicit stored loaded-base material and 0.03..3 mm thickness. No defaults are inserted.')
        support=plugin.get('pj.tray.supportResins',[])
        if not isinstance(support,list) or len(support)>16 or any(not isinstance(x,str) or not x or len(x)>256 for x in support):
            raise ValidationError('Stored support resin context must be a bounded name list.')
        known={'pj.tray.resins','pj.tray.adhesionLayer','pj.tray.AdhesiveCarpetMaterial','pj.tray.AdhesiveCarpetThickness'}|set(PROFILE_VALUES)|TRAY_CONTEXT_FIELDS|TRAY_BOOLEAN_FEATURES|TRAY_NULL_FEATURES|TRAY_CHECKED_FEATURES|TRAY_EMPTY_FEATURES
        unknown=set(plugin)-known
        if unknown:
            raise ValidationError('Unrecognized active/uncategorized tray settings require review: '+', '.join(sorted(unknown)))
        return 'recognized_techstyle_highmix'
    if project.get('selectedPrinter')=={} and not {'vendor','model'} & set(gender):
        return 'internal_diagnostic'
    raise ValidationError('Project has no recognized serialized PolyJet / Stratasys J850 TechStyle / Print-on-Fabric / High Mix profile. No user-confirmation override exists.')


def _keys(value, keys, label):
    if not isinstance(value,dict) or set(value) != set(keys):
        raise ValidationError(label + ': unknown or missing fields; capability contract refused.')


def _same(value, expected, label):
    if semantic_differences(value,expected):
        raise ValidationError(label + ': unsupported value/state; capability contract refused.')


def _string(value, label):
    if not isinstance(value,str) or not value or len(value)>4096:
        raise ValidationError(label + ': expected a bounded nonempty string.')


def _stored_version(version):
    """Native loader admission uses provider internal schemas, not build labels.

    Only this explicit pair is supported; no range or migration is assumed.
    Application/PJ external build strings remain unchanged descriptive metadata.
    """
    _keys(version,{'applicationName','applicationVersion','versionNumbers'},'Stored version')
    _same(version['applicationName'],'GrabCAD Print','Application identity')
    _string(version['applicationVersion'],'Descriptive application build')
    providers=version['versionNumbers']; _keys(providers,{'print','pj'},'Provider schemas')
    _keys(providers['print'],{'internal'},'Print schema')
    _keys(providers['pj'],{'internal','external'},'PolyJet schema')
    _string(providers['pj']['external'],'Descriptive PolyJet build')
    detected=(providers['print']['internal'],providers['pj']['internal'])
    if any(type(v) not in (int,Decimal) or not Decimal(v).is_finite() for v in detected) or detected!=(2191,2190):
        raise ValidationError('Unsupported internal project schemas: detected Print '+str(detected[0])+
                              ' / PolyJet '+str(detected[1])+'. Supported pair: Print 2191 / PolyJet 2190. App build '+
                              version['applicationVersion']+' is descriptive, not a schema override; a reviewed adapter profile is required.')


def _material(material):
    """Admit only the three complete forms observed in the native fixture oracle."""
    _keys(material,MATERIAL_FIELDS,'Material')
    for key in ('id','name','vendorMaterialId','uiColor'):
        _string(material[key],'Material '+key)
    _same(material['properties'],{},'Material properties')
    _same(material['printerFamily'],'PolyJet','Material printer family')
    appearance=material['threeDAppearance']; _keys(appearance,{'r','g','b','a'},'Material appearance')
    if any(type(x) not in (int,Decimal) or not Decimal(x).is_finite() or not 0<=x<=255 for x in appearance.values()):
        raise ValidationError('Unknown material appearance representation.')
    meta=material['metadata']
    if not isinstance(meta,dict): raise ValidationError('Material metadata must be an object.')
    mode=meta.get('materialType')
    common=set(BASE_METADATA)|{'displayName','resinId','materialType'}
    extras={'color_picker':{'pickerSelectedColor'},
            'cmykwt_dm_mixer':{'Name','cmykwt_dm_used_materials_id', *('cmykwt_dm_'+f for f in FIELDS)},
            'base_material':set()}
    if mode not in extras: raise ValidationError('Unknown or implicit material mode refused.')
    _keys(meta,common|extras[mode],'Material metadata')
    for k,v in BASE_METADATA.items(): _same(meta[k],v,'Material '+k)
    _string(meta['displayName'],'Material display name')
    if mode=='base_material':
        _same((material['name'],material['vendorMaterialId'],meta['resinId']),
              ('VEcoFlxBlk','VEcoFlxBlk',11936),'Direct EcoFlexBlack identity')
    else:
        _same(meta['resinId'],2916,'Color resin identity')
        if mode=='color_picker':
            _same((material['name'],material['vendorMaterialId']),('Color','Color'),'Color Picker identity')
            _string(meta['pickerSelectedColor'],'Picker selected color')
        else:
            summary=material_summary(material)
            if summary.get('issue') or not summary.get('recipe'):
                raise ValidationError('Invalid full mixer material.')
            expected=[CHANNEL_RESINS[c] for c in CHANNELS if Decimal(summary['recipe']['channels'][c])>0]
            if summary['resin_ids']!=expected:
                raise ValidationError('Mixer resin identities/order differ from the native channel contract.')
            if material['name']!=material['vendorMaterialId'] or not material['name'].startswith('CMYKWT DM Mixer: '):
                raise ValidationError('Incomplete native mixer name/vendor identity.')
            _string(meta['Name'],'Native mixer display name')
    return material_summary(material)


class ExternalMaterialCatalog:
    """Integrity-bound EXTERNAL catalog, not authenticated vendor provenance.

    The internal caller obtains expected_sha256 independently from the actual
    native converter run. A caller-supplied file plus its own hash establishes
    only integrity, never vendor authenticity, runtime feasibility or readiness.
    No catalog or vendor code is shipped by this module.
    """
    def __init__(self, path, expected_sha256, *, producer='externally supplied native converter output'):
        self.path=Path(path)
        if self.path.stat().st_size>32*1024**2:
            raise ValidationError('External material catalog exceeds bounded size limit.')
        if not isinstance(expected_sha256,str) or len(expected_sha256)!=64 or file_hash(path)!=expected_sha256:
            raise ValidationError('External catalog differs from independently captured digest.')
        self.sha256=expected_sha256; self.producer=producer
        document=strict_json(self.path.read_bytes())
        _keys(document,{'schema','scope','version','channel_resin_ids','samples','label'},'External catalog')
        _same(document['schema'],'oracle-material-catalog.v1','Catalog schema')
        _same(document['version'],VERSION,'Catalog version')
        _same({k:str(v) for k,v in document['channel_resin_ids'].items()},CHANNEL_RESINS,'Catalog channel resin identities')
        if not isinstance(document['samples'],dict) or not document['samples'] or len(document['samples'])>100000:
            raise ValidationError('External catalog needs a bounded nonempty sample map.')
        self.samples={}
        for key,material in document['samples'].items():
            recipe=parse_bundle(key); canonical=recipe_key(recipe)
            if canonical in self.samples: raise ValidationError('Duplicate canonical external recipe.')
            self._matches(material,recipe)
            self.samples[canonical]=material
        self._document=document
        self._document_digest=sha256_bytes(exact_json(document).encode())
        self.label=document['label']
        if _material(self.label).get('mode')!='base_material':
            raise ValidationError('Label requires complete direct EcoFlexBlack material.')

    @staticmethod
    def _matches(material,recipe):
        summary=_material(material)
        if summary.get('mode')!='cmykwt_dm_mixer' or any(
                Decimal(summary['recipe']['channels'][c])!=Decimal(recipe['channels'][c]) for c in CHANNELS):
            raise ValidationError('Requested recipe has no exact native serialized material representation.')
        # Actual metadata must be numeric, not numeric-looking strings/bools or
        # caller float objects whose provenance/precision cannot be established.
        if any(type(material['metadata']['cmykwt_dm_'+f]) not in (int,Decimal) for f in FIELDS):
            raise ValidationError('Native recipe percentages must be exact parsed JSON numbers.')

    def sample(self,recipe):
        material=self.samples.get(recipe_key(recipe))
        if material is None:
            raise ValidationError('No exact externally supplied native conversion for this recipe precision. No rounding or normalization.')
        self._matches(material,recipe)
        return copy.deepcopy(material)

    def direct_black(self):
        _material(self.label)
        return copy.deepcopy(self.label)

    def check_integrity(self):
        if file_hash(self.path)!=self.sha256 or sha256_bytes(exact_json(self._document).encode())!=self._document_digest:
            raise ValidationError('External catalog changed after integrity binding.')

    def evidence(self):
        return {'sha256':self.sha256,'producer':self.producer,'version':VERSION,
                'integrity_bound':True,'vendor_origin_authenticated':False,
                'provenance':'Externally supplied; this adapter verifies integrity and structure, not vendor origin.'}


def validate_capability(inv):
    """Read-only, versioned material/geometry allowlist and contextual passthrough."""
    document=inv['project_document']; _keys(document,{'version','project'},'Archive document')
    _stored_version(document['version'])
    project,nodes,bodies=project_index(document)
    if any(node.get('children') for node in nodes.values()):
        raise ValidationError('Nested occurrence hierarchy has unvalidated material inheritance in this candidate adapter. Read-only geometry may inspect passive containers; this rejection does not establish active assembly/core features.')
    _keys(project,{'id','name','rootOccurrences','trays','selectedPrinter','activeTrayId','tessellationMap',
                  'gender','properties','manufacturingNotes','labelManager','wamManager',
                  'featureDetectionManager','projectType','manufacturingTemplateName','noBuildZones'},'Project')
    context=_profile_context(project)
    for k,v in {'properties':{},'labelManager':LABEL_MANAGER,'wamManager':WAM_MANAGER,
                'featureDetectionManager':{'detectedFeatures':[],'detectedFeatureAssociations':[]},
                'projectType':'standard','noBuildZones':[]}.items():
        _same(project[k],v,'Project '+k)
    if not isinstance(project['manufacturingNotes'],list) or (project['manufacturingTemplateName'] is not None and not isinstance(project['manufacturingTemplateName'],str)):
        raise ValidationError('Project notes/template name has unknown structural type.')
    if context=='internal_diagnostic':
        _keys(project['gender'],{'id','properties','capabilities','trayParameterMetadata'},'Gender')
        for k,v in {'properties':{},'capabilities':{},'trayParameterMetadata':'[]'}.items():
            _same(project['gender'][k],v,'Gender '+k)
        _same(project['manufacturingTemplateName'],None,'Diagnostic template')
    if len(project['trays'])!=1: raise ValidationError('Exactly one tray is supported by this candidate contract.')
    tray=project['trays'][0]
    _keys(tray,{'id','properties','name','trayBodies','printerParameters','pluginParameters',
                'composerGenerated','manuallyRenamed','requireSnapshot'},'Tray')
    _same(project['activeTrayId'],tray['id'],'Active tray')
    for k,v in {'properties':{},'composerGenerated':False}.items(): _same(tray[k],v,'Tray '+k)
    if type(tray['manuallyRenamed']) is not bool or type(tray['requireSnapshot']) is not bool:
        raise ValidationError('Tray descriptive/snapshot flags must be explicit booleans.')
    if context=='internal_diagnostic':
        _same(tray['printerParameters'],{},'Diagnostic printer parameters')
        _keys(tray['pluginParameters'],{'pj.tray.resins'},'Diagnostic tray plugin parameters')
        if len(tray['pluginParameters'].get('pj.tray.resins',[]))!=6:
            raise ValidationError('Internal diagnostic fixtures require the original six-resin test profile.')
    resins=tray['pluginParameters'].get('pj.tray.resins')
    if (not isinstance(resins,list) or len(resins) not in (6,7) or any(not isinstance(x,str) for x in resins) or
            len(set(resins))!=len(resins) or not set(RESIN_NAMES)<=set(resins) or
            not set(resins)<=set(RESIN_NAMES)|{OPTIONAL_ADHESION_RESIN}):
        raise ValidationError('Tray needs six unique EcoFlex mixing resins plus optional VEcoContact adhesion resin only; support remains separate and order is preserved.')
    if not 0<len(nodes)<=20000: raise ValidationError('Candidate object count exceeds bound or is empty.')
    tess=project['tessellationMap']
    if not isinstance(tess,dict) or len(tess)!=len(nodes):
        raise ValidationError('Exactly one independent tessellation per leaf is required.')
    used_tess=set()
    defaults={'rotationLock':{'x':False,'y':False,'z':False},'separability':True,
              'scale.factor':{'x':100,'y':100,'z':100},'info.units':'MM'}
    properties={k:{'isDefault':False,'isLocked':False,'isReadOnly':False,'value':v} for k,v in defaults.items()}
    occurrence_fields={'id','properties','children','dependencies','transform','name','filePath','fileSize',
                       'tessellationKey','extension','loadStatus','occurrenceType','occurrenceScaling',
                       'flags','instanceCount','units','rootScaling','sourceProperties','featureManager','material'}
    for oid,node in nodes.items():
        _keys(node,occurrence_fields,'Occurrence '+oid)
        for k,v in {'properties':properties,'children':[],'dependencies':[],'transform':IDENTITY,
                    'extension':'stl','loadStatus':'loaded','occurrenceType':'part','occurrenceScaling':Decimal('.001'),
                    'flags':0,'instanceCount':0,'units':'MM','rootScaling':IDENTITY,
                    'sourceProperties':{'numberOfColors':0},'featureManager':FEATURES}.items():
            _same(node[k],v,'Occurrence '+oid+' '+k)
        for k in ('name','filePath','tessellationKey'): _string(node[k],'Occurrence '+k)
        if type(node['fileSize']) is not int or node['fileSize']<0: raise ValidationError('Unknown source file size.')
        refs=bodies.get(oid,[])
        if len(refs)!=1: raise ValidationError('Each flat leaf must have exactly one actual body.')
        body=refs[0][1]
        _keys(body,{'id','properties','occurrence','transform','material','rootOccurrenceId','composeTransform'},'Tray body '+oid)
        _same(body['properties'],{},'Tray-body properties'); _same(body['rootOccurrenceId'],oid,'Root occurrence')
        _material(node['material']); _material(body['material'])
        _same(node['material'],body['material'],'Desired/actual material mismatch for '+oid)
        key=node['tessellationKey']
        if key not in tess or key in used_tess: raise ValidationError('Missing/aliased tessellation reference.')
        used_tess.add(key); t=tess[key]
        _keys(t,{'id','properties','name','colorModes','errors','representations'},'Tessellation')
        for k,v in {'properties':{},'colorModes':[],'errors':[]}.items(): _same(t[k],v,'Tessellation '+k)
        _keys(t['representations'],{'stl'},'Tessellation representation')
        _same(t['representations']['stl'],node['filePath'],'Geometry reference consistency')
    return project,nodes,bodies


def candidate_readiness(source):
    """Read-only structural gate for a UI; never a printability certification.

    This does not validate workbook mapping, role masks, user review, or final
    preservation. The copy function independently repeats every applicable check.
    """
    detected_version=None
    try:
        inv=archive_inventory(source)
        if isinstance(inv['project_document'],dict): detected_version=copy.deepcopy(inv['project_document'].get('version'))
        project,_,_=validate_capability(inv)
        inspect_geometry(source,tray_id=project['trays'][0]['id'])
        context=_profile_context(project)
        return {'candidate_allowed':context=='recognized_techstyle_highmix',
                'profile_context':context,'project_sha256':inv['sha256'],
                'contract':PROFILE_CONTRACT if context=='recognized_techstyle_highmix' else CONTRACT,
                'detected_version':copy.deepcopy(inv['project_document']['version']),
                'supported_internal_schemas':{'print':2191,'pj':2190},
                'print_ready':False,'gui_validated':False,'native_recomposition_validated':False,
                'reason':('Recognized serialized profile; mapping/role review and output preservation are still required.'
                          if context=='recognized_techstyle_highmix' else 'Internal no-printer diagnostic fixture; not enabled for public candidate download.')}
    except (ValidationError,OSError) as exc:
        return {'candidate_allowed':False,'print_ready':False,'reason':str(exc),
                'detected_version':detected_version,'supported_internal_schemas':{'print':2191,'pj':2190}}


def _mapping_evidence(grid,source,mapping,witness,inv):
    _keys(witness,{'schema','selection','anchor','tolerance_mm','candidate_id','geometry_binding','objects'},'Mapping witness')
    _same(witness['schema'],'gridcad.candidate-witness.v1','Witness schema')
    selection=witness['selection']
    if not isinstance(selection,dict) or not any(k in selection for k in ('region_mm','geometry_signature','group_id')):
        raise ValidationError('Independent aggregate sample selection is required.')
    if set(selection.get('role_regions_mm',{}))!={'row_label','column_label'}:
        raise ValidationError('Both complete row-label and column-label aggregate masks are required.')
    inspected=inspect_geometry(source,tray_id=mapping['tray_id'],tolerance_mm=witness['tolerance_mm'])
    _same(inspected['binding'],witness['geometry_binding'],'Stale geometry/transform witness')
    proposed=propose_grid_mapping(grid,source,selection=selection,anchor=witness['anchor'],
                                 tray_id=mapping['tray_id'],tolerance_mm=witness['tolerance_mm'])
    candidates=[c for c in proposed['orientation_candidates'] if c['candidate_id']==witness['candidate_id']]
    if len(candidates)!=1: raise ValidationError('Chosen orientation is missing/ambiguous/stale.')
    candidate=candidates[0]
    if candidate['label_grouping_issues']: raise ValidationError('Geometry label grouping is unresolved.')
    _same(mapping['transform'],candidate['transform'],'Geometry-derived orientation')
    def target_key(t):
        return (t['role'],tuple(sorted(t['occurrence_ids'])),t.get('grid_row'),t.get('grid_column'))
    intended=[t for t in mapping['targets'] if t['role']!='preserved_other']
    if sorted(map(target_key,intended))!=sorted(map(target_key,candidate['targets'])):
        raise ValidationError('Mapping differs from independently recomputed geometry cell/label groups.')
    project,nodes,bodies=project_index(inv['project_document'])
    objects=witness['objects']
    if not isinstance(objects,list) or len(objects)!=len(nodes): raise ValidationError('Independent all-object role manifest is incomplete.')
    records={r['occurrence_id']:r for r in inspected['bodies']}; byid={}
    assigned={oid:t for t in candidate['targets'] for oid in t['occurrence_ids']}
    for obj in objects:
        _keys(obj,{'id','role','body_id','geometry_member','geometry_sha256','body_transform',
                   'compose_transform','occurrence_transform','grid_row','grid_column'},'Independent witness object')
        oid=obj['id']
        if oid in byid or oid not in nodes: raise ValidationError('Independent role manifest duplicates or invents an object.')
        byid[oid]=obj; node=nodes[oid]; body=bodies[oid][0][1]; record=records[oid]
        expected_role=assigned[oid]['role'] if oid in assigned else 'preserved_other'
        _same(obj['role'],expected_role,'Independent required role '+oid)
        for key,value in {'body_id':body['id'],'geometry_member':record['member'],
                          'geometry_sha256':record['mesh_sha256'],'body_transform':body['transform'],
                          'compose_transform':body['composeTransform'],'occurrence_transform':node['transform']}.items():
            _same(obj[key],value,'Independent geometry/placement '+oid+' '+key)
        if expected_role=='sample':
            _same([obj['grid_row'],obj['grid_column']],
                  [assigned[oid]['grid_row'],assigned[oid]['grid_column']],'Independent physical cell '+oid)
    return proposed


def mapping_from_geometry_review(grid,source,*,selection,candidate_id,anchor=None,
                                 tolerance_mm=.02,reviewed=False):
    """Build a read-only mapping from explicitly reviewed aggregate role masks.

    reviewed means the user reviewed orientation, complete sample/label regions,
    and preservation of everything outside those masks. It does NOT attest to
    version, printer feasibility, native composition, or physical printability.
    Geometry is reread; caller-supplied IDs/positions/material IDs are not used.
    """
    if reviewed is not True:
        raise ValidationError('Review the complete sample/label masks, orientation and preservation of all unselected objects before creating a candidate.')
    inv=archive_inventory(source); project,nodes,bodies=validate_capability(inv)
    inspection=inspect_geometry(source,tray_id=project['trays'][0]['id'],tolerance_mm=tolerance_mm)
    proposal=propose_grid_mapping(grid,source,selection=selection,anchor=anchor,
                                 tray_id=project['trays'][0]['id'],tolerance_mm=tolerance_mm)
    candidates=[c for c in proposal['orientation_candidates'] if c['candidate_id']==candidate_id]
    if len(candidates)!=1: raise ValidationError('Reviewed geometry candidate is stale or missing; review the refreshed preview.')
    candidate=candidates[0]
    mapping={'schema':'gridcad.mapping.v1','mapping_confirmed':True,'tray_id':proposal['tray_id'],
             'transform':candidate['transform'],'channel_resin_ids':CHANNEL_RESINS.copy(),
             'label_material':{'mode':'base_material','name':'VEcoFlxBlk','vendor_material_id':'VEcoFlxBlk','resin_id':'11936'},
             'targets':candidate['targets']}
    targets={oid:t for t in candidate['targets'] for oid in t['occurrence_ids']}
    objects=[]
    for record in inspection['bodies']:
        oid=record['occurrence_id']; target=targets.get(oid,{}); body=bodies[oid][0][1]
        objects.append({'id':oid,'role':target.get('role','preserved_other'),
                        'grid_row':target.get('grid_row'),'grid_column':target.get('grid_column'),
                        'body_id':body['id'],'geometry_member':record['member'],'geometry_sha256':record['mesh_sha256'],
                        'body_transform':body['transform'],'compose_transform':body['composeTransform'],
                        'occurrence_transform':nodes[oid]['transform']})
    witness={'schema':'gridcad.candidate-witness.v1','selection':selection,'anchor':anchor,
             'tolerance_mm':tolerance_mm,'candidate_id':candidate_id,
             'geometry_binding':inspection['binding'],'objects':objects}
    checked_geometry=_mapping_evidence(grid,source,mapping,witness,inv)
    return {'source_layout_warnings':copy.deepcopy(checked_geometry.get('source_layout_warnings',[])),
            'mapping':mapping,'witness':witness,'role_evidence':'User-reviewed aggregate geometry regions; label text/semantic roles are not inferred.',
            'preserved_unselected_objects':len(nodes)-len(targets),'print_ready':False}


def write_reviewed_candidate_copy(grid,source,output,*,selection,candidate_id,
                                  assignment_policy,reviewed=False,anchor=None,tolerance_mm=.02):
    """UI entry point: fresh real-profile gate, reviewed mapping, own converter.

    Internal no-printer diagnostic fixtures are never downloadable through this
    entry point. No caller version/resin/catalog/feasibility flags are accepted.
    """
    workflow_start=time.perf_counter()
    readiness=candidate_readiness(source)
    if not readiness['candidate_allowed']:
        raise ValidationError(readiness['reason'])
    profile_gate_seconds=time.perf_counter()-workflow_start
    mapping_start=time.perf_counter()
    prepared=mapping_from_geometry_review(grid,source,selection=selection,candidate_id=candidate_id,
                                         anchor=anchor,tolerance_mm=tolerance_mm,reviewed=reviewed)
    reviewed_mapping_seconds=time.perf_counter()-mapping_start
    if prepared['witness']['geometry_binding']['archive_sha256']!=readiness['project_sha256']:
        raise ValidationError('Source changed since the fresh profile check; refresh and review it again.')
    result=write_candidate_copy(grid,source,prepared['mapping'],prepared['witness'],EcoFlexMaterialProvider(),
                                output,assignment_policy=assignment_policy)
    result['role_evidence']=prepared['role_evidence']
    result['timings']['public_profile_gate_seconds']=profile_gate_seconds
    result['timings']['public_reviewed_mapping_seconds']=reviewed_mapping_seconds
    result['timings']['public_total_seconds']=time.perf_counter()-workflow_start
    return result


def write_candidate_copy(grid,source,mapping,witness,material_provider,output,*,assignment_policy):
    """Write an atomic no-overwrite candidate copy, with no print-ready branch.

    overwrite_targets explicitly replaces conflicts; fill_uncompleted requires
    explicit pending and completed IDs partitioning all mapped samples. Exact current requested
    matches are skipped in either policy. Default/color-picker is never completion.
    """
    start=time.perf_counter(); timings={}; source=Path(source); output=Path(output)
    if output.exists() or output.is_symlink() or output.resolve()==source.resolve():
        raise ValidationError('Copy output must be a new path, never the input.')
    if type(material_provider) not in (ExternalMaterialCatalog,EcoFlexMaterialProvider):
        raise ValidationError('A supported versioned full-material provider is required; raw patches/catalog dictionaries and arbitrary provider subclasses are refused.')
    material_provider.check_integrity()
    inv=archive_inventory(source); document=inv['project_document']; validate_capability(inv)
    timings['input_inventory_admission_seconds']=time.perf_counter()-start
    phase=time.perf_counter()
    if mapping.get('channel_resin_ids')!=CHANNEL_RESINS: raise ValidationError('Mapping channel identities differ from native catalog.')
    report=mapping_preview(grid,source,mapping)
    if not report['input_validation_passed']: raise ValidationError('Preview has unresolved workbook/mapping issues: '+str(report['issues'][:3]))
    geometry_evidence=_mapping_evidence(grid,source,mapping,witness,inv)
    if not isinstance(assignment_policy,dict): raise ValidationError('An explicit assignment policy is required.')
    mode=assignment_policy.get('mode')
    if mode=='overwrite_targets':
        _keys(assignment_policy,{'mode'},'Assignment policy'); completed=set(); pending=None
    elif mode=='fill_uncompleted':
        _keys(assignment_policy,{'mode','completed_occurrence_ids','pending_occurrence_ids'},'Assignment policy')
        for key in ('completed_occurrence_ids','pending_occurrence_ids'):
            ids=assignment_policy[key]
            if not isinstance(ids,list) or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):
                raise ValidationError('Pending/completed samples must be explicit unique occurrence IDs.')
        completed=set(assignment_policy['completed_occurrence_ids'])
        pending=set(assignment_policy['pending_occurrence_ids'])
    else: raise ValidationError('Choose overwrite_targets or fill_uncompleted explicitly.')
    assignments={oid:a for a in report['assignments'] for oid in a['occurrence_ids']}
    sample_ids={oid for oid,a in assignments.items() if a['role']=='sample'}
    if not completed<=sample_ids: raise ValidationError('Completed IDs must identify mapped samples, not labels/unmatched objects.')
    if pending is not None and (completed & pending or completed | pending != sample_ids):
        raise ValidationError('Explicit pending and completed IDs must form a disjoint complete sample partition; unclassified conflicts cannot be overwritten.')
    changed=copy.deepcopy(document); _,nodes,bodies=project_index(changed); changed_ids=[]; skipped=[]
    for oid,assignment in assignments.items():
        current=next(c for c in assignment['current'] if c['occurrence_id']==oid)
        if assignment['role']=='sample':
            recipe=assignment['recipe']
            # Revalidate caller-provided grid data, never trust precomputed totals.
            validate_recipe([recipe['channels'][c] for c in CHANNELS])
            try:
                material=material_provider.sample(recipe)
            except ValidationError as exc:
                raise ValidationError(f"Workbook cell {assignment.get('cell', 'unknown')} (sample {oid}): {exc}") from exc
        else: material=material_provider.direct_black()
        if assignment['role']=='sample': ExternalMaterialCatalog._matches(material,assignment['recipe'])
        elif _material(material).get('mode')!='base_material':
            raise ValidationError('Label provider did not return complete direct EcoFlexBlack.')
        # Exact completion also covers vendor-derived display/appearance fields.
        # Native converters assign fresh random IDs, which are not color semantics.
        old_semantics={k:v for k,v in nodes[oid]['material'].items() if k!='id'}
        new_semantics={k:v for k,v in material.items() if k!='id'}
        if current['serialized_request_matches'] and not semantic_differences(old_semantics,new_semantics):
            skipped.append(oid); continue
        if oid in completed:
            raise ValidationError('Explicitly completed sample '+oid+' does not match the complete native material in both desired and actual state; resolve or choose explicit overwrite.')
        nodes[oid]['material']=copy.deepcopy(material)
        bodies[oid][0][1]['material']=copy.deepcopy(material); changed_ids.append(oid)
    timings['mapping_material_assignment_seconds']=time.perf_counter()-phase
    before=copy.deepcopy(document); after=copy.deepcopy(changed)
    for doc in (before,after):
        _,ns,bs=project_index(doc)
        for oid in changed_ids:
            ns[oid].pop('material'); bs[oid][0][1].pop('material')
    if semantic_differences(before,after): raise ValidationError('Unexpected non-material mutation.')
    phase=time.perf_counter(); fd,temp=tempfile.mkstemp(prefix='.gridcad-candidate-',suffix='.print',dir=output.parent); os.close(fd)
    try:
        with zipfile.ZipFile(source) as src,zipfile.ZipFile(temp,'w') as dst:
            dst.comment=src.comment
            for entry in src.infolist():
                dst.writestr(entry,exact_json(changed).encode('utf-8') if entry.filename=='project.json' else src.read(entry))
        audit=audit_projects(source,temp)
        if audit['added_archive_entries'] or audit['removed_archive_entries'] or audit['changed_nonproject_payloads']:
            raise ValidationError('Archive preservation failed.')
        saved=archive_inventory(temp); validate_capability(saved)
        if semantic_differences(changed,saved['project_document']): raise ValidationError('Exact serialized material/project readback failed.')
        verified=mapping_preview(grid,temp,mapping)
        if not all(c['serialized_request_matches'] for a in verified['assignments'] for c in a['current']):
            raise ValidationError('Saved copy does not match every requested sample/label material.')
        material_provider.check_integrity()
        if file_hash(source)!=inv['sha256']:
            raise ValidationError('Input changed during copy; no output published.')
        with open(temp,'rb') as f: os.fsync(f.fileno())
        os.link(temp,output)  # Atomic create, never replace, including publication races.
        timings['archive_write_preservation_readback_seconds']=time.perf_counter()-phase
        timings['total_seconds']=time.perf_counter()-start
        context=_profile_context(document['project'])
        return {'status':'DIAGNOSTIC_CANDIDATE_COPY_NOT_PRINT_READY' if context=='internal_diagnostic' else 'UNVERIFIED_CANDIDATE_COPY',
                'contract':CONTRACT if context=='internal_diagnostic' else PROFILE_CONTRACT,
                'profile_context':_profile_context(document['project']),
                'detected_version':copy.deepcopy(document['version']),
                'supported_internal_schemas':{'print':2191,'pj':2190},
                'output':str(output),'source_sha256':inv['sha256'],'output_sha256':file_hash(output),
                'changed_objects':len(changed_ids),'skipped_exact_matches':len(skipped),
                'changed_occurrence_ids':changed_ids,'skipped_occurrence_ids':skipped,
                'preserved_unmatched_objects':len(nodes)-len(assignments),'assignment_policy':assignment_policy,
                'geometry_mapping_recomputed_passed':True,'nonmaterial_preservation_passed':True,
                'source_layout_warnings':copy.deepcopy(geometry_evidence.get('source_layout_warnings',[])),
                'material_provider':material_provider.evidence(),'timings':timings,'audit':audit,
                'vendor_loader_reopen_validated':False,'gui_validated':False,'production_write':False,'print_ready':False,
                'gate':('No printer selected. Diagnostic only; this is not a printable project.' if context=='internal_diagnostic' else 'Recognized serialized TechStyle/Fabric/High Mix profile only; inspect and reopen/recompose in GrabCAD before use.')+' Actual loaded resins, GUI reopen, native recomposition and print readiness are not verified.'}
    finally:
        os.unlink(temp)
