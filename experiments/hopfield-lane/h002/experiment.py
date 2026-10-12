"""H002: fresh bodies, complete versus retained writing, paired cue support."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import time
import traceback
import numpy as np

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
sys.path.insert(0, str(LANE))
import model as m
import run as h001
sys.path.insert(0, str(HERE))

ARMS = h001.ARMS
SUPPORT = (8, 4)
WRITERS = ('complete', 'retained')
RETENTION = np.array([0., .5])[None, :, None, None, None, None, None]
N, F, R = h001.N, h001.F, h001.R


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def fresh_reader(records, base, seed, key, cues):
    birth = h001.bits(m.rng(seed, *key, 'birth'), (F, R, len(cues), N))
    orders = h001.orders(seed, *key, 'order')
    states = []
    for support, matrix in zip(SUPPORT, records):
        shape = (*matrix.shape[:-2], len(cues), N)
        states.append(m.relax(base + matrix[..., None, :, :], np.broadcast_to(birth, shape),
                              orders, np.arange(support), cues[:, None]))
    return np.stack(states)


def next_record(body, surviving, prior, permutation):
    """Explicit writer interventions; complete writing uses only body activity."""
    body_component = m.write_body(body)
    body_component[:, :, ARMS.index('write_off')] = 0
    j = ARMS.index('writer_scrambled')
    body_component[:, :, j] = m.permute_record(body_component[:, :, j], permutation)
    outgoing = (1-RETENTION)*body_component + RETENTION*surviving
    outgoing[:, :, ARMS.index('protected_copy')] = prior[:, :, ARMS.index('protected_copy')]
    outgoing[:, :, ARMS.index('damaged_copy')] = surviving[:, :, ARMS.index('damaged_copy')]
    return outgoing


def lineage(seed, task, generations):
    base, founder, initial, cues, stable = h001.acquire(seed, task)
    permutation = np.r_[h001.INPUTS, m.rng(seed,task,'permutation').permutation(np.arange(8,N))]
    foreign = np.roll(initial,-1,axis=0) if task=='capture' else initial[[2,3,0,1]]
    record = np.broadcast_to(initial[None,None,None,:,None], (2,2,len(ARMS),F,R,N,N)).copy()
    record[:,:,ARMS.index('foreign')] = foreign[:,None]
    record[:,:,ARMS.index('scrambled')] = m.permute_record(initial,permutation)[:,None]
    record[:,:,ARMS.index('erased')] = 0
    checkpoints = sorted(set([0,generations]+[g for g in (1,4,8,16) if g<=generations]))
    records, bodies, damage, reads, success, metric, body_success = [record.copy()],[],[],[],[],[],[]
    body_metric = []
    for g in range(generations+1):
        if g in checkpoints:
            state = fresh_reader(record,base,seed,(task,'h002_assay',g),cues)
            score, passed = h001.score(state,task,founder,cues)
            reads.append(state.astype(np.int8)); success.append(passed); metric.append(score)
        if g==generations:
            break
        mask = m.mask_edges(m.rng(seed,task,'h002_damage',g+1),(F,R,N,N),.5)
        surviving = record*mask
        protected = ARMS.index('protected_copy')
        surviving[:,:,protected] = record[:,:,protected]
        reading = surviving.copy(); reading[:,:,ARMS.index('read_off')] = 0
        body = fresh_reader(reading,base,seed,(task,'h002_body',g+1),cues)
        score, passed = h001.score(body,task,founder,cues)
        record = next_record(body,surviving,record,permutation)
        records.append(record.copy()); bodies.append(body.astype(np.int8)); damage.append(mask)
        body_success.append(passed); body_metric.append(score)
    return dict(base=base,founder=founder.astype(np.int8),initial=initial,stable_founder=stable.astype(np.int8),
        cues=cues,permutation=permutation,checkpoints=np.array(checkpoints),arms=np.array(ARMS),
        support=np.array(SUPPORT),writers=np.array(WRITERS),records=np.stack(records),bodies=np.stack(bodies),
        damage=np.stack(damage),reader_states=np.stack(reads),success=np.stack(success),metric=np.stack(metric),
        body_success=np.stack(body_success),body_metric=np.stack(body_metric))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['benchmark','development'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    out=args.output.resolve()
    if not out.is_relative_to(LANE):
        parser.error('Outputs must remain within this lane')
    out.mkdir(parents=True,exist_ok=False)
    config=dict(experiment='H002',classification='ENGINEERING_BENCHMARK' if args.mode=='benchmark' else 'PROSPECTIVE_DEVELOPMENT',
        seeds=[11900] if args.mode=='benchmark' else list(range(12000,12024)),
        generations=2 if args.mode=='benchmark' else 16,
        mode=args.mode,arms=ARMS,writers=WRITERS,support=SUPPORT,neurons=N,founders=F,replicates=R,
        retention=[0.,.5],damage_probability=.5,bootstrap_draws=20000,analysis_seed=920002,
        started_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),numpy=np.__version__,
        pid=os.getpid(),threads={key:os.environ.get(key) for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']})
    write_json(out/'config.json',config)
    source=out/'source'; source.mkdir()
    for path, name in [(HERE/'experiment.py','h002/experiment.py'),(HERE/'analysis.py','h002/analysis.py'),
                       (HERE/'audit.py','h002/audit.py'),(HERE/'PROTOCOL.md','h002/PROTOCOL.md'),
                       (LANE/'model.py','model.py'),(LANE/'run.py','run.py'),
                       (LANE/'run_python.sh','run_python.sh')]:
        target=source/name;target.parent.mkdir(exist_ok=True,parents=True)
        shutil.copyfile(path,target)
    write_json(out/'freeze.json',{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [out/'config.json',*sorted(p for p in source.rglob('*') if p.is_file())]})
    started=time.perf_counter()
    write_json(out/'STATUS.json',dict(state='RUNNING',completed_blocks=0,pid=os.getpid()))
    try:
        # Load our audit/analysis before long computation; later workspace edits
        # cannot change the in-memory run's analysis implementation.
        import audit
        import analysis
        for index, seed in enumerate(config['seeds']):
            for task in ['capture','function']:
                np.savez_compressed(out/f'{task}_{seed}.npz',**lineage(seed,task,config['generations']))
            write_json(out/'STATUS.json',dict(state='RUNNING',completed_blocks=index+1,pid=os.getpid()))
            print(f'Completed {index+1}/{len(config["seeds"])} blocks in {time.perf_counter()-started:.1f}s',flush=True)
        write_json(out/'raw_sha256.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.npz'))})
        audit.audit(out)
        analysis.analyze(out)
        write_json(out/'STATUS.json',dict(state='COMPLETE',completed_blocks=len(config['seeds']),elapsed_seconds=time.perf_counter()-started))
        print((out/'REPORT.md').as_posix(),flush=True)
    except BaseException:
        write_json(out/'STATUS.json',dict(state='FAILED',elapsed_seconds=time.perf_counter()-started,traceback=traceback.format_exc()))
        raise


if __name__=='__main__':
    main()
