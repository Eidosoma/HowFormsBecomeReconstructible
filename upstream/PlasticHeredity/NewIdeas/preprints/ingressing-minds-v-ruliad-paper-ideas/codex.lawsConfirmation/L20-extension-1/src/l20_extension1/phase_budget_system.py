"""D146: equal extra update budget for fresh reading versus rewriting."""
from dataclasses import asdict, dataclass
from functools import lru_cache
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from . import diagnostics as dev

ROOT=dev.ROOT
SOURCE_RUN='l20_extension1_serial_compatible_feedback_v1_attempt1'
SOURCE_COMPLETE_SHA='adf150141ae7c5b200de105f480ce6544edc9bdcb9a5d3fb8e56477efaa03d88'
TAG='l20-extension1-phase-budget-v1'
BLOCKS=tuple(range(93000,93016)); DISPOSABLE=514246
CONFIG=old.CONFIG
LEVELS=((4,),(4,))
TIMINGS={'base':(300,1000),'read':(600,1000),'write':(300,1300)}
KINDS=tuple(t+s for t in TIMINGS for s in ('','_copy','_read_off','_write_off'))

@dataclass(frozen=True)
class PhaseConfig(old.Config):
    def __post_init__(self):
        super().__post_init__()
        if (self.steps,self.source_steps) not in TIMINGS.values():
            raise ValueError('only three registered phase budgets')
    @property
    def read_times(self):
        return (0,1,100,101,300,600) if self.steps==600 else (0,1,100,101,200,300)
    @property
    def source_times(self):
        return (0,1,300,1000,1300) if self.source_steps==1300 else (0,1,300,500,1000)

def phase_config(kind):
    if kind not in KINDS:raise ValueError('declared timing/control required')
    reading,writing=TIMINGS[kind.split('_')[0]]
    return PhaseConfig(steps=reading,source_steps=writing)

GENERATIONS=(1,2,3)
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
PHASES=tuple(f'g{g}:{p}' for g in GENERATIONS for p in ('birth','read','write','terminal_birth','terminal_read'))
FOUNDER_KEYS=('native_theta','theta0','parent_birth','settled','targets','founder_states',
    'founder_packets','pre_states','source_starts','source_shift','source_states','written_fields')


def validate(index,life,noise=None):
    if type(index) is not int or index not in BLOCKS+(DISPOSABLE,) or type(life) is not int or life not in range(4):
        raise ValueError('declared fresh/disposable block and life required')
    if noise is not None and (type(noise) is not int or noise not in (0,1)): raise ValueError('two noise replicates only')


def rng(index,life,noise,phase):
    validate(index,life,noise)
    if phase not in PHASES: raise ValueError('declared physics phase required')
    return old.generator(TAG,index,life,f'noise{noise}:{phase}')


@lru_cache(maxsize=4,typed=True)
def members(role,quarter):
    if type(role) is not int or role not in (0,1) or type(quarter) is not int or quarter not in LEVELS[role]:
        raise ValueError('declared role/geometry class required')
    t=dev.targets()[role]
    result=np.array([divmod(i,16) for i in range(1,256)
        if np.mean(t*np.roll(t,divmod(i,16),(0,1)))==quarter/4],np.int64)
    result.setflags(write=False)
    return result


def address(index,life,noise,role,kind,generation):
    validate(index,life,noise)
    if type(role) is not int or (role,kind) not in CASES: raise ValueError('declared condition required')
    if type(generation) is not int or generation not in GENERATIONS: raise ValueError('three generations required')
    pool=members(role,4)
    random=old.generator(TAG,index,life,f'address:noise{noise}:role{role}:q4:g{generation}')
    return pool[int(random.integers(len(pool)))].copy()


def schedule(index):
    validate(index,0)
    return np.stack([np.stack([np.stack([np.stack([address(index,l,n,r,k,g) for g in GENERATIONS])
        for r,k in CASES]) for n in (0,1)]) for l in range(4)])


