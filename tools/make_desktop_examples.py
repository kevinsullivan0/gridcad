"""Invented rectangular archive-contract fixtures; never native/printable evidence."""
from pathlib import Path
import argparse
import copy
import html
import json
import math
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop_core import address, op


def box(x0,y0,x1,y1,z1=2):
    points=[(x,y,z) for z in (0,z1) for y in (y0,y1) for x in (x0,x1)]
    faces=[(0,2,3),(0,3,1),(4,5,7),(4,7,6),(0,1,5),(0,5,4),(2,6,7),(2,7,3),(0,4,6),(0,6,2),(1,3,7),(1,7,5)]
    return [tuple(points[i] for i in face) for face in faces]


def pyramid(size, height):
    """Closed square-based pyramid: two base triangles and four side faces."""
    h=size/2
    points=[(-h,-h,0),(h,-h,0),(h,h,0),(-h,h,0),(0,0,height)]
    faces=[(0,2,1),(0,3,2),(0,1,4),(1,2,4),(2,3,4),(3,0,4)]
    return [tuple(points[i] for i in face) for face in faces]


def binary_stl(triangles):
    records=[]
    for tri in triangles:
        tri=[tuple(map(float,v)) for v in tri]
        a=[tri[1][i]-tri[0][i] for i in range(3)];b=[tri[2][i]-tri[0][i] for i in range(3)]
        normal=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
        length=math.sqrt(sum(v*v for v in normal));normal=tuple(v/length for v in normal) if length else (0.,0.,0.)
        records.append(struct.pack('<12fH',*normal,*(v for point in tri for v in point),0))
    return b'GRIDCAD INVENTED DO NOT PRINT'.ljust(80,b'\0')+struct.pack('<I',len(triangles))+b''.join(records)


SEGMENTS={'0':'abcedf','1':'bc','2':'abged','3':'abgcd','4':'fgbc','5':'afgcd','6':'afgecd','7':'abc','8':'abcdefg','9':'abfgcd'}
STROKES={'a':(0,3,1.8,3.25),'b':(1.55,1.65,1.8,3.25),'c':(1.55,0,1.8,1.6),'d':(0,0,1.8,.25),'e':(0,0,.25,1.6),'f':(0,1.65,.25,3.25),'g':(0,1.5,1.8,1.75)}


def number_mesh(number):
    # Our own seven-segment strokes, extruded 0.5 mm; no font/vendor assets.
    tris=[]
    for i,char in enumerate(str(number)):
        for segment in SEGMENTS[char]:
            x0,y0,x1,y1=STROKES[segment];tris+=box(x0+2.3*i,y0,x1+2.3*i,y1,.5)
    # Local geometry is quarter-turned by the source profile; rotate it back so
    # the physical XY preview shows ordinary upright index digits.
    return [tuple((-p[1],p[0],p[2]) for p in tri) for tri in tris]


