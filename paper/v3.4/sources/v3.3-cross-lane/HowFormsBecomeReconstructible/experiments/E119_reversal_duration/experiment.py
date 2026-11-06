"""Finite-budget reviewer tests, preserving each actual outgoing branch."""
import time
import numpy as np
from common import dump,utc
from E022_reader_compensation.audit import source_record
from E119_reversal_duration import model,data
from E119_reversal_duration.plan import REGIMES,regime_parameters

def block(study,mode,task,cfg,run):
    start=time.monotonic();timings={};rows=[];mechanism=[];record_steps=0
    c=cfg['config'];steps=cfg['steps'];R=cfg['recipients']
    def timed(stage,fn):
        t=time.monotonic();v=fn();timings[stage]=timings.get(stage,0.)+time.monotonic()-t;return v
    def save(name,v):timed('storage',lambda:data.save(run/f'{name}_{task}.npz',v))
    def progress(stage,g=0):dump(run/f'progress_{task}.json',dict(utc=utc(),task=task,stage=stage,generation=g))
    def body(name,packets,seed,mask_seed,flags=False,noinj=False,tolerance=None,s=None,pulse=None):
        nonlocal record_steps
        progress(name);st=steps if s is None else s
        result=timed('dynamics',lambda:model.checked_body(packets,task,c,st,seed,mask_seed,flags,noinj,pulse,tolerance))
        record_steps+=int(np.prod(packets.shape[:-1]))*st['read_steps']
        save(name,result);return result
    def append_scores(result,labels,draw,aliases=None):
        sc=model.scores(result)
        for j,label in enumerate(labels):
            slot=j if aliases is None else aliases[j]
            if label['policy']=='E':
                for f0 in (0,2):
                    assert result['mean_ports'][slot,f0].tobytes()==result['mean_ports'][slot,f0+1].tobytes()
                    assert not (sc['both'][slot,f0]&sc['both'][slot,f0+1]).any()
            for f,r in np.ndindex(4,R):
                diag=label.get('diag')
                row={k:v for k,v in label.items() if k!='diag'}
                row.update(task=task,founder=f,recipient=r,draw=draw,
                    selected_edges=int(diag['selected_edges'][f,r]) if diag else 0,
                    reisolated_cells=int(diag['reisolated_cells'][f,r]) if diag else 0,
                    selected_coupling_share=float(diag['selected_coupling_share'][f,r]) if diag else 0.)
                row.update({k:float(v[slot,f,r]) for k,v in sc.items()});rows.append(row)
    def label(reg,proc,policy,arm,g,reader='common',diag=None):
        return dict(regime=reg,renewal_injury=proc,reader=reader,policy=policy,generation=g,
                    kind='erased' if arm==4 else 'native' if arm<2 else 'mixture',
                    history='none' if arm==4 else 'sham' if arm%2==0 else 'pulse',diag=diag)
    def diag_for(d,arm):return {k:v[arm] for k,v in d.items()}
    def assess(name,packets,labels,flags=False):
        flags=np.broadcast_to(np.asarray(flags,dtype=bool),(len(packets),))
        unique=[];seen={};aliases=[]
        for slot in range(len(packets)):
            key=(packets[slot].tobytes(),bool(flags[slot]))
            if key not in seen:seen[key]=len(unique);unique.append(slot)
            aliases.append(seen[key])
        # Byte-identical whole-context records and noise rules need only one read.
        # Aliased observations remain in the table with their original source identity.
        save(name+'_aliases',dict(unique_slots=np.array(unique),aliases=np.array(aliases),
                                  independent_noise=flags))
        for draw in cfg['draws']:
            # Same terminal draws at every horizon, and independent of every writer.
            phase=f'{study}_assessment_{draw}'
            a=body(f'{name}_r{draw}',packets[unique],('reviewer',study,task,phase), (phase+'_injury',0),flags[unique])
            append_scores(a,labels,draw,aliases)
    def mechanism_rows(writer,labels,original_selected,original_reiso,g):
        # Includes all cells and edges; associations cannot establish unique mediation.
        score=model.scores(writer);out=model.base.decode(writer['outgoing'])
        available=model.reader.surviving_edges(writer['masks'])
        x=np.tanh(3.*writer['end']);contrast=(x[:,:,:,0]-x[:,:,:,1])/2
        for slot,l in enumerate(labels):
            e=original_selected[slot];ri=original_reiso[slot]
            active=e&available
            inc=writer['denominator'][slot]
            outd=model.reader.incident_sum(abs(out[slot]))
            for f,r in np.ndindex(4,R):
                a=active[f,r];den=inc[f,r];free=(~writer['masks'][f,r])&~model.P.any(axis=0)
                row={k:v for k,v in l.items() if k!='diag'}
                row.update(task=task,founder=f,recipient=r,generation=g,
                    available_selected=int(a.sum()),fallback_selected=int((a&writer['fallback'][slot,f,r]).sum()),
                    contrast_selected=int((a&~writer['fallback'][slot,f,r]).sum()),
                    selected_outgoing_mass=float((abs(out[slot,f,r])*a).sum()),
                    isolated_before=int(((den==0)&free).sum()),isolated_after=int(((outd[f,r]==0)&free).sum()),
                    returning_reisolated=int((ri[f,r]&free).sum()),
                    returning_reisolated_zero_contrast=int((ri[f,r]&free&(contrast[slot,f,r]==0)).sum()),
                    weak_positive_denominators=int(((den>0)&(den<1e-4)&free).sum()),
                    body_both=float(score['both'][slot,f,r]),body_margin=float(score['minimum_margin'][slot,f,r]))
                mechanism.append(row)
    if study in ('duration','transport'):
        inter=data.starting(study,mode,task,R);save('starting',inter)
        p=inter['packets'];selected=inter['eligible']
        d=model.structure_diagnostics(p[:4],p[4:8],selected);save('initial_structure',d)
        selection9=np.concatenate((selected,selected,np.zeros_like(selected[:1])))
        reiso9=np.concatenate((d['reisolated'],d['reisolated'],np.zeros_like(d['reisolated'][:1])))
        def labels9(reg,proc,g):
            return [label(reg,proc,'I' if a<4 else 'P' if a<8 else 'E',a%4 if a<8 else 4,g,
                          diag=diag_for(d,a%4) if a<8 else None) for a in range(9)]
        if study=='duration':
            assess('initial_assay',np.concatenate((p,p)),
                   labels9('matched_exact','none',0)+labels9('matched_exact','repeated',0))
            for proc in ('none','repeated'):
                current=p.copy()
                for g in range(1,5):
                    labels=labels9('matched_exact',proc,g)
                    incoming=current.copy()
                    a=body(f'{proc}_writer_g{g}',current,('E077',task,'develop',g),
                           ('develop_injury',g),noinj=proc=='none',tolerance=0.)
                    assert a['incoming'].tobytes()==incoming.tobytes()
                    current=a['outgoing'].copy()  # Unconditional: all failures transmit.
                    mechanism_rows(a,labels,selection9,reiso9,g)
                    assess(f'{proc}_g{g}_assay',current,labels)
        else:
            # Exact/tolerant writing shares the very same supplying body per noise regime.
            immediate=[];outgoing=[];labels=[]
            for reg in REGIMES:immediate.extend(labels9(reg,'repeated',0))
            assess('immediate',np.concatenate([p]*4),immediate)
            for independent_noise in (False,True):
                a=body(f'writer_noise_{int(independent_noise)}',p,('E077',task,'develop',1),
                       ('develop_injury',1),independent_noise)
                for tol in (0.,cfg['tolerance']):
                    reg=('independent' if independent_noise else 'matched')+('_tolerant' if tol else '_exact')
                    cap=model.capture(a,tol);data.equal(cap,model.capture(a,tol,True));save('capture_'+reg,cap)
                    full=dict(a,**cap);labs=labels9(reg,'repeated',1)
                    mechanism_rows(full,labs,selection9,reiso9,1)
                    outgoing.append(cap['outgoing']);labels.extend(labs)
            assess('after_writing',np.concatenate(outgoing),labels)
    else:
        assert study=='histories'
        acfg=model.base.Config(**{**c,'teach_steps':cfg['acquisition_steps'],'capture_steps':cfg['acquisition_capture_steps']})
        acq=timed('acquisition',lambda:model.reader.acquisition.teach(task,acfg))
        audited,_=timed('acquisition',lambda:source_record(acq,task,acfg.__dict__))
        assert acq['acquired'][1].tobytes()==audited.tobytes();save('acquisition',acq)
        acquired=np.broadcast_to(acq['acquired'][1,None,:,None],(4,4,R,4096)).copy()
        flags=[regime_parameters(r)['independent'] for r in REGIMES]
        tolerances=[regime_parameters(r)['tolerance'] for r in REGIMES]
        save('committed_acquired',dict(packets=acquired))
        # Native and common-reader acquisition usefulness; no result selects a lineage.
        labs=[dict(label(reg,'repeated','I',0,-1,reader='native'),kind='acquired',history='none') for reg in REGIMES]
        assess('acquired_assay',np.concatenate((acquired,acquired)),labs+[dict(l,reader='common') for l in labs],flags+[False]*4)
        current=acquired
        for g in range(1,33):
            a=body(f'ancestry_g{g}',current,('E022',task,'develop',g),('E121_ancestry_injury',g),flags,tolerance=tolerances)
            current=a['outgoing'].copy()
        # Each regime has its own sham and pulse; the selected cue-noise regime also applies here.
        current=np.repeat(current,2,axis=0);pf=np.repeat(flags,2);pt=np.repeat(tolerances,2)
        pulse=dict(start=steps['read_steps'],amplitude=cfg['pulse_amplitude'],sites=cfg['pulse_sites'],arms=[False,True]*4)
        pulse_steps=dict(steps,read_steps=steps['read_steps']+cfg['pulse_steps'])
        a=body('pulse',current,('E055',task,'current_body'),('E121_current_body_injury',0),pf,
               tolerance=pt,s=pulse_steps,pulse=pulse)
        assert a['before'][::2].tobytes()==a['before'][1::2].tobytes()
        current=a['outgoing'].copy();early=current.copy()
        for g in range(1,4):
            a=body(f'continuation_g{g}',current,('E058',task,'develop',g),('E121_continuation_injury',g),pf,tolerance=pt)
            current=a['outgoing'].copy()
        oldw=model.base.decode(early).reshape(4,2,4,R,2,16,16)
        final=model.base.decode(current).reshape(oldw.shape);common=(oldw!=0)&(final!=0)
        mixed=np.where(common,np.copysign(abs(oldw),final),final)
        source=model.base.encode(np.concatenate((final,mixed,np.zeros_like(final[:,:1])),axis=1).reshape(20,4,R,2,16,16))
        save('mixture',dict(early=early,final=current,common=common,packets=source))
        rf=np.repeat(flags,5);rt=np.repeat(tolerances,5)
        recovery=body('recovery',source,('E077',task,'develop',0),('develop_injury',0),rf,tolerance=rt)
        packets=[];labels=[];allselected=[];allreiso=[];writer_flags=[];writer_tol=[]
        for i,reg in enumerate(REGIMES):
            sl=slice(i*5,(i+1)*5);before=recovery['incoming'][sl];after=recovery['outgoing'][sl]
            fallback=recovery['fallback'][sl]
            sf=model.selection(before[:4],after[:4],fallback[:4],'fallback')
            sr=model.selection(before[:4],after[:4],fallback[:4],'restored')
            pf=model.prune(after[:4],sf);pr=model.prune(after[:4],sr)
            df=model.structure_diagnostics(after[:4],pf,sf);dr=model.structure_diagnostics(after[:4],pr,sr)
            save('selection_'+reg,dict(fallback=sf,restored=sr,**{'fallback_'+k:v for k,v in df.items()},**{'restored_'+k:v for k,v in dr.items()}))
            slots=np.concatenate((after[:4],pf,pr,after[4:5]));packets.append(slots)
            allselected.extend(np.concatenate((sr,sf,sr,np.zeros_like(sr[:1]))))
            allreiso.extend(np.concatenate((dr['reisolated'],df['reisolated'],dr['reisolated'],np.zeros_like(dr['reisolated'][:1]))))
            for j in range(13):
                arm=j%4 if j<12 else 4;policy='I' if j<4 else 'PF' if j<8 else 'PR' if j<12 else 'E'
                labels.append(label(reg,'repeated',policy,arm,0,diag=diag_for(df if policy=='PF' else dr,arm) if arm<4 else None))
            writer_flags.extend([flags[i]]*13);writer_tol.extend([tolerances[i]]*13)
        packets=np.concatenate(packets);save('starting',dict(packets=packets,selected=np.array(allselected)))
        # Common terminal environment isolates record differences; native readers assess whole-regime usefulness.
        assay_labels=labels+[dict(l,reader='native') for l in labels]
        assay_flags=[False]*len(labels)+writer_flags
        assess('immediate_assay',np.concatenate((packets,packets)),assay_labels,assay_flags)
        writer=body('writer',packets,('E077',task,'develop',1),('develop_injury',1),writer_flags,tolerance=writer_tol)
        mechanism_rows(writer,labels,np.array(allselected),np.array(allreiso),1)
        assess('after_writing_assay',np.concatenate((writer['outgoing'],writer['outgoing'])),
               [dict(l,generation=1) for l in assay_labels],assay_flags)
    data.export(run/f'cases_{task}.csv',rows)
    if mechanism:data.export(run/f'mechanism_{task}.csv',mechanism)
    report=dict(status='PASS',utc=utc(),task=task,study=study,seconds=time.monotonic()-start,
        timings=timings,record_steps=record_steps,all_new_steps_independently_replayed=True,
        all_cases_retained=True,assessment_feedback=False,transmit_after_failure=True,
        rows=len(rows),mechanism_rows=len(mechanism))
    dump(run/f'block_{task}.json',report);return rows,mechanism,report
