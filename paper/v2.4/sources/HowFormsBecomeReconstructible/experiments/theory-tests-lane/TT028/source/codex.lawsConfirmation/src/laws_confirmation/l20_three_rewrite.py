"""D117: three fresh read/erase/rewrite lives, then a fresh terminal reader."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.util

import numpy as np

from . import l20_acquisition as parent
from .io import canonical_digest

WS, ORIGIN, PACKAGES = parent.WS, parent.ORIGIN, parent.PACKAGES
RUN_ID = 'l20_three_boundary_rewrite_v1_attempt1'
CONTROL_ID = 'l20_three_boundary_rewrite_v1_source_bridge_attempt1'
TAG = 'l20-three-rewrite-v1'
TISSUES, DISPOSABLE = tuple(range(60000, 60008)), 514217
KINDS = ('rewrite', 'live', 'copy', 'write_off', 'read_off', 'wrong', 'lesion', 'rescue')
CASES = tuple((r,k) for r in (0,1) for k in KINDS)
PROBES = tuple((r,k) for r in (0,1) for k in KINDS+('ideal','zero'))
METRICS = parent.METRICS
SCIENCE = ('src/laws_confirmation/l20_three_rewrite.py',
    'src/laws_confirmation/l20_three_rewrite_run.py',
    'scripts/audit_l20_three_rewrite_outputs.py', 'tests/test_l20_three_rewrite.py',
    'scripts/run_l20_three_rewrite.sh', 'protocols/L20_THREE_BOUNDARY_REWRITE_V1.md')
api, context, encode, decode, source_bridge = parent.api, parent.context, parent.encode, parent.decode, parent.source_bridge


@dataclass(frozen=True)
class Config:
    lives: int = 4
    settle: int = 120
    teaching: int = 1000
    generations: int = 3
    read_steps: int = 300
    write_steps: int = 1000
    rescue_after: int = 100
    norm: float = .3
    lam: float = .001
    amp_threshold: float = .2

    def __post_init__(self):
        counts=(self.lives,self.settle,self.teaching,self.read_steps,self.write_steps,self.rescue_after)
        if any(type(x) is not int or x<=0 for x in counts): raise ValueError('positive integer counts required')
        if type(self.generations) is not int or self.generations!=3 or not 1<=self.rescue_after<self.read_steps:
            raise ValueError('three generations and internal rescue time required')
        if (self.norm,self.lam,self.amp_threshold)!=(.3,.001,.2): raise ValueError('fixed norm/rate/observer required')

    @property
    def read_times(self): return tuple(sorted({0,1,self.rescue_after,self.rescue_after+1,self.read_steps}))
    @property
    def write_times(self): return tuple(sorted({1,min(300,self.write_steps),self.write_steps}))
    @property
    def times(self): return self.read_times+tuple(self.read_steps+x for x in self.write_times)
    @property
    def probe_times(self): return tuple(sorted({0,1,min(100,self.read_steps),self.read_steps}))
    @property
    def parent_times(self): return tuple(sorted({0,1,min(20,self.teaching),min(80,self.teaching),min(300,self.teaching),self.teaching}))
    def parent_config(self):
        return parent.Config(lives=self.lives,settle=self.settle,teaching=self.teaching,
            parent_times=self.parent_times,steps=self.read_steps,times=self.probe_times)


CONFIG=Config()


def rng(index,life,phase):
    key=hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(key[:16],'little')))


def checker():
    spec=importlib.util.spec_from_file_location('d117_checker',WS/SCIENCE[2])
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def write_phase(start,theta0,index,life,generation,writing,cfg=CONFIG):
    """No old packet, founder target or other generation state is an input."""
    ctx=context(index); state=tuple(x[None].copy() for x in start)
    field=theta0[None].copy(); random=rng(index,life,f'g{generation}:write'); saved=[]
    for t in range(1,cfg.write_steps+1):
        result=ctx['api']['original'].cascade_step(*state,field,ctx['tissue'],ctx['ladder'],
            ctx['bp'],random,cfg.lam if writing else 0.,cfg.norm)
        state,field=result[:3],result[3]
        if t in cfg.write_times: saved.append(np.stack((*state,field))[:,0])
    return np.stack(saved),canonical_digest(random.bit_generator.state)


def descendant(packet,index,life,generation,kind,cfg=CONFIG,*,rescue_packet=None):
    """Only theta bytes enter; the exceptional rescue backup is explicitly tagged."""
    if type(generation) is not int or not 1<=generation<=3 or kind not in KINDS:
        raise ValueError('declared generation/condition required')
    needs_rescue=kind=='rescue' and generation==1
    if needs_rescue!=(rescue_packet is not None): raise ValueError('backup only for declared G1 rescue')
    field=decode(packet); backup=decode(rescue_packet) if needs_rescue else None
    ctx=context(index); random=rng(index,life,f'g{generation}:birth')
    v=.2*random.standard_normal((1,16,16)); birth_rng=canonical_digest(random.bit_generator.state)
    state=(v,v.copy(),v.copy()); saved=[np.concatenate((np.stack(state)[:,0],field[None]))]
    random=rng(index,life,f'g{generation}:read')
    for t in range(1,cfg.read_steps+1):
        if needs_rescue and t==cfg.rescue_after+1: field=backup.copy()
        applied=field if kind!='read_off' else np.zeros_like(field)
        state=ctx['api']['blueprint_step'](*state,applied,ctx['tissue'],ctx['ladder'],ctx['bp'],'T',random,c_m=0.)
        if t in cfg.read_times: saved.append(np.concatenate((np.stack(state)[:,0],field[None])))
    read_rng=canonical_digest(random.bit_generator.state)
    write_field=field.copy() if kind in ('live','copy') else np.zeros_like(field)
    write_birth=np.concatenate((np.stack(state)[:,0],write_field[None]))
    written,write_rng=write_phase(write_birth[:3],write_birth[3],index,life,generation,
                                  kind not in ('copy','write_off'),cfg)
    trace=np.concatenate((np.stack(saved),written),axis=0)
    output=encode(written[-1,3])
    meta=dict(generation=generation,kind=kind,birth_rng=birth_rng,read_rng=read_rng,write_rng=write_rng,
        input_sha256=hashlib.sha256(packet).hexdigest(),output_sha256=hashlib.sha256(output).hexdigest(),
        rescue_sha256=hashlib.sha256(rescue_packet).hexdigest() if needs_rescue else None,
        available_packet_bytes=4096 if needs_rescue else 2048,erased_before_writing=kind not in ('live','copy'),
        inherited_reader_enabled=kind!='read_off',writing_enabled=kind not in ('copy','write_off'))
    return trace,write_birth,output,meta


def probe(packet,index,life,cfg=CONFIG):
    field=decode(packet); ctx=context(index); random=rng(index,life,'terminal:birth')
    v=.2*random.standard_normal((1,16,16)); birth_rng=canonical_digest(random.bit_generator.state)
    state=(v,v.copy(),v.copy()); saved=[np.stack(state)[:,0]]; random=rng(index,life,'terminal:read')
    for t in range(1,cfg.read_steps+1):
        state=ctx['api']['blueprint_step'](*state,field,ctx['tissue'],ctx['ladder'],ctx['bp'],'T',random,c_m=0.)
        if t in cfg.probe_times: saved.append(np.stack(state)[:,0])
    return np.stack(saved),dict(birth_rng=birth_rng,read_rng=canonical_digest(random.bit_generator.state),
        input_sha256=hashlib.sha256(packet).hexdigest(),packet_bytes=2048,writing=False,gain=0.)


def observations(states,targets,cases,cfg=CONFIG):
    """case, any checkpoint axes, field, row, column -> case,...,metric."""
    if len(states)!=len(cases) or states.shape[-3]!=3 or not np.isfinite(states).all():
        raise ValueError('complete finite V/EMA/R states required')
    mean=lambda x:x.mean(axis=(-2,-1)); rows=[]
    for (role,_),trace in zip(cases,states):
        v,ref=trace[...,0,:,:],trace[...,2,:,:]; amp=abs(v)>cfg.amp_threshold
        own,other=(v>0)==(targets[role]>0),(v>0)==(targets[1-role]>0)
        rough=(abs(v-np.roll(v,1,-1))+abs(v-np.roll(v,1,-2)))/2
        rows.append(np.stack((mean(own&amp),mean(other&amp),mean(own),mean(other),mean(amp),mean(v),
            np.sqrt(mean(v*v)),mean(abs(v)==2.),mean(rough),mean(ref),np.sqrt(mean(ref*ref)),mean(abs(v-ref))),axis=-1))
    return np.stack(rows)


def simulate_life(index,life,cfg=CONFIG,order=CASES):
    if type(life) is not int or not 0<=life<cfg.lives or len(order)!=16 or set(order)!=set(CASES):
        raise ValueError('valid life and complete unique condition order required')
    ctx=context(index); targets=parent.capacity.target_fields(ctx); pcfg=cfg.parent_config()
    native,theta0,birth,settled,seeds=parent.common_parent(index,life,pcfg)
    acquired=[parent.acquire(settled,theta0,targets[r],index,life,True,pcfg) for r in (0,1)]
    founder=np.stack([x[0] for x in acquired]); founder_packets=[encode(founder[r,-1,3]) for r in (0,1)]
    perms=np.stack([rng(index,life,f'lesion:{r}').permutation(256) for r in (0,1)])
    starts={}
    for r,k in CASES:
        if k=='wrong': starts[(r,k)]=founder_packets[1-r]
        elif k in ('lesion','rescue'): starts[(r,k)]=encode(founder[r,-1,3].ravel()[perms[r]].reshape(16,16))
        else: starts[(r,k)]=founder_packets[r]
    paths={}
    for r,k in order:
        packet=starts[(r,k)]; trace=[]; write_birth=[]; incoming=[]; outgoing=[]; records=[]
        for g in range(1,4):
            incoming.append(np.frombuffer(packet,np.uint8))
            states,wb,output,meta=descendant(packet,index,life,g,k,cfg,
                rescue_packet=founder_packets[r] if k=='rescue' and g==1 else None)
            trace.append(states); write_birth.append(wb); outgoing.append(np.frombuffer(output,np.uint8))
            records.append(meta); packet=output
        paths[(r,k)]=(np.stack(trace),np.stack(write_birth),np.stack(incoming),np.stack(outgoing),records)
    probes={}; packets=[]
    for r,k in PROBES:
        if k=='ideal': packet=encode(ctx['api']['original'].project_theta(np.tanh(1.5*targets[r]),cfg.norm))
        elif k=='zero': packet=encode(np.zeros((16,16)))
        else: packet=paths[(r,k)][3][-1].tobytes()
        packets.append(np.frombuffer(packet,np.uint8)); probes[(r,k)]=probe(packet,index,life,cfg)
    generations=np.stack([paths[c][0] for c in CASES]); probe_states=np.stack([probes[c][0] for c in PROBES])
    raw=dict(native_theta=native,theta0=theta0,parent_birth=birth,settled=settled,targets=targets,
        founder_states=founder,permutations=perms,founder_packets=np.stack([np.frombuffer(x,np.uint8) for x in founder_packets]),
        generation_states=generations,write_birth=np.stack([paths[c][1] for c in CASES]),
        incoming=np.stack([paths[c][2] for c in CASES]),outgoing=np.stack([paths[c][3] for c in CASES]),
        probe_packets=np.stack(packets),probe_states=probe_states,
        values=observations(generations[:,:,:,:3],targets,CASES,cfg),probe_values=observations(probe_states,targets,PROBES,cfg))
    meta=dict(index=index,life=life,config=asdict(cfg),cases=[list(c) for c in CASES],probes=[list(c) for c in PROBES],
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),**seeds,
        teaching_rng=[x[1] for x in acquired],generations=[paths[c][4] for c in CASES],terminal=[probes[c][1] for c in PROBES],
        times=list(cfg.times),probe_times=list(cfg.probe_times),parent_tag=parent.TAG,descendant_tag=TAG,
        ordinary_packet_bytes=2048,rescue_g1_extra_bytes=2048,descendant_target_labels=False,
        renewal_generations=3,terminal_extra_transfer=True)
    return raw,meta


def execute_block(index,cfg=CONFIG):
    rows=[]; records=[]; audit=checker()
    for life in range(cfg.lives):
        raw,meta=simulate_life(index,life,cfg); meta['replay']=audit.check_life(raw,meta,cfg,replay=True)
        rows.append(raw); records.append(meta)
    return {k:np.stack([r[k] for r in rows]) for k in rows[0]},dict(index=index,config=asdict(cfg),lives=records)


def summarize(blocks,cfg=CONFIG):
    if len(blocks)!=8: raise ValueError('eight equal blocks required')
    v=np.stack([b['values'] for b in blocks]); q=np.stack([b['probe_values'] for b in blocks])
    if v.shape!=(8,cfg.lives,16,3,len(cfg.times),12) or q.shape!=(8,cfg.lives,20,len(cfg.probe_times),12):
        raise ValueError('complete observation panel required')
    if not np.isfinite(v).all() or not np.isfinite(q).all(): raise ValueError('finite measurements required')
    draws=rng(0,0,'bootstrap').integers(0,8,(10000,8)); rows=[]
    contrasts=(('rewrite','read_off'),('rewrite','write_off'),('live','copy'),('rewrite','copy'),
               ('rewrite','wrong'),('rewrite','lesion'),('rescue','lesion'))
    for observer,col in (('qualified',0),('sign',2)):
        for stage in (1,2,3,4):
            obs=v[:,:,:,stage-1,cfg.times.index(cfg.read_steps)] if stage<4 else q[:,:,:,-1]
            cases=CASES if stage<4 else PROBES; pref=obs[...,col]-obs[...,col+1]
            for left,right in contrasts+( (('ideal','zero'),('copy','zero')) if stage==4 else () ):
                effects=[pref[:,:,cases.index((r,left))]-pref[:,:,cases.index((r,right))] for r in (0,1)]
                for role,effect in ((0,effects[0]),(1,effects[1]),('both',sum(effects)/2)):
                    rows.append(dict(name=left+'_minus_'+right,stage=stage,role=role,observer=observer,
                                    **parent.capacity.native.contrast_stats(effect,draws)))
    pick=lambda name,stage=4,role='both':next(r for r in rows if r['name']==name and r['stage']==stage and r['role']==role and r['observer']=='qualified')
    primary=pick('rewrite_minus_read_off'); directions=[pick('rewrite_minus_read_off',role=r) for r in (0,1)]
    writer=pick('rewrite_minus_write_off'); continuity=[pick('rewrite_minus_read_off',stage=s) for s in (2,3,4)]
    gates=[pick(name,role=r) for name in ('ideal_minus_zero','copy_minus_zero') for r in (0,1)]
    disagreement=[[int(np.count_nonzero(b['targets'][l,0]!=b['targets'][l,1])) for l in range(cfg.lives)] for b in blocks]
    readable=bool(np.all(np.asarray(disagreement)>0) and all(x['pointwise_block_bootstrap_95'][0]>0 for x in gates))
    positive=bool(all(x['pointwise_block_bootstrap_95'][0]>0 for x in continuity+[writer]) and
        all(pick('rewrite_minus_read_off',stage=s,role=r)['mean']>0 for s in (2,3,4) for r in (0,1)) and
        all(pick('rewrite_minus_write_off',role=r)['mean']>0 for r in (0,1)))
    return dict(schema='l20_three_boundary_rewrite_v1',tissues=list(TISSUES),
        label='READOUT_NOT_QUALIFIED' if not readable else 'QUALIFIED_READ_ERASE_REWRITE' if positive else 'REWRITE_UNRESOLVED',
        primary=primary,directional_primary=directions,writer_control=writer,continuity=continuity,readout_gates=gates,
        readout_qualified=readable,target_disagreement_cells=disagreement,contrasts=rows,
        cases=[list(c) for c in CASES],probes=[list(c) for c in PROBES],times=list(cfg.times),probe_times=list(cfg.probe_times),
        metrics=list(METRICS),generation_cell_means=v.mean(axis=(0,1)).tolist(),probe_cell_means=q.mean(axis=(0,1)).tolist(),
        blocks=8,lives_per_block=cfg.lives,renewal_generations=3,transfer_interfaces_including_probe=4,
        ordinary_packet_bytes=2048,rescue_g1_available_bytes=4096,absolute_fidelity_gate=None,
        engineered_erasure=True,native_renewal_necessity=False,independent_confirmation=False,
        secondary_intervals_multiplicity_adjusted=False)


def contract():
    return dict(schema='l20_three_boundary_rewrite_v1',decision='D117',law='L20/L17',run_id=RUN_ID,
        control_id=CONTROL_ID,tag=TAG,parent_tag=parent.TAG,config=asdict(CONFIG),tissues=list(TISSUES),disposable=DISPOSABLE,
        cases=[list(c) for c in CASES],probes=[list(c) for c in PROBES],metrics=list(METRICS),
        times=list(CONFIG.times),probe_times=list(CONFIG.probe_times),parent_paths=64,generation_paths=1536,terminal_paths=640,
        full_life_replays=32,exact_terminal_aliases=192,packet_bytes=2048,rescue_g1_available_bytes=4096,
        generations=3,transfer_interfaces_including_probe=4,primary='terminal qualified rewrite-minus-read_off preference',
        positive='reading gates, primary and G2/G3 continuity, writer-off contrast lower95>0 and both direction means>0',
        reading='both ideal-minus-zero and copy-minus-zero role terminal intervals lower95>0',
        uncertainty='10000 whole-block percentile pointwise95; eight native-field/random-stream blocks',
        taught_descendants=False,erased_primary_before_writing=True,native_live_control=True,exact_copy_control=True,
        first_write_projection='lambda scale cancels when denominator floor inactive; not proof of slow filtering',
        state_atol=1e-10,metric_atol=1e-12,automatic_retry=False,automatic_follow_on=False)
