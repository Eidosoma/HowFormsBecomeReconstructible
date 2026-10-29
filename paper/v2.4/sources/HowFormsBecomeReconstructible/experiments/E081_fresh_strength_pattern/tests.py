"""Scientific parity, intervention identities, endpoint harms and signed inference."""
import inspect
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from common import rng
from E081_fresh_strength_pattern import model,audit_model,data,inference,individuals
from E081_fresh_strength_pattern.plan import HERE,settings,PRIMARY,PREDICTED


def legacy_projection_check(source_inter,source,inter,comp,packets,block,cfg,raw,fresh):
    from E077_fresh_reconstruction_tradeoff import model as previous
    from E080_strength_allocation import model as allocation
    def remap(tag,*parts):
        assert tag=='E077';return rng('E081',*parts)
    with patch.object(previous,'rng',side_effect=remap):
        old_source=previous.rebuild(source_inter['packets'],block,0,cfg['config'],cfg['source_recovery_cycle'])
        old=previous.rebuild(inter['packets'],block,1,cfg['config'],cfg['cycle'])
        read=previous.develop(packets,block,cfg['reader'],cfg['reader'],'terminal')
    data.equal(source,old_source);data.equal(inter,previous.intervene(source))
    data.equal(raw,old);data.equal(fresh,read)
    o=model.base.decode(comp['ordinary_packets']);f=model.base.decode(comp['filtered_packets'])
    a=allocation.allocate(o,f,inter['eligible'],cfg)
    assert comp['packets'].tobytes()==model.base.encode(a['weights'][8:]).tobytes()
    for name in ('ordinary_total','filtered_total'):assert comp[name].tobytes()==a[name].tobytes()
    for name in ('scales','target_totals'):assert comp[name].tobytes()==a[name][8:].tobytes()
    c=allocation.capture(raw['end'],model.reader.surviving_edges(raw['masks']),cfg['config']['writer_beta'])
    assert c['captured'].tobytes()==model.base.decode(raw['outgoing']).tobytes()
    for a,b in (('capture_ordinary','ordinary'),('capture_contrast','contrast'),('capture_fallback','fallback')):
        assert c[a].tobytes()==raw[b].tobytes()
    projected=dict(fresh)
    for key in ('mean_ports','denominator','coupling','boundary_counts'):projected[key]=fresh[key][:18]
    from E073_saved_cohort_reversal_replication import model as endpoints
    old_cases,old_records,old_transition=endpoints.diagnostics(packets[:18],inter,projected,raw,cfg['reader'])
    cases,records,transition=model.diagnostics(packets,inter,fresh,raw,cfg['reader'])
    data.equal(old_cases,{k:cases[k][:18] for k in old_cases})
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
        comp=model.components(raw,inter['eligible'],cfg)
        data.equal(comp,audit_model.components(raw,inter['eligible'],cfg))
        packets=np.concatenate((inter['packets'],raw['outgoing'],comp['packets']))
        fresh=model.develop(packets,900041,cfg['reader'],cfg['reader'],'terminal')
        data.equal(fresh,audit_model.develop(packets,900041,cfg['reader'],cfg['reader'],'terminal'))
        return cfg,source_inter,source,inter,raw,comp,packets,fresh

    def test_new_sources_unchanged_settings_and_exact_equations(self):
        from E068_fresh_recovery_confirmation.plan import settings as old_source
        from E073_saved_cohort_reversal_replication.plan import settings as old_settings
        from E077_fresh_reconstruction_tradeoff import model as old,audit_model as old_audit
        for mode in ('fixture','benchmark','scientific'):
            cfg=settings(mode);prev=old_settings(mode);source=old_source(mode)
            for k in ('config','cycle','reader','recipients'):self.assertEqual(cfg[k],prev[k])
            for k in ('source_config','source_cycle','body','source_continuation'):self.assertEqual(cfg[k],source[k])
            self.assertEqual(cfg['source_recovery_cycle'],source['cycle'])
        for current,previous,functions in (
            (model,old,('intervene','digest','masks','coupling','develop','capture','rebuild','score')),
            (audit_model,old_audit,('intervene','digest','masks','alive','coupling','develop','capture','rebuild','score'))):
            for name in functions:
                self.assertEqual(inspect.getsource(getattr(current,name)),inspect.getsource(getattr(previous,name)).replace("'E077'","'E081'"))
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
        self.assertEqual(comp['packets'].shape[0],8);self.assertEqual(packets.shape[0],26)
        for group in (slice(18,22),slice(22,26)):
            np.testing.assert_allclose(cases['selected_mass'][group],comp['filtered_total'],rtol=2e-14,atol=0.)
        w=model.base.decode(comp['packets']);original=model.base.decode(raw['outgoing'])
        e=inter['eligible']
        np.testing.assert_array_equal(w[:4]!=0,w[4:]!=0)
        np.testing.assert_array_equal(np.signbit(w[:4]),np.signbit(w[4:]))
        for group in (w[:4],w[4:]):self.assertEqual(group[~e].tobytes(),original[4:8][~e].tobytes())
        self.assertEqual(comp['packets'][4:].tobytes(),comp['filtered_packets'].tobytes())

    def arrays(self):
        o=np.zeros((4,4,1,2,16,16));f=o.copy();e=np.zeros_like(o,bool)
        o[...,0,0,:4]=[3.,-1.,.25,-0.];f[:]=o;f[...,0,0,0]=.5;f[...,0,0,1]=-1.5;f[...,0,0,3]=0.
        e[...,0,0,:2]=True;e[...,0,0,3]=True
        return o,f,e,settings('fixture')

    def allocation(self,o,f,e,cfg):
        a=model.allocate(o,f,e,cfg);data.equal(a,audit_model.allocate(o,f,e,cfg));return a

    def test_exact_matched_total_pattern_and_E080_projection(self):
        from E080_strength_allocation import model as previous
        o,f,e,cfg=self.arrays();a=self.allocation(o,f,e,cfg);w=a['weights']
        for start,values in ((0,(1.5,-.5)),(4,(.5,-1.5))):
            g=w[start:start+4]
            np.testing.assert_array_equal(g[...,0,0,:2],np.broadcast_to(values,g[...,0,0,:2].shape))
            self.assertEqual(g[~e].tobytes(),o[~e].tobytes())
            np.testing.assert_array_equal(np.signbit(g),np.signbit(o));np.testing.assert_array_equal(g!=0,o!=0)
            np.testing.assert_array_equal(np.where(e,abs(g),0.).sum(axis=(-3,-2,-1)),2.)
        old=previous.allocate(o,f,e,cfg)
        for k in ('weights','scales','target_totals'):self.assertEqual(a[k].tobytes(),old[k][8:].tobytes())
        for k in ('ordinary_total','filtered_total'):self.assertEqual(a[k].tobytes(),old[k].tobytes())
        d,k=model.coupling(w);self.assertFalse(np.array_equal(d[:4],d[4:]))
        alive=np.ones_like(w,bool);alive[...,0,0,0]=False
        after=np.where(np.concatenate((e,e)),abs(w*alive),0.).sum(axis=(-3,-2,-1))
        np.testing.assert_array_equal(after[:4],.5);np.testing.assert_array_equal(after[4:],1.5)

    def test_zero_tiny_proportional_and_unbounded_scaling(self):
        o,f,e,cfg=self.arrays();o[e]=-0.;f[e]=0.;a=self.allocation(o,f,e,cfg)
        np.testing.assert_array_equal(a['scales'],1.);np.testing.assert_array_equal(a['target_totals'],0.)
        self.assertTrue(np.signbit(a['weights'][:4][e]).all())
        tiny=np.nextafter(0.,1.)
        o[...,0,0,:2]=[tiny,-3*tiny];f[...,0,0,:2]=[2*tiny,-2*tiny]
        self.assertTrue((self.allocation(o,f,e,cfg)['target_totals']>0).all())
        o,f,e,cfg=self.arrays();f[e]=o[e]/2;a=self.allocation(o,f,e,cfg)
        self.assertEqual(a['weights'][:4].tobytes(),a['weights'][4:].tobytes())
        o,f,e,cfg=self.arrays();o[...,0,0,:2]=[.99,-.01];f[...,0,0,:2]=[.9,-.9]
        a=self.allocation(o,f,e,cfg);self.assertGreater(abs(a['weights'][:4]).max(),1.)
        np.testing.assert_allclose(np.where(np.concatenate((e,e)),abs(a['weights']),0.).sum(axis=(-3,-2,-1)),a['target_totals'],rtol=2e-14,atol=0.)

    def test_support_and_numerical_failure_no_cases_dropped(self):
        for module in (model,audit_model):
            o,f,e,cfg=self.arrays();f[...,0,0,0]=0.
            with self.assertRaisesRegex(AssertionError,'Selected support mismatch'):module.allocate(o,f,e,cfg)
            o,f,e,cfg=self.arrays();o[...,0,0,:2]=[1.,-np.nextafter(0.,1.)];f[...,0,0,:2]=[1e-100,-1e-100]
            with self.assertRaisesRegex(AssertionError,'Scaled support mismatch'):module.allocate(o,f,e,cfg)
            o,f,e,cfg=self.arrays();f[...,0,0,0]=np.inf
            with self.assertRaisesRegex(AssertionError,'Nonfinite donor'):module.allocate(o,f,e,cfg)

    def test_empty_and_injured_selections_alias(self):
        o,f,e,cfg=self.arrays();reader_cfg=dict(cfg['reader'],recipients=1)
        for injured in (False,True):
            if injured:e[:]=np.broadcast_to(~model.reader.surviving_edges(model.masks(990081,1,'terminal_injury')),e.shape)
            else:e[:]=False
            a=self.allocation(o,f,e,cfg);packets=model.base.encode(a['weights'])
            fresh=model.develop(packets,990081,reader_cfg,reader_cfg,'terminal')
            data.equal(fresh,audit_model.develop(packets,990081,reader_cfg,reader_cfg,'terminal'))
            self.assertEqual(fresh['end'][:4].tobytes(),fresh['end'][4:].tobytes())

    def test_failed_construction_preserves_available_endpoints(self):
        from E081_fresh_strength_pattern import run,sources
        cfg=settings('fixture');ancestry=data.technical_source('fixture')
        with tempfile.TemporaryDirectory(dir=HERE/'analysis',prefix='failed_construction_') as path:
            path=Path(path)
            with patch.object(sources,'generate',return_value=(ancestry,{},{})),patch.object(model,'components',side_effect=AssertionError('Injected total check failure')):
                with self.assertRaisesRegex(AssertionError,'Injected total check failure'):run.block(path,900041,cfg)
            receipt=json.loads((path/'component_failure_900041.json').read_text())
            self.assertIsNone(receipt['prediction_supported']);self.assertTrue(receipt['no_cases_dropped'])
            self.assertEqual(receipt['available_endpoint_slots'],18)
            available=data.load(path/'available_cases_900041.npz')
            self.assertEqual(available['both'].shape,(18,4,cfg['recipients']))
            self.assertFalse((path/'components_900041.npz').exists())

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

    def test_all_nine_binary_pairs_and_scientific_suppression(self):
        for ordinary,filtered in itertools.product((0.,.5,1.),repeat=2):
            x=np.zeros((26,4,1),bool)
            x[20:22,:int(ordinary*4)]=True;x[24:26,:int(filtered*4)]=True
            cases=[dict(both=x)]*2;controls=[{'pass':True}]*2
            s=inference.analyze(cases,controls,'scientific');inference.audit(cases,controls,s,'scientific')
            value=filtered-ordinary;label='POSITIVE_EFFECT' if value>0 else 'NEGATIVE_EFFECT' if value<0 else 'UNRESOLVED'
            self.assertEqual(s['primary_effects'],{'mixture_pattern_gain':label})
            self.assertEqual(s['prediction_supported'],filtered>ordinary)
            self.assertEqual(s['statistics']['effect/both/pooled/mixture_pattern_gain']['mean'],value)
            self.assertEqual(s['primary_family_size'],1);self.assertEqual(s['primary_confidence'],.95)
            for mode,ok in (('fixture',True),('benchmark',True),('scientific',False)):
                c=[{'pass':ok}]*2;q=inference.analyze(cases,c,mode);inference.audit(cases,c,q,mode)
                self.assertIsNone(q['prediction_supported']);self.assertTrue(all(v is None for v in q['primary_effects'].values()))

    def test_block_weighting_and_individual_harms_do_not_disappear_in_averages(self):
        g=np.random.default_rng(81002);cases=[]
        for _ in range(3):
            ports=g.normal(size=(26,4,2,2,2))
            # Guarantee a known harm; a random sample need not contain one.
            ports[2,0,0]=np.array([[1.,-1.],[-1.,1.]])
            ports[6,0,0]=0.
            cases.append(model.score(ports,.25))
        s=inference.analyze(cases,[{'pass':True}]*3,'scientific');inference.audit(cases,[{'pass':True}]*3,s,'scientific')
        expected=[float(c['both'][6:8].mean()-c['both'][2:4].mean()) for c in cases]
        self.assertEqual(s['statistics']['effect/both/pooled/'+'mixture_pruning_h0']['block_means'],expected)
        rows=individuals.rows_for([1,2,3],cases);counts=individuals.summarize(rows)
        individuals.audit(rows,counts,[1,2,3],cases,s)
        q=counts['mixture_pooled'];self.assertEqual(sum(map(sum,q['h0_rows_h1_columns'])),48)
        self.assertGreater(q['harmed_at_either_endpoint'],0)
        # Deliberate missing-harm corruption must be rejected.
        q['comparisons']['pattern_gain']['lost']+=1
        with self.assertRaises(AssertionError):individuals.audit(rows,counts,[1,2,3],cases,s)


if __name__=='__main__':unittest.main()
