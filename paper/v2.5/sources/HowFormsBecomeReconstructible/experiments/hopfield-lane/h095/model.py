"""Fresh tapes; the frozen H093/H094 physics and writer are reused verbatim."""
import hashlib,json
import numpy as np
from h089 import model as original
from h093 import model as unprotected
from h094 import model as protected
from h094.model import N,R,NY,TRAIN,TEST,PANELS,READERS,ORIGINS,BASELINES,KINDS,ROUTES,X,SCHEMAS
from h094.model import physics_inputs,get_record,get_read,response,digest,observations,native,complete,compile_record,copy_record
SEED,NETWORKS,ENGINEERING=95095,32,4
CONDITIONS=('unprotected','protected')

def rng(cohort,block,stream):
    assert cohort in ('fixture','engineering','confirmation') and int(block)==block and block>=0
    if cohort=='engineering':assert block<ENGINEERING
    if cohort=='confirmation':assert block<NETWORKS
    key=json.dumps([SEED,cohort,int(block),stream],separators=(',',':')).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:16],'little'))

def tapes(cohort,block):
    out={}
    for origin in ORIGINS:
        gen=rng(cohort,block,'rule_'+origin)
        masks=np.r_[np.asarray([1,2,4,8]),gen.integers(1,16,size=44)].astype(np.int8);gen.shuffle(masks)
        signs=gen.choice([-1,1],size=48).astype(np.int8)
        out['rule_masks_'+origin]=masks;out['rule_signs_'+origin]=signs
        out['responses_'+origin]=original.parity_values(original.X,masks)*signs
    out['birth']=rng(cohort,block,'birth').choice([-1,1],size=(3,R,N)).astype(np.int8)
    for phase,count in (('context',4),('gap',4),('query',8)):
        gen=rng(cohort,block,'orders_'+phase)
        out['orders_'+phase]=np.stack([np.stack([gen.permutation(N) for _ in range(count)]) for _ in range(3)])
    return out

def run_tapes(tape,condition):
    assert condition in CONDITIONS
    return (protected if condition=='protected' else unprotected).run_tapes(tape)
