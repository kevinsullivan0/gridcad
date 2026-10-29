"""Shape-independent mapping contracts; generated geometry, never native proof."""
import collections
import copy
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

import desktop_core as core
from tools.make_desktop_examples import create, binary_stl, pyramid


class GridShapeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def fixture(self,shape='pyramid',rows=3,columns=5,pitch=14,size=8,height=6):
        folder=create(self.root/str(len(list(self.root.iterdir()))),rows,columns,pitch,size,sample_shape=shape,height=height)
        project=core.load_project(folder/'DO_NOT_PRINT.PRINT');book=core.read_workbook(folder/'DO_NOT_PRINT.xlsx')
        return folder,project,book,dict(sheet='Recipes',selected_range=f'D4:{core.address(rows+3,columns+3)}',sample_name='Sample',label_container='synthetic-labels',orientation='Rows down; columns right')
    def propose(self,case,**kwargs):
        folder,project,book,args=case
        return core.propose(project,folder/'DO_NOT_PRINT.xlsx',book,**(args|kwargs))
    def test_pyramid_is_closed_nonflat_geometry_not_a_renamed_box(self):
        tris=pyramid(8,6);self.assertEqual(len(tris),6)
        self.assertEqual({v for t in tris for v in t},{(-4.,-4.,0),(4.,-4.,0),(4.,4.,0),(-4.,4.,0),(0,0,6)})
        directed=collections.Counter((t[i],t[(i+1)%3]) for t in tris for i in range(3))
        self.assertTrue(all(directed[(b,a)]==1 for a,b in directed))
        raw=binary_stl(tris);self.assertEqual(core._mesh(raw)['triangles'],6)
        self.assertEqual(core._mesh(raw)['bounds'],[[-4.,-4.,0.],[4.,4.,6.]])
        normals=[v[:3] for v in struct.iter_unpack('<12fH',raw[84:])]
        self.assertGreater(len(set(normals)),2)
    def test_pyramid_variants_have_exact_cell_body_mapping(self):
        for rows,columns,pitch,size,height in [(2,3,12,8,6),(3,7,18,11,8),(5,2,9,4,3)]:
            case=self.fixture(rows=rows,columns=columns,pitch=pitch,size=size,height=height)
            proposal=self.propose(case)
            self.assertEqual({m['cell']:m['id'] for m in proposal['mapping']},{core.address(r+4,c+4):f'synthetic-sample-{r+1}-{c+1}' for r in range(rows) for c in range(columns)})
            self.assertEqual(proposal['grid_basis'],'mesh-footprint-centers')
    def test_different_shapes_sizes_heights_share_one_grid(self):
        case=self.fixture('mixed');proposal=self.propose(case)
        samples=[case[1]['records'][i] for i in case[1]['groups']['Sample']]
        self.assertGreater(len({r['mesh_sha256'] for r in samples}),2)
        self.assertGreater(len({r['bounds'][1][2] for r in samples}),1)
        self.assertEqual(len(proposal['mapping']),15)
        transposed=self.propose(case,orientation='Rows right; columns down',transpose=True)
        self.assertEqual([(m['cell'],m['id']) for m in proposal['mapping']],[(m['cell'],m['id']) for m in transposed['mapping']])
    def test_asymmetric_offsets_use_only_strictly_contained_anchors(self):
        case=self.fixture('mixed');folder,project,book,args=case
        source=folder/'DO_NOT_PRINT.PRINT';document=core.op.project_document(source)
        with zipfile.ZipFile(source) as archive:payloads={name:archive.read(name) for name in archive.namelist()}
        # Generate genuine asymmetric mesh payloads with alternating local
        # offsets; the placement origins remain their independent regular grid.
        tess=document['project']['tessellationMap']
        for i,oid in enumerate(project['groups']['Sample']):
            shift=.4 if i%2 else -.3
            raw=payloads[tess[oid]['representations']['stl']];triangles=[]
            for values in struct.iter_unpack('<12fH',raw[84:]):
                triangles.append(tuple((values[j],values[j+1]+shift,values[j+2]) for j in (3,6,9)))
            member=f'mesh/asymmetric-{i}.stl';payloads[member]=binary_stl(triangles)
            tess[oid]['representations']['stl']=member
        payloads['project.json']=core.op.exact_json(document).encode()
        changed=folder/'asymmetric.PRINT'
        with zipfile.ZipFile(changed,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,raw in payloads.items():archive.writestr(name,raw)
        loaded=core.load_project(changed)
        case=(folder,loaded,book,args);records=loaded['records']
        p=self.propose(case);self.assertEqual(p['grid_basis'],'contained-placement-anchors')
        self.assertEqual(p['mapping'][0]['id'],'synthetic-sample-1-1')
        # A body shifted away from its origin is no longer an unambiguous fallback.
        oid=case[1]['groups']['Sample'][0]
        for corner in records[oid]['bounds']:corner[0]+=5
        records[oid]['center'][0]+=5
        with self.assertRaises(core.op.ValidationError):self.propose(case)
    def test_mixed_save_preserves_every_geometry_payload_and_original(self):
        case=self.fixture('mixed');folder,project,_,_=case
        old_hash=core.op.digest(folder/'DO_NOT_PRINT.PRINT');proposal=self.propose(case)
        audit=core.save(folder/'DO_NOT_PRINT.PRINT',folder/'DO_NOT_PRINT.xlsx',proposal,self.root/'output','Generated physical index corners and representative mixed-shape cells verified.')
        with zipfile.ZipFile(folder/'DO_NOT_PRINT.PRINT') as a,zipfile.ZipFile(self.root/'output/candidate_UNVERIFIED.PRINT') as b:
            for name in a.namelist():
                if name!='project.json':self.assertEqual(a.read(name),b.read(name))
        self.assertEqual(old_hash,core.op.digest(folder/'DO_NOT_PRINT.PRINT'))
        self.assertTrue(audit['nonmaterial_preservation_passed']);self.assertFalse(audit['print_ready'])
    def test_staggered_base_holes_duplicates_and_overlaps_refused(self):
        for fault in ('raised','duplicate','overlap','hole'):
            case=self.fixture('mixed');records=case[1]['records'];oid='synthetic-sample-2-2';r=records[oid]
            if fault=='raised':
                for bound in r['bounds']:bound[2]+=1
                r['center'][2]+=1
            elif fault=='duplicate':
                records[oid]=copy.deepcopy(records['synthetic-sample-1-1']);records[oid]['id']=oid
                case[1]['bodies'][oid]['transform']=copy.deepcopy(case[1]['bodies']['synthetic-sample-1-1']['transform'])
            elif fault=='overlap':
                r['bounds'][0][0]-=20;r['bounds'][1][0]+=20
            else:case[1]['groups']['Sample'].remove(oid)
            with self.subTest(fault=fault),self.assertRaises(core.op.ValidationError):self.propose(case)
    def test_diagonal_overlap_cannot_escape_neighbor_checks(self):
        case=self.fixture('mixed',rows=2,columns=2,pitch=12,size=4)
        for oid in case[1]['groups']['Sample']:
            r=case[1]['records'][oid];row,col=map(int,oid.rsplit('-',2)[1:]);half=10 if row==col else 1
            for axis in (0,1):r['bounds'][0][axis]=r['center'][axis]-half;r['bounds'][1][axis]=r['center'][axis]+half
        with self.assertRaisesRegex(core.op.ValidationError,'Diagonal'):self.propose(case)


if __name__=='__main__':unittest.main()
