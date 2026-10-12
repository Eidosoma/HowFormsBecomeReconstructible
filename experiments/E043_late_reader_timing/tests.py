"""Excluded timing, baseline, pairing, evidence, indexing and decision checks."""
from dataclasses import asdict, replace
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E043_late_reader_timing import model, run, audit
from E031_renewal_durability.audit import load_compact, replay_assay
import numpy as np


class ExpressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run.cap_cpus(8)
        cls.source, _, cls.cfg, cls.cycle = run.source_config('fixture')
        cls.record = run.load(cls.source/'boundary_900041_g32.npz')['outgoing'][3]

    def test_fixed_scientific_timing_and_single_source_conversion(self):
        base = model.Cycle(read_steps=2048, settling_steps=1024, write_steps=128, generations=32)
        clocks = model.schedules(base)
        self.assertEqual([(c.settling_steps, c.read_steps) for c in clocks], [(1024, 2048), (1024, 4096), (3072, 4096)])
        self.assertEqual(clocks[0].read_steps-clocks[0].settling_steps, clocks[2].read_steps-clocks[2].settling_steps)
        self.assertEqual([asdict(c) for c in clocks], audit.schedules(asdict(base), 3))
        self.assertEqual((self.cycle.read_steps, self.cycle.settling_steps), (24, 12))
        self.assertEqual(model.HORIZONS, (24, 32))
        self.assertEqual(len(model.PANELS), 12)
        with self.assertRaises(AssertionError): model.schedules(self.cycle, 4)
        with self.assertRaises(AssertionError): model.schedules(replace(self.cycle, settling_steps=3))

    def test_original_matches_saved_mean_ports_and_all_controls(self):
        original = run.load(self.source/'assay_900041_h32.npz')
        raw = model.assay(self.record, 900041, 32, self.cfg, self.cycle)
        np.testing.assert_array_equal(raw['late_ports'].mean(axis=0), original['mean_ports'][[3, 14]])
        for k in ('masks', 'permutations'): np.testing.assert_array_equal(raw[k], original[k])

    def test_random_streams_packets_pairing_and_compact_replay(self):
        before = self.record.copy(); reference = None
        for i, cycle in enumerate(model.schedules(self.cycle)):
            raw = model.assay(self.record, 900041, 32, self.cfg, cycle)
            if reference is None: reference = raw
            for k in ('birth', 'masks', 'permutations', 'packets', 'receiver_denominators'):
                np.testing.assert_array_equal(raw[k], reference[k])
            path = HERE/'analysis'/f'compact_fixture_t{i}.npz'
            model.evidence.save(path, raw, 'assay')
            saved = load_compact(path, 'assay')
            independently = replay_assay(saved, self.record[None], 900041, 32, asdict(self.cfg), asdict(cycle))
            for a, b in zip(model.score(raw['late_ports'].mean(axis=0), self.cfg), independently): np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(self.record, before)

    def test_paired_trajectory_prefix_before_intervention(self):
        trace = []
        for cycle in model.schedules(self.cycle):
            cfg = replace(self.cfg, observe_steps=cycle.read_steps)
            trace.append(model.assay(self.record, 900041, 32, cfg, cycle)['late_ports'])
        np.testing.assert_array_equal(trace[0], trace[1][:self.cycle.read_steps])
        np.testing.assert_array_equal(trace[1][:self.cycle.settling_steps], trace[2][:self.cycle.settling_steps])

    def test_corrupted_omitted_array_commitment_rejected(self):
        raw = model.assay(self.record, 900041, 32, self.cfg, self.cycle)
        path = HERE/'analysis/corruption_fixture.npz'; model.evidence.save(path, raw, 'assay')
        compact = load_compact(path, 'assay'); compact.descriptors['end']['sha256'] = '0'*64
        with self.assertRaisesRegex(AssertionError, 'array commitment'):
            replay_assay(compact, self.record[None], 900041, 32, asdict(self.cfg), asdict(self.cycle))

    def test_focal_contrast_axes(self):
        values = np.zeros((3, 12, 3, 7))
        values[:, 11, 1, 0] = [.8, .7, .6]; values[:, 9, 1, 0] = [.2, .4, .5]
        expected = values[:, 11, 1, 0]-values[:, 9, 1, 0]
        np.testing.assert_array_equal(run.primary_values(values), expected)
        values[:, :9] = .91; values[:, 10] = .92; values[:, :, (0, 2)] = .9; values[:, :, :, 1:] = .9
        np.testing.assert_array_equal(run.primary_values(values), expected)

    def test_strict_primary_threshold_and_technical_null(self):
        for low, expected in ((.049, False), (.05, False), (.050001, True)):
            stat = dict(ci95=[low, .2])
            self.assertEqual(run.primary_decision(stat, False), expected)
            self.assertIsNone(run.primary_decision(stat, True))

    def test_paired_rescues_and_losses_keep_all_cases(self):
        low = np.array([[[0, 0, 1, 1]], [[1, 0, 1, 0]]], dtype=bool)
        high = np.array([[[0, 1, 0, 1]], [[0, 0, 0, 0]]], dtype=bool)
        result = run.transition_counts(low, high)
        self.assertEqual(result['total'], 8)
        self.assertEqual(result['counts'], dict(both_fail=3, rescued=1, lost=3, both_succeed=1))
        self.assertEqual(result['by_block']['lost'], [1, 2])
        self.assertEqual(result['counts']['rescued']-result['counts']['lost'], int(high.sum())-int(low.sum()))


if __name__ == '__main__': unittest.main(verbosity=2)
