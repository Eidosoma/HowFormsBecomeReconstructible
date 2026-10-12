"""Meaningful boundary, perturbation, replay and inference checks on excluded synthetic inputs."""
import copy
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import cap_cpus, rng
from E055_stress_capture_recovery import model, audit_model, inference, audit
from E055_stress_capture_recovery.plan import settings
import numpy as np


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cap_cpus(1)
        cls.cfg = settings('fixture'); cls.cfg['recipients'] = 1
        cls.w = rng('E055', 'tests').uniform(-1, 1, (3, 4, 1, 2, 16, 16))
        cls.body = model.develop(cls.w, 900099, cls.cfg)
        cls.out = model.transmit(cls.body, cls.cfg)
        cls.fresh = model.assay(cls.out['packets'], 900099, cls.cfg)
        cls.cases, cls.controls = model.diagnostics(cls.body, cls.out, cls.fresh, cls.cfg)

    def test_independent_whole_pipeline(self):
        b = audit_model.develop(self.w, 900099, self.cfg); audit.compare(b, self.body)
        o = audit_model.transmit(b, self.cfg); audit.compare(o, self.out)
        f = audit_model.assay(o['packets'], 900099, self.cfg); audit.compare(f, self.fresh)
        c, controls = audit_model.diagnostics(b, o, f, self.cfg)
        audit.compare(c, self.cases); self.assertEqual(controls, self.controls)

    def test_zero_pulse_equivalence(self):
        cfg = dict(self.cfg, pulse_amplitude=0.)
        b = model.develop(self.w, 900099, cfg); o = model.transmit(b, cfg)
        np.testing.assert_array_equal(b['states'][:, 0], b['states'][:, 1])
        np.testing.assert_array_equal(o['packets'][:, 0], o['packets'][:, 1])
        np.testing.assert_array_equal(o['packets'][:, 2], o['packets'][:, 3])

    def test_before_pulse_pairing(self):
        self.assertTrue(self.controls['before_equal'])
        v = self.body['initial']; noninput = ~model.P[0]
        np.testing.assert_array_equal(v[..., 0, :, :][..., noninput], v[..., 1, :, :][..., noninput])

    def test_rule_blind_pulse_and_support(self):
        field = self.body['pulse_field']; chosen = self.body['pulse_sites']
        np.testing.assert_array_equal(field[::2], field[1::2])
        self.assertFalse(chosen[..., model.P.any(axis=0)].any())
        self.assertFalse((chosen & self.body['masks']).any())
        self.assertTrue((chosen.sum(axis=(-2, -1)) == 64).all())
        self.assertTrue(np.array_equal(abs(field) > 0, chosen))

    def test_dose_and_clipping_accounting(self):
        expected = self.cfg['pulse_steps']*64*(self.cfg['dt']*self.cfg['pulse_amplitude'])**2
        np.testing.assert_allclose(self.body['requested_squared'], expected)
        self.assertTrue((self.body['delivered_squared'] <= expected+1e-12).all())
        self.assertTrue((self.body['clipping_count'] >= 0).all())

    def test_large_pulse_clipping_is_retained(self):
        cfg = dict(self.cfg, pulse_amplitude=100.)
        b = model.develop(self.w, 900099, cfg)
        self.assertGreater(b['clipping_count'].sum(), 0)
        self.assertLessEqual(abs(b['states']).max(), 2.)
        audit.compare(b, audit_model.develop(self.w, 900099, cfg))

    def test_absent_cells_and_masked_edges(self):
        self.assertTrue((self.body['states']*self.body['masks'][None, None, None, :, :, None] == 0).all())
        w = model.base.decode(self.out['packets'])
        self.assertTrue((w*~self.body['available'][None, None] == 0).all())

    def test_exact_fallback(self):
        state = np.ones((1, 4, 1, 2, 16, 16))*.2
        w, ordinary, contrast, fallback = model.capture(state, np.ones((4, 1, 2, 16, 16), bool), 3.)
        self.assertTrue(fallback.all()); self.assertFalse(contrast.any())
        np.testing.assert_array_equal(w, ordinary)

    def test_tiny_nonzero_contrast_is_not_tolerance(self):
        state = np.ones((1, 4, 1, 2, 16, 16))*1e-8; state[..., 1, :, :] *= -1
        w, ordinary, contrast, fallback = model.capture(state, np.ones((4, 1, 2, 16, 16), bool), 3.)
        self.assertFalse(fallback.any()); self.assertTrue((contrast > 0).all())
        np.testing.assert_array_equal(w, contrast)

    def test_capture_cannot_read_incoming_values(self):
        changed = dict(self.body, effective=self.body['effective']*0.)
        other = model.transmit(changed, self.cfg)
        np.testing.assert_array_equal(other['packets'][:, :4], self.out['packets'][:, :4])
        self.assertFalse(model.base.decode(other['packets'][:, 4:6]).any())

    def test_later_state_cannot_change_early_capture(self):
        changed = dict(self.body, states=self.body['states'].copy())
        changed['states'][:, :, 2] = 0.
        other = model.transmit(changed, self.cfg)
        np.testing.assert_array_equal(other['packets'][:, :2], self.out['packets'][:, :2])
        self.assertFalse(np.array_equal(other['packets'][:, 2:4], self.out['packets'][:, 2:4]))

    def test_capture_does_not_mutate_body(self):
        before = {k: v.copy() for k, v in self.body.items()}
        model.transmit(self.body, self.cfg)
        audit.compare(before, self.body)

    def test_protected_boundary_and_fresh_reader(self):
        for key in ('protected_packets_equal', 'protected_end_equal', 'protected_traces_equal'):
            self.assertTrue(self.controls[key])
        H, A, F, R = self.out['packets'].shape[:4]
        initial = self.fresh['birth']
        self.assertEqual(initial.shape, (F, R, 3, 16, 16))
        self.assertTrue((self.cases['fresh_both'][:, 4] == self.cases['fresh_both'][:, 5]).all())

    def test_packet_corruption_rejected(self):
        changed = {k: v.copy() for k, v in self.out.items()}; changed['packets'].flat[0] ^= 1
        with self.assertRaises(AssertionError): audit.compare(self.out, changed)

    def test_state_hash_corruption_rejected(self):
        changed = {k: v.copy() for k, v in self.body.items()}; changed['state_hashes'].flat[0] ^= 1
        with self.assertRaises(AssertionError): audit.compare(self.body, changed)

    def test_independent_nonconstant_block_statistics(self):
        other = {k: v.copy() for k, v in self.cases.items()}
        other['fresh_both'][:, 1] = ~other['fresh_both'][:, 1]
        cases = [self.cases, other]; controls = [self.controls]*2
        s = inference.analyze(cases, controls, 'scientific')
        self.assertGreater(audit.check_summary(s, cases, controls, 'scientific'), 500)
        bad = copy.deepcopy(s); key = next(iter(bad['statistics'])); bad['statistics'][key]['mean'] += .1
        with self.assertRaises(AssertionError): audit.check_summary(bad, cases, controls, 'scientific')

    def test_technical_results_never_qualify(self):
        s = inference.analyze([self.cases], [self.controls], 'fixture')
        self.assertEqual(s['status'], 'TECHNICAL_ONLY'); self.assertIsNone(s['transfer_protection'])
        self.assertTrue(all(v is None for v in s['primary_gates'].values()))

    def test_interaction_alone_is_insufficient(self):
        s = inference.analyze([self.cases], [self.controls], 'scientific')['statistics']
        for k in s: s[k]['interval'] = [0., 0.]
        s['fresh_effect/both/independent_rewrite/interaction/scattered']['interval'] = [.2, .3]
        s['fresh/both/independent_rewrite/pulse_late/scattered']['interval'] = [.9, 1.]
        gates, _ = inference.decisions(s, 'scientific', True)
        self.assertTrue(gates['delay_interaction_exceeds_five'])
        self.assertFalse(gates['early_transferred_loss_exceeds_five']); self.assertFalse(all(gates.values()))

    def test_strict_five_point_bound(self):
        s = inference.analyze([self.cases], [self.controls], 'scientific')['statistics']
        s['fresh_effect/both/independent_rewrite/late/scattered']['interval'] = [-.05, 0.]
        gates, _ = inference.decisions(s, 'scientific', True)
        self.assertFalse(gates['late_loss_bounded_within_five'])

    def test_control_failure_suppresses_classifications(self):
        failed = dict(self.controls, pass_value=False); failed['pass'] = False
        s = inference.analyze([self.cases], [failed], 'scientific')
        self.assertEqual(s['status'], 'NUMERICAL_CONTROL_FAILURE')
        self.assertIsNone(s['transfer_protection'])


if __name__ == '__main__': unittest.main()
