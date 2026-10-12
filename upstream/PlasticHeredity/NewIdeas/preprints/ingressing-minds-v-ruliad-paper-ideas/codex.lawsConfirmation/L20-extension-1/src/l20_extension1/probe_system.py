"""D151 fixed D149 edits on diagnostic copies, never on actual lineages."""
from dataclasses import asdict
import hashlib
import numpy as np
from . import recovery_features as sources,diagnostics as original,component_system as edit

old=original.old;ROOT=sources.ROOT;WS=sources.WS;CONFIG=original.CONFIG
SPECS=sources.SPECS;CASES=sources.CASES
DISPOSABLE=('disposable_dev',514240);OTHER_DISPOSABLE=('disposable_test',514240)
EDITS=('attenuate','sham_plus','sham_minus')
ORDER=tuple((ci,ei) for ci in range(4) for ei in range(3))
TAG='l20-extension1-targeted-prediction-v1'


def validate(spec,life):
    if spec not in SPECS+(DISPOSABLE,OTHER_DISPOSABLE) or type(spec[1]) is not int or type(life) is not int or life not in range(4):
        raise ValueError('declared existing source and life required')
    host=spec[1]-2000 if spec[0]=='d135' else spec[1]
    tag=('l20-extension1-heldout-v1:diagnostics:'+('heldout' if spec[0]=='former_test' else 'disposable')
         if spec[0] in ('former_test','disposable_test') else
         'l20-extension1-diagnostics-v1:'+('disposable' if spec==DISPOSABLE else spec[0]))
    return host,tag


def load_source(spec):
    validate(spec,0)
    return sources.diagnostic(spec,spec in (DISPOSABLE,OTHER_DISPOSABLE))


def random(spec,life,phase):
    _,tag=validate(spec,life)
    if phase not in ('birth','read','shift','write','final_birth','final_read'):raise ValueError('declared phase')
    return old.generator(tag,spec[1],life,'trial1:'+phase)


def sha(packet):return hashlib.sha256(packet).hexdigest()


def candidates(founders,guide):
    if founders.shape!=(2,2048) or founders.dtype!=np.uint8:raise ValueError('two founder packets only')
    original.validate_guide(guide);values=[];entries=[]
    for ci,(role,mode) in enumerate(CASES):
        founder=founders[role].tobytes();routed,scores,selection=old.route(founder,'learned',guide)
        edited,detail=edit.edit_packets(routed,role);row=[];plans=[]
        for name in EDITS:
            candidate=edited[name]
            plans.append(dict(role=role,writer=mode,edit=name,founder_sha256=sha(founder),
                selected_sha256=sha(routed),edited_sha256=sha(candidate),identity=candidate==routed,**detail))
            row.append((routed,candidate,scores,selection))
        entries.append(plans);values.append(row)
    return values,entries


def block_plan(spec):
    source,meta=load_source(spec);lives=[]
    from . import probe_audit as audit
    for life in range(4):
        values,plan=candidates(source['founder_packets'][life],source['guide'][life])
        for ci in range(4):
            for ei in range(3):
                assert values[ci][ei][0]==source['routed'][life,ci,1].tobytes()
                audit.check_edit(values[ci][ei][1],plan[ci][ei],source['founder_packets'][life],source['guide'][life],ci,ei)
        lives.append(plan)
    identities=sum(cell['identity'] for life in lives for case in life for cell in case)
    return dict(spec=list(spec),lives=lives,new_cycles=48,identity_cycles=identities,carrier_bytes=2048,new_founders=0)


def cycle(packet,spec,life,mode,guide):
    host,_=validate(spec,life)
    if mode not in ('translated','aligned'):raise ValueError('original writer mode required')
    original.validate_guide(guide);ctx=old.context(host)
    # The input is ALREADY selected and edited. No second entrance route.
    reads,reader=old.read_selected(packet,ctx,random(spec,life,'birth'),random(spec,life,'read'),CONFIG)
    shift=np.asarray(divmod(int(random(spec,life,'shift').integers(1,256)),16),np.int64)
    writes,writer=old.write_streams(reads[-1],ctx,random(spec,life,'write'),mode,shift,CONFIG)
    outgoing=old.encode(old.record(writes[-1,2]))
    terminal_packet,scores,selection=old.route(outgoing,'learned',guide)
    terminal,final=old.read_selected(terminal_packet,ctx,random(spec,life,'final_birth'),random(spec,life,'final_read'),CONFIG,times=CONFIG.times)
    raw=dict(input=np.frombuffer(packet,np.uint8),outgoing=np.frombuffer(outgoing,np.uint8),
        terminal_packet=np.frombuffer(terminal_packet,np.uint8),read_states=reads,write_states=writes,
        terminal_states=terminal,last_scores=scores,shift=shift)
    meta=dict(reader=reader,writer=writer,terminal_selector=selection,terminal_reader=final,trial=1)
    return raw,meta


def simulate_life(spec,life,founders,guide,plan,order=ORDER):
    host,namespace=validate(spec,life)
    if len(order)!=12 or set(order)!=set(ORDER):raise ValueError('all four cases and three edits required')
    values,expected=candidates(founders,guide)
    if plan!=expected:raise ValueError('frozen edited-packet plan mismatch')
    paths={};history={}
    for ci,ei in order:
        selected,packet,scores,selection=values[ci][ei];role,mode=CASES[ci]
        row,entry=cycle(packet,spec,life,mode,guide)
        row['record_values']=edit.record_values(packet,selected,role)
        row['diagnostic_features']=np.r_[original.record_features(row['outgoing'].tobytes(),role,guide),
            original.terminal_features(row['terminal_states'][-1,0],role)]
        paths[ci,ei]=row;history[ci,ei]=dict(plan=plan[ci][ei],initial_selector=selection,**entry)
    result={k:np.stack([np.stack([paths[ci,ei][k] for ei in range(3)]) for ci in range(4)]) for k in paths[0,0]}
    result.update(founder_packets=founders.copy(),guide=guide.copy(),
        selected_packets=np.stack([np.frombuffer(values[ci][0][0],np.uint8) for ci in range(4)]))
    ctx=old.context(host)
    meta=dict(spec=list(spec),life=life,host=dict(index=host,tissue=asdict(ctx['tissue']),
        ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp'])),tag=TAG,physics_namespace=namespace,
        config=asdict(CONFIG),cases=[list(c) for c in CASES],edits=list(EDITS),
        cells=[[history[ci,ei] for ei in range(3)] for ci in range(4)],
        guide_sha256=old.GUIDE_SHA256,carrier_bytes=2048,new_cycles=12,new_readers=24,new_writers=12,
        new_founders=0,new_main_lineages=0,diagnostic_to_lineage=False,source_state_given_to_reader=False,
        rerouted_after_edit=False,independent_new_noise=False,analyst_supplied_edit=True,prospective_evidence=False)
    return result,meta
