"""Synthetic tests of grouping, source axes, histories and missing observations."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from E044_transition_diagnosis import metrics as m,audit,run
import numpy as np


def fixture():
    R=2
    ports=np.zeros((12,4,R,2,3,7,2))
    cases=dict(ports=ports,correct=np.zeros(ports.shape[:-1],bool),margin=np.zeros(ports.shape[:-1]))
    diagnosis=dict(packet=np.zeros((33,11,4,R,17)),body=np.zeros((32,9,4,R,10)),
        repair=np.zeros((32,11,4,R,17)),graph=np.zeros((7,4,4,R,3,4)),terminal=np.zeros((7,11,4,R,3,10)))
    diagnosis['terminal'][...,3]=1;diagnosis['body'][...,3]=1
    return diagnosis,cases


def assign(cases,p,f,r,d,v):
    v=np.asarray(v,float);cases['ports'][p,f,r,:,d,0]=v
    sign=(1. if f in (0,2) else -1.)*np.array([[1.,-1.],[-1.,1.]])
    signed=v*sign;cases['correct'][p,f,r,:,d,0]=(signed>.25).all(axis=-1)
    cases['margin'][p,f,r,:,d,0]=signed.min(axis=-1)


class DiagnosticTests(unittest.TestCase):
    def test_output_classes_and_strict_threshold(self):
        v=np.array([[[1.,-1.],[-1.,1.]],[[-1.,1.],[1.,-1.]],[[1.,-1.],[1.,1.]],[[.25,-.25],[-.25,.25]]])
        a=m.prior.output_features(v,np.ones(4));b=audit.prior.output(v,np.ones(4))
        np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(a[:,:4],np.eye(4))

    def test_all_four_outcome_groups(self):
        np.testing.assert_array_equal(m.classify(np.array([0,0,1,1]),np.array([0,1,0,1])),[0,1,2,3])

    def test_reader_horizon_founder_injury_and_arm_axes(self):
        _,cases=fixture();assign(cases,11,2,1,1,[[1.,-1.],[-1.,1.]])
        assign(cases,3,1,0,2,[[-1.,1.],[1.,-1.]])
        cases['ports'][10]=1.;cases['ports'][...,1,:]=2.
        out=m.outputs(cases)
        self.assertEqual(out.shape,(2,3,4,2,3,10))
        self.assertEqual(out[...,0].sum(),2)
        self.assertEqual(out[1,2,2,1,1,0],1);self.assertEqual(out[0,1,1,0,2,0],1)
        broken={k:v.copy() for k,v in cases.items()};broken['correct'][11,2,1,0,1,0]=False
        with self.assertRaises(AssertionError):m.outputs(broken)

    def test_history_window_and_prior_vs_current_failure(self):
        packet=np.zeros((33,4,1,17));body=np.zeros((32,4,1,10));body[...,0]=1
        body[2,...,0]=0;body[23,...,0]=0
        packet[:,...,11]=np.arange(33)[:,None,None]
        x=m.history(packet,body,24)
        self.assertAlmostEqual(x[0,0,0],1/23)
        np.testing.assert_array_equal(x[0,0,1:6],[1,0,1,1,0])
        self.assertEqual(x[0,0,8],164)
        y=m.history(packet,body,32)
        self.assertEqual(y[0,0,5],1);self.assertEqual(y[0,0,3],0)

    def test_source_join_class_transitions_and_missing_followup(self):
        diag,cases=fixture()
        assign(cases,11,0,0,1,[[1.,-1.],[-1.,1.]])
        diag['body'][24,3,...,0]=1;diag['body'][24,3,...,3]=0
        x=m.join(diag,cases);y=audit.reconstruct(diag,cases)
        np.testing.assert_allclose(x['features'],y['features'],rtol=1e-14,atol=1e-12)
        np.testing.assert_array_equal(x['groups'],y['groups'])
        self.assertEqual(x['groups'][1,0,0,1],1)
        self.assertEqual(x['features'][1,0,0,1,m.FEATURES.index('class_change.other_failure_to_both_correct')],1)
        self.assertTrue((x['features'][0,...,m.FEATURES.index('witness.next_body_success')]==1).all())
        self.assertFalse(x['features'][1,...,m.FEATURES.index('witness.next_body_observed')].any())

    def test_conditional_ratios_keep_empty_blocks(self):
        draws=np.array([[0,0],[0,1],[1,1]])
        a=run.statistics([0,6],[0,2],draws)
        self.assertEqual(a['mean'],3);self.assertEqual(a['valid_bootstrap_draws'],2);self.assertEqual(a['ci95'],[3.,3.])
        z=run.statistics([0,0],[0,0],draws);self.assertIsNone(z['mean']);self.assertIsNone(z['ci95'])

    def test_last_body_missing_is_null_in_summary(self):
        raw=m.join(*fixture());data={k:v[None] for k,v in raw.items()}
        series,defs=run.summarize(data,[900041])
        self.assertIsNone(series['h32.scattered.persistent_failure.witness.next_body_success']['mean'])
        self.assertEqual(series['h24.scattered.persistent_failure.witness.next_body_success']['mean'],0)
        self.assertEqual(sum(series['h32.scattered.persistent_failure.cohort_fraction']['block_numerators']),8)
        self.assertEqual(defs,audit.definitions());self.assertEqual(len(series),3480)

    def test_source_row_and_strong_accounting_mismatch_rejected(self):
        diag,cases=fixture();diag['terminal'][6,3,0,0,1,0]=1
        with self.assertRaises(AssertionError):m.join(diag,cases)
        diag,cases=fixture();diag['packet'][32,3,0,0,1]=1
        with self.assertRaises(AssertionError):m.join(diag,cases)


if __name__=='__main__':unittest.main(verbosity=2)
