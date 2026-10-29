"""H078 dynamics unchanged; new fixed replication random streams only."""
import hashlib
import json
import numpy as np
from h078.model import (N,NC,NQ,NY,R,CONTEXT,QUERY,RESPONSE,CODES,QUERY_CODES,X,SHIFT,
    SCENARIOS,GAPS,HORIZONS,NEURAL,BASELINES,METHODS,TOL,BUDGET,acquire,energy,
    baseline,history,source_index,packet_for_baseline,load,save,constant_segment,
    SCHEDULES,FEEDBACK,effective,segment,run_tapes,view)

SEED,NETWORKS,ENGINEERING=79079,192,4


def rng(cohort,block,stream):
    assert cohort in ('fixture','engineering','replication') and int(block)==block and block>=0
    if cohort=='engineering':assert block<ENGINEERING
    if cohort=='replication':assert block<NETWORKS
    text=json.dumps([SEED,cohort,int(block),stream],separators=(',',':')).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(text).digest()[:16],'little'))


def tapes(cohort,block):
    gen=rng(cohort,block,'responses');y=np.full((8,NY),-1,dtype=np.int8)
    for row in y:row[gen.permutation(NY)[:NY//2]]=1
    out=dict(responses=y,birth=rng(cohort,block,'birth').choice([-1,1],size=(R,N)).astype(np.int8))
    for phase,count in (('context',4),('gap',4),('query',8)):
        gen=rng(cohort,block,'orders_'+phase)
        out['orders_'+phase]=np.stack([gen.permutation(N) for _ in range(count)])
    return out


def run(cohort,block):
    return run_tapes(tapes(cohort,block))
