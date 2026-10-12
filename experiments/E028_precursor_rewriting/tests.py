"""Excluded-source checks for the precursor-reading / target-refresh factorial."""
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
from E028_precursor_rewriting import model, run as study, audit
from E023_receiver_compensation import model as predecessor
from E023_receiver_compensation.audit import receiver_denominators as independent_denominators
import numpy as np


class PrecursorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus()
        cls.incoming,cls.masks,cls.source,cls.cfg,cls.cycle=study.source_packets('fixture',900027)
        cls.raw=model.boundary(cls.incoming,cls.masks,900027,cls.cfg,cls.cycle)

    def test_mask_only_target_and_exact_unchanged_body(self):
        available,target=model.target_edges(self.masks)
        independent=np.zeros_like(available)
        for g in range(3):
            for y in range(16):
                for x in range(16):
                    independent[g,...,0,y,x]=~(self.masks[g,...,y,x]|self.masks[g,...,y,(x+1)%16])
                    independent[g,...,1,y,x]=~(self.masks[g,...,y,x]|self.masks[g,...,(y+1)%16,x])
        np.testing.assert_array_equal(available,independent)
        np.testing.assert_array_equal(target,(~independent[0]) & independent[1] & independent[2])
        self.assertTrue(target.any());self.assertFalse((target & ~available[2]).any())
        with np.load(self.source/'boundary_900027_g3.npz',allow_pickle=False) as old:
            model.check_boundary(self.raw,old)

    def test_freeze_only_targets_and_keep_tiny_values(self):
        d=self.raw;before={k:v.copy() for k,v in d.items()}
        target,current=d['target'],d['available'][2]
        old=model.base.decode(d['incoming']);fresh=model.base.decode(d['computed_packets'])
        ix=tuple(np.argwhere(target)[0]);old[ix]=-1e-14
        records=model.construct(model.base.encode(old),d['computed_packets'],target,current)
        w=model.base.decode(records)
        for k,reading in enumerate((0,0,1,1)):
            np.testing.assert_array_equal(w[k][~target],fresh[reading][~target])
            np.testing.assert_array_equal(w[k][target],(old if k%2 else fresh[reading])[target])
        self.assertEqual(w[1][ix],-1e-14);self.assertEqual(w[3][ix],-1e-14)
        self.assertFalse(w[:,~current].any())
        for key in d:np.testing.assert_array_equal(d[key],before[key])
        # Reading deletion does not prevent the independent frozen-write intervention.
        self.assertFalse(model.base.decode(d['read_packets'])[1][target].any())
        np.testing.assert_array_equal(model.base.decode(d['records'])[3][target],model.base.decode(d['incoming'])[target])

    def test_paired_births_noise_and_staging(self):
        calls=[];step=model.renewal.compensated_step
        def watched(v,w,den,noise,cfg,amplification):
            if not calls:np.testing.assert_array_equal(v[0],v[1])
            self.assertEqual(noise.shape,(1,4,2,1,16,16));calls.append(amplification)
            return step(v,w,den,noise,cfg,amplification)
        with patch.object(model.renewal,'compensated_step',side_effect=watched):
            developed=model.develop(self.raw['read_packets'],self.raw['body_masks'],900027,self.cfg,self.cycle)
        self.assertEqual(calls,[False]*6+[True]*18)
        for key in developed:np.testing.assert_array_equal(developed[key],self.raw[key])

    def test_terminal_exact_endpoint_and_control_denominators(self):
        self.assertIs(model.assay,predecessor.assay);self.assertIs(model.score,predecessor.score)
        raw=model.assay(self.raw['records'],900027,3,self.cfg,self.cycle)
        with np.load(self.source/'assay_900027_h3.npz',allow_pickle=False) as old:model.check_endpoints(raw,old)
        weights=np.concatenate([model.base.effective_weights(p,raw['masks']) for p in raw['packets']])
        np.testing.assert_array_equal(raw['receiver_denominators'],independent_denominators(weights))
        den=raw['receiver_denominators'];self.assertTrue((den[:4]==4).all())
        self.assertFalse(den[4:,...,[3,5],:,:].any())
        for panel in range(8):
            for arm in (3,5,6):
                np.testing.assert_array_equal(raw['end'][panel,:,:,0,:,arm][...,~model.PORTS[0]],raw['end'][panel,:,:,1,:,arm][...,~model.PORTS[0]])
        bodyden=self.raw['read_denominators']
        self.assertTrue((bodyden[1]<=bodyden[0]).all());self.assertTrue((bodyden[1]!=bodyden[0]).any())

    def test_focal_directions_and_interaction(self):
        table=np.array([[.875,.5,.625,.25],[.5,.625,.75,.875],[.875,.75,.625,.5]])
        e=study.effects(table)
        np.testing.assert_array_equal(e['rewrite_with_precursors'],[.375,-.125,.125])
        np.testing.assert_array_equal(e['precursors_with_rewriting'],[.25,-.25,.25])
        np.testing.assert_array_equal(e['interaction'],[0,0,0])
        np.testing.assert_array_equal(e['total_effect'],e['rewrite_with_precursors']+e['precursors_without_rewriting'])
        shifted=table.copy();shifted[:,0]+=.125
        np.testing.assert_array_equal(study.effects(shifted)['interaction'],[.125,.125,.125])
        swapped=study.effects(table[:,[1,0,3,2]])
        np.testing.assert_array_equal(swapped['rewrite_with_precursors'],-e['rewrite_with_precursors'])

    def test_strength_descriptions_use_same_coordinates_and_retain_empty_sets(self):
        raw={k:v.copy() for k,v in self.raw.items()}
        raw['target'][0,0]=False
        rows=model.strength_rows(raw)
        self.assertEqual(len(rows),8)
        self.assertTrue(all(rows[0][key]==0 for key in model.STRENGTH_FIELDS))
        old,fresh=model.base.decode(raw['incoming']),model.base.decode(raw['computed_packets'])
        for row in rows[1:]:
            f,r=row['founder'],row['lineage'];t=raw['target'][f,r]
            self.assertEqual(row['target_count'],int(t.sum()))
            for label,w in [('incoming',old[f,r]),('kept',fresh[0,f,r]),('erased',fresh[1,f,r])]:
                self.assertEqual(row[label+'_mean_abs'],float(abs(w[t]).mean()))
                self.assertEqual(row[label+'_strong'],int((abs(w[t])>.5).sum()))

    def test_independent_end_to_end(self):
        started=time.monotonic();output=study.create(HERE/'analysis/fixture_attempt1','fixture',1)
        study.save_block(output,900027);study.analyze(output)
        summary=study.load(output/'summary.json');self.assertEqual(summary['status'],'TECHNICAL_ONLY')
        self.assertEqual(summary['individual_observations'],2688);self.assertEqual(summary['body_individual_observations'],32)
        for item in summary['focal'].values():
            self.assertIsNone(item['lower_bound_above_zero']);self.assertIsNone(item['lower_bound_above_010'])
        study.finish(output,started,dict(experiment='E028',blocks_completed=1))
        receipt=audit.audit(output,1)
        self.assertEqual(receipt['status'],'PASS');self.assertEqual(receipt['individual_observations'],2688)
        self.assertEqual(receipt['body_individual_observations'],32)


if __name__=='__main__':unittest.main(verbosity=2)
