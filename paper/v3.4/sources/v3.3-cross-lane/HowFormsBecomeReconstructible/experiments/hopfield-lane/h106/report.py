"""Separate fixed-record access and inherited-record effects under a common reader."""
from pathlib import Path
import csv
import numpy as np
from h007.io import save
from h106 import model as m,measure

LEVEL=1-.05/16
def aggregate(blocks,kind,branches,generations,metrics,offset=0,readers=True):
    shape=(len(blocks),)+( (3,) if readers else () )+(len(branches),generations,len(metrics))
    values=np.zeros(shape);counts=np.zeros(shape)
    for n,block in enumerate(blocks):
        for row in block[kind]:
            idx=(n,)+( (m.POLICIES.index(row['reader']),) if readers else () )+(branches.index(row['branch']),row['g']-offset)
            for k,(_,num,den) in enumerate(metrics):values[idx+(k,)]+=row[num];counts[idx+(k,)]+=row[den] if den else 1
    assert np.all(counts>0);return values/counts
def interval(v,draws,level=.95):
    distribution=v[draws].mean(1);a=(1-level)/2
    return dict(mean=np.asarray(v.mean(0)).tolist(),lower=np.asarray(np.quantile(distribution,a,axis=0)).tolist(),upper=np.asarray(np.quantile(distribution,1-a,axis=0)).tolist(),level=level)

def decide(contrasts,means):
    access={};supply={}
    assert len(contrasts)==16 and {(r['endpoint'],r['g'],r['comparator']) for r in contrasts}=={(kind,g,p) for kind in ('access','supply') for g in range(1,5) for p in ('standard','two_start')}
    for i,g in enumerate(range(1,5)):
        access[f'g{g}_fidelity']=means['access_fidelity'][i]>=.8
        supply[f'g{g}_capability']=means['supply_task'][i]>=.5;supply[f'g{g}_copy_capability']=means['copy_task'][i]>=.5
        supply[f'g{g}_donor_gap']=means['supply_task'][i]-means['donor_task'][i]>=.25;supply[f'g{g}_erased_gap']=means['supply_task'][i]-means['erased_task'][i]>=.25
    for row in contrasts:
        gates=access if row['endpoint']=='access' else supply;key=f"g{row['g']}_{row['comparator']}"
        gates[key+'_gain']=row['mean']>=.05;gates[key+'_interval']=row['lower']>0;gates[key+'_network_support']=row['positive_networks']>=16
    a=bool(all(access.values()));s=bool(all(supply.values()))
    return dict(access_gain=a,supply_gain=s,access_gates={k:bool(v) for k,v in access.items()},supply_gates={k:bool(v) for k,v in supply.items()},
        access_verdict='FIXED_RECORD_ACCESS_GAIN' if a else 'NO_QUALIFIED_FIXED_RECORD_ACCESS_GAIN',
        supply_verdict='FOUR_HANDOFF_SUPPLY_POLICY_GAIN' if s else 'NO_QUALIFIED_FOUR_HANDOFF_SUPPLY_POLICY_GAIN',
        verdict='ACCESS_AND_SUPPLY_TRANSFER_QUALIFIED' if a and s else 'NO_JOINT_ACCESS_AND_SUPPLY_QUALIFICATION')

def primary_result(task,capture,draws):
    assert task.shape==(32,3,6,5,8) and capture.shape==(32,3,3,4,4)
    contrasts=[]
    for g in range(1,5):
        for name in ('standard','two_start'):
            p=m.POLICIES.index(name)
            for endpoint,delta in (('access',capture[:,1,0,g-1,0]-capture[:,p,0,g-1,0]),('supply',task[:,0,1,g,0]-task[:,0,p,g,0])):
                contrasts.append(dict(endpoint=endpoint,g=g,comparator=name,**interval(delta,draws,LEVEL),positive_networks=int((delta>0).sum()),negative_networks=int((delta<0).sum())))
    means=dict(access_fidelity=capture[:,1,0,:,0].mean(0).tolist(),supply_task=task[:,0,1,1:,0].mean(0).tolist(),
        copy_task=task[:,0,3,1:,0].mean(0).tolist(),donor_task=task[:,0,4,1:,0].mean(0).tolist(),erased_task=task[:,0,5,1:,0].mean(0).tolist())
    return dict(primary_contrasts=contrasts,primary_means=means,**decide(contrasts,means))

