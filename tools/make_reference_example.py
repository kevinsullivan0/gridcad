"""Newly invented reference-copy example. No native provenance; DO NOT PRINT."""
from pathlib import Path
import copy
import zipfile
from tools.make_desktop_examples import create
import desktop_core as core

REFERENCE_ID='synthetic-reference-white'
REFERENCE_NAME='Reference white'


def create_reference_example(folder):
    folder=create(folder)
    path=folder/'DO_NOT_PRINT.PRINT'
    doc=core.op.project_document(path);nodes,leaves,bodies=core.op.index(doc)
    for oid in sorted(leaves):
        if 'label-' in oid:
            material=copy.deepcopy(nodes[oid]['material']);material['id']='unique-label-material-'+oid
            nodes[oid]['material']=material;bodies[oid]['material']=copy.deepcopy(material)
    template='synthetic-sample-1-1'
    node=copy.deepcopy(nodes[template]);body=copy.deepcopy(bodies[template])
    material=core.op.EcoFlexMaterialProvider().direct_black()
    material.update(id='synthetic-reference-white-material',name='VEcoFlxWht',vendorMaterialId='VEcoFlxWht',uiColor='rgb(240, 240, 240)')
    material['metadata'].update(resinId=11935,displayName='EcoFlexWhite',synthetic_native_extra={'preserve':['all','fields'], 'flag':True})
    material['threeDAppearance']={'r':240,'g':240,'b':240,'a':255}
    node.update(id=REFERENCE_ID,name=REFERENCE_NAME,tessellationKey=REFERENCE_ID,material=copy.deepcopy(material))
    # Outside sample group and labels; moves only this newly generated fixture body.
    node['transform'][3]=24;node['transform'][7]=-24
    body.update(id='body-'+REFERENCE_ID,occurrence=REFERENCE_ID,material=copy.deepcopy(material))
    body['transform'][3]=core.op.D('-.024');body['transform'][7]=core.op.D('-.024')
    body['properties']['threeDAppearance']['value']=copy.deepcopy(material['threeDAppearance'])
    doc['project']['rootOccurrences'][0]['children'].append(node)
    doc['project']['trays'][0]['trayBodies'].append(body)
    doc['project']['tessellationMap'][REFERENCE_ID]=copy.deepcopy(doc['project']['tessellationMap'][template])
    replacement=folder/'reference-temp.PRINT'
    with zipfile.ZipFile(path) as src,zipfile.ZipFile(replacement,'x',compression=zipfile.ZIP_DEFLATED) as dst:
        dst.comment=src.comment
        for info in src.infolist():dst.writestr(info,core.op.exact_json(doc) if info.filename=='project.json' else src.read(info))
    replacement.replace(path)
    return folder
