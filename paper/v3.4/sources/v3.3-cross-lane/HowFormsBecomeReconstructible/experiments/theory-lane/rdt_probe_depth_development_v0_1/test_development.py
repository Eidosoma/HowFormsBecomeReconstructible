"""Scientific semantics, grouping, target aggregation and leakage regressions."""
from pc_common import *
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import time
from pc_fit import Fits,future_brier
from pc_score import estimates
from pc_measure import decisions


class DevelopmentContracts(unittest.TestCase):
    def test_memory_gate_uses_current_image_but_keeps_the_same_ceiling(self):
        from pc_measure import check
        with patch('pc_measure.resource.getrusage',return_value=SimpleNamespace(ru_maxrss=2_000_000)), \
             patch('pc_measure.shutil.disk_usage',return_value=SimpleNamespace(free=3_000_000_000)), \
             patch('pc_measure.current_memory_bytes',return_value={'VmRSS':40_000_000,'VmHWM':60_000_000}):
            check(ROOT,time.time()+10)
        with patch('pc_measure.current_memory_bytes',return_value={'VmRSS':40_000_000,'VmHWM':2_000_000_000}):
            with self.assertRaisesRegex(ValueError,'RSS ceiling'):check(ROOT,time.time()+10)

    def test_all_related_cases_share_outer_fold(self):
        cases=read(ROOT/'prepared/CASES.json')
        self.assertEqual(len(cases),638)
        self.assertEqual({c['block'] for c in cases},set(range(80)))
        for b in range(80):
            selected=[c for c in cases if c['block']==b]
            self.assertEqual({c['fold'] for c in selected},{b%8})
            self.assertEqual({c['regime'] for c in selected},set(REGIMES))
            self.assertEqual({c['current_pass'] for c in selected},{0,1})

    def test_individual_brier_is_not_error_against_average_target(self):
        y=np.array([0.,1.,1.,1.]);p=.2
        self.assertAlmostEqual(float(future_brier(p,y.mean())),float(np.mean((p-y)**2)))
        self.assertGreater(abs(float(future_brier(p,y.mean()))-(p-y.mean())**2),.1)

    def test_fractional_binomial_fit_matches_repeated_binary_targets(self):
        _,m=cheap();rng=np.random.default_rng(22)
        x=rng.normal(size=(24,3));y=rng.binomial(1,.6,size=(24,4));w=np.linspace(1,2,24)
        a=m.logistic(x,y.mean(axis=1),w,.1)
        b=m.logistic(np.repeat(x,4,axis=0),y.ravel(),np.repeat(w/4,4),.1)
        np.testing.assert_allclose(a['coefficients'],b['coefficients'],rtol=0,atol=1e-7)
        np.testing.assert_allclose(a['mean'],b['mean'],rtol=0,atol=1e-12)

    def test_outer_target_changes_cannot_change_selected_model_or_prediction(self):
        rng=np.random.default_rng(107);x=rng.normal(size=(32,2));groups=np.repeat(np.arange(8),4)
        y=rng.integers(1,4,size=32)/4;weights=np.full(32,1/32)
        schema={'all_columns':['a','b'],'families':{'candidate':['a','b']}}
        outputs=[]
        for held_y in (y, np.where(groups==0,1-y,y)):
            fit=Fits(dict(X=x,y=held_y,blocks=groups,weights=weights),schema)
            chosen,_=fit.select('candidate',list(range(1,8)))
            p=fit.inner.probabilities('candidate',list(range(1,8)),chosen['ridge'],chosen['calibration'])[groups==0]
            outputs.append((chosen,p))
            self.assertTrue(all(0 not in r['train_blocks'] for r in fit.inner.receipts))
            self.assertTrue(all(0 not in r['train_blocks'] for r in fit.inner.calibration_receipts))
        self.assertEqual(outputs[0][0],outputs[1][0])
        np.testing.assert_array_equal(outputs[0][1],outputs[1][1])

    def test_descendant_duplication_does_not_create_more_source_units(self):
        rng=np.random.default_rng(23);values=rng.random(80);weights=np.full(80,1/80);blocks=np.arange(80)
        counts=rng.multinomial(80,np.full(80,1/80),size=30)
        a=estimates(values,weights,blocks,counts)
        b=estimates(np.repeat(values,4),np.repeat(weights/4,4),np.repeat(blocks,4),counts)
        np.testing.assert_allclose(a[0],b[0],rtol=0,atol=1e-14)
        np.testing.assert_allclose(a[1],b[1],rtol=0,atol=1e-14)

    def test_case_weights_preserve_both_regime_populations_and_orientation_expansion(self):
        cases=read(ROOT/'prepared/CASES.json')
        for regime in REGIMES:
            group=[c for c in cases if c['regime']==regime]
            for profile in PROFILES:self.assertAlmostEqual(sum(c['weights'][profile] for c in group),1.)
            fail=sum(c['weights']['population'] for c in group if not c['current_pass'])
            self.assertAlmostEqual(fail,868/5120)

    def test_only_declared_cheap_features_and_probe_enter_new_models(self):
        s=read(ROOT/'prepared/SCHEMA.json')
        for family in ('direct8','depth0','depth1','depth2'):
            self.assertEqual(s['families'][family][:-1],s['cheap_columns'])
            self.assertEqual(len(s['families'][family]),71)
        self.assertTrue(all(n not in s['all_columns'] for n in ('block','fold','key','target','y','terminal_success','legacy_probability')))

    def test_strict_endpoint_and_supplied_orientation(self):
        sign=np.array([[1.,-1.],[-1.,1.]])
        a=np.broadcast_to(.25*sign,(1,32,1,2,2)).copy()
        self.assertEqual(decisions(a,1).item(),0)
        self.assertEqual(decisions(a+.01*sign,1).item(),1)
        self.assertEqual(decisions(a+.01*sign,-1).item(),0)


if __name__=='__main__':unittest.main()
