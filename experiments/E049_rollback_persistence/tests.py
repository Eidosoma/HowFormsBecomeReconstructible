"""Twelve synthetic/excluded-fixture checks; no scientific receiving."""
from dataclasses import asdict
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import cap_cpus, rng
from E049_rollback_persistence import model, run, audit
import numpy as np


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cap_cpus(8)
        cls.source, _, cls.reference, _, cls.cfg, cls.cycle = run.source_config('fixture')
        cls.index = np.array([[0, 0, 1], [1, 1, 2], [2, 0, 3], [3, 1, 5], [0, 1, 29]], np.int64)
        old, new, dead, _, _ = run.gather(cls.source, 900041, cls.index)
        cls.selection = model.construct(old, new, dead, cls.index, 900041)

    def rebuild(self, packets=None, offset=1):
        return model.rebuild(self.selection['packets'] if packets is None else packets,
            self.index, offset, 900041, self.cfg, self.cycle)

    def test_01_first_failure_and_followup_boundary(self):
        correct = np.ones((32, 4, 2, 2), bool)
        correct[0, 0, 0, 0] = False; correct[12, 0, 0] = False
        correct[28, 1, 0, 1] = False; correct[29, 2, 1] = False; correct[31, 3, 0] = False
        first, index = model.first_failures(correct)
        np.testing.assert_array_equal(index, [[0, 0, 1], [1, 0, 29]])
        self.assertEqual(first[2, 1], 30); self.assertEqual(first[3, 0], 32)
        self.assertEqual((first == 0).sum(), 4)
        np.testing.assert_array_equal(model.shifted(index, 3)[:, 2]+1, [4, 32])
        with self.assertRaises(AssertionError): model.shifted(np.array([[0, 0, 30]]), 1)

    def test_02_initial_intervention_and_first_body_reproduce_e048(self):
        prior = run.load(self.reference/'selection_900041.npz')
        index = prior['index']; old, new, dead, _, _ = run.gather(self.source, 900041, index)
        selection = model.construct(old, new, dead, index, 900041)
        for k in selection: run.equal(selection[k], prior[k], k)
        raw = model.rebuild(selection['packets'], index, 1, 900041, self.cfg, self.cycle)
        reader = run.load(self.reference/'read_900041.npz')
        audit.equal_dict({k:raw[k] for k in model.READ_KEYS}, reader)
        audit.equal_dict(model.score(raw['mean_ports'], index, self.cfg), run.load(self.reference/'cases_900041.npz'))
        self.assertEqual(self.cycle.settling_steps, 12)

    def test_03_capture_contrast_fallback_and_torus(self):
        body = np.full((3, 1, 2, 16, 16), .3)
        body[:, :, 1, 15, 15] = -.3; body[:, :, 1, 15, 0] = -.3
        fresh = model.capture(body, self.cfg.writer_beta)
        run.equal(fresh, audit.capture(body, self.cfg.writer_beta))
        decoded = model.base.decode(fresh); x = np.tanh(self.cfg.writer_beta*.3)
        self.assertEqual(decoded[0, 0, 0, 0, 0], x*x)  # identical cues: ordinary fallback
        self.assertEqual(decoded[0, 0, 0, 15, 15], x*x)  # contrast through wrap
        self.assertEqual(decoded[0, 0, 0, 15, 0], 0.)  # one endpoint has zero contrast

    def test_04_capture_precedes_holding(self):
        raw = self.rebuild()
        run.equal(raw['computed_packets'], model.capture(raw['end'], self.cfg.writer_beta))
        self.assertNotEqual(raw['end'].tobytes(), raw['write_end'].tobytes())
        self.assertNotEqual(raw['computed_packets'].tobytes(), model.capture(raw['write_end'], self.cfg.writer_beta).tobytes())

    def test_05_original_serial_chain_and_final_available_generation(self):
        packets = self.selection['packets'].copy()
        source_cases = run.load(self.source/'cases_900041.npz')
        for offset in model.OFFSETS:
            raw = self.rebuild(packets, offset)
            run.equal(raw['incoming'], packets)
            cases = model.score(raw['mean_ports'], self.index, self.cfg)
            for j, (f, r, g) in enumerate(self.index.tolist()):
                src = run.load(self.source/f'boundary_900041_g{g+offset}.npz')
                run.equal(raw['outgoing'][0, j], src['outgoing'][3, f, r])
                for k, name in (('ports', 'body_ports'), ('correct', 'body_correct'), ('margin', 'body_margin')):
                    run.equal(cases[k][0, j], source_cases[name][g+offset-1, 3, f, r])
            packets = raw['outgoing'].copy()

    def test_06_full_holding_noise_stream_before_case_selection(self):
        for offset in model.OFFSETS:
            actual = model.write_draws(self.index, offset, 900041, self.cfg, self.cycle)
            for j, (f, r, g) in enumerate(self.index.tolist()):
                stream = rng('E022', 900041, 'write', g+offset)
                expected = np.stack([stream.standard_normal((2, self.cfg.recipients, 16, 16))[f//2, r]
                    for _ in range(self.cycle.write_steps)])
                run.equal(actual[:, j], expected)

    def test_07_independent_replay_of_complete_three_body_chain(self):
        produced = self.selection['packets'].copy(); independent = produced.copy()
        for offset in model.OFFSETS:
            actual = self.rebuild(produced, offset)
            expected = audit.replay(independent, self.index, offset, 900041, asdict(self.cfg), asdict(self.cycle))
            audit.equal_dict(actual, expected)
            produced, independent = actual['outgoing'].copy(), expected['outgoing'].copy()

    def test_08_capture_and_holding_commitment_corruption_detected(self):
        raw = self.rebuild()
        for key in ('computed_packets', 'write_state_hashes', 'outgoing'):
            altered = {k:v.copy() for k, v in raw.items()}
            altered[key].flat[0] ^= np.uint8(1)
            with self.assertRaises(AssertionError): audit.equal_dict(raw, altered)

    def test_09_fresh_full_rewriting_and_positive_zero_erasure(self):
        packets = model.base.encode(np.full((3, len(self.index), 2, 16, 16), .95))
        raw = self.rebuild(packets)
        weights = model.base.decode(raw['outgoing']); available = model.renewal.surviving_edges(raw['masks'])
        fresh = model.base.decode(raw['computed_packets'])
        for v in range(3):
            run.equal(weights[v][available], fresh[v][available])
            run.equal(weights[v][~available], np.zeros_like(weights[v][~available]))
        self.assertTrue(np.any(weights[0][available] != .95))

    def test_10_empty_serial_cohort_and_pooled_ratios(self):
        _, index = model.first_failures(np.ones((32, 4, 2, 2), bool))
        self.assertEqual(index.shape, (0, 3))
        packets = np.empty((3, 0, 4096), np.uint8)
        for offset in model.OFFSETS:
            actual = model.rebuild(packets, index, offset, 900041, self.cfg, self.cycle)
            audit.equal_dict(actual, audit.replay(packets, index, offset, 900041, asdict(self.cfg), asdict(self.cycle)))
            packets = actual['outgoing']
        st = run.statistics([1, 0, 0], [1, 9, 0]); self.assertEqual(st['mean'], .1)
        self.assertLess(st['bootstrap_valid'], 10000)
        st = run.statistics([0, 0], [0, 0]); self.assertIsNone(st['mean']); self.assertEqual(st['bootstrap_valid'], 0)

    def test_11_three_body_histories_and_unconditional_losses(self):
        patterns = np.array([[7, 4, 2, 0], [7, 6, 1, 0], [0, 5, 3, 7]], np.int8)
        both = np.stack([(patterns & bit) != 0 for bit in (4, 2, 1)])
        correct = np.repeat(both[..., None], 2, axis=-1)
        episodes, codes = run.episode_values(correct)
        np.testing.assert_array_equal(codes, patterns)
        np.testing.assert_array_equal(episodes['sustained'].sum(axis=1), [1, 1, 1])
        np.testing.assert_array_equal(episodes['any_recovery'].sum(axis=1), [3, 3, 3])
        np.testing.assert_array_equal(episodes['relapse_after_first'].sum(axis=1), [1, 1, 1])
        np.testing.assert_array_equal(run.loss_counts(correct[2]), [0, 1])

    def test_12_all_three_primary_requirements_are_strict(self):
        def result(a, b, c, technical=False):
            return run.decision({k:{'ci95':v} for k, v in zip(('original', 'full_rollback', 'loss_reduction'), (a, b, c))}, technical)
        self.assertTrue(result([.051, .2], [.001, .1], [.001, .1]))
        for a, b, c in (([.05, .2], [.01, .1], [.01, .1]), ([.06, .2], [0, .1], [.01, .1]),
            ([.06, .2], [.01, .1], [0, .1]), ([-.2, -.05], [-.1, -.01], [-.1, -.01]),
            ([None, None], [None, None], [None, None])):
            self.assertFalse(result(a, b, c))
        self.assertIsNone(result([.1, .2], [.1, .2], [.1, .2], True))


if __name__ == '__main__': unittest.main(verbosity=2)
