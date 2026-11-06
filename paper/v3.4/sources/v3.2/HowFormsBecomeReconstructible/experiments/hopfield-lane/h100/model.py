"""Fresh H095-family tapes; unchanged H094 physics and H099 calibration learner."""
import hashlib,json
import numpy as np
from h095.model import N,R,NY,TRAIN,TEST,PANELS,READERS,ORIGINS,BASELINES,KINDS,ROUTES,X,SCHEMAS
from h095.model import physics_inputs,get_record,get_read,response,digest,observations,native,complete,compile_record,copy_record
from h095 import model as previous
from h094.model import run_tapes
from h099 import calibration
from h099.engineering import measured_reference

SEED,NETWORKS,ENGINEERING=100100,32,4
MODES=('retained','erased_no_reference','erased_reference_repair')
SPACES=('canonical','physical')
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
        out['responses_'+origin]=previous.original.parity_values(previous.original.X,masks)*signs
    out['birth']=rng(cohort,block,'birth').choice([-1,1],size=(3,R,N)).astype(np.int8)
    for phase,count in (('context',4),('gap',4),('query',8)):
        gen=rng(cohort,block,'orders_'+phase)
        out['orders_'+phase]=np.stack([np.stack([gen.permutation(N) for _ in range(count)]) for _ in range(3)])
    out['calibration_polarity']=rng(cohort,block,'calibration').choice([-1,1],size=48).astype(np.int8)
    return out
def task_digest(tape):return digest({k:v for k,v in tape.items() if k.startswith('responses_')})
def core_tape(tape,space):
    assert space in SPACES
    out={k:v.copy() for k,v in tape.items() if k!='calibration_polarity'}
    if space=='physical':
        d=tape['calibration_polarity'];out['birth'][...,80:]*=d
        for origin in ORIGINS:
            out['responses_'+origin]*=d;out['rule_signs_'+origin]*=d
    return out
def calibration_bank(polarity):
    signs=np.zeros((3,3,4,48),dtype=np.int8);known=np.zeros_like(signs,dtype=bool)
    erased_signs=np.zeros_like(signs);erased_known=np.zeros_like(known)
    commands=np.empty((3,4,2,48),dtype=np.int8);measured=np.empty_like(commands);observed=np.ones_like(commands,dtype=bool)
    for g in range(3):
        for b in range(4):
            packet=measured_reference(polarity)
            commands[g,b]=packet['reference_commands'];measured[g,b]=packet['measured_responses']
            for mi,mode in enumerate(MODES):
                if g==0:book=calibration.learn(packet)
                else:
                    prior=dict(signs=signs[mi,g-1,b],known=known[mi,g-1,b])
                    if mode=='retained':book={k:v.copy() for k,v in prior.items()}
                    else:
                        removed=calibration.erase(prior);erased_signs[mi,g,b]=removed['signs'];erased_known[mi,g,b]=removed['known']
                        supplied=packet if mode=='erased_reference_repair' else {k:v[:0].copy() for k,v in packet.items()}
                        book=calibration.learn(supplied)
                signs[mi,g,b]=book['signs'];known[mi,g,b]=book['known']
    return dict(signs=signs,known=known,erased_signs=erased_signs,erased_known=erased_known,
        reference_commands=commands,measured_responses=measured,observed=observed)
