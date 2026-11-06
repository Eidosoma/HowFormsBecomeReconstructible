"""Entirely fresh ancestry followed by one fixed own-repair pruning comparison."""
import time
import numpy as np
from common import dump,utc
from E022_reader_compensation.audit import source_record
from E116_finite_resolution_pruning import dynamics,model as finite,audit as finite_audit
from E118_finite_formation import model,audit,data
from E118_finite_formation.plan import REGIMES,parameters,EPS

def commit_check(packets):
    data.equal({'packet':model.channel(packets)},{'packet':packets})
    data.equal({'packet':audit.channel(packets)},{'packet':packets})

def ancestor_projection(raw,name):
    old=data.golden(name);got={};wanted={}
    for k in ('incoming','denominator','end','mean_ports','ordinary','contrast','fallback','outgoing'):
        got[k]=raw[k][0];wanted[k]=old[k]
    got.update(masks=raw['masks'],birth=raw['birth'],late_ports=raw['late_ports'][:,0],
               effective_packets=model.base.encode(raw['effective'][0]),read_state_hashes=raw['reference_hashes'])
    wanted.update({k:old[k] for k in ('masks','birth','late_ports','effective_packets','read_state_hashes')})
    data.equal(got,wanted)

def endpoint_projection(raw,name,slots):
    old=data.golden(name);expected={};got={}
    for k in ('end','mean_ports','effective','denominator','coupling','boundary_counts'):
        got[k]=raw[k][0];expected[k]=old[k][:slots]
    got['late_ports']=np.moveaxis(raw['late_ports'][0],3,0);expected['late_ports']=old['late_ports'][:,:slots]
    data.equal(got,expected)

