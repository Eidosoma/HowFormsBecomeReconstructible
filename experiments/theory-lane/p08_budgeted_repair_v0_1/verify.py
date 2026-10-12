"""Recompute endpoints, bootstrap and every table without importing analysis."""
import csv
import numpy as np
from common import ROOT,arrays,read,write,sha,stamp,equal
from audit_serial import audit_block


def verify_diagnostics(a,panel,cfg):
    for vi,name in enumerate(cfg['variants']):
        expected={key:sum(int(d[key][:,vi].sum()) for d in panel.values())
            for key in ('available_edges','fallback_edges','returning_edges','returning_fallback_edges')}
        expected['fallback_fraction']=expected['fallback_edges']/expected['available_edges'] if expected['available_edges'] else None
        expected['returning_fallback_fraction']=expected['returning_fallback_edges']/expected['returning_edges'] if expected['returning_edges'] else None
        assert a['mechanism'][name]==expected
    for ni,name in enumerate(cfg['noise_regimes']):
        total=np.zeros(6)
        for d in panel.values():
            for generation in d['noise_moments']:total+=generation[ni]
        p,m,pp,mm,pm,n=total;vp=pp/n-(p/n)**2;vm=mm/n-(m/n)**2
        expected=dict(mean_plus=p/n,mean_minus=m/n,variance_plus=vp,variance_minus=vm,
                      correlation=(pm/n-(p/n)*(m/n))/np.sqrt(vp*vm))
        got=a['noise_diagnostics'][name]
        assert got['draws']==int(n) and got['target_correlation']==cfg['correlations'][ni]
        for key,value in expected.items():assert abs(got[key]-value)<=1e-12,key


def check_summary(s,values,cfg):
    values=np.asarray(values,float)
    assert abs(s['mean']-float(sum(values)/16))<=1e-14
    assert s['by_block']==dict(zip(map(str,cfg['blocks']),map(float,values)))
    assert [s['positive_blocks'],s['tied_blocks'],s['negative_blocks']]==[
        sum(v>0 for v in values),sum(v==0 for v in values),sum(v<0 for v in values)]
    rng=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    totals=np.zeros(cfg['bootstrap_replicates'])
    for h in range(4):
        pool=[i for i,b in enumerate(cfg['blocks']) if cfg['history_by_block'][str(b)]==h]
        indices=rng.integers(0,4,(cfg['bootstrap_replicates'],4))
        for j in range(4):totals+=values[np.array(pool)[indices[:,j]]]
    expected=np.quantile(totals/16,[.025,.975])
    np.testing.assert_allclose(s['descriptive_stratified_block_bootstrap_95'],expected,rtol=0,atol=1e-14)


def independent_endpoints(good,opposite):
    out={k:np.zeros((4,16)) for k in ('uninterrupted','terminal','ever_recovered','terminal_after_failure',
        'mean_cycle_success','initial_success_run','ever_opposite','terminal_opposite','first_pass','first_pass_then_later_failure')}
    for v in range(4):
        for case in range(16):
            x=[bool(t[v,case]) for t in good];y=[bool(t[v,case]) for t in opposite]
            first=next((i for i,passed in enumerate(x) if not passed),len(x))
            out['uninterrupted'][v,case]=all(x);out['terminal'][v,case]=x[-1]
            out['ever_recovered'][v,case]=any((not x[i-1]) and x[i] for i in range(1,len(x)))
            out['terminal_after_failure'][v,case]=x[-1] and not all(x[:-1])
            out['mean_cycle_success'][v,case]=sum(x)/len(x)
            out['initial_success_run'][v,case]=first
            out['ever_opposite'][v,case]=any(y);out['terminal_opposite'][v,case]=y[-1]
            out['first_pass'][v,case]=x[0]
            out['first_pass_then_later_failure'][v,case]=x[0] and any(not z for z in x[1:])
    return out


