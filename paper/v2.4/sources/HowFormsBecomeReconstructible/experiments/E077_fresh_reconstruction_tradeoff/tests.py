"""Scientific parity, intervention identities, endpoint harms and signed inference."""
import inspect
import itertools
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from common import rng
from E077_fresh_reconstruction_tradeoff import model,audit_model,data,inference,individuals
from E077_fresh_reconstruction_tradeoff.plan import HERE,settings,PRIMARY,PREDICTED


def legacy_projection_check(source_inter,source,inter,comp,packets,block,cfg,raw,fresh):
    from E068_fresh_recovery_confirmation import model as source_legacy
    from E073_saved_cohort_reversal_replication import model as endpoint_legacy
    from E076_selected_sign_magnitude import model as components_legacy
    def source_remap(tag,*parts):
        assert tag=='E068';return rng('E077',*parts)
    def endpoint_remap(tag,*parts):
        assert tag=='E073';return rng('E077',*parts)
    with patch.object(source_legacy,'rng',side_effect=source_remap):
        old_source=source_legacy.rebuild(source_inter['packets'],block,0,cfg['config'],cfg['source_recovery_cycle'])
    data.equal(source,old_source)
    data.equal(inter,endpoint_legacy.intervene(source))
    with patch.object(endpoint_legacy,'rng',side_effect=endpoint_remap):
        old=endpoint_legacy.rebuild(inter['packets'],block,1,cfg['config'],cfg['cycle'])
        read=endpoint_legacy.develop(packets,block,cfg['reader'],cfg['reader'],'terminal')
    data.equal(raw,old);data.equal(fresh,read)
    previous=components_legacy.intervene(dict(outgoing=raw['outgoing'],eligible=inter['eligible']))
    assert comp.tobytes()==previous['packets'][8:16].tobytes()
    projected=dict(fresh)
    for key in ('mean_ports','denominator','coupling','boundary_counts'):projected[key]=fresh[key][:18]
    old_cases,old_records,old_transition=endpoint_legacy.diagnostics(packets[:18],inter,projected,raw,cfg['reader'])
    cases,records,transition=model.diagnostics(packets,inter,fresh,raw,cfg['reader'])
    data.equal(old_cases,{k:v[:18] for k,v in cases.items()})
    data.equal(old_records,{k:v[:18] for k,v in records.items()});data.equal(old_transition,transition)


