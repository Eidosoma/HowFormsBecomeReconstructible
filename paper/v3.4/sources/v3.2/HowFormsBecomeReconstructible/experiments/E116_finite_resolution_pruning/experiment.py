"""All E112 records, unchanged edge selection, eight finite regimes and shared readers."""
import time
import numpy as np
from common import dump,rng,utc
from E116_finite_resolution_pruning import model,audit,data,dynamics
from E116_finite_resolution_pruning.plan import REGIMES,BODY_FIELDS,panels,panel_indices,key


def assert_dict(a,b):
    assert set(a)==set(b)
    for k in a:data.equal(a[k],b[k],k)


def check_archived(task,source,writer,assays,cfg):
    """Check the exact apparatus and original reference outcome labels, without new dynamics."""
    R=cfg['config']['recipients'];packets=source['packets']
    for phase,g,pkts,body in [('develop',1,packets,writer)]+[
        (f'E098_terminal_{d}',0,np.concatenate((packets,writer['outgoing'])),a)
        for d,a in enumerate(assays)]:
        mask=audit.legacy.masks(task,R,phase+'_injury',g);data.equal(mask,body['masks'],'archive mask')
        stream=audit.legacy.random('E077',task,phase,g)
        birth=cfg['config']['birth_sd']*audit.legacy.pair(stream.standard_normal((2,R,16,16)))
        data.equal(birth,body['birth'],'archive birth')
        n=len(pkts);effective,d,eff,k=audit.structure(pkts,np.broadcast_to(mask,(*pkts.shape[:-1],16,16)),np.zeros(pkts.shape[:-1]))
        for field,val in [('effective',effective),('denominator',d),('coupling',k)]:
            data.equal(val,body[field][:n],field)
        data.equal(body['late_ports'].mean(axis=0),body['mean_ports'],'archive means')
    a=model.capture(writer['end'][:9],model.reader.surviving_edges(writer['masks']),0.)
    b=audit.capture(writer['end'][:9],audit.legacy.alive(writer['masks']),0.)
    assert_dict(a,b);data.equal(a['pre_channel'],writer['outgoing'][:9],'archive capture')
    for k in ('ordinary','contrast','fallback'):data.equal(a[k],writer[k][:9],k)


def initial_records(src,delta):
    original=src['packets'];sel=src['eligible']
    quantized=model.quantize(original,delta)
    data.equal(quantized,audit.quantize(original,delta),'initial grid')
    weights=model.base.decode(quantized)
    pruned=weights[:4].copy();pruned[sel]=0.
    data.equal(model.base.encode(pruned),quantized[4:8],'prune-grid commutation')
    return quantized


DIAG_FIELDS=('available','present_before','present_after','erased_by_grid','restored_before_grid',
             'restored_delivered','sign_changes','fallback','exact_zero_product','near_product',
             'mass_before','mass_after','quantization_l1','ordinary_l1','contrast_l1')


def capture_diagnostics(incoming,cap,outgoing,selected,physical,tau):
    before=model.base.decode(cap['pre_channel']);after=model.base.decode(outgoing)
    old=model.base.decode(incoming);avail=np.broadcast_to(physical,before.shape)
    e=np.concatenate((selected,selected,np.zeros_like(selected[:1])))
    regions=(e&avail,(~e)&avail,avail);values=[]
    for region in regions:
        both=(before!=0)&(after!=0);product=cap['contrast']
        fields=(np.ones_like(region),before!=0,after!=0,(before!=0)&(after==0),
            (old==0)&(before!=0),(old==0)&(after!=0),both&(np.signbit(before)!=np.signbit(after)),
            cap['fallback'],product==0,(abs(product)>0)&(abs(product)<=1e-4),
            abs(before),abs(after),abs(after-before),abs(cap['ordinary']),abs(product))
        values.append(np.stack([(v*region).sum(axis=(-3,-2,-1)) for v in fields],axis=-1))
    return np.stack(values,axis=-2)


