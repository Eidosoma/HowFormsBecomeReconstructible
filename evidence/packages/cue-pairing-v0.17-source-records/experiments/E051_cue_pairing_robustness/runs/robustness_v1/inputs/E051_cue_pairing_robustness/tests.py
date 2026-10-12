"""Synthetic checks and technical exclusions; no scientific tuning."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import cap_cpus, rng
from E051_cue_pairing_robustness import model, audit, evidence, run
import numpy as np


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cap_cpus(8)
        cls.cfg=replace(model.base.Config(),recipients=1,teach_steps=12,capture_steps=6,observe_steps=2)
        cls.cycle=model.Cycle(read_steps=4,settling_steps=2,write_steps=1,generations=32)
        cls.packet=np.zeros((35,4,1,4096),np.uint8)
        cls.mask=np.zeros((4,1,16,16),bool)

    def test_01_exact_zero_endpoint_switch(self):
        body=np.full((35,4,1,2,16,16),.2)
        a=model.capture(body,3.); b=audit.capture(body,3.)
        for x,y in zip(a,b): audit.equal(x,y)
        self.assertGreater(a[0][0,0,0,0,0,0],.28)
        body[:,:,:,0,0,0]+=1e-12
        self.assertTrue(model.capture(body,3.)[2][0,0,0,0,0,0])
        body[:,:,:,0,0,1]+=1e-12
        a=model.capture(body,3.); b=audit.capture(body,3.)
        for x,y in zip(a,b): audit.equal(x,y)
        self.assertFalse(a[2][0,0,0,0,0,0]); self.assertLess(a[0][0,0,0,0,0,0],1e-22)
        self.assertTrue(a[2][1,0,0,0,0,0])

    def test_02_tolerance_and_exact_boundaries(self):
        tau=model.TAU; q=np.array([0.,np.nextafter(0.,1.),-tau,tau,np.nextafter(tau,np.inf),np.nextafter(-tau,-np.inf)])
        np.testing.assert_array_equal(model.ordinary_mask(q,'exact_rewrite'),[1,0,0,0,0,0])
        np.testing.assert_array_equal(model.ordinary_mask(q,'tolerance_rewrite'),[1,1,1,1,0,0])
        self.assertTrue(model.ordinary_mask(q,'ordinary_rewrite').all())
        self.assertFalse(model.ordinary_mask(q,'contrast_rewrite').any())

    def test_03_available_edges_and_strict_preservation(self):
        shape=(35,4,1,2,16,16); old=np.full(shape,.5); computed=np.full(shape,.123)
        old[...,0,0,1]=np.nextafter(.5,np.inf)
        available=np.ones(shape[1:],bool); available[...,0,0,2]=False
        chosen,kept=model.select(old,computed,available)
        self.assertEqual(chosen[4,0,0,0,0,0],.123)
        self.assertEqual(chosen[4,0,0,0,0,1],np.nextafter(.5,np.inf))
        self.assertEqual(chosen[0,0,0,0,0,1],.123)
        self.assertFalse((chosen*~available).any())
        self.assertFalse(kept[np.array([n%5!=4 for n in range(35)])].any())

    def test_04_correlated_gaussian_marginals(self):
        r=rng('E051','excluded','correlation_check'); z=r.standard_normal((2,128,16,16)); e=r.standard_normal(z.shape)
        rho=[1.,.999,.99,.9,0.]; paired=model.paired_draw(z,e,rho)
        audit.equal(paired[0,:,:,0],paired[0,:,:,1])
        audit.equal(paired[-1,:,:,1],model.base.paired_founders(e))
        for n,target in enumerate(rho):
            a,b=paired[n,:,:,0].ravel(),paired[n,:,:,1].ravel()
            self.assertLess(abs(b.mean()),.015); self.assertLess(abs(b.var()-1.),.02)
            self.assertLess(abs(np.corrcoef(a,b)[0,1]-target),.015)

    def test_05_independent_general_capture(self):
        body=rng('E051','excluded','capture').normal(size=(35,4,1,2,16,16))
        a=model.capture(body,3.); b=audit.capture(body,3.)
        for x,y in zip(a,b): audit.equal(x,y)
        altered=body.copy(); altered[0]*=-1
        a=model.capture(altered,3.)
        for x,y in zip(a,b): audit.equal(x[1:],y[1:])

    def test_06_nonzero_connectivity(self):
        w=np.zeros((1,2,16,16)); w[0,0,7,2]=1e-300; w[0,1,7,3]=-1.
        a=model.reachable(w); audit.equal(a,audit.reach(w))
        self.assertEqual(a.sum(),6); self.assertTrue(a[0,8,3])
        w[0,0,7,2]=0.; self.assertEqual(model.reachable(w).sum(),4)

    def test_07_reset_and_noise_are_separate(self):
        raw=model.rebuild(self.packet,900041,1,self.mask,self.cfg,self.cycle)
        for n in range(1,5): audit.equal(raw['birth'][n],raw['birth'][0])
        for n in (5,6):
            self.assertFalse(np.array_equal(raw['birth'][n,:,:,0],raw['birth'][n,:,:,1]))
            audit.equal(raw['noise_moments'][n],raw['noise_moments'][0])
        live=~raw['masks']; noninput=~model.base.PORTS[0]
        a,b=raw['end'][0,:,:,0],raw['end'][0,:,:,1]
        audit.equal(a[...,noninput],b[...,noninput])
        a,b=raw['end'][5,:,:,0],raw['end'][5,:,:,1]
        self.assertTrue(((a!=b)&live&noninput).any())
        self.assertFalse(raw['counts'][...,3].any())
        independent=audit.replay(self.packet,900041,1,self.mask,asdict(self.cfg),asdict(self.cycle))
        audit.equal_dict(raw,independent)

    def test_08_capture_precedes_holding(self):
        a=model.rebuild(self.packet,900041,2,self.mask,self.cfg,self.cycle)
        b=model.rebuild(self.packet,900041,2,self.mask,self.cfg,replace(self.cycle,write_steps=3))
        audit.equal(a['outgoing'],b['outgoing']); audit.equal(a['end'],b['end'])
        self.assertFalse(np.array_equal(a['write_end'],b['write_end']))

    def test_09_compact_evidence_rejects_corruption(self):
        raw=model.assay(self.packet[:1],900041,0,self.cfg,self.cycle)
        with tempfile.TemporaryDirectory(prefix='excluded_evidence_',dir=HERE/'analysis') as tmp:
            path=Path(tmp)/'valid.npz'; evidence.save(path,raw,'assay'); audit.check_compact(path,raw,'assay')
            saved=run.load(path); saved['end']=saved['end'].copy(); saved['end'].flat[0]+=1e-6
            bad=Path(tmp)/'corrupt.npz'; run.save(bad,saved)
            with self.assertRaises(AssertionError): audit.check_compact(bad,raw,'assay')
            saved=run.load(path); meta=json.loads(saved['__index__'].tobytes()); del meta['arrays']['denominator']
            saved['__index__']=np.frombuffer(json.dumps(meta).encode(),np.uint8)
            bad=Path(tmp)/'missing.npz'; run.save(bad,saved)
            with self.assertRaises(AssertionError): audit.check_compact(bad,raw,'assay')

    def test_10_strict_primary_and_unresolved_failure(self):
        stats={'assay/32/paired/exact_rewrite/scattered':{'ci95':[.8,.9]}}
        for p in ('noise_0999','reset_099'):
            stats[f'assay/32/{p}/exact_rewrite/scattered']={'ci95':[.8,.9]}
            stats[f'pairing_effect/{p}/exact_rewrite']={'ci95':[-.04,.02]}
        self.assertTrue(run.decisions(stats,False)['primary_decision'])
        self.assertIsNone(run.decisions(stats,True)['primary_decision'])
        stats['pairing_effect/noise_0999/exact_rewrite']['ci95']=[-.05,.02]
        d=run.decisions(stats,False); self.assertFalse(d['primary_decision']); self.assertEqual(d['primary_classifications']['noise_0999'],'UNRESOLVED')
        stats['pairing_effect/noise_0999/exact_rewrite']['ci95']=[-.2,-.051]
        self.assertEqual(run.decisions(stats,False)['primary_classifications']['noise_0999'],'LOSS_EXCEEDS_FIVE_POINTS')
        stats['assay/32/paired/exact_rewrite/scattered']['ci95'][0]=.75
        self.assertFalse(run.decisions(stats,False)['primary_gates']['paired_baseline_lower_above_075'])

    def test_11_score_axes_require_both_cues(self):
        values=np.empty((35,4,1,2,3,2))
        for n,f,r,c,d in np.ndindex(35,4,1,2,3):
            target=model.base.RULES[f]*model.base.CUES[c]; values[n,f,r,c,d]=[target,-target]
        values[0,0,0,1,1]=0.
        result=model.score(values,self.cfg); audit.equal_dict(result,audit.score(values,asdict(self.cfg)))
        self.assertEqual(result['correct'][0,:,:,:,1].all(axis=2).mean(),.75)
        self.assertEqual(result['correct'][0,:,:,:,0].all(axis=2).mean(),1.)

    def test_12_fresh_ids_and_fixed_design(self):
        ids,cfg,cycle=run.configuration('fixture'); self.assertEqual(ids,[900041])
        spec=json.loads((HERE/'SOURCE_DATA.json').read_text())
        self.assertFalse(set(spec['blocks'])&set(spec['prior_block_ids']))
        self.assertEqual(len(model.CONDITIONS),35); self.assertEqual(model.TAU,1e-4)
        self.assertEqual(list(model.PAIRINGS),list(audit.PAIRINGS))
        self.assertEqual(cycle.generations,32); self.assertEqual(cfg.recipients,2)


if __name__=='__main__': unittest.main(verbosity=2)
