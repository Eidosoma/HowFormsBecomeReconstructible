"""Excluded adapter qualification, including original-native trajectory matching."""
from dataclasses import replace
from pathlib import Path
import tempfile
import os
import unittest

import numpy as np
import support as s
import adapter as a
import auditor


class Checks(unittest.TestCase):
    def setUp(self):
        self.cfg=s.config('fixture')
        self.record=dict(block=900003,source_depth=0,founder=0,rule=1)
        self.key=s.event_key(self.record,'assay',0)
        self.w=np.repeat(s.cases('fixture')[1][0][None],2,axis=0)

    def test_strict_threshold_and_label_involution(self):
        v=np.array([[[.25,-.25],[-.25,.25]]])
        self.assertEqual(s.classify(v,1)[0][0],2)
        v=np.sign(v)*np.nextafter(.25,1.)
        self.assertEqual(s.classify(v,1)[0][0],0)
        self.assertEqual(s.classify(v,-1)[0][0],1)
        with self.assertRaises(ValueError):s.classify(np.full((1,2,2),np.nan),1)

    def test_clone_immutability_and_no_label_input(self):
        original=self.w.tobytes(); self.w.flags.writeable=False
        first=a.simulate(self.w,self.key,self.cfg)
        other=dict(self.record,rule=-1)
        second=a.simulate(self.w,s.event_key(other,'assay',0),self.cfg)
        self.assertEqual(original,self.w.tobytes())
        auditor.equal(first['read_end'],second['read_end'],'no label input')

    def test_assay_schedule_cannot_change_renewal(self):
        key=s.event_key(self.record,'renewal',1)
        first=a.simulate(self.w,key,self.cfg,renewal=True)
        a.simulate(self.w,self.key,self.cfg)
        a.simulate(self.w,s.event_key(self.record,'assay',0,1),self.cfg)
        second=a.simulate(self.w,key,self.cfg,renewal=True)
        auditor.equal(first['outgoing'],second['outgoing'],'assay-order independence')

    def test_paths_and_streams_are_separate(self):
        m,b,noise=s.draws(self.key,2,self.cfg); m2,b2,noise2=s.draws(self.key,3,self.cfg)
        np.testing.assert_array_equal(m,m2[:2]); np.testing.assert_array_equal(b,b2[:2])
        np.testing.assert_array_equal(next(noise),next(noise2)[:2])
        self.assertFalse(np.array_equal(b[0],b[1]))
        _,renew,_=s.draws(s.event_key(self.record,'renewal',1),2,self.cfg)
        self.assertFalse(np.array_equal(b,renew))
        self.assertFalse((m & s.ports().any(axis=0)).any())
        np.testing.assert_array_equal(m.sum(axis=(1,2)),[24,24])

    def test_erased_and_disabled_reader(self):
        erased=a.simulate(np.zeros_like(self.w),self.key,self.cfg)
        disabled=a.simulate(self.w,self.key,self.cfg,disabled=True)
        auditor.equal(erased['read_end'],disabled['read_end'],'zero communication')
        self.assertTrue((s.classify(erased['mean_ports'],1)[0]==2).all())

    def test_capture_precedes_holding(self):
        key=s.event_key(self.record,'renewal',1)
        x=a.simulate(self.w,key,self.cfg,renewal=True)
        y=a.simulate(self.w,key,dict(self.cfg,write_steps=1),renewal=True)
        auditor.equal(x['outgoing'],y['outgoing'],'capture before holding')
        self.assertFalse(np.array_equal(x['holding_end'],y['holding_end']))
        self.assertFalse((x['outgoing']*~x['available']).any())

    def test_safe_positive_binary_rescaling(self):
        x=a.simulate(self.w,self.key,self.cfg)
        y=a.simulate(self.w*.5,self.key,self.cfg)
        auditor.equal(x['read_end'],y['read_end'],'binary scaling invariance')

    def test_separate_replay_and_corruption_detection(self):
        key=s.event_key(self.record,'renewal',1)
        raw=a.simulate(self.w,key,self.cfg,renewal=True)
        cache=Path(os.environ.get('XDG_CACHE_HOME', str(s.HERE/'.cache')))/'TT003_checks'; cache.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as name:
            p=Path(name)/'event.npz'; np.savez_compressed(p,**raw)
            replay=auditor.replay_event(p,self.w,key,self.cfg,renewal=True)
            auditor.equal(replay,raw['outgoing'],'independent replay')
            raw['mean_ports'][0,0,0]+=.01; q=Path(name)/'corrupt.npz'; np.savez_compressed(q,**raw)
            with self.assertRaises(ValueError):auditor.replay_event(q,self.w,key,self.cfg,renewal=True)

    def test_original_e041_rewrite_fixture(self):
        native=s.reference('E041_full_rewrite_confirmation.model')
        cfg=replace(native.CFG,recipients=2,teach_steps=12,capture_steps=6,observe_steps=4)
        cycle=replace(native.CYCLE,read_steps=24,settling_steps=3,write_steps=8)
        weights=s.random('TT003','native_fixture').uniform(-1,1,(11,4,2,2,16,16))
        incoming=native.base.encode(weights)
        result=native.replace_record(incoming,900041,1,cfg,cycle)
        stream=native.rng('E022',900041,'develop',1)
        stream.standard_normal((2,2,16,16))
        noises=(native.base.paired_founders(stream.standard_normal((2,2,16,16))).reshape(8,16,16) for _ in range(24))
        own=a.read_body(weights[3].reshape(8,2,16,16),result['renewal_mask'].reshape(8,16,16),
            result['birth'].reshape(8,16,16),noises,self.cfg)
        auditor.equal(own['read_end'],result['developed_end'][3].reshape(8,2,16,16),'original E041 read')
        auditor.equal(own['late_ports'],result['developed_late_ports'][:,3].reshape(4,8,2,2),'original E041 ports')
        computed=a.capture(own['read_end'],own['available'])
        auditor.equal(computed,native.base.decode(result['outgoing'][3]).reshape(8,2,16,16),'original E041 rewrite')
        stream=native.rng('E022',900041,'write',1)
        noises=(native.base.paired_founders(stream.standard_normal((2,2,16,16))).reshape(8,16,16) for _ in range(8))
        held=a.hold(own['read_end'],result['renewal_mask'].reshape(8,16,16),own['available'],noises,self.cfg)
        auditor.equal(held['holding_end'],result['write_end'][3].reshape(8,2,16,16),'original E041 holding')

    def test_original_e041_fresh_assay_fixture(self):
        native=s.reference('E041_full_rewrite_confirmation.model')
        cfg=replace(native.CFG,recipients=2,teach_steps=12,capture_steps=6,observe_steps=4)
        cycle=replace(native.CYCLE,read_steps=24,settling_steps=3,write_steps=8)
        weights=s.random('TT003','assay_fixture').uniform(-1,1,(1,4,2,2,16,16))
        result=native.assay(native.base.encode(weights),900041,0,cfg,cycle)
        stream=native.rng('E022',900041,'assay',0); stream.standard_normal((2,2,3,16,16))
        noises=(native.base.paired_founders(stream.standard_normal((2,2,3,16,16)))[:,:,1].reshape(8,16,16) for _ in range(24))
        own=a.read_body(weights[0].reshape(8,2,16,16),result['masks'][:,:,1].reshape(8,16,16),
            result['birth'][:,:,1].reshape(8,16,16),noises,self.cfg)
        auditor.equal(own['read_end'],result['end'][1,:,:,:,1,0].reshape(8,2,16,16),'original normalized assay')
        auditor.equal(own['late_ports'],result['late_ports'][:,1,:,:,:,1,0].reshape(4,8,2,2),'original assay scores')


if __name__=='__main__':unittest.main(verbosity=2)
