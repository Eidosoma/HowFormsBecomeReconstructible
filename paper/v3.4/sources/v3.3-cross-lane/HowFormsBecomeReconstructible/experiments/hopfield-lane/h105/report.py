"""Task advantage at every boundary and absolute local fidelity remain separate."""
from pathlib import Path
import csv
import numpy as np
from h007.io import save
from h105 import model as m,measure

LEVEL=1-.05/16

def aggregate(blocks,kind,arms,generations,metrics,offset=0):
    values=np.zeros((len(blocks),len(arms),generations,len(metrics)));counts=np.zeros_like(values)
    for n,block in enumerate(blocks):
        for row in block[kind]:
            idx=(n,arms.index(row['arm']),row['g']-offset)
            for k,(_,num,den) in enumerate(metrics):values[idx+(k,)]+=row[num];counts[idx+(k,)]+=row[den] if den else 1
    assert np.all(counts>0);return values/counts

def interval(v,draws,level=.95):
    means=v[draws].mean(1);a=(1-level)/2
    return dict(mean=np.asarray(v.mean(0)).tolist(),lower=np.asarray(np.quantile(means,a,axis=0)).tolist(),upper=np.asarray(np.quantile(means,1-a,axis=0)).tolist(),level=level)

def decide(contrasts,fidelity,means):
    task={};capture={}
    assert len(contrasts)==12 and len(fidelity)==4
    assert {(r['g'],r['comparator']) for r in contrasts}=={(g,w) for g in range(1,5) for w in ('hebbian','centered','norm_hebbian')}
    assert {r['g'] for r in fidelity}==set(range(1,5))
    for i,g in enumerate(range(1,5)):
        task[f'g{g}_projection_capability']=means['projection'][i]>=.5
        task[f'g{g}_copy_capability']=means['copy'][i]>=.5
        task[f'g{g}_donor_gap']=means['projection'][i]-means['donor'][i]>=.25
        task[f'g{g}_erased_gap']=means['projection'][i]-means['erased'][i]>=.25
    for row in contrasts:
        key=f"g{row['g']}_{row['comparator']}"
        task[key+'_gain']=row['mean']>=.05;task[key+'_interval']=row['lower']>0;task[key+'_network_support']=row['positive_networks']>=16
    for row in fidelity:
        capture[f"g{row['g']}_mean"]=row['mean']>=.5;capture[f"g{row['g']}_interval"]=row['lower']>.5
    task_pass=bool(all(task.values()));capture_pass=bool(all(capture.values()))
    return dict(task_advantage=task_pass,local_capture_fidelity=capture_pass,task_gates={k:bool(v) for k,v in task.items()},capture_gates={k:bool(v) for k,v in capture.items()},
        task_verdict='FOUR_HANDOFF_TASK_ADVANTAGE' if task_pass else 'NO_QUALIFIED_FOUR_HANDOFF_TASK_ADVANTAGE',
        capture_verdict='FOUR_HANDOFF_LOCAL_CAPTURE_FIDELITY' if capture_pass else 'NO_QUALIFIED_FOUR_HANDOFF_LOCAL_CAPTURE_FIDELITY',
        verdict='FOUR_HANDOFF_TASK_AND_CAPTURE_QUALIFIED' if task_pass and capture_pass else 'NO_JOINT_FOUR_HANDOFF_QUALIFICATION')

def primary_result(task,capture,draws):
    assert task.shape==(32,7,5,7) and capture.shape==(32,4,4,4)
    contrasts=[];fidelity=[]
    for g in range(1,5):
        for name in ('hebbian','centered','norm_hebbian'):
            delta=task[:,2,g,0]-task[:,m.ARMS.index(name),g,0]
            contrasts.append(dict(g=g,comparator=name,**interval(delta,draws,LEVEL),positive_networks=int((delta>0).sum()),negative_networks=int((delta<0).sum())))
        fidelity.append(dict(g=g,**interval(capture[:,2,g-1,0],draws,LEVEL)))
    means={name:task[:,m.ARMS.index(name),1:,0].mean(0).tolist() for name in ('projection','copy','donor','erased')}
    return dict(primary_task_contrasts=contrasts,primary_local_capture=fidelity,primary_means=means,**decide(contrasts,fidelity,means))

