import unittest
import math
import numpy as np
import analyze as a


def synthetic(counts):
    rows=[]
    for (b,c,s),n in counts.items():
        for j in range(n):
            rows.append(dict(block=b,current_pass=c,rule=s,history='fixture',founder=0,recipient=j,
                             key=[b,c,s,j],selection_hash=f'{j:08d}'))
    chosen=[]
    for b in sorted({r['block'] for r in rows}):chosen+=a.select([r for r in rows if r['block']==b])
    return rows,chosen


class AnalysisSemantics(unittest.TestCase):
    def test_orientation_expansion_changes_weights_beyond_class_prevalence(self):
        full,selected=synthetic({(0,0,-1):9,(0,0,1):1,(0,1,-1):2,(0,1,1):8})
        w,info,cells=a.weights(full,selected)
        np.testing.assert_allclose(w['balanced'],[.25]*4)
        np.testing.assert_allclose(w['population'],[.45,.05,.1,.4])
        np.testing.assert_allclose(w['population_fail'],[.9,.1,0,0])
        self.assertEqual(sum(r['expansion'] for r in info),20)

    def test_singleton_class_and_single_orientation_keep_support(self):
        full,selected=synthetic({(0,0,-1):1,(0,1,1):7})
        w,info,cells=a.weights(full,selected)
        self.assertEqual(len(selected),3)
        np.testing.assert_allclose(w['balanced'],[.5,.25,.25])
        np.testing.assert_allclose(w['population'],[1/8,3.5/8,3.5/8])
        self.assertTrue(all(c['supported'] for c in cells))

    def test_population_weighting_refuses_an_unrepresented_cell(self):
        full,selected=synthetic({(0,0,-1):3,(0,0,1):1,(0,1,1):7})
        with self.assertRaises(AssertionError):a.weights(full,[r for r in selected if r['rule']!= -1])

    def test_resampling_ratio_renormalizes_unequal_block_weights(self):
        blocks=np.array([0,1]);w=np.array([.1,.9]);v=np.array([0.,1.])
        draws=np.array([[2,0],[1,1],[0,2]])
        mean,boot,_,_=a.estimate(v,w,blocks,draws)
        self.assertAlmostEqual(mean[0],.9)
        np.testing.assert_allclose(boot[:,0],[0.,.9,1.])

    def test_duplicate_futures_do_not_create_independent_blocks(self):
        blocks=np.array([0,0,1,1]);w=np.array([.25]*4);v=np.array([.2,.4,.6,.8])
        draws=np.array([[2,0],[1,1],[0,2]])
        m,b,_,_=a.estimate(v,w,blocks,draws)
        m2,b2,_,_=a.estimate(np.repeat(v,4),np.repeat(w/4,4),np.repeat(blocks,4),draws)
        np.testing.assert_allclose(m,m2);np.testing.assert_allclose(b,b2)

    def test_individual_brier_is_not_loss_of_mean_outcome(self):
        p=.5;outcomes=np.array([0.,1.,0.,1.])
        self.assertEqual(np.mean((p-outcomes)**2),.25)
        self.assertEqual((p-outcomes.mean())**2,0.)

    def test_original_block_t_preserves_sign_and_degrees_of_freedom(self):
        v=np.array([-.1,.1,.2,.4])
        mean,lo,hi=a.original_t(v)
        self.assertAlmostEqual(mean,.15)
        self.assertAlmostEqual(hi-mean,mean-lo)
        self.assertAlmostEqual(hi-mean,3.182446305284263*np.std(v,ddof=1)/math.sqrt(4),places=9)

    def test_empty_conditional_bins_remain_undefined(self):
        m,b,_,_=a.estimate(np.array([1.,0.]),np.zeros(2),np.array([0,1]),np.array([[2,0],[0,2]]))
        self.assertTrue(np.isnan(m).all() and np.isnan(b).all())
        self.assertEqual(a.bounds(b[:,0]),[None,None])


if __name__=='__main__':unittest.main()