def produce(out,blocks,phase):
    out=Path(out);n=len(blocks);draws=m.rng(phase,0,'inference').integers(0,n,size=(20000,n))
    task=aggregate(blocks,'cases',m.BRANCHES,5,measure.TASK);capture=aggregate(blocks,'fidelity',m.POLICIES,4,measure.CAPTURE,1)
    static_metrics=(('free','stable_free','queries'),('output','stable_output','queries'),('free_bits','stable_free_bits','free_total'))
    stable=aggregate(blocks,'stability',m.POLICIES,4,static_metrics,1,False)
    supplier_metrics=(('query','query_correct','queries'),('exact','exact_correct','queries'),('bits','bit_correct','bits'),('pre_query','pre_query_correct','queries'),
        ('hidden_distinct','hidden_distinct',None),('hidden_absolute_overlap','hidden_absolute_overlap',None),('second_selected','second_selected','queries'))
    suppliers=aggregate(blocks,'suppliers',m.POLICIES,4,supplier_metrics,readers=False)
    selections=aggregate(blocks,'cases',m.BRANCHES,5,(('second_selected','second_selected','queries'),))
    task_scores={reader:{branch:{metric:interval(task[:,p,a,:,k],draws) for k,(metric,_,_) in enumerate(measure.TASK)} for a,branch in enumerate(m.BRANCHES)} for p,reader in enumerate(m.POLICIES)}
    capture_scores={reader:{branch:{metric:interval(capture[:,p,a,:,k],draws) for k,(metric,_,_) in enumerate(measure.CAPTURE)} for a,branch in enumerate(m.POLICIES)} for p,reader in enumerate(m.POLICIES)}
    stability={name:{metric:interval(stable[:,a,:,k],draws) for k,(metric,_,_) in enumerate(static_metrics)} for a,name in enumerate(m.POLICIES)}
    supplying={name:{metric:interval(suppliers[:,a,:,k],draws) for k,(metric,_,_) in enumerate(supplier_metrics)} for a,name in enumerate(m.POLICIES)}
    selection_rates={branch:interval(selections[:,2,a,:,0],draws) for a,branch in enumerate(m.BRANCHES)}
    rows_written=0
    for kind in blocks[0]:
        rows=[r for block in blocks for r in block[kind]];path=out/(kind+'.csv')
        with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        with path.open() as f:saved=list(csv.DictReader(f))
        assert saved==[{k:str(v) for k,v in row.items()} for row in rows];rows_written+=len(rows)
    result=dict(experiment='H106',phase=phase,independent_networks=n,horizons=list(range(5)),policies=list(m.POLICIES),branches=list(m.BRANCHES),
        actual_handoffs=4,task_scores=task_scores,capture_scores=capture_scores,stability=stability,suppliers=supplying,two_start_second_selection=selection_rates,
        rows_serialized_and_verified=rows_written,primary_interval_level=LEVEL,bootstrap_samples=20000,primary_access_history='standard',primary_supply_reader='standard',
        sweeps_per_access_policy=8,full_endpoint_energy_evaluations_per_policy=2,assessment_matched_across_horizons=True,
        capture_reference='own_immediately_preceding_actual_supplier',H105_verdict_unchanged='NO_JOINT_FOUR_HANDOFF_QUALIFICATION',
        original_H097_acceptance='FAILED',private_sources_quoted=False,public_manuscript_changed=False,next_experiment_launched=False)
    if phase=='main':result.update(primary_result(task,capture,draws))
    else:result['verdict']='ENGINEERING_ONLY'
    save(out/'summary.json',result)
    lines=['# H106 — access and actual supplying policy','',f"**{result['verdict']}**; {n} independent {phase} networks.",'',
        'Every access policy uses eight free-coordinate sweeps and two full-matrix endpoint-energy evaluations. Preparation uses surviving cue drive, and two-start selection uses energy alone. Original targets and source patterns are observers only.',
        '', '| Common standard reader: record history | G0 | G1 | G2 | G3 | G4 |','|---|---:|---:|---:|---:|---:|']
    for name in m.BRANCHES:lines.append('| '+name+' | '+' | '.join(f'{100*x:.2f}%' for x in task_scores['standard'][name]['query']['mean'])+' |')
    lines+=['','| Access to identical standard-history records: exact captured output | G1 | G2 | G3 | G4 |','|---|---:|---:|---:|---:|']
    for name in m.POLICIES:lines.append('| '+name+' | '+' | '.join(f'{100*x:.2f}%' for x in capture_scores[name]['standard']['output_exact']['mean'])+' |')
    lines+=['','| Secondary coupled supplier/reader task success | G0 | G1 | G2 | G3 | G4 |','|---|---:|---:|---:|---:|---:|']
    for name in m.POLICIES:lines.append('| '+name+' | '+' | '.join(f'{100*x:.2f}%' for x in task_scores[name][name]['query']['mean'])+' |')
    if phase=='main':
        lines+=['',result['access_verdict'],result['supply_verdict'],'','Sixteen primary contrasts use 99.6875% paired whole-network intervals. Common-reader transmission cannot be rescued by coupled supplier/reader success.',
            '', '| Endpoint | Handoff | Comparator | Gain (points) | Adjusted interval | Positive networks |','|---|---|---|---:|---|---:|']
        for r in result['primary_contrasts']:lines.append(f"| {r['endpoint']} | G{r['g']} | {r['comparator']} | {100*r['mean']:.2f} | [{100*r['lower']:.2f}, {100*r['upper']:.2f}] | {r['positive_networks']}/32 |")
        lines+=['','Failed access requirements: '+(', '.join(k for k,v in result['access_gates'].items() if not v) or 'none')+'.',
            'Failed supply requirements: '+(', '.join(k for k,v in result['supply_gates'].items() if not v) or 'none')+'.']
    lines+=['','All secondary task, preparation, fidelity, stability, fixed-endpoint, source and selection scores retain descriptive 95% intervals in summary.json. Copying is a benchmark with different information. This is not a pruning reversal or evidence of recovery of arbitrary erased task information.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');return result

def plot(out,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11.8,4.2),sharey=True)
    for name in (*m.POLICIES,'copy'):
        s=result['task_scores']['standard'][name]['query'];axes[0].plot(range(5),np.array(s['mean'])*100,marker='o',label=name)
        axes[0].fill_between(range(5),np.array(s['lower'])*100,np.array(s['upper'])*100,alpha=.12)
    for name in m.POLICIES:
        s=result['capture_scores'][name]['standard']['output_exact'];axes[1].plot(range(1,5),np.array(s['mean'])*100,marker='o',label=name)
        axes[1].fill_between(range(1,5),np.array(s['lower'])*100,np.array(s['upper'])*100,alpha=.12)
    for i,(ax,title) in enumerate(zip(axes,('Task: common standard reader, different suppliers','Access: different readers, identical standard-history record'))):
        ax.set(title=title,xlabel='Actual handoffs',xticks=range(5) if i==0 else range(1,5),ylim=(-2,102));ax.grid(alpha=.2);ax.legend(fontsize=8)
    axes[0].set_ylabel('Queries (%)');fig.tight_layout();fig.savefig(Path(out)/'access_and_supply.png',dpi=180);plt.close(fig)
