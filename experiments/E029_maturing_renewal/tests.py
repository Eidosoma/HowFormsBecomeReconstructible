"""Fixed-threshold contracts, legacy trajectory equality and independent replay."""
from dataclasses import asdict, replace
import hashlib
import inspect
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E029_maturing_renewal import model, run as study, audit
from E027_selective_renewal import model as legacy
import numpy as np


class MaturingRenewalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus(8)
        cls.cfg = replace(model.CFG, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cls.cycle = model.Cycle(read_steps=24, settling_steps=6, write_steps=8, generations=3)
        source = model.acquisition.teach(study.BENCHMARK, cls.cfg)
        packet = np.repeat(source['acquired'][1, :, None], 2, axis=1)
        cls.incoming = np.repeat(packet[None], 10, axis=0)

    def test_threshold_boundaries_and_weak_maturation(self):
        old = np.zeros((4, 2, 2, 16, 16))
        above = np.nextafter(.5, 1.)
        old.flat[:9] = [.7, -.7, 1e-250, .5, -.5, above, -above, -0., -.8]
        available = np.ones_like(old, dtype=bool)
        available.flat[8] = False
        packet = model.base.encode(old)
        before = packet.copy()
        fresh = model.base.encode(np.full_like(old, .42))
        result, kept, eligible = model.selective_packet(packet, fresh, available)
        np.testing.assert_array_equal(model.base.decode(result).ravel()[:9], [.7, -.7, .42, .42, .42, above, -above, .42, 0.])
        np.testing.assert_array_equal(kept.ravel()[:9], [True, True, False, False, False, True, True, False, False])
        np.testing.assert_array_equal(kept | eligible, available)
        self.assertFalse((kept & eligible).any())
        np.testing.assert_array_equal(packet, before)
        # A tiny repair can be rewritten twice, then is preserved after crossing 0.5.
        for value in (.4, .8, .1):
            result, _, _ = model.selective_packet(result, model.base.encode(np.full_like(old, value)), available)
        self.assertEqual(model.base.decode(result).ravel()[2], .8)
        old_result, _, _ = model.selective_packet(packet, fresh, available, threshold=0.)
        reference, _, _ = legacy.selective_packet(packet, fresh, available)
        np.testing.assert_array_equal(old_result, reference)

    def test_serial_handoffs_and_unchanged_reference_trajectories(self):
        incoming = self.incoming.copy()
        old_incoming = incoming[:8].copy()
        cumulative = np.ones((4, 2, 2, 16, 16), dtype=bool)
        new_positions, old_positions = [6, 2, 3, 4, 5], [0, 2, 3, 4, 5]
        masks, births = [], []
        for generation in range(1, 4):
            before = incoming.copy()
            raw = model.replace_record(incoming, study.BENCHMARK, generation, self.cfg, self.cycle)
            old = legacy.replace_record(old_incoming, study.BENCHMARK, generation, self.cfg, self.cycle)
            np.testing.assert_array_equal(incoming, before)
            for name in ('read_packets', 'read_denominators', 'developed_end', 'computed_packets', 'write_end'):
                np.testing.assert_array_equal(raw[name][new_positions], old[name][old_positions])
            np.testing.assert_array_equal(raw['developed_late_ports'][:, new_positions], old['developed_late_ports'][:, old_positions])
            for t in range(self.cycle.write_steps):
                for new_a, old_a in zip(new_positions, old_positions):
                    digest = hashlib.sha256(np.asarray(old['write_states'][t, old_a], dtype='<f8', order='C').tobytes()).digest()
                    self.assertEqual(raw['write_state_hashes'][t, new_a].tobytes(), digest)
            np.testing.assert_array_equal(raw['outgoing'][[8, 2, 3, 4, 5, 6, 7]], old['outgoing'][[0, 2, 3, 4, 5, 6, 7]])
            np.testing.assert_array_equal(raw['outgoing'][4], self.incoming[4])
            cumulative &= model.renewal.surviving_edges(raw['renewal_mask'])
            np.testing.assert_array_equal(raw['outgoing'][5], model.base.encode(model.base.decode(self.incoming[5])*cumulative))
            replayed, _ = audit.replay_boundary(raw, before, study.BENCHMARK, generation, asdict(self.cfg), asdict(self.cycle))
            np.testing.assert_array_equal(replayed, raw['outgoing'])
            masks.append(raw['renewal_mask']); births.append(raw['birth'])
            incoming, old_incoming = raw['outgoing'].copy(), old['outgoing'].copy()
        for a in range(3):
            for b in range(a):
                self.assertFalse(np.array_equal(masks[a], masks[b]))
                self.assertFalse(np.array_equal(births[a], births[b]))
        with self.assertRaises(AssertionError):
            model.replace_record(incoming, study.BENCHMARK, 4, self.cfg, self.cycle)

    def test_primary_noninferiority_axes_and_function_identity(self):
        for name in ('assay', 'score', 'receiver_denominators'):
            self.assertIs(getattr(model, name), getattr(legacy, name))
        self.assertIs(model.acquisition.teach, legacy.acquisition.teach)
        self.assertEqual(model.CYCLE, legacy.CYCLE)
        self.assertEqual(model.CFG, legacy.CFG)
        self.assertEqual(study.BENCHMARK_CYCLE.read_steps, 512)
        rates = np.full((3, 42, 3, 7), .25)
        candidate, previous, full = [model.PANELS.index((3, c, 'local_strength')) for c in ('maturing', 'selective', 'strength_compensated')]
        rates[:, candidate, 1, 0] = [.875, .75, .625]
        rates[:, previous, 1, 0] = [.5, .625, .875]
        rates[:, full, 1, 0] = [.9, .7, .6]
        expected = np.array([.375, .125, -.25])
        np.testing.assert_array_equal(study.primary_values(rates), expected)
        np.testing.assert_array_equal(study.noninferiority_values(rates), rates[:, candidate, 1, 0]-rates[:, full, 1, 0])
        other = rates.copy()
        other[:, :32] = .9375
        other[:, :, (0, 2)] = .875
        other[:, :, :, 1:] = 0.
        other[:, model.PANELS.index((3, 'masked_copy', 'local_strength')), 1, 0] = 1.
        np.testing.assert_array_equal(study.primary_values(other), expected)
        rates[:, [candidate, previous]] = rates[:, [previous, candidate]]
        np.testing.assert_array_equal(study.primary_values(rates), -expected)

    def test_explicit_copy_access_and_activity_only_refresh(self):
        self.assertEqual(tuple(inspect.signature(model.renewal.capture_from_activity).parameters), ('body', 'cfg'))
        real_writer = model.write_from_activity
        with patch.object(model, 'develop', wraps=model.develop) as develop:
            def guard(*args):
                self.assertFalse(develop.call_args.args[0].any())
                return real_writer(*args)
            with patch.object(model, 'write_from_activity', side_effect=guard), patch.object(model, 'assay', side_effect=AssertionError('Terminal feedback entered renewal')):
                raw = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        self.assertFalse(raw['erased_packets'].any())
        self.assertFalse(raw['read_packets'][[1, 4]].any())
        self.assertTrue(raw['retained_packets'][1].any())
        self.assertFalse(raw['outgoing'][7].any())
        old = model.base.decode(raw['retained_packets'])
        new = model.base.decode(raw['outgoing'][[0, 1, 8, 9]])
        np.testing.assert_array_equal(new[raw['retained_edges']], old[raw['retained_edges']])
        self.assertFalse(new[3][raw['eligible_edges'][3]].any())
        self.assertTrue(raw['read_packets'][7].any())
        np.testing.assert_array_equal(raw['computed_packets'], model.renewal.capture_from_activity(raw['developed_end'], self.cfg))

    def test_denominators_and_terminal_pairing(self):
        raw = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        np.testing.assert_array_equal(raw['read_denominators'], audit.local_denominators(model.base.decode(raw['read_packets']), model.renewal.surviving_edges(raw['body_masks'])))
        self.assertFalse(raw['read_denominators'][[1, 4]].any())
        observed = model.assay(raw['outgoing'], study.BENCHMARK, 1, self.cfg, self.cycle)
        expected = audit.replay_assay(observed, raw['outgoing'], study.BENCHMARK, 1, asdict(self.cfg), asdict(self.cycle))
        for left, right in zip(model.score(observed['late_ports'], self.cfg), expected):
            np.testing.assert_array_equal(left, right)

    def test_zero_drive_and_refresh_blocked_control(self):
        old = np.full((4, 2, 2, 16, 16), .3)
        old.flat[:3] = [.8, -.9, .5]
        alive = np.ones_like(old, bool)
        result, kept, eligible = model.selective_packet(model.base.encode(old), model.base.encode(np.ones_like(old)), alive, refresh=False)
        expected = np.zeros_like(old); expected.flat[:2] = [.8, -.9]
        np.testing.assert_array_equal(model.base.decode(result), expected)
        self.assertTrue(eligible.ravel()[2])
        v = study.rng('E029', 'zero_fixture').normal(0, .1, (2, 16, 16))
        for amplified in (False, True):
            actual = model.renewal.compensated_step(v, np.zeros((2, 16, 16)), np.zeros((16, 16)), np.zeros_like(v), self.cfg, amplified)
            expected = v+self.cfg.dt*((v-v**3 if amplified else -v**3)-2*v)
            np.testing.assert_array_equal(actual, expected)

    def test_corrupted_intermediate_holding_digest_rejected(self):
        raw = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        raw['write_state_hashes'][2, 7, 0] ^= 1
        with self.assertRaisesRegex(AssertionError, 'holding digest'):
            audit.replay_boundary(raw, self.incoming, study.BENCHMARK, 1, asdict(self.cfg), asdict(self.cycle))

    def test_independent_end_to_end(self):
        output = HERE/'analysis/fixture_attempt1'
        started = time.monotonic()
        study.new_run(output, study.input_paths(), dict(experiment='E029', blocks=[study.BENCHMARK], gain=2.,
            panels=model.PANELS, conditions=model.CONDITIONS, receivers=model.RECEIVERS,
            config=asdict(self.cfg), cycle=asdict(self.cycle), workers=1, mode='technical_fixture'))
        study.save_block(output, study.BENCHMARK, self.cfg, self.cycle)
        result = study.analyze(output, [study.BENCHMARK], True, self.cfg, self.cycle)
        self.assertEqual(result['status'], 'TECHNICAL_ONLY')
        self.assertIsNone(result['primary']['lower_bound_above_010'])
        self.assertIsNone(result['noninferiority']['lower_bound_above_minus_005'])
        self.assertIsNone(result['full_maturing_renewal_qualified'])
        self.assertIsNone(result['qualification_requirements_pass'])
        self.assertEqual(len(result['qualification_gates']), 14)
        self.assertEqual(len(result['boundary_gates']), 12)
        h3 = result['packet_contrasts']['3']['local_strength']
        self.assertEqual(result['primary']['statistics'], h3['maturing_minus_selective']['both_cues']['scattered'])
        self.assertEqual(result['noninferiority']['statistics'], h3['maturing_minus_strength_compensated']['both_cues']['scattered'])
        study.finish(output, started, dict(experiment='E029', blocks_completed=1))
        receipt = audit.audit(output, workers=1)
        self.assertEqual(receipt['status'], 'PASS')
        self.assertEqual(receipt['individual_observations'], 14112)
        self.assertEqual(receipt['body_individual_observations'], 384)


if __name__ == '__main__':
    unittest.main(verbosity=2)
