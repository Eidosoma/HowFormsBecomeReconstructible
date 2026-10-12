"""Saved D146/D147 chronology: descriptive localization, no new dynamics."""
import numpy as np
from . import stopping_system as source

LABELS=tuple(f'G{g}_{t}' for g in (1,2,3) for t in (1000,1300))


def features(packet,role,guide):
    x=source.dev.record_features(packet,role,guide)
    _,_,sel=source.old.route(packet,'learned',guide)
    return dict(own_shape=float(x[0]),alternative_shape=float(x[0]-x[1]),shape_margin=float(x[1]),
        guide_margin=float(x[2]),canonical_margin=float(x[3]),guide_label=sel['inferred_family'],
        selected_forward_shift=sel['chosen_forward_shift'])


def profiles(states,times,role):
    rows=[]
    for state,t in zip(states,times):
        own=source.source.best(state[2],role);other=source.source.best(state[2],1-role)
        rows.append(dict(time=t,reference_own_shape=own,reference_alternative_shape=other,
            reference_shape_margin=own-other,body_preference=float(source.dev.terminal_features(state[0],role)[0])))
    assert len(rows)==len(times)
    return rows


def extract_life(index,life,raw,meta,upstream,upstream_meta):
    assert (meta['index'],meta['life'])==(upstream_meta['index'],upstream_meta['life'])==(index,life)
    rows=[]
    for noise in (0,1):
        for role in (0,1):
            wi=source.source.CASES.index((role,'write'));ci=source.CASES.index((role,1300,'intact'))
            expected=raw['founder_packets'][role].tobytes();stages=[];outcomes=[]
            for gi in range(3):
                packet=upstream['incoming'][noise,wi,gi].tobytes();assert packet==expected
                reads=profiles(upstream['read_states'][noise,wi,gi],[0,1,100,101,200,300],role)
                writes=profiles(upstream['write_states'][noise,wi,gi],[0,1,300,1000,1300],role)
                stops=[]
                for stop in (1000,1300):
                    pi=source.CASES.index((role,stop,'intact'));p=raw['packet'][noise,pi,gi].tobytes()
                    ref=upstream['write_states'][noise,wi,gi,3 if stop==1000 else 4,2]
                    assert p==source.old.encode(source.old.record(ref))
                    v=raw['terminal_states'][noise,pi,gi,-1,0]
                    item=dict(stage=f'G{gi+1}_{stop}',stop=stop,record=features(p,role,raw['guide']),
                        preference=float(source.dev.terminal_features(v,role)[0]))
                    stops.append(item);outcomes.append(item)
                expected=raw['packet'][noise,ci,gi].tobytes()
                assert expected==upstream['outgoing'][noise,wi,gi].tobytes()
                incoming=features(packet,role,raw['guide'])
                stages.append(dict(generation=gi+1,incoming=incoming,read=reads,write=writes,stops=stops,
                    incoming_to_read_end_shape=reads[-1]['reference_own_shape']-incoming['own_shape'],
                    read_to_write1000_shape=writes[-2]['reference_own_shape']-reads[-1]['reference_own_shape'],
                    write1000_to1300_shape=writes[-1]['reference_own_shape']-writes[-2]['reference_own_shape']))
            first=lambda rule:next((item['stage'] for item in outcomes if rule(item)),None)
            rows.append(dict(index=index,life=life,noise=noise,role=role,stages=stages,
                first_negative_assay_stage=first(lambda x:x['preference']<0),
                first_negative_shape_margin_stage=first(lambda x:x['record']['shape_margin']<0),
                first_nonown_guide_stage=first(lambda x:x['record']['guide_label']!=role),
                final_negative=outcomes[-1]['preference']<0,
                g2_positive_to_negative=outcomes[2]['preference']>0 and outcomes[3]['preference']<0))
    return rows


def summarize(rows):
    if len(rows)!=256:raise ValueError('all 256 family/life/replica histories required')
    result=[]
    state=lambda value:'negative' if value<0 else 'positive' if value>0 else 'zero'
    for role in (0,1):
        group=[r for r in rows if r['role']==role];assert len(group)==128
        first={key:{label:sum(r[key]==(None if label=='none' else label) for r in group)
            for label in (*LABELS,'none')} for key in
            ('first_negative_assay_stage','first_negative_shape_margin_stage','first_nonown_guide_stage')}
        transitions=[]
        for g in (1,2,3):
            pair=[(r['stages'][g-1]['stops'][0]['preference'],r['stages'][g-1]['stops'][1]['preference']) for r in group]
            transitions.append(dict(kind='early_to_late',generation=g,counts={a+'->'+b:sum(state(x)==a and state(y)==b for x,y in pair)
                for a in ('negative','zero','positive') for b in ('negative','zero','positive')}))
        for g in (1,2):
            pair=[(r['stages'][g-1]['stops'][1]['preference'],r['stages'][g]['stops'][1]['preference']) for r in group]
            transitions.append(dict(kind='late_to_next_late',generation=g,counts={a+'->'+b:sum(state(x)==a and state(y)==b for x,y in pair)
                for a in ('negative','zero','positive') for b in ('negative','zero','positive')}))
        identity=lambda r:[r['index'],r['life'],r['noise'],r['role']]
        result.append(dict(role=role,cases=128,first=first,transitions=transitions,
            final_negative_ids=[identity(r) for r in group if r['final_negative']],
            g2_reversal_ids=[identity(r) for r in group if r['g2_positive_to_negative']]))
    return dict(schema='l20_placement_history_v1',rows=rows,groups=result,all_cases_retained=True,
        history_rows=256,new_dynamics=0,posthoc_descriptive=True,early_branches_propagated=False,
        predictive_validation=False,exact_onset_between_checkpoints_identified=False)
