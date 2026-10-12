"""Selective-copy contracts, unchanged references and independent disposable replay."""
from dataclasses import asdict, replace
import inspect
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E027_selective_renewal import model, run as study, audit
from E024_serial_compensation import model as predecessor
import numpy as np


class SelectiveRenewalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus()
        cls.cfg = replace(model.CFG, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cls.cycle = model.Cycle(read_steps=24, settling_steps=6, write_steps=8, generations=3)
        source = model.acquisition.teach(study.BENCHMARK, cls.cfg)
        packet = np.repeat(source['acquired'][1, :, None], 2, axis=1)
        cls.incoming = np.repeat(packet[None], 8, axis=0)

    def test_exact_zero_infill_and_tiny_value_preservation(self):
        old = np.zeros((2, 4, 2, 2, 16, 16))
        old.flat[:6] = [.7, -.3, 1e-250, -.8, -0., -1e-250]
        fresh = np.full_like(old, .42)
        available = np.ones_like(old, dtype=bool)
        available.flat[3] = False
        packet, computed = model.base.encode(old), model.base.encode(fresh)
        before = packet.copy()
        result, retained, eligible = model.selective_packet(packet, computed, available)
        values = model.base.decode(result)
        np.testing.assert_array_equal(values.ravel()[:6], [.7, -.3, 1e-250, 0., .42, -1e-250])
        np.testing.assert_array_equal(retained.ravel()[:6], [True, True, True, False, False, True])
        np.testing.assert_array_equal(eligible.ravel()[:6], [False, False, False, False, True, False])
        np.testing.assert_array_equal(packet, before)
        np.testing.assert_array_equal(retained | eligible, available)
        self.assertFalse((retained & eligible).any())
        self.assertFalse((values*~available).any())

    def test_serial_handoffs_and_unchanged_reference_chains(self):
        incoming = self.incoming.copy()
        cumulative = np.ones((4, 2, 2, 16, 16), dtype=bool)
        masks, births = [], []
        for generation in range(1, 4):
            before = incoming.copy()
            raw = model.replace_record(incoming, study.BENCHMARK, generation, self.cfg, self.cycle)
            old = predecessor.replace_record(incoming, study.BENCHMARK, generation, self.cfg, self.cycle)
            np.testing.assert_array_equal(incoming, before)
            np.testing.assert_array_equal(raw['incoming'], before)
            for name in ('read_packets', 'read_denominators', 'developed_end', 'computed_packets', 'write_end'):
                np.testing.assert_array_equal(raw[name][2:], old[name][2:])
            for name in ('developed_late_ports', 'write_states'):
                np.testing.assert_array_equal(raw[name][:, 2:], old[name][:, 2:])
            np.testing.assert_array_equal(raw['outgoing'][2:], old['outgoing'][2:])
            np.testing.assert_array_equal(raw['outgoing'][4], self.incoming[4])
            cumulative &= model.renewal.surviving_edges(raw['renewal_mask'])
            np.testing.assert_array_equal(raw['outgoing'][5], model.base.encode(model.base.decode(self.incoming[5])*cumulative))
            if generation == 1:
                self.assertFalse(raw['eligible_edges'].any())
                # Physical zeros may differ in sign bit; all numerical weights agree.
                np.testing.assert_array_equal(model.base.decode(raw['outgoing'][0]), model.base.decode(raw['outgoing'][5]))
            else:
                self.assertTrue(raw['eligible_edges'].any())
                self.assertFalse(np.array_equal(incoming[0], self.incoming[0]))
            replayed, _ = audit.replay_boundary(raw, before, study.BENCHMARK, generation, asdict(self.cfg), asdict(self.cycle))
            np.testing.assert_array_equal(replayed, raw['outgoing'])
            masks.append(raw['renewal_mask']); births.append(raw['birth'])
            incoming = raw['outgoing'].copy()
        for a in range(3):
            for b in range(a):
                self.assertFalse(np.array_equal(masks[a], masks[b]))
                self.assertFalse(np.array_equal(births[a], births[b]))
        with self.assertRaises(AssertionError):
            model.replace_record(incoming, study.BENCHMARK, 4, self.cfg, self.cycle)

    def test_primary_axes_direction_and_function_identity(self):
        for name in ('assay', 'score', 'receiver_denominators'):
            self.assertIs(getattr(model, name), getattr(predecessor, name))
        self.assertIs(model.acquisition.teach, predecessor.acquisition.teach)
        rates = np.full((3, 34, 3, 7), .25)
        # h3/local-strength panels: selective 26, full rebuilding 28.
        rates[:, 26, 1, 0] = [.875, .75, .625]
        rates[:, 28, 1, 0] = [.5, .625, .875]
        expected = np.array([.375, .125, -.25])
        np.testing.assert_array_equal(study.primary_values(rates), expected)
        other = rates.copy()
        other[:, :26] = .9375
        other[:, :, (0, 2)] = .875
        other[:, :, :, 1:] = 0.
        other[:, 31, 1, 0] = 1.  # Copy is a qualification comparator, not primary.
        np.testing.assert_array_equal(study.primary_values(other), expected)
        rates[:, [26, 28]] = rates[:, [28, 26]]
        np.testing.assert_array_equal(study.primary_values(rates), -expected)

    def test_explicit_copy_access_and_activity_only_infill(self):
        self.assertEqual(tuple(inspect.signature(model.renewal.capture_from_activity).parameters), ('body', 'cfg'))
        real_writer = model.renewal.write_from_activity
        with patch.object(model, 'develop', wraps=model.develop) as develop:
            def guard(*args):
                self.assertFalse(develop.call_args.args[0].any())
                return real_writer(*args)
            with patch.object(model.renewal, 'write_from_activity', side_effect=guard), patch.object(model, 'assay', side_effect=AssertionError('Terminal feedback entered renewal')):
                raw = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        self.assertFalse(raw['erased_packets'].any())
        self.assertFalse(raw['read_packets'][[1, 4]].any())
        self.assertTrue(raw['retained_packets'][1].any())
        self.assertFalse(raw['outgoing'][7].any())
        old = model.base.decode(raw['retained_packets'])
        new = model.base.decode(raw['outgoing'][:2])
        np.testing.assert_array_equal(new[raw['retained_edges']], old[raw['retained_edges']])
        np.testing.assert_array_equal(raw['computed_packets'], model.renewal.capture_from_activity(raw['developed_end'], self.cfg))

    def test_denominators_and_terminal_pairing(self):
        raw = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        np.testing.assert_array_equal(raw['read_denominators'], audit.local_denominators(model.base.decode(raw['read_packets']), model.renewal.surviving_edges(raw['body_masks'])))
        self.assertFalse(raw['read_denominators'][[1, 4]].any())
        observed = model.assay(raw['outgoing'], study.BENCHMARK, 1, self.cfg, self.cycle)
        c, m, v = audit.replay_assay(observed, raw['outgoing'], study.BENCHMARK, 1, asdict(self.cfg), asdict(self.cycle))
        actual = model.score(observed['late_ports'], self.cfg)
        for left, right in zip(actual, (c, m, v)):
            np.testing.assert_array_equal(left, right)

    def test_zero_drive_and_copy_only_policy(self):
        available = model.renewal.surviving_edges(model.base.damage_masks(study.BENCHMARK, 'E022_renewal_g2', self.cfg)[:, :, 1])
        old = model.base.decode(self.incoming[:2]).copy()
        old[..., 0, 1, 1] = 0.
        physical = model.base.encode(old*available)
        result, _, _ = model.selective_packet(physical, np.zeros_like(physical), np.broadcast_to(available, old.shape))
        np.testing.assert_array_equal(model.base.decode(result), old*available)
        v = study.rng('E027', 'zero_fixture').normal(0, .1, (2, 16, 16))
        for amplified in (False, True):
            actual = model.renewal.compensated_step(v, np.zeros((2, 16, 16)), np.zeros((16, 16)), np.zeros_like(v), self.cfg, amplified)
            expected = v+self.cfg.dt*((v-v**3 if amplified else -v**3)-2*v)
            np.testing.assert_array_equal(actual, expected)

    def test_independent_end_to_end(self):
        output = HERE/'analysis/fixture_attempt1'
        started = time.monotonic()
        study.new_run(output, study.input_paths(), dict(experiment='E027', blocks=[study.BENCHMARK], gain=2.,
            panels=model.PANELS, conditions=model.CONDITIONS, receivers=model.RECEIVERS,
            config=asdict(self.cfg), cycle=asdict(self.cycle), workers=1, mode='technical_fixture'))
        study.save_block(output, study.BENCHMARK, self.cfg, self.cycle)
        result = study.analyze(output, [study.BENCHMARK], True, self.cfg, self.cycle)
        self.assertEqual(result['status'], 'TECHNICAL_ONLY')
        self.assertIsNone(result['primary']['lower_bound_above_zero'])
        self.assertIsNone(result['full_selective_renewal_qualified'])
        self.assertIsNone(result['qualification_requirements_pass'])
        self.assertEqual(len(result['qualification_gates']), 13)
        self.assertEqual(len(result['boundary_gates']), 12)
        self.assertEqual(result['primary']['statistics'], result['packet_contrasts']['3']['local_strength']['selective_minus_strength_compensated']['both_cues']['scattered'])
        study.finish(output, started, dict(experiment='E027', blocks_completed=1))
        receipt = audit.audit(output, workers=1)
        self.assertEqual(receipt['status'], 'PASS')
        self.assertEqual(receipt['individual_observations'], 11424)
        self.assertEqual(receipt['body_individual_observations'], 288)


if __name__ == '__main__':
    unittest.main(verbosity=2)
