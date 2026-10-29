"""Preserve H038 controls and test confirmation logic independently."""
import io
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import model as m
from h038.fixtures import Fixtures as DynamicsFixtures
from h039 import design as d
from h039.inference import infer


class ConfirmationFixtures(unittest.TestCase):
    def positive(self):
        return {k: dict(mean=.8, adjusted_lower=.2) for k in d.ENDPOINTS}

    def test_positive_and_integrity_gate(self):
        self.assertTrue(d.decisions(self.positive())['primary_qualified'])
        result = d.decisions(self.positive(), integrity_passed=False)
        self.assertFalse(result['primary_qualified'])
        self.assertFalse(result['original_reader_qualified'])
        self.assertFalse(result['uninterrupted_qualified'])

    def test_small_effect_cannot_pass_on_direction_alone(self):
        values = self.positive(); values['serial_benefit_at_gain8']['mean'] = .099
        result = d.decisions(values)
        self.assertFalse(result['primary_qualified'])
        self.assertFalse(result['original_reader_qualified'])

    def test_every_control_is_required(self):
        for control in d.CONTROLS:
            values = self.positive(); values['own_minus_'+control]['adjusted_lower'] = 0
            self.assertFalse(d.decisions(values)['primary_qualified'], control)

    def test_secondary_verdicts_stay_separate(self):
        values = self.positive(); values['serial_benefit_at_gain4']['adjusted_lower'] = 0
        result = d.decisions(values)
        self.assertTrue(result['primary_qualified']); self.assertFalse(result['original_reader_qualified'])
        self.assertTrue(result['uninterrupted_qualified'])
        values = self.positive(); values['path_gain8']['mean'] = .49
        result = d.decisions(values)
        self.assertTrue(result['primary_qualified']); self.assertTrue(result['original_reader_qualified'])
        self.assertFalse(result['uninterrupted_qualified'])

    def test_positive_task_and_copy_controls_required(self):
        for name in ('g0_renewal_gain8', 'g16_protected_gain8', 'g16_8_8'):
            values = self.positive(); values[name]['mean'] = .1
            self.assertFalse(d.decisions(values)['primary_qualified'])

    def test_bootstrap_against_independent_network_counts(self):
        count, draws = 64, 37
        summaries = [dict(block=d.FIRST_BLOCK+i) for i in range(count)]
        def endpoints(s):
            i = s['block']-d.FIRST_BLOCK
            return {k: ((i+3*j)%17)/16 for j, k in enumerate(d.ENDPOINTS)}
        values = np.array([list(endpoints(s).values()) for s in summaries])
        with patch.object(d, 'endpoints', side_effect=endpoints), patch.object(d, 'BOOTSTRAPS', draws):
            result = infer(summaries, True)
        random = m.rng(d.ANALYSIS_SEED, 'H039 whole-network bootstrap')
        expected = []
        for _ in range(draws):
            frequencies = np.bincount(random.integers(0, count, count), minlength=count)
            expected.append(np.sum(frequencies[:, None]*values, axis=0)/count)
        expected = np.array(expected)
        for j, name in enumerate(d.ENDPOINTS):
            row = result['estimates'][name]
            np.testing.assert_allclose([row['low'], row['high']], np.quantile(expected[:, j], [.025, .975]), atol=1e-14, rtol=0)
            if name in d.FAMILY:
                self.assertAlmostEqual(row['adjusted_lower'], float(np.quantile(expected[:, j], .05/12)), places=14)
        self.assertEqual(result['networks'], 64)

    def test_duplicate_networks_rejected(self):
        with self.assertRaises(AssertionError):
            infer([dict(block=0), dict(block=0)], False)


def run_tests(path):
    suite = unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(DynamicsFixtures),
        unittest.defaultTestLoader.loadTestsFromTestCase(ConfirmationFixtures)])
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    Path(path).write_text(stream.getvalue())
    if not result.wasSuccessful():
        raise AssertionError(stream.getvalue())
    return dict(tests=result.testsRun, passed=True, original_dynamics_controls=8)
