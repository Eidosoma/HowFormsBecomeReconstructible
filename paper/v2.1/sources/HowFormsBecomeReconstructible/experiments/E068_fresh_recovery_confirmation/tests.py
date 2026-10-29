"""Writer parity, packet-only controls, reader aliasing and inferential gates."""
import unittest
from unittest.mock import patch
import numpy as np
from common import rng
from E068_fresh_recovery_confirmation import model, audit_model, data, inference
from E068_fresh_recovery_confirmation.plan import settings, index


def legacy_projection_check(packets, block, cfg, raw):
    from E058_capture_benefit_persistence import model as legacy
    shape = (3, 2, *packets.shape)
    repeated = np.broadcast_to(packets, shape).copy()
    def remap(tag, *parts):
        assert tag == 'E058'
        return rng('E068', *parts)
    def damage(b, tag, config):
        assert b == block and tag == 'E058_renewal_g1'
        m = np.zeros((4, config.recipients, 3, 16, 16), bool)
        m[:, :, 1] = model.masks(block, config.recipients, 'develop_injury', 1)
        return m
    config = legacy.base.Config(**cfg['config'])
    with patch.object(legacy, 'rng', side_effect=remap), patch.object(legacy.base, 'damage_masks', side_effect=damage):
        old = legacy.rebuild(repeated, block, 1, config, cfg['cycle'])
    assert old['outgoing'][0, 0].tobytes() == raw['outgoing'].tobytes()
    for key in ('end', 'ordinary', 'contrast', 'fallback', 'write_end', 'mean_ports'):
        expected = old[key].reshape(3, 2, *raw[key].shape)[0, 0]
        assert expected.tobytes() == raw[key].tobytes(), key
    for key in ('birth', 'masks'):
        assert old[key].tobytes() == raw[key].tobytes(), key


def alias_check(packets, block, cfg, fresh):
    ids = [0, 1, 2, 3, 4, 0, 1, 2, 3, 4]
    repeated = model.develop(packets[ids], block, cfg['reader'], cfg['reader'], 'terminal')
    for key in ('effective', 'denominator', 'coupling', 'end', 'mean_ports', 'boundary_counts'):
        assert repeated[key].tobytes() == fresh[key][ids].tobytes(), key
    assert repeated['late_ports'].tobytes() == fresh['late_ports'][:, ids].tobytes()
    for h in (0, 1, 3):
        assert index(h, 'protected', 'mixture_sham') == 2
        assert index(h, 'copy', 'erased') == 4
    assert index(1, 'rewrite', 'erased') == 9 and index(3, 'rewrite', 'erased') == 18