def block(mode,task,cfg,run=None):
    started=time.monotonic();source_mode='scientific' if mode=='scientific' else 'benchmark'
    src=data.source(source_mode,f'source_pruning_{task}.npz')
    recovery=data.source(source_mode,f'source_recovery_{task}.npz')
    assert_dict(src,model.old.intervene(recovery));assert_dict(src,audit.legacy.intervene(recovery))
    writer=data.source(source_mode,f'writer_{task}.npz')
    assays=[data.source(source_mode,f'assay_{task}_r{d}.npz') for d in cfg['draws']]
    oldcfg=data.source_settings(source_mode)
    check_archived(task,src,writer,assays,oldcfg)
    cache=dynamics.archived_cache(src['packets'],writer) if mode=='scientific' else {}
    if mode=='benchmark':
        # Excluded timing uses the complete scientific recipient width, not a thin batch.
        src={k:np.repeat(v,cfg['recipients'],axis=2) for k,v in src.items()}
    input_by_q=[initial_records(src,q*2**-16) for q in (0,1)]
    input_weights=[model.base.decode(p) for p in input_by_q]
    inputs=np.stack([input_by_q[q] for f in (0,1) for q in (0,1)])
    if run is not None:dump(run/f'progress_{task}.json',dict(utc=utc(),stage='writer_bodies',task=task))
    bodies,wb=dynamics.resolve(inputs,[0.,0.,1e-4,1e-4],task,cfg,'develop',1,cache,run,'writer')
    # Holding is after this capture, has no path to the inherited record or reader, and is omitted.
    out=[];pre=[];fallback=[];ordinary=[];contrast=[];diagnostics=[]
    physical=model.reader.surviving_edges(bodies['masks'])
    for regime in REGIMES:
        t,f,q=(int(regime['id'][n]) for n in (1,3,5));j=2*f+q
        cap=model.capture(bodies['end'][j],physical,regime['tolerance'])
        assert_dict(cap,audit.capture(bodies['end'][j],physical,regime['tolerance']))
        packet=model.quantize(cap['pre_channel'],regime['grid_step'])
        data.equal(packet,audit.quantize(cap['pre_channel'],regime['grid_step']),'outgoing grid')
        assert not model.base.decode(packet)[np.broadcast_to(~physical,model.base.decode(packet).shape)].any()
        out.append(packet);pre.append(cap['pre_channel']);fallback.append(cap['fallback'])
        ordinary.append(cap['ordinary']);contrast.append(cap['contrast'])
        diagnostics.append(capture_diagnostics(inputs[j],cap,packet,src['eligible'],physical,regime['tolerance']))
    out=np.stack(out)
    if mode=='scientific':data.equal(out[0],writer['outgoing'][:9],'reference outgoing')
    capture=dict(outgoing=out,pre_channel=np.stack(pre),fallback=np.stack(fallback),
        ordinary=np.stack(ordinary),contrast=np.stack(contrast),diagnostics=np.stack(diagnostics),selected=src['eligible'])
    if run is not None:
        data.save(run/f'writer_{task}.npz',bodies);data.save(run/f'capture_{task}.npz',capture)
    layout=panels();packets=[];floors=[]
    for p in layout:
        if p['stage']==0:packets.append(input_by_q[p['q']])
        else:packets.append(out[4*p['t']+2*p['f']+p['q']])
        floors.append(0. if p['common'] else p['f']*1e-4)
    packets=np.stack(packets);rows=[];erased=[];reader_reports=[];records=[]
    oldrows=data.original_rows(source_mode) if mode=='scientific' else None
    for draw in cfg['draws']:
        if run is not None:dump(run/f'progress_{task}.json',dict(utc=utc(),stage='terminal_readers',task=task,draw=draw))
        cache=dynamics.archived_cache(np.concatenate((src['packets'],writer['outgoing'][:9])),
                                     assays[draw]) if mode=='scientific' else {}
        result,rr=dynamics.resolve(packets,floors,task,cfg,f'E098_terminal_{draw}',0,cache,run,f'assay_r{draw}')
        reader_reports.append(rr)
        shape=result['mean_ports'].shape[:-2];founders=result['contexts'][...,0].reshape(-1)
        scores=model.scores(result['mean_ports'].reshape(-1,2,2),founders)
        assert_dict(scores,audit.scores(result['mean_ports'].reshape(-1,2,2),founders))
        scores={k:v.reshape(shape) for k,v in scores.items()}
        result.update({'score_'+k:v for k,v in scores.items()})
        if run is not None:data.save(run/f'assay_{task}_r{draw}.npz',result)
        for regime in REGIMES:
            name=regime['id'];h0,h1=panel_indices(name);_,common=panel_indices(name,True)
            for arm,f,r in np.ndindex(4,4,cfg['recipients']):
                row=dict(task=task,arm=arm,kind='native' if arm<2 else 'mixture',
                    history='sham' if arm%2==0 else 'pulse',founder=f,recipient=r,draw=draw,regime=name)
                for endpoint,p,s in [('I0',h0,arm),('P0',h0,arm+4),('I1',h1,arm),('P1',h1,arm+4),
                                     ('I1_common',common,arm),('P1_common',common,arm+4)]:
                    for metric,value in scores.items():row[endpoint+'_'+metric]=float(value[p,s,f,r])
                    if name=='T0F0Q0' and oldrows is not None and endpoint in ('I0','P0','I1','P1'):
                        oldprefix=endpoint+('_paired' if endpoint.endswith('1') else '')
                        for metric in scores:
                            assert row[endpoint+'_'+metric]==float(oldrows[key(row)][oldprefix+'_'+metric]),(task,endpoint,metric)
                row['immediate_event']=int(row['P0_both']-row['I0_both'])
                row['later_event']=int(row['P1_both']-row['I1_both'])
                row['common_later_event']=int(row['P1_common_both']-row['I1_common_both'])
                sel=src['eligible'][arm,f,r];w=input_weights[int(name[5])][arm,f,r]
                row['selected_edges']=int(sel.sum());row['selected_erased_at_input']=int((sel&(w==0)).sum())
                row['pruning_noop']=not bool((sel&(w!=0)).any())
                rows.append(row)
        for p,f,r in np.ndindex(len(layout),4,cfg['recipients']):
            erased.append(dict(task=task,draw=draw,panel=layout[p]['id'],founder=f,recipient=r,
                               **{k:float(v[p,8,f,r]) for k,v in scores.items()}))
        for p in range(len(layout)):
            for f in (0,2):
                data.equal(packets[p,8,f],packets[p,8,f+1],'erased packets')
                data.equal(result['mean_ports'][p,8,f],result['mean_ports'][p,8,f+1],'erased responses')
                assert not (scores['both'][p,8,f]&scores['both'][p,8,f+1]).any()
        records.append(dict(draw=draw,archive_outcomes=rr['archive_outcomes']))
    elapsed=time.monotonic()-started;dynamics_seconds=wb['seconds']+sum(r['seconds'] for r in reader_reports)
    report=dict(status='PASS',utc=utc(),task=task,seconds=elapsed,writer=wb,readers=reader_reports,
        dynamics_seconds=dynamics_seconds,static_seconds=elapsed-dynamics_seconds,
        total_new_records=wb['new_records']+sum(r['new_records'] for r in reader_reports),
        new_record_steps=wb['new_record_steps']+sum(r['new_record_steps'] for r in reader_reports),
        all_new_steps_independently_replayed=True,original_reference_exact=mode=='scientific',
        all_cases_endpoints_and_harms_retained=True,all_channel_operations_independently_checked=True,
        context_draw_rows=len(rows)//8,condition_rows=len(rows),erased_rows=len(erased))
    if run is not None:
        data.export(run/f'cases_{task}.csv',rows);data.export(run/f'erased_{task}.csv',erased)
        dump(run/f'block_{task}.json',report)
    return rows,erased,report