def produce(out,blocks,phase):
    out=Path(out);n=len(blocks);draws=m.rng(phase,0,'inference').integers(0,n,size=(20000,n))
    task=aggregate(blocks,'cases',m.ARMS,5,measure.TASK);capture=aggregate(blocks,'fidelity',m.WRITERS,4,measure.CAPTURE,1)
    static_metrics=(('free','stable_free','queries'),('output','stable_output','queries'),('free_bits','stable_free_bits','free_total'))
    stable=aggregate(blocks,'stability',m.WRITERS,4,static_metrics,1)
    supplier_metrics=(('query','query_correct','queries'),('exact','exact_correct','queries'),('bits','bit_correct','bits'))+tuple((k,k,None) for k in
        ('hidden_distinct','hidden_absolute_overlap','incoming_norm','outgoing_norm','incoming_isolated','outgoing_isolated','body_isolated'))
    suppliers=aggregate(blocks,'suppliers',m.WRITERS,4,supplier_metrics)
    task_scores={name:{metric:interval(task[:,a,:,k],draws) for k,(metric,_,_) in enumerate(measure.TASK)} for a,name in enumerate(m.ARMS)}
    capture_scores={name:{metric:interval(capture[:,a,:,k],draws) for k,(metric,_,_) in enumerate(measure.CAPTURE)} for a,name in enumerate(m.WRITERS)}
    stability={name:{metric:interval(stable[:,a,:,k],draws) for k,(metric,_,_) in enumerate(static_metrics)} for a,name in enumerate(m.WRITERS)}
    supplying={name:{metric:interval(suppliers[:,a,:,k],draws) for k,(metric,_,_) in enumerate(supplier_metrics)} for a,name in enumerate(m.WRITERS)}
    differences={name:interval(task[:,2,:,0]-task[:,a,:,0],draws) for a,name in enumerate(m.ARMS) if name!='projection'}
    local_differences={name:interval(capture[:,2,:,0]-capture[:,a,:,0],draws) for a,name in enumerate(m.WRITERS) if name!='projection'}
    change={name:interval(task[:,a,1:,0]-task[:,a,0,None,0],draws) for a,name in enumerate(m.ARMS)}
    rows_written=0
    for kind in blocks[0]:
        rows=[r for block in blocks for r in block[kind]];path=out/(kind+'.csv')
        with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        with path.open() as f:saved=list(csv.DictReader(f))
        assert saved==[{k:str(v) for k,v in row.items()} for row in rows];rows_written+=len(rows)
    result=dict(experiment='H105',phase=phase,independent_networks=n,horizons=list(range(5)),arms=list(m.ARMS),actual_handoffs=4,
        task_scores=task_scores,capture_scores=capture_scores,stability=stability,suppliers=supplying,task_differences=differences,
        local_capture_differences=local_differences,task_change_from_g0=change,rows_serialized_and_verified=rows_written,
        primary_interval_level=LEVEL,bootstrap_samples=20000,assessment_matched_across_horizons=True,capture_reference='own_immediately_preceding_actual_supplier',
        local_capture_is_not_task_retention=True,protected_copy_has_extra_information=True,H103_verdict_unchanged='NO_DEVELOPMENT_REVERSAL_LEAD',
        H104_verdict_unchanged='FRESH_WRITER_FIDELITY_AND_TASK_GAIN',original_H097_acceptance='FAILED',private_sources_quoted=False,public_manuscript_changed=False,next_experiment_launched=False)
    if phase=='main':result.update(primary_result(task,capture,draws))
    else:result['verdict']='ENGINEERING_ONLY'
    save(out/'summary.json',result)
    lines=['# H105 — four actual handoffs','',f"**{result['verdict']}**; {n} independent {phase} networks.",'',
        'The task was acquired once. Every fixed writer uses its own actual supplying activity; later inputs can differ because earlier writes differ. Assessments use matched injury, birth and order tapes across arms and horizons.',
        '', '| Original-task query success | G0 | G1 | G2 | G3 | G4 |','|---|---:|---:|---:|---:|---:|']
    for name in m.ARMS:lines.append('| '+name+' | '+' | '.join(f'{100*x:.2f}%' for x in task_scores[name]['query']['mean'])+' |')
    lines+=['','| Exact immediate-supplier output recovery | G1 | G2 | G3 | G4 |','|---|---:|---:|---:|---:|']
    for name in m.WRITERS:lines.append('| '+name+' | '+' | '.join(f'{100*x:.2f}%' for x in capture_scores[name]['output_exact']['mean'])+' |')
    if phase=='main':
        lines+=['',result['task_verdict'],result['capture_verdict'],'','Twelve task contrasts and four absolute local-fidelity intervals use 99.6875% paired whole-network bootstrap intervals. Task advantage must pass at every boundary. Local fidelity is a separate absolute test, not an advantage over comparators or original-task retention.',
            '','| Handoff | Task comparator | Gain (points) | Adjusted interval | Positive networks |','|---|---|---:|---|---:|']
        for r in result['primary_task_contrasts']:lines.append(f"| G{r['g']} | {r['comparator']} | {100*r['mean']:.2f} | [{100*r['lower']:.2f}, {100*r['upper']:.2f}] | {r['positive_networks']}/32 |")
        lines+=['','Failed task requirements: '+(', '.join(k for k,v in result['task_gates'].items() if not v) or 'none')+'.',
            'Failed local-capture requirements: '+(', '.join(k for k,v in result['capture_gates'].items() if not v) or 'none')+'.']
    lines+=['','All exact-query, complete-task, bit-level, matched retention/loss/gain, supplier and static-stability diagnostics are retained in summary.json with descriptive 95% intervals. No pruning intervention, copying advantage, ancestral rescue or persistence beyond four handoffs is established by this test.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');return result

def plot(out,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(13.6,4),sharey=True)
    for a,name in enumerate(m.ARMS):
        s=result['task_scores'][name]['query'];axes[0].plot(range(5),np.array(s['mean'])*100,marker='o',label=name)
        axes[0].fill_between(range(5),np.array(s['lower'])*100,np.array(s['upper'])*100,alpha=.1)
    for name in m.WRITERS:
        for ax,scores,key in ((axes[1],result['capture_scores'],'output_exact'),(axes[2],result['stability'],'free')):
            s=scores[name][key];ax.plot(range(1,5),np.array(s['mean'])*100,marker='o',label=name)
            ax.fill_between(range(1,5),np.array(s['lower'])*100,np.array(s['upper'])*100,alpha=.1)
    for i,(ax,title) in enumerate(zip(axes,('Original task','Exact immediate-supplier output','Static captured free-pattern stability'))):
        ax.set(title=title,xlabel='Actual handoffs',xticks=range(5) if i==0 else range(1,5),ylim=(-2,102));ax.grid(alpha=.2)
    axes[0].set_ylabel('Queries (%)');axes[0].legend(fontsize=7,loc='best');axes[1].legend(fontsize=7,loc='best')
    fig.tight_layout();fig.savefig(Path(out)/'trajectories.png',dpi=180);plt.close(fig)
