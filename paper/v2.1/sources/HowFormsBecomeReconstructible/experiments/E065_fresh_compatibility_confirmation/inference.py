"""Three fresh-source confirmation contrasts; native and secondary results retained."""
import numpy as np
from common import rng
from E065_fresh_compatibility_confirmation.plan import SLOTS,PRIMARY,CONFIDENCE,CONDITIONS,SOURCE_METRICS

SCORES=('both','minimum_margin','transfer','aligned_transfer')


def effects(x):
    ff,fo,of,oo,c,s=[x[...,i] for i in range(6)]
    return dict(earlier_sign_benefit=oo-fo,sign_magnitude_interaction=(oo-fo)-(of-ff),
        joint_magnitude_excess_loss=(c-ff)+(s-ff)-(fo-ff),
        sign_effect_final_magnitude=of-ff,matched_earlier_vs_native=oo-ff,
        earlier_both_effect=fo-ff,earlier_changed_effect=c-ff,earlier_unchanged_effect=s-ff,
        restore_changed_benefit=s-fo,restore_changed_advantage=s-c,restore_unchanged_benefit=c-fo)


def values(cases):
    out={}
    for metric in cases[0]:
        if metric=='margin':continue
        x=np.stack([c[metric] for c in cases]).mean(axis=(-2,-1))
        labels=('sham','pulse') if metric in SOURCE_METRICS else SLOTS
        for i,label in enumerate(labels):out[f'native/{metric}/{label}']=x[:,i]
        if metric in SCORES:
            for label,selected in (('sham',x[:,0:12:2]),('pulse',x[:,1:12:2]),
                ('pooled',x[:,:12].reshape(len(cases),6,2).mean(axis=-1))):
                for name,v in effects(selected).items():out[f'effect/{metric}/{label}/{name}']=v
    return out


def classification(interval):
    return 'POSITIVE_EFFECT' if interval[0]>0 else 'NEGATIVE_EFFECT' if interval[1]<0 else 'UNRESOLVED'


def analyze(cases,controls,mode):
    B=len(cases);draws=rng('E065','fresh_compatibility','bootstrap').integers(0,B,(10000,B));stats={}
    primary_keys=[f'effect/both/pooled/{name}' for name in PRIMARY]
    for key,x in values(cases).items():
        conf=CONFIDENCE if key in primary_keys else .95;tail=(1-conf)/2
        stats[key]=dict(mean=float(x.mean()),interval=np.quantile(x[draws].mean(axis=1),[tail,1-tail]).tolist(),
            confidence=conf,block_means=x.tolist())
    ok=all(c['pass'] for c in controls);enabled=ok and mode=='scientific'
    labels={k:classification(stats[f'effect/both/pooled/{k}']['interval']) if enabled else None for k in PRIMARY}
    passed=all(v=='POSITIVE_EFFECT' for v in labels.values()) if enabled else None
    return dict(status='TECHNICAL_ONLY' if mode!='scientific' else 'NUMERICAL_CONTROL_FAILURE' if not ok else
        'FRESH_COMPATIBILITY_CONFIRMED' if passed else 'COMPATIBILITY_NOT_CONFIRMED',
        primary_effects=labels,primary_confirmed=passed,controls_pass=ok,controls_by_block=controls,
        independent_blocks=B,lineages_per_slot=B*cases[0]['both'].shape[-2]*cases[0]['both'].shape[-1],
        original_arms_paired=True,primary_arm_weighting='equal_within_block',primary_family_size=3,
        primary_confidence=CONFIDENCE,cohort_reused=False,fresh_source_blocks=mode=='scientific',old_observations_pooled=False,
        nochange_reader_aliased=True,groups_not_equal_dose=True,statistics=stats)


