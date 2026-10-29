"""One fixed replicate over all blocks; no retries or model fitting."""
import argparse
from pathlib import Path
import os
import resource
import signal
import time
import traceback
import numpy as np
from rr_common import C, ev, read, require, ledger, paired, inherited_verify, inherited, Guard, REGIMES
from rr_streams import adapter
import rr_audit


def run(output, seal, seal_sha, replica, stage, deadline):
    output.mkdir(parents=True,exist_ok=False)
    started,cpu=time.monotonic(),time.process_time()
    def expired(*_): raise TimeoutError('Common deadline or coordinator stop; no retry')
    signal.signal(signal.SIGALRM,expired); signal.signal(signal.SIGTERM,expired)
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.time()))
    try:
        require(ev.sha(seal)==seal_sha,'Pre-future seal changed')
        specification=read(seal)
        require(stage==specification['stage'] and replica in specification['replicates'],'Wrong study stream')
        rows=specification['rows']
        initial=ev.load(seal.parent/'ACTIONS.npz',specification['actions_sha256'])['initial_packets']
        require([[inherited.digest(a) for a in pair] for pair in initial]==specification['branch_sha256'],'Wrong action branches')
        for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
            require(os.environ.get(name)=='1','One numerical thread required')
        ev.write(output/'START.json',dict(utc=ev.utc(),pid=os.getpid(),replicate=replica,stage=stage,deadline_epoch=deadline,seal_sha256=seal_sha))
        ev.status(output,status='RUNNING',stage='futures',replicate=replica)
        guard=Guard(output,deadline)
        paired.environment=adapter(replica)
        references=[]; labels=[]; batch_times=[]
        blocks=sorted({r['block'] for r in rows})
        for block in blocks:
            indices=[i for i,row in enumerate(rows) if row['block']==block]
            selected=[rows[i] for i in indices]
            audit_key=min(selected,key=lambda row:row['selection_hash'])['key']
            for regime in REGIMES:
                guard.check()
                target=output/'futures'/f'block_{block}_{regime}'
                target.mkdir(parents=True)
                begin=time.monotonic()
                receipt,outcomes=paired.batch(selected,initial[indices],audit_key,regime,stage,target,guard,seal,seal_sha)
                check=inherited_verify.continuation(target,selected,initial[indices],regime,stage,seal_sha,audit_key)
                check['replicate_forcing']=rr_audit.forcing(target,replica,stage,audit_key)
                ev.write(target/'VERIFICATION.json',check)
                identity=dict(replicate=replica,stage=stage,block=block,regime=regime,seal_sha256=seal_sha)
                ledger.commit(target,identity,dict(primary_native_reads=receipt['primary_native_reads'],flat_native_reads=receipt['flat_native_reads']))
                references.append(dict(reference=ledger.reference(output,target),identity=identity,indices=indices,audit_key=audit_key))
                labels.extend([dict(**o,replicate=replica) for o in outcomes])
                batch_times.append(time.monotonic()-begin)
                ev.status(output,status='RUNNING',stage='futures',replicate=replica,completed_batches=len(references),total_batches=2*len(blocks))
        for item in references:
            target,_=ledger.referenced(output,item['reference'],item['identity'])
            indices=item['indices']
            inherited_verify.continuation(target,[rows[i] for i in indices],initial[indices],item['identity']['regime'],stage,seal_sha,item['audit_key'])
        require(len(labels)==2*len(rows),'Incomplete replicate')
        require(ev.sha(seal)==seal_sha,'Seal changed during future')
        ev.write(output/'OUTCOMES.json',labels)
        ev.write(output/'FUTURE_REFERENCES.json',references)
        guard.check()
        result=dict(utc=ev.utc(),status='COMPLETE',replicate=replica,stage=stage,seal_sha256=seal_sha,
            records=len(rows),paired_outcomes=len(labels),batches=len(references),batch_wall_seconds=batch_times,
            primary_native_reads=38*len(labels),flat_native_reads=76*len(blocks),wall_seconds=time.monotonic()-started,
            cpu_seconds=time.process_time()-cpu,peak_resident_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        ev.write(output/'COMPLETE.json',result)
        # Nested batch commits are verified above; bind the whole worker separately.
        from rr_common import manifest
        ev.write(output/'OUTPUTS.json',dict(sha256=manifest(output)))
        ev.status(output,status='COMPLETE',stage='complete',replicate=replica)
        print(dict(status='COMPLETE',replicate=replica,wall_seconds=result['wall_seconds']),flush=True)
    except BaseException as error:
        ev.write(output/'FAILED.json',dict(utc=ev.utc(),type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        ev.status(output,status='FAILED',stage='failed',replicate=replica)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seal',type=Path,required=True)
    p.add_argument('--seal-sha',required=True);p.add_argument('--replicate',type=int,required=True)
    p.add_argument('--stage',required=True);p.add_argument('--deadline',type=float,required=True)
    a=p.parse_args();run(a.output,a.seal,a.seal_sha,a.replicate,a.stage,a.deadline)
