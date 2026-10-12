"""D144 fixed paired sixteen-founder-block inference; one primary contrast."""
import numpy as np
from .symmetry_system import CASES

SEED=14420260918
METRICS=('terminal_preference','outgoing_shape','write_end_shape','terminal_reference_shape')


def stats(x,draws):
    if x.shape!=(16,4,2) or draws.shape!=(10000,16) or not np.isfinite(x).all():raise ValueError('complete sixteen-block panel required')
    means=x.mean(axis=(1,2)); interval=np.quantile(means[draws].mean(axis=1),[.025,.975])
    return dict(mean=float(means.mean()),pointwise_block_bootstrap_95=interval.tolist(),
        block_means=means.tolist(),life_noise_values=x.tolist())


def arrays(blocks):
    assert len(blocks)==16
    terminal=np.stack([b['terminal_values'] for b in blocks])
    record=np.stack([b['record_values'] for b in blocks])
    write=np.stack([b['write_values'] for b in blocks])
    assert terminal.shape==(16,4,2,22,4,2) and record.shape==(16,4,2,22,2) and write.shape==(16,4,2,22,4,2)
    assert all(np.isfinite(x).all() for x in (terminal,record,write))
    return dict(terminal_preference=terminal[...,-1,0],outgoing_shape=record[...,1],
        write_end_shape=write[...,-1,1],terminal_reference_shape=terminal[...,-1,1])


def summarize(blocks,records):
    data=arrays(blocks); draws=np.random.default_rng(SEED).integers(0,16,(10000,16))
    rows=[]; contrasts=[]; controls=[]
    for ci,(role,kind) in enumerate(CASES):
        zero=CASES.index((role,'zero')); values={m:stats(y[...,ci],draws) for m,y in data.items()}
        profiles={phase:np.stack([b[phase+'_values'] for b in blocks])[:,:,:,ci].mean(axis=(0,1,2)).tolist()
                  for phase in ('read','write','terminal')}
        labels=[records[b]['lives'][l]['trials'][n]['paths'][ci]['terminal_selector']['inferred_family']
                for b in range(16) for l in range(4) for n in range(2)]
        shifts=np.stack([b['shift'] for b in blocks])[:,:,:,ci]
        counts=np.zeros((16,16),np.int64); np.add.at(counts,tuple(shifts.reshape(-1,2).T),1)
        rows.append(dict(role=role,condition=kind,metrics=values,profiles=profiles,address_counts=counts.tolist(),
            incoming_shape=float(np.stack([b['record_values'] for b in blocks])[:,:,:,ci,0].mean()),
            negative=int(np.count_nonzero(data['terminal_preference'][...,ci]<0)),
            zero=int(np.count_nonzero(data['terminal_preference'][...,ci]==0)),own_guide=sum(x==role for x in labels),cells=128))
        if kind!='zero':contrasts.append(dict(role=role,condition=kind,reference='zero',
            metrics={m:stats(y[...,ci]-y[...,zero],draws) for m,y in data.items()}))
    for role in (0,1):
        for left,right in (('copy','write_off'),('zero','read_off'),('zero','write_off')):
            value=stats(data['terminal_preference'][...,CASES.index((role,left))]-data['terminal_preference'][...,CASES.index((role,right))],draws)
            controls.append(dict(role=role,left=left,right=right,**value,passes=value['pointwise_block_bootstrap_95'][0]>0))
    primary=next(r['metrics']['terminal_preference'] for r in contrasts if (r['role'],r['condition'])==(1,'q4'))
    lo,hi=primary['pointwise_block_bootstrap_95']; instrument=all(r['passes'] for r in controls)
    evidence='B_COMPATIBLE_DESCENDANT_BENEFIT' if lo>0 else 'B_COMPATIBLE_DESCENDANT_HARM' if hi<0 else 'B_COMPATIBLE_EFFECT_UNRESOLVED'
    return dict(schema='l20_compatible_feedback_v1',primary_name='B_q4_minus_zero_terminal_preference',primary=primary,
        primary_interval_classification=evidence,apparatus_qualified=instrument,
        label=evidence if instrument else 'APPARATUS_NOT_QUALIFIED',groups=rows,contrasts=contrasts,controls=controls,
        independent_blocks=16,record_host_pairs=128,noise_replicates=2,terminal_cells=2816,rewrites=1,
        cases=[list(c) for c in CASES],read_times=[0,1,100,101,300],write_times=[0,1,300,1000],terminal_times=[0,1,100,300],
        metric_columns=['native_preference','best_own_R_shape'],bootstrap_seed=SEED,bootstrap_draws=10000,
        secondary_intervals_multiplicity_adjusted=False,equivalence_test=False,autonomous_address_rule=False,
        fresh_founders=True,all_cases_retained=True,refits=0,carrier_bytes=2048,automatic_successor=False)
