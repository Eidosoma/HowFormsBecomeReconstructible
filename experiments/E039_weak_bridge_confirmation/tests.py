"""Excluded checks of source evidence, unchanged references and serial causality."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E039_weak_bridge_confirmation import model, run, audit, evidence
from E036_serial_cue_capture_v2 import model as original
from E038_weak_bridge_capture import model as confirmed
from E031_renewal_durability.audit import load_compact
from E035_cue_selective_capture import model as same_body
import numpy as np


class SerialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run.cap_cpus(8); ids, cls.cfg, cls.cycle = run.configuration('fixture'); cls.block = ids[0]
        cls.source = model.acquisition.teach(cls.block, cls.cfg)
        cls.record = np.repeat(cls.source['acquired'][1, :, None], cls.cfg.recipients, axis=1)
        incoming = np.repeat(cls.record[None], 9, axis=0)
        old = np.repeat(cls.record[None], 9, axis=0)
        prior = incoming.copy()
        cls.boundaries, cls.references, cls.confirmation_references = [], [], []
        for g in range(1, 17):
            new = model.replace_record(incoming, cls.block, g, cls.cfg, cls.cycle)
            reference = original.replace_record(old, cls.block, g, cls.cfg, cls.cycle)
            confirmation = confirmed.replace_record(prior, cls.block, g, cls.cfg, cls.cycle)
            cls.boundaries.append(new); cls.references.append(reference)
            cls.confirmation_references.append(confirmation)
            incoming, old = new['outgoing'].copy(), reference['outgoing'].copy()
            prior = confirmation['outgoing'].copy()
        cls.source_path = HERE/'analysis/unit_source.npz'
        cls.boundary_path = HERE/'analysis/unit_boundary.npz'
        evidence.save_source(cls.source_path, cls.source)
        evidence.save(cls.boundary_path, cls.boundaries[0], 'boundary')

    def test_same_body_reference_rules_and_scalar_capture(self):
        raw = self.boundaries[0]
        for n in range(1, 5):
            np.testing.assert_array_equal(raw['developed_end'][n], raw['developed_end'][0])
        available = raw['retained_edges'][0] | raw['eligible_edges'][0]
        data = same_body.construct(raw['developed_end'][0], self.record, available, self.cfg)
        np.testing.assert_array_equal(raw['outgoing'][[0, 1, 4]], data['records'][[0, 1, 2]])
        np.testing.assert_array_equal(raw['computed_packets'], audit.capture(raw['developed_end'], self.cfg.writer_beta))

    def test_reference_policies_match_e036_for_all_sixteen_boundaries(self):
        for new, old in zip(self.boundaries, self.references):
            for n, o in ((0, 0), (1, 1), (4, 2)):
                for key in ('incoming', 'outgoing', 'read_packets', 'retained_packets', 'body_masks',
                            'read_denominators', 'developed_end', 'computed_packets', 'write_end', 'retained_edges', 'eligible_edges'):
                    np.testing.assert_array_equal(new[key][n], old[key][o])
                np.testing.assert_array_equal(new['developed_late_ports'][:, n], old['developed_late_ports'][:, o])
                np.testing.assert_array_equal(new['write_state_hashes'][:, n], old['write_state_hashes'][:, o])
            np.testing.assert_array_equal(new['birth'], old['birth'])
            np.testing.assert_array_equal(new['renewal_mask'], old['renewal_mask'])

    def test_e038_model_and_all_nine_histories_are_unchanged(self):
        self.assertEqual((HERE/'model.py').read_bytes(), (HERE.parent/'E038_weak_bridge_capture/model.py').read_bytes())
        for new, old in zip(self.boundaries, self.confirmation_references):
            self.assertEqual(set(new), set(old))
            for key in new:
                np.testing.assert_array_equal(new[key], old[key])

    def test_exact_zero_fallback_and_nonzero_cue_products(self):
        body = np.full((7, 4, self.cfg.recipients, 2, 16, 16), .2)
        body[:, :, :, 0, 0, :2] = .3
        body[:, :, :, 1, 0, :2] = .1
        body[:, :, :, 0, 0, 2] = .2+1e-12
        x = np.tanh(self.cfg.writer_beta*body)
        d = (x[:, :, :, 0]-x[:, :, :, 1])/2
        contrast = np.stack((d*np.roll(d,-1,-1),d*np.roll(d,-1,-2)),axis=-3)
        standard = model.base.correlations(body,self.cfg.writer_beta).mean(axis=3)
        captured = model.base.decode(model.capture(body,self.cfg.writer_beta))
        self.assertTrue((contrast[2] == 0).any())
        self.assertTrue(((abs(contrast[2])>0)&(abs(contrast[2])<1e-10)).any())
        for n in (2,3,5,6):
            zero = contrast[n]==0
            np.testing.assert_array_equal(captured[n][zero],standard[n][zero])
            np.testing.assert_array_equal(captured[n][~zero],contrast[n][~zero])
            self.assertTrue((captured[n][zero]!=0).all())
        np.testing.assert_array_equal(captured[4],contrast[4])
        np.testing.assert_array_equal(model.capture(body,self.cfg.writer_beta),audit.capture(body,self.cfg.writer_beta))

    def test_each_generation_reads_own_history_with_paired_damage(self):
        incoming = np.repeat(self.record[None], 9, axis=0)
        for raw in self.boundaries:
            np.testing.assert_array_equal(raw['incoming'], incoming)
            available = model.renewal.surviving_edges(raw['body_masks'])
            expected = model.base.encode(model.base.decode(incoming[:7])*available)
            np.testing.assert_array_equal(raw['retained_packets'], expected)
            expected[5] = 0
            np.testing.assert_array_equal(raw['read_packets'], expected)
            for n in range(7):
                np.testing.assert_array_equal(raw['body_masks'][n], raw['renewal_mask'])
            self.assertTrue((raw['renewal_mask'].sum(axis=(-2, -1)) == 24).all())
            self.assertFalse((raw['renewal_mask'] & model.PORTS.any(axis=0)).any())
            incoming = raw['outgoing']
        self.assertFalse(np.array_equal(incoming[0], incoming[3]))

    def test_read_write_and_cumulative_copy_controls(self):
        cumulative = np.ones((4, self.cfg.recipients, 2, 16, 16), bool)
        for raw in self.boundaries:
            self.assertFalse(raw['read_packets'][5].any()); self.assertFalse(raw['read_denominators'][5].any())
            self.assertFalse(raw['erased_packets'].any()); self.assertFalse(raw['outgoing'][6].any())
            np.testing.assert_array_equal(raw['outgoing'][7], self.record)
            cumulative &= model.renewal.surviving_edges(raw['renewal_mask'])
            np.testing.assert_array_equal(raw['outgoing'][8], model.base.encode(model.base.decode(self.record)*cumulative))
            body = raw['developed_end'][5]
            np.testing.assert_array_equal(body[:, :, 0][..., ~model.PORTS[0]], body[:, :, 1][..., ~model.PORTS[0]])

    def test_strict_strength_cutoff_and_absent_edges(self):
        shape = (7, 4, self.cfg.recipients, 2, 16, 16)
        old = np.full(shape, .5); fresh = np.full(shape, -.2); available = np.ones(shape, bool)
        old[..., 0, 0, :4] = [.5, np.nextafter(.5, 1.), -.5, -np.nextafter(.5, 1.)]
        available[..., 1, 0, 0] = False
        packets, held, eligible = model.select(model.base.encode(old), model.base.encode(fresh), available)
        decoded = model.base.decode(packets)
        for n in (0, 2, 4, 5, 6):
            self.assertFalse(held[n, ..., 0, 0, 0].any()); self.assertTrue(held[n, ..., 0, 0, 1].all())
            self.assertFalse(held[n, ..., 0, 0, 2].any()); self.assertTrue(held[n, ..., 0, 0, 3].all())
        for n in (1, 3): self.assertFalse(held[n].any())
        np.testing.assert_array_equal(held | eligible, available)
        np.testing.assert_array_equal(decoded[held], old[held])
        np.testing.assert_array_equal(decoded[eligible], fresh[eligible])
        self.assertFalse(decoded[~available].any())

    def test_capture_precedes_holding_and_inputs_are_immutable(self):
        first = self.boundaries[0]
        packets = first['incoming'].copy()
        shorter = model.replace_record(packets, self.block, 1, self.cfg, replace(self.cycle, write_steps=1))
        for key in ('computed_packets', 'outgoing', 'developed_end'):
            np.testing.assert_array_equal(shorter[key], first[key])
        np.testing.assert_array_equal(packets, first['incoming'])
        np.testing.assert_array_equal(first['computed_packets'], model.capture(first['developed_end'], self.cfg.writer_beta))
        self.assertFalse(np.array_equal(shorter['write_end'], first['write_end']))

    def test_independent_replay_and_corruption_rejection(self):
        source = audit.load_source(self.source_path)
        np.testing.assert_array_equal(audit.replay_source(source, self.block, asdict(self.cfg)), self.source['acquired'][1])
        source = audit.load_source(self.source_path); source.descriptors['capture_states']['sha256'] = '0'*64
        with self.assertRaisesRegex(AssertionError, 'array commitment'):
            audit.replay_source(source, self.block, asdict(self.cfg))
        raw = load_compact(self.boundary_path, 'boundary')
        outgoing, mean = audit.replay_boundary(raw, self.boundaries[0]['incoming'], self.block, 1, asdict(self.cfg), asdict(self.cycle))
        np.testing.assert_array_equal(outgoing, self.boundaries[0]['outgoing'])
        np.testing.assert_array_equal(mean, self.boundaries[0]['developed_late_ports'].mean(axis=0))
        raw = load_compact(self.boundary_path, 'boundary'); raw.descriptors['developed_end']['sha256'] = '0'*64
        with self.assertRaisesRegex(AssertionError, 'array commitment'):
            audit.replay_boundary(raw, self.boundaries[0]['incoming'], self.block, 1, asdict(self.cfg), asdict(self.cycle))
        bad = run.load(self.boundary_path); meta = json.loads(bad['__index__'].tobytes())
        del meta['arrays']['write_end']; bad['__index__'] = np.frombuffer(json.dumps(meta).encode(), np.uint8)
        path = HERE/'analysis/unit_missing_descriptor.npz'; self.assertFalse(path.exists()); np.savez_compressed(path, **bad)
        with self.assertRaises(AssertionError): load_compact(path, 'boundary')
        bad = run.load(self.boundary_path); bad['outgoing'][0, 0, 0, 0] ^= 1
        path = HERE/'analysis/unit_corrupt_retained.npz'; self.assertFalse(path.exists()); np.savez_compressed(path, **bad)
        with self.assertRaisesRegex(AssertionError, 'retained evidence'): load_compact(path, 'boundary')

    def test_focal_axes_and_frozen_timings(self):
        self.assertEqual(model.PANELS, audit.PANELS); self.assertEqual(len(model.PANELS), 74)
        clock = model.terminal_cycle(model.CYCLE)
        self.assertEqual((clock.settling_steps, clock.read_steps, clock.generations), (1024, 2048, 16))
        a, b = model.PANELS.index((16, 'bridge_preserve', 'local_strength')), model.PANELS.index((16, 'standard_preserve', 'local_strength'))
        x = np.zeros((3, 74, 3, 7)); x[:, a, 1, 0] = [.8, .7, .6]; x[:, b, 1, 0] = [.2, .4, .5]
        expected = x[:, a, 1, 0]-x[:, b, 1, 0]
        np.testing.assert_array_equal(run.replication_values(x), expected)
        x[:, [i for i in range(74) if i not in (a, b)]] = .95
        x[:, :, (0, 2)] = .85; x[:, :, :, 1:] = .75
        np.testing.assert_array_equal(run.replication_values(x), expected)
        a, b = model.PANELS.index((16, 'bridge_rewrite', 'local_strength')), model.PANELS.index((16, 'bridge_preserve', 'local_strength'))
        x = np.zeros((3, 74, 3, 7)); x[:, a, 1, 0] = [.9, .8, .7]; x[:, b, 1, 0] = [.7, .7, .8]
        expected = x[:, a, 1, 0]-x[:, b, 1, 0]
        np.testing.assert_array_equal(run.rewrite_values(x), expected)
        x[:, [i for i in range(74) if i not in (a, b)]] = .95
        x[:, :, (0, 2)] = .85; x[:, :, :, 1:] = .75
        np.testing.assert_array_equal(run.rewrite_values(x), expected)

    def test_joint_confirmation_strict_bounds_and_technical_exclusion(self):
        def statistic(lower): return dict(mean=lower+.01, ci95=[lower, lower+.02], block_means=[lower+.01])
        for repair, rewrite, expected in ((.05, .01, False), (.06, 0., False), (.06, -.01, False),
                (.04, .01, False), (np.nextafter(.05, 1.), np.nextafter(0., 1.), True)):
            actual = run.primary_decision(statistic(repair), statistic(rewrite), technical=False)
            self.assertEqual(actual['both_passed'], expected)
            self.assertEqual(actual['replication']['lower_above_margin'], repair > .05)
            self.assertEqual(actual['rewrite_benefit']['lower_above_margin'], rewrite > 0.)
        excluded = run.primary_decision(statistic(.10), statistic(.10), technical=True)
        self.assertIsNone(excluded['both_passed'])
        self.assertIsNone(excluded['replication']['lower_above_margin'])
        self.assertIsNone(excluded['rewrite_benefit']['lower_above_margin'])


if __name__ == '__main__': unittest.main(verbosity=2)
