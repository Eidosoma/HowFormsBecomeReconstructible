"""D144: fresh, matched one-rewrite test of all ideal feedback geometry classes."""
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from . import diagnostics as dev

ROOT=dev.ROOT
SOURCE_RUN='l20_extension1_crossed_address_noise_v1_attempt1'
SOURCE_COMPLETE_SHA='a592f4a4131f2dd74251fc88f3938ad90c1932bccbae7f3cf7e053a1a68d2e03'
TAG='l20-extension1-compatible-feedback-v1'
BLOCKS=tuple(range(91000,91016)); DISPOSABLE=514244
CONFIG=old.CONFIG
LEVELS=(tuple(range(-4,5)),(-4,-2,0,2,4))
CASES=tuple((r,k) for r in (0,1) for k in ('zero',)+tuple(f'q{q}' for q in LEVELS[r])+('copy','read_off','write_off'))
PHASES=('birth','read','write','terminal_birth','terminal_read')
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


def members(role,quarter):
    if type(role) is not int or role not in (0,1) or type(quarter) is not int or quarter not in LEVELS[role]:
        raise ValueError('declared role/geometry class required')
    t=dev.targets()[role]
    return np.array([divmod(i,16) for i in range(1,256)
        if np.mean(t*np.roll(t,divmod(i,16),(0,1)))==quarter/4],np.int64)


def address(index,life,noise,role,kind):
    validate(index,life,noise)
    if type(role) is not int or (role,kind) not in CASES: raise ValueError('declared condition required')
    if not kind.startswith('q'): return np.zeros(2,np.int64)
    pool=members(role,int(kind[1:])); random=old.generator(TAG,index,life,f'address:noise{noise}:role{role}:{kind}')
    return pool[int(random.integers(len(pool)))].copy()


def schedule(index):
    validate(index,0)
    return np.stack([np.stack([np.stack([address(index,l,n,r,k) for r,k in CASES])
        for n in (0,1)]) for l in range(4)])


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


def simulate(index,life,noise,founders,guide,order=CASES):
    validate(index,life,noise); dev.validate_guide(guide)
    if founders.shape!=(2,2048) or founders.dtype!=np.uint8: raise ValueError('only two F0 packets may enter')
    if len(order)!=len(CASES) or set(order)!=set(CASES): raise ValueError('complete unique condition panel required')
    ctx=old.context(index); random=lambda phase:rng(index,life,noise,phase); paths={}; entries={}
    for role,kind in order:
        incoming=founders[role].tobytes(); routed,first_scores,selection=old.route(incoming,'learned',guide)
        reads,rm=old.read_selected(routed,ctx,random('birth'),random('read'),CONFIG,kind!='read_off')
        shift=address(index,life,noise,role,kind); mode='translated' if kind.startswith('q') else 'aligned'
        writes,wm=old.write_streams(reads[-1],ctx,random('write'),mode,shift,CONFIG,kind not in ('copy','write_off'))
        output=incoming if kind=='copy' else bytes(2048) if kind=='write_off' else old.encode(old.record(writes[-1,2]))
        final_packet,last_scores,last_selection=old.route(output,'learned',guide)
        terminal,tm=old.read_selected(final_packet,ctx,random('terminal_birth'),random('terminal_read'),CONFIG,times=CONFIG.times)
        paths[role,kind]=dict(incoming=np.frombuffer(incoming,np.uint8),routed=np.frombuffer(routed,np.uint8),
            outgoing=np.frombuffer(output,np.uint8),terminal_packet=np.frombuffer(final_packet,np.uint8),
            read_states=reads,write_states=writes,terminal_states=terminal,shift=shift,
            scores=np.stack((first_scores,last_scores)),read_values=observations(reads,role),
            write_values=observations(writes,role),terminal_values=observations(terminal,role),
            record_values=np.array([best(old.decode(b),role) for b in (incoming,output)]))
        entries[role,kind]=dict(role=role,kind=kind,selector=selection,reader=rm,writer=wm,
            terminal_selector=last_selection,terminal_reader=tm)
    raw={k:np.stack([paths[c][k] for c in CASES]) for k in paths[CASES[0]]}
    meta=dict(index=index,life=life,noise=noise,tag=TAG,config=asdict(CONFIG),cases=[list(c) for c in CASES],
        paths=[entries[c] for c in CASES],guide_sha256=old.GUIDE_SHA256,
        record_bytes=2048,public_guide_bytes=4096,parent_state_access=False,
        family_supplied_to_address_rule=True,writer_receives_target_labels=False,
        terminal_is_fresh=True,guide_refitted=False)
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
