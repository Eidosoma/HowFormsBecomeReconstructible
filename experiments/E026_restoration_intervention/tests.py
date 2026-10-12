"""Short excluded-source checks before any full-duration hybrid simulation."""
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
from E026_restoration_intervention import model, run as study, audit
from E023_receiver_compensation import model as predecessor
from E023_receiver_compensation.audit import receiver_denominators as independent_denominators
import numpy as np


class RestorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus()
        cls.data,cls.source,cls.cfg,cls.cycle=study.source_packets('fixture',900025)

    def test_partition_and_changes_only_on_restored_coordinates(self):
        d=self.data;before={k:v.copy() for k,v in d.items()}
        alive=~d['renewal_masks'];current=np.zeros_like(d['current']);common=current.copy()
        for f in range(4):
            for r in range(2):
                for axis in range(2):
                    for y in range(16):
                        for x in range(16):
                            yy,xx=((y,(x+1)%16) if axis==0 else ((y+1)%16,x))
                            present=alive[:,f,r,y,x]&alive[:,f,r,yy,xx]
                            current[f,r,axis,y,x]=present[2];common[f,r,axis,y,x]=all(present)
        np.testing.assert_array_equal(d['current'],current);np.testing.assert_array_equal(d['common'],common)
        np.testing.assert_array_equal(d['restored'],current&~common)
        self.assertTrue(d['restored'].any());self.assertFalse((d['restored']&common).any())
        w=model.base.decode(d['records']);M=model.base.decode(d['copy_packet']);R=model.base.decode(d['rebuilt_packet']);T=d['restored']
        np.testing.assert_array_equal(w[1][~T],M[~T]);np.testing.assert_array_equal(w[1][T],R[T])
        np.testing.assert_array_equal(w[2][~T],R[~T]);self.assertFalse(w[2][T].any())
        self.assertFalse(w[:,~current].any())
        # A small signed restored value must be retained, not thresholded away.
        R[tuple(np.argwhere(T)[0])]=-1e-14
        changed=model.construct(d['copy_packet'],model.base.encode(R),d['renewal_masks'])
        self.assertEqual(model.base.decode(changed['records'])[1][tuple(np.argwhere(T)[0])],-1e-14)
        for key in d:np.testing.assert_array_equal(d[key],before[key])

    def test_exact_old_endpoints_and_paired_randomness(self):
        self.assertIs(model.assay,predecessor.assay);self.assertIs(model.score,predecessor.score)
        calls=[];step=predecessor.renewal.compensated_step
        def watched(v,w,den,noise,cfg,amplification):
            if not calls:
                for n in range(1,8):np.testing.assert_array_equal(v[0],v[n])
            self.assertEqual(noise.shape[0],1);calls.append(amplification)
            return step(v,w,den,noise,cfg,amplification)
        with patch.object(predecessor.renewal,'compensated_step',side_effect=watched):
            raw=model.assay(self.data['records'],900025,3,self.cfg,self.cycle)
        self.assertEqual(calls,[False]*6+[True]*18)
        with np.load(self.source/'assay_900025_h3.npz',allow_pickle=False) as old:
            model.check_endpoints(raw,old)
            np.testing.assert_array_equal(raw['late_ports'][:,[0,3,4,7]],old['late_ports'][:,[5,2,13,10]])

    def test_focal_contrast_directions_and_interaction(self):
        table=np.array([[.25,.5,.375,.875],[.5,.625,.75,.875],[.875,.75,.625,.5]])
        e=study.effects(table)
        np.testing.assert_array_equal(e['restoration_with_copied_survivors'],[.25,.125,-.125])
        np.testing.assert_array_equal(e['restoration_with_rebuilt_survivors'],[.5,.125,-.125])
        np.testing.assert_array_equal(e['interaction'],[.25,0,0])
        np.testing.assert_array_equal(e['total_gap'],e['restoration_with_rebuilt_survivors']+e['rewritten_survivors_without_restoration'])
        swapped=study.effects(table[:,[1,0,3,2]])
        np.testing.assert_array_equal(swapped['restoration_with_copied_survivors'],-e['restoration_with_copied_survivors'])
        null=study.effects(table[:,[0,0,3,3]])
        self.assertFalse(null['restoration_with_copied_survivors'].any());self.assertFalse(null['restoration_with_rebuilt_survivors'].any())

    def test_denominators_recomputed_after_every_control(self):
        packets,_=predecessor.renewal.assay_packets(self.data['records'],900025,3)
        masks=model.base.damage_masks(900025,'E022_h3',self.cfg)
        weights=np.concatenate([model.base.effective_weights(p,masks) for p in packets])
        den=model.receiver_denominators(weights)
        np.testing.assert_array_equal(den,independent_denominators(weights))
        self.assertTrue((den[:4]==4).all())
        self.assertFalse(den[4:,...,[3,5],:,:].any())
        self.assertTrue((den[5,...,0,:,:]>=den[4,...,0,:,:]).all())
        self.assertTrue((den[7,...,0,:,:]>=den[6,...,0,:,:]).all())
        self.assertTrue((den[5,...,0,:,:]!=den[4,...,0,:,:]).any())

    def test_independent_end_to_end(self):
        started=time.monotonic();output=study.create(HERE/'analysis/fixture_attempt1','fixture',1)
        study.save_block(output,900025);study.analyze(output)
        summary=study.load(output/'summary.json')
        self.assertEqual(summary['status'],'TECHNICAL_ONLY')
        self.assertEqual(summary['individual_observations'],2688)
        for item in summary['focal'].values():
            self.assertIsNone(item['lower_bound_above_zero']);self.assertIsNone(item['lower_bound_above_010'])
        study.finish(output,started,dict(experiment='E026',blocks_completed=1))
        receipt=audit.audit(output,1)
        self.assertEqual(receipt['status'],'PASS');self.assertEqual(receipt['individual_observations'],2688)


if __name__=='__main__':unittest.main(verbosity=2)
