"""Exact nearest-rank equivalence and bounded lookup work; synthetic data only."""
import math
from pathlib import Path
import random
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import desktop_core as core


def original_rank(axis, value):
    return min(range(len(axis)), key=lambda j: abs(axis[j] - value))


class CountingAxis:
    """Count indexed reads without imposing wall-clock timing requirements."""
    def __init__(self, values):
        self.values = values
        self.reads = 0

    def __len__(self):
        return len(self.values)

    def __getitem__(self, index):
        self.reads += 1
        return self.values[index]


class GridRankPerformanceTests(unittest.TestCase):
    def assert_rank_equivalent(self, axis, value, *, finite_axis=True):
        self.assertEqual(core._nearest_rank(axis, value, finite_axis=finite_axis),
                         original_rank(axis, value), (axis, value))

    def test_exact_centers_midpoint_ties_duplicates_and_boundaries(self):
        for axis in ([0.0], [-0.0, 0.0], [-4.0, -1.0, 2.0, 5.0],
                     [-2.0, -2.0, 0.0, 0.0, 2.0, 2.0]):
            points = list(axis) + [-100.0, 100.0]
            for left, right in zip(axis, axis[1:]):
                midpoint = (left + right) / 2
                points.extend((midpoint, math.nextafter(midpoint, -math.inf),
                               math.nextafter(midpoint, math.inf)))
            for value in points:
                with self.subTest(axis=axis, value=value):
                    self.assert_rank_equivalent(axis, value)
        self.assertEqual(core._nearest_rank([0.0, 2.0], 1.0), 0)

    def test_rounded_distance_ties_choose_first_not_nearest_neighbor_index(self):
        # Floating subtraction can tie over several centers, not just a midpoint.
        cases = [([0.0, 1.0, 2.0], 1e20),
                 ([-2.0, -1.0, 0.0], -1e20),
                 ([0.0, 1.0, 2.0], 1e308),
                 ([-1.7e308, -1.6e308, -1.5e308], 1.7e308),
                 ([0.0, math.ulp(0.0), 2 * math.ulp(0.0)], 1.0)]
        for axis, value in cases:
            with self.subTest(axis=axis, value=value):
                self.assert_rank_equivalent(axis, value)

    def test_random_uniform_axes_and_near_boundaries(self):
        rng = random.Random(2170)
        for _ in range(250):
            axis = sorted(rng.uniform(-1e6, 1e6) for _ in range(rng.randrange(1, 150)))
            points = [rng.uniform(-2e6, 2e6) for _ in range(8)]
            center = rng.choice(axis)
            points.extend((center, math.nextafter(center, -math.inf),
                           math.nextafter(center, math.inf)))
            for value in points:
                self.assert_rank_equivalent(axis, value)

    def test_random_finite_binary64_extremes(self):
        rng = random.Random(11936)

        def finite_float():
            while True:
                value = struct.unpack('!d', rng.getrandbits(64).to_bytes(8, 'big'))[0]
                if math.isfinite(value):
                    return value

        for _ in range(250):
            axis = sorted(finite_float() for _ in range(rng.randrange(1, 100)))
            for value in [finite_float() for _ in range(8)] + [rng.choice(axis)]:
                self.assert_rank_equivalent(axis, value)

    def test_nonfinite_inputs_preserve_original_fallback_behavior(self):
        axes = [[-math.inf, 0.0, math.inf], [0.0, math.inf],
                [-math.inf, -1.0, 1.0], [math.nan, 0.0, 1.0],
                [0.0, math.nan, 1.0], [math.inf]]
        for axis in axes:
            for value in (-math.inf, -1.0, 0.0, 1.0, math.inf, math.nan):
                self.assert_rank_equivalent(axis, value, finite_axis=False)
        for value in (-math.inf, math.inf, math.nan):
            self.assert_rank_equivalent([-1.0, 0.0, 1.0], value)

    def test_empty_axis_preserves_refusal(self):
        for finite_axis in (False, True):
            with self.assertRaises(ValueError):
                core._nearest_rank([], 0.0, finite_axis=finite_axis)

    def test_lookup_work_stays_logarithmic_including_wide_tie_plateau(self):
        count = 65536
        values = [float(i) for i in range(count)]
        for value in (-1e20, 0.0, 32767.5, 65535.0, 1e20):
            axis = CountingAxis(values)
            self.assertEqual(core._nearest_rank(axis, value), original_rank(values, value))
            self.assertLessEqual(axis.reads, 2 * math.ceil(math.log2(count)) + 10)

    def test_skinny_grid_ranks_are_exhaustive_in_both_axes(self):
        for varying_axis in (0, 1):
            records = []
            for rank in range(2048):
                center = [0.0, 0.0, 1.0]
                center[varying_axis] = rank * 12.0
                records.append({'id': str(rank), 'center': center,
                                'bounds': [[center[0] - 4, center[1] - 4, 0],
                                           [center[0] + 4, center[1] + 4, 2]]})
            axes, ranks, basis = core._shape_grid(records, {})
            self.assertEqual(basis, 'mesh-footprint-centers')
            self.assertEqual(len(axes[varying_axis]), len(records))
            self.assertEqual(len(axes[1 - varying_axis]), 1)
            expected = {str(i): (i, 0) if varying_axis == 0 else (0, i)
                        for i in range(len(records))}
            self.assertEqual(ranks, expected)


if __name__ == '__main__':
    unittest.main()
