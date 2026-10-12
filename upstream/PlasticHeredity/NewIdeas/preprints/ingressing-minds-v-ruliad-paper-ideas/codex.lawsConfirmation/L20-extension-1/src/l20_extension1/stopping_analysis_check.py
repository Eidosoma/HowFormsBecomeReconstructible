"""Independent sixteen-block D147 inference; no production summaries or metrics."""
import numpy as np
from .stopping_audit import CASES,KINDS,physics
from .phase_budget_analysis_check import stats


def check(summary,blocks,records):
    assert len(blocks)==len(records)==16
    names=('terminal_preference','outgoing_shape','shape_margin','guide_margin','canonical_margin','terminal_reference_shape')
    data={k:np.empty((16,4,2,16,3)) for k in names}
    for bi,b in enumerate(blocks):
        assert b['terminal_values'].shape==(4,2,16,3,4,2) and b['record_values'].shape==(4,2,16,3,4)
        data['terminal_preference'][bi]=b['terminal_values'][...,-1,0]
        data['terminal_reference_shape'][bi]=b['terminal_values'][...,-1,1]
        for column,key in enumerate(names[1:5]): data[key][bi]=b['record_values'][...,column]
    draws=np.random.Generator(np.random.PCG64(14720260919)).integers(0,16,(10000,16))
    weights=np.stack([np.bincount(row,minlength=16) for row in draws])
    stat=lambda x:stats(x,draws,weights)
    groups=[];changes=[];contrasts=[];copies=[];controls=[]
    for ci,(role,stop,kind) in enumerate(CASES):
        for gi in range(3):
            own=0
            for bi in range(16):
                for life in range(4):
                    for noise in (0,1):
                        own+=records[bi]['lives'][life]['cells'][noise][ci][gi]['terminal_selector']['inferred_family']==role
            y=data['terminal_preference'][...,ci,gi]
            profiles=np.sum(np.stack([b['terminal_values'][:,:,ci,gi] for b in blocks]),axis=(0,1,2))/128
            groups.append(dict(role=role,stop=stop,condition=kind,generation=gi+1,
                metrics={k:stat(v[...,ci,gi]) for k,v in data.items()},terminal_profile=profiles.tolist(),
                negative=int(np.count_nonzero(y<0)),zero=int(np.count_nonzero(y==0)),own_guide=own,cells=128))
        changes.append(dict(role=role,stop=stop,condition=kind,change='G3_minus_G1',
            metrics={k:stat(v[...,ci,2]-v[...,ci,0]) for k,v in data.items()}))
    for role in (0,1):
        for kind in KINDS:
            early=CASES.index((role,1000,kind));late=CASES.index((role,1300,kind))
            for g in range(3):
                delta=data['terminal_preference'][...,late,g]-data['terminal_preference'][...,early,g]
                contrasts.append(dict(role=role,condition=kind,generation=g+1,contrast='1300_minus_1000',
                    metrics={k:stat(v[...,late,g]-v[...,early,g]) for k,v in data.items()},
                    positive=int(np.count_nonzero(delta>0)),negative=int(np.count_nonzero(delta<0)),
                    zero=int(np.count_nonzero(delta==0))))
        for stop in (1000,1300):
            for gi in range(3):
                a=CASES.index((role,stop,'intact'));b=CASES.index((role,stop,'copy'))
                copies.append(dict(role=role,stop=stop,generation=gi+1,contrast='intact_minus_copy',
                    metrics={k:stat(v[...,a,gi]-v[...,b,gi]) for k,v in data.items()}))
                for left,right in (('copy','write_off'),('intact','read_off'),('intact','write_off')):
                    a=CASES.index((role,stop,left));b=CASES.index((role,stop,right))
                    value=stat(data['terminal_preference'][...,a,gi]-data['terminal_preference'][...,b,gi])
                    controls.append(dict(role=role,stop=stop,left=left,right=right,generation=gi+1,**value,
                        passes=value['pointwise_block_bootstrap_95'][0]>0))
    p=next(c['metrics']['terminal_preference'] for c in contrasts
        if c['role']==1 and c['condition']=='intact' and c['generation']==3)
    low,high=p['pointwise_block_bootstrap_95']
    label='B_CONTINUATION_FAVORED' if low>0 else 'B_STOPPING_FAVORED' if high<0 else 'B_STOPPING_DIFFERENCE_UNRESOLVED'
    ok=all(c['passes'] for c in controls)
    expected=dict(schema='l20_stopping_time_v1',primary_name='B_intact_G3_1300_minus_1000_terminal_preference',
        primary=p,primary_interval_classification=label,apparatus_qualified=ok,
        label=label if ok else 'APPARATUS_NOT_QUALIFIED',groups=groups,stop_contrasts=contrasts,
        copy_contrasts=copies,controls=controls,serial_changes=changes,independent_blocks=16,record_host_pairs=128,
        noise_replicates=2,labelled_cells=6144,new_assays=512,reused_labels=5632,new_founders=0,
        new_upstream_dynamics=0,cases=[list(c) for c in CASES],terminal_times=[0,1,100,300],
        metric_columns=['native_preference','best_own_R_shape'],bootstrap_seed=14720260919,bootstrap_draws=10000,
        secondary_intervals_multiplicity_adjusted=False,equivalence_test=False,fresh_cohort=False,
        same_extended_history=True,new_independent_noise=False,adaptive_stopping_policy_tested=False,
        all_cases_retained=True,carrier_bytes=2048,refits=0,assay_enters_lineage=False,automatic_successor=False)
    physics.nested(summary,expected)
    assert len(groups)==48 and len(contrasts)==24 and len(copies)==12 and len(controls)==36 and len(changes)==16
    return dict(passes=True,groups=48,stop_contrasts=24,copy_contrasts=12,controls=36,serial_changes=16,
        independent_blocks=16,normalization=16,labelled_cells=6144,new_assays=512,bootstrap_draws=10000,
        bootstrap_seed=14720260919,primary_independently_reconstructed=True)
