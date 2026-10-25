import copy
from decimal import Decimal as D
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.make_synthetic_case import create_case
from gridcad_operator.operator import (ValidationError, apply, prepare, project_document,
    index, exact_json, fingerprint, digest, inspect, matches_mixer, recipe, REVIEWED_ID_PROFILE, mapping_digest)
from gridcad_operator.material_converter import EcoFlexMaterialProvider


class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.project,self.book,self.plan=create_case(self.root/'case')
        self.out=self.root/'result'
    def tearDown(self): self.temp.cleanup()
    def rewrite(self, mutate):
        doc=project_document(self.project); mutate(doc)
        replacement=self.root/'replacement.print'
        with zipfile.ZipFile(self.project) as src,zipfile.ZipFile(replacement,'x') as dst:
            dst.comment=src.comment
            for info in src.infolist(): dst.writestr(info,exact_json(doc) if info.filename=='project.json' else src.read(info))
        replacement.replace(self.project)
        self.plan['archive_sha256']=digest(self.project)
        self.plan['source_version']=copy.deepcopy(doc['version'])
        nodes,_,_=index(doc)
        for entry in self.plan['samples']+self.plan['labels']:
            entry['source_material_sha256']=fingerprint(nodes[entry['occurrence_id']]['material'])
    def refused(self):
        with self.assertRaises(ValidationError): apply(self.project,self.book,self.plan,self.out)
        self.assertFalse(self.out.exists())
    def reviewed_ids(self):
        self.plan['placement_profile']=REVIEWED_ID_PROFILE
        self.plan.pop('axes',None)
        self.plan['review']['mapping_sha256']=mapping_digest(self.plan)
    def common_translation(self):
        def change(doc):
            for body in index(doc)[2].values():
                body['composeTransform'][3]=D('-.21');body['composeTransform'][7]=D('.17')
        self.rewrite(change)
    def test_success_payloads_unrelated_guid_and_black_metadata(self):
        before=project_document(self.project);source_hash=digest(self.project)
        report=apply(self.project,self.book,self.plan,self.out)
        after=project_document(self.out/'candidate_UNVERIFIED.PRINT')
        bn,_,bb=index(before);an,_,ab=index(after)
        for oid in ('glyph-0','glyph-1','unrelated'):
            self.assertEqual(bn[oid],an[oid]);self.assertEqual(bb[oid],ab[oid])
        self.assertEqual(before['project']['labelManager'],after['project']['labelManager'])
        self.assertEqual(before['version'],after['version'])
        self.assertEqual(report['changed_count'],4)
        self.assertFalse(report['print_ready']);self.assertEqual(digest(self.project),source_hash)
        with zipfile.ZipFile(self.project) as src,zipfile.ZipFile(self.out/'candidate_UNVERIFIED.PRINT') as dst:
            for name in ('mesh/example.stl','opaque.bin'):self.assertEqual(src.read(name),dst.read(name))
    def test_inspect_is_readonly_and_exposes_material_fingerprint(self):
        h=digest(self.project);result=inspect(self.project,self.book)
        self.assertTrue(result['placement_profile_supported']);self.assertEqual(digest(self.project),h)
        self.assertEqual(len(result['leaves']),7)
    def test_refuses_even_empty_existing_output_directory(self):
        self.out.mkdir()
        with self.assertRaises(ValidationError):apply(self.project,self.book,self.plan,self.out)
        self.assertEqual(list(self.out.iterdir()),[])
    def test_refuses_output_symlink(self):
        self.out.symlink_to(self.root/'missing',target_is_directory=True)
        with self.assertRaises(ValidationError):apply(self.project,self.book,self.plan,self.out)
        self.assertTrue(self.out.is_symlink())
    def test_hash_binding(self):
        self.plan['archive_sha256']='0'*64;self.refused()
    def test_workbook_hash_binding(self):
        self.plan['workbook_sha256']='0'*64;self.refused()
    def test_unknown_source_version_even_when_plan_updated(self):
        self.rewrite(lambda d:d['version']['versionNumbers']['pj'].update(internal=2171));self.refused()
    def test_unknown_material_profile(self):
        self.plan['material_profile']='unknown';self.refused()
    def test_unverified_profile_acknowledgement_required(self):
        self.plan['allow_unverified_material_profile']=False;self.refused()
    def test_units_not_normalized(self):
        self.rewrite(lambda d:index(d)[0]['sample-0-0'].update(units='MM'));self.refused()
    def test_nonreviewed_rotation_refused(self):
        self.rewrite(lambda d:index(d)[2]['sample-0-0']['transform'].__setitem__(0,D('.2')));self.refused()
    def test_root_scaling_not_repaired(self):
        self.rewrite(lambda d:index(d)[0]['assembly']['rootScaling'].__setitem__(0,D('.2')));self.refused()
    def test_column_major_translation_refused(self):
        self.rewrite(lambda d:index(d)[2]['sample-0-0']['transform'].__setitem__(12,D('.01')));self.refused()
    def test_plan_cardinality(self):
        self.plan['samples'].pop();self.refused()
    def test_duplicate_cell(self):
        self.plan['samples'][1]['cell']='D4';self.refused()
    def test_duplicate_body_mapping(self):
        self.plan['samples'][1]['occurrence_id']='sample-0-0';self.refused()
    def test_wrong_orientation(self):
        self.plan['axes']['row_direction']=-1;self.refused()
    def test_wrong_pitch(self):
        self.plan['axes']['pitch_mm']='10';self.refused()
    def test_missing_preserved_leaf_declaration(self):
        self.plan['preserve_occurrence_ids']=[];self.refused()
    def test_expected_label_percentages_must_match_workbook(self):
        self.plan['samples'][0]['expected_percentages']=['1','0','0','0','99','0'];self.refused()
    def test_no_normalization_or_missing_channel(self):
        for text in ('2 / 0 / 0 / 0 / 97 / 0','2 / 0 / 0 / / 98 / 0','2 / 0 / 0 / 98 / 0'):
            with self.assertRaises(ValidationError):recipe(text)
    def test_heterogeneous_picker_conflicts(self):
        def change(doc):
            n,_,b=index(doc)
            for m in (n['sample-0-1']['material'],b['sample-0-1']['material']):m['name']='different-intentional-color'
        self.rewrite(change);self.refused()
    def test_prior_mixer_never_blindly_overwritten(self):
        def change(doc):
            n,_,b=index(doc);m=EcoFlexMaterialProvider().sample(recipe('1 / 0 / 0 / 0 / 99 / 0'))
            m['id']=n['sample-0-0']['material']['id']
            n['sample-0-0']['material']=copy.deepcopy(m);b['sample-0-0']['material']=copy.deepcopy(m)
        self.rewrite(change);self.refused()
    def test_matching_prior_mixer_preserved_completely(self):
        def change(doc):
            n,_,b=index(doc);m=EcoFlexMaterialProvider().sample(recipe('2 / 0 / 0 / 0 / 98 / 0'))
            m['id']=n['sample-0-0']['material']['id'];m['metadata']['invented_native_extra']='retain'
            n['sample-0-0']['material']=copy.deepcopy(m);b['sample-0-0']['material']=copy.deepcopy(m)
            b['sample-0-0']['properties']['threeDAppearance']['value'].update(m['threeDAppearance'])
        self.rewrite(change);self.plan['samples'][0]['action']='preserve_exact_mixer'
        before=project_document(self.project);apply(self.project,self.book,self.plan,self.out)
        self.assertEqual(index(before)[0]['sample-0-0'],index(project_document(self.out/'candidate_UNVERIFIED.PRINT'))[0]['sample-0-0'])
    def test_desired_actual_mismatch(self):
        self.rewrite(lambda d:index(d)[2]['sample-0-0']['material'].update(name='conflict'));self.refused()
    def test_shared_material_id_not_split_or_deleted(self):
        def change(doc):
            n,_,b=index(doc)
            for m in (n['sample-0-1']['material'],b['sample-0-1']['material']):m['id']=n['sample-0-0']['material']['id']
        self.rewrite(change);self.refused()
    def test_native_black_reference_retains_complete_metadata(self):
        def change(doc):
            n,_,b=index(doc);m=copy.deepcopy(n['sample-0-0']['material']);m['id']='new-gray-glyph-material'
            n['glyph-1']['material']=copy.deepcopy(m);b['glyph-1']['material']=copy.deepcopy(m)
        self.rewrite(change)
        self.plan['labels'][1].update(action='assign_from_picker_using_native_black',reference_occurrence_id='glyph-0')
        before=project_document(self.project);apply(self.project,self.book,self.plan,self.out)
        n,_,_=index(project_document(self.out/'candidate_UNVERIFIED.PRINT'))
        expected=copy.deepcopy(index(before)[0]['glyph-0']['material']);expected['id']='new-gray-glyph-material'
        self.assertEqual(n['glyph-1']['material'],expected)
    def test_unknown_action_has_no_overwrite_escape(self):
        self.plan['samples'][0]['action']='overwrite';self.refused()
    def test_root_translation_refused(self):
        self.rewrite(lambda d:index(d)[0]['assembly']['transform'].__setitem__(3,D('.01')));self.refused()
    def test_orientation_translation_refused(self):
        self.rewrite(lambda d:index(d)[0]['assembly']['properties']['orientation']['value'].__setitem__(3,D('.01')));self.refused()
    def test_formula_cache_missing_never_invented(self):
        replacement=self.root/'changed.xlsx'
        with zipfile.ZipFile(self.book) as src,zipfile.ZipFile(replacement,'x') as dst:
            for info in src.infolist():
                raw=src.read(info)
                if info.filename.endswith('sheet1.xml'):
                    raw=raw.replace(b'<c r="D4" t="inlineStr"><is><t>2 / 0 / 0 / 0 / 98 / 0</t></is></c>',b'<c r="D4"><f>UNSUPPORTED()</f><v/></c>')
                dst.writestr(info,raw)
        replacement.replace(self.book);self.plan['workbook_sha256']=digest(self.book)
        self.plan['formula_cache_policy']='confirmed_current_cache';self.refused()
    def test_formula_stored_cache_requires_explicit_confirmation(self):
        replacement=self.root/'changed.xlsx'
        with zipfile.ZipFile(self.book) as src,zipfile.ZipFile(replacement,'x') as dst:
            for info in src.infolist():
                raw=src.read(info)
                if info.filename.endswith('sheet1.xml'):
                    raw=raw.replace(b'<c r="D4" t="inlineStr"><is><t>2 / 0 / 0 / 0 / 98 / 0</t></is></c>',b'<c r="D4" t="str"><f>UNSUPPORTED()</f><v>2 / 0 / 0 / 0 / 98 / 0</v></c>')
                dst.writestr(info,raw)
        replacement.replace(self.book);self.plan['workbook_sha256']=digest(self.book)
        self.refused()
        self.plan['formula_cache_policy']='confirmed_current_cache'
        apply(self.project,self.book,self.plan,self.out)
    def test_minimal_black_refused_when_native_template_available(self):
        def change(doc):
            n,_,b=index(doc);m=copy.deepcopy(n['sample-0-0']['material']);m['id']='gray-glyph-material'
            n['glyph-1']['material']=copy.deepcopy(m);b['glyph-1']['material']=copy.deepcopy(m)
        self.rewrite(change);self.plan['labels'][1]['action']='assign_from_picker_using_unverified_black';self.refused()
    def test_publication_race_never_overwrites_or_deletes_foreign_file(self):
        import os
        real_link=os.link
        def collision(source,destination):
            Path(destination).write_bytes(b'foreign concurrent file')
            return real_link(source,destination)
        with patch('gridcad_operator.operator.os.link',side_effect=collision):
            with self.assertRaises(FileExistsError):apply(self.project,self.book,self.plan,self.out)
        self.assertEqual((self.out/'UNVERIFIED.txt').read_bytes(),b'foreign concurrent file')
        self.assertFalse((self.out/'candidate_UNVERIFIED.PRINT').exists())
    def test_ancestor_shared_sample_material_identity_refused(self):
        def change(doc):
            n,_,_=index(doc)
            n['assembly']['material']=copy.deepcopy(n['sample-0-0']['material'])
        self.rewrite(change)
        with self.assertRaisesRegex(ValidationError,'shared material identity'):
            apply(self.project,self.book,self.plan,self.out)
        self.assertFalse(self.out.exists())
    def test_nested_container_shared_sample_identity_refused(self):
        def change(doc):
            n,_,_=index(doc)
            n['glyph-container']['material']=copy.deepcopy(n['sample-0-0']['material'])
        self.rewrite(change)
        with self.assertRaisesRegex(ValidationError,'shared material identity'):
            apply(self.project,self.book,self.plan,self.out)
        self.assertFalse(self.out.exists())
    def test_unrelated_tray_only_material_alias_refused(self):
        def change(doc):
            n,_,b=index(doc)
            b['unrelated']['material']=copy.deepcopy(n['sample-0-0']['material'])
        self.rewrite(change)
        with self.assertRaisesRegex(ValidationError,'shared material identity'):
            apply(self.project,self.book,self.plan,self.out)
        self.assertFalse(self.out.exists())
    def test_ancestor_active_feature_refused(self):
        self.rewrite(lambda d:index(d)[0]['assembly']['featureManager']['uniqueFeatures'].append({'invented':'active'}))
        with self.assertRaisesRegex(ValidationError,'ancestor features'):
            apply(self.project,self.book,self.plan,self.out)
        self.assertFalse(self.out.exists())
    def test_nested_ancestor_current_feature_state_refused(self):
        self.rewrite(lambda d:index(d)[0]['glyph-container']['featureManager']['currentStateIndices'].append(0))
        with self.assertRaisesRegex(ValidationError,'ancestor features'):
            apply(self.project,self.book,self.plan,self.out)
        self.assertFalse(self.out.exists())
    def test_missing_ancestor_feature_state_refused(self):
        self.rewrite(lambda d:index(d)[0]['assembly'].pop('featureManager'))
        with self.assertRaisesRegex(ValidationError,'ancestor features'):
            apply(self.project,self.book,self.plan,self.out)
        self.assertFalse(self.out.exists())
    def test_differential_compose_translation_refused(self):
        self.rewrite(lambda d:index(d)[2]['sample-0-0']['composeTransform'].__setitem__(3,D('.01')))
        with self.assertRaisesRegex(ValidationError,'Nonidentity composeTransform'):
            apply(self.project,self.book,self.plan,self.out)
        self.assertFalse(self.out.exists())
    def test_unrelated_body_differential_compose_refused(self):
        self.rewrite(lambda d:index(d)[2]['unrelated']['composeTransform'].__setitem__(7,D('.01')))
        self.refused()
    def test_common_compose_translation_refused_without_native_semantics(self):
        def change(doc):
            for b in index(doc)[2].values():
                b['composeTransform'][3]=D('.25');b['composeTransform'][7]=D('-.125')
        self.rewrite(change)
        with self.assertRaisesRegex(ValidationError,'Nonidentity composeTransform'):
            apply(self.project,self.book,self.plan,self.out)
        self.assertFalse(self.out.exists())
    def test_compose_rotation_refused(self):
        self.rewrite(lambda d:index(d)[2]['sample-0-0']['composeTransform'].__setitem__(0,D('.5')))
        self.refused()
    def test_large_common_compose_translation_refused(self):
        def change(doc):
            for b in index(doc)[2].values():b['composeTransform'][3]=D('100')
        self.rewrite(change);self.refused()
    def test_different_tray_linear_blocks_refused_even_inside_profile_epsilon(self):
        self.rewrite(lambda d:index(d)[2]['sample-0-0']['transform'].__setitem__(0,D('1e-13')))
        self.refused()
    def test_missing_compose_transform_refused(self):
        self.rewrite(lambda d:index(d)[2]['sample-0-0'].pop('composeTransform'));self.refused()
    def test_check_plan_refuses_serializer_precision_domain(self):
        replacement=self.root/'precision.xlsx'
        old=b'2 / 0 / 0 / 0 / 98 / 0'
        new=b'0.123456789012345678 / 0 / 0 / 0 / 99.876543210987654322 / 0'
        with zipfile.ZipFile(self.book) as src,zipfile.ZipFile(replacement,'x') as dst:
            for info in src.infolist():
                raw=src.read(info)
                if info.filename.endswith('sheet1.xml'):raw=raw.replace(old,new)
                dst.writestr(info,raw)
        replacement.replace(self.book);self.plan['workbook_sha256']=digest(self.book)
        self.plan['samples'][0]['expected_percentages']=new.decode().split(' / ')
        with self.assertRaisesRegex(ValidationError,'cannot survive native binary64'):
            prepare(self.project,self.book,self.plan)
        self.refused()
    def test_reviewed_ids_common_translation_preserved_without_interpretation(self):
        self.common_translation();self.reviewed_ids()
        before=project_document(self.project)
        report=apply(self.project,self.book,self.plan,self.out)
        self.assertEqual(report['mapping_mode'],'reviewed_exact_ids')
        self.assertEqual(report['placement_interpretation'],'not_interpreted_source_transforms_preserved')
        self.assertFalse(report['physical_mapping_automatically_verified'])
        bb=index(before)[2];ab=index(project_document(self.out/'candidate_UNVERIFIED.PRINT'))[2]
        for oid in bb:
            self.assertEqual(bb[oid]['transform'],ab[oid]['transform'])
            self.assertEqual(bb[oid]['composeTransform'],ab[oid]['composeTransform'])
    def test_reviewed_ids_are_not_derived_from_translation_ranks(self):
        def change(doc):
            bodies=index(doc)[2]
            bodies['sample-0-0']['transform'][3]=D('.5')
            bodies['sample-1-1']['transform'][3]=D('-.2')
        self.rewrite(change);self.common_translation();self.reviewed_ids()
        # This artificial fixture's IDs are the externally supplied mapping;
        # no geometric/native correctness claim is made by the writer.
        report=apply(self.project,self.book,self.plan,self.out)
        self.assertEqual(report['changed_count'],4)
        self.assertFalse(report['physical_mapping_automatically_verified'])
    def test_reviewed_ids_require_mapping_digest(self):
        self.common_translation();self.reviewed_ids();self.plan['review'].pop('mapping_sha256');self.refused()
    def test_reviewed_ids_reject_stale_mapping_binding(self):
        self.common_translation();self.reviewed_ids()
        a,b=self.plan['samples'][:2]
        a['cell'],b['cell']=b['cell'],a['cell']
        a['expected_percentages'],b['expected_percentages']=b['expected_percentages'],a['expected_percentages']
        with self.assertRaisesRegex(ValidationError,'mapping binding differs'):
            prepare(self.project,self.book,self.plan)
        self.assertFalse(self.out.exists())
    def test_reviewed_ids_reject_axes_as_pseudo_mapping_evidence(self):
        self.common_translation();axes=copy.deepcopy(self.plan['axes']);self.reviewed_ids();self.plan['axes']=axes;self.refused()
    def test_reviewed_ids_still_reject_ancestor_alias(self):
        def change(doc):
            n,_,_=index(doc);n['assembly']['material']=copy.deepcopy(n['sample-0-0']['material'])
        self.rewrite(change);self.common_translation();self.reviewed_ids();self.refused()
    def test_reviewed_ids_still_reject_ancestor_features(self):
        self.rewrite(lambda d:index(d)[0]['assembly']['featureManager']['uniqueFeatures'].append({'invented':'active'}))
        self.common_translation();self.reviewed_ids();self.refused()
    def test_reviewed_ids_still_reject_rotation_in_compose_form(self):
        self.common_translation()
        self.rewrite(lambda d:index(d)[2]['sample-0-0']['composeTransform'].__setitem__(1,D('1e-13')))
        self.reviewed_ids();self.refused()
    def test_reviewed_ids_reject_unobserved_per_body_compose_offsets(self):
        self.common_translation()
        self.rewrite(lambda d:index(d)[2]['sample-0-0']['composeTransform'].__setitem__(3,D('-.22')))
        self.reviewed_ids();self.refused()
    def test_reviewed_ids_still_require_complete_plan(self):
        self.common_translation();self.reviewed_ids();self.plan['samples'].pop();self.refused()
    def test_reviewed_ids_still_reject_preserved_tray_only_material_alias(self):
        def change(doc):
            n,_,b=index(doc);b['unrelated']['material']=copy.deepcopy(n['sample-0-0']['material'])
        self.rewrite(change);self.common_translation();self.reviewed_ids();self.refused()
    def test_reviewed_ids_do_not_skip_serializer_domain(self):
        self.common_translation();self.reviewed_ids()
        self.test_check_plan_refuses_serializer_precision_domain()
    def test_reviewed_ids_require_numeric_compose_translation_entries(self):
        self.common_translation()
        self.rewrite(lambda d:index(d)[2]['sample-0-0']['composeTransform'].__setitem__(3,'-.21'))
        self.reviewed_ids();self.refused()


if __name__=='__main__':unittest.main()
