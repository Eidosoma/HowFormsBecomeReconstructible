"""Meaningful controls for one-time pruning, unchanged writing and inference."""
import inspect
import unittest
from unittest.mock import patch
import numpy as np
from common import check_inputs, rng
from E073_saved_cohort_reversal_replication import model, audit_model, data, inference
from E073_saved_cohort_reversal_replication.plan import ROOT, settings, SLOTS, index


def legacy_projection_check(source, inter, packets, block, cfg, raw, fresh):
    from E072_single_pruning_persistence import model as legacy
    check_inputs(ROOT/'E072_single_pruning_persistence/analysis/freeze_v1')
    old_inter = legacy.intervene(source)
    data.equal(old_inter, inter)
    def remap(tag, *parts):
        assert tag == 'E072'
        return rng('E073', *parts)
    with patch.object(legacy, 'rng', side_effect=remap):
        old = legacy.rebuild(inter['packets'], block, 1, cfg['config'], cfg['cycle'])
        read = legacy.develop(packets, block, cfg['reader'], cfg['reader'], 'terminal')
    data.equal(old, raw)
    data.equal(read, fresh)
    a = model.diagnostics(packets, inter, fresh, raw, cfg['reader'])
    b = legacy.diagnostics(packets, old_inter, read, old, cfg['reader'])
    for x, y in zip(a, b, strict=True): data.equal(x, y)


