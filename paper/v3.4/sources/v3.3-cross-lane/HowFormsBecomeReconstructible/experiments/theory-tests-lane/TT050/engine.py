"""One complete causal block, with sealed inputs and independent native replay."""
from study import *
import time, traceback
import checks
from interventions import construct, capture_controls
from instrument import record, summarize

def block(path,block_id,technical=False,short=False):
    path=Path(path);path.mkdir();started=time.monotonic();timings={}
    cfg=dict(CONFIG);steps=dict(STEPS)
    if short:cfg.update(recipients=1,observe_steps=8);steps.update(read_steps=32,settling_steps=16)
    task=900041 if technical else block_id
    def stage(name,fn):
        guard(path);replace(path/'STATUS.json',dict(status='RUNNING',stage=name,utc=now()))
        t=time.monotonic();v=fn();timings[name]=time.monotonic()-t;return v
    try:
        inter,legacy=source(task,technical,recipients=cfg['recipients'])
        incoming,meta=stage('construct',lambda:construct(inter['packets'],inter['eligible']))
        audit=checks.controls(inter['packets'],inter['eligible'],incoming,meta)
        save(path/'PREPARED.npz',dict(packets=incoming,eligible=inter['eligible'],**meta))
        write(path/'SEALED.json',dict(utc=now(),prepared_sha256=sha(path/'PREPARED.npz'),
            received_future_outcomes=False,writer_injury_used_for_construction=False,construction_audit=audit,
            source_block=task,run_block=block_id,technical=technical,short=short))
        ref=np.concatenate([incoming[:4]]*len(ARMS));eligible=np.concatenate([inter['eligible']]*len(ARMS))
        initial=stage('initial_instrumentation',lambda:record(incoming,ref,eligible))
        save(path/'INITIAL_STRUCTURE.npz',initial)
        writer=stage('writer_and_independent_replay',lambda:native.checked_body(incoming,task,cfg,steps,
            ('E077',task,'develop',1),('develop_injury',1),tolerance=0.))
        bridge=False
        if not technical:
            for k in ('incoming','outgoing','end','late_ports','mean_ports','effective','denominator','coupling','ordinary','contrast','fallback'):
                axis=1 if k=='late_ports' else 0
                a=np.take(writer[k],range(8),axis=axis);b=np.take(legacy[k],range(8),axis=axis)
                assert a.tobytes()==b.tobytes(),f'E077 scientific writer bridge {k}'
            bridge=True
        save(path/'WRITER.npz',writer)
        writing=stage('writer_instrumentation',lambda:record(incoming,ref,eligible,writer['masks'],writer))
        save(path/'WRITER_STRUCTURE.npz',writing)
        outref=np.concatenate([writer['outgoing'][:4]]*len(ARMS))
        outgoing=stage('outgoing_instrumentation',lambda:record(writer['outgoing'],outref,eligible))
        save(path/'OUTGOING_STRUCTURE.npz',outgoing)
        extra,support=stage('capture_controls',lambda:capture_controls(writer,inter['eligible']))
        checks.capture(writer,inter['eligible'],extra)
        save(path/'CAPTURE_CONTROLS.npz',dict(packets=extra,**support))
        all_packets=np.concatenate((incoming,writer['outgoing'],extra))
        save(path/'TERMINAL_PACKETS.npz',dict(packets=all_packets))
        write(path/'TERMINAL_SEAL.json',dict(utc=now(),sha256=sha(path/'TERMINAL_PACKETS.npz'),
            labels=LABELS,feedback=False,draws=[0,1]))
        for draw in (0,1):
            phase=f'duration_assessment_{draw}'
            body=stage(f'reader_{draw}_and_independent_replay',lambda:native.checked_body(all_packets,task,cfg,steps,
                ('reviewer','duration',task,phase),(phase+'_injury',0)))
            score=native.scores(body);save(path/f'READER_{draw}.npz',body);save(path/f'SCORES_{draw}.npz',score)
            del body
        body_score=native.scores(writer);save(path/'BODY_SCORES.npz',body_score)
        flat={}
        for prefix,data in [('initial',initial),('writer',writing),('outgoing',outgoing)]:
            flat.update({prefix+'_'+k:v for k,v in summarize(data).items()})
        save(path/'MECHANISM_SUMMARY.npz',flat)
        guard(path)
        write(path/'COMPLETE.json',dict(status='COMPLETE',utc=now(),block=block_id,source_block=task,
            technical=technical,short=short,seconds=time.monotonic()-started,timings=timings,
            independent_replay=True,construction_audit=audit,E077_writer_bridge=bridge,
            config=cfg,steps=steps,arms=ARMS,labels=LABELS,records=int(np.prod(inter['eligible'].shape[:3])),
            outputs={p.name:sha(p) for p in sorted(path.iterdir()) if p.is_file() and p.name!='STATUS.json'},
            bytes=size(path)))
        replace(path/'STATUS.json',dict(status='COMPLETE',utc=now()))
        return read(path/'COMPLETE.json')
    except BaseException:
        replace(path/'STATUS.json',dict(status='FAILED',utc=now(),traceback=traceback.format_exc()))
        raise

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('path');p.add_argument('block',type=int)
    p.add_argument('--technical',action='store_true');p.add_argument('--short',action='store_true')
    args=p.parse_args();verify_inputs();result=block(args.path,args.block,args.technical,args.short)
    print(json.dumps({k:result[k] for k in ('status','block','seconds','bytes')}),flush=True)

