"""D147 fixed late stopping contrast and complete secondary/control panel."""
import numpy as np
from .stopping_system import CASES,KINDS
from .phase_budget_analysis import stats

SEED=14720260919
METRICS=('terminal_preference','outgoing_shape','shape_margin','guide_margin','canonical_margin','terminal_reference_shape')


def arrays(blocks):
    assert len(blocks)==16
    terminal=np.stack([b['terminal_values'] for b in blocks])
    record=np.stack([b['record_values'] for b in blocks])
    assert terminal.shape==(16,4,2,16,3,4,2) and record.shape==(16,4,2,16,3,4)
    assert np.isfinite(terminal).all() and np.isfinite(record).all()
    return dict(terminal_preference=terminal[...,-1,0],outgoing_shape=record[...,0],
        shape_margin=record[...,1],guide_margin=record[...,2],canonical_margin=record[...,3],
        terminal_reference_shape=terminal[...,-1,1])


def summarize(blocks,records):
    assert len(records)==16
    data=arrays(blocks); draws=np.random.default_rng(SEED).integers(0,16,(10000,16))
    groups=[];contrasts=[];copies=[];controls=[];changes=[]
    for ci,(role,stop,kind) in enumerate(CASES):
        for gi in range(3):
            values={m:stats(y[...,ci,gi],draws) for m,y in data.items()}
            labels=[records[b]['lives'][l]['cells'][n][ci][gi]['terminal_selector']['inferred_family']
                for b in range(16) for l in range(4) for n in (0,1)]
            pref=data['terminal_preference'][...,ci,gi]
            profile=np.stack([b['terminal_values'][:,:,ci,gi] for b in blocks]).mean(axis=(0,1,2))
            groups.append(dict(role=role,stop=stop,condition=kind,generation=gi+1,metrics=values,
                terminal_profile=profile.tolist(),negative=int((pref<0).sum()),zero=int((pref==0).sum()),
                own_guide=sum(x==role for x in labels),cells=128))
        changes.append(dict(role=role,stop=stop,condition=kind,change='G3_minus_G1',
            metrics={m:stats(y[...,ci,2]-y[...,ci,0],draws) for m,y in data.items()}))
    for role in (0,1):
        for kind in KINDS:
            a=CASES.index((role,1000,kind));b=CASES.index((role,1300,kind))
            for gi in range(3):
                diff=data['terminal_preference'][...,b,gi]-data['terminal_preference'][...,a,gi]
                contrasts.append(dict(role=role,condition=kind,generation=gi+1,contrast='1300_minus_1000',
                    metrics={m:stats(y[...,b,gi]-y[...,a,gi],draws) for m,y in data.items()},
                    positive=int((diff>0).sum()),negative=int((diff<0).sum()),zero=int((diff==0).sum())))
        for stop in (1000,1300):
            for gi in range(3):
                intact=CASES.index((role,stop,'intact'));copy=CASES.index((role,stop,'copy'))
                copies.append(dict(role=role,stop=stop,generation=gi+1,contrast='intact_minus_copy',
                    metrics={m:stats(y[...,intact,gi]-y[...,copy,gi],draws) for m,y in data.items()}))
                for left,right in (('copy','write_off'),('intact','read_off'),('intact','write_off')):
                    y=data['terminal_preference'];a=CASES.index((role,stop,left));b=CASES.index((role,stop,right))
                    value=stats(y[...,a,gi]-y[...,b,gi],draws)
                    controls.append(dict(role=role,stop=stop,left=left,right=right,generation=gi+1,**value,
                        passes=value['pointwise_block_bootstrap_95'][0]>0))
    primary=next(c['metrics']['terminal_preference'] for c in contrasts
        if (c['role'],c['condition'],c['generation'])==(1,'intact',3))
    lo,hi=primary['pointwise_block_bootstrap_95']
    evidence='B_CONTINUATION_FAVORED' if lo>0 else 'B_STOPPING_FAVORED' if hi<0 else 'B_STOPPING_DIFFERENCE_UNRESOLVED'
    qualified=all(c['passes'] for c in controls)
    return dict(schema='l20_stopping_time_v1',primary_name='B_intact_G3_1300_minus_1000_terminal_preference',
        primary=primary,primary_interval_classification=evidence,apparatus_qualified=qualified,
        label=evidence if qualified else 'APPARATUS_NOT_QUALIFIED',groups=groups,stop_contrasts=contrasts,
        copy_contrasts=copies,controls=controls,serial_changes=changes,independent_blocks=16,record_host_pairs=128,
        noise_replicates=2,labelled_cells=6144,new_assays=512,reused_labels=5632,new_founders=0,
        new_upstream_dynamics=0,cases=[list(c) for c in CASES],terminal_times=[0,1,100,300],
        metric_columns=['native_preference','best_own_R_shape'],bootstrap_seed=SEED,bootstrap_draws=10000,
        secondary_intervals_multiplicity_adjusted=False,equivalence_test=False,fresh_cohort=False,
        same_extended_history=True,new_independent_noise=False,adaptive_stopping_policy_tested=False,
        all_cases_retained=True,carrier_bytes=2048,refits=0,assay_enters_lineage=False,automatic_successor=False)
