"""Local compensation, unchanged interfaces and independent replay fixtures."""
from dataclasses import asdict, replace
import inspect
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E022_reader_compensation import model, run as study, audit
from E021_damaged_renewal import model as predecessor
import numpy as np


class ReaderCompensationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus()
        cls.cfg = replace(model.CFG, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cls.cycle = model.Cycle(read_steps=24, settling_steps=6, write_steps=8)
        source = model.acquisition.teach(study.BENCHMARK, cls.cfg)
        record = np.repeat(source['acquired'][1, :, None], 2, axis=1)
        cls.incoming = np.repeat(record[None], 8, axis=0)

    def test_local_arithmetic_and_zero_strength(self):
        stream = study.rng('E022', 'fixture', 'local')
        masks = np.zeros((6, 4, 2, 16, 16), dtype=bool)
        masks[:, :, :, 0, 0] = True
        masks[3] = False
        weights = stream.uniform(-1, 1, (6, 4, 2, 2, 16, 16))*model.surviving_edges(masks)
        weights[4] = 0
        denominator = model.reading_denominators(weights, masks)
        for y, x in ((0, 0), (0, 15), (1, 0), (6, 8)):
            neighbors = ((y, (x+1)%16), (y, (x-1)%16), ((y+1)%16, x), ((y-1)%16, x))
            expected_degree = sum((~masks[1, ..., y, x] & ~masks[1, ..., a, b]).astype(float) for a, b in neighbors)
            np.testing.assert_array_equal(denominator[1, ..., y, x], expected_degree)
            for a in (2, 4, 5):
                expected = abs(weights[a, ..., 0, y, x])+abs(weights[a, ..., 0, y, (x-1)%16])+abs(weights[a, ..., 1, y, x])+abs(weights[a, ..., 1, (y-1)%16, x])
                np.testing.assert_array_equal(denominator[a, ..., y, x], expected)
        self.assertFalse(denominator[4].any())
        np.testing.assert_array_equal(denominator[[0, 3]], 4*np.ones((2, 4, 2, 16, 16)))
        v = stream.normal(0, .15, (6, 4, 2, 2, 16, 16))
        noise = np.zeros_like(v)
        for amplified in (False, True):
            actual = model.compensated_step(v, weights[:, :, :, None], denominator[:, :, :, None], noise, self.cfg, amplified)
            self.assertTrue(np.isfinite(actual).all())
            zero_expected = v[4]+self.cfg.dt*((v[4]-v[4]**3 if amplified else -v[4]**3)-2*v[4])
            np.testing.assert_array_equal(actual[4], zero_expected)
            old = model.base.step(v[[0, 3]], weights[[0, 3], :, :, None], 2., noise[[0, 3]], self.cfg) if amplified else model.unamplified(v[[0, 3]], weights[[0, 3], :, :, None], noise[[0, 3]], self.cfg)
            np.testing.assert_array_equal(actual[[0, 3]], old)
            scaled = weights/4
            d2 = model.reading_denominators(scaled, masks)
            normalized = model.compensated_step(v, scaled[:, :, :, None], d2[:, :, :, None], noise, self.cfg, amplified)
            np.testing.assert_array_equal(actual[[2, 4, 5]], normalized[[2, 4, 5]])

    def test_exact_predecessor_baseline_and_terminal_reader(self):
        raw = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        old_cycle = predecessor.Cycle(read_steps=24, settling_steps=6, write_steps=8)
        old = predecessor.develop(raw['read_packets'][[0, 3, 4, 5]], raw['body_masks'][[0, 3, 4, 5]], study.BENCHMARK, 1, self.cfg, old_cycle)
        true_rng, true_masks = study.rng, model.base.damage_masks
        def paired_rng(tag, *parts): return true_rng('E021' if tag == 'E022' else tag, *parts)
        def paired_masks(block, phase, cfg): return true_masks(block, phase.replace('E022', 'E021'), cfg)
        with patch.object(model, 'rng', side_effect=paired_rng):
            new = model.develop(raw['read_packets'], raw['body_masks'], study.BENCHMARK, 1, self.cfg, self.cycle)
        np.testing.assert_array_equal(new['developed_end'][[0, 3]], old['developed_end'][[0, 1]])
        np.testing.assert_array_equal(new['developed_late_ports'][:, [0, 3]], old['developed_late_ports'][:, [0, 1]])
        old_assay = predecessor.assay(raw['outgoing'], study.BENCHMARK, 1, self.cfg, old_cycle)
        with patch.object(model, 'rng', side_effect=paired_rng), patch.object(model.base, 'damage_masks', side_effect=paired_masks), patch.object(model, 'compensated_step', side_effect=AssertionError('Compensation entered terminal assay')):
            new_assay = model.assay(raw['outgoing'], study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in old_assay: np.testing.assert_array_equal(new_assay[key], old_assay[key])

    def test_unchanged_activity_only_capture(self):
        self.assertEqual(tuple(inspect.signature(model.capture_from_activity).parameters), ('body', 'cfg'))
        mask = model.base.damage_masks(study.BENCHMARK, 'E022_renewal_g1', self.cfg)[:, :, 1]
        masks = np.repeat(mask[None], 6, axis=0); masks[3] = False
        body = study.rng('E022', 'fixture', 'writer').normal(0, .2, (6, 4, 2, 2, 16, 16))
        body *= (~masks)[:, :, :, None]
        before = body.copy()
        written = model.write_from_activity(body, masks, study.BENCHMARK, 1, self.cfg, self.cycle)
        np.testing.assert_array_equal(written['computed_packets'], predecessor.capture_from_activity(before, self.cfg))
        with patch.object(model.base, 'decode', side_effect=AssertionError('Writer decoded a record')), patch.object(model, 'RULES', np.zeros(4)), patch.object(model, 'reading_denominators', side_effect=AssertionError('Writer accessed denominators')):
            changed = model.write_from_activity(body, masks, study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in written: np.testing.assert_array_equal(written[key], changed[key])
        np.testing.assert_array_equal(body, before)
        later = model.write_from_activity(body, masks, study.BENCHMARK+1, 1, self.cfg, replace(self.cycle, write_steps=3))
        np.testing.assert_array_equal(written['computed_packets'], later['computed_packets'])
        self.assertFalse(np.array_equal(written['write_end'], later['write_end']))

    def test_physical_damage_erasure_and_forbidden_information(self):
        before = self.incoming.copy()
        real_writer = model.write_from_activity
        with patch.object(model, 'develop', wraps=model.develop) as develop:
            def guarded_writer(*args):
                self.assertFalse(develop.call_args.args[0].any(), 'Incoming packet not erased')
                return real_writer(*args)
            with patch.object(model, 'write_from_activity', side_effect=guarded_writer):
                raw = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        self.assertFalse(raw['erased_packets'].any())
        self.assertFalse(raw['read_packets'][4].any())
        self.assertFalse(raw['read_denominators'][4].any())
        self.assertFalse(raw['outgoing'][7].any())
        np.testing.assert_array_equal(raw['outgoing'][4], before[4])
        np.testing.assert_array_equal(self.incoming, before)
        masks = raw['body_masks']
        np.testing.assert_array_equal(masks.sum(axis=(-2, -1)), np.broadcast_to(np.array([24, 24, 24, 0, 24, 24])[:, None, None], (6, 4, 2)))
        self.assertFalse((masks & model.PORTS.any(axis=0)).any())
        self.assertFalse((raw['developed_end']*masks[:, :, :, None]).any())
        self.assertFalse((raw['write_states']*masks[None, :, :, :, None]).any())
        surviving = model.surviving_edges(masks)
        self.assertFalse((model.base.decode(raw['read_packets'])*(~surviving)).any())
        self.assertFalse((model.base.decode(raw['computed_packets'])*(~surviving)).any())
        np.testing.assert_array_equal(raw['outgoing'][5], model.base.encode(model.base.decode(before[5])*surviving[0]))
        np.testing.assert_array_equal(raw['read_packets'][3], before[3])
        with patch.object(model, 'RULES', np.zeros(4)), patch.object(model.base, 'RULES', np.zeros(4)), patch.object(model, 'score', side_effect=AssertionError('Scorer entered renewal')):
            changed = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in raw: np.testing.assert_array_equal(raw[key], changed[key])
        alternative = self.incoming.copy()
        alternative[6] = model.base.encode(np.ones((4, 2, 2, 16, 16)))
        blocked = model.replace_record(alternative, study.BENCHMARK, 1, self.cfg, self.cycle)
        np.testing.assert_array_equal(raw['outgoing'][6], blocked['outgoing'][6])

    def test_independent_end_to_end(self):
        parent = HERE/'analysis'
        attempt = 1
        while (parent/f'fixture_attempt{attempt}').exists(): attempt += 1
        started = time.monotonic()
        output = study.new_run(parent/f'fixture_attempt{attempt}', study.input_paths(), dict(experiment='E022',
            blocks=[study.BENCHMARK], gain=2., panels=model.PANELS, conditions=model.CONDITIONS,
            config=asdict(self.cfg), cycle=asdict(self.cycle), workers=1, mode='technical_fixture'))
        study.save_block(output, study.BENCHMARK, self.cfg, self.cycle)
        result = study.analyze(output, [study.BENCHMARK], True, self.cfg, self.cycle)
        self.assertEqual(result['status'], 'TECHNICAL_ONLY')
        self.assertIsNone(result['primary']['lower_bound_above_010'])
        self.assertIsNone(result['full_compensation_qualified'])
        self.assertEqual(len(result['boundary_gates']), 6)
        study.finish(output, started, dict(experiment='E022', blocks_completed=1))
        receipt = audit.audit(output, workers=1)
        self.assertEqual(receipt['status'], 'PASS')
        self.assertEqual(receipt['individual_observations'], 3024)
        self.assertEqual(receipt['body_individual_observations'], 96)


if __name__ == '__main__': unittest.main(verbosity=2)
