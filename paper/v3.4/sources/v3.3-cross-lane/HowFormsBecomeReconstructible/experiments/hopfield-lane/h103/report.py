"""Development selection, fresh paired endpoints and duration kept separate."""
from pathlib import Path
import csv
import numpy as np
from h007.io import save
from h103 import model as m

def arrays(blocks,variants):
    result=np.zeros((len(blocks),len(variants),3,5))
    for i,block in enumerate(blocks):
        counts=np.zeros((len(variants),3,5),dtype=int)
        for r in block['cases']:
            key=(variants.index(r['variant']),m.ROUTES.index(r['route']),r['g'])
            result[(i,)+key]+=r['query_correct'];counts[key]+=r['queries']
        assert np.all(counts==64);result[i]/=counts
    return result
def selection(values,variants):
    assert values.shape==(16,len(variants),3,5)
    u=values[:,variants.index('unchanged'),0];erased=values[:,variants.index('erased'),0];donor=values[:,variants.index('donor'),0]
    candidates=[]
    for name in m.CANDIDATES:
        p=values[:,variants.index(name),0];delta=p-u;mean=delta.mean(0)
        gates=dict(current_capability=p[:,0].mean()>=.5,unchanged_acquired=u[:,0].mean()>=.25,
            erased_gap=(p[:,0]-erased[:,0]).mean()>=.25,donor_gap=(p[:,0]-donor[:,0]).mean()>=.25,
            current_gain=mean[0]>=.05,first_successor_cost=mean[1]<=-.05,
            current_network_support=np.count_nonzero(delta[:,0]>0)>=8,later_network_support=np.count_nonzero(delta[:,1]<0)>=8)
        candidates.append(dict(candidate=name,eligible=bool(all(gates.values())),gates={k:bool(v) for k,v in gates.items()},
            unchanged=u.mean(0).tolist(),pruned=p.mean(0).tolist(),differences=mean.tolist(),score=float(min(mean[0],-mean[1]))))
    eligible=[r for r in candidates if r['eligible']];selected=max(eligible,key=lambda r:(r['score'],-m.CANDIDATES.index(r['candidate'])))['candidate'] if eligible else None
    return dict(selected=selected,candidates=candidates,verdict='DEVELOPMENT_REVERSAL_LEAD' if selected else 'NO_DEVELOPMENT_REVERSAL_LEAD',
        development_only=True,confirmation_outcomes_acquired=False)
def interval(values,indices,level=.95):
    distribution=values[indices].mean(1);a=(1-level)/2
    return dict(mean=np.asarray(values.mean(0)).tolist(),lower=np.asarray(np.quantile(distribution,a,axis=0)).tolist(),
        upper=np.asarray(np.quantile(distribution,1-a,axis=0)).tolist(),level=level)
def duration(delta,lag,regain,first_cost):
    return dict(cost_through_four_handoffs=bool(first_cost and all(v<0 for v in delta['upper'][1:])),
        converged_by_g2=bool(all(a>-.02 and b<.02 for a,b in zip(lag['convergence']['lower'],lag['convergence']['upper']))),
        regained_g0_by_g2=bool(all(v>-.02 for v in regain['lower'])),
        one_generation_delay_compatible=bool(first_cost and all(a>-.02 and b<.02 for a,b in zip(lag['shift']['lower'],lag['shift']['upper']))),
        resolved_alternation=bool(all((delta['lower'][g]>0 if g%2==0 else delta['upper'][g]<0) for g in range(5))))
