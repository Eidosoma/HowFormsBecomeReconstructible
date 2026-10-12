"""Excluded checks for renewal causality, exact reproduction and independent replay."""
from dataclasses import asdict
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E034_settled_rebuilding import model, run, audit
from E031_renewal_durability.audit import load_compact, replay_assay
import numpy as np


class RebuildingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run.cap_cpus(8)
        cls.source, _, cls.cfg, cls.cycle = run.source_config('fixture')
        cls.incoming = run.load(cls.source/'boundary_900031_g8.npz')['outgoing'][0]
        cls.reference = load_compact(cls.source/'boundary_900031_g9.npz', 'boundary')
        cls.raw = model.boundary(cls.incoming, 900031, cls.cfg, cls.cycle, 2)
        cls.path = HERE/'analysis/boundary_fixture.npz'
        model.evidence.save(cls.path, cls.raw, 'boundary')

    def test_fixed_timing_and_crossed_panels(self):
        full = model.Cycle(read_steps=2048, settling_steps=256, write_steps=128, generations=16)
        clocks = model.schedules(full)
        self.assertEqual([(c.settling_steps, c.read_steps) for c in clocks], [(256, 2048), (1024, 2048)])
        self.assertEqual([asdict(c) for c in clocks], audit.clocks(asdict(full), 4))
        self.assertEqual(len(model.PANELS), 8)
        with self.assertRaises(AssertionError): model.schedules(self.cycle, 4)

    def test_exact_original_boundary_and_source_immutability(self):
        model.check_original(self.raw, self.reference)
        np.testing.assert_array_equal(self.incoming, run.load(self.source/'boundary_900031_g8.npz')['outgoing'][0])
        np.testing.assert_array_equal(self.raw['incoming'], self.incoming)
        self.assertFalse(self.raw['erased_packets'].any())

    def test_unmodified_selective_writer_and_paired_inputs(self):
        raw = self.raw
        for key in ('read_packets', 'body_masks', 'retained_packets', 'read_denominators', 'retained_edges', 'eligible_edges'):
            np.testing.assert_array_equal(raw[key][0], raw[key][1])
        old, outgoing, fresh = [model.base.decode(raw[k]) for k in ('retained_packets', 'outgoing', 'computed_packets')]
        np.testing.assert_array_equal(outgoing[raw['retained_edges']], old[raw['retained_edges']])
        np.testing.assert_array_equal(outgoing[raw['eligible_edges']], fresh[raw['eligible_edges']])
        self.assertFalse(outgoing[~(raw['retained_edges'] | raw['eligible_edges'])].any())

    def test_independent_boundary_replays_every_commitment(self):
        saved = load_compact(self.path, 'boundary')
        outgoing, ports = audit.replay_boundary(saved, self.incoming, 900031, asdict(self.cfg), asdict(self.cycle), 2, self.reference)
        np.testing.assert_array_equal(outgoing, self.raw['outgoing'])
        np.testing.assert_array_equal(ports, self.raw['developed_late_ports'].mean(axis=0))

    def test_omitted_array_corruption_is_rejected(self):
        saved = load_compact(self.path, 'boundary')
        saved.descriptors['developed_end']['sha256'] = '0'*64
        with self.assertRaisesRegex(AssertionError, 'array commitment'):
            audit.replay_boundary(saved, self.incoming, 900031, asdict(self.cfg), asdict(self.cycle), 2, self.reference)

    def test_terminal_pairing_and_independent_replay(self):
        first = None
        for i, clock in enumerate(model.schedules(self.cycle, 2)):
            raw = model.assay(self.raw['outgoing'], 900031, self.cfg, clock)
            if first is None: first = raw
            for key in ('packets', 'birth', 'masks', 'permutations', 'receiver_denominators'):
                np.testing.assert_array_equal(raw[key], first[key])
            path = HERE/'analysis'/f'assay_fixture_t{i}.npz'
            model.evidence.save(path, raw, 'assay')
            independently = replay_assay(load_compact(path, 'assay'), self.raw['outgoing'], 900031, 9, asdict(self.cfg), asdict(clock))
            for x, y in zip(model.score(raw['late_ports'].mean(axis=0), self.cfg), independently):
                np.testing.assert_array_equal(x, y)

    def test_focal_axes_keep_terminal_setting_fixed(self):
        x = np.zeros((3, 8, 3, 7)); x[:, 7, 1, 0] = [.8, .7, .6]; x[:, 6, 1, 0] = [.2, .4, .5]
        expected = x[:, 7, 1, 0]-x[:, 6, 1, 0]
        np.testing.assert_array_equal(run.primary_values(x), expected)
        x[:, :6] = .95; x[:, :, (0, 2)] = .85; x[:, :, :, 1:] = .75
        np.testing.assert_array_equal(run.primary_values(x), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
