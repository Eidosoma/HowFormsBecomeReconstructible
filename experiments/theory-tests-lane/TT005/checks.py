"""Meaningful excluded checks of sampling, measurement and native compatibility."""
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np
import support as s
import engine
import auditor


class Checks(unittest.TestCase):
    def setUp(self):
        self.cfg=s.config('fixture')
        self.contexts,self.weights=s.cases('fixture')
        self.context=self.contexts[0];self.weights=self.weights[0]

    def test_strict_threshold_and_opposite_rule(self):
        v=np.array([[[.25,-.25],[-.25,.25]]])
        self.assertEqual(int(s.score(v,1,.25)['category'][0]),2)
        v=np.sign(v)*np.nextafter(.25,1.)
        self.assertEqual(int(s.score(v,1,.25)['category'][0]),0)
        self.assertEqual(int(s.score(v,-1,.25)['category'][0]),1)
        with self.assertRaises(ValueError):s.score(np.full((1,2,2),np.nan),1,.25)

    def test_cue_pairing_and_independent_streams(self):
        mask,birth,noise=s.draws(self.context,self.cfg);frame=next(noise)
        np.testing.assert_array_equal(mask.sum(axis=(1,2)),[24,24])
        self.assertFalse((mask&s.ports().any(axis=0)).any())
        for c in range(4):
            np.testing.assert_array_equal(birth[c,:,0],birth[0,:,0]);np.testing.assert_array_equal(frame[c,:,0],frame[0,:,0])
        np.testing.assert_array_equal(birth[0,:,0],birth[0,:,1]);np.testing.assert_array_equal(birth[1],birth[0])
        np.testing.assert_array_equal(birth[2],birth[3])
        np.testing.assert_array_equal(frame[0,:,0],frame[0,:,1]);np.testing.assert_array_equal(frame[2],frame[0])
        np.testing.assert_array_equal(frame[1],frame[3])
        self.assertFalse(np.array_equal(birth[0,:,0],birth[2,:,1]))
        self.assertFalse(np.array_equal(frame[0,:,0],frame[1,:,1]))
        self.assertFalse(np.array_equal(birth[0,0],birth[0,1]))
        self.assertFalse(np.array_equal(frame[0,0],frame[0,1]))
        for a in [birth[0,:,0]/.05,birth[2,:,1]/.05,frame[0,:,0],frame[1,:,1]]:
            self.assertLess(abs(float(a.mean())),.12);self.assertLess(abs(float(a.var())-1),.15)

    def test_sample_extension_preserves_existing_draws(self):
        m,b,noise=s.draws(self.context,self.cfg)
        mm,bb,nn=s.draws(self.context,dict(self.cfg,masks_per_context=3))
        np.testing.assert_array_equal(m,mm[:2]);np.testing.assert_array_equal(b,bb[:,:4])
        np.testing.assert_array_equal(next(noise),next(nn)[:,:4])
        other=dict(self.context,block=self.context['block']+1)
        self.assertFalse(np.array_equal(b,s.draws(other,self.cfg)[1]))

    def test_input_immutability_label_isolation_and_first_cue(self):
        original=self.weights.tobytes();self.weights.flags.writeable=False
        raw=engine.simulate(self.weights,self.context,self.cfg)
        second=engine.simulate(self.weights,dict(self.context,rule=-1),self.cfg)
        self.assertEqual(original,self.weights.tobytes())
        auditor.equal(raw['read_end'],second['read_end'],'label isolation')
        for c in range(1,4):auditor.equal(raw['read_end'][:,0,:,0],raw['read_end'][:,c,:,0],'first-cue invariance')

    def test_negative_control_and_physical_erasures(self):
        raw=engine.simulate(self.weights,self.context,self.cfg)
        self.assertFalse((raw['physical']*~raw['available'][None]).any())
        self.assertTrue((s.score(raw['mean_ports'][9],1,.25)['category']==2).all())
        self.assertFalse(raw['physical'][9].any());self.assertFalse(raw['denominator'][9].any())
        for q in range(len(raw['masks'])):
            self.assertFalse(raw['read_end'][:,:,q,:,raw['masks'][q]].any())

    def test_separate_replay_and_corruption_rejection(self):
        raw=engine.simulate(self.weights,self.context,self.cfg)
        cache=Path(os.environ['XDG_CACHE_HOME'])/'TT005_checks';cache.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as folder:
            path=Path(folder)/'valid.npz';np.savez_compressed(path,**raw)
            auditor.replay(path,self.weights,self.context,self.cfg)
            raw['state_hashes'][0,0]^=1
            bad=Path(folder)/'corrupt.npz';np.savez_compressed(bad,**raw)
            with self.assertRaises(ValueError):auditor.replay(bad,self.weights,self.context,self.cfg)

    def test_invalid_inputs_and_read_length_rejected(self):
        mask,birth,noise=s.draws(self.context,self.cfg);expanded=np.repeat(mask,2,axis=0)
        broken=expanded.copy();broken[:,7,1]=True
        with self.assertRaises(ValueError):engine.read_body(self.weights,broken,birth,noise,self.cfg)
        with self.assertRaises(ValueError):engine.read_body(self.weights,expanded,birth,iter([]),self.cfg)

    def test_scalar_analysis_contract_on_fixture(self):
        # Use actual excluded outcomes; the analysis audit is separately coded.
        import analyze
        import analysis_audit
        cache=Path(os.environ['XDG_CACHE_HOME'])/'TT005_checks';cache.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as folder:
            path=Path(folder);engine.run_events(path,'fixture');analyze.run(path)
            report=analysis_audit.audit(path)
            self.assertEqual(report['categories'],176)

    def test_saved_e051_full_length_assays(self):
        source=s.verify_inputs();cfg=dict(s.PLAN['native'])
        with np.load(s.HERE/'native_checks.npz',allow_pickle=False) as z:raw={k:z[k] for k in z.files}
        self.assertEqual(raw['packets'].shape,(8,10,4096))
        for i,context in enumerate(source['contexts']):
            stream=s.random('E022',context['block'],'assay',32)
            initial=.05*stream.standard_normal((2,4,3,16,16))
            f=context['founder']//2;r=context['recipient']
            auditor.equal(raw['birth'][i],initial[f,r,1],'saved E051 initial state')
            birth=np.broadcast_to(raw['birth'][i],(1,1,2,16,16)).copy()
            def draws():
                for _ in range(2048):
                    draw=stream.standard_normal((2,4,3,16,16))[f,r,1]
                    yield np.broadcast_to(draw,(1,1,2,16,16)).copy()
            weights=np.frombuffer(raw['packets'][i].tobytes(),dtype='<f8').reshape(10,2,16,16).copy()
            own=engine.read_body(weights,raw['masks'][i][None],birth,draws(),cfg)
            auditor.equal(own['read_end'][:,0,0],raw['read_end'][i],'saved E051 final state')
            auditor.equal(own['mean_ports'][:,0,0],raw['mean_ports'][i],'saved E051 mean ports')


if __name__=='__main__':unittest.main(verbosity=2)