def create(folder,rows=4,columns=6,pitch=12,size=8,*,sample_shape="box",height=2):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    if not 2<=rows<=100 or not 2<=columns<=100 or not 0<size<pitch<=100:
        raise ValueError('Use 2–100 rows/columns and 0 < size < pitch <= 100 mm.')
    if sample_shape not in ('box','pyramid','mixed') or not 0<height<=100:
        raise ValueError('Example shape must be box, pyramid or mixed; height must be greater than zero and at most 100 mm.')
    from decimal import Decimal as D
    pitch, size = D(str(pitch)), D(str(size))
    def affine(scale=1):return [scale,0,0,0,0,scale,0,0,0,0,scale,0,0,0,0,1]
    props={'info.units':{'value':'CM'},'scale.factor':{'value':{'x':100,'y':100,'z':100}},'orientation':{'value':[0,1,0,0,-1,0,0,0,0,0,1,0,0,0,0,1]}}
    def node(oid,name,children=None,material=None,root=False):
        n={'id':oid,'name':name,'children':children or [],'units':'CM','occurrenceScaling':D('.001'),
           'rootScaling':affine(D('.1')),'transform':affine(D('.1') if root else 1),
           'properties':copy.deepcopy(props),'featureManager':{'uniqueFeatures':[],'currentStateIndices':[]}}
        if material:n['material']=copy.deepcopy(material);n['tessellationKey']=oid
        return n
    def picker(oid):return {'id':'material-'+oid,'properties':{},'name':'rgba,210,213,207,255','vendorMaterialId':'rgba,210,213,207,255','printerFamily':'PolyJet','threeDAppearance':{'r':210,'g':213,'b':207,'a':255},'uiColor':'rgb(210,213,207)','metadata':{'materialType':'color_picker','pickerSelectedColor':'synthetic-gray'}}
    bodies=[];parts=[];labels=[];meshes={};tess={}
    def body(n,x,y,member):
        # Occurrence and tray convention agree exactly with the bounded profile.
        n['transform'][3]=-y;n['transform'][7]=x
        material=n['material'];oid=n['id']
        bodies.append({'id':'body-'+oid,'occurrence':oid,'rootOccurrenceId':'synthetic-assembly','material':copy.deepcopy(material),
            'transform':[0,D('.1'),0,D(str(x))/1000,-D('.1'),0,0,D(str(y))/1000,0,0,D('.1'),0,0,0,0,1],
            'composeTransform':affine(),'properties':{'representation':{'value':'stl'},'threeDAppearance':{'value':copy.deepcopy(material['threeDAppearance'])}}})
        tess[oid]={'representations':{'stl':member}}
    values={}
    for r in range(rows):
        for c in range(columns):
            oid=f'synthetic-sample-{r+1}-{c+1}';n=node(oid,'Sample',material=picker(oid));parts.append(n)
            # This generator offers examples, not an application shape whitelist.
            kind=('pyramid' if (r+c)%2 else 'box') if sample_shape=='mixed' else sample_shape
            width=size*(D('0.65') if sample_shape=='mixed' and (r+c)%3==1 else 1)
            tall=float(height)*(1+(r%3)*0.25 if sample_shape=='mixed' else 1)
            triangles=pyramid(width,tall) if kind=='pyramid' else box(-width/2,-width/2,width/2,width/2,tall)
            member=f'mesh/sample-{kind}-{width}-{tall}.stl';meshes[member]=binary_stl(triangles)
            body(n,c*pitch,-r*pitch,member)
            cyan=(r*7+c*3)%51;clear=(c*5)%31;recipe=f'{cyan}/0/0/0/{100-cyan-clear}/{clear}'
            values[address(r+4,c+4)]=recipe
    black=op.EcoFlexMaterialProvider().direct_black();black['id']='synthetic-shared-black';black['metadata']['synthetic_preserve_marker']='keep-complete-object'
    for kind,count in [('row',rows),('column',columns)]:
        for i in range(count):
            oid=f'synthetic-{kind}-label-{i+1}';n=node(oid,'Printed index '+str(i+1),material=black);labels.append(n)
            member=f'mesh/index-{i+1}.stl';meshes[member]=binary_stl(number_mesh(i+1))
            body(n,-pitch if kind=='row' else i*pitch,-i*pitch if kind=='row' else pitch,member)
    parts.append(node('synthetic-labels','Printed labels',children=labels))
    doc={'version':copy.deepcopy(op.SOURCE_VERSION),'project':{'id':'synthetic-gridcad-archive-contract',
         'rootOccurrences':[node('synthetic-assembly','DO NOT PRINT — invented example',children=parts,root=True)],
         'trays':[{'id':'synthetic-tray','trayBodies':bodies,'synthetic_do_not_print':True}],
         'tessellationMap':tess,'synthetic_notice':'Invented archive contract, not generated or validated by native GrabCAD.'}}
    with zipfile.ZipFile(folder/'DO_NOT_PRINT.PRINT','w',compression=zipfile.ZIP_DEFLATED) as z:
        z.comment=b'GRIDCAD SYNTHETIC ARCHIVE CONTRACT - DO NOT PRINT'
        z.writestr('project.json',op.exact_json(doc));z.writestr('SYNTHETIC.txt','DO NOT PRINT. No native application provenance.');
        for name,raw in meshes.items():z.writestr(name,raw)
    # Vendor-neutral geometry companion, generated from our invented meshes.
    # Separate bodies share world-space millimetre coordinates for assembly import.
    geometry=folder/'import-geometry';geometry.mkdir(exist_ok=True)
    imported=[]
    for b in bodies:
        oid=b['occurrence'];member=tess[oid]['representations']['stl'];raw=meshes[member];m=b['transform']
        triangles=[]
        for record in struct.iter_unpack('<12fH',raw[84:]):
            points=[record[3:6],record[6:9],record[9:12]]
            triangles.append(tuple(tuple(float(sum(m[r*4+k]*D(str(v[k]))*10 for k in range(3))+m[r*4+3]*1000) for r in range(3)) for v in points))
        name=oid+'.stl';(geometry/name).write_bytes(binary_stl(triangles))
        imported.append({'file':name,'units':'mm','role':'sample' if oid.startswith('synthetic-sample-') else 'label'})
    (geometry/'geometry-manifest.json').write_text(json.dumps({'units':'mm','shared_coordinates':True,'native_import_verified':False,'bodies':imported},indent=2),encoding='utf-8')
    (geometry/'IMPORT-GUIDE.txt').write_text('GENERATED GEOMETRY STUDY, NOT A CERTIFIED PRINT JOB\n'
        'These ordinary binary STL bodies use millimetres and shared assembly coordinates.\n'
        'The matching workbook is ../DO_NOT_PRINT.xlsx; sample row/column indices occur in filenames.\n'
        'In your CAD/printing tool, import all STL bodies as one assembly while preserving relative positions,\n'
        'do not auto-arrange individual parts, and confirm millimetres and overall dimensions.\n'
        'Keep sample bodies distinct and group label bodies separately. Save with your own printer/material setup.\n'
        'Exact import UI and generated native project schema have not been validated here. A newly exported\n'
        'project may not match the converter\'s bounded 2170 profile; unknown profiles must be refused, not forced.\n'
        'The adjacent synthetic .PRINT lets you exercise GridCAD directly without native import.\n'
        'Do not print either example without ordinary native preparation and process review.\n',encoding='utf-8')
    make_workbook(folder/'DO_NOT_PRINT.xlsx',values,rows,columns)
    (folder/'README.txt').write_text(f'INVENTED EXAMPLE — DO NOT PRINT\n{rows} rows x {columns} columns, pitch {pitch} mm, maximum sample width {size} mm, {sample_shape} shapes.\nWorksheet Recipes!D4:{address(rows+3,columns+3)}. Sample group Sample; label container Printed labels.\nChoose Rows down; columns right. No transpose. Printed index digits start at 1.\nThese archives test software contracts. Native GrabCAD opening/recomposition is unverified.\n',encoding='utf-8')
    return folder


