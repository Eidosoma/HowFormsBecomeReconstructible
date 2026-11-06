"""Six frozen primary contrasts; diagnostic extra information cannot rescue them."""
from pathlib import Path
import csv
import numpy as np
from h007.io import save
from h104 import model as m,measure

METRICS=tuple(x[0] for x in measure.METRICS)
LEVEL=1-.05/6

def arrays(blocks):
    value=np.zeros((len(blocks),11,2,2,len(METRICS)));counts=np.zeros_like(value,dtype=int)
    for n,block in enumerate(blocks):
        for row in block['cases']:
            idx=(n,m.BRANCHES.index(row['branch']),m.INJURIES.index(row['injury']),m.BIRTHS.index(row['birth']))
            for k,(_,num,den) in enumerate(measure.METRICS):value[idx+(k,)]+=row[num];counts[idx+(k,)]+=row[den]
    assert np.all(counts[:,:,:,:,0]==64);assert np.all(counts>0)
    return value/counts

def interval(v,draws,level=.95):
    a=(1-level)/2;distribution=v[draws].mean(1)
    return dict(mean=np.asarray(v.mean(0)).tolist(),lower=np.asarray(np.quantile(distribution,a,axis=0)).tolist(),
        upper=np.asarray(np.quantile(distribution,1-a,axis=0)).tolist(),level=level)

def decide(primary,means):
    task_gates=dict(projection_capability=means['projection_task']>=.5,copy_capability=means['copy_task']>=.5,
        donor_gap=means['projection_task']-means['donor_task']>=.25,erased_gap=means['projection_task']-means['erased_task']>=.25)
    fidelity_gates=dict(projection_fidelity=means['projection_capture']>=.5)
    for row in primary:
        target=task_gates if row['metric']=='task_query' else fidelity_gates;prefix=row['comparator']
        target[prefix+'_gain']=row['mean']>=.05;target[prefix+'_interval']=row['lower']>0
        target[prefix+'_network_support']=row['positive_networks']>=16
    assert len(primary)==6 and len(task_gates)==13 and len(fidelity_gates)==10
    task=bool(all(task_gates.values()));capture=bool(all(fidelity_gates.values()))
    return dict(task_gain=task,captured_output_gain=capture,task_gates={k:bool(v) for k,v in task_gates.items()},
        captured_output_gates={k:bool(v) for k,v in fidelity_gates.items()},
        task_verdict='FRESH_TASK_RETENTION_GAIN' if task else 'NO_QUALIFIED_FRESH_TASK_RETENTION_GAIN',
        captured_output_verdict='FRESH_CAPTURED_OUTPUT_GAIN' if capture else 'NO_QUALIFIED_FRESH_CAPTURED_OUTPUT_GAIN',
        verdict='FRESH_WRITER_FIDELITY_AND_TASK_GAIN' if task and capture else 'NO_JOINT_FRESH_WRITER_GAIN')

def primary_result(v,draws):
    assert len(v)==32
    primary=[];p=m.BRANCHES.index('actual_projection');means={}
    for metric in ('task_query','captured_output_exact'):
        k=METRICS.index(metric)
        for name in ('hebbian','centered','norm_hebbian'):
            delta=v[:,p,1,0,k]-v[:,m.BRANCHES.index('actual_'+name),1,0,k]
            primary.append(dict(metric=metric,comparator=name,**interval(delta,draws,LEVEL),positive_networks=int((delta>0).sum()),negative_networks=int((delta<0).sum())))
    for name,branch,metric in (('projection_task','actual_projection','task_query'),('copy_task','copy','task_query'),
        ('donor_task','donor','task_query'),('erased_task','erased','task_query'),('projection_capture','actual_projection','captured_output_exact')):
        means[name]=float(v[:,m.BRANCHES.index(branch),1,0,METRICS.index(metric)].mean())
    return dict(primary_contrasts=primary,primary_means=means,**decide(primary,means))

