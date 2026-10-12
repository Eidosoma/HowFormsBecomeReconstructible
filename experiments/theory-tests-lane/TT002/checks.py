"""Behavioral checks for the matched-channel follow-up."""
import unittest
import numpy as np
import study as s


class Checks(unittest.TestCase):
    def test_latest_only_and_all_channels(self):
        d = s.e.synthetic(4, 4, seed=11)
        p = s.e.probe(d, 8)
        expected = d.features[:, 7].copy()
        p.features[:, :7] = 1e9
        np.testing.assert_array_equal(s.current_design(p), expected)
        self.assertEqual(s.current_design(p).shape, (16, 24))

    def test_test_labels_and_future_cannot_affect_forecasts(self):
        d = s.e.synthetic(8, 8, seed=12)
        train, test = d.take(d.groups < 6), d.take(d.groups >= 6)
        changed = test.take(np.arange(len(test.groups)))
        changed.features[:, 8:] = 1e8; changed.body[:, 8:] = ~changed.body[:, 8:]
        changed.terminal[:] = ~changed.terminal
        for model, p in [('current24_logistic', {'C': .1}), ('current24_boosted', {'leaves': 3, 'l2': 1})]:
            before = s.predict(model, p, train, s.e.probe(test, 8), 8, 'terminal')
            after = s.predict(model, p, train, s.e.probe(changed, 8), 8, 'terminal')
            np.testing.assert_array_equal(before, after)

    def test_reference_six_channel_logistic_compatibility(self):
        d = s.e.synthetic(8, 8, seed=13)
        train, test = d.take(d.groups < 6), d.take(d.groups >= 6)
        p = s.e.probe(test, 3)
        expected = s.e.predict('current_logistic', {'C': 1.}, train, p, 3, 'terminal')
        actual = s.predict('current24_logistic', {'C': 1.}, train, p, 3, 'terminal', columns=[0, 5, 6, 7, 8, 9])
        np.testing.assert_array_equal(expected, actual)

    def test_overlap_and_bad_measurements_rejected(self):
        d = s.e.synthetic(4, 4, seed=14)
        with self.assertRaises(ValueError):
            s.predict('current24_logistic', {'C': .1}, d, s.e.probe(d, 3), 3, 'terminal')
        p = s.e.probe(d, 3); p.observed[0, -1, 23] = False
        with self.assertRaises(ValueError): s.current_design(p)
        p.observed[:] = True; p.features[0, -1, 23] = np.nan
        with self.assertRaises(ValueError): s.current_design(p)

    def test_constant_class(self):
        d = s.e.synthetic(4, 4, seed=15)
        train, test = d.take(d.groups < 3), d.take(d.groups == 3)
        train.terminal[:] = False
        for model, param in [('current24_logistic', {'C': 1}), ('current24_boosted', {'leaves': 3, 'l2': 1})]:
            p = s.predict(model, param, train, s.e.probe(test, 3), 3, 'terminal')
            np.testing.assert_array_equal(p, np.full(4, .5/13))

    def test_score_endpoint_and_equal_block_weighting(self):
        d = s.e.synthetic(2, 2, seed=16)
        d.terminal[:] = True; d.body[:] = True; d.body[:, :3] = False
        p = np.array([.2, .4, .6, .8])
        result = s.scalar_scores(d, 'k3.future_path_and_terminal.example', p)
        self.assertAlmostEqual(result['brier'], sum((1-x)**2 for x in p)/4)
        self.assertEqual(result['observed_rate'], 1.)


if __name__ == '__main__':
    unittest.main(verbosity=2)