class Checks(unittest.TestCase):
    def test_new_cohort_and_unchanged_scientific_settings(self):
        from E067_ordinary_mixture_rebuilding.plan import settings as old
        from E065_fresh_compatibility_confirmation.plan import settings as source
        new = settings('scientific')
        prior = old('scientific')
        self.assertEqual(len(new['blocks']), 32)
        self.assertFalse(set(new['blocks']) & set(prior['blocks']))
        for field in ('config', 'cycle', 'reader', 'primary', 'primary_confidence', 'slots', 'horizons'):
            self.assertEqual(new[field], prior[field])
        s = source('scientific')
        for name, previous in (('source_config', 'config'), ('source_cycle', 'source_cycle'),
                               ('body', 'body'), ('source_continuation', 'continuation')):
            self.assertEqual(new[name], s[previous])
        data.verify_receipts('scientific')
        with self.assertRaises(AssertionError):
            data.reference('scientific', 'source_039000.npz')

    def fixture(self):
        cfg = settings('fixture')
        source = data.technical_source('fixture')
        inter = model.intervene(source)
        return cfg, source, inter

    def test_archived_initial_intervention(self):
        cfg, source, inter = self.fixture()
        data.equal(inter, audit_model.intervene(source))
        self.assertEqual(inter['packets'][:2].tobytes(), data.reference('fixture', 'interventions_900041.npz')['packets'][:2].tobytes())
        self.assertEqual(inter['packets'][2:4].tobytes(), data.reference('fixture', 'interventions_900041.npz')['packets'][2:4].tobytes())
        self.assertFalse(inter['packets'][4].any())

    def test_exact_zero_fallback_and_small_difference(self):
        state = np.full((1, 4, 1, 2, 16, 16), .1)
        available = np.ones((4, 1, 2, 16, 16), bool)
        for skew in (0., 1e-5):
            state[..., 1, :, :] = .1 + skew
            result = model.capture(state, available, 3.)
            independent = audit_model.capture(state, available, 3.)
            for a, b in zip(result, independent, strict=True):
                self.assertEqual(a.tobytes(), b.tobytes())
            self.assertEqual(bool(result[3].all()), skew == 0)
            self.assertTrue((result[0] > 0).all())
            self.assertEqual(result[0].tobytes(), result[1 if skew == 0 else 2].tobytes())

    def test_renewal_equations_and_unchanged_writer_projection(self):
        cfg, source, inter = self.fixture()
        raw = model.rebuild(inter['packets'], 900041, 1, cfg['config'], cfg['cycle'])
        data.equal(raw, audit_model.rebuild(inter['packets'], 900041, 1, cfg['config'], cfg['cycle']))
        legacy_projection_check(inter['packets'], 900041, cfg, raw)
        self.assertTrue(model.base.decode(raw['outgoing'][4]).any())
        self.assertEqual(raw['outgoing'][4, 0].tobytes(), raw['outgoing'][4, 1].tobytes())

    def test_unchanged_e067_equations_under_new_stream_tag(self):
        from E067_ordinary_mixture_rebuilding import model as previous
        cfg, source, inter = self.fixture()
        def remap(tag, *parts):
            self.assertEqual(tag, 'E067')
            return rng('E068', *parts)
        with patch.object(previous, 'rng', side_effect=remap):
            old = previous.rebuild(inter['packets'], 900041, 1, cfg['config'], cfg['cycle'])
            old_reader = previous.develop(inter['packets'], 900041, cfg['reader'], cfg['reader'], 'terminal')
        data.equal(old, model.rebuild(inter['packets'], 900041, 1, cfg['config'], cfg['cycle']))
        data.equal(old_reader, model.develop(inter['packets'], 900041, cfg['reader'], cfg['reader'], 'terminal'))

    def test_cumulative_erasure_and_retained_values(self):
        cfg, source, inter = self.fixture()
        copied = inter['packets'].copy()
        available = np.ones((4, 2, 2, 16, 16), bool)
        for g in range(1, 4):
            mask = model.masks(900041, 2, 'develop_injury', g)
            available &= model.reader.surviving_edges(mask)
            other = audit_model.copy_step(copied, mask)
            copied = model.copy_step(copied, mask)
            self.assertEqual(copied.tobytes(), other.tobytes())
        expected = model.base.encode(model.base.decode(inter['packets']) * available)
        self.assertEqual(copied.tobytes(), expected.tobytes())
        self.assertFalse(model.base.decode(copied[4]).any())

    def test_terminal_replay_and_deduplication(self):
        cfg, source, inter = self.fixture()
        initial = inter['packets']
        packets = np.concatenate((initial, initial, initial[:4], initial, initial[:4]))
        fresh = model.develop(packets, 900041, cfg['reader'], cfg['reader'], 'terminal')
        data.equal(fresh, audit_model.develop(packets, 900041, cfg['reader'], cfg['reader'], 'terminal'))
        cases, records = model.diagnostics(packets, fresh, cfg['reader'])
        c2, r2 = audit_model.diagnostics(packets, fresh, cfg['reader'])
        data.equal(cases, c2); data.equal(records, r2)
        alias_check(packets, 900041, cfg, fresh)
        self.assertFalse(cases['both'][4].any())

    def test_scoring_partition_threshold_and_signed_zero(self):
        values = np.zeros((5, 4, 1, 2, 2))
        for f, rule in enumerate((1., -1., 1., -1.)):
            for c, cue in enumerate((1., -1.)):
                values[:, f, 0, c] = [rule * cue * .25, -rule * cue * .25]
        self.assertFalse(model.score(values, .25)['both'].any())
        self.assertTrue(model.score(values, .25)['correct_signs_below_threshold'].all())
        for x in (values, values * 1.01, -values * 1.01, values * 0.):
            a, b = model.score(x, .25), audit_model.score(x, .25)
            data.equal(a, b)
            total = sum(a[k].astype(int) for k in ('both', 'correct_signs_below_threshold', 'zero_without_wrong_sign', 'any_wrong_sign'))
            self.assertTrue((total == 1).all())

    def test_recovery_requires_absolute_gain_and_both_controls(self):
        c = {'both': np.zeros((23, 4, 1), bool)}
        c['both'][16:18] = True
        controls = [{'pass': True}] * 2
        s = inference.analyze([c, c], controls, 'scientific')
        inference.audit([c, c], controls, s, 'scientific')
        self.assertTrue(s['recovery_supported'])
        self.assertEqual(s['status'], 'FRESH_RECOVERY_CONFIRMED')
        for altered in ((2, 3), (21, 22), (18,)):
            other = {'both': c['both'].copy()}
            other['both'][list(altered)] = True
            s = inference.analyze([other, other], controls, 'scientific')
            inference.audit([other, other], controls, s, 'scientific')
            self.assertFalse(s['recovery_supported'])
        for mode, control in (('fixture', controls), ('benchmark', controls), ('scientific', [{'pass': False}] * 2)):
            s = inference.analyze([c, c], control, mode)
            inference.audit([c, c], control, s, mode)
            self.assertIsNone(s['recovery_supported'])
            self.assertTrue(all(v is None for v in s['primary_effects'].values()))
        self.assertEqual(inference.classification([0., .1]), 'UNRESOLVED')


if __name__ == '__main__':
    unittest.main()
