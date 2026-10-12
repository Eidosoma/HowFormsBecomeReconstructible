"""Excluded checks for capture content, matched strength and exact replay."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E035_cue_selective_capture import model, run, audit
from E031_renewal_durability.audit import load_compact, replay_assay
import numpy as np


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run.cap_cpus(8)
        cls.source, cls.parent, _, cls.cfg, cls.cycle, cls.factor = run.source_config('fixture')
        cls.incoming = run.load(cls.parent/'boundary_900031_g8.npz')['outgoing'][0]
        cls.reference = load_compact(cls.parent/'boundary_900031_g9.npz', 'boundary')
        cls.raw = model.history.boundary(cls.incoming, 900031, cls.cfg, cls.cycle, cls.factor)
        cls.saved_path = cls.source/'boundary_900031.npz'
        cls.saved = run.load(cls.saved_path)
        cls.available = cls.raw['retained_edges'][1] | cls.raw['eligible_edges'][1]
        cls.data = model.construct(cls.raw['developed_end'][1], cls.incoming, cls.available, cls.cfg)

    def test_common_and_opposing_cue_limits(self):
        a = np.linspace(-1, 1, 4*2*16*16).reshape(4, 2, 16, 16)
        body = np.stack((a, a), axis=2)
        mean, cue, standard, contrast, matched = model.captures(body)
        self.assertFalse(cue.any()); self.assertFalse(contrast.any())
        np.testing.assert_array_equal(matched, standard)
        body[:, :, 1] = -a
        mean, cue, standard, contrast, matched = model.captures(body)
        self.assertFalse(mean.any())
        np.testing.assert_array_equal(contrast, standard)
        np.testing.assert_array_equal(matched, standard)

    def test_decomposition_cue_swap_and_exact_zero_ties(self):
        body = self.data['body']
        mean, cue, standard, contrast, matched = model.captures(body)
        common = np.stack((mean*np.roll(mean, -1, -1), mean*np.roll(mean, -1, -2)), axis=-3)
        np.testing.assert_allclose(standard, common+contrast, rtol=0, atol=5e-16)
        flipped = model.captures(body[:, :, ::-1])
        np.testing.assert_array_equal(mean, flipped[0])
        np.testing.assert_array_equal(cue, -flipped[1])
        for a, b in zip((standard, contrast, matched), flipped[2:]):
            np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(abs(matched), abs(standard))
        np.testing.assert_array_equal(matched[contrast == 0], standard[contrast == 0])

    def test_availability_strong_copy_and_source_immutability(self):
        old = model.base.decode(self.incoming)
        weights = model.base.decode(self.data['records'])
        held = self.available & (abs(old) > .5)
        np.testing.assert_array_equal(held, self.data['retained'])
        for i, name in enumerate(('standard', 'contrast', 'matched')):
            np.testing.assert_array_equal(weights[2*i][held], old[held])
            for n in (2*i, 2*i+1):
                self.assertFalse(weights[n][~self.available].any())
            np.testing.assert_array_equal(weights[2*i+1][self.available], self.data[name][self.available])
            free = self.available & ~held
            np.testing.assert_array_equal(weights[2*i][free], self.data[name][free])
        for a, b in ((0, 4), (1, 5)):
            np.testing.assert_array_equal(abs(weights[a]), abs(weights[b]))
            np.testing.assert_array_equal(weights[a] != 0, weights[b] != 0)
        np.testing.assert_array_equal(self.incoming, run.load(self.parent/'boundary_900031_g8.npz')['outgoing'][0])
        np.testing.assert_array_equal(self.data['body'], self.raw['developed_end'][1])

    def test_exact_source_commitments_and_current_packet(self):
        model.verify_source(self.raw, self.saved)
        np.testing.assert_array_equal(self.data['records'][0], self.raw['outgoing'][1])
        np.testing.assert_array_equal(model.base.encode(self.data['standard']), self.raw['computed_packets'][1])
        full = model.Cycle(read_steps=2048, settling_steps=256, write_steps=128, generations=16)
        clock = model.terminal_cycle(full, 4)
        self.assertEqual((clock.settling_steps, clock.read_steps), (1024, 2048))
        self.assertEqual(model.PANELS, audit.PANELS)
        self.assertEqual(len(model.PANELS), 12)

    def test_independent_source_and_scalar_capture(self):
        source = load_compact(self.saved_path, 'boundary')
        outgoing, mean, body = audit.replay_source(source, self.incoming, 900031, asdict(self.cfg), asdict(self.cycle), self.factor, self.reference)
        np.testing.assert_array_equal(outgoing, self.raw['outgoing'])
        np.testing.assert_array_equal(mean, self.raw['developed_late_ports'].mean(axis=0))
        independently = audit.construction(body[1], self.incoming, self.available, asdict(self.cfg))
        self.assertEqual(set(independently), set(self.data))
        for key in independently:
            np.testing.assert_array_equal(independently[key], self.data[key])

    def test_unstored_source_array_corruption_is_rejected(self):
        saved = dict(self.saved)
        meta = json.loads(saved['__index__'].tobytes())
        meta['arrays']['developed_end']['sha256'] = '0'*64
        saved['__index__'] = np.frombuffer(json.dumps(meta).encode(), np.uint8)
        with self.assertRaisesRegex(AssertionError, 'source commitment'):
            model.verify_source(self.raw, saved)
        source = load_compact(self.saved_path, 'boundary')
        source.descriptors['developed_end']['sha256'] = '0'*64
        with self.assertRaisesRegex(AssertionError, 'array commitment'):
            audit.replay_source(source, self.incoming, 900031, asdict(self.cfg), asdict(self.cycle), self.factor, self.reference)

    def test_terminal_baseline_magnitude_controls_and_replay(self):
        clock = model.terminal_cycle(self.cycle, self.factor)
        records = self.data['records']
        raw = model.assay(records, 900031, self.cfg, clock)
        model.check_baseline(raw, run.load(self.source/'assay_900031_t1.npz'))
        path = HERE/'analysis/assay_fixture.npz'
        self.assertFalse(path.exists())
        model.evidence.save(path, raw, 'assay')
        saved = load_compact(path, 'assay')
        independently = replay_assay(saved, records, 900031, 9, asdict(self.cfg), asdict(clock))
        audit.check_matched_controls(saved, records)
        for x, y in zip(model.score(raw['late_ports'].mean(axis=0), self.cfg), independently):
            np.testing.assert_array_equal(x, y)

    def test_primary_axes_keep_reader_damage_and_control_fixed(self):
        x = np.zeros((3, 12, 3, 7))
        x[:, 9, 1, 0] = [.8, .7, .6]; x[:, 6, 1, 0] = [.2, .4, .5]
        expected = x[:, 9, 1, 0]-x[:, 6, 1, 0]
        np.testing.assert_array_equal(run.primary_values(x), expected)
        x[:, [i for i in range(12) if i not in (6, 9)]] = .95
        x[:, :, (0, 2)] = .85; x[:, :, :, 1:] = .75
        np.testing.assert_array_equal(run.primary_values(x), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
