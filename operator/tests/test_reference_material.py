"""Invented assignments only: full native-object cloning, not native acceptance."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.make_synthetic_case import create_case
from gridcad_operator import operator as op

class ReferenceMaterialTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.project,self.book,self.plan=create_case(self.root/'case');self.out=self.root/'result'
        material=op.EcoFlexMaterialProvider().direct_black()
        material.update(id='reference-cyan',name='VEcoFlxCyn',vendorMaterialId='VEcoFlxCyn',uiColor='rgb(0, 137, 166)')
        material['metadata'].update(resinId=11934,displayName='EcoFlexCyan',custom_native={'keep':[True,12,'x']})
        material['threeDAppearance']={'r':0,'g':137,'b':166,'a':255}
        def change(doc):
            nodes,_,bodies=op.index(doc)
            for oid in ('glyph-0','glyph-1'):
                m=copy.deepcopy(nodes[oid]['material']);m['id']='unique-'+oid
                nodes[oid]['material']=copy.deepcopy(m);bodies[oid]['material']=copy.deepcopy(m)
            nodes['unrelated']['material']=copy.deepcopy(material);bodies['unrelated']['material']=copy.deepcopy(material)
            bodies['unrelated']['properties']['threeDAppearance']['value'].update(material['threeDAppearance'])
        self.rewrite(change)
        for entry in self.plan['labels']:
            entry.update(action='copy_native_reference',reference_occurrence_id='unrelated',
                         reference_material_sha256=op.fingerprint(material),replacement_confirmed=True)
    def tearDown(self):self.temp.cleanup()
    def rewrite(self,mutate):
        doc=op.project_document(self.project);mutate(doc);tmp=self.root/'replacement.print'
        with zipfile.ZipFile(self.project) as src,zipfile.ZipFile(tmp,'w') as dst:
            dst.comment=src.comment
            for info in src.infolist():dst.writestr(info,op.exact_json(doc) if info.filename=='project.json' else src.read(info))
        tmp.replace(self.project);self.plan['archive_sha256']=op.digest(self.project)
        nodes,_,_=op.index(doc)
        for e in self.plan['samples']+self.plan['labels']:e['source_material_sha256']=op.fingerprint(nodes[e['occurrence_id']]['material'])
        for e in self.plan['labels']:
            if e.get('reference_occurrence_id') in nodes:e['reference_material_sha256']=op.fingerprint(nodes[e['reference_occurrence_id']]['material'])
    def refused(self,pattern=None):
        with self.assertRaisesRegex(op.ValidationError,pattern or '.'):
            op.apply(self.project,self.book,self.plan,self.out)
        self.assertFalse(self.out.exists())
    def test_complete_reference_clone_identity_and_payloads(self):
        before=op.project_document(self.project);nodes,_,bodies=op.index(before);source=op.digest(self.project)
        audit=op.apply(self.project,self.book,self.plan,self.out)
        after=op.project_document(self.out/'candidate_UNVERIFIED.PRINT');an,_,ab=op.index(after)
        self.assertEqual(audit['changed_count'],6);self.assertFalse(audit['print_ready'])
        for oid in ('glyph-0','glyph-1'):
            expected=copy.deepcopy(nodes['unrelated']['material']);expected['id']=nodes[oid]['material']['id']
            self.assertEqual(an[oid]['material'],expected);self.assertEqual(ab[oid]['material'],expected)
            self.assertTrue(op.appearance_matches(ab[oid],expected))
            self.assertEqual(ab[oid]['properties']['threeDAppearance']['value']['invented_uniforms'],{'keep':True})
        self.assertEqual(an['unrelated'],nodes['unrelated']);self.assertEqual(ab['unrelated'],bodies['unrelated'])
        self.assertEqual(op.digest(self.project),source)
        self.assertEqual(op.stripped(before,set(audit['changed_occurrence_ids'])),op.stripped(after,set(audit['changed_occurrence_ids'])))
        with zipfile.ZipFile(self.project) as a,zipfile.ZipFile(self.out/'candidate_UNVERIFIED.PRINT') as b:
            for name in a.namelist():
                if name!='project.json':self.assertEqual(a.read(name),b.read(name))
        entries=json.loads((self.out/'assignments.json').read_text())
        self.assertTrue(all(x['reference_material_sha256'] for x in entries if x['role']=='label'))
    def test_intentional_replacement_requires_actual_boolean_confirmation(self):
        for value in (False,'yes',1,None):
            with self.subTest(value=value):
                self.plan['labels'][0]['replacement_confirmed']=value;self.refused('explicitly confirm')
    def test_dangling_reference_refused(self):
        self.plan['labels'][0]['reference_occurrence_id']='missing';self.refused('reference is missing')
    def test_reference_fingerprint_bound(self):
        self.plan['labels'][0]['reference_material_sha256']='0'*64;self.refused('changed after review')
    def test_reference_desired_actual_conflict_refused(self):
        self.rewrite(lambda d:op.index(d)[2]['unrelated']['material']['metadata'].update(displayName='wrong'))
        self.refused('conflicting material')
    def test_reference_preview_conflict_refused(self):
        self.rewrite(lambda d:op.index(d)[2]['unrelated']['properties']['threeDAppearance']['value'].update(r=32))
        self.refused('conflicting material')
    def test_wrong_family_and_unknown_resin_refused(self):
        for key,value in (('printerFamily','FDM'),('resinId',99999)):
            with self.subTest(key=key):
                def change(d):
                    n,_,b=op.index(d)
                    for x in (n['unrelated']['material'],b['unrelated']['material']):
                        if key=='resinId':x['metadata'][key]=value
                        else:x[key]=value
                self.rewrite(change);self.refused()
    def test_reference_malformed_rgb_refused(self):
        def change(d):
            n,_,b=op.index(d)
            n['unrelated']['material']['threeDAppearance']['r']=-3
            b['unrelated']['material']['threeDAppearance']['r']=-3
            b['unrelated']['properties']['threeDAppearance']['value']['r']=-3
        self.rewrite(change);self.refused('invalid preview')
    def test_shared_identity_not_bypassed_by_confirmation(self):
        def change(d):
            n,_,b=op.index(d)
            for oid in ('glyph-0','glyph-1'):
                n[oid]['material']['id']='shared';b[oid]['material']['id']='shared'
        self.rewrite(change);self.refused('shared material identity')
    def test_matching_reference_preserved_without_confirmation(self):
        def change(d):
            n,_,b=op.index(d)
            for oid in ('glyph-0','glyph-1'):
                m=copy.deepcopy(n['unrelated']['material']);m['id']=n[oid]['material']['id']
                n[oid]['material']=m;b[oid]['material']=copy.deepcopy(m)
                b[oid]['properties']['threeDAppearance']['value'].update(m['threeDAppearance'])
        self.rewrite(change)
        for e in self.plan['labels']:e['action']='preserve_reference_material';e['replacement_confirmed']=False
        audit=op.apply(self.project,self.book,self.plan,self.out);self.assertEqual(audit['changed_count'],4)
    def test_valid_mixer_reference_and_full_optional_metadata(self):
        def change(d):
            n,_,b=op.index(d);m=op.EcoFlexMaterialProvider().sample(op.recipe('2/0/0/0/98/0'));m['id']='reference-mixer';m['metadata']['extra']={'keep':True}
            n['unrelated']['material']=m;b['unrelated']['material']=copy.deepcopy(m)
            b['unrelated']['properties']['threeDAppearance']['value'].update(m['threeDAppearance'])
        self.rewrite(change);audit=op.apply(self.project,self.book,self.plan,self.out);self.assertEqual(audit['changed_count'],6)
    def test_reference_marked_for_change_is_refused(self):
        # Even a no-op copy action may not designate its own changing source.
        for e in self.plan['labels']:
            e['reference_occurrence_id']='glyph-0'
            e['reference_material_sha256']=e['source_material_sha256'] if e['occurrence_id']=='glyph-0' else self.plan['labels'][0]['source_material_sha256']
        self.refused('would also change')
    def test_reference_alias_with_conflicting_definition_refused(self):
        def change(d):
            n,_,b=op.index(d)
            for obj in (n['glyph-0'],b['glyph-0']):obj['material']['id']='reference-cyan'
        self.rewrite(change);self.refused('conflicting saved definitions')
    def test_malformed_mixer_reference_is_refused(self):
        def change(d):
            n,_,b=op.index(d);m=op.EcoFlexMaterialProvider().sample(op.recipe('2/0/0/0/98/0'))
            m['metadata']['cmykwt_dm_used_materials_id']=[-1];m['id']='bad-mixer'
            n['unrelated']['material']=m;b['unrelated']['material']=copy.deepcopy(m)
            b['unrelated']['properties']['threeDAppearance']['value'].update(m['threeDAppearance'])
        self.rewrite(change);self.refused('not a supported saved')
    def test_reference_must_not_be_changed_sample(self):
        # A pre-existing matching mixer may be used only if the sample stays unchanged.
        for e in self.plan['labels']:e['reference_occurrence_id']='sample-0-0'
        self.refused('not a supported saved')

if __name__=='__main__':unittest.main()