class Checks(unittest.TestCase):
    def fixture(self):
        cfg = settings('fixture')
        source = data.source('fixture', 900041)
        return cfg, source, model.intervene(source)

    def test_frozen_equations_unchanged(self):
        from E067_ordinary_mixture_rebuilding import model as previous, audit_model as previous_audit
        for new, old in ((model, previous), (audit_model, previous_audit)):
            for name in ('digest', 'masks', 'coupling', 'develop', 'capture', 'rebuild', 'score'):
                self.assertEqual(inspect.getsource(getattr(new, name)),
                                 inspect.getsource(getattr(old, name)).replace("'E067'", "'E073'"))
        cfg = settings('scientific')
        self.assertEqual(cfg['blocks'], list(range(40000, 40032)))
        self.assertEqual(cfg['cycle']['generations'], 1)
        self.assertEqual(len(SLOTS), 18)
        self.assertEqual(index(1, 'pruned', 'mixture_pulse'), 16)

    def test_complete_E072_numerical_source_and_settings_identity(self):
        from E072_single_pruning_persistence import audit_model as previous_audit
        from E072_single_pruning_persistence.plan import settings as previous_settings
        self.assertTrue(previous_audit.__file__.endswith('E072_single_pruning_persistence/audit_model.py'))
        for name in ('model.py', 'audit_model.py'):
            old = (ROOT/'E072_single_pruning_persistence'/name).read_text()
            expected = old.replace('E072_single_pruning_persistence', 'E073_saved_cohort_reversal_replication').replace('E072', 'E073')
            self.assertEqual((ROOT/'E073_saved_cohort_reversal_replication'/name).read_text(), expected)
        allowed = {'blocks','source_experiment','E068_prior_outcomes_known','E072_prior_outcomes_known',
                   'independent_source_cohort_from_E072','reversal_replication_criterion'}
        for mode in ('fixture','benchmark','scientific'):
            old, new = previous_settings(mode), settings(mode)
            self.assertEqual({k:v for k,v in old.items() if k not in allowed},
                             {k:v for k,v in new.items() if k not in allowed})

    def test_E072_inference_identity_after_stream_remapping(self):
        from E072_single_pruning_persistence import inference as previous
        stream = rng('E073', 'development_statistics')
        cases = [dict(both=stream.random((18,4,2)) > .5,
                      minimum_margin=stream.standard_normal((18,4,2)),
                      aligned_transfer=stream.standard_normal((18,4,2))) for _ in range(3)]
        controls = [{'pass':True}]*3
        def remap(tag, *parts):
            assert tag == 'E072'
            return rng('E073', *parts)
        with patch.object(previous, 'rng', side_effect=remap):
            old = previous.analyze(cases, controls, 'scientific')
        new = inference.analyze(cases, controls, 'scientific')
        self.assertEqual({k:v for k,v in new.items() if k != 'reversal_replicated'}, old)
        inference.audit(cases, controls, new, 'scientific')

    def test_reversal_replication_requires_both_specific_directions(self):
        controls = [{'pass':True}]*2
        for before in (-1, 0, 1):
            for after in (-1, 0, 1):
                both = np.zeros((18,4,1), bool)
                if before > 0: both[6:8] = True
                if before < 0: both[2:4] = True
                if after > 0: both[15:17] = True
                if after < 0: both[11:13] = True
                cases = [dict(both=both)]*2
                result = inference.analyze(cases, controls, 'scientific')
                inference.audit(cases, controls, result, 'scientific')
                self.assertEqual(result['reversal_replicated'], before == 1 and after == -1)
        for mode, ctrl in (('fixture',controls),('benchmark',controls),('scientific',[{'pass':False}]*2)):
            result = inference.analyze(cases, ctrl, mode)
            inference.audit(cases, ctrl, result, mode)
            self.assertIsNone(result['reversal_replicated'])

    def test_real_selection_bytes_and_independent_intervention(self):
        cfg, source, inter = self.fixture()
        data.equal(inter, audit_model.intervene(source))
        w = model.base.decode(inter['packets'])
        original = model.base.decode(source['outgoing'])
        e = inter['eligible']
        self.assertTrue(e.any())
        self.assertEqual(inter['packets'][:4].tobytes(), source['outgoing'][:4].tobytes())
        self.assertFalse(w[4:8][e].any())
        self.assertFalse(np.signbit(w[4:8][e]).any())
        self.assertEqual(w[4:8][~e].tobytes(), original[:4][~e].tobytes())
        self.assertEqual(inter['packets'][8].tobytes(), source['outgoing'][4].tobytes())

    def test_empty_full_selection_and_signed_zero(self):
        shape = (5, 4, 1, 2, 16, 16)
        before = np.full(shape, -0.)
        after = np.ones(shape)
        after[..., 0, 0, 0] = -np.nextafter(0., 1.)
        for select in (False, True):
            source = dict(incoming=model.base.encode(before), outgoing=model.base.encode(after),
                          fallback=np.full(shape, select, bool))
            inter = model.intervene(source)
            data.equal(inter, audit_model.intervene(source))
            w = model.base.decode(inter['packets'])
            if select:
                self.assertFalse(w[4:8].any())
                self.assertFalse(np.signbit(w[4:8]).any())
            else:
                self.assertEqual(inter['packets'][:4].tobytes(), inter['packets'][4:8].tobytes())

    def test_one_rewrite_replay_no_repeated_pruning_and_legacy_projection(self):
        cfg, source, inter = self.fixture()
        original = inter['packets'].tobytes()
        raw = model.rebuild(inter['packets'], 900041, 1, cfg['config'], cfg['cycle'])
        data.equal(raw, audit_model.rebuild(inter['packets'], 900041, 1, cfg['config'], cfg['cycle']))
        self.assertEqual(inter['packets'].tobytes(), original)
        output = model.base.decode(raw['outgoing'])
        self.assertTrue((output[4:8][inter['eligible']] != 0).any())
        packets = np.concatenate((inter['packets'], raw['outgoing']))
        fresh = model.develop(packets, 900041, cfg['reader'], cfg['reader'], 'terminal')
        data.equal(fresh, audit_model.develop(packets, 900041, cfg['reader'], cfg['reader'], 'terminal'))
        a = model.diagnostics(packets, inter, fresh, raw, cfg['reader'])
        b = audit_model.diagnostics(packets, inter, fresh, raw, cfg['reader'])
        for x, y in zip(a, b, strict=True): data.equal(x, y)
        legacy_projection_check(source, inter, packets, 900041, cfg, raw, fresh)

    def test_empty_policy_alias_through_writer_and_terminal(self):
        cfg, source, inter = self.fixture()
        source['fallback'][:] = False
        inter = model.intervene(source)
        raw = model.rebuild(inter['packets'], 900041, 1, cfg['config'], cfg['cycle'])
        self.assertEqual(raw['outgoing'][:4].tobytes(), raw['outgoing'][4:8].tobytes())
        packets = np.concatenate((inter['packets'], raw['outgoing']))
        fresh = model.develop(packets, 900041, cfg['reader'], cfg['reader'], 'terminal')
        for base in (0, 9):
            self.assertEqual(fresh['end'][base:base+4].tobytes(), fresh['end'][base+4:base+8].tobytes())
        # Identical packets at distinct horizons receive identical draws too.
        duplicate = np.concatenate((inter['packets'], inter['packets']))
        same = model.develop(duplicate, 900041, cfg['reader'], cfg['reader'], 'terminal')
        self.assertEqual(same['end'][:9].tobytes(), same['end'][9:].tobytes())

    def test_exact_fallback_and_small_cue_difference(self):
        state = np.full((1, 4, 1, 2, 16, 16), .1)
        available = np.ones((4, 1, 2, 16, 16), bool)
        for skew in (0., 1e-5):
            state[..., 1, :, :] = .1+skew
            a = model.capture(state, available, 3.)
            b = audit_model.capture(state, available, 3.)
            for x, y in zip(a, b, strict=True): self.assertEqual(x.tobytes(), y.tobytes())
            self.assertEqual(bool(a[3].all()), skew == 0)
            self.assertEqual(a[0].tobytes(), a[1 if skew == 0 else 2].tobytes())

    def test_scoring_strict_boundary_signed_zero_and_partition(self):
        ports = np.zeros((18, 4, 1, 2, 2))
        for f, rule in enumerate((1., -1., 1., -1.)):
            for c, cue in enumerate((1., -1.)):
                ports[:, f, 0, c] = [rule*cue*.25, -rule*cue*.25]
        self.assertFalse(model.score(ports, .25)['both'].any())
        for values in (ports, ports*1.01, -ports*1.01, ports*0.):
            a, b = model.score(values, .25), audit_model.score(values, .25)
            data.equal(a, b)
            self.assertTrue((sum(a[k].astype(int) for k in ('both','correct_signs_below_threshold','zero_without_wrong_sign','any_wrong_sign')) == 1).all())

    def test_persistence_gate_requires_both_benefits(self):
        controls = [{'pass': True}]*2
        base = np.zeros((18, 4, 1), bool)
        for before, after, expected in (
                (True, True, 'PERSISTENCE_SUPPORTED'),
                (True, False, 'POST_REWRITE_BENEFIT_UNRESOLVED'),
                (False, True, 'POST_REWRITE_GAIN_WITHOUT_IMMEDIATE_CONFIRMATION'),
                (False, False, 'PERSISTENCE_NOT_ESTABLISHED')):
            both = base.copy()
            both[6:8] = before
            both[15:17] = after
            cases = [dict(both=both), dict(both=both)]
            summary = inference.analyze(cases, controls, 'scientific')
            inference.audit(cases, controls, summary, 'scientific')
            self.assertEqual(summary['status'], expected)
            self.assertEqual(summary['persistence_supported'], before and after)
        both = base.copy(); both[6:8] = True; both[11:13] = True
        cases = [dict(both=both)]*2
        s = inference.analyze(cases, controls, 'scientific')
        inference.audit(cases, controls, s, 'scientific')
        self.assertEqual(s['status'], 'BENEFIT_REVERSED')
        for mode, ctrl in (('fixture', controls), ('benchmark', controls), ('scientific', [{'pass':False}]*2)):
            s = inference.analyze(cases, ctrl, mode)
            inference.audit(cases, ctrl, s, mode)
            self.assertIsNone(s['persistence_supported'])
            self.assertTrue(all(x is None for x in s['primary_effects'].values()))
        self.assertEqual(inference.classification([0., .1]), 'UNRESOLVED')
        self.assertEqual(inference.classification([-.1, 0.]), 'UNRESOLVED')


if __name__ == '__main__':
    unittest.main()