def make_workbook(path,values,rows=4,columns=6,*,formula_cache=None):
    cells={'A1':'GRIDCAD — SYNTHETIC TEMPLATE — DO NOT PRINT','A2':'C / M / Y / K / W / T; exactly 100%; explicit zeros; index labels start at 1',**values}
    for c in range(columns):cells[address(3,c+4)]=str(c+1)
    for r in range(rows):cells[address(r+4,3)]=str(r+1)
    grouped={}
    for addr,value in cells.items():
        row=op.cell_position(addr)[0]
        if formula_cache and addr in formula_cache:
            cached=formula_cache[addr]
            raw=f'<c r="{addr}" t="str"><f>"{html.escape(value)}"</f>'+('' if cached is None else '<v>'+html.escape(cached)+'</v>')+'</c>'
        else:raw=f'<c r="{addr}" t="inlineStr"><is><t>{html.escape(value)}</t></is></c>'
        grouped.setdefault(row,[]).append(raw)
    content='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><cols><col min="1" max="2" width="14" customWidth="1"/><col min="3" max="200" width="24" customWidth="1"/></cols><sheetData>'+''.join('<row r="'+str(r)+'">'+''.join(grouped[r])+'</row>' for r in sorted(grouped))+'</sheetData></worksheet>'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Recipes" sheetId="1" r:id="rId1"/></sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml',content)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--rows',type=int,default=4);p.add_argument('--columns',type=int,default=6);p.add_argument('--pitch',type=float,default=12);p.add_argument('--size',type=float,default=8)
    p.add_argument('--shape',choices=('box','pyramid','mixed'),default='box');p.add_argument('--height',type=float,default=2)
    args=p.parse_args();create(args.folder,args.rows,args.columns,args.pitch,args.size,sample_shape=args.shape,height=args.height)