class Checks(unittest.TestCase):
    def fixture(self):
        from E068_fresh_recovery_confirmation import model as old,audit_model as old_audit
        cfg=settings('fixture');ancestry=data.technical_source('fixture')
        source_inter=old.intervene(ancestry);data.equal(source_inter,old_audit.intervene(ancestry))
        source=model.rebuild(source_inter['packets'],900041,0,cfg['config'],cfg['source_recovery_cycle'])
        data.equal(source,audit_model.rebuild(source_inter['packets'],900041,0,cfg['config'],cfg['source_recovery_cycle']))
        inter=model.intervene(source);data.equal(inter,audit_model.intervene(source))
        raw=model.rebuild(inter['packets'],900041,1,cfg['config'],cfg['cycle'])
        data.equal(raw,audit_model.rebuild(inter['packets'],900041,1,cfg['config'],cfg['cycle']))
        comp=model.components(raw['outgoing'],inter['eligible'])
        assert comp.tobytes()==audit_model.components(raw['outgoing'],inter['eligible']).tobytes()
        packets=np.concatenate((inter['packets'],raw['outgoing'],comp))
        fresh=model.develop(packets,900041,cfg['reader'],cfg['reader'],'terminal')
        data.equal(fresh,audit_model.develop(packets,900041,cfg['reader'],cfg['reader'],'terminal'))
        return cfg,source_inter,source,inter,raw,comp,packets,fresh

    def test_new_sources_unchanged_settings_and_exact_equations(self):
        from E068_fresh_recovery_confirmation.plan import settings as old_source
        from E073_saved_cohort_reversal_replication.plan import settings as old_settings
        from E073_saved_cohort_reversal_replication import model as old,audit_model as old_audit
        for mode in ('fixture','benchmark','scientific'):
            cfg=settings(mode);prev=old_settings(mode);source=old_source(mode)
            for k in ('config','cycle','reader','recipients'):self.assertEqual(cfg[k],prev[k])
            for k in ('source_config','source_cycle','body','source_continuation'):self.assertEqual(cfg[k],source[k])
            self.assertEqual(cfg['source_recovery_cycle'],source['cycle'])
        for current,previous,functions in (
            (model,old,('intervene','digest','masks','coupling','develop','capture','rebuild','score')),
            (audit_model,old_audit,('intervene','digest','masks','alive','coupling','develop','capture','rebuild','score'))):
            for name in functions:
                self.assertEqual(inspect.getsource(getattr(current,name)),inspect.getsource(getattr(previous,name)).replace("'E073'","'E077'"))
        self.assertEqual(len(settings('scientific')['blocks']),32)
        data.verify_receipts('scientific')
        with self.assertRaises(AssertionError):data.reference('scientific','source_040000.npz')

    def test_full_fixture_replay_legacy_projections_and_individual_export(self):
        cfg,si,source,inter,raw,comp,packets,fresh=self.fixture()
        legacy_projection_check(si,source,inter,comp,packets,900041,cfg,raw,fresh)
        cases,records,transition=model.diagnostics(packets,inter,fresh,raw,cfg['reader'])
        other,r2,t2=audit_model.diagnostics(packets,inter,fresh,raw,cfg['reader'])
        data.equal(cases,other);data.equal(records,r2);data.equal(transition,t2)
        summary=inference.analyze([cases],[{'pass':True}],'fixture')
        inference.audit([cases],[{'pass':True}],summary,'fixture')
        with tempfile.TemporaryDirectory(dir=HERE/'analysis',prefix='development_') as p:
            counts=individuals.export(Path(p),[900041],[cases],summary)
            self.assertEqual(counts['mixture_pooled']['cases'],16)
        self.assertEqual(comp.shape[0],8);self.assertEqual(packets.shape[0],26)
        for item in (records,fresh):
            self.assertEqual(item['denominator'][18:22].tobytes(),item['denominator'][22:26].tobytes())
            self.assertEqual(abs(item['coupling'][18:22]).tobytes(),abs(item['coupling'][22:26]).tobytes())

    def synthetic(self,n=64):
        g=np.random.default_rng(77001)
        w=g.uniform(.01,1.,(9,4,1,2,16,16))*g.choice((-1.,1.),(9,4,1,2,16,16))
        w[8]=0.
        flat=w.reshape(9,4,1,512)
        flat[:4,...,5]=np.nextafter(0.,1.);flat[4:8,...,5]=-np.nextafter(0.,1.)
        flat[:4,...,20]=-0.;flat[4:8,...,20]=0.
        e=np.zeros((4,4,1,2,16,16),bool);e.reshape(4,4,1,512)[...,:n]=True
        return model.base.encode(w),e

    def test_component_support_signs_magnitudes_signed_zero_and_denominators(self):
        for count in (0,64,512):
            packets,e=self.synthetic(count);w=model.base.decode(packets)
            result=model.components(packets,e);self.assertEqual(result.tobytes(),audit_model.components(packets,e).tobytes())
            m,j=model.base.decode(result)[:4],model.base.decode(result)[4:]
            for x in (m,j):
                np.testing.assert_array_equal(x!=0,w[4:8]!=0)
                self.assertEqual(x[~e].tobytes(),w[4:8][~e].tobytes())
                self.assertEqual(abs(x[e]).tobytes(),abs(w[:4][e]).tobytes())
            np.testing.assert_array_equal(np.signbit(m),np.signbit(w[4:8]))
            self.assertEqual(j[e].tobytes(),w[:4][e].tobytes())
            d,k=model.coupling(model.base.decode(result))
            self.assertEqual(d[:4].tobytes(),d[4:].tobytes());self.assertEqual(abs(k[:4]).tobytes(),abs(k[4:]).tobytes())
        w=np.zeros((9,4,1,2,16,16));w[:4]=-0.;e[:]=True
        result=model.components(model.base.encode(w),e)
        self.assertEqual(result.tobytes(),audit_model.components(model.base.encode(w),e).tobytes())
        z=model.base.decode(result);self.assertFalse(np.signbit(z[:4]).any());self.assertTrue(np.signbit(z[4:]).all())

    def test_support_mismatch_rejected_by_both_constructors(self):
        packets,e=self.synthetic();w=model.base.decode(packets);w[4,0,0,0,0,0]=0.
        for construct in (model.components,audit_model.components):
            with self.assertRaisesRegex(AssertionError,'Selected support mismatch'):construct(model.base.encode(w),e)

    def test_empty_or_injured_component_selections_alias_readers(self):
        cfg=settings('fixture')['reader'].copy();cfg['recipients']=1
        packets,e=self.synthetic(0)
        for injured in (False,True):
            if injured:
                absent=~model.reader.surviving_edges(model.masks(990077,1,'terminal_injury'))
                e[:]=np.broadcast_to(absent,e.shape)
            comp=model.components(packets,e)
            p=np.concatenate((packets[4:8],comp))
            fresh=model.develop(p,990077,cfg,cfg,'terminal')
            data.equal(fresh,audit_model.develop(p,990077,cfg,cfg,'terminal'))
            for start in (4,8):self.assertEqual(fresh['end'][:4].tobytes(),fresh['end'][start:start+4].tobytes())

    def test_exact_zero_fallback_pruning_and_no_repeat_pruning(self):
        state=np.full((1,4,1,2,16,16),.1);available=np.ones((4,1,2,16,16),bool)
        for skew in (0.,1e-5):
            state[...,1,:,:]=.1+skew
            a=model.capture(state,available,3.);b=audit_model.capture(state,available,3.)
            for x,y in zip(a,b,strict=True):self.assertEqual(x.tobytes(),y.tobytes())
            self.assertEqual(bool(a[3].all()),skew==0)
        cfg=settings('fixture');w=np.zeros((5,4,2,2,16,16))
        outgoing=np.ones_like(w)*.1;outgoing[4]=0.
        source=dict(incoming=model.base.encode(w),outgoing=model.base.encode(outgoing),fallback=np.ones_like(w,bool))
        inter=model.intervene(source);data.equal(inter,audit_model.intervene(source))
        self.assertFalse(model.base.decode(inter['packets'][4:8]).any())
        raw=model.rebuild(inter['packets'],990077,1,cfg['config'],cfg['cycle'])
        data.equal(raw,audit_model.rebuild(inter['packets'],990077,1,cfg['config'],cfg['cycle']))
        self.assertTrue(model.base.decode(raw['outgoing'][4:8]).any())

    def test_score_strict_threshold_and_zero_touching_intervals(self):
        v=np.zeros((26,4,1,2,2))
        for f,rule in enumerate((1,-1,1,-1)):
            for c,cue in enumerate((1,-1)):v[:,f,0,c]=(rule*cue*.25,-rule*cue*.25)
        self.assertFalse(model.score(v,.25)['both'].any())
        self.assertTrue(model.score(v*1.01,.25)['both'].all())
        for x in (v,v*1.01,-v,v*0.):data.equal(model.score(x,.25),audit_model.score(x,.25))
        for bounds in ((0.,.1),(-.1,0.)):self.assertEqual(inference.classification(bounds),'UNRESOLVED')

    def test_all_81_direction_combinations_and_scientific_suppression(self):
        for labels in itertools.product(('NEGATIVE_EFFECT','UNRESOLVED','POSITIVE_EFFECT'),repeat=4):
            d=dict(zip(PRIMARY,labels,strict=True));value=inference.verdict('scientific',True,d)
            if labels==PREDICTED:self.assertEqual(value,'FRESH_TRADEOFF_AND_COMPATIBILITY_CONFIRMED')
            elif any(a not in (b,'UNRESOLVED') for a,b in zip(labels,PREDICTED,strict=True)):
                self.assertEqual(value,'PREDICTED_PATTERN_CONTRADICTED')
            else:self.assertEqual(value,'PREDICTED_PATTERN_UNRESOLVED')
        # Four directional effects on a feasible common set of binary case arrays.
        x=np.zeros((26,4,1),bool);x[6:8]=True;x[11:13]=True;x[15:17,:2]=True;x[24:26]=True
        cases=[dict(both=x)]*2;controls=[{'pass':True}]*2
        summary=inference.analyze(cases,controls,'scientific');inference.audit(cases,controls,summary,'scientific')
        self.assertTrue(summary['prediction_supported'])
        self.assertEqual([summary['statistics']['effect/both/pooled/'+k]['mean'] for k in PRIMARY],[1.,-.5,-.5,.5])
        for mode,ok in (('fixture',True),('benchmark',True),('scientific',False)):
            c=[{'pass':ok}]*2;s=inference.analyze(cases,c,mode);inference.audit(cases,c,s,mode)
            self.assertIsNone(s['prediction_supported']);self.assertTrue(all(v is None for v in s['primary_effects'].values()))

    def test_block_weighting_and_individual_harms_do_not_disappear_in_averages(self):
        g=np.random.default_rng(77002);cases=[]
        for _ in range(3):
            ports=g.normal(size=(26,4,2,2,2))
            # Guarantee a known harm; a random sample need not contain one.
            ports[2,0,0]=np.array([[1.,-1.],[-1.,1.]])
            ports[6,0,0]=0.
            cases.append(model.score(ports,.25))
        s=inference.analyze(cases,[{'pass':True}]*3,'scientific');inference.audit(cases,[{'pass':True}]*3,s,'scientific')
        expected=[float(c['both'][6:8].mean()-c['both'][2:4].mean()) for c in cases]
        self.assertEqual(s['statistics']['effect/both/pooled/'+PRIMARY[0]]['block_means'],expected)
        rows=individuals.rows_for([1,2,3],cases);counts=individuals.summarize(rows)
        individuals.audit(rows,counts,[1,2,3],cases,s)
        q=counts['mixture_pooled'];self.assertEqual(sum(map(sum,q['h0_rows_h1_columns'])),48)
        self.assertGreater(q['harmed_at_either_endpoint'],0)
        # Deliberate missing-harm corruption must be rejected.
        q['comparisons']['joint_h1']['lost']+=1
        with self.assertRaises(AssertionError):individuals.audit(rows,counts,[1,2,3],cases,s)


if __name__=='__main__':unittest.main()
