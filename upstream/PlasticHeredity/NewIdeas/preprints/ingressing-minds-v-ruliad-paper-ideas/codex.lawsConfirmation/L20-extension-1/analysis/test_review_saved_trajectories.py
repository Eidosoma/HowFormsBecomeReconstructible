"""Synthetic, in-memory checks; never execute simulation or held-out extraction."""
import unittest
import numpy as np
from review_saved_trajectories import TARGETS, decode, shape, preference, first_negative, correlation


class SavedReviewTests(unittest.TestCase):
    def test_own_template(self):
        for role in (0, 1):
            s = shape(TARGETS[role], role)
            self.assertAlmostEqual(s['own_best'], 1.)
            self.assertAlmostEqual(s['alternative_best'], 0.)
            self.assertAlmostEqual(s['canonical_margin'], 1.)

    def test_translation_invariance(self):
        for role in (0, 1):
            original = shape(TARGETS[role], role)
            for shift in ((1, 3), (8, 4), (15, 15)):
                shifted = shape(np.roll(TARGETS[role], shift, (0, 1)), role)
                self.assertAlmostEqual(original['own_best'], shifted['own_best'])

    def test_scale_and_offset(self):
        for role in (0, 1):
            s = shape(3 * TARGETS[role] + 7, role)
            self.assertAlmostEqual(s['own_best'], 1.)

    def test_direct_fft_noise(self):
        rng = np.random.default_rng(17)
        for _ in range(10):
            for role in (0, 1):
                self.assertLess(shape(rng.normal(size=(16, 16)), role)['direct_fft_max_error'], 1e-12)

    def test_constant_shape(self):
        for value in (0., 1.):
            s = shape(np.full((16, 16), value), 0)
            self.assertEqual(s['own_best'], 0.)
            self.assertEqual(s['canonical_margin'], 0.)

    def test_shape_invalid(self):
        for value in (np.zeros(256), np.full((16, 16), np.nan)):
            with self.assertRaises(ValueError):
                shape(value, 0)
        with self.assertRaises(ValueError):
            shape(TARGETS[0], 2)

    def test_preference_strict_threshold(self):
        self.assertEqual(preference(.2 * TARGETS[0], 0), 0.)
        self.assertEqual(preference(.200001 * TARGETS[0], 0), .5)

    def test_preference_denominator_all_cells(self):
        v = np.zeros((16, 16))
        # Own A positive, alternative B negative here: one qualified contribution.
        v[0, 4] = 1.
        self.assertEqual(preference(v, 0), 1/256)

    def test_alternative_negative(self):
        self.assertEqual(preference(TARGETS[1], 0), -.5)
        self.assertEqual(preference(TARGETS[0], 1), -.5)

    def test_zero_not_negative(self):
        self.assertIsNone(first_negative([.1, 0., .2, 0.]))
        self.assertEqual(first_negative([.1, 0., -.01, .2]), 3)
        self.assertEqual(first_negative([-.1, .2, -.2, .1]), 1)

    def test_byte_record(self):
        encoded = np.frombuffer(TARGETS[0].astype('<f8').tobytes(), dtype=np.uint8)
        np.testing.assert_array_equal(decode(encoded), TARGETS[0])
        for packet in (np.zeros(2047, np.uint8), np.zeros(2048, float)):
            with self.assertRaises(ValueError):
                decode(packet)

    def test_correlation_degenerate(self):
        self.assertIsNone(correlation([1, 1], [1, 2]))
        self.assertIsNone(correlation([], []))
        self.assertAlmostEqual(correlation([1, 2, 3], [3, 2, 1]), -1.)
        with self.assertRaises(ValueError):
            correlation([1, 2], [1])


if __name__ == '__main__':
    unittest.main()
