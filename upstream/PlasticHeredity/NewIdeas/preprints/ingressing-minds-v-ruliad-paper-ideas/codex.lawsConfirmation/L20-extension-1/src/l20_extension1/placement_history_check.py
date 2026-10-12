"""Independent raw-state chronology and full-cohort counts; no new dynamics."""
import numpy as np
from .placement_audit import prior,physics,metrics,source_index


def packet_features(packet,role,guide):
    field=prior.unpack(packet);values=metrics.corr(field,prior.prior.targets()).max(axis=(1,2))
    routed,scores,selection=prior.prior.select(packet,guide)
    r=prior.unpack(routed);z=r-r.mean();scale=np.sqrt(np.sum(z*z)/256)
    canon=[float(np.sum(z*t)/(256*scale)) if scale else 0. for t in prior.prior.targets()]
    maxima=scores.max(axis=(1,2))
    return dict(own_shape=float(values[role]),alternative_shape=float(values[1-role]),
        shape_margin=float(values[role]-values[1-role]),guide_margin=float(maxima[role]-maxima[1-role]),
        canonical_margin=canon[role]-canon[1-role],guide_label=selection['inferred_family'],
        selected_forward_shift=selection['chosen_forward_shift'])


def trace(states,times,role):
    assert len(states)==len(times)
    result=[]
    for i,t in enumerate(times):
        x=states[i];best=metrics.corr(x[2],prior.prior.targets()).max(axis=(1,2))
        result.append(dict(time=t,reference_own_shape=float(best[role]),reference_alternative_shape=float(best[1-role]),
            reference_shape_margin=float(best[role]-best[1-role]),body_preference=float(metrics.terminal_features(x[0],role)[0])))
    return result


def reconstruct(index,life,source,source_meta,old,old_meta):
    assert (source_meta['index'],source_meta['life'])==(old_meta['index'],old_meta['life'])==(index,life)
    rows=[]
    for n in (0,1):
        for role in (0,1):
            wi=role*12+8;stages=[];seen=[];incoming=source['founder_packets'][role].tobytes()
            for g in (1,2,3):
                gi=g-1
                assert old['incoming'][n,wi,gi].tobytes()==incoming
                read=trace(old['read_states'][n,wi,gi],(0,1,100,101,200,300),role)
                write=trace(old['write_states'][n,wi,gi],(0,1,300,1000,1300),role)
                stops=[]
                for t,checkpoint in ((1000,3),(1300,4)):
                    ci=source_index(role,t,'intact');p=source['packet'][n,ci,gi].tobytes()
                    ref=old['write_states'][n,wi,gi,checkpoint,2]
                    assert p==prior.packet(prior.project(np.tanh(ref)))
                    value=metrics.terminal_features(source['terminal_states'][n,ci,gi,-1,0],role)[0]
                    item=dict(stage=f'G{g}_{t}',stop=t,record=packet_features(p,role,source['guide']),preference=float(value))
                    stops.append(item);seen.append(item)
                feature=packet_features(incoming,role,source['guide'])
                stages.append(dict(generation=g,incoming=feature,read=read,write=write,stops=stops,
                    incoming_to_read_end_shape=read[-1]['reference_own_shape']-feature['own_shape'],
                    read_to_write1000_shape=write[3]['reference_own_shape']-read[-1]['reference_own_shape'],
                    write1000_to1300_shape=write[4]['reference_own_shape']-write[3]['reference_own_shape']))
                incoming=source['packet'][n,source_index(role,1300,'intact'),gi].tobytes()
                assert old['outgoing'][n,wi,gi].tobytes()==incoming
            first_pref=first_shape=first_guide=None
            for item in seen:
                if first_pref is None and item['preference']<0:first_pref=item['stage']
                if first_shape is None and item['record']['shape_margin']<0:first_shape=item['stage']
                if first_guide is None and item['record']['guide_label']!=role:first_guide=item['stage']
            rows.append(dict(index=index,life=life,noise=n,role=role,stages=stages,
                first_negative_assay_stage=first_pref,first_negative_shape_margin_stage=first_shape,
                first_nonown_guide_stage=first_guide,final_negative=seen[5]['preference']<0,
                g2_positive_to_negative=seen[2]['preference']>0 and seen[3]['preference']<0))
    return rows


def check_life(rows,index,life,source,source_meta,old,old_meta):
    expected=reconstruct(index,life,source,source_meta,old,old_meta)
    physics.nested(rows,expected)
    return dict(passes=True,history_rows=4,saved_reference_checkpoints=132,natural_assays=24,new_dynamics=0)


def check_summary(summary,rows):
    assert len(rows)==256
    labels=('G1_1000','G1_1300','G2_1000','G2_1300','G3_1000','G3_1300','none')
    groups=[]
    state=lambda x:('negative','zero','positive')[int(np.sign(x))+1]
    for role in (0,1):
        group=[r for r in rows if r['role']==role];assert len(group)==128
        counts={key:dict.fromkeys(labels,0) for key in
            ('first_negative_assay_stage','first_negative_shape_margin_stage','first_nonown_guide_stage')}
        final=[];reverse=[]
        for row in group:
            for key in counts:counts[key][row[key] if row[key] is not None else 'none']+=1
            identity=[row['index'],row['life'],row['noise'],row['role']]
            if row['final_negative']:final.append(identity)
            if row['g2_positive_to_negative']:reverse.append(identity)
        transitions=[]
        for kind,stages in (('early_to_late',(1,2,3)),('late_to_next_late',(1,2))):
            for g in stages:
                tally={a+'->'+b:0 for a in ('negative','zero','positive') for b in ('negative','zero','positive')}
                for row in group:
                    a=row['stages'][g-1]['stops'][0 if kind=='early_to_late' else 1]['preference']
                    b=row['stages'][g-1 if kind=='early_to_late' else g]['stops'][1]['preference']
                    tally[state(a)+'->'+state(b)]+=1
                transitions.append(dict(kind=kind,generation=g,counts=tally))
        groups.append(dict(role=role,cases=128,first=counts,transitions=transitions,final_negative_ids=final,g2_reversal_ids=reverse))
    expected=dict(schema='l20_placement_history_v1',rows=rows,groups=groups,all_cases_retained=True,
        history_rows=256,new_dynamics=0,posthoc_descriptive=True,early_branches_propagated=False,
        predictive_validation=False,exact_onset_between_checkpoints_identified=False)
    physics.nested(summary,expected)
    return dict(passes=True,history_rows=256,groups=2,all_cases_retained=True,new_dynamics=0)
