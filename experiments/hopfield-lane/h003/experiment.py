"""Prospective H003 intervention on cue coupling during complete rewriting."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import traceback
import numpy as np

HERE=Path(__file__).resolve().parent
LANE=HERE.parent
sys.path.insert(0,str(LANE))
import model as m
import run as h001
from h003.diagnose import categories, LABELS

N,F,R=64,4,4
INPUTS=np.arange(4)
ARMS=h001.ARMS
REGIMES=('cue_gain1','cue_gain2','cue_gain4','decoy_gain4')
GAINS=(1.,2.,4.,4.)
SITES=(INPUTS,INPUTS,INPUTS,np.arange(24,28))


def save(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def effective_weights(base,record,gain,sites):
    selected=np.zeros(base.shape[-1],bool);selected[np.asarray(sites,int)]=True
    incident=selected[:,None]^selected[None,:]
    return (base+record)*np.where(incident,float(gain),1.)


def read_one(record,base,seed,key,gain,sites,sweeps=8):
    birth=h001.bits(m.rng(seed,*key,'birth'),(F,R,2,N))
    orders=h001.orders(seed,*key,'order',sweeps=sweeps)
    weight=effective_weights(base,record,gain,sites)
    shape=(*record.shape[:-2],2,N)
    return m.relax(weight[...,None,:,:],np.broadcast_to(birth,shape),
                   orders,INPUTS,np.array([-1.,1.])[:,None])


def read_all(records,base,seed,key):
    return np.stack([read_one(record,base,seed,key,gain,sites)
                     for record,gain,sites in zip(records,GAINS,SITES)])


def lineage(seed):
    base,founder,initial,cues,stable=h001.acquire(seed,'function')
    p=np.r_[np.arange(8),m.rng(seed,'h003','permutation').permutation(np.arange(8,N))]
    record=np.broadcast_to(initial[None,None,:,None],(4,len(ARMS),F,R,N,N)).copy()
    record[:,ARMS.index('foreign')]=initial[[2,3,0,1],None]
    record[:,ARMS.index('scrambled')]=m.permute_record(initial,p)[:,None]
    record[:,ARMS.index('erased')]=0
    checkpoints=[0,1,4,8,16]
    records=[record.copy()];bodies=[];masks=[];readers=[];success=[];metrics=[];body_success=[]
    for g in range(17):
        if g in checkpoints:
            state=read_all(record,base,seed,('h003','assay',g))
            metric,correct=h001.score(state,'function',founder,cues)
            readers.append(state.astype(np.int8));success.append(correct);metrics.append(metric)
        if g==16:break
        mask=m.mask_edges(m.rng(seed,'h003','damage',g+1),(F,R,N,N),.5)
        surviving=record*mask
        protected=ARMS.index('protected_copy')
        surviving[:,protected]=record[:,protected]
        reading=surviving.copy();reading[:,ARMS.index('read_off')]=0
        state=read_all(reading,base,seed,('h003','body',g+1))
        _,correct=h001.score(state,'function',founder,cues)
        outgoing=m.write_body(state)
        outgoing[:,ARMS.index('write_off')]=0
        outgoing[:,protected]=record[:,protected]
        outgoing[:,ARMS.index('damaged_copy')]=surviving[:,ARMS.index('damaged_copy')]
        a=ARMS.index('writer_scrambled');outgoing[:,a]=m.permute_record(outgoing[:,a],p)
        record=outgoing
        records.append(record.copy());bodies.append(state.astype(np.int8));masks.append(mask);body_success.append(correct)
    late=np.stack([read_one(record[0],base,seed,('h003','assay',16),4.,INPUTS),
                   read_one(record[0],base,seed,('h003','assay',16),1.,INPUTS,sweeps=32)])
    late_metric,late_success=h001.score(late,'function',founder,cues)
    return dict(base=base,founder=founder.astype(np.int8),initial=initial,cues=cues,
        stable_founder=stable.astype(np.int8),permutation=p,checkpoints=np.array(checkpoints),
        regimes=np.array(REGIMES),arms=np.array(ARMS),records=np.stack(records),bodies=np.stack(bodies),
        damage=np.stack(masks),reader_states=np.stack(readers),success=np.stack(success),metric=np.stack(metrics),
        body_success=np.stack(body_success),reader_category=categories(np.stack(readers)),
        body_category=categories(np.stack(bodies)),late_states=late.astype(np.int8),late_success=late_success,
        late_metric=late_metric,late_category=categories(late),late_names=np.array(['late_gain4','long_gain1']))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['benchmark','development'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    out=args.output.resolve()
    if not out.is_relative_to(LANE):parser.error('Output must stay within the lane')
    out.mkdir(parents=True,exist_ok=False)
    config=dict(experiment='H003',mode=args.mode,
        classification='ENGINEERING_BENCHMARK' if args.mode=='benchmark' else 'PROSPECTIVE_DEVELOPMENT',
        seeds=[12900] if args.mode=='benchmark' else list(range(13000,13024)),generations=16,
        regimes=REGIMES,gains=GAINS,gain_sites=[x.tolist() for x in SITES],arms=ARMS,
        neurons=N,founders=F,replicates=R,clamps=INPUTS.tolist(),damage_probability=.5,
        bootstrap_draws=20000,analysis_seed=930003,numpy=np.__version__,python=sys.version,
        started_utc=datetime.now(timezone.utc).isoformat(),pid=os.getpid(),workers=1,
        threads={key:os.environ.get(key) for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']})
    save(out/'config.json',config)
    source=out/'source';source.mkdir()
    for name in ['model.py','run.py','run_python.sh','h003/experiment.py','h003/diagnose.py',
                 'h003/audit.py','h003/analysis.py','h003/fixtures.py','h003/PROTOCOL.md']:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(LANE/name,target)
    save(out/'freeze.json',{str(path.relative_to(out)):checksum(path) for path in
         [out/'config.json',*sorted(p for p in source.rglob('*') if p.is_file())]})
    started=time.perf_counter();save(out/'STATUS.json',dict(state='RUNNING',pid=os.getpid(),completed_blocks=0))
    try:
        # All scientific modules load before the campaign can outlive this turn.
        from h003.audit import audit
        from h003.analysis import analyze
        from h003.fixtures import run_tests
        run_tests(out/'fixtures.log')
        for i,seed in enumerate(config['seeds']):
            np.savez_compressed(out/f'function_{seed}.npz',**lineage(seed))
            save(out/'STATUS.json',dict(state='RUNNING',pid=os.getpid(),completed_blocks=i+1))
            print(f'Completed {i+1}/{len(config["seeds"])} blocks in {time.perf_counter()-started:.1f}s',flush=True)
        simulation_seconds=time.perf_counter()-started
        save(out/'raw_sha256.json',{p.name:checksum(p) for p in sorted(out.glob('*.npz'))})
        audit(out);audit_seconds=time.perf_counter()-started-simulation_seconds
        analyze(out)
        save(out/'checksums.json',{p.name:checksum(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='STATUS.json'})
        save(out/'STATUS.json',dict(state='COMPLETE',completed_blocks=len(config['seeds']),
            elapsed_seconds=time.perf_counter()-started,simulation_seconds=simulation_seconds,audit_seconds=audit_seconds))
        print(out/'REPORT.md',flush=True)
    except BaseException:
        save(out/'STATUS.json',dict(state='FAILED',elapsed_seconds=time.perf_counter()-started,traceback=traceback.format_exc()))
        raise


if __name__=='__main__':main()