def generate_founders(index,life):
    """Literal existing acquisition/source-writing sequence, new index and tag."""
    validate(index,life); cfg=CONFIG; random=lambda phase:old.generator(TAG,index,life,phase)
    ctx=old.context(index); targets=old.previous.acquisition.capacity.target_fields(ctx)
    native,theta,birth,settled,seeds=old.previous.common_parent_streams(ctx,random('parent_birth'),random('parent_settle'),cfg)
    acquired=[old.previous.acquire_streams(settled,theta,targets[r],ctx,random('teaching'),cfg) for r in (0,1)]
    founders=np.stack([x[0] for x in acquired]); incoming=[old.encode(founders[r,-1,3]) for r in (0,1)]
    before=[old.previous.read_streams(b,ctx,random('source_birth'),random('source_read'),cfg,True) for b in incoming]
    pre=np.stack([x[0] for x in before]); starts=pre[:,-1]
    shift=np.asarray(divmod(int(random('source_shift').integers(1,256)),16),np.int64)
    writes=[[old.previous.source_path_write(starts[r],ctx,random('source_write'),mode,shift,cfg)
        for mode in ('translated','aligned')] for r in (0,1)]
    paths=np.stack([np.stack([x[0] for x in row]) for row in writes])
    fields=np.stack([np.stack([old.record(ref) for ref in row]) for row in paths[:,:,-1,2]])
    raw=dict(native_theta=native,theta0=theta,parent_birth=birth,settled=settled,targets=targets,
        founder_states=founders,founder_packets=np.stack([np.frombuffer(b,np.uint8) for b in incoming]),
        pre_states=pre,source_starts=starts.copy(),source_shift=shift,source_states=paths,written_fields=fields)
    meta=dict(index=index,life=life,config=asdict(cfg),tag=TAG,**seeds,teaching_rng=[x[1] for x in acquired],
        pre_readers=[x[1] for x in before],writers=[[x[1] for x in row] for row in writes],
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']))
    return raw,meta


def best(field,role):
    z=field-field.mean(); norm=np.sqrt(np.mean(z*z))
    return float(np.einsum('nij,ij->n',dev.template_bank()[role],z).max()/(256*norm)) if norm else 0.


def observations(states,role):
    return np.array([[dev.terminal_features(s[0],role)[0],best(s[2],role)] for s in states])


def assay(packet,ctx,index,life,noise,generation):
    """A disposable readout body; only results, never states, return to the lineage."""
    return old.read_selected(packet,ctx,rng(index,life,noise,f'g{generation}:terminal_birth'),
        rng(index,life,noise,f'g{generation}:terminal_read'),CONFIG,times=CONFIG.times)


def simulate(index,life,noise,founders,guide,order=CASES):
    validate(index,life,noise); dev.validate_guide(guide)
    if founders.shape!=(2,2048) or founders.dtype!=np.uint8: raise ValueError('only two F0 packets may enter')
    if len(order)!=len(CASES) or set(order)!=set(CASES): raise ValueError('complete unique condition panel required')
    ctx=old.context(index); paths={}; entries={}
    for role,kind in order:
        cfg=phase_config(kind)
        incoming=founders[role].tobytes(); rows=[]; history=[]
        for generation in GENERATIONS:
            random=lambda phase:rng(index,life,noise,f'g{generation}:{phase}')
            routed,first_scores,selection=old.route(incoming,'learned',guide)
            reads,rm=old.read_selected(routed,ctx,random('birth'),random('read'),cfg,not kind.endswith('read_off'))
            shift=address(index,life,noise,role,kind,generation)
            mode='translated'
            enabled=not kind.endswith(('_copy','_write_off'))
            writes,wm=old.write_streams(reads[-1],ctx,random('write'),mode,shift,cfg,enabled)
            output=incoming if kind.endswith('_copy') else bytes(2048) if kind.endswith('write_off') else old.encode(old.record(writes[-1,2]))
            final_packet,last_scores,last_selection=old.route(output,'learned',guide)
            terminal,tm=assay(final_packet,ctx,index,life,noise,generation)
            rows.append(dict(incoming=np.frombuffer(incoming,np.uint8),routed=np.frombuffer(routed,np.uint8),
                outgoing=np.frombuffer(output,np.uint8),terminal_packet=np.frombuffer(final_packet,np.uint8),
                read_states=reads,write_states=writes,terminal_states=terminal,shift=shift,
                scores=np.stack((first_scores,last_scores)),read_values=observations(reads,role),
                write_values=observations(writes,role),terminal_values=observations(terminal,role),
                record_values=np.array([best(old.decode(b),role) for b in (incoming,output)])))
            history.append(dict(generation=generation,role=role,kind=kind,phase_config=asdict(cfg),
                read_times=list(cfg.read_times),write_times=list(cfg.source_times),assay_steps=300,
                selector=selection,reader=rm,writer=wm,
                terminal_selector=last_selection,terminal_reader=tm,erased_before_writing=True,
                inherited_bytes=2048,assay_enters_lineage=False))
            incoming=output
        paths[role,kind]={k:np.stack([row[k] for row in rows]) for k in rows[0]}
        entries[role,kind]=dict(role=role,kind=kind,generations=history)
    raw={k:np.stack([paths[c][k] for c in CASES]) for k in paths[CASES[0]]}
    meta=dict(index=index,life=life,noise=noise,tag=TAG,config=asdict(CONFIG),cases=[list(c) for c in CASES],
        paths=[entries[c] for c in CASES],timings={k:list(v) for k,v in TIMINGS.items()},
        guide_sha256=old.GUIDE_SHA256,generations=3,
        record_bytes=2048,public_guide_bytes=4096,parent_state_access=False,
        family_supplied_to_address_rule=True,writer_receives_target_labels=False,
        terminal_is_fresh=True,assay_enters_lineage=False,guide_refitted=False)
    return raw,meta


def simulate_life(index,life,guide):
    source,source_meta=generate_founders(index,life)
    founders=np.stack([np.frombuffer(old.encode(source['written_fields'][r,0]),np.uint8) for r in (0,1)])
    trials=[simulate(index,life,n,founders,guide) for n in (0,1)]
    raw={k:np.stack([r[0][k] for r in trials]) for k in trials[0][0]}
    raw.update(founder_packets=founders,guide=guide.copy(),**{'f_'+k:v for k,v in source.items()})
    meta=dict(index=index,life=life,tag=TAG,config=asdict(CONFIG),founder=source_meta,trials=[r[1] for r in trials],
        host=dict(index=index,**{k:source_meta[k] for k in ('tissue','ladder','blueprint')}))
    return raw,meta
