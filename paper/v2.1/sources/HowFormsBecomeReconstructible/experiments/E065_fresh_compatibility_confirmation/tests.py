"""Mechanistic invariants, exact predecessor constructions and inference direction."""
import unittest
import numpy as np
from E065_fresh_compatibility_confirmation import model,audit_model,source_model,source_audit,data,inference
from E065_fresh_compatibility_confirmation.plan import settings,PRIMARY,CONFIDENCE
from E062_cross_stage_compatibility import model as old62
from E064_magnitude_subset_intervention import model as old64


def source():
    g=np.random.default_rng(781);old=g.uniform(.01,1.,(2,4,1,2,16,16))*g.choice([-1.,1.],(2,4,1,2,16,16))
    final=old*.5;final[...,0,2,2]*=-1;old[...,0,0,0]=0.;final[...,0,0,0]=-.25;final[...,1,1,1]=0.
    return dict(initial=model.base.encode(old),final=model.base.encode(final))


class Checks(unittest.TestCase):
    def test_construction_and_prior_equivalence(self):
        s=source();a=model.intervene(s);b=audit_model.intervene(s);data.equal(a,b)
        x=old62.intervene(s);y=old64.intervene(s)
        data.equal({'packets':a['packets']},{'packets':np.concatenate((x['packets'][:8],y['packets'][2:6],x['packets'][10:11]))})
        self.assertTrue((a['changed'].sum(axis=(-3,-2,-1))==1).all())
        self.assertTrue((a['unchanged'].sum(axis=(-3,-2,-1))==509).all())
        np.testing.assert_array_equal(a['denominator'][:2],a['denominator'][4:6])
        np.testing.assert_array_equal(a['denominator'][2:4],a['denominator'][6:8])

    def test_empty_groups_and_signed_zero(self):
        s=source();old=model.base.decode(s['initial']);final=model.base.decode(s['final'])
        for scenario in ('common','changed','unchanged'):
            previous=old.copy()
            if scenario=='common':previous.fill(-0.)
            elif scenario=='changed':previous=np.copysign(abs(previous),final)
            else:previous=np.copysign(abs(previous),-final)
            item=dict(initial=model.base.encode(previous),final=s['final'])
            a=model.intervene(item);data.equal(a,audit_model.intervene(item))
            self.assertFalse(a[scenario].any())
            start={'common':2,'changed':8,'unchanged':10}[scenario]
            self.assertEqual(a['packets'][start:start+2].tobytes(),s['final'].tobytes())

    def test_reader_controls_and_replay(self):
        s=source();a=model.intervene(s);cfg={**settings('fixture')['reader'],'recipients':1}
        fresh=model.assay(a['packets'],900091,cfg);other=audit_model.assay(a['packets'],900091,cfg)
        fresh.update(model.graph.batch(fresh['effective']));other.update(audit_model.graph_batch(other['effective']))
        data.equal(fresh,other);case,c=model.diagnostics(s,a,fresh,cfg);case2,c2=audit_model.diagnostics(s,a,other,cfg)
        data.equal(case,case2);self.assertEqual(c,c2);self.assertTrue(c['pass'],c)

    def test_both_renewal_namespaces(self):
        s=source();cfg=settings('fixture');config=model.base.Config(**{**cfg['config'],'recipients':1})
        for namespace,packet in (('E022',s['initial'][:1]),('E058',s['initial'])):
            a,_=source_model.rebuild(packet,900091,1,config,cfg['source_cycle'],namespace)
            b,_=source_audit.rebuild(packet,900091,1,{**cfg['config'],'recipients':1},cfg['source_cycle'],namespace)
            data.equal(a,b)

    def test_effect_orientation_and_boundaries(self):
        e=inference.effects(np.array([.9,.3,.8,.75,.86,.7]))
        self.assertAlmostEqual(e['earlier_sign_benefit'],.45)
        self.assertAlmostEqual(e['sign_magnitude_interaction'],.55)
        self.assertAlmostEqual(e['joint_magnitude_excess_loss'],.36)
        self.assertEqual(inference.classification([0.,.1]),'UNRESOLVED')
        self.assertEqual(inference.classification([-.1,0.]),'UNRESOLVED')

    def test_reduced_archived_fixture_projections(self):
        cfg=settings('fixture');config=model.base.Config(**cfg['config']);b=900041
        acq=source_model.reader.acquisition.teach(b,config)
        data.equal(acq,data.reference('fixture','E057','acquisition_900041.npz'))
        packets=acq['acquired'][1,:,None].repeat(config.recipients,axis=1)[None]
        for g in range(1,33):
            raw,_=source_model.rebuild(packets,b,g,config,cfg['source_cycle'],'E022')
            data.legacy_boundary('fixture','source',g,raw);packets=raw['outgoing']
        body,out=source_model.perturb(packets,b,cfg['body']);data.legacy_body('fixture',body,out)
        initial=out['packets'].copy();packets=initial.copy()
        for g in range(1,4):
            raw,_=source_model.rebuild(packets,b,g,config,cfg['continuation'],'E058')
            data.legacy_boundary('fixture','continuation',g,raw);packets=raw['outgoing']
        source=dict(initial=initial,final=packets)
        previous=data.reference('fixture','E062','source_900041.npz')
        data.equal(source,{k:previous[k] for k in source})

    def test_three_primary_conjunction_and_suppression(self):
        pattern=np.array([1,1,0,0,1,1,1,1,1,1,1,1,0],float)[:,None,None]
        cases=[dict(both=pattern.copy()) for _ in range(2)]
        for mode,ok in (('scientific',True),('fixture',True),('scientific',False)):
            controls=[{'pass':ok} for _ in cases]
            s=inference.analyze(cases,controls,mode);self.assertEqual(inference.audit(cases,controls,s,mode),46)
            self.assertEqual(s['primary_confirmed'],True if mode=='scientific' and ok else None)
            for name in PRIMARY:self.assertEqual(s['statistics']['effect/both/pooled/'+name]['confidence'],CONFIDENCE)
        bad=pattern.copy();bad[6:8]=0.
        s=inference.analyze([dict(both=bad),dict(both=bad)],[{'pass':True}]*2,'scientific')
        self.assertFalse(s['primary_confirmed'])

    def test_paired_original_history_weighting(self):
        v=np.array([1,1,0,0,1,1,1,0,1,1,1,1,0],float)[:,None,None]
        cases=[dict(both=v)];s=inference.analyze(cases,[{'pass':True}],'scientific')
        inference.audit(cases,[{'pass':True}],s,'scientific')
        self.assertEqual(s['statistics']['effect/both/pooled/earlier_sign_benefit']['mean'],.5)


if __name__=='__main__':unittest.main()
