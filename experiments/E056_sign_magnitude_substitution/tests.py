"""Boundary, factorial, graph and independent-replay checks on synthetic records."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import cap_cpus,rng
from E056_sign_magnitude_substitution import model,audit_model,inference,audit
from E056_sign_magnitude_substitution.plan import settings
import numpy as np


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cap_cpus(1);cls.cfg=settings('fixture');cls.cfg['recipients']=1
        g=rng('E056','synthetic')
        w=g.uniform(-1,1,(3,2,2,4,1,2,16,16)); support=g.random((3,2,1,4,1,2,16,16))>.1
        w*=support;cls.source=dict(packets=model.base.encode(w))
        cls.inter=model.intervene(cls.source['packets'])
        cls.fresh=model.assay(cls.inter['packets'],900099,cls.cfg)
        cls.cases,cls.controls=model.diagnostics(cls.source,cls.inter,cls.fresh,cls.cfg)

    def test_independent_pipeline(self):
        inter=audit_model.intervene(self.source['packets']);audit.compare(inter,self.inter)
        fresh=audit_model.assay(inter['packets'],900099,self.cfg);audit.compare(fresh,self.fresh)
        cases,controls=audit_model.diagnostics(self.source,inter,fresh,self.cfg)
        audit.compare(cases,self.cases);self.assertEqual(controls,self.controls);self.assertTrue(controls['pass'])

    def test_known_substitution_values(self):
        w=np.ones((3,2,2,4,1,2,16,16));w[:,:,0]*=-.25;w[:,:,1]*=.75
        out=model.base.decode(model.intervene(model.base.encode(w))['packets'])
        for a,value in enumerate((-.25,.75,-.75,.25,0.)):self.assertTrue((out[:,:,a]==value).all())

    def test_support_mismatch_rejected(self):
        w=model.base.decode(self.source['packets']).copy();w[0,0,0,0,0,0,0,0]=0.;w[0,0,1,0,0,0,0,0]=1.
        for f in (model.intervene,audit_model.intervene):
            with self.assertRaises(AssertionError):f(model.base.encode(w))

    def test_nonfinite_rejected(self):
        w=model.base.decode(self.source['packets']).copy();w.flat[0]=np.nan
        for f in (model.intervene,audit_model.intervene):
            with self.assertRaises(AssertionError):f(model.base.encode(w))

    def test_input_immutable(self):
        p=self.source['packets'].copy();model.intervene(p)
        np.testing.assert_array_equal(p,self.source['packets'])

    def test_signed_zeros_do_not_create_edges(self):
        w=np.zeros((3,2,2,4,1,2,16,16));w[:,:,1]=-0.
        source=dict(packets=model.base.encode(w));inter=model.intervene(source['packets'])
        self.assertFalse(model.base.decode(inter['packets']).any())
        np.testing.assert_array_equal(inter['packets'][:,:,1],source['packets'][:,:,1])
        audit.compare(inter,audit_model.intervene(source['packets']))

    def test_identical_sources_have_identical_trajectories(self):
        w=model.base.decode(self.source['packets']).copy();w[:,:,1]=w[:,:,0]
        inter=model.intervene(model.base.encode(w));fresh=model.assay(inter['packets'],900099,self.cfg)
        end=fresh['end'].reshape(3,2,5,4,1,2,3,16,16)
        trace=fresh['late_ports'].reshape(self.cfg['observe_steps'],3,2,5,4,1,2,3,2)
        for a in range(1,4):
            np.testing.assert_array_equal(end[:,:,0],end[:,:,a]);np.testing.assert_array_equal(trace[:,:,:,0],trace[:,:,:,a])

    def test_sign_substitution_preserves_denominators(self):
        self.assertTrue(self.controls['sign_swap_denominators_fixed'])
        d=self.fresh['denominator'].reshape(3,2,5,4,1,3,16,16)
        np.testing.assert_array_equal(d[:,:,0],d[:,:,3]);np.testing.assert_array_equal(d[:,:,1],d[:,:,2])

    def test_uniform_strength_scaling_preserves_normalized_drive(self):
        w=model.base.decode(self.source['packets']).copy();w[:,:,1]=w[:,:,0]*.5
        out=model.intervene(model.base.encode(w));k=out['coupling']
        np.testing.assert_array_equal(k[:,:,0],k[:,:,1])
        self.assertFalse(np.array_equal(out['denominator'][:,:,0],out['denominator'][:,:,1]))

    def test_coordinated_cell_signs_have_balanced_cycles(self):
        signs=np.ones((16,16));signs[4:8,5:9]=-1
        w=np.stack((signs*np.roll(signs,-1,1),signs*np.roll(signs,-1,0)))
        np.testing.assert_array_equal(model.anchored(w),signs)
        np.testing.assert_array_equal(model.anchored(w),audit_model.anchored(w))
        self.assertEqual(model.graph_batch(w)[3],0)

    def test_disconnected_nodes_have_no_input_alignment(self):
        w=np.ones((2,16,16));port=model.P[0].ravel()
        w.ravel()[port[model.U]|port[model.V]]=0.
        a=model.anchored(w);self.assertTrue((a[~model.P[0]]==0).all())
        np.testing.assert_array_equal(a,audit_model.anchored(w))

    def test_inconsistent_sign_loop_is_detected(self):
        w=np.ones((2,16,16));w[0,0,0]=-1
        self.assertGreater(model.graph_batch(w)[3],0)
        np.testing.assert_array_equal(model.graph_batch(w),audit_model.graph_batch(w))
        np.testing.assert_array_equal(model.anchored(w),audit_model.anchored(w))

    def test_reader_injuries_protect_ports_and_are_rule_paired(self):
        mask=self.fresh['masks'];np.testing.assert_array_equal(mask[::2],mask[1::2])
        np.testing.assert_array_equal(mask.sum(axis=(-2,-1)),np.broadcast_to([0,24,9],(4,1,3)))
        self.assertFalse(mask[...,model.P.any(axis=0)].any())

    def test_packet_corruption_rejected(self):
        changed={k:v.copy() for k,v in self.inter.items()};changed['packets'].flat[0]^=1
        with self.assertRaises(AssertionError):audit.compare(self.inter,changed)

    def test_trajectory_hash_corruption_rejected(self):
        changed={k:v.copy() for k,v in self.fresh.items()};changed['state_hashes'].flat[0]^=1
        with self.assertRaises(AssertionError):audit.compare(self.fresh,changed)

    def test_factorial_contrasts_and_independent_block_inference(self):
        cases=[]
        for counts in ((4,1,2,3),(3,2,3,3)):
            c={k:v.copy() for k,v in self.cases.items()}
            for a,n in enumerate(counts):
                c['fresh_both'][1,0,a,1]=False;c['fresh_both'][1,0,a,1,:n]=True
            cases.append(c)
        s=inference.analyze(cases,[self.controls]*2,'scientific')
        expected=(.25,.375,.125,.25,-.125)
        for name,value in zip(inference.PRIMARY,expected):
            stat=s['statistics'][inference.primary_key(name)]
            self.assertEqual(stat['mean'],value);self.assertEqual(stat['confidence'],.99)
        self.assertEqual(audit.check_summary(s,cases,[self.controls]*2,'scientific'),1506)

    def test_technical_runs_cannot_classify(self):
        s=inference.analyze([self.cases],[self.controls],'fixture')
        self.assertEqual(s['status'],'TECHNICAL_ONLY');self.assertTrue(all(x is None for x in s['primary_effects'].values()))

    def test_control_failure_suppresses_classification(self):
        failed=dict(self.controls);failed['pass']=False
        s=inference.analyze([self.cases],[failed],'scientific')
        self.assertEqual(s['status'],'NUMERICAL_CONTROL_FAILURE');self.assertTrue(all(x is None for x in s['primary_effects'].values()))

    def test_zero_bound_is_unresolved(self):
        self.assertEqual(inference.classification([0.,.2],True),'UNRESOLVED')
        self.assertEqual(inference.classification([-.2,0.],True),'UNRESOLVED')
        self.assertEqual(inference.classification([.001,.2],True),'POSITIVE_EFFECT')
        self.assertIsNone(inference.classification([.001,.2],False))

    def test_summary_corruption_rejected(self):
        s=inference.analyze([self.cases],[self.controls],'scientific');bad=copy.deepcopy(s)
        bad['statistics'][inference.primary_key('interaction')]['mean']+=.1
        with self.assertRaises(AssertionError):audit.check_summary(bad,[self.cases],[self.controls],'scientific')


if __name__=='__main__':unittest.main()
