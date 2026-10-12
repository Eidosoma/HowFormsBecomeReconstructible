"""Recompute endpoints, bootstrap and every table without importing analysis."""
import csv
import numpy as np
from common import ROOT,arrays,read,write,sha,stamp,equal
from audit_serial import audit_block


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
        'mean_cycle_success','initial_success_run','ever_opposite','terminal_opposite')}
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
    return out


def verify(folder,cfg,scientific=True):
    a=read(folder/'analysis.json')
    assert a['status']=='EXPOSED_COHORT_CONTINUATION_ANALYZED' and a['blocks']==16 and a['records']==256
    assert a['read_contexts']==18432 and a['fitted_parameters']==0
    panel={};ep={};counts=dict(independent_captures=0,independent_repair_constructions=0,native_audit_contexts=0)
    source=arrays(ROOT/'sources/boundaries.npz') if scientific else None
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
            got=audit_block(d,source['initial_packets'][bi],b,cfg)
            assert receipt['independent_optimizer_checks']==592==got['independent_repair_constructions']
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
        for k in ('added_edges','added_abs_weight','repair_cpu_seconds','audit_cpu_seconds'):
            assert resources[k]==float(sum(d[k][:,vi].sum() for d in panel.values()))
        assert resources['added_edges_per_lineage']==resources['added_edges']/256
        assert resources['record_bytes_per_boundary']==4096 and resources['read_updates_per_lineage']==36864
        assert resources['optimizer_starts_per_call']==16 and resources['maximum_sweeps_per_call']==64
        for hi,h in enumerate(cfg['histories']):
            blocks=[b for b in cfg['blocks'] if cfg['history_by_block'][str(b)]==hi]
            for metric in ('uninterrupted','terminal'):
                assert a['history_summaries'][h][name][metric]==float(sum(ep[b][metric][vi].mean() for b in blocks)/4)
    for label,left,right in [('repeated_minus_baseline',2,0),('one_time_minus_baseline',1,0),
                             ('repeated_minus_one_time',2,1),('repeated_minus_shuffled',2,3)]:
        for metric in ('uninterrupted','terminal'):
            values=[(ep[b][metric][left]-ep[b][metric][right]).mean() for b in cfg['blocks']]
            check_summary(a['contrasts'][label][metric],values,cfg)
    for metric in ('uninterrupted','terminal'):
        buckets=[0,0,0,0]
        for b in cfg['blocks']:
            for case in range(16):
                l=bool(ep[b][metric][2,case]);r=bool(ep[b][metric][0,case])
                buckets[0 if l and not r else 1 if r and not l else 2 if l else 3]+=1
        assert a['paired_counts'][metric]==dict(zip(('repeated_only','baseline_only','both','neither'),buckets),lineages=256)
    assert a['primary_direction_observed']==(a['contrasts']['repeated_minus_baseline']['uninterrupted']['mean']>0)
    assert a['renewal_cpu_seconds']==float(sum(d['renewal_cpu_seconds'].sum() for d in panel.values()))
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
                        ('repair_cpu_seconds','repair_cpu_seconds'),('audit_cpu_seconds','audit_cpu_seconds')]:
                        assert float(row[column])==float(d[array][gi,v,case])
                    assert int(row['record_bytes'])==4096
            assert key not in seen;seen.add(key)
    if scientific:
        assert counts==dict(independent_captures=18432,independent_repair_constructions=9472,native_audit_contexts=32)
    result=dict(status='PASS',at_utc=stamp(),scientific=scientific,records=256,read_contexts=18432,
        **counts,independent_optimizer_checks_during_preparation=9472 if scientific else 0,
        analysis_module_imported=False,primary_renewal_module_imported=False,
        independent_damage_masks=bool(scientific),same_lane_internal_verification=True,
        files_sha256={p.name:sha(p) for p in sorted(folder.iterdir()) if p.suffix in ('.npz','.csv')})
    if not (folder/'VERIFICATION.json').exists():write(folder/'VERIFICATION.json',result)
    return result
