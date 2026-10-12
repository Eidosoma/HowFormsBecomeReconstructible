"""Separate raw-window scoring, tables and stratified inference; no analysis import."""
import csv
import numpy as np
from common import arrays,read,write,sha,stamp,equal


def close(actual,expected,label):
    assert abs(float(actual)-float(expected))<=1e-11*max(1.,abs(float(expected))),label


def resample(values,cfg):
    x=np.asarray(values,float);rng=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    out=np.zeros(cfg['bootstrap_replicates'])
    for h in range(4):
        pool=[i for i,b in enumerate(cfg['blocks']) if cfg['history_by_block'][str(b)]==h]
        choices=rng.integers(0,len(pool),(cfg['bootstrap_replicates'],len(pool)))
        for j in range(len(pool)):out+=x[np.array(pool)[choices[:,j]]]
    return out/len(cfg['blocks'])


def check_summary(saved,values,cfg,divisor=1):
    raw=list(map(float,values));draws=resample(raw,cfg)/divisor
    values=[x/divisor for x in raw]
    close(saved['mean'],sum(values)/len(values),'mean')
    assert set(saved['by_block'])==set(map(str,cfg['blocks']))
    for b,v in zip(cfg['blocks'],values):close(saved['by_block'][str(b)],v,'block value')
    for k,q in [('one_sided_95_lower',.05),('one_sided_95_upper',.95)]:close(saved[k],np.quantile(draws,q),k)
    np.testing.assert_allclose(saved['two_sided_95'],np.quantile(draws,[.025,.975]),rtol=0,atol=1e-12)
    assert [saved[k] for k in ('positive_blocks','tied_blocks','negative_blocks')]==[sum(x>0 for x in values),sum(x==0 for x in values),sum(x<0 for x in values)]


def csv_row(reader,expected):
    row=next(reader);assert set(row)==set(expected)
    for key,value in expected.items():
        if isinstance(value,str):assert row[key]==value,(key,row[key],value)
        else:close(row[key],value,key)


