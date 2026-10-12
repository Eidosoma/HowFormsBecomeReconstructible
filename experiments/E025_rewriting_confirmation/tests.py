"""Receiving-reader contracts and independent replay on disposable inputs."""
from dataclasses import asdict, replace
import inspect
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E025_rewriting_confirmation import model, run as study, audit
from E022_reader_compensation import model as predecessor
from E024_serial_compensation import model as serial_predecessor, audit as serial_audit
import numpy as np


class RewritingConfirmationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus()
        cls.cfg = replace(model.CFG, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cls.cycle = model.Cycle(read_steps=24, settling_steps=6, write_steps=8, generations=3)
        source = model.acquisition.teach(study.BENCHMARK, cls.cfg)
        record = np.repeat(source['acquired'][1, :, None], 2, axis=1)
        cls.incoming = np.repeat(record[None], 8, axis=0)

    def test_confirmation_contract_and_endpoint_selection(self):
        for name in ('replace_record', 'assay', 'score', 'receiver_denominators'):
            self.assertIs(getattr(model, name), getattr(serial_predecessor, name))
        self.assertIs(model.acquisition.teach, serial_predecessor.acquisition.teach)
        self.assertIs(audit.inspect_block, serial_audit.inspect_block)
        self.assertEqual(model.CFG, serial_predecessor.CFG)
        self.assertEqual(model.CYCLE, serial_predecessor.CYCLE)
        self.assertEqual(model.PANELS, serial_predecessor.PANELS)
        # An independently specified table distinguishes all endpoint axes.
        # In the frozen layout, panels 28/31 are h3 normalized candidate/copy.
        rates = np.full((3, 34, 3, 7), .25)
        rates[:, 28, 1, 0] = [.875, .75, .625]
        rates[:, 31, 1, 0] = [.5, .625, .875]
        expected = np.array([.375, .125, -.25])
        np.testing.assert_array_equal(study.primary_values(rates), expected)
        changed = rates.copy()
        changed[:, :18] = .9375  # Initial and first-replacement panels.
        changed[:, 18:26] = .125  # Third-replacement fixed-four receiver.
        changed[:, :, (0, 2)] = .875  # Other terminal injuries.
        changed[:, :, :, 1:] = 0.  # Other record/communication arms.
        np.testing.assert_array_equal(study.primary_values(changed), expected)
        swapped = rates.copy()
        swapped[:, [28, 31]] = rates[:, [31, 28]]
        np.testing.assert_array_equal(study.primary_values(swapped), -expected)

    def test_serial_handoffs_fresh_masks_and_cumulative_erasure(self):
        first = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        old = predecessor.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg,
                                         replace(self.cycle, generations=1))
        for key in old: np.testing.assert_array_equal(first[key], old[key])
        incoming = self.incoming.copy()
        cumulative = np.ones((4, self.cfg.recipients, 2, 16, 16), bool)
        masks, births = [], []
        for g in range(1, 4):
            before = incoming.copy()
            raw = model.replace_record(incoming, study.BENCHMARK, g, self.cfg, self.cycle)
            np.testing.assert_array_equal(incoming, before)
            np.testing.assert_array_equal(raw['incoming'], before)
            np.testing.assert_array_equal(raw['outgoing'][4], self.incoming[4])
            cumulative &= predecessor.surviving_edges(raw['renewal_mask'])
            expected = model.base.encode(model.base.decode(self.incoming[5])*cumulative)
            np.testing.assert_array_equal(raw['outgoing'][5], expected)
            np.testing.assert_array_equal(raw['computed_packets'], predecessor.capture_from_activity(raw['developed_end'], self.cfg))
            self.assertFalse(raw['outgoing'][7].any())
            self.assertFalse(raw['read_packets'][4].any())
            self.assertFalse((raw['developed_end']*raw['body_masks'][:, :, :, None]).any())
            self.assertFalse((model.base.decode(raw['computed_packets'])*(~predecessor.surviving_edges(raw['body_masks']))).any())
            if g > 1:
                self.assertFalse(raw['read_packets'][5].any())
                fresh_only = model.base.encode(model.base.decode(self.incoming[5])*predecessor.surviving_edges(raw['renewal_mask']))
                self.assertFalse(np.array_equal(raw['outgoing'][5], fresh_only))
            masks.append(raw['renewal_mask']); births.append(raw['birth'])
            incoming = raw['outgoing'].copy()
        for a in range(3):
            for b in range(a):
                self.assertFalse(np.array_equal(masks[a], masks[b]))
                self.assertFalse(np.array_equal(births[a], births[b]))
        with self.assertRaises(AssertionError):
            model.replace_record(incoming, study.BENCHMARK, 4, self.cfg, self.cycle)

    def test_denominators_after_damage_and_controls(self):
        packets, _ = predecessor.assay_packets(self.incoming[:2], study.BENCHMARK, 1)
        masks = model.base.damage_masks(study.BENCHMARK, 'E022_h1', self.cfg)
        weights = np.concatenate([model.base.effective_weights(p, masks) for p in packets])
        denominator = model.receiver_denominators(weights)
        N = len(packets)
        np.testing.assert_array_equal(denominator[:N], 4*np.ones_like(denominator[:N]))
        for y, x in ((0, 0), (0, 15), (7, 1), (7, 2), (8, 2), (11, 10)):
            expected = abs(weights[..., 0, y, x])+abs(weights[..., 0, y, (x-1)%16])+abs(weights[..., 1, y, x])+abs(weights[..., 1, (y-1)%16, x])
            np.testing.assert_array_equal(denominator[N:, ..., y, x], expected)
        self.assertFalse(denominator[N:, ..., [3, 5], :, :].any())
        self.assertFalse(denominator[N:, ..., 6, :, :][..., model.PORTS[0]].any())
        np.testing.assert_array_equal(denominator, audit.receiver_denominators(weights))
        before = denominator.copy()
        changed = weights.copy(); changed[0, 0, 0, 0, 0, 0, 0, 0, 0] *= .5
        after = model.receiver_denominators(changed)
        locations = np.argwhere(after != before)
        self.assertEqual(len(locations), 2)
        self.assertEqual(set(map(tuple, locations[:, -2:])), {(0, 0), (0, 1)})

    def test_exact_fixed_reader_and_shared_packet_randomness(self):
        boundary = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        records = boundary['outgoing']; before = records.copy()
        old = predecessor.assay(records, study.BENCHMARK, 1, self.cfg, self.cycle)
        new = model.assay(records, study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in ('packets', 'permutations', 'masks', 'birth'):
            np.testing.assert_array_equal(new[key], old[key])
        for key in ('end', 'late_mean'): np.testing.assert_array_equal(new[key][:8], old[key])
        np.testing.assert_array_equal(new['late_ports'][:, :8], old['late_ports'])
        np.testing.assert_array_equal(records, before)
        # Both receiver variants consume one identical birth and noise stream.
        calls = []
        real = predecessor.compensated_step
        def capture(v, weights, denominator, noise, cfg, amplification):
            if not calls:
                np.testing.assert_array_equal(v[:8], v[8:])
                np.testing.assert_array_equal(weights[:8], weights[8:])
            self.assertEqual(noise.shape[0], 1)
            calls.append(amplification)
            return real(v, weights, denominator, noise, cfg, amplification)
        with patch.object(predecessor, 'compensated_step', side_effect=capture):
            again = model.assay(records, study.BENCHMARK, 1, self.cfg, self.cycle)
        self.assertEqual(calls, [False]*6+[True]*18)
        for key in new: np.testing.assert_array_equal(again[key], new[key])

    def test_unchanged_writer_erasure_and_no_assay_feedback(self):
        self.assertEqual(tuple(inspect.signature(predecessor.capture_from_activity).parameters), ('body', 'cfg'))
        real_writer = predecessor.write_from_activity
        with patch.object(predecessor, 'develop', wraps=predecessor.develop) as develop:
            def guarded_writer(*args):
                self.assertFalse(develop.call_args.args[0].any())
                return real_writer(*args)
            with patch.object(predecessor, 'write_from_activity', side_effect=guarded_writer), patch.object(model, 'assay', side_effect=AssertionError('Assay feedback entered renewal')):
                raw = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        self.assertFalse(raw['erased_packets'].any())
        self.assertFalse(raw['read_packets'][4].any())
        self.assertFalse(raw['outgoing'][7].any())
        np.testing.assert_array_equal(raw['outgoing'][4], self.incoming[4])
        rebuilt = predecessor.capture_from_activity(raw['developed_end'], self.cfg)
        np.testing.assert_array_equal(rebuilt, raw['computed_packets'])
        with patch.object(model, 'RULES', np.zeros(4)), patch.object(predecessor, 'RULES', np.zeros(4)), patch.object(model.base, 'RULES', np.zeros(4)), patch.object(model, 'score', side_effect=AssertionError('Scorer entered dynamics')):
            changed = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in raw: np.testing.assert_array_equal(raw[key], changed[key])
        expected = model.assay(raw['outgoing'], study.BENCHMARK, 1, self.cfg, self.cycle)
        with patch.object(model, 'RULES', np.zeros(4)), patch.object(predecessor, 'RULES', np.zeros(4)), patch.object(model.base, 'RULES', np.zeros(4)), patch.object(model, 'score', side_effect=AssertionError('Scorer entered receiver')):
            changed = model.assay(raw['outgoing'], study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in expected: np.testing.assert_array_equal(expected[key], changed[key])

    def test_normalized_scaling_zero_input_and_physical_zeros(self):
        record = self.incoming[:2]
        raw = model.assay(record, study.BENCHMARK, 1, self.cfg, self.cycle)
        scaled = model.base.encode(model.base.decode(record)/4)
        other = model.assay(scaled, study.BENCHMARK, 1, self.cfg, self.cycle)
        np.testing.assert_array_equal(raw['end'][2:], other['end'][2:])
        np.testing.assert_array_equal(raw['late_ports'][:, 2:], other['late_ports'][:, 2:])
        for arm in (3, 5):
            np.testing.assert_array_equal(raw['end'][:2, ..., arm, :, :], raw['end'][2:, ..., arm, :, :])
        self.assertFalse((raw['end']*raw['masks'][None, :, :, None, :, None]).any())
        for arm in (5, 6):
            np.testing.assert_array_equal(raw['end'][:, :, :, 0, :, arm][..., ~model.PORTS[0]], raw['end'][:, :, :, 1, :, arm][..., ~model.PORTS[0]])
        # Arithmetic includes the zero-denominator definition, in both stages.
        v = study.rng('E025', 'zero_fixture').normal(0, .1, (2, 16, 16))
        for amplified in (False, True):
            actual = predecessor.compensated_step(v, np.zeros((2, 16, 16)), np.zeros((16, 16)), np.zeros_like(v), self.cfg, amplified)
            expected = v+self.cfg.dt*((v-v**3 if amplified else -v**3)-2*v)
            np.testing.assert_array_equal(actual, expected)

    def test_independent_end_to_end(self):
        parent = HERE/'analysis'; attempt = 1
        while (parent/f'fixture_attempt{attempt}').exists(): attempt += 1
        started = time.monotonic()
        output = study.new_run(parent/f'fixture_attempt{attempt}', study.input_paths(), dict(experiment='E025',
            blocks=[study.BENCHMARK], gain=2., panels=model.PANELS, conditions=model.CONDITIONS, receivers=model.RECEIVERS,
            config=asdict(self.cfg), cycle=asdict(self.cycle), workers=1, mode='technical_fixture'))
        study.save_block(output, study.BENCHMARK, self.cfg, self.cycle)
        result = study.analyze(output, [study.BENCHMARK], True, self.cfg, self.cycle)
        self.assertEqual(result['status'], 'TECHNICAL_ONLY')
        self.assertIsNone(result['primary']['lower_bound_above_010'])
        self.assertIsNone(result['full_confirmation_qualified'])
        self.assertIsNone(result['serial_reliability_qualified'])
        self.assertEqual(len(result['boundary_gates']), 12)
        self.assertEqual(len(result['qualification_gates']), 11)
        self.assertIn('h3_candidate_intact_both_cue_lower_above_075', result['qualification_gates'])
        self.assertEqual(result['primary']['statistics'],
            result['packet_contrasts']['3']['local_strength']['strength_compensated_minus_masked_copy']['both_cues']['scattered'])
        self.assertEqual(len(result['panels']), 34)
        self.assertEqual(set(result['body_reading']), {'1', '2', '3'})
        self.assertEqual(set(result['groups']), {'0', '1', '3'})
        study.finish(output, started, dict(experiment='E025', blocks_completed=1))
        receipt = audit.audit(output, workers=1)
        self.assertEqual(receipt['status'], 'PASS')
        self.assertEqual(receipt['individual_observations'], 11424)
        self.assertEqual(receipt['body_individual_observations'], 288)


if __name__ == '__main__': unittest.main(verbosity=2)
