"""Executable checks for uncertainty, measurement and selection calculations."""
import itertools
import math
from pathlib import Path
import sys
import unittest

import numpy as np
from scipy.stats import binomtest

import core

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'source/theory'))
import two_mode as tm


def direct_tail(p,n,k,upper):
    indices=range(k,n+1) if upper else range(k+1)
    return math.fsum(math.comb(n,j)*p**j*(1-p)**(n-j) for j in indices)


def invert_tail(n,k,alpha,upper):
    left,right=0.,1.
    for _ in range(65):
        middle=(left+right)/2; value=direct_tail(middle,n,k,upper)
        if (value<alpha)==upper:left=middle
        else:right=middle
    return (left+right)/2


class Checks(unittest.TestCase):
    def test_exact_intervals_direct_inversion(self):
        for n in (1,2,16,64):
            for alpha in (.05,.05/48):
                interval=core.binomial_interval(np.arange(n+1),n,alpha)
                for k in range(n+1):
                    expected=[0. if k==0 else invert_tail(n,k,alpha/2,True),
                              1. if k==n else invert_tail(n,k,alpha/2,False)]
                    np.testing.assert_allclose(interval[k],expected,atol=2e-14,rtol=2e-12)

    def test_scipy_interval_reference(self):
        for n in (16,32,64,128,256,512,1024,2048):
            for k in sorted({0,1,2,n//4,n//2,n-2,n-1,n}):
                for method in ('exact','wilson'):
                    expected=binomtest(k,n).proportion_ci(method=method)
                    np.testing.assert_allclose(core.binomial_interval(k,n,method=method),
                        [expected.low,expected.high],atol=2e-12,rtol=2e-10)

    def test_invalid_counts(self):
        for k,n in ((0,0),(1.5,3),(-1,4),(5,4),(np.nan,4)):
            with self.assertRaises(ValueError):core.binomial_interval(k,n)
        with self.assertRaises(ValueError):core.binomial_interval(1,2,alpha=0)
        with self.assertRaises(ValueError):core.pair_components([1],[1])

    def test_pair_variance_unbiased(self):
        outcomes=np.array(list(itertools.product((0,1),repeat=2)))
        for values,weights in (([.75],[1.]),([0.,1.],[.25,.75]),([.2,.8],[.3,.7])):
            q=np.array(values); weight=np.array(weights)
            probabilities=np.array([np.sum(weight*q**pair.sum()*(1-q)**(2-pair.sum())) for pair in outcomes])
            mean=float(weight@q); second=float(weight@(q*q))
            for n in (2,3):
                expectations=np.zeros(3)
                for indices in itertools.product(range(4),repeat=n):
                    pairs=outcomes[list(indices)]; chance=float(np.prod(probabilities[list(indices)]))
                    item=core.pair_components(pairs[:,0],pairs[:,1])
                    expectations+=chance*np.array([item['within_packet_estimate'],item['between_packet_estimate'],item['total_estimate']])
                np.testing.assert_allclose(expectations,[mean-second,second-mean*mean,mean*(1-mean)],atol=1e-14)

    def test_negative_components_are_retained(self):
        result=core.pair_components([1,0],[0,1])
        self.assertEqual(result['between_packet_estimate'],-.25)
        self.assertEqual(result['within_packet_estimate'],.5)
        self.assertTrue(result['negative_between_estimate'])

    def test_models_are_inside_candidate(self):
        for q in (0.,.005,.1,.5):
            for horizon in (0,1,2,8,32):
                absorbing=tm.distributions([0.,1-q,1.,1.,1.],[horizon])[0]
                flipping=tm.distributions([1.,0.,1-2*q,1.,1.],[horizon])[0]
                np.testing.assert_allclose(absorbing,[(1-q)**horizon,0.,1-(1-q)**horizon],atol=1e-14)
                truth=(1+(1-2*q)**horizon)/2
                np.testing.assert_allclose(flipping,[truth,1-truth,0.],atol=1e-14)

    def test_hidden_path_enumeration(self):
        for theta in ([0.,.995,1.,1.,1.],[1.,0.,.98,1.,1.],[.75,0.,1.,1.,1.]):
            initial,transition=tm.hidden_model(theta)
            expected=np.zeros(27)
            for states in itertools.product(range(4),repeat=3):
                chance=initial[states[0]]*transition[states[0],states[1]]*transition[states[1],states[2]]
                outputs=[int(np.argmax(tm.EMISSION[state])) for state in states]
                expected[9*outputs[0]+3*outputs[1]+outputs[2]]+=chance
            np.testing.assert_allclose(tm.pattern_probabilities(theta),expected,atol=1e-15)

    def test_clone_observation_counterexample(self):
        for p in (.1,.5,.75,.9):
            models=core.observation_models(p)
            singles=[core.observation_patterns(m,1)[1] for m in models]
            np.testing.assert_allclose(singles[0],singles[1],atol=1e-15)
            np.testing.assert_allclose(singles[0],tm.pattern_probabilities([p,0.,1.,1.,1.]),atol=1e-15)
            for i,model in enumerate(models):
                patterns,mass=core.observation_patterns(model,2)
                self.assertAlmostEqual(float(mass[patterns[:,2]!=patterns[:,3]].sum()),2*p*(1-p) if i==0 else 0.)

    def test_zero_loss_limit_and_required_budget(self):
        table=core.interval_table('absorbing_loss',16,32,.05,'exact')
        np.testing.assert_allclose(table['forecast'][-1],[.025,1.],atol=1e-14)
        for target in (.8,.9,.95):
            result=core.zero_loss_requirement(target)
            self.assertGreater(result['lower_bound'],target)
            self.assertLessEqual(.025**(16/(result['paths']-1)),target)

    def test_empty_sets_not_repaired(self):
        table=core.interval_table('identity_flip',16,32,.05,'exact')
        self.assertFalse(table['valid'][-1])
        self.assertTrue(np.isnan(table['forecast'][-1]).all())
        self.assertGreater(table['parameter'][-1,0],table['parameter'][-1,1])

    def test_conditional_interval_inversion(self):
        n=8; selected=(0,1,2,6,7,8)
        adjusted=core.conditional_parameter_intervals(n,selected,.05)
        for k in selected:
            for endpoint,p in enumerate(adjusted[k]):
                if p in (0.,1.):continue
                weights=[math.comb(n,j)*p**j*(1-p)**(n-j) for j in selected]
                mask=[j>=k if endpoint==0 else j<=k for j in selected]
                conditional=math.fsum(w for w,take in zip(weights,mask) if take)/math.fsum(weights)
                self.assertAlmostEqual(conditional,.025,places=11)

    def test_conditional_coverage_and_no_second_gate(self):
        for model in ('absorbing_loss','identity_flip'):
            ordinary=core.interval_table(model,16,32,.05,'exact')
            adjusted=core.selection_table(model,16,32,ordinary)
            for q in (0.,.0001,.005,.05,.25,.5):
                result=core.selected_scenario(model,16,32,q,adjusted)
                coverage=result['conditional_coverage_given_gate']
                if coverage is not None:self.assertGreaterEqual(coverage,.95-1e-10)
                self.assertFalse(result['second_width_filter_applied'])


if __name__=='__main__':unittest.main(verbosity=2)