def block(mode,task,cfg,run):
    start=time.monotonic();timings={};new_steps=0;ancestry_steps=0;all_counts=[]
    fixture=mode=='fixture';R=cfg['recipients'];K=len(REGIMES)
    def progress(stage,g=0):dump(run/f'progress_{task}.json',dict(utc=utc(),task=task,stage=stage,generation_verified=g))
    def timed(name,operation):
        t=time.monotonic();v=operation();timings[name]=timings.get(name,0.)+time.monotonic()-t;return v
    def save(name,values):timed('storage',lambda:data.save(run/f'{name}_{task}.npz',values))
    def body(incoming,namespace,g,c,steps,pulse=None):
        nonlocal ancestry_steps
        a=timed(namespace,lambda:model.develop(incoming,task,c,steps,namespace,g,pulse))
        b=timed(namespace,lambda:audit.develop(incoming,task,c,steps,namespace,g,pulse));data.equal(a,b)
        ancestry_steps+=int(np.prod(incoming.shape[:-1]))*steps['read_steps']
        cap=timed('capture',lambda:model.capture(incoming,a['end'],a['masks'],c['writer_beta']))
        other=timed('capture',lambda:audit.capture(incoming,b['end'],b['masks'],c['writer_beta']));data.equal(cap,other)
        commit_check(cap['outgoing']);a.update(cap)
        assert (a['masks'].sum(axis=(-2,-1))==24).all() and not a['masks'][...,model.P.any(axis=0)].any()
        return a
    progress('acquisition')
    acq=timed('acquisition',lambda:model.reader.acquisition.teach(task,model.base.Config(**cfg['source_config'])))
    audited,_=timed('acquisition',lambda:source_record(acq,task,cfg['source_config']))
    data.equal({'a':acq['acquired'][1]},{'a':audited})
    if fixture:data.equal(acq,data.golden(f'acquisition_{task}.npz'))
    save('acquisition',acq)
    pre=np.broadcast_to(acq['acquired'][1,None,:,None],(K,1,4,R,4096)).copy()
    current=model.channel(pre);data.equal({'a':current},{'a':audit.channel(pre)});commit_check(current)
    save('acquired',dict(pre_channel=pre,packets=current))
    for g in range(1,cfg['ancestry_generations']+1):
        a=body(current,'E022',g,cfg['source_config'],cfg['source_steps'])
        if fixture:ancestor_projection(a,f'source_boundary_{task}_g{g}.npz')
        save(f'ancestry_g{g}',a);current=a['outgoing'];progress('ancestry',g)
    progress('pulse')
    p=cfg['body'];c=dict(cfg['source_config'],observe_steps=p['observe_steps'])
    steps=dict(read_steps=p['body_pre_steps']+p['pulse_steps'],settling_steps=p['body_settling_steps'])
    a=body(np.repeat(current,2,axis=1),'E055',0,c,steps,p)
    data.equal({'before':a['before'][:,0]},{'before':a['before'][:,1]})
    assert not (a['pulse_sites']&a['masks']).any() and not a['pulse_sites'][...,model.P.any(axis=0)].any()
    assert (a['pulse_sites'].sum(axis=(-2,-1))==p['pulse_sites']).all()
    if fixture:
        old=data.golden(f'body_{task}.npz')
        data.equal(dict(end=a['end'][0],before=a['before'][0],hashes=a['reference_hashes'],
                        trace=np.moveaxis(a['late_ports'][:,0],0,1),
                        requested=a['requested_squared'][0],delivered=a['delivered_squared'][0]),
                   dict(end=old['states'][0,:,1],before=old['states'][0,:,0],hashes=old['state_hashes'],
                        trace=old['port_windows'][0,:,1],requested=old['requested_squared'][0],delivered=old['delivered_squared'][0]))
        old=data.golden(f'outgoing_{task}.npz');data.equal({'a':a['outgoing'][0]},{'a':old['packets']})
    save('body',a);current=a['outgoing'];initial=current.copy()
    for g in range(1,cfg['continuation_generations']+1):
        a=body(current,'E058',g,cfg['source_config'],cfg['source_steps'])
        if fixture:ancestor_projection(a,f'source_continuation_{task}_g{g}.npz')
        save(f'continuation_g{g}',a);current=a['outgoing'];progress('continuation',g)
    inter=model.mixture(initial,current);data.equal(inter,audit.mixture(initial,current));commit_check(inter['packets'])
    if fixture:
        old=data.golden(f'source_mixture_{task}.npz');data.equal({k:inter[k][0] for k in old},old)
    save('mixture',inter)
    floors=[parameters(r)['floor'] for r in REGIMES]
    def develop(name,packets,phase,g,steps,ff):
        nonlocal new_steps
        c=dict(cfg,steps=steps)
        result,report=timed(name,lambda:dynamics.resolve(packets,ff,task,c,phase,g,{},run,name))
        new_steps+=report['new_record_steps'];all_counts.append(dict(stage=name,**report));return result
    def attach_capture(raw):
        raw['incoming']=raw['packets'].copy()
        a=model.capture(raw['incoming'],raw['end'],raw['masks'],cfg['config']['writer_beta'])
        b=audit.capture(raw['incoming'],raw['end'],raw['masks'],cfg['config']['writer_beta']);data.equal(a,b)
        commit_check(a['outgoing']);raw.update(a);return raw
    progress('recovery')
    recovery=attach_capture(develop('recovery',inter['packets'],'develop',0,cfg['source_steps'],floors))
    if fixture:
        endpoint_projection(recovery,f'source_recovery_{task}.npz',5)
        old=data.golden(f'source_recovery_{task}.npz');data.equal({k:recovery[k][0] for k in ('outgoing','fallback')},{k:old[k] for k in ('outgoing','fallback')})
    save('recovery',recovery)
    pruning=model.prune(recovery);data.equal(pruning,audit.prune(recovery));commit_check(pruning['packets'])
    if fixture:data.equal(dict(packets=pruning['packets'][0],eligible=pruning['selected'][0]),data.golden(f'source_pruning_{task}.npz'))
    w=model.base.decode(pruning['packets']);selected=pruning['selected']
    assert w[:,:4][~selected].tobytes()==w[:,4:8][~selected].tobytes()
    assert not w[:,4:8][selected].any()
    save('pruning',pruning);progress('pruning_writer')
    writer=attach_capture(develop('writer',pruning['packets'],'develop',1,cfg['steps'],floors))
    if fixture:
        endpoint_projection(writer,f'writer_{task}.npz',9)
        old=data.golden(f'writer_{task}.npz');data.equal({'a':writer['outgoing'][0]},{'a':old['outgoing'][:9]})
    save('writer',writer)
    layout=[(i,stage,False) for i in range(K) for stage in (0,1)]
    layout += [(i,1,True) for i in range(K) if floors[i]>0]
    packets=np.stack([pruning['packets'][i] if stage==0 else writer['outgoing'][i] for i,stage,common in layout])
    reader_floors=[0. if common else floors[i] for i,stage,common in layout]
    rows=[];erased=[]
    for draw in cfg['draws']:
        progress('terminal_readers',draw)
        fresh=develop(f'assay_r{draw}',packets,f'E098_terminal_{draw}',0,cfg['steps'],reader_floors)
        shape=fresh['mean_ports'].shape[:-2];f=fresh['contexts'][...,0].reshape(-1)
        s=finite.scores(fresh['mean_ports'].reshape(-1,2,2),f)
        data.equal(s,finite_audit.scores(fresh['mean_ports'].reshape(-1,2,2),f))
        scores={k:v.reshape(shape) for k,v in s.items()};fresh.update({'score_'+k:v for k,v in scores.items()})
        if fixture:
            old=data.golden(f'assay_{task}_r{draw}.npz')
            for i,start_slot in ((0,0),(1,9)):
                data.equal({k:fresh[k][i] for k in ('end','mean_ports','effective','denominator','coupling')},
                           {k:old[k][start_slot:start_slot+9] for k in ('end','mean_ports','effective','denominator','coupling')})
        save(f'assay_r{draw}',fresh)
        for i,reg in enumerate(REGIMES):
            h0=layout.index((i,0,False));h1=layout.index((i,1,False));common=layout.index((i,1,True)) if floors[i] else h1
            for arm,f,r in np.ndindex(4,4,R):
                row=dict(task=task,arm=arm,kind='native' if arm<2 else 'mixture',history='sham' if arm%2==0 else 'pulse',
                         founder=f,recipient=r,draw=draw,regime=reg)
                for ep,p,slot in (('I0',h0,arm),('P0',h0,arm+4),('I1',h1,arm),('P1',h1,arm+4),('I1_common',common,arm),('P1_common',common,arm+4)):
                    for k,v in scores.items():row[ep+'_'+k]=float(v[p,slot,f,r])
                tag=selected[i,arm,f,r];ref=selected[0,arm,f,r];delivered=pruning['delivered_selected'][i,arm,f,r]
                row.update(selected_edges=int(tag.sum()),delivered_selected_edges=int(delivered.sum()),
                    selected_erased_by_grid=int((tag&~delivered).sum()),pruning_noop=not bool(delivered.any()),
                    selected_overlap_reference=int((tag&ref).sum()),selected_only_finite=int((tag&~ref).sum()),
                    selected_only_reference=int((ref&~tag).sum()),immediate_event=int(row['P0_both']-row['I0_both']),
                    later_event=int(row['P1_both']-row['I1_both']),common_later_event=int(row['P1_common_both']-row['I1_common_both']))
                rows.append(row)
        for p,(i,stage,common) in enumerate(layout):
            for f in (0,2):
                data.equal({'a':fresh['mean_ports'][p,8,f]},{'a':fresh['mean_ports'][p,8,f+1]})
                assert not (scores['both'][p,8,f]&scores['both'][p,8,f+1]).any()
            for f,r in np.ndindex(4,R):erased.append(dict(task=task,draw=draw,regime=REGIMES[i],stage=stage,common=common,founder=f,recipient=r,
                **{k:float(v[p,8,f,r]) for k,v in scores.items()}))
    elapsed=time.monotonic()-start
    report=dict(status='PASS',utc=utc(),task=task,seconds=elapsed,timings=timings,endpoint_reports=all_counts,
        ancestry_record_steps=ancestry_steps,endpoint_record_steps=new_steps,
        all_new_steps_independently_replayed=True,finite_from_first_commit=True,own_lineage_donors=True,
        all_cases_endpoints_and_harms_retained=True,excluded_reference_exact=fixture,
        condition_rows=len(rows),context_draw_rows=len(rows)//K,erased_rows=len(erased),
        static_other_seconds=max(0.,elapsed-sum(timings.values())))
    data.export(run/f'cases_{task}.csv',rows);data.export(run/f'erased_{task}.csv',erased);dump(run/f'block_{task}.json',report)
    return rows,erased,report
