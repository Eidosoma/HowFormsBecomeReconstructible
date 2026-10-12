"""Adversarial evaluator checks on excluded synthetic and exact finite inputs."""
import json
from pathlib import Path
import unittest

import numpy as np

import evaluator as e
from operators import probabilities, short_probe_counterexample

PLAN = json.loads((Path(__file__).parent/'plan.json').read_text())


class EvaluatorChecks(unittest.TestCase):
    def test_group_splits(self):
        groups = np.repeat(np.arange(32000, 32032), 16)
        outer = e.group_folds(groups, 4)
        np.testing.assert_array_equal(outer, (groups-32000) % 4)
        for f in range(4):
            self.assertEqual(len(set(groups[outer == f])), 8)
            tr = groups[outer != f]
            inner = e.group_folds(tr, 3)
            for j in range(3):
                self.assertFalse(set(tr[inner == j]) & set(tr[inner != j]))

    def test_future_excluded_from_features(self):
        a = e.synthetic(8, 4, seed=3)
        b = a.take(np.arange(len(a.groups)))
        for k in (3, 8):
            b.features[:, k:] = 1e9
            b.body[:, k:] = ~a.body[:, k:]
            b.terminal[:] = ~a.terminal
            for model in ('current_logistic', 'prefix_logistic'):
                np.testing.assert_array_equal(e.design(e.probe(a, k), model),
                                              e.design(e.probe(b, k), model))
            b = a.take(np.arange(len(a.groups)))

    def test_heldout_labels_cannot_change_predictions(self):
        a = e.synthetic(8, 4, seed=9)
        train, test = a.take(a.groups < 6), a.take(a.groups >= 6)
        changed = test.take(np.arange(len(test.groups)))
        changed.terminal[:] = ~test.terminal
        changed.body[:, 8:] = ~test.body[:, 8:]
        changed.features[:, 8:] = 1e6
        for model in PLAN['models']:
            params = e.candidates(model, PLAN)[0]
            before = e.predict(model, params, train, e.probe(test, 8), 8, 'terminal')
            after = e.predict(model, params, train, e.probe(changed, 8), 8, 'terminal')
            np.testing.assert_array_equal(before, after)

    def test_overlap_rejected(self):
        a = e.synthetic(4, 4)
        with self.assertRaises(ValueError):
            e.predict('prevalence', {}, a, e.probe(a, 3), 3, 'terminal')

    def test_single_class(self):
        a = e.synthetic(4, 4)
        train, test = a.take(a.groups < 3), a.take(a.groups == 3)
        train.terminal[:] = True
        for model in ('current_logistic', 'prefix_logistic', 'prefix_boosted'):
            p = e.predict(model, e.candidates(model, PLAN)[0], train, e.probe(test, 3), 3, 'terminal')
            np.testing.assert_array_equal(p, np.full(4, 12.5/13))

    def test_future_path_excludes_prefix(self):
        a = e.synthetic(2, 2)
        a.body[:] = True; a.terminal[:] = True
        a.body[:, :3] = False
        self.assertTrue(e.target(a, 3, 'future_path_and_terminal').all())
        a.body[0, 3] = False
        self.assertFalse(e.target(a, 3, 'future_path_and_terminal')[0])

    def test_equal_block_weighting(self):
        np.testing.assert_array_equal(e.block_means([1, 0, 0, 0], [0, 1, 1, 1]), [1, 0])

    def test_probability_rejection(self):
        for p in [np.array([np.nan]), np.array([1.1])]:
            with self.assertRaises(ValueError):
                e.losses(np.array([1]), p)

    def test_masked_measurement_not_zero(self):
        a = e.synthetic(2, 2)
        before = e.design(e.probe(a, 3), 'prefix_logistic')
        a.features[:, 0, 13:16] = 1e9
        np.testing.assert_array_equal(before, e.design(e.probe(a, 3), 'prefix_logistic'))

    def test_markov_exact_path(self):
        a = e.synthetic(2, 2)
        a.body[:, :3] = True
        transition = np.repeat(np.array([[[.7, .3], [.2, .8]]]), 31, axis=0)
        readout = np.array([.1, .9])
        terminal = e.markov_predict((transition, readout), e.probe(a, 3), 'terminal')
        expected = np.array([0., 1.])@np.linalg.matrix_power(transition[0], 29)@readout
        np.testing.assert_allclose(terminal, expected)
        np.testing.assert_allclose(e.markov_predict((transition, readout), e.probe(a, 3),
                                                   'future_path_and_terminal'), .8**29*.9)

    def test_joint_pass_correlation(self):
        k = [[.5, .5], [.5, .5]]
        terminal, path = probabilities([1, 0], k, [[.5, 0], [.5, 0]], [1, 0], 1)
        self.assertEqual(terminal, .5)
        self.assertEqual(path, .5)
        self.assertNotEqual(path, .5*terminal)

    def test_two_state_channel(self):
        for h in (0, 1, 3, 32):
            p, a, b = .07, .9, .2
            k = [[1-p, p], [p, 1-p]]
            terminal, _ = probabilities([1, 0], k, k, [a, b], h)
            self.assertAlmostEqual(terminal, (a+b)/2+(a-b)/2*(1-2*p)**h)

    def test_nonidentifiable_short_probe(self):
        witness = short_probe_counterexample()
        self.assertEqual(witness['prefix_observations_a'], witness['prefix_observations_b'])
        self.assertEqual(witness['terminal_a'], 1.)
        self.assertEqual(witness['terminal_b'], 0.)


if __name__ == '__main__':
    unittest.main(verbosity=2)
