"""Excluded equation, precision, channel, evidence and inference checks."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, rng
from E052_precision_normalization import model, audit, audit_dynamics as dyn, evidence, run
from E052_precision_normalization.design import *
import numpy as np


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cap_cpus(8)
        cls.cfg = replace(model.base.Config(), recipients=1, teach_steps=12, capture_steps=6, observe_steps=2)
        cls.cycle = model.Cycle(read_steps=4, settling_steps=2, write_steps=1, generations=32)
        cls.packet = np.zeros((33, 4, 1, 4096), np.uint8)
        cls.mask = np.zeros((4, 1, 16, 16), bool)
        cls.tags = np.zeros((33, 4, 1, 2, 16, 16), bool)
        cls.available = np.ones((4, 1, 2, 16, 16), bool)

    def test_01_fixed_matrix_and_fresh_ids(self):
        self.assertEqual(len(CONDITIONS), 33)
        self.assertEqual([r['id'] for r in REGIMES], ['reference', 'record32', 'arithmetic32', 'grid_2m16', 'grid_2m12',
            'record_noise_1e4', 'record_noise_1e3', 'record_noise_leakage_1e4', 'floor_1e6', 'floor_1e4', 'floor_1e2'])
        self.assertEqual(PRIMARY, ('arithmetic32', 'grid_2m16', 'record_noise_1e4', 'floor_1e4'))
        self.assertEqual(REGIMES[1]['arithmetic'], 'float64'); self.assertEqual(REGIMES[2]['arithmetic'], 'float32')
        ids, cfg, cycle = run.configuration('fixture'); self.assertEqual(ids, [900041]); self.assertEqual(cycle.generations, 32)
        spec = json.loads((HERE / 'SOURCE_DATA.json').read_text())
        self.assertFalse(set(spec['blocks']) & set(spec['prior_block_ids']))

    def test_02_actual_typed_arithmetic(self):
        random = rng('E052', 'excluded', 'typed_step')
        v = random.normal(0, .4, (2, 4, 1, 2, 16, 16)).astype(np.float32)
        w = random.normal(0, .3, (2, 4, 1, 1, 2, 16, 16)).astype(np.float32)
        d = model.renewal.incident_sum(abs(w)); noise = random.normal(size=v.shape).astype(np.float32)
        actual = model.typed_step(v, w, d, noise, self.cfg, True, 0.)
        self.assertEqual(actual.dtype, np.float32)
        dyn.equal(actual, dyn.step(v, w, d, noise, asdict(self.cfg), True, 0.))
        double = model.typed_step(v.astype(float), w.astype(float), d.astype(float), noise.astype(float), self.cfg, True, 0.)
        self.assertTrue((actual != double.astype(np.float32)).any())

    def test_03_precision_sensitive_fallback(self):
        v = np.full((1, 4, 1, 2, 16, 16), .2); v[:, :, :, 0, 0, :2] += 1e-10
        for kind in (np.float64, np.float32):
            a, b = model.capture(v.astype(kind), 3.), dyn.capture(v.astype(kind), 3.)
            for x, y in zip(a, b): dyn.equal(x, y)
        self.assertFalse(model.capture(v, 3.)[2][0, 0, 0, 0, 0, 0])
        self.assertTrue(model.capture(v.astype(np.float32), 3.)[2][0, 0, 0, 0, 0, 0])

    def test_04_quantizer_ties_and_bounds(self):
        weights = np.zeros((33, 4, 1, 2, 16, 16)); delta = 2.**-16
        weights[..., 0, 0, :6] = delta * np.array([.5, 1.5, 2.5, -.5, -1.5, -2.5])
        raw = model.channel(model.base.encode(weights), self.available, 900041, 0)
        w = model.base.decode(raw['outgoing'])
        np.testing.assert_array_equal(w[3, 0, 0, 0, 0, :6], delta*np.array([0, 2, 2, 0, -2, -2]))
        self.assertLessEqual(float(abs(w[3]-weights[3]).max()), delta/2)
        dyn.equal_dict(raw, dyn.transmit(model.base.encode(weights), self.available, 900041, 0))

    def test_05_record_noise_support_and_physical_erasure(self):
        av = self.available.copy(); av[..., 0, 0, 0] = False
        result = model.channel(self.packet, av, 900041, 1); w = model.base.decode(result['outgoing'])
        self.assertFalse(w[5].any()); self.assertFalse(w[6].any())
        self.assertEqual(np.count_nonzero(w[7]), np.count_nonzero(av))
        self.assertFalse(w[..., 0, 0, 0].any())
        dyn.equal_dict(result, dyn.transmit(self.packet, av, 900041, 1))

    def test_06_noise_draws_and_clipping(self):
        w = np.ones((33, 4, 1, 2, 16, 16)); w[..., 0, 0, :2] = [1e-320, -1e-320]
        packets = model.base.encode(w); a = model.channel(packets, self.available, 900041, 2)
        b = dyn.transmit(packets, self.available, 900041, 2); dyn.equal_dict(a, b)
        out = model.base.decode(a['outgoing']); self.assertLessEqual(abs(out).max(), 1.)
        self.assertGreater(int(a['channel_counts'][5, ..., 6].sum()), 0)
        dyn.equal(a['channel_noise'][0], a['channel_noise'][1])
        self.assertFalse(np.array_equal(a['channel_noise'], model.channel(packets, self.available, 900041, 3)['channel_noise']))

    def test_07_identity_and_storage_rounding(self):
        w = rng('E052', 'excluded', 'record').uniform(-1, 1, (33, 4, 1, 2, 16, 16)); w[..., 0, 0, 0] = -0.
        packets = model.base.encode(w); raw = model.channel(packets, self.available, 900041, 0)
        for index in (0, 8, 9, 10, 11, 22): dyn.equal(raw['outgoing'][index], packets[index])
        for index in (1, 2, 12, 13, 23, 24):
            dyn.equal(model.base.decode(raw['outgoing'])[index], w[index].astype(np.float32).astype(np.float64))
        self.assertEqual(raw['outgoing'].shape[-1], 4096)

    def test_08_normalization_scaling_floor_and_zero(self):
        random = rng('E052', 'excluded', 'scaling'); v = random.uniform(-.4, .4, (1, 4, 1, 2, 16, 16))
        w = random.uniform(-.2, .2, (1, 4, 1, 1, 2, 16, 16)); d = model.renewal.incident_sum(abs(w)); noise = np.zeros_like(v)
        a = model.typed_step(v, w, d, noise, self.cfg, True, 0.)
        b = model.typed_step(v, w*2.**-20, d*2.**-20, noise, self.cfg, True, 0.); dyn.equal(a, b)
        dyn.equal(a, model.typed_step(v, w, d, noise, self.cfg, True, 1e-8))
        altered = model.typed_step(v, w*2.**-20, d*2.**-20, noise, self.cfg, True, 1e-4)
        self.assertFalse(np.array_equal(a, altered))
        zero = model.typed_step(v, w*0, d*0, noise, self.cfg, True, 1e-4)
        dyn.equal(zero, model.typed_step(v, w*0, d*0, noise, self.cfg, True, 0.))
        v = np.ones_like(v); w = np.full_like(w, 1e-6); d = model.renewal.incident_sum(abs(w))
        expected = 1 + self.cfg.dt * 2 * (.04 - 1)
        np.testing.assert_array_equal(model.typed_step(v, w, d, noise, self.cfg, True, 1e-4), np.full_like(v, expected))

    def test_09_common_scoring_float64(self):
        v = rng('E052', 'excluded', 'observation').normal(size=(2, 4, 1, 2, 16, 16)).astype(np.float32)
        obs = model.observations(v); self.assertEqual(obs.dtype, np.float64)
        dyn.equal(obs, dyn.observe(v)); dyn.equal(obs, model.observations(v.astype(float)))

    def test_10_next_body_repair_and_denominator_diagnostics(self):
        w = np.zeros((33, 4, 1, 2, 16, 16)); tags = self.tags.copy()
        w[..., 0, 0, 0] = 1e-6; tags[..., 0, 0, 0] = True
        d = model.renewal.incident_sum(abs(w)); a = model.numerical_diagnostics(w, d, self.mask, tags)
        dyn.equal_dict(a, dyn.numerics(w, d, self.mask, tags))
        self.assertTrue((a['repair_counts'][..., 0] == 1).all())
        self.assertTrue((a['repair_counts'][..., 2] == 1).all())
        self.assertEqual(a['denom_counts'][9, 0, 0, 3], 2)
        self.assertAlmostEqual(a['attenuation'][9, 0, 0, 0, 0], .01)
        self.assertEqual(a['repair_fraction'][9, 0, 0, 0, 0], 1.)

    def test_11_independent_rebuilding_replay(self):
        a = model.rebuild(self.packet, 900041, 1, self.mask, self.tags, self.cfg, self.cycle)
        b = dyn.replay(self.packet, 900041, 1, self.mask, self.tags, asdict(self.cfg), asdict(self.cycle))
        dyn.equal_dict(a, b)
        for index in (0, 11, 22): dyn.equal(a['birth'][index], a['birth'][0])
        self.assertFalse(a['repair_counts'][..., 0].any())
        self.assertEqual(a['noise_moments'].shape, (3, 6))

    def test_12_capture_precedes_holding(self):
        a = model.rebuild(self.packet, 900041, 2, self.mask, self.tags, self.cfg, self.cycle)
        b = model.rebuild(self.packet, 900041, 2, self.mask, self.tags, self.cfg, replace(self.cycle, write_steps=3))
        for name in ('end', 'pre_channel', 'outgoing', 'channel_counts'): dyn.equal(a[name], b[name])
        self.assertFalse(np.array_equal(a['write_end'], b['write_end']))

    def test_13_native_common_packet_identity_and_deduplication(self):
        packet = model.base.encode(rng('E052', 'excluded', 'assay').normal(0, .1, (33, 4, 1, 2, 16, 16)))
        a = model.assay(packet, packet[0], 900041, 0, self.cfg, self.cycle)
        b = dyn.assay(packet, packet[0], 900041, 0, asdict(self.cfg), asdict(self.cycle)); dyn.equal_dict(a, b)
        panels, mapping = assay_layout(0); self.assertEqual(len(panels), 51)
        self.assertEqual(len(assay_layout(32)[0]), 50); self.assertEqual((panels, mapping), dyn.layout(0))
        for name, role, index in mapping:
            dyn.equal(a['records'][index], packet[CONDITIONS.index(name)])
        self.assertEqual(dict((role, i) for name, role, i in mapping if name == 'paired/record32')['native'],
                         dict((role, i) for name, role, i in mapping if name == 'paired/record32')['common'])

    def test_14_channel_timing_at_acquisition(self):
        acquired = model.base.encode(np.full((4, 2, 16, 16), .123456789))
        a = model.initial(acquired, 900041, self.cfg); b = dyn.initialization(acquired, 900041, asdict(self.cfg))
        dyn.equal_dict(a, b); self.assertFalse(np.array_equal(a['outgoing'][5], a['pre_channel'][5]))
        assay = model.assay(a['outgoing'], acquired[:, None], 900041, 0, self.cfg, self.cycle)
        for index, (record, reader) in enumerate(assay_layout(0)[0]):
            if record >= 0: dyn.equal(assay['records'][index], a['outgoing'][record])

    def test_15_evidence_corruption_is_rejected(self):
        raw = model.initial(model.base.encode(np.zeros((4, 2, 16, 16))), 900041, self.cfg)
        with tempfile.TemporaryDirectory(prefix='excluded_', dir=HERE / 'analysis') as tmp:
            path = Path(tmp) / 'valid.npz'; evidence.save(path, raw, 'initial'); audit.check_compact(path, raw, 'initial')
            saved = run.load(path); saved['outgoing'] = saved['outgoing'].copy(); saved['outgoing'].flat[0] ^= 1
            bad = Path(tmp) / 'bad.npz'; run.save(bad, saved)
            with self.assertRaises(AssertionError): audit.check_compact(bad, raw, 'initial')

    def test_16_nine_strict_primary_gates_and_technical_null(self):
        stats = {'assay/32/paired/reference/native/scattered': {'ci95': [.8, .9]}}
        for r in PRIMARY:
            stats[f'assay/32/paired/{r}/native/scattered'] = {'ci95': [.8, .9]}
            stats[f'regime_effect/paired/{r}/native'] = {'ci95': [-.04, .02]}
        self.assertTrue(run.decisions(stats, False)['primary_decision'])
        self.assertEqual(len(run.decisions(stats, False)['primary_gates']), 9)
        self.assertIsNone(run.decisions(stats, True)['primary_decision'])
        stats['regime_effect/paired/arithmetic32/native']['ci95'] = [-.05, .01]
        self.assertEqual(run.decisions(stats, False)['primary_classifications']['arithmetic32'], 'UNRESOLVED')
        stats['regime_effect/paired/arithmetic32/native']['ci95'] = [-.1, -.051]
        self.assertEqual(run.decisions(stats, False)['primary_classifications']['arithmetic32'], 'LOSS_EXCEEDS_FIVE_POINTS')
        stats['assay/32/paired/reference/native/scattered']['ci95'][0] = .75
        self.assertFalse(run.decisions(stats, False)['primary_gates']['reference_lower_above_075'])

    def test_17_both_cue_axis_and_strict_margin(self):
        values = np.empty((50, 4, 1, 2, 3, 2))
        for n, f, r, c, d in np.ndindex(50, 4, 1, 2, 3):
            desired = model.base.RULES[f] * model.base.CUES[c]; values[n, f, r, c, d] = [desired, -desired]
        values[0, 0, 0, 1, 1] = [-.25, .25]
        a = model.score(values, self.cfg); dyn.equal_dict(a, dyn.score(values, asdict(self.cfg)))
        self.assertEqual(a['correct'][0, :, :, :, 1].all(axis=2).mean(), .75)

    def test_18_independent_inference_axes(self):
        data = []
        random = rng('E052', 'excluded', 'synthetic_scores')
        for block in range(3):
            d = {}
            for h in HORIZONS: d[f'assay_h{h}_correct'] = random.random((len(assay_layout(h)[0]), 4, 1, 2, 3)) > .2
            d['body_correct'] = random.random((32, 33, 4, 1, 2)) > .2
            d['counts'] = np.ones((32, 33, 4, 1, 13), np.int64); d['sums'] = np.ones((32, 33, 4, 1, 2))
            for field, labels in run.DIAGNOSTICS.items():
                d[field] = np.ones((33 if field.startswith('channel_') else 32, 33, 4, 1, len(labels)))
            data.append(d)
        a, b = run.block_values(data), audit.values_from_cases(data)
        self.assertEqual(set(a), set(b))
        for k in a: dyn.equal(a[k], b[k])


if __name__ == '__main__': unittest.main(verbosity=2)