def report(s):
    stats=s['statistics']
    def fmt(key,scale=1):
        v=stats[key];return f'{scale*v["mean"]:.4f} [{scale*v["interval"][0]:.4f}, {scale*v["interval"][1]:.4f}]'
    lines=['# E065 fresh-source compatibility confirmation','',s['status'],'',
        'Fresh acquisition, shared-noise h32 ancestry, early sham/pulse capture and three further rewrites.',
        'Six fixed record constructions and fresh matched readers. All source cases; no old cases pooled.','',
        '| Primary, equal original-history weighting within block | Points [98.3333%] | Classification |','| --- | ---: | --- |']
    for name in PRIMARY:lines.append(f'| {name} | {fmt("effect/both/pooled/"+name,100)} | {s["primary_effects"][name]} |')
    lines+=['','| Condition | Unstressed successes | Disturbed successes | Unstressed % [95%] | Disturbed % [95%] |',
        '| --- | ---: | ---: | ---: | ---: |']
    for c in CONDITIONS:
        keys=[f'native/both/{c}_{a}' for a in ('sham','pulse')];n=s['lineages_per_slot']
        counts=[round(stats[k]['mean']*n) for k in keys]
        lines.append(f'| {c} | {counts[0]}/{n} | {counts[1]}/{n} | {fmt(keys[0],100)} | {fmt(keys[1],100)} |')
    lines+=['','F/O denote final/initial signs then magnitudes on common edges; final support and later-only values stay fixed.',
        'Earlier changed/unchanged are the partial magnitude substitutions with final signs.',
        'Joint excess loss = (C−FF)+(S−FF)−(FO−FF), oriented positive for a more damaging combined substitution.','',
        '| Secondary pooled contrast | Points [95%] |','| --- | ---: |']
    for name in effects(np.zeros(6)):
        if name not in PRIMARY:lines.append(f'| {name} | {fmt("effect/both/pooled/"+name,100)} |')
    lines+=['',f'Controls passed: {s["controls_pass"]}; independent fresh source blocks: {s["independent_blocks"]}.',
        "E064's failed preferential changed-group claim remains failed; its contrasts here are secondary.",
        'Groups differ in size and normalization changes under magnitude substitution. No equal-dose, equivalence, mediation or autonomous-repair claim.',
        'Interpret after full independent source, reader, intervention and inference verification.','']
    return '\n'.join(lines)


def audit(cases,controls,summary,mode):
    from E015_functional_inheritance.audit import random
    all_values={};B=len(cases)
    for key in summary['statistics']:
        fields=key.split('/');metric=fields[1];vals=[]
        for case in cases:
            x=np.array([np.sum(a)/a.size for a in case[metric]])
            if fields[0]=='native':
                labels=('sham','pulse') if metric in ('common_edges','changed_edges','unchanged_edges','later_only_edges') else SLOTS
                vals.append(x[labels.index(fields[2])])
            else:
                arm,name=fields[2:]
                if arm=='pooled':ff,fo,of,oo,c,s=[(x[i]+x[i+1])/2 for i in (0,2,4,6,8,10)]
                else:ff,fo,of,oo,c,s=[x[i+(arm=='pulse')] for i in (0,2,4,6,8,10)]
                entries=dict(earlier_sign_benefit=oo-fo,sign_magnitude_interaction=(oo-fo)-(of-ff),
                    joint_magnitude_excess_loss=(c-ff)+(s-ff)-(fo-ff),
                    sign_effect_final_magnitude=of-ff,matched_earlier_vs_native=oo-ff,
                    earlier_both_effect=fo-ff,earlier_changed_effect=c-ff,earlier_unchanged_effect=s-ff,
                    restore_changed_benefit=s-fo,restore_changed_advantage=s-c,restore_unchanged_benefit=c-fo)
                vals.append(entries[name])
        all_values[key]=np.array(vals)
    draws=random('E065','fresh_compatibility','bootstrap').integers(0,B,size=(10000,B))
    for key,x in all_values.items():
        v=summary['statistics'][key]
        conf=1-.05/3 if key in tuple('effect/both/pooled/'+n for n in ('earlier_sign_benefit','sign_magnitude_interaction','joint_magnitude_excess_loss')) else .95
        np.testing.assert_array_equal(v['block_means'],x);assert v['mean']==x.mean() and v['confidence']==conf
        np.testing.assert_array_equal(v['interval'],np.quantile(x[draws].mean(axis=1),[(1-conf)/2,1-(1-conf)/2]))
    ok=all(c['pass'] for c in controls);assert summary['controls_pass']==ok
    labels={}
    for name in ('earlier_sign_benefit','sign_magnitude_interaction','joint_magnitude_excess_loss'):
        lo,hi=summary['statistics']['effect/both/pooled/'+name]['interval']
        labels[name]=('POSITIVE_EFFECT' if lo>0 else 'NEGATIVE_EFFECT' if hi<0 else 'UNRESOLVED') if mode=='scientific' and ok else None
    assert summary['primary_effects']==labels
    passed=all(v=='POSITIVE_EFFECT' for v in labels.values()) if mode=='scientific' and ok else None
    assert summary['primary_confirmed']==passed
    return len(all_values)
