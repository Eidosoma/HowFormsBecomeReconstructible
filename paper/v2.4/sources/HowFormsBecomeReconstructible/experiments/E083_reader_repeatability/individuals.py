"""Every original case, both fresh draws, every functional endpoint and effect."""
import csv
import numpy as np
from E083_reader_repeatability.plan import STARTS,cohort,source_block
from E083_reader_repeatability.inference import GROUPS


def export(run,tasks,sources,cases,summary):
    path=run/'individual_draws.csv';aggregate=run/'individual_two_draw_means.csv'
    rows=[];means=[]
    fields=('both','minimum_margin','transfer','aligned_transfer','postinjury_selected_coupling_share')
    for task,src,new in zip(tasks,sources,cases,strict=True):
        for arm,f,r in np.ndindex((4,)+src['old_both'].shape[1:]):
            oldof=int(src['old_both'][18+arm,f,r]);oldff=int(src['old_both'][22+arm,f,r])
            base=dict(cohort=cohort(task),task=task,source_block=source_block(task),kind='native' if arm<2 else 'mixture',
                      history='sham' if arm%2==0 else 'pulse',arm=arm,founder=f,recipient=r,
                      old_group=GROUPS[2*oldof+oldff],old_effect=oldff-oldof,
                      old_endpoint_provenance='E077' if cohort(task)=='E080' else 'E081')
            for c,start in STARTS.items():
                for key in ('both','minimum_margin','transfer','aligned_transfer'):
                    value=src['old_'+key][start+arm,f,r];base['old_'+c+'_'+key]=int(value) if key=='both' else float(value)
                for q in range(2):base['old_'+c+'_cue_'+str(q)+'_margin']=float(src['old_margin'][start+arm,f,r,q])
            pair=[]
            for d,arr in enumerate(new):
                row=dict(base,draw=d)
                for c,start in STARTS.items():
                    for key in fields:
                        v=arr[key][start+arm,f,r];row[c+'_'+key]=int(v) if key=='both' else float(v)
                    for q in range(2):row[c+'_cue_'+str(q)+'_margin']=float(arr['margin'][start+arm,f,r,q])
                row['pattern_effect']=row['FF_both']-row['OF_both']
                row['pruning_h0']=row['P0_both']-row['I0_both'];row['pruning_h1']=row['P1_both']-row['I1_both']
                rows.append(row);pair.append(row)
            mean=dict(base)
            for key in pair[0]:
                if key not in base and key!='draw':mean[key]=sum(p[key] for p in pair)/2
            mean['gain_draws']=sum(p['pattern_effect']==1 for p in pair)
            mean['harm_draws']=sum(p['pattern_effect']==-1 for p in pair)
            mean['old_sign_recurrence_draws']=sum(p['pattern_effect']==base['old_effect'] for p in pair) if base['old_effect'] else ''
            means.append(mean)
    for dest,table in ((path,rows),(aggregate,means)):
        with dest.open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
        with dest.open(newline='') as f:loaded=list(csv.DictReader(f))
        assert len(loaded)==len(table)
        for got,expected in zip(loaded,table,strict=True):assert got=={k:str(v) for k,v in expected.items()}
    # Independent raw-array lookup and recount, including each original endpoint.
    lookup={task:(s,n) for task,s,n in zip(tasks,sources,cases,strict=True)}
    with path.open(newline='') as f:
        recount={tag:dict(gain=0,harm=0,rows=0) for tag in summary['cohorts']};seen=set()
        for row in csv.DictReader(f):
            t,a,founder,r,d=[int(row[k]) for k in ('task','arm','founder','recipient','draw')]
            key=(t,a,founder,r,d);assert key not in seen;seen.add(key)
            src,new=lookup[t];arr=new[d]
            for c,start in STARTS.items():
                for metric in fields:
                    assert float(row[c+'_'+metric])==float(arr[metric][start+a,founder,r])
                    if 'old_'+metric in src:assert float(row['old_'+c+'_'+metric])==float(src['old_'+metric][start+a,founder,r])
                for q in (0,1):
                    assert float(row[c+'_cue_'+str(q)+'_margin'])==arr['margin'][start+a,founder,r,q]
                    assert float(row['old_'+c+'_cue_'+str(q)+'_margin'])==src['old_margin'][start+a,founder,r,q]
            x=int(arr['both'][22+a,founder,r])-int(arr['both'][18+a,founder,r])
            assert int(row['pattern_effect'])==x
            assert int(row['pruning_h0'])==int(arr['both'][4+a,founder,r])-int(arr['both'][a,founder,r])
            assert int(row['pruning_h1'])==int(arr['both'][13+a,founder,r])-int(arr['both'][9+a,founder,r])
            assert int(row['old_effect'])==int(src['old_both'][22+a,founder,r])-int(src['old_both'][18+a,founder,r])
            stats=recount[cohort(t)];stats['gain']+=x==1;stats['harm']+=x==-1;stats['rows']+=1
    return dict(source_cases=len(means),case_draw_pairs=len(rows),all_rows_independently_checked=True,by_cohort=recount)
