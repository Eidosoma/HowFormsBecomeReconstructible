"""Read only completed arrays; retain original endpoints and every source."""
import time
import numpy as np
from common import utc
from E117_saved_finite_sensitivity import data,measure,audit
from E117_saved_finite_sensitivity.plan import REGIMES,ENDPOINTS,FEATURES,EDGE_METRICS,indices,identity,key

FIELDS=('packets','floors','masks','effective','denominator','effective_denominator','coupling','mean_ports',
        'score_both','score_minimum_margin','score_transfer','score_aligned_transfer')

def checked_compare(before,after,masks,selected,before_floor,after_floor):
    e,c,a,b=measure.compare(before,after,masks,selected,before_floor,after_floor)
    ee,cc,aa,bb=audit.compare(before,after,masks,selected,before_floor,after_floor)
    n=data.close(e,ee,'edge metrics')+data.close(c,cc,'cell metrics')
    for x,y in ((a,aa),(b,bb)):
        for k in x:n+=data.close(x[k],y[k],k,exact=True)
    return e,c,a,b,n

def check_archive(body,calculated):
    n=0
    for old,new in (('effective','weights'),('denominator','denominator'),('effective_denominator','effective_denominator'),('coupling','coupling')):
        n+=data.close(body[old],calculated[new],old,exact=True)
    return n

def ratio_fields(row,prefix,num,den):
    for i,name in enumerate(FEATURES):
        n=float(num[i]);d=float(den[i])
        row[prefix+'_'+name]=n/d if d>0 else None
        row[prefix+'_'+name+'_numerator']=n;row[prefix+'_'+name+'_denominator']=d

def block(mode,task,known):
    tick=time.monotonic();checks=0
    writer=data.arrays(mode,f'writer_{task}.npz',('packets','floors','masks','effective','denominator','effective_denominator','coupling'))
    cap=data.arrays(mode,f'capture_{task}.npz',('outgoing','pre_channel','selected','fallback','diagnostics'))
    read_seconds=time.monotonic()-tick;selected=np.concatenate((cap['selected'],cap['selected'],np.zeros_like(cap['selected'][:1])))
    w=measure.decode(writer['packets']);ref=np.broadcast_to(w[0],w.shape)
    edge,cell,a,b,n=checked_compare(ref,w,writer['masks'],selected,0.,writer['floors']);checks+=n+check_archive(writer,b)
    ce,cc,_,_,n=checked_compare(ref,w,writer['masks'],selected,0.,0.);checks+=n
    derived=dict(writer_edge=edge,writer_cell=cell,writer_channel_edge=ce,writer_channel_cell=cc,
                 selected=selected,writer_masks=writer['masks'])
    pre=measure.decode(cap['pre_channel']);post=measure.decode(cap['outgoing'])
    ce,cc,_,_,n=checked_compare(pre,post,writer['masks'],selected,0.,0.);checks+=n
    derived.update(capture_channel_edge=ce,capture_channel_cell=cc)
    assert np.all(ce[::2,...,EDGE_METRICS.index('weight_l1')]==0)
    # Existing E116 channel diagnostics give a separate check on actual erased edge counts/mass.
    existing=cap['diagnostics']
    checks+=data.close(ce[...,EDGE_METRICS.index('lost_edges')],existing[...,3],'capture erasures')
    checks+=data.close(ce[...,EDGE_METRICS.index('reference_mass')],existing[...,10],'capture mass')
    reader_edges=[];reader_cells=[];channel_edges=[];channel_cells=[];allnums=[];alldens=[];rows=[];score_checks=0
    for draw in (0,1):
        start=time.monotonic();body=data.arrays(mode,f'assay_{task}_r{draw}.npz',FIELDS);read_seconds+=time.monotonic()-start
        current=measure.decode(body['packets']);reference=np.stack([current[0] if p<4 else current[4] for p in range(16)])
        edge,cell,a,b,n=checked_compare(reference,current,body['masks'],selected,0.,body['floors']);checks+=n+check_archive(body,b)
        channel_pre=np.stack([w[0] if p<4 else pre[p-4] if p<12 else pre[2+4*((p-12)//2)+(p-12)%2] for p in range(16)])
        ce,cc,_,_,n=checked_compare(channel_pre,current,body['masks'],selected,0.,0.);checks+=n
        # Floors do not alter packets; common readers must carry the same stored record.
        for p in (12,13,14,15):data.close(body['packets'][p],cap['outgoing'][2+4*((p-12)//2)+(p-12)%2],f'common packet {p}',exact=True)
        nums,dens=measure.features(edge,cell,ce)
        f=np.broadcast_to(np.arange(4)[None,None,:,None],body['mean_ports'].shape[:-2])
        scores=audit.scores(body['mean_ports'],f)
        for k,v in scores.items():score_checks+=data.close(v,body['score_'+k],k,exact=True)
        for arm,founder,recipient in np.ndindex(4,4,4):
            reference_row=known[(task,arm,founder,recipient,draw,'T0F0Q0')]
            for reg in REGIMES:
                original=known[(task,arm,founder,recipient,draw,reg)];row=dict(original)
                for k in ('task','arm','founder','recipient','draw','immediate_event','later_event','common_later_event'):row[k]=int(row[k])
                row['reference_immediate_event']=int(reference_row['immediate_event']);row['reference_later_event']=int(reference_row['later_event'])
                h0,h1,common=indices(reg)
                for ep,p,slot in [('I0',h0,arm),('P0',h0,arm+4),('I1',h1,arm),('P1',h1,arm+4),('I1_common',common,arm),('P1_common',common,arm+4)]:
                    loc=p,slot,founder,recipient
                    for metric in scores:
                        assert float(original[ep+'_'+metric])==float(scores[metric][loc]),(ep,metric,loc)
                        score_checks+=1
                    ratio_fields(row,ep,nums[loc],dens[loc])
                row['reference_gain_lost']=row['reference_immediate_event']==1 and row['immediate_event']!=1
                row['reference_gain_retained']=row['reference_immediate_event']==1 and row['immediate_event']==1
                row['reference_later_harm_retained']=row['reference_later_event']==-1 and row['later_event']==-1
                row['reference_later_harm_resolved']=row['reference_later_event']==-1 and row['later_event']!=-1
                rows.append(row)
        reader_edges.append(edge);reader_cells.append(cell);channel_edges.append(ce);channel_cells.append(cc)
        allnums.append(nums);alldens.append(dens)
    derived.update(reader_edge=np.stack(reader_edges),reader_cell=np.stack(reader_cells),
        reader_channel_edge=np.stack(channel_edges),reader_channel_cell=np.stack(channel_cells),
        feature_numerators=np.stack(allnums),feature_denominators=np.stack(alldens))
    assert len(rows)==1024 and len({key(r) for r in rows})==1024
    elapsed=time.monotonic()-tick
    return rows,derived,dict(status='PASS',utc=utc(),task=task,seconds=elapsed,read_seconds=read_seconds,
        measurement_seconds=elapsed-read_seconds,condition_rows=len(rows),independent_metric_values=checks,
        score_values_checked=score_checks,no_new_dynamics=True,all_cases_retained=True,earlier_primary_unchanged=True)
