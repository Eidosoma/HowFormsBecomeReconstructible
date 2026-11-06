"""Scientific-interface checks on excluded sources and analytic fixtures."""
import json,time,traceback
from dataclasses import replace
import numpy as np
from common import dump,sha,utc
from E122_specificity_ceiling_and_tail import sources,dynamics,audit,statistics,experiment,inference
from E122_specificity_ceiling_and_tail.plan import ROOT,HERE,CFG,BENCHMARK,CHECKPOINTS,settings

def run(paths):
    out=HERE/'analysis';out.mkdir(exist_ok=True)
    attempt=len(list(out.glob('tests_attempt_*.json')))+1;path=out/f'tests_attempt_{attempt:03d}.json'
    tick=time.monotonic();passed=[];timings=[]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in paths}
    try:
        sources.verify('benchmark')
        for factor in (1,4):
            old=sources.load('benchmark',BENCHMARK,factor);p=old['incoming'][0,:,:,:2].copy()
            for g in (1,2,3):
                t=time.monotonic();p,body=dynamics.generation(p,BENCHMARK,g,factor);timings.append(time.monotonic()-t)
                np.testing.assert_array_equal(p,old['outgoing'][g-1,:,:,:2])
                for name in ('read','written'):np.testing.assert_array_equal(body[name],old['generation_'+name][g-1,:,:,:2])
            p,body=dynamics.generation(old['incoming'][15,:,:,:2],BENCHMARK,16,factor)
            np.testing.assert_array_equal(p,old['outgoing'][15,:,:,:2])
            q,detail=audit.generation(old['outgoing'][15,:,:,:2],BENCHMARK,17,factor)
            r,result=dynamics.generation(old['outgoing'][15,:,:,:2],BENCHMARK,17,factor)
            np.testing.assert_array_equal(q,r);audit.compare(detail,result)
            passed.append(f'factor_{factor}_legacy_first_three_and_16_exact_and_independent_17')
            protected=old['incoming'][0][:,:,[7,1]]
            for f in range(4):np.testing.assert_array_equal(protected[f,:,1],protected[(f+1)%4,:,0])
            panel=np.concatenate((p,protected),axis=2);before=panel.tobytes()
            state,birth,mask=dynamics.read(panel,BENCHMARK,'terminal',factor)
            replay=audit.read(panel,BENCHMARK,'terminal',factor)
            for a,b in zip((state,birth,mask),replay):np.testing.assert_array_equal(a,b)
            np.testing.assert_array_equal(state[:,:,:3],old['checkpoint_read'][-1][:,:,[0,1,7]])
            assert before==panel.tobytes()
            counts=dynamics.counts(state,old['prototype']);audit.counts(state,old['prototype'],counts)
            pair=dynamics.pair_counts(state,old['prototype'])
            for f,r in np.ndindex(4,2):
                v=counts[f,r,:,f]
                metrics=(v[:,1,1],v[:,1,:].sum(axis=-1),v[:,:,1].sum(axis=-1))
                for j,(a,b) in enumerate(((0,1),(2,3))):
                    for k,x in enumerate(metrics):assert int(x[a])-int(x[b])==int(pair[f,r,j,k,0])-int(pair[f,r,j,k,1])
            passed.append(f'factor_{factor}_protected_donor_and_terminal_projection_nonfeedback_counts')
        v=np.zeros((4,2,4,3,16,16));v[:,:,:,0,:,0]=.2;v[:,:,:,0,:,1]=np.nextafter(.2,1.)
        counts=dynamics.counts(v,np.ones((4,16,16)));audit.counts(v,np.ones((4,16,16)),counts)
        assert (counts[...,1,1]==16).all() and (counts[...,1,:].sum(axis=-1)==32).all()
        passed.append('strict_amplitude_and_zero_sign_boundary')
        d=np.linspace(.9,1.1,64);n=.5*d
        f=statistics.fieller(n,d);assert f['kind']=='bounded' and abs(f['point']-.5)<1e-12
        for scale in (-.4,2.):
            f=statistics.fieller(scale*d,d);assert f['kind']=='bounded' and abs(f['point']-scale)<1e-12
        z=np.tile([-1.,1.],32);f=statistics.fieller(np.ones(64),z)
        assert f['point'] is None and f['kind']=='two_rays'
        f=statistics.fieller(np.zeros(64),z);assert f['kind']=='all_real'
        sensitivity,arr=statistics.ratio_bootstrap(np.ones(2),np.array([-1.,1.]),np.array([[0,0],[0,1],[1,1]]))
        assert sensitivity['zero_denominators']==1 and sensitivity['discarded_draws']==0 and sensitivity['percentile95'] is None
        assert np.isneginf(arr[0,2])==False and np.isinf(arr[1,2])
        passed.append('paired_fieller_bounded_signed_unbounded_and_no_denominator_dropping')
        cfg=settings('benchmark');g=np.array(CHECKPOINTS);tau=np.geomspace(*cfg['fit_tau_bounds'],cfg['fit_tau_points'])[100]
        for c in (-.012,.012):
            y=c+.02*np.exp(-g/tau);fit=statistics.fit_batch(y,g,'exponential_plateau',cfg)[0]
            np.testing.assert_allclose(fit[:3],[c,.02,tau],atol=1e-9,rtol=1e-9)
        y=.02*np.exp(-g/tau);fit=statistics.fit_batch(y,g,'exponential_zero',cfg)[0]
        np.testing.assert_allclose(statistics.predict(fit,g,'exponential_zero')[0],y,atol=1e-12)
        ptau=np.geomspace(*cfg['fit_tau_bounds'],cfg['power_tau_points'])[60];p=2.
        y=.02*(1+g/ptau)**(-p);fit=statistics.fit_batch(y,g,'power_zero',cfg)[0]
        np.testing.assert_allclose(statistics.predict(fit,g,'power_zero')[0],y,atol=1e-10)
        passed.append('signed_plateau_zero_asymptote_and_power_synthetic_recovery')
        fixture=out/f'interface_attempt_{attempt:03d}';fixture.mkdir(exist_ok=False)
        for factor in (1,4):experiment.factor('benchmark',BENCHMARK,factor,fixture,replace(CFG,read=3,write=4))
        small=dict(cfg,bootstrap_samples=100,fit_bootstrap_samples=20)
        summary=inference.analyze(fixture,small)
        assert not summary['primary']['scientific_claim_allowed'] and summary['independent_blocks']==1
        assert summary['technical_replication_for_cost_only']
        for factor in (1,4):
            with np.load(fixture/f'block_{BENCHMARK:06d}_factor_{factor}.npz') as z:
                assert z['boundary_packets'].shape==(241,4,2,2,2048//factor**2)
                np.testing.assert_array_equal(z['checkpoint_packet'][3,:,:,:2],z['boundary_packets'][0])
                np.testing.assert_array_equal(z['checkpoint_packet'][-1,:,:,:2],z['boundary_packets'][-1])
                assert z['checkpoint_state'].dtype==np.float64
        passed.append('complete_export_ratio_fit_and_plot_interface_short_dynamics_excluded_source')
        result=dict(status='PASS',utc=utc(),seconds=time.monotonic()-tick,checks=passed,
            inputs_sha256=hashes,registry_sha256=sha(HERE/'SOURCE_DATA.json'),
            full_generation_seconds=timings,technical_source=BENCHMARK,scientific_outcomes_inspected=False)
        dump(path,result);return path,result
    except BaseException:
        dump(path,dict(status='FAILED',utc=utc(),seconds=time.monotonic()-tick,checks_passed=passed,
            inputs_sha256=hashes,traceback=traceback.format_exc(),automatic_retry=False));raise
