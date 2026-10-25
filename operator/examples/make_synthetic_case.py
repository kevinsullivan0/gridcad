"""Generate tiny, invented DO_NOT_PRINT fixtures. These are not native evidence."""
import copy
from pathlib import Path
import struct
import sys
import zipfile
from decimal import Decimal as D

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gridcad_operator.operator import (SOURCE_VERSION, PLACEMENT_PROFILE, MATERIAL_PROFILE,
                                      exact_json, digest, fingerprint)
from gridcad_operator.material_converter import EcoFlexMaterialProvider


def affine(scale=1, x=0, y=0, z=0):
    return [scale,0,0,x, 0,scale,0,y, 0,0,scale,z, 0,0,0,1]


def quarter(x=0, y=0):
    return [0,D('.1'),0,x, -D('.1'),0,0,y, 0,0,D('.1'),0, 0,0,0,1]


def create_case(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    project_path, book_path = folder/'DO_NOT_PRINT.print', folder/'DO_NOT_PRINT.xlsx'
    provider = EcoFlexMaterialProvider()
    native_black = provider.direct_black()
    native_black['id'] = 'invented-shared-black-material'
    native_black['metadata'].update(isSuitableForCore=True, isSuitableForColorCore=True,
                                  defaultGridStyle='Standard', invented_extra={'keep':[1,True,'synthetic']})
    picker = {'id':'placeholder','properties':{},'name':'rgba,210,213,207,255',
              'vendorMaterialId':'rgba,210,213,207,255','printerFamily':'PolyJet',
              'threeDAppearance':{'r':210,'g':213,'b':207,'a':255},'uiColor':'rgb(210,213,207)',
              'metadata':{'materialType':'color_picker','pickerSelectedColor':'synthetic-gray'}}
    properties = {'info.units':{'value':'CM'}, 'scale.factor':{'value':{'x':100,'y':100,'z':100}},
                  'orientation':{'value':[0,1,0,0, -1,0,0,0, 0,0,1,0, 0,0,0,1]}}
    def node(oid, material=None, children=None, root=False):
        result = {'id':oid,'name':oid,'children':children or [], 'units':'CM','occurrenceScaling':D('.001'),
                  'rootScaling':affine(D('.1')), 'transform':affine(D('.1') if root else 1),
                  'properties':copy.deepcopy(properties),'featureManager':{'uniqueFeatures':[], 'currentStateIndices':[]},
                  'tessellationKey':'invented-mesh','unrelated':{'retain':[1,'synthetic',None]}}
        if material: result['material'] = copy.deepcopy(material)
        return result
    def body(oid, material, row=0, col=0):
        return {'id':'body-'+oid, 'occurrence':oid,'material':copy.deepcopy(material),
                'transform':quarter(D(row)*D('.012'),-D(col)*D('.012')),
                'composeTransform':affine(), 'rootOccurrenceId':'assembly',
                'properties':{'representation':{'value':'stl'},'threeDAppearance':{
                    'value':{**material['threeDAppearance'],'invented_uniforms':{'keep':True}}}}}
    parts, bodies, entries = [], [], []
    recipes = [['2','0','0','0','98','0'], ['2','0','0','0','0','98'],
               ['0','0','2','0','98','0'], ['0','0','2','0','0','98']]
    for row in range(2):
        for col in range(2):
            oid = 'sample-'+str(row)+'-'+str(col)
            material = copy.deepcopy(picker); material['id'] = 'material-'+oid
            parts.append(node(oid, material)); bodies.append(body(oid, material,row,col))
            entries.append({'cell':chr(ord('D')+col)+str(row+4),'occurrence_id':oid,
                'tray_body_id':'body-'+oid,'source_material_sha256':fingerprint(material),
                'expected_percentages':recipes[row*2+col], 'action':'replace_uniform_color_picker'})
    glyphs, labels = [], []
    for i in range(2):
        oid = 'glyph-'+str(i)
        glyphs.append(node(oid, native_black)); bodies.append(body(oid,native_black))
        labels.append({'occurrence_id':oid,'tray_body_id':'body-'+oid,
                       'source_material_sha256':fingerprint(native_black),'action':'preserve_native_black'})
    unrelated = copy.deepcopy(picker); unrelated['id']='unrelated-material'
    parts.append(node('unrelated',unrelated)); bodies.append(body('unrelated',unrelated))
    parts.append(node('glyph-container',children=glyphs))
    doc = {'version':copy.deepcopy(SOURCE_VERSION), 'project':{'id':'invented-project',
        'rootOccurrences':[node('assembly',children=parts,root=True)],
        'trays':[{'id':'invented-tray','trayBodies':bodies,'invented_parameters':{'retain':True}}],
        'labelManager':{'physicalInstanceIdManager':{'occurrenceToGuidMap':{'unrelated':'invented-native-guid'}}},
        'tessellationMap':{'invented-mesh':{'representations':{'stl':'mesh/example.stl'}}},
        'invented_notes':['DO NOT PRINT. No native provenance.']}}
    triangle = b'DO_NOT_PRINT_SYNTHETIC'.ljust(80,b'\0') + struct.pack('<I',1) + struct.pack('<12fH',0,0,1,0,0,0,1,0,0,0,1,0,0)
    with zipfile.ZipFile(project_path,'x',compression=zipfile.ZIP_DEFLATED) as z:
        z.comment=b'DO_NOT_PRINT_SYNTHETIC'
        z.writestr('project.json',exact_json(doc))
        z.writestr('mesh/example.stl',triangle)
        z.writestr('opaque.bin',b'untouched\x00\xffsynthetic')
    cells = ''.join('<row r="'+str(r)+'">'+''.join(
        '<c r="'+chr(ord('D')+c)+str(r)+'" t="inlineStr"><is><t>'+' / '.join(recipes[(r-4)*2+c])+'</t></is></c>'
        for c in range(2))+'</row>' for r in (4,5))
    with zipfile.ZipFile(book_path,'x') as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Recipes" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+cells+'</sheetData></worksheet>')
    plan = {'plan_version':1,'archive_sha256':digest(project_path),'workbook_sha256':digest(book_path),
            'source_version':copy.deepcopy(SOURCE_VERSION),'placement_profile':PLACEMENT_PROFILE,
            'material_profile':MATERIAL_PROFILE,'allow_unverified_material_profile':True,
            'review':{'geometry_and_labels_confirmed':True,'evidence':'INVENTED TEST ONLY: known synthetic 2x2 layout, no glyph/native evidence.'},
            'sheet':'Recipes','range':'D4:E5','formula_cache_policy':'reject',
            'axes':{'row_axis':'x','row_direction':1,'column_axis':'y','column_direction':-1,
                    'pitch_mm':'12','cluster_tolerance_mm':'0.00001'},
            'expected_counts':{'samples':4,'labels':2},'samples':entries,'labels':labels,
            'preserve_occurrence_ids':['unrelated']}
    plan_path=folder/'synthetic_plan.json'; plan_path.write_text(exact_json(plan)+'\n')
    return project_path, book_path, plan


if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Usage: python examples/make_synthetic_case.py NEW_DIRECTORY')
    project, book, plan = create_case(sys.argv[1])
    print('Created invented DO_NOT_PRINT case:', project, book)