def verify(folder,cfg,scientific=True):
    a=read(folder/'analysis.json');n=len(cfg['blocks']);names=cfg['variants']
    assert a['status']=='PROSPECTIVE_EFFICIENCY_ANALYZED' and a['records']==16*n==cfg['cohort_size'] and a['blocks']==n
    metrics=('uninterrupted','terminal','first_pass','later_loss','ever_recovered','terminal_after_failure')
    counts={key:[] for key in metrics};ep=[];rate_curves=[];opposite_curves=[];noise=[];renewal_cpu=0.
    resource_keys=('repair_calls','added_edges','added_abs_weight','repair_cpu_seconds','audit_cpu_seconds')
    mechanism_keys=('available_edges','fallback_edges','returning_edges','returning_fallback_edges')
    resources={name:{key:0. for key in resource_keys} for name in names}
    mechanisms={name:{key:0 for key in mechanism_keys} for name in names}
    scientific_counts=dict(independent_captures=0,independent_repair_constructions=0,new_independent_optimizer_checks=0,native_audit_contexts=0,independent_noise_checks=0,independent_policy_decisions=0)
    with (folder/'reads.csv').open() as f,(folder/'resources.csv').open() as rf,(folder/'block_summaries.csv').open() as bf:
        reads=csv.DictReader(f);costs=csv.DictReader(rf);blocks=csv.DictReader(bf)
        for b in cfg['blocks']:
            path=folder/f'continuation_{b:06d}.npz';d=arrays(path)
            assert int(d['block'])==b and int(d['history'])==cfg['history_by_block'][str(b)]
            means=d['port_windows'].mean(axis=1);equal(means,d['mean_ports'],'raw port mean')
            good=np.zeros((18,3,16),bool);opposite=np.zeros_like(good);minimum=np.zeros(good.shape);om=np.zeros(good.shape)
            for gi in range(18):
                for v in range(3):
                    for case in range(16):
                        rule=1. if (case//4)%2==0 else -1.;mu=means[gi,v,case]
                        margins=[rule*mu[0,0],-rule*mu[0,1],-rule*mu[1,0],rule*mu[1,1]]
                        minimum[gi,v,case]=min(margins);om[gi,v,case]=-max(margins)
                        good[gi,v,case]=min(margins)>.25;opposite[gi,v,case]=-max(margins)>.25
            for key,want in [('both_pass',good),('opposite_pass',opposite),('min_margin',minimum),('opposite_margin',om)]:np.testing.assert_array_equal(d[key],want)
            assert np.array_equal(good[0,0],good[0,1]) and np.array_equal(good[0,0],good[0,2])
            e={key:np.zeros((3,16),bool) for key in metrics}
            for v,name in enumerate(names):
                for case in range(16):
                    x=[bool(good[gi,v,case]) for gi in range(18)]
                    e['uninterrupted'][v,case]=all(x);e['terminal'][v,case]=x[-1];e['first_pass'][v,case]=x[0]
                    e['later_loss'][v,case]=x[0] and not all(x[1:])
                    e['ever_recovered'][v,case]=any(x[i] and not x[i-1] for i in range(1,18))
                    e['terminal_after_failure'][v,case]=x[-1] and not all(x[:-1])
                csv_row(blocks,dict(block=b,history=cfg['history_by_block'][str(b)],variant=name,**{key:int(e[key][v].sum()) for key in metrics}))
                resources[name]['repair_calls']+=int(d['applied'][:,v].sum())
                for key in resource_keys[1:]:resources[name][key]+=float(d[key][:,v].sum())
                for key in mechanism_keys:mechanisms[name][key]+=int(d[key][:,v].sum())
            ep.append(e)
            for key in metrics:counts[key].append(e[key].sum(axis=1))
            rate_curves.append(good.mean(axis=2));opposite_curves.append(opposite.mean(axis=2));noise.append(d['noise_moments'].sum(axis=0));renewal_cpu+=float(d['renewal_cpu_seconds'].sum())
            for gi,g in enumerate(cfg['generations']):
                for vi,name in enumerate(names):
                    expected=g in cfg['repair_generations'][vi]
                    assert np.all(d['applied'][gi,vi]==expected)
                    for case in range(16):
                        keys=dict(block=b,generation=g,variant=name,case=case)
                        csv_row(reads,dict(**keys,intended=int(good[gi,vi,case]),opposite=int(opposite[gi,vi,case]),min_margin=minimum[gi,vi,case],opposite_margin=om[gi,vi,case],uninterrupted_so_far=int(all(good[:gi+1,vi,case]))))
                        csv_row(costs,dict(**keys,repair_call=int(expected),**{key:d[key][gi,vi,case] for key in ['missing_edges','added_edges','added_abs_weight','magnitude','repair_cpu_seconds','audit_cpu_seconds']}))
            if scientific:
                receipt=read(folder/f'worker_{b:06d}.json');audit=read(folder/f'audit_{b:06d}.json')
                assert receipt['status']==audit['status']=='COMPLETE' and not receipt['selected_on_outcome']
                assert receipt['audit_sha256']==sha(folder/f'audit_{b:06d}.json') and audit['block']==b
                assert receipt['continuation_sha256']==audit['continuation_sha256']==sha(path)
                for name in ('acquisition','lineage'):
                    digest=sha(folder/f'{name}_{b:06d}.npz')
                    assert digest==receipt[name+'_sha256']==audit[name+'_sha256']
                assert audit['acquisition_and_history_audit_passed'] and receipt['independent_optimizer_checks']==400
                for key in scientific_counts:scientific_counts[key]+=audit['continuation_checks'][key]
        for reader in (reads,costs,blocks):assert next(reader,None) is None
    counts={key:np.array(value) for key,value in counts.items()}
    for vi,name in enumerate(names):
        assert a['counts'][name]=={key:int(counts[key][:,vi].sum()) for key in metrics}
        for key in metrics:check_summary(a['rates'][name][key],counts[key][:,vi]/16,cfg)
        for key in resource_keys:close(a['resources'][name][key],resources[name][key],'resource '+key)
        assert resources[name]['repair_calls']==cfg['repair_budgets'][vi]*cfg['cohort_size']
        assert a['mechanism'][name]==mechanisms[name]
    for label,left,right in [('six_minus_one',1,0),('eighteen_minus_six',2,1),('eighteen_minus_one',2,0)]:
        for key in ('uninterrupted','terminal'):check_summary(a['contrasts'][label][key],(counts[key][:,left]-counts[key][:,right])/16,cfg)
        pairs=[(bool(e['uninterrupted'][left,c]),bool(e['uninterrupted'][right,c])) for e in ep for c in range(16)]
        assert a['paired_counts'][label]==dict(left_only=sum(x and not y for x,y in pairs),right_only=sum(y and not x for x,y in pairs),both=sum(x and y for x,y in pairs),neither=sum(not x and not y for x,y in pairs))
    u=counts['uninterrupted'];g=u[:,2]-u[:,0];d=17*u[:,1]-10*u[:,2]-7*u[:,0]
    p=a['primary'];check_summary(p['continual_benefit'],g,cfg,16);check_summary(p['double_call_efficiency'],d,cfg,16*17)
    passed=bool(np.quantile(resample(g,cfg),.05)>0 and np.quantile(resample(d,cfg),.05)>0)
    contradicted=bool(np.quantile(resample(g,cfg),.975)<0 or np.quantile(resample(d,cfg),.975)<0)
    assert p['criterion_passed']==passed and p['verdict']==('SUPPORTED' if passed else ('CONTRADICTED' if contradicted else 'UNRESOLVED'))
    denominator=float(sum(u[:,2]-u[:,0]));numerator=float(sum(u[:,1]-u[:,0]))
    if denominator>0:
        close(p['retained_benefit_fraction'],numerator/denominator,'retained benefit');close(p['benefit_per_additional_call_ratio'],17*numerator/(5*denominator),'call efficiency ratio')
    else:assert p['retained_benefit_fraction'] is p['benefit_per_additional_call_ratio'] is None
    eligible=counts['first_pass'][:,0];total=int(sum(eligible));den=resample(eligible,cfg)
    assert a['common_first_pass_records']==total and a['common_first_fail_records']==16*n-total
    for vi,name in enumerate(names):
        m=a['maintenance_among_common_first_pass'][name];num=counts['uninterrupted'][:,vi];draws=resample(num,cfg)
        assert m['eligible']==total and m['successes']==int(sum(num)) and m['empty_bootstrap_resamples']==int((den==0).sum())
        if total:close(m['rate'],sum(num)/total,'conditional rate')
        else:assert m['rate'] is None
        if (den>0).any():np.testing.assert_allclose(m['two_sided_95'],np.quantile(draws[den>0]/den[den>0],[.025,.975]),rtol=0,atol=1e-12)
        else:assert m['two_sided_95'] is None
    for h,label in enumerate(cfg['histories']):
        indices=[i for i,b in enumerate(cfg['blocks']) if cfg['history_by_block'][str(b)]==h]
        for vi,name in enumerate(names):
            for key in ('uninterrupted','terminal'):close(a['history_summaries'][label][name][key],sum(counts[key][indices,vi])/(16*len(indices)),'history summary')
    np.testing.assert_allclose(a['generation_success_rates'],np.mean(rate_curves,axis=0),rtol=0,atol=1e-12)
    np.testing.assert_allclose(a['generation_opposite_rates'],np.mean(opposite_curves,axis=0),rtol=0,atol=1e-12)
    np.testing.assert_allclose(a['noise_moments_total'],np.sum(noise,axis=0),rtol=1e-12,atol=1e-8)
    close(a['renewal_cpu_seconds'],renewal_cpu,'renewal CPU')
    if scientific:
        expected=dict(independent_captures=n*864,independent_repair_constructions=n*400,new_independent_optimizer_checks=n*400,native_audit_contexts=n*12,independent_noise_checks=n*18,independent_policy_decisions=n*864)
        assert scientific_counts==expected
    result=dict(status='PASS',at_utc=stamp(),scientific=scientific,records=16*n,blocks=n,**scientific_counts,
        independent_raw_scores=n*864,independent_teachings=n if scientific else 0,independent_history_captures=n*224 if scientific else 0,
        independent_history_flat_contexts=n if scientific else 0,analysis_module_imported=False,
        same_lane_internal_verification=True,primary_criterion_passed=passed,files_sha256={p.name:sha(p) for p in sorted(folder.iterdir()) if p.suffix in ('.npz','.csv') or p.name=='analysis.json'})
    write(folder/'VERIFICATION.json',result);return result