def verify(folder,cfg,scientific=True):
    a=read(folder/'analysis.json')
    assert a['status']=='BUDGETED_REPAIR_ANALYZED' and a['blocks']==16 and a['records']==256
    assert a['read_contexts']==18432 and a['fitted_parameters']==7
    assert (a['simulated_read_contexts'],a['reused_control_contexts'],a['new_continuation_contexts'])==(18432,0,18432)
    panel={};ep={};counts=dict(independent_captures=0,independent_repair_constructions=0,new_independent_optimizer_checks=0,native_audit_contexts=0,independent_noise_checks=0,independent_policy_decisions=0)
    model=read(ROOT/'development/MODEL.json')
    for bi,b in enumerate(cfg['blocks']):
        d=arrays(folder/f'continuation_{b:06d}.npz');panel[b]=d
        assert int(d['block'])==b and int(d['history'])==cfg['history_by_block'][str(b)]
        means=d['port_windows'].mean(axis=1);equal(means,d['mean_ports'],'raw window means')
        intended=np.zeros((18,4,16),bool);opposite=np.zeros_like(intended)
        mm=np.zeros(intended.shape);om=np.zeros(intended.shape)
        for gi in range(18):
            for v in range(4):
                for case in range(16):
                    rule=1. if (case//4)%2==0 else -1.
                    mu=means[gi,v,case]
                    margins=[rule*mu[0,0],-rule*mu[0,1],-rule*mu[1,0],rule*mu[1,1]]
                    mm[gi,v,case]=min(margins);om[gi,v,case]=-max(margins)
                    intended[gi,v,case]=min(margins)>.25
                    opposite[gi,v,case]=-max(margins)>.25
        for key,expected in [('both_pass',intended),('opposite_pass',opposite),('min_margin',mm),('opposite_margin',om)]:
            np.testing.assert_array_equal(d[key],expected,err_msg='independent scores '+key)
        assert not (intended&opposite).any()
        ep[b]=independent_endpoints(intended,opposite)
        if scientific:
            receipt=read(folder/f'worker_{b:06d}.json')
            assert receipt['status']=='COMPLETE' and receipt['records']==16 and not receipt['selected_on_outcome']
            assert receipt['continuation_sha256']==sha(folder/f'continuation_{b:06d}.npz')
            from audit_cohort import check_lineage
            from audit_serial import masks
            acquisition=arrays(folder/f'acquisition_{b:06d}.npz',receipt['acquisition_sha256'])
            lineage=arrays(folder/f'lineage_{b:06d}.npz',receipt['lineage_sha256'])
            check_lineage(acquisition,lineage,b,cfg,dynamics=True)
            for gi in range(14):
                equal(lineage['masks'][gi],masks(cfg['lineage_namespace']+':'+str(b),gi+1),'independent history injury')
            got=audit_block(d,lineage['outgoing'][-1],lineage['masks'][-1],b,cfg,model)
            assert receipt['independent_optimizer_checks']==720==got['new_independent_optimizer_checks']
            assert got['independent_repair_constructions']==720
            for key,val in got.items():counts[key]+=val
    for vi,name in enumerate(cfg['variants']):
        for metric in ep[cfg['blocks'][0]]:
            check_summary(a['rates'][name][metric],[ep[b][metric][vi].mean() for b in cfg['blocks']],cfg)
        for gi,g in enumerate(cfg['generations']):
            expected=dict(generation=g,
                success=float(sum(d['both_pass'][gi,vi].mean() for d in panel.values())/16),
                uninterrupted=float(sum(d['both_pass'][:gi+1,vi].all(axis=0).mean() for d in panel.values())/16),
                opposite=float(sum(d['opposite_pass'][gi,vi].mean() for d in panel.values())/16))
            assert a['curves'][name][gi]==expected
        resources=a['resources'][name]
        assert resources['repair_calls']==sum(int(d['applied'][:,vi].sum()) for d in panel.values())
        for k in ('added_edges','added_abs_weight','repair_cpu_seconds','audit_cpu_seconds','diagnostic_cpu_seconds'):
            assert resources[k]==float(sum(d[k][:,vi].sum() for d in panel.values()))
        assert resources['added_edges_per_lineage']==resources['added_edges']/256
        assert resources['record_bytes_per_boundary']==4096 and resources['read_updates_per_lineage']==36864
        assert resources['optimizer_starts_per_call']==16 and resources['maximum_sweeps_per_call']==64
        assert resources['execution_origin']=='current_run'
        for hi,h in enumerate(cfg['histories']):
            blocks=[b for b in cfg['blocks'] if cfg['history_by_block'][str(b)]==hi]
            for metric in ('uninterrupted','terminal'):
                assert a['history_summaries'][h][name][metric]==float(sum(ep[b][metric][vi].mean() for b in blocks)/4)
    for label,coefs in cfg['contrasts'].items():
        for metric in ('uninterrupted','terminal'):
            values=[sum(float(coefs[v])*ep[b][metric][v,case] for v in range(4) for case in range(16))/16 for b in cfg['blocks']]
            check_summary(a['contrasts'][label][metric],values,cfg)
    for label,(left,right) in cfg['comparison_pairs'].items():
        for metric in ('uninterrupted','terminal'):
            buckets=[0,0,0,0]
            for b in cfg['blocks']:
                for case in range(16):
                    l=bool(ep[b][metric][left,case]);r=bool(ep[b][metric][right,case])
                    buckets[0 if l and not r else 1 if r and not l else 2 if l else 3]+=1
            assert a['paired_counts'][label][metric]==dict(zip(('left_only','right_only','both','neither'),buckets),lineages=256,left=cfg['variants'][left],right=cfg['variants'][right])
    assert a['primary_direction_observed']==(a['contrasts'][cfg['primary_contrast']]['uninterrupted']['mean']>0)
    verify_diagnostics(a,panel,cfg)
    assert a['renewal_cpu_seconds']==float(sum(d['renewal_cpu_seconds'].sum() for d in panel.values()))
    assert a['warning_policy']==dict(diagnostic_calls=4352,linear_transfer_updates_per_call=64,
        reason_counts={str(i):sum(int((d['warning_reason']==i).sum()) for d in panel.values()) for i in (1,2,3,4)},
        repair_calls_by_generation={str(g):sum(int(d['applied'][gi,0].sum()) for d in panel.values()) for gi,g in enumerate(cfg['generations'])},
        apparatus_numeric_bytes=(19+len(model['calibration_sorted_scores']))*8)
    for filename in ('reads.csv','resources.csv','block_summaries.csv'):
        with (folder/filename).open(newline='') as f:rows=list(csv.DictReader(f))
        expected_count=64 if filename=='block_summaries.csv' else 18432
        assert len(rows)==expected_count;seen=set()
        for row in rows:
            b=int(row['block']);v=cfg['variants'].index(row['variant']);d=panel[b]
            if filename=='block_summaries.csv':
                key=(b,v);assert int(row['history'])==cfg['history_by_block'][str(b)]
                for metric in ep[b]:assert float(row[metric])==ep[b][metric][v].mean()
            else:
                gi=cfg['generations'].index(int(row['generation']));case=int(row['case']);key=(b,gi,v,case)
                assert 0<=case<16
                if filename=='reads.csv':
                    for column,array in [('intended','both_pass'),('opposite','opposite_pass'),
                                         ('min_margin','min_margin'),('opposite_margin','opposite_margin')]:
                        assert float(row[column])==float(d[array][gi,v,case])
                    assert int(row['uninterrupted_so_far'])==int(d['both_pass'][:gi+1,v,case].all())
                else:
                    for column,array in [('repair_call','applied'),('missing_edges','missing_edges'),('added_edges','added_edges'),
                        ('added_abs_weight','added_abs_weight'),('imputed_magnitude','magnitude'),
                        ('repair_cpu_seconds','repair_cpu_seconds'),('audit_cpu_seconds','audit_cpu_seconds'),('diagnostic_cpu_seconds','diagnostic_cpu_seconds')]:
                        assert float(row[column])==float(d[array][gi,v,case])
                    assert int(row['record_bytes'])==4096
            assert key not in seen;seen.add(key)
    if scientific:
        assert counts==dict(independent_captures=18432,independent_repair_constructions=11520,new_independent_optimizer_checks=11520,native_audit_contexts=256,independent_noise_checks=288,independent_policy_decisions=18432)
    result=dict(status='PASS',at_utc=stamp(),scientific=scientific,records=256,read_contexts=18432,
        **counts,independent_optimizer_checks_during_preparation=11520 if scientific else 0,
        analysis_module_imported=False,primary_renewal_module_imported=False,
        independent_damage_masks=bool(scientific),same_lane_internal_verification=True,
        files_sha256={p.name:sha(p) for p in sorted(folder.iterdir()) if p.suffix in ('.npz','.csv')})
    if not (folder/'VERIFICATION.json').exists():write(folder/'VERIFICATION.json',result)
    return result
