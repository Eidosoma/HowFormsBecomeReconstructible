"""Independent paired sum/count bootstrap verification for all D144 outcomes."""
import numpy as np
from .symmetry_audit import CASES,physics


def stats(x,draws,weights=None):
    assert x.shape==(16,4,2) and draws.shape==(10000,16) and np.isfinite(x).all()
    means=np.array([sum(float(v) for v in block.flat)/8 for block in x])
    if weights is None: weights=np.stack([np.bincount(row,minlength=16) for row in draws])
    boot=weights@means/16
    return dict(mean=float(sum(means)/16),pointwise_block_bootstrap_95=np.percentile(boot,[2.5,97.5]).tolist(),
        block_means=means.tolist(),life_noise_values=x.tolist())


def check(summary,blocks,records):
    assert len(blocks)==len(records)==16
    metrics={k:np.empty((16,4,2,22)) for k in ('terminal_preference','outgoing_shape','write_end_shape','terminal_reference_shape')}
    for bi,block in enumerate(blocks):
        assert block['terminal_values'].shape==(4,2,22,4,2) and block['record_values'].shape==(4,2,22,2)
        metrics['terminal_preference'][bi]=block['terminal_values'][...,-1,0]
        metrics['outgoing_shape'][bi]=block['record_values'][...,1]
        metrics['write_end_shape'][bi]=block['write_values'][...,-1,1]
        metrics['terminal_reference_shape'][bi]=block['terminal_values'][...,-1,1]
    draws=np.random.Generator(np.random.PCG64(14420260918)).integers(0,16,(10000,16))
    weights=np.stack([np.bincount(row,minlength=16) for row in draws])
    stat=lambda x:stats(x,draws,weights)
    groups=[]; contrasts=[]; controls=[]
    for ci,(role,kind) in enumerate(CASES):
        profiles={phase:(np.sum(np.stack([b[phase+'_values'][:,: ,ci] for b in blocks]),axis=(0,1,2))/128).tolist()
                  for phase in ('read','write','terminal')}
        shifts=np.zeros((16,16),int); own=0; incoming=0.
        for bi,block in enumerate(blocks):
            for l in range(4):
                for n in range(2):
                    dy,dx=block['shift'][l,n,ci]; shifts[dy,dx]+=1
                    own+=records[bi]['lives'][l]['trials'][n]['paths'][ci]['terminal_selector']['inferred_family']==role
                    incoming+=float(block['record_values'][l,n,ci,0])/128
        y=metrics['terminal_preference'][...,ci]
        groups.append(dict(role=role,condition=kind,metrics={m:stat(v[...,ci]) for m,v in metrics.items()},
            profiles=profiles,address_counts=shifts.tolist(),incoming_shape=incoming,
            negative=int((y<0).sum()),zero=int((y==0).sum()),own_guide=own,cells=128))
        if kind!='zero':
            z=CASES.index((role,'zero'))
            contrasts.append(dict(role=role,condition=kind,reference='zero',metrics={m:stat(v[...,ci]-v[...,z]) for m,v in metrics.items()}))
    for role in (0,1):
        for left,right in (('copy','write_off'),('zero','read_off'),('zero','write_off')):
            x=metrics['terminal_preference'][...,CASES.index((role,left))]-metrics['terminal_preference'][...,CASES.index((role,right))]
            v=stat(x); controls.append(dict(role=role,left=left,right=right,**v,passes=v['pointwise_block_bootstrap_95'][0]>0))
    ci=CASES.index((1,'q4')); zi=CASES.index((1,'zero')); primary=stat(metrics['terminal_preference'][...,ci]-metrics['terminal_preference'][...,zi])
    low,high=primary['pointwise_block_bootstrap_95']; label='B_COMPATIBLE_DESCENDANT_BENEFIT' if low>0 else 'B_COMPATIBLE_DESCENDANT_HARM' if high<0 else 'B_COMPATIBLE_EFFECT_UNRESOLVED'
    passes=all(c['passes'] for c in controls)
    expected=dict(schema='l20_compatible_feedback_v1',primary_name='B_q4_minus_zero_terminal_preference',primary=primary,
        primary_interval_classification=label,apparatus_qualified=passes,label=label if passes else 'APPARATUS_NOT_QUALIFIED',
        groups=groups,contrasts=contrasts,controls=controls,independent_blocks=16,record_host_pairs=128,noise_replicates=2,
        terminal_cells=2816,rewrites=1,cases=[list(c) for c in CASES],read_times=[0,1,100,101,300],
        write_times=[0,1,300,1000],terminal_times=[0,1,100,300],metric_columns=['native_preference','best_own_R_shape'],
        bootstrap_seed=14420260918,bootstrap_draws=10000,secondary_intervals_multiplicity_adjusted=False,
        equivalence_test=False,autonomous_address_rule=False,fresh_founders=True,all_cases_retained=True,
        refits=0,carrier_bytes=2048,automatic_successor=False)
    physics.nested(summary,expected)
    return dict(passes=True,independent_blocks=16,terminal_cells=2816,groups=22,contrasts=20,control_checks=6,new_dynamics=0)
