"""Excluded reader projections and inference edge cases before any scientific draw."""
import csv
import json
from pathlib import Path
import sys
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import dump,sha,utc
from E083_reader_repeatability import data,model,audit_model,inference
from E083_reader_repeatability.plan import HERE,settings


class Checks(unittest.TestCase):
    def test_stratified_alignment(self):
        a=np.array([[[1.,0,-1,0],[1,1,1,1]],[[0,0,0,0],[-1,0,1,0]]])
        np.testing.assert_array_equal(inference.alignment(a,a),[.25,.25])
        np.testing.assert_array_equal(inference.alignment(a,-a),[-.25,-.25])
        np.testing.assert_array_equal(inference.alignment(a,np.ones_like(a)),[0,0])
        np.testing.assert_array_equal(inference.alignment(np.ones_like(a),a),[0,0])
        # Relative alignment can be positive although every fresh effect is positive.
        a=np.array([[[-1.,0.,1.,0.]]]);b=np.array([[[.25,.5,1.,.5]]])
        self.assertGreater(inference.alignment(a,b)[0],0);self.assertGreater(b.min(),0)

    def test_conditional_empty_bootstrap(self):
        idx=np.array([[0,0],[1,1],[0,1]])
        r=inference.conditional([1,0],[1,0],idx)
        self.assertEqual(r['mean'],1);self.assertIsNone(r['interval']);self.assertEqual(r['undefined_bootstrap_draws'],1)
        r=inference.conditional([0,0],[0,0],idx)
        self.assertIsNone(r['mean']);self.assertIsNone(r['interval']);self.assertEqual(r['undefined_bootstrap_draws'],3)
        r=inference.conditional([1,-1],[1,1],idx)
        self.assertEqual(r['mean'],0);self.assertIsNotNone(r['interval'])

    def test_transitions(self):
        of=np.array([[False,False,True,True]])
        ff=np.array([[False,True,False,True]])
        nf=np.array([[[False,False,True,True],[False,True,False,True]]])
        ng=np.array([[[True,True,False,True],[False,False,False,False]]])
        r=inference.transitions(of,ff,nf,ng)
        self.assertEqual(r['original_group_counts'],[1,1,1,1])
        self.assertEqual(r['recurrence_0_1_2_draws'],dict(gain=[0,1,0],harm=[0,1,0]))
        self.assertEqual(r['old_group_new_effect_tables']['mean_sign'],[[0,0,1],[0,1,0],[1,0,0],[1,0,0]])
        self.assertEqual(inference.label([0.,.1]),'UNRESOLVED')
        self.assertEqual(inference.label([-.1,0.]),'UNRESOLVED')

    def test_threshold_and_signed_transfer(self):
        p=np.zeros((1,4,1,2,2))
        for f in range(4):
            for q,cue in enumerate((1.,-1.)):
                x=(1. if f%2==0 else -1.)*cue*.25;p[0,f,0,q]=[x,-x]
        data.equal(model.score(p,.25),audit_model.score(p,.25));self.assertFalse(model.score(p,.25)['both'].any())
        p*=2;self.assertTrue(model.score(p,.25)['both'].all())
        np.testing.assert_array_equal(model.score(p,.25)['aligned_transfer'],.5*np.ones((1,4,1)))
        p*=-1;self.assertTrue(model.score(p,.25)['opposite_rule_success'].all())

    def test_source_and_reader_projections(self):
        from E081_fresh_strength_pattern import model as previous
        cfg=settings('fixture')
        for task,tag in ((900080,'E080'),(900081,'E081')):
            s=data.source('fixture',task);data.equal(s,data.source('fixture',task,independent=True))
            if tag=='E080':
                c=data.archive('fixture','E080',900041,'cases')
                r=data.archive('fixture','E080',900041,'records')
                self.assertEqual(s['packets'][18:26].tobytes(),r['packets'][8:16].tobytes())
                self.assertEqual(s['old_both'][18:26].tobytes(),c['both'][8:16].tobytes())
            phase='terminal_'+tag
            legacy=model.develop(s['packets'],900041,cfg,cfg,phase,stream_tag='E081')
            data.equal(legacy,previous.develop(s['packets'],900041,cfg,cfg,phase))
            fresh=model.develop(s['packets'],900041,cfg,cfg,phase,0)
            data.equal(fresh,audit_model.develop(s['packets'],900041,cfg,cfg,phase,0))
            for a,b in zip(model.diagnostics(s['packets'],s['eligible'],fresh,cfg),audit_model.diagnostics(s['packets'],s['eligible'],fresh,cfg)):data.equal(a,b)
            self.assertFalse(np.array_equal(fresh['birth'],model.develop(s['packets'],900041,cfg,cfg,phase,1)['birth']))
            altered={k:v.copy() for k,v in fresh.items()};altered['mean_ports'].flat[0]+=1
            with self.assertRaises(AssertionError):data.equal(fresh,altered)

    def test_synthetic_full_inference(self):
        sources=[];cases=[];tasks=[41000,41001,42000,42001]
        stream=np.random.default_rng(83)
        for _ in tasks:
            s=dict(old_both=stream.random((26,4,2))>.5)
            for k in ('minimum_margin','transfer','aligned_transfer'):s['old_'+k]=stream.normal(size=(26,4,2))
            sources.append(s);draw=[]
            for _ in range(2):
                d={k:stream.normal(size=(26,4,2)) for k in inference.METRICS};d['both']=stream.random((26,4,2))>.5;draw.append(d)
            cases.append(draw)
        controls=[dict(pass_=True,**{'pass':True}) for _ in tasks]
        summary=inference.analyze(tasks,sources,cases,controls,'fixture')
        self.assertGreater(inference.audit(tasks,sources,cases,controls,summary,'fixture'),100)
        self.assertIsNone(summary['alignment_at_both_cohorts']);self.assertTrue(all(v is None for v in summary['primary_effects'].values()))
        summary['cohorts']['E080']['primary_alignment']['mean']+=1
        # Primary point estimate must be audited as well as its block scores/CI.
        with self.assertRaises(AssertionError):inference.audit(tasks,sources,cases,controls,summary,'fixture')


if __name__=='__main__':
    start=time.monotonic();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    receipt=HERE/'analysis/development_tests_v1.json';receipt.parent.mkdir(parents=True,exist_ok=True)
    if not receipt.exists():dump(receipt,dict(status='PASS' if result.wasSuccessful() else 'FAIL',utc=utc(),seconds=time.monotonic()-start,tests=result.testsRun,tests_sha256=sha(Path(__file__)),scientific_outcomes_seen=False))
    sys.exit(0 if result.wasSuccessful() else 1)
