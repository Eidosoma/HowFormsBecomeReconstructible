import unittest

import numpy as np

from memory_metrics import classify, opposite, perturb_recipient, recovery_decision, regulatory_distance


class MemoryMetricsTests(unittest.TestCase):
    def setUp(self):
        self.config = {"minimum_challenge_distance": .1, "recovery_absolute_tolerance": .02,
                       "recovery_distance_ratio": .2}

    def test_labels_and_strict_boundary(self):
        values = np.array([[5, 0, 2, 0], [0, 5, 0, 2]])
        np.testing.assert_array_equal(classify(values, {"miR200_total": 0, "Zeb_mRNA_total": 1}), ["E", "M", "X", "X"])
        self.assertEqual(classify(values[None], {"miR200_total": 0, "Zeb_mRNA_total": 1}).shape, (1, 4))

    def test_opposite(self):
        self.assertEqual(opposite("E"), "M")
        self.assertEqual(opposite("M"), "E")
        with self.assertRaises(ValueError):
            opposite("X")

    def test_perturbation_only_changes_recipient_regulators(self):
        state = np.arange(24, dtype=float).reshape(4, 6)
        original = state.copy()
        changed = perturb_recipient(state, np.array([100, 100, 100, 100]), [1, 2, 3], .2)
        np.testing.assert_array_equal(state, original)
        np.testing.assert_array_equal(changed[:, 1:], state[:, 1:])
        self.assertEqual(changed[0, 0], state[0, 0])
        np.testing.assert_allclose(changed[[1, 2, 3], 0], .8 * state[[1, 2, 3], 0] + 20)

    def test_distance_uses_reference_scales(self):
        self.assertAlmostEqual(regulatory_distance([1, 2, 3], [0, 0, 0], [10, 10, 10]), .3)
        with self.assertRaises(ValueError):
            regulatory_distance([1], [0], [0])

    def test_recovery_requires_substantive_challenge(self):
        self.assertFalse(recovery_decision(0, 0, "E", "E", "E", self.config)["recovered"])
        self.assertFalse(recovery_decision(.01, .001, "E", "E", "E", self.config)["recovered"])

    def test_same_label_without_distance_recovery_fails(self):
        self.assertFalse(recovery_decision(.2, .1, "E", "E", "E", self.config)["recovered"])

    def test_different_or_ambiguous_label_fails(self):
        self.assertFalse(recovery_decision(.2, .001, "E", "E", "M", self.config)["recovered"])
        self.assertFalse(recovery_decision(.2, .001, "X", "X", "X", self.config)["recovered"])

    def test_valid_recovery_passes(self):
        result = recovery_decision(.2, .01, "M", "M", "M", self.config)
        self.assertTrue(result["recovered"])
        self.assertAlmostEqual(result["distance_ratio"], .05)


if __name__ == "__main__":
    unittest.main()
