"""Excluded checks of selection, evidence, receiving and inference contracts."""
from dataclasses import asdict
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E045_weakening_rollback import model, run, audit
from E031_renewal_durability.audit import load_compact, replay_assay
import numpy as np


class RollbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run.cap_cpus(8)
        cls.source, _, cls.cfg, cls.cycle = run.source_config('fixture')
        old = run.load(cls.source/'boundary_900041_g31.npz')['outgoing'][3]
        boundary = run.load(cls.source/'boundary_900041_g32.npz')
        cls.intervention = model.construct(old, boundary['outgoing'][3], boundary['renewal_mask'], 900041, 32)
        cls.raw = model.assay(cls.intervention['packets'], 900041, 32, cls.cfg, cls.cycle)

    def synthetic(self, old_values, new_values, dead_cell=None):
        old = np.zeros((4, 2, 2, 16, 16)); new = old.copy()
        old.reshape(4, 2, 512)[..., :len(old_values)] = old_values
        new.reshape(4, 2, 512)[..., :len(new_values)] = new_values
        dead = np.zeros((4, 2, 16, 16), bool)
        if dead_cell is not None: dead[..., dead_cell[0], dead_cell[1]] = True
        before = model.base.encode(old), model.base.encode(new)
        result = model.construct(*before, dead, 900045, 32)
        np.testing.assert_array_equal(before[0], model.base.encode(old))
        np.testing.assert_array_equal(before[1], model.base.encode(new))
        return result

    def test_single_source_conversion_and_panel_order(self):
        self.assertEqual((self.cycle.read_steps, self.cycle.settling_steps), (24, 12))
        self.assertEqual(model.PANELS, audit.PANELS)
        self.assertEqual(model.PANELS[10], (32, 'targeted_rollback', 'local_strength'))
        self.assertEqual(model.PANELS[9], (32, 'original', 'local_strength'))
        self.assertEqual(model.PANELS[11], (32, 'random_rollback', 'local_strength'))

    def test_strict_strong_cutoff_signed_and_exact_zero_targets(self):
        x = self.synthetic([1., -.9, .5, .5000000001, 1., -.8, 0.],
                           [.5, .2, .1, .50000000001, -.8, 0., .9])
        np.testing.assert_array_equal(x['target'][0, 0].ravel()[:7], [1, 1, 0, 0, 0, 1, 0])
        np.testing.assert_array_equal(x['pool'][0, 0].ravel()[:7], [1, 1, 0, 1, 1, 1, 0])
        changed = model.base.decode(x['packets'][1])[0, 0].ravel()[:7]
        np.testing.assert_array_equal(changed, [1., -.9, .1, .50000000001, -.8, -.8, .9])

    def test_physical_erasures_including_torus_seams_stay_erased(self):
        old = np.ones((4, 2, 2, 16, 16)); new = old*.25
        dead = np.zeros((4, 2, 16, 16), bool); dead[..., 0, 0] = True
        # Four incident coordinates, including wraparound neighbors.
        for direction, y, x in ((0, 0, 0), (0, 0, 15), (1, 0, 0), (1, 15, 0)):
            new[..., direction, y, x] = 0.
        result = model.construct(model.base.encode(old), model.base.encode(new), dead, 900045, 24)
        self.assertEqual(int((~result['available']).sum()), 4*4*2)
        self.assertFalse(result['target'][~result['available']].any())
        for packet in result['packets']:
            self.assertFalse(model.base.decode(packet)[~result['available']].any())

    def test_old_weak_new_repairs_and_unchanged_strong_are_preserved(self):
        x = self.synthetic([0., 1.e-300, -.5, .5, 1., -.9], [.8, .7, -.9, -.7, 1., .1])
        old, new = model.base.decode(x['incoming']), model.base.decode(x['outgoing'])
        protected = (abs(old) <= .5) | (old == new)
        for packet in x['packets']:
            np.testing.assert_array_equal(model.base.decode(packet)[protected], new[protected])
        np.testing.assert_array_equal(x['packets'][0], x['outgoing'])

    def test_empty_target_and_random_pool_containing_only_targets(self):
        empty = self.synthetic([1., .5], [.75, .8])
        self.assertFalse(empty['target'].any()); self.assertTrue(empty['pool'].any())
        np.testing.assert_array_equal(empty['packets'], np.broadcast_to(empty['outgoing'], empty['packets'].shape))
        full = self.synthetic([1., -.9], [.1, -.2])
        np.testing.assert_array_equal(full['selected'], full['target'])
        np.testing.assert_array_equal(full['packets'][1], full['packets'][2])

    def test_deterministic_random_counts_and_independent_reconstruction(self):
        x = self.synthetic([1., -.9, .8, -.7, .6], [.1, .7, -.9, .8, .9])
        other = audit.reconstruct(x['incoming'], x['outgoing'], x['renewal_mask'], 900045, 32)
        for key in x: np.testing.assert_array_equal(x[key], other[key], err_msg=key)
        np.testing.assert_array_equal(x['counts'][..., 0], x['counts'][..., 2])
        self.assertTrue((x['counts'][..., 1] > x['counts'][..., 0]).all())
        self.assertFalse((x['selected'] & ~x['pool']).any())

    def test_original_exact_endpoints_all_controls_and_paired_inputs(self):
        original = run.load(self.source/'assay_900041_h32.npz')
        np.testing.assert_array_equal(self.raw['late_ports'].mean(axis=0)[[0, 3]], original['mean_ports'][[3, 14]])
        for k in ('masks', 'permutations'): np.testing.assert_array_equal(self.raw[k], original[k])
        alone = model.receiver.assay(self.intervention['outgoing'][None], 900041, 32, self.cfg, self.cycle)
        for k in ('birth', 'masks', 'permutations'): np.testing.assert_array_equal(self.raw[k], alone[k])
        for k in ('end', 'late_mean', 'receiver_denominators'):
            np.testing.assert_array_equal(self.raw[k][[0, 3]], alone[k])

    def test_denominators_recomputed_after_packet_and_injury_controls(self):
        x = self.synthetic([1., .8], [.1, -.9])
        raw = model.assay(x['packets'], 900045, 32, self.cfg, self.cycle)
        effective = np.concatenate([model.base.effective_weights(p, raw['masks']) for p in raw['packets']], axis=0)
        expected = np.zeros(effective.shape[:-3]+(16, 16))
        for y in range(16):
            for xcoord in range(16):
                expected[..., y, xcoord] = (abs(effective[..., 0, y, xcoord])+abs(effective[..., 0, y, (xcoord-1)%16])
                    + abs(effective[..., 1, y, xcoord])+abs(effective[..., 1, (y-1)%16, xcoord]))
        np.testing.assert_array_equal(raw['receiver_denominators'][:3], np.full_like(expected, 4.))
        np.testing.assert_array_equal(raw['receiver_denominators'][3:], expected)
        self.assertTrue((expected[0] != expected[1]).any())
        self.assertFalse(expected[..., [3, 5], :, :].any())
        path = HERE/'analysis/synthetic_compact.npz'
        model.evidence.save(path, raw, 'assay')
        recovered = replay_assay(load_compact(path, 'assay'), x['packets'], 900045, 32, asdict(self.cfg), asdict(self.cycle))
        for a, b in zip(model.score(raw['late_ports'].mean(axis=0), self.cfg), recovered): np.testing.assert_array_equal(a, b)

    def test_compact_replay_and_corrupted_commitment_rejection(self):
        path = HERE/'analysis/compact_fixture.npz'
        model.evidence.save(path, self.raw, 'assay')
        compact = load_compact(path, 'assay')
        replay = replay_assay(compact, self.intervention['packets'], 900041, 32, asdict(self.cfg), asdict(self.cycle))
        for a, b in zip(model.score(self.raw['late_ports'].mean(axis=0), self.cfg), replay): np.testing.assert_array_equal(a, b)
        compact.descriptors['end']['sha256'] = '0'*64
        with self.assertRaisesRegex(AssertionError, 'array commitment'):
            replay_assay(compact, self.intervention['packets'], 900041, 32, asdict(self.cfg), asdict(self.cycle))

    def test_primary_axes_exclude_other_panels_injuries_controls(self):
        values = np.zeros((3, 12, 3, 7))
        values[:, 10, 1, 0] = [.8, .7, .6]; values[:, 9, 1, 0] = [.2, .4, .5]
        values[:, 11, 1, 0] = [.3, .2, .1]
        expected = {k:v.copy() for k, v in run.primary_values(values).items()}
        np.testing.assert_array_equal(expected['original'], values[:, 10, 1, 0]-values[:, 9, 1, 0])
        np.testing.assert_array_equal(expected['random_rollback'], values[:, 10, 1, 0]-values[:, 11, 1, 0])
        values[:, :9] = .91; values[:, :, (0, 2)] = .9; values[:, :, :, 1:] = .9
        for key, result in run.primary_values(values).items(): np.testing.assert_array_equal(result, expected[key])

    def test_strict_joint_primary_thresholds_and_technical_null(self):
        for useful, specific, expected in ((.05, .1, False), (.06, 0., False), (.050001, .000001, True), (.049, -.01, False)):
            stats = dict(original=dict(ci95=[useful, .2]), random_rollback=dict(ci95=[specific, .2]))
            self.assertEqual(run.primary_decision(stats, False), expected)
            self.assertIsNone(run.primary_decision(stats, True))

    def test_rescues_and_losses_keep_all_cases(self):
        low = np.array([[[0, 0, 1, 1]], [[1, 0, 1, 0]]], dtype=bool)
        high = np.array([[[0, 1, 0, 1]], [[0, 0, 0, 0]]], dtype=bool)
        result = run.transition_counts(low, high)
        self.assertEqual(result['total'], 8)
        self.assertEqual(result['counts'], dict(both_fail=3, rescued=1, lost=3, both_succeed=1))
        self.assertEqual(result['by_block']['lost'], [1, 2])


if __name__ == '__main__': unittest.main(verbosity=2)
