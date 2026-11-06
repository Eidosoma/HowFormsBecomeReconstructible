"""Continue exact E014 records, preserving native fields only at declared checkpoints."""
import hashlib,json,time
from dataclasses import asdict
import numpy as np
from common import dump,sha,utc
from E122_specificity_ceiling_and_tail import sources,dynamics,audit
from E122_specificity_ceiling_and_tail.plan import ROOT,CFG,CHECKPOINTS,OLD,AUDIT_GENERATIONS,ROUTES

def packet_hashes(p):
    return np.array([hashlib.sha256(x.tobytes()).hexdigest().encode() for x in p.reshape(-1,p.shape[-1])],dtype='S64').reshape(p.shape[:-1])

def factor(mode,block,factor,run,renewal_cfg=CFG):
    assert renewal_cfg==CFG or mode=='benchmark'
    started=time.monotonic();timings={}; replayed=[]
    def timed(key,fn):
        t=time.monotonic();result=fn();timings[key]=timings.get(key,0.)+time.monotonic()-t;return result
    def progress(stage,g):dump(run/f'progress_{block}.json',dict(utc=utc(),block=block,factor=factor,stage=stage,generation=g))
    old=timed('source_load',lambda:sources.load(mode,block,factor))
    protected=old['incoming'][0][:,:,[7,1]].copy()
    np.testing.assert_array_equal(protected[:,:,0],old['incoming'][0][:,:,0])
    for f in range(4):np.testing.assert_array_equal(protected[f,:,1],protected[(f+1)%4,:,0])
    current=old['outgoing'][-1,:,:,:2].copy()
    assert current.shape==(4,2,2,2048//factor**2)
    boundary=[current.copy()]; checkpoint={}; read_counts=[];written_counts=[]
    def probe(g,packet,writer_incoming,writer_read,writer_written):
        panel=np.concatenate((packet,protected),axis=2)
        before=packet.tobytes()
        state,birth,mask=timed('checkpoint_reads',lambda:dynamics.read(panel,block,'terminal',factor))
        independent=timed('checkpoint_audit',lambda:audit.read(panel,block,'terminal',factor))
        for a,b in zip((state,birth,mask),independent):np.testing.assert_array_equal(a,b)
        assert packet.tobytes()==before
        count=dynamics.counts(state,old['prototype']);audit.counts(state,old['prototype'],count)
        if g in OLD:
            j=OLD.index(g)
            np.testing.assert_array_equal(state[:,:,:3],old['checkpoint_read'][j][:,:,[0,1,7]])
            np.testing.assert_array_equal(panel[:,:,:3],old['checkpoint_packets'][j][:,:,[0,1,7]])
            np.testing.assert_array_equal(birth,old['checkpoint_birth'][j]);np.testing.assert_array_equal(mask,old['checkpoint_mask'][j])
        if checkpoint:
            first=checkpoint[1]
            np.testing.assert_array_equal(state[:,:,2:],first['state'][:,:,2:])
            np.testing.assert_array_equal(birth,first['birth']);np.testing.assert_array_equal(mask,first['mask'])
        checkpoint[g]=dict(packet=panel,state=state,birth=birth,mask=mask,joint=count,
            pair_counts=dynamics.pair_counts(state,old['prototype']),writer_incoming=writer_incoming.copy(),
            writer_outgoing=packet.copy(),writer_read=writer_read.copy(),writer_written=writer_written.copy())
    for j,g in enumerate(OLD):
        progress('retained_checkpoint_and_protected_foreign',g)
        probe(g,old['outgoing'][g-1,:,:,:2],old['incoming'][g-1,:,:,:2],
              old['generation_read'][g-1,:,:,:2],old['generation_written'][g-1,:,:,:2])
    for g in range(17,257):
        progress('actual_rewrite',g);incoming=current.copy()
        current,body=timed('renewal',lambda:dynamics.generation(incoming,block,g,factor,renewal_cfg))
        assert np.isfinite(body['written']).all()
        np.testing.assert_array_equal(incoming,boundary[-1])
        np.testing.assert_array_equal(dynamics.tissue.pack(body['written'][:,:,:,3],factor),current)
        boundary.append(current.copy())
        read_counts.append(dynamics.counts(body['read'],old['prototype']))
        written_counts.append(dynamics.counts(body['written'],old['prototype']))
        if g in AUDIT_GENERATIONS:
            replay,detail=timed('renewal_audit',lambda:audit.generation(incoming,block,g,factor,renewal_cfg))
            np.testing.assert_array_equal(replay,current);audit.compare(detail,body);replayed.append(g)
        if g in CHECKPOINTS:
            probe(g,current,incoming,body['read'],body['written'])
    arrays={k:old[k] for k in ('prototype','prototype_halves','background')}
    arrays.update(boundary_numbers=np.arange(16,257,dtype=np.int16),boundary_packets=np.stack(boundary),
        checkpoints=np.array(CHECKPOINTS,dtype=np.int16),protected_packets=protected,
        generation_numbers=np.arange(17,257,dtype=np.int16),
        generation_read_joint=np.stack(read_counts),generation_written_joint=np.stack(written_counts))
    arrays['boundary_sha256']=packet_hashes(arrays['boundary_packets'])
    for name in checkpoint[1]:arrays['checkpoint_'+name]=np.stack([checkpoint[g][name] for g in CHECKPOINTS])
    path=run/f'block_{block:06d}_factor_{factor}.npz'
    timed('storage',lambda:np.savez_compressed(path,**arrays))
    with np.load(path,allow_pickle=False) as stored:
        for name,v in arrays.items():np.testing.assert_array_equal(stored[name],v)
    meta=dict(status='PASS',utc=utc(),block=block,factor=factor,packet_bytes=2048//factor**2,
        file=str(path.relative_to(ROOT)),sha256=sha(path),bytes=path.stat().st_size,
        seconds=time.monotonic()-started,timings=timings,renewal_generations=240,
        renewal_config=asdict(renewal_cfg),technical_short_dynamics=renewal_cfg!=CFG,
        independent_replay_generations=replayed,independent_checkpoint_reads=len(CHECKPOINTS),
        early_checkpoint_projection_exact=True,protected_copy_exact=True,observer_feedback=False,
        all_founders_and_recipients_retained=True,all_steps_replayed=False,
        historical_donor_by_founder_route=[[f,(f+1)%4,f,(f+1)%4] for f in range(4)],
        native_target_by_founder=list(range(4)),route_order=list(ROUTES),
        source_files=[str((sources.root(mode)/n).relative_to(ROOT)) for n in
                      (f'source_{block:06d}.npz',f'block_{block:06d}_factor_{factor}.npz')],
        arrays={k:dict(shape=list(v.shape),native_dtype=str(v.dtype),exported_dtype=str(v.dtype),
                       bytes=v.nbytes,lossy_conversion=False) for k,v in arrays.items()},
        boundary_notes='Checkpoint packet enters an independent nonwriting reader; writer fields are the actual preceding lifecycle. Prototypes are evaluator resources; donor labels are metadata only.')
    dump(run/f'block_{block:06d}_factor_{factor}.json',meta);return meta

def block(mode,block,run):
    started=time.monotonic();sources.verify(mode,block)
    reports=[factor(mode,block,f,run) for f in (1,4)]
    # Both budget readers have identical nuisance streams and masks.
    with np.load(run/f'block_{block:06d}_factor_1.npz') as a,np.load(run/f'block_{block:06d}_factor_4.npz') as b:
        for k in ('checkpoint_birth','checkpoint_mask','prototype','prototype_halves','background'):
            np.testing.assert_array_equal(a[k],b[k])
    result=dict(status='PASS',utc=utc(),block=block,seconds=time.monotonic()-started,
                factors=reports,paired_budget_streams_exact=True)
    dump(run/f'block_{block:06d}.json',result);return result
