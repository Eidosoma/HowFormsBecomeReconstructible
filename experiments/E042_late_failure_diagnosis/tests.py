"""Bounded arithmetic and graph fixtures; no scientific cases."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from E042_late_failure_diagnosis import metrics as m, audit, run
import numpy as np


class DiagnosticTests(unittest.TestCase):
    def test_edge_accounting_and_underflow_safe_signs(self):
        old = np.zeros((1, 2, 16, 16)); new = old.copy(); original = old.copy()
        old.flat[:7] = [.8, -.8, .5, 1e-250, .9, .8, .7]
        new.flat[:7] = [.8, .8, .9, -1e-250, 0., .2, -.7]
        original.flat[:7] = [.8, -.8, .5, 1e-250, .9, .8, .7]
        live = np.ones_like(old, bool); live.flat[4] = False
        a = m.prior.packet_features(old, new, original, live)
        b = audit.prior.record(old, new, original, live)
        np.testing.assert_array_equal(a, b)
        expected = dict(nonzero=6, strong=4, weak_nonzero=2, changed_sign_nonzero=3,
            physical_strong_lost=1, available_strong_before=4, weak_promoted=1,
            strong_weakened=1, strong_sign_flips=2, new_strong_changed_sign=0,
            surviving_strong_changed_sign=2, exact_strong_copies=1)
        for k, v in expected.items(): self.assertEqual(a[0, m.PACKET_FIELDS.index(k)], v, k)

    def test_output_classes_are_distinct(self):
        ports = np.array([[[1., -1.], [-1., 1.]], [[-1., 1.], [1., -1.]],
                          [[1., -1.], [1., 1.]], [[.25, -.25], [-.25, .25]]])
        a = m.prior.output_features(ports, np.ones(4)); b = audit.prior.output(ports, np.ones(4))
        np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(a[:, :4], np.eye(4))
        np.testing.assert_array_equal(a[:, 4], [1., 0., .5, 0.])

    def test_strong_graph_threshold_and_disconnection(self):
        w = np.full((1, 2, 16, 16), .5)
        np.testing.assert_array_equal(m.prior.graph_features(w), [[0., 0.]])
        w.fill(.5000000001)
        np.testing.assert_array_equal(m.prior.graph_features(w), [[1., 1.]])
        w.fill(0.)
        w[0, 0, 7, 1:10] = 1.
        w[0, 1, 3:7, 10] = 1.
        w[0, 0, 3:5, 10] = 1.; w[0, 1, 3, 10:12] = 1.
        np.testing.assert_array_equal(m.prior.graph_features(w), [[.5, 0.]])
        np.testing.assert_array_equal(m.prior.graph_features(w), audit.prior.graph(w))
        w *= -1
        np.testing.assert_array_equal(m.prior.graph_features(w), audit.prior.graph(w))

    def test_first_failure_and_recovery(self):
        success = np.array([[1, 0], [0, 0], [1, 1], [0, 1]])
        x = m.prior.transitions(success)
        np.testing.assert_array_equal(x, audit.prior.history(success))
        np.testing.assert_array_equal(x[..., 0], [[0, 1], [1, 0], [0, 0], [0, 0]])
        np.testing.assert_array_equal(x[..., 3], [[0, 0], [0, 0], [1, 1], [0, 0]])
        self.assertEqual(x[3, 0, 2], 1.)

    def test_conditional_ratios_keep_empty_blocks(self):
        draws = np.array([[0, 0], [0, 1], [1, 1]])
        x = run.statistics([0, 6], [0, 2], draws)
        self.assertEqual(x['mean'], 3.)
        self.assertEqual(x['ci95'], [3., 3.])
        self.assertEqual(x['valid_bootstrap_draws'], 2)
        self.assertIsNone(run.statistics([0, 0], [0, 0], draws)['mean'])


    def test_returning_and_young_repairs(self):
        old=np.zeros((1,2,16,16));new=old.copy();live=np.ones_like(old,bool)
        previous=live.copy();young=np.zeros_like(live)
        old.flat[:6]=[0.,.01,.5,.7,-.01,0.]
        new.flat[:6]=[.001,.8,0.,.7,0.,.9]
        previous.flat[[0,5]]=False;young.flat[[1,4]]=True
        actual,returning=m.repair(old,new,live,previous,young)
        np.testing.assert_allclose(actual,audit.repair(old,new,live,previous,young),rtol=1e-14,atol=1e-12)
        expected={'returning':2,'returning_nonzero':2,'returning_strong':1,'available_weak_nonzero':3,
            'weak_promoted':1,'weak_erased':2,'zero_restored':2,'zero_promoted':1,'young_weak':2,
            'young_promoted':1,'young_erased':1}
        for key,value in expected.items():self.assertEqual(actual[0,m.REPAIR_FIELDS.index(key)],value,key)
        self.assertEqual(returning.sum(),2)

    def test_same_record_witness_body_mapping_and_unobserved_followup(self):
        terminal=np.zeros((7,11,4,1,3,10));body=np.zeros((32,9,4,1,10))
        terminal[1,9,:,:,0,0]=1;body[0:2,7,:,:,0]=1;body[31,7,:,:,0]=1
        result=m.joint(terminal,body)
        np.testing.assert_array_equal(result,audit.joint(terminal,body))
        for field in (1,5,7,9,10):self.assertTrue((result[0,7,...,field]==1).all())
        self.assertFalse(result[0,6,...,7].any())
        self.assertTrue((result[-1,7,...,7]==1).all())
        self.assertFalse(result[-1,...,9:11].any())
        stat=run.statistics([0],[0],np.zeros((3,1),int))
        self.assertIsNone(stat['mean']);self.assertIsNone(stat['ci95'])

    def test_graphs_use_actual_injury_and_include_tiny_edges(self):
        w=np.zeros((1,2,16,16));w[0,0,7,1:10]=.8;w[0,1,3:7,10]=.8
        w[0,0,3:5,10]=.8;w[0,1,3,10:12]=.8
        np.testing.assert_array_equal(m.graph(w),[[.5,0.,.5,0.]])
        mask=np.zeros((1,16,16),bool);mask[0,7,5]=True
        np.testing.assert_array_equal(m.prior.available(mask),audit.available(mask))
        np.testing.assert_array_equal(m.graph(w*m.prior.available(mask)),[[0.,0.,0.,0.]])
        w.fill(1e-300)
        np.testing.assert_array_equal(m.graph(w),[[1.,1.,0.,0.]])


if __name__ == '__main__': unittest.main(verbosity=2)
