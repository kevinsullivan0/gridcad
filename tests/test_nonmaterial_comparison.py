"""Differential guard tests against the original deep-copy preservation check."""
import copy
from decimal import Decimal
from pathlib import Path
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import desktop_core as core
from tools.make_desktop_examples import create


class NonmaterialComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = create(Path(self.temp.name)/'input')
        self.before = core.op.project_document(root/'DO_NOT_PRINT.PRINT')
        self.changed = {'synthetic-sample-1-1','synthetic-sample-1-2'}

    def original(self, before, after):
        return core.op.stripped(before, self.changed) == core.op.stripped(after, self.changed)

    def check(self, after):
        original_before, original_after = copy.deepcopy(self.before), copy.deepcopy(after)
        def result(fn):
            try:
                return bool(fn())
            except (KeyError, TypeError, ValueError, IndexError):
                return False  # Both implementations must refuse malformed state.
        expected = result(lambda: self.original(self.before, after))
        actual = result(lambda: core.op._same_nonmaterial(self.before, after, self.changed))
        self.assertEqual(actual, expected)
        self.assertEqual(self.before, original_before)
        self.assertEqual(after, original_after)
        return actual

    def test_exact_ignored_fields_and_untouched_fields(self):
        after = copy.deepcopy(self.before)
        nodes, _, bodies = core.op.index(after)
        for oid in self.changed:
            nodes[oid]['material'] = {'different':'complete assignment'}
            bodies[oid]['material'] = {'different':'complete assignment'}
            bodies[oid]['properties']['threeDAppearance']['value'].update(r=1,g=2,b=3,a=4)
        self.assertTrue(self.check(after))
        bodies['synthetic-sample-1-1']['properties']['threeDAppearance']['value']['unexpected'] = 5
        self.assertFalse(self.check(after))
        after = copy.deepcopy(self.before)
        _, _, bodies = core.op.index(after)
        bodies['synthetic-sample-2-2']['properties']['threeDAppearance']['value']['r'] = 17
        self.assertFalse(self.check(after))

    def test_seeded_scalar_mutations_match_original_guard(self):
        def leaves(value, path=()):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield from leaves(item,path+(key,))
            elif isinstance(value, list):
                for key, item in enumerate(value):
                    yield from leaves(item,path+(key,))
            else:
                yield path,value
        cases = list(leaves(self.before))
        rng = random.Random(4220)
        for path, old in rng.sample(cases, min(180,len(cases))):
            after = copy.deepcopy(self.before)
            target = after
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = ('different' if isinstance(old,str) else
                not old if isinstance(old,bool) else
                old+Decimal('0.125') if isinstance(old,(int,Decimal)) else 'different')
            with self.subTest(path=path):
                self.check(after)

    def test_missing_material_or_rgba_and_shared_appearance_refused(self):
        for field in ('material','r','g','b','a'):
            after = copy.deepcopy(self.before)
            nodes,_,bodies = core.op.index(after)
            if field == 'material':
                del nodes['synthetic-sample-1-1'][field]
            else:
                del bodies['synthetic-sample-1-1']['properties']['threeDAppearance']['value'][field]
            self.assertFalse(self.check(after))
        after = copy.deepcopy(self.before)
        _,_,bodies = core.op.index(after)
        bodies['synthetic-sample-1-2']['properties']['threeDAppearance']['value'] = bodies['synthetic-sample-1-1']['properties']['threeDAppearance']['value']
        self.assertFalse(self.check(after))

    def test_occurrence_tray_object_alias_refused_like_original(self):
        after = copy.deepcopy(self.before)
        nodes,_,bodies = core.op.index(after)
        oid = 'synthetic-sample-1-1'
        node, body = nodes[oid], bodies[oid]
        node.update({key: value for key, value in body.items() if key != 'id'})
        tray = after['project']['trays'][0]['trayBodies']
        tray[tray.index(body)] = node
        self.assertFalse(self.check(after))

    def test_reordered_lists_and_new_keys_are_not_ignored(self):
        after = copy.deepcopy(self.before)
        after['project']['trays'][0]['trayBodies'].reverse()
        self.assertFalse(self.check(after))
        after = copy.deepcopy(self.before)
        after['unexpected'] = {'material': {'r': 1}}
        self.assertFalse(self.check(after))

    def test_empty_changed_set_still_compares_everything(self):
        self.changed = set()
        self.assertTrue(self.check(copy.deepcopy(self.before)))
        after = copy.deepcopy(self.before)
        nodes,_,_ = core.op.index(after)
        nodes['synthetic-sample-1-1']['material']['id'] = 'altered'
        self.assertFalse(self.check(after))


if __name__ == '__main__':
    unittest.main()
