"""Scientific boundary, numerical, task-independence and decision controls."""
from __future__ import annotations

import io
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import model as m
from h035 import design as d, experiment as e
from h035.audit import audit, reference_relax
from h035.analysis import screens


class Fixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.short = e.lineage('fixture', 0, generations=1)

    def test_two_independent_history_bits(self):
        np.testing.assert_array_equal(d.CUE_AXES @ d.CUE_AXES.T, 4*np.eye(2))
        self.assertEqual(len(np.unique(d.RULES, axis=0)), 4)
        for arm, task in (('foreign_a', 0), ('foreign_b', 1)):
            donor = d.RULES[d.DONORS[arm]]
            np.testing.assert_array_equal(donor[:, task], -d.RULES[:, task])
            np.testing.assert_array_equal(donor[:, 1-task], d.RULES[:, 1-task])

    def test_single_rule_budget_does_not_double_record_strength(self):
        founder = self.short['founder'].astype(float)
        for l, s in ((0, [0, 1]), (1, [2, 3])):
            np.testing.assert_array_equal(self.short['initial'][l], m.write_body(founder[:, s]))
        np.testing.assert_array_equal(self.short['initial'][2], m.write_body(founder))

    def test_selective_irrelevant_history_cannot_change_single_rule(self):
        for l, arm in ((0, 'foreign_b'), (1, 'foreign_a')):
            a = d.ARMS.index(arm)
            np.testing.assert_array_equal(self.short['records'][:, l, a], self.short['records'][:, l, 0])
            np.testing.assert_array_equal(self.short['reader_states'][:, l, a], self.short['reader_states'][:, l, 0])

    def test_gain_is_symmetric_and_uses_only_cue_incident_edges(self):
        w = e.effective_weights(self.short['base'], self.short['initial'])
        np.testing.assert_array_equal(w, w.swapaxes(-1, -2))
        self.assertFalse(np.diagonal(w, axis1=-1, axis2=-2).any())
        plain = self.short['base']+self.short['initial']
        np.testing.assert_array_equal(w[..., :4, :4], plain[..., :4, :4])
        np.testing.assert_array_equal(w[..., 4:, 4:], plain[..., 4:, 4:])
        np.testing.assert_array_equal(w[..., :4, 4:], 4*plain[..., :4, 4:])

    def test_sequential_scalar_energy_and_reference(self):
        r = np.random.default_rng(350350)
        w = m.symmetric(r.normal(size=(12, 12)))
        x = r.choice([-1., 1.], size=12); x[:2] = [-1., 1.]
        order = np.array([r.permutation(12) for _ in range(8)])
        scalar, energies = x.copy(), [m.energy(x, w)]
        for sweep in order:
            for i in sweep:
                if i < 2:
                    continue
                field = sum(float(w[i, j])*float(scalar[j]) for j in range(12))
                if field != 0:
                    scalar[i] = 1 if field > 0 else -1
                energies.append(m.energy(scalar, w))
        self.assertLessEqual(float(np.diff(energies).max()), 1e-12)
        np.testing.assert_array_equal(m.relax(w, x, order, [0, 1], [-1, 1]), scalar)
        np.testing.assert_array_equal(reference_relax(w, x, order, [0, 1], [-1, 1]), scalar)

    def test_zero_field_preserves_previous_bit(self):
        x = np.array([1., -1., 1., -1.])
        np.testing.assert_array_equal(m.relax(np.zeros((4, 4)), x, [[3, 1, 2, 0]]), x)

    def test_score_requires_each_rule_both_polarities_both_patches(self):
        states = np.ones((4, 2, 4, 64))
        states[..., 8:16] = d.TARGETS[:, None, :, None]
        states[..., 16:24] = -d.TARGETS[:, None, :, None]
        self.assertTrue(e.score(states)[2].all())
        states[0, 0, 2, 8:16] *= -1
        rule, joint = e.score(states)[1:]
        self.assertTrue(rule[0, 0, 0]); self.assertFalse(rule[0, 0, 1]); self.assertFalse(joint[0, 0])
        states[0, 0, 2, 8:16] *= -1
        states[0, 0, 0, 8:16] *= .5
        self.assertFalse(e.score(states)[1][0, 0, 0])

    def test_reader_cannot_use_scorers_teacher_or_history_labels(self):
        raw = self.short
        args = (raw['records'][0], raw['base'], raw['assay_birth'][0], raw['assay_orders'][0], d.CUES)
        before = args[0].copy()
        expected = e.read(*args)
        with patch.object(d, 'TARGETS', np.full_like(d.TARGETS, np.nan)), patch.object(d, 'RULES', -d.RULES):
            np.testing.assert_array_equal(e.read(*args), expected)
        np.testing.assert_array_equal(args[0], before)

    def test_full_boundary_audit(self):
        self.assertTrue(audit(self.short, 'fixture', 0)['passed'])

    def test_erasure_removes_history_information(self):
        for arm in ('erased', 'read_off'):
            r = self.short['records'][1, :, d.ARMS.index(arm)]
            np.testing.assert_array_equal(r, np.broadcast_to(r[:, :1], r.shape))

    def test_no_generation_reset_to_founder_in_copy_controls(self):
        raw = self.short
        for arm in ('protected_copy', 'damaged_copy'):
            a = d.ARMS.index(arm)
            expected = raw['records'][0, :, a]
            if arm == 'damaged_copy':
                expected = expected * raw['damage'][0]
            np.testing.assert_array_equal(raw['records'][1, :, a], expected)
        self.assertFalse(raw['records'][1, :, d.ARMS.index('write_off')].any())

    def test_pilot_namespaces_independent_of_engineering(self):
        self.assertFalse(np.array_equal(d.random('pilot', 0, 'base').normal(size=64),
                                       d.random('engineering', 0, 'base').normal(size=64)))
        np.testing.assert_array_equal(d.random('pilot', 0, 'base').normal(size=64),
                                      d.random('pilot', 0, 'base').normal(size=64))

    def test_failed_starting_task_cannot_be_rescued_by_rewriting_scores(self):
        j = np.zeros((5, 3, 11)); r = np.ones((5, 3, 11, 2))
        donors = {a: r.copy() for a in d.DONORS}
        j[:, :, 0] = 1
        # Protected-copy positive control deliberately fails.
        result = screens(j, r, donors, d.CHECKPOINTS)
        self.assertEqual(result['verdict'], 'STARTING_TASK_LIMITED')
        self.assertFalse(result['rewriting_lead'])
        self.assertFalse(result['confirmation'])

    def test_one_rule_cannot_substitute_for_joint_success(self):
        j = np.ones((5, 3, 11)); r = np.ones((5, 3, 11, 2))
        j[-1, 2, 0] = 0
        donors = {a: r.copy() for a in d.DONORS}
        result = screens(j, r, donors, d.CHECKPOINTS)
        self.assertFalse(result['gates']['rewriting']['g16_both_joint'])
        self.assertFalse(result['rewriting_lead'])


def run_tests(path):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Fixtures))
    Path(path).write_text(stream.getvalue())
    if not result.wasSuccessful():
        raise AssertionError('H035 fixtures failed; see '+str(path))
    return dict(tests=result.testsRun, passed=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