def produce(out,blocks,phase):
    out=Path(out);v=arrays(blocks);n=len(blocks);draws=m.rng(phase,0,'inference').integers(0,n,size=(20000,n))
    scores={};diagnostics=[]
    for b,name in enumerate(m.BRANCHES):
        scores[name]={}
        for i,injury in enumerate(m.INJURIES):
            scores[name][injury]={birth:{metric:interval(v[:,b,i,u,k],draws) for k,metric in enumerate(METRICS)} for u,birth in enumerate(m.BIRTHS)}
        for k,metric in enumerate(METRICS):
            diagnostics.append(dict(branch=name,metric=metric,contrast='captured_minus_fresh_damaged',**interval(v[:,b,1,1,k]-v[:,b,1,0,k],draws)))
            diagnostics.append(dict(branch=name,metric=metric,contrast='damaged_minus_intact_fresh',**interval(v[:,b,1,0,k]-v[:,b,0,0,k],draws)))
    for w,rule in enumerate(m.WRITERS):
        for k,metric in enumerate(METRICS):diagnostics.append(dict(branch=rule,metric=metric,contrast='ancestral_minus_actual_damaged_fresh',**interval(v[:,w+4,1,0,k]-v[:,w,1,0,k],draws)))
    stability={}
    for b,name in enumerate(m.BRANCHES):
        stability[name]={}
        for injury in m.INJURIES:
            subset=[[r for r in block['stability'] if r['branch']==name and r['injury']==injury] for block in blocks]
            stability[name][injury]={key:interval(np.array([sum(r[key] for r in group)/sum(r[den] for r in group) for group in subset]),draws)
                for key,den in (('stable_free','queries'),('stable_output','queries'),('stable_free_bits','free_bits'))}
    supplier={}
    for key,den in (('task_query_correct','queries'),('task_exact_correct','queries'),('task_bit_correct','task_bits'),('hidden_distinct',None),('hidden_absolute_overlap',None)):
        a=np.array([sum(r[key] for r in block['suppliers'])/(sum(r[den] for r in block['suppliers']) if den else 4) for block in blocks]);supplier[key]=interval(a,draws)
    total=0
    for kind in blocks[0]:
        rows=[r for block in blocks for r in block[kind]];path=out/(kind+'.csv')
        with path.open('w',newline='') as stream:
            w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        with path.open() as stream:stored=list(csv.DictReader(stream))
        assert stored==[{k:str(v) for k,v in row.items()} for row in rows];total+=len(rows)
    result=dict(experiment='H104',phase=phase,independent_networks=n,actual_handoffs=1,branches=list(m.BRANCHES),metrics=list(METRICS),
        scores=scores,diagnostics=diagnostics,stability=stability,supplier=supplier,rows_serialized_and_verified=total,
        primary_source='actual',primary_injury='damaged',primary_birth='fresh',bootstrap_samples=20000,primary_interval_level=LEVEL,
        diagnostics_use_extra_information=True,copy_has_extra_information=True,H103_verdict_unchanged='NO_DEVELOPMENT_REVERSAL_LEAD',
        original_H097_acceptance='FAILED',private_sources_quoted=False,public_manuscript_changed=False,next_experiment_launched=False)
    if phase=='main':result.update(primary_result(v,draws))
    else:result['verdict']='ENGINEERING_ONLY'
    save(out/'summary.json',result)
    lines=['# H104 — supply, writing and access','',f"**{result['verdict']}**; {n} independent {phase} networks, one actual handoff.",'',
        'The primary uses actual supplying activity, damaged recipients and fresh births. Ancestral activity and captured-pattern starts provide additional information and are diagnostic only.',
        '', '| Packet | Task, fresh damaged | Captured output, fresh damaged | Task, captured start damaged | Static free stability, damaged |',
        '|---|---:|---:|---:|---:|']
    for name in m.BRANCHES:
        s=scores[name]['damaged'];values=[s['fresh']['task_query']['mean'],s['fresh']['captured_output_exact']['mean'],s['captured']['task_query']['mean'],stability[name]['damaged']['stable_free']['mean']]
        lines.append('| '+name+' | '+' | '.join(f'{100*x:.2f}%' for x in values)+' |')
    if phase=='main':
        lines+=['',result['task_verdict'],result['captured_output_verdict'],'','Six primary contrasts use 99.1667% paired whole-network bootstrap intervals. Diagnostic intervals are descriptive 95% intervals.','',
            '| Metric | Comparator | Gain (points) | Interval (points) | Positive networks |','|---|---|---:|---|---:|']
        for r in result['primary_contrasts']:lines.append(f"| {r['metric']} | {r['comparator']} | {100*r['mean']:.2f} | [{100*r['lower']:.2f}, {100*r['upper']:.2f}] | {r['positive_networks']}/32 |")
    lines+=['','All gates, failures, secondary endpoints and diagnostic contrasts are retained in summary.json. This test does not establish a pruning reversal, recovery over several generations, or superiority to copying.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');return result

def plot(out,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    names=list(m.BRANCHES);fig,axes=plt.subplots(1,2,figsize=(12,5.2),sharey=True)
    for ax,metric,title in zip(axes,('task_query','captured_output_exact'),('Original task','Exact captured output')):
        for shift,birth,color in ((-.16,'fresh','#2378a7'),(.16,'captured','#d29124')):
            scores=[result['scores'][name]['damaged'][birth][metric] for name in names];means=np.array([s['mean'] for s in scores])*100
            errors=np.array([[s['mean']-s['lower'] for s in scores],[s['upper']-s['mean'] for s in scores]])*100
            ax.barh(np.arange(11)+shift,means,.3,xerr=errors,color=color,label=birth)
        ax.set(title=title+'; damaged recipient',xlabel='Successful queries (%)',xlim=(0,102),yticks=np.arange(11),yticklabels=names);ax.grid(axis='x',alpha=.2)
    axes[0].invert_yaxis();axes[1].legend();fig.suptitle('H104: captured starts and ancestral packets provide extra information',fontsize=10)
    fig.tight_layout();fig.savefig(Path(out)/'transmission.png',dpi=180);plt.close(fig)