def produce(out,blocks,variants,phase,selected=None):
    out=Path(out);values=arrays(blocks,variants);n=len(blocks)
    draws=m.rng(phase,0,'inference').integers(0,n,size=(20000,n));summaries={}
    for vi,name in enumerate(variants):
        summaries[name]={route:interval(values[:,vi,ci],draws) for ci,route in enumerate(m.ROUTES)}
    rows_written=0
    for kind in blocks[0]:
        rows=[r for block in blocks for r in block[kind]];path=out/(kind+'.csv')
        with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        with path.open() as f:saved=list(csv.DictReader(f))
        assert saved==[{k:str(v) for k,v in r.items()} for r in rows];rows_written+=len(rows)
    result=dict(experiment='H103',phase=phase,independent_networks=n,variants=list(variants),routes=list(m.ROUTES),
        horizons=list(range(5)),scores=summaries,rows_serialized_and_verified=rows_written,assessment_tapes_matched_across_horizons=True,
        writer_exact_zero_fallback=False,original_H097_acceptance='FAILED',historical_verdicts_unchanged=True,
        acquisition_gain=4.,assessment_gain=2.,supplying_gain=2.,record_edge_deletion=.2,
        H101_verdict_unchanged=True,H102_regime_used_without_reselection=True,
        new_learned_reader_work=False,private_sources_quoted=False,public_manuscript_changed=False,next_experiment_launched=False)
    if phase=='development':result['selection']=selection(values,variants);result['verdict']=result['selection']['verdict']
    elif phase=='confirmation':
        assert n==32 and selected in m.CANDIDATES
        u=values[:,variants.index('unchanged'),0];p=values[:,variants.index(selected),0]
        delta=interval(p-u,draws,.99);convergence=interval((p-u)[:,2:],draws,.90)
        shifts=np.column_stack((p[:,1:]-u[:,:-1],u[:,1]-p[:,0]));lag=interval(shifts,draws,.90)
        regain=interval(p[:,2:]-p[:,0,None],draws,.90)
        capability=p[:,0].mean()>=.5 and u[:,0].mean()>=.25 and all((p[:,0]-values[:,variants.index(control),0,0]).mean()>=.25 for control in ('erased','donor'))
        benefit=delta['mean'][0]>=.05 and delta['lower'][0]>0
        cost=delta['mean'][1]<=-.05 and delta['upper'][1]<0
        gates=dict(acquired_task=bool(capability),present_benefit=bool(benefit),first_successor_cost=bool(cost),endpoint_reversal_confirmed=bool(capability and benefit and cost))
        result.update(selected=selected,primary_differences=delta,convergence_intervals=convergence,shift_intervals=lag,regain_intervals=regain,
            gates=gates,duration=duration(delta,dict(convergence=convergence,shift=lag),regain,cost),
            verdict='FRESH_ENDPOINT_REVERSAL_CONFIRMED' if all(gates.values()) else 'FRESH_ENDPOINT_REVERSAL_NOT_CONFIRMED')
        result['writing_controls']={route:interval(values[:,variants.index(selected),ci]-values[:,variants.index('unchanged'),ci],draws) for ci,route in enumerate(m.ROUTES)}
    else:result['verdict']='ENGINEERING_ONLY'
    save(out/'summary.json',result)
    lines=['# H103 — present retrieval and four actual handoffs','',f"**{result['verdict']}**; {n} independent {phase} networks.",
        'Query success requires at least 14/16 correct output bits. All eight cues, both founders, both descendants and both assessment draws are retained.',
        'Acquisition remains at cue gain four; assessment and actual supplying bodies both use the H102-qualified gain two, with 20% record-edge deletion.',
        'Assessment injury, birth and order tapes are identical across arms and horizons. Writers use independent cue births and have no exact-zero coactivity fallback.','',
        '| Ordinary writer: variant | G0 | G1 | G2 | G3 | G4 |','|---|---:|---:|---:|---:|---:|']
    for name in variants:lines.append('| '+name+' | '+' | '.join(f'{100*v:.2f}%' for v in summaries[name]['hebbian']['mean'])+' |')
    if phase=='development':
        lines+=['',f"Selected candidate: **{result['selection']['selected']}**.",'All candidate eligibility gates and failures are retained in summary.json. Development outcomes do not constitute confirmation.']
    elif phase=='confirmation':
        lines+=['','Primary G0--G4 differences use 99% whole-network intervals (nominal 95% family target).']
        for key,value in result['gates'].items():lines.append(f'{key}: **{value}**.')
        for key,value in result['duration'].items():lines.append(f'{key}: **{value}**.')
        lines+=['','Convergence alone is not recovery. Delay compatibility is a finite-observer result, and four handoffs cannot establish permanent harm.']
    lines+=['','Protected-copy assessments must be exactly invariant across horizons. Centered capture, random pruning and norm-matched attenuation remain controls, not alternate primaries.',
        'The task is acquired once; unseen-combination generalization is not tested. Numerical rejection stops acceptance without dropping cases or changing tolerances.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return result
def plot(out,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    chosen=[summary.get('selected')] if summary.get('selected') else list(m.CANDIDATES)
    fig,axes=plt.subplots(1,3,figsize=(13,3.6),sharey=True)
    for ax,route in zip(axes,m.ROUTES):
        for name in ('unchanged',*chosen):
            if name not in summary['scores']:continue
            s=summary['scores'][name][route];ax.plot(range(5),np.asarray(s['mean'])*100,marker='o',label=name)
            ax.fill_between(range(5),np.asarray(s['lower'])*100,np.asarray(s['upper'])*100,alpha=.12)
        ax.set(title=route,xlabel='Actual handoffs',xticks=range(5),ylim=(-2,102));ax.grid(alpha=.2)
    axes[0].set_ylabel('Successful queries (%)');axes[-1].legend(fontsize=8)
    fig.suptitle('H103 '+summary['phase']+' — '+summary['verdict']);fig.tight_layout()
    fig.savefig(Path(out)/'trajectories.png',dpi=180);fig.savefig(Path(out)/'trajectories.pdf');plt.close(fig)
