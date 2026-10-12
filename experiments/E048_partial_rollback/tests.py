"""Twelve synthetic/excluded-fixture checks; no scientific receiving."""
from dataclasses import asdict
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import cap_cpus, rng
from E048_partial_rollback import model, run, audit
import numpy as np


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cap_cpus(8)
        cls.source, cls.chronology, cls.reference, _, cls.cfg, cls.cycle = run.source_config('fixture')

    def example(self):
        old = np.full((2, 2, 16, 16), .8)
        new = np.full_like(old, .7)
        new[:, 0, 1, :7] = .1
        dead = np.zeros((2, 16, 16), bool)
        index = np.array([[0, 0, 1], [3, 1, 7]], np.int64)
        return model.base.encode(old), model.base.encode(new), dead, index

    def test_01_cohort_first_last_and_missing(self):
        correct = np.ones((32, 4, 2, 2), bool)
        correct[0, 0, 0, 0] = False; correct[12, 0, 0] = False
        correct[30, 1, 0, 1] = False; correct[31, 2, 1] = False
        first, index = model.first_failures(correct)
        np.testing.assert_array_equal(index, [[0, 0, 1], [1, 0, 31]])
        self.assertEqual(first[2, 1], 32); self.assertEqual((first == 0).sum(), 5)

    def test_02_strict_cue_scoring(self):
        index = np.array([[0, 0, 1], [1, 0, 1]])
        target = model.base.RULES[index[:, 0]][:, None]*model.base.CUES[None]
        p = np.repeat(np.stack((target, -target), axis=-1)[None], 3, axis=0)
        p[1] *= .25; p[2] *= -.8
        s = model.score(p, index, self.cfg)
        self.assertTrue(s['correct'][0].all()); self.assertFalse(s['correct'][1:].any())
        np.testing.assert_array_equal(s['margin'][1], np.full((2, 2), .25))

    def test_03_cutoffs_sign_and_physical_wrap(self):
        old = np.zeros((1, 2, 16, 16)); new = old.copy()
        old.flat[:6] = [.8, .5, -.8, .8, 0, .7]
        new.flat[:6] = [.5, 0, -.51, -.9, .3, .7]
        dead = np.zeros((1, 16, 16), bool); dead[0, 15, 15] = True
        old[0, 0, 15, 15] = .9
        args = model.base.encode(old), model.base.encode(new), dead, np.array([[0, 0, 1]])
        result = model.construct(*args, 900041)
        np.testing.assert_array_equal(result['target'].ravel()[:6], [True, False, False, False, False, False])
        self.assertEqual(int(result['target'].sum()), 1)
        self.assertFalse(result['available'][0, 0, 15, 15])
        self.assertFalse(result['available'][0, 0, 15, 14])
        self.assertEqual(model.base.decode(result['packets'])[1, 0, 0, 0, 4], .3)
        np.testing.assert_array_equal(model.base.decode(result['packets'])[1, 0].ravel()[:6], [.65, 0, -.51, -.9, .3, .7])
        audit.equal_dict(result, audit.reconstruct(*args, 900041))

    def test_04_signed_half_interpolation_and_rounding(self):
        args = self.example(); one = model.construct(*args, 900041)
        other = model.construct(*(x[::-1].copy() for x in args), 900041)
        np.testing.assert_array_equal(one['packets'], other['packets'][:, ::-1])
        audit.equal_dict(one, audit.reconstruct(*args, 900041))
        old, new = model.base.decode(args[0]), model.base.decode(args[1])
        old[0].flat[:3] = [-.8, np.nextafter(.5, 1), .8]
        new[0].flat[:3] = [.4, .5, -.2]
        modified = model.construct(model.base.encode(old), model.base.encode(new), *args[2:], 900041)
        actual = model.base.decode(modified['packets'])
        np.testing.assert_array_equal(actual[1, 0].ravel()[:3], new[0].ravel()[:3]+.5*(old[0].ravel()[:3]-new[0].ravel()[:3]))
        self.assertTrue(modified['target'][0].flat[1]); self.assertFalse(modified['half_changed'][0].flat[1])
        self.assertTrue(modified['full_changed'][0].flat[1])

    def test_05_no_edits_and_exact_endpoints(self):
        old, new, dead, index = self.example()
        zero = model.construct(old, old, dead, index, 900041)
        self.assertFalse(zero['target'].any()); self.assertFalse(zero['half_changed'].any())
        np.testing.assert_array_equal(zero['packets'], np.stack([old]*3))
        new = model.base.encode(np.zeros((2, 2, 16, 16)))
        full = model.construct(old, new, dead, index, 900041)
        np.testing.assert_array_equal(full['full_changed'], full['target'])
        self.assertEqual(full['packets'][2].tobytes(), old.tobytes())
        self.assertEqual(full['packets'][0].tobytes(), new.tobytes())
        np.testing.assert_array_equal(model.base.decode(full['packets'][1]), .5*model.base.decode(old))

    def test_06_full_noise_stream_before_selection(self):
        index = np.array([[0, 0, 1], [1, 1, 1], [2, 0, 5], [3, 1, 5]])
        masks, actual = model.matched_inputs(index, 900041, self.cfg, self.cycle)
        for g in (2, 6):
            stream = rng('E022', 900041, 'develop', g)
            full = np.stack([stream.standard_normal((2, self.cfg.recipients, 16, 16)) for _ in range(self.cycle.read_steps+1)])
            for c, (f, r, onset) in enumerate(index):
                if onset+1 == g:
                    np.testing.assert_array_equal(actual[:, c], full[:, f//2, r])
                    np.testing.assert_array_equal(masks[c], audit.masks_for(900041, g, self.cfg.recipients, True)[f, r, 1])

    def test_07_acquired_generation_one_and_single_conversion(self):
        index = np.array([[0, 0, 1], [1, 1, 1]])
        incoming, outgoing, dead, _, _ = run.gather(self.source, 900041, index)
        source = run.load(self.source/'source_900041.npz')['acquired'][1]
        np.testing.assert_array_equal(incoming, source[[0, 1]])
        self.assertEqual((self.cycle.read_steps, self.cycle.settling_steps), (24, 12))
        actual = model.construct(incoming, outgoing, dead, index, 900041)
        audit.equal_dict(actual, audit.reconstruct(incoming, outgoing, dead, index, 900041))

    def test_08_mixed_generation_exact_baseline_and_replay(self):
        index = np.array([[0, 0, 1], [1, 1, 2], [2, 0, 3], [3, 1, 5]])
        incoming, outgoing, dead, next_dead, expected = run.gather(self.source, 900041, index)
        selection = model.construct(incoming, outgoing, dead, index, 900041)
        result = model.read(selection['packets'], index, 900041, self.cfg, self.cycle)
        np.testing.assert_array_equal(result['mean_ports'][0], expected)
        np.testing.assert_array_equal(result['masks'], next_dead)
        replay = audit.replay(selection['packets'], index, 900041, asdict(self.cfg), asdict(self.cycle))
        audit.equal_dict(result, replay)

    def test_09_corruption_rejected(self):
        args = self.example(); actual = model.construct(*args, 900041)
        expected = audit.reconstruct(*args, 900041)
        actual['packets'][1, 0, 0] ^= 1
        with self.assertRaises(AssertionError): audit.equal_dict(actual, expected)
        index = np.array([[0, 0, 1]])
        packet = np.zeros((3, 1, 4096), np.uint8)
        raw = model.read(packet, index, 900041, self.cfg, self.cycle)
        replay = audit.replay(packet, index, 900041, asdict(self.cfg), asdict(self.cycle))
        raw['end'][0, 0, 0, 0, 0] += .01
        with self.assertRaises(AssertionError): audit.equal_dict(raw, replay)

    def test_10_next_injury_erases_edit_and_recomputes_denominator(self):
        index = np.array([[0, 0, 1]])
        masks, _ = model.matched_inputs(index, 900041, self.cfg, self.cycle)
        unavailable = np.flatnonzero(~audit.edges(masks)[0])
        w = np.full((3, 1, 2, 16, 16), .7)
        w[1, 0].flat[unavailable[0]] = -.9
        result = model.read(model.base.encode(w), index, 900041, self.cfg, self.cycle)
        # Physical multiplication retains signed zero bits; compare erased values.
        np.testing.assert_array_equal(model.base.decode(result['effective_packets'][0]), model.base.decode(result['effective_packets'][1]))
        np.testing.assert_array_equal(result['end'][0], result['end'][1])
        self.assertFalse(np.any(model.base.decode(result['effective_packets'])[:, 0, ~audit.edges(masks)[0]]))
        audit.equal_dict(result, audit.replay(model.base.encode(w), index, 900041, asdict(self.cfg), asdict(self.cycle)))

    def test_11_empty_cases_and_pooled_ratios(self):
        first, index = model.first_failures(np.ones((32, 4, 2, 2), bool))
        self.assertEqual(index.shape, (0, 3))
        packets = np.empty((3, 0, 4096), np.uint8)
        actual = model.read(packets, index, 900041, self.cfg, self.cycle)
        audit.equal_dict(actual, audit.replay(packets, index, 900041, asdict(self.cfg), asdict(self.cycle)))
        selection = model.construct(packets[0], packets[0], np.empty((0, 16, 16), bool), index, 900041)
        self.assertEqual(selection['counts'].shape, (0, 9))
        st = run.statistics([1, 0, 0], [1, 9, 0]); self.assertEqual(st['mean'], .1)
        self.assertLess(st['bootstrap_valid'], 10000)
        empty = run.statistics([0, 0], [0, 0]); self.assertIsNone(empty['mean']); self.assertEqual(empty['bootstrap_valid'], 0)

    def test_12_loss_accounting_and_three_strict_requirements(self):
        success = np.array([[1, 1, 0, 0], [1, 0, 1, 0], [0, 0, 1, 1]], bool)
        np.testing.assert_array_equal(run.loss_counts(np.repeat(success[..., None], 2, axis=-1)), [1, 2])
        def result(a, b, c, technical=False):
            return run.decision({k:{'ci95':v} for k, v in zip(('original', 'full_rollback', 'loss_reduction'), (a, b, c))}, technical)
        self.assertTrue(result([.051, .2], [.001, .1], [.001, .1]))
        for a, b, c in (([.05, .2], [.01, .1], [.01, .1]), ([.06, .2], [0, .1], [.01, .1]),
            ([.06, .2], [.01, .1], [0, .1]), ([-.2, -.05], [-.1, -.01], [-.1, -.01]),
            ([None, None], [None, None], [None, None])):
            self.assertFalse(result(a, b, c))
        self.assertIsNone(result([.1, .2], [.1, .2], [.1, .2], True))


if __name__ == '__main__': unittest.main(verbosity=2)
