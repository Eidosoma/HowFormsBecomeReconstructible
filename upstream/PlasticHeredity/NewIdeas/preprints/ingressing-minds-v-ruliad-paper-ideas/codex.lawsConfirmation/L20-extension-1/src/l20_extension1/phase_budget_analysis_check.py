"""Independent D146 whole-block inference for the fixed allocation contrast."""
import numpy as np
from .phase_budget_audit import CASES,KINDS,TIMINGS,phase_config,physics


def stats(x,draws,weights=None):
    assert x.shape==(16,4,2) and draws.shape==(10000,16) and np.isfinite(x).all()
    means=np.array([sum(float(v) for v in block.flat)/8 for block in x])
    if weights is None:weights=np.stack([np.bincount(row,minlength=16) for row in draws])
    boot=weights@means/16
    return dict(mean=float(sum(means)/16),pointwise_block_bootstrap_95=np.percentile(boot,[2.5,97.5]).tolist(),
        block_means=means.tolist(),life_noise_values=x.tolist())


def check(summary,blocks,records):
    assert len(blocks)==len(records)==16
    metrics={k:np.empty((16,4,2,24,3)) for k in ('terminal_preference','outgoing_shape','write_end_shape','terminal_reference_shape')}
    for bi,block in enumerate(blocks):
        assert block['terminal_values'].shape==(4,2,24,3,4,2) and block['record_values'].shape==(4,2,24,3,2)
        metrics['terminal_preference'][bi]=block['terminal_values'][...,-1,0]
        metrics['outgoing_shape'][bi]=block['record_values'][...,1]
        metrics['write_end_shape'][bi]=block['write_values'][...,-1,1]
        metrics['terminal_reference_shape'][bi]=block['terminal_values'][...,-1,1]
    draws=np.random.Generator(np.random.PCG64(14620260918)).integers(0,16,(10000,16))
    weights=np.stack([np.bincount(row,minlength=16) for row in draws])
    stat=lambda x:stats(x,draws,weights)
    groups=[];contrasts=[];controls=[];copy_contrasts=[];changes=[];advantage=[];allocation=[]
    for ci,(role,kind) in enumerate(CASES):
        for gi in range(3):
            profiles={phase:(np.sum(np.stack([b[phase+'_values'][:,:,ci,gi] for b in blocks]),axis=(0,1,2))/128).tolist()
                for phase in ('read','write','terminal')}
            shifts=np.zeros((16,16),int);own=0;incoming=0.
            for bi,block in enumerate(blocks):
                for l in range(4):
                    for n in range(2):
                        dy,dx=block['shift'][l,n,ci,gi];shifts[dy,dx]+=1
                        own+=records[bi]['lives'][l]['trials'][n]['paths'][ci]['generations'][gi]['terminal_selector']['inferred_family']==role
                        incoming+=float(block['record_values'][l,n,ci,gi,0])/128
            y=metrics['terminal_preference'][...,ci,gi]
            groups.append(dict(role=role,condition=kind,generation=gi+1,
                metrics={m:stat(v[...,ci,gi]) for m,v in metrics.items()},profiles=profiles,address_counts=shifts.tolist(),
                incoming_shape=incoming,negative=int((y<0).sum()),zero=int((y==0).sum()),own_guide=own,cells=128))
            if kind!='base':
                z=CASES.index((role,'base'))
                contrasts.append(dict(role=role,condition=kind,reference='base',generation=gi+1,
                    metrics={m:stat(v[...,ci,gi]-v[...,z,gi]) for m,v in metrics.items()}))
        changes.append(dict(role=role,condition=kind,change='G3_minus_G1',
            metrics={m:stat(v[...,ci,2]-v[...,ci,0]) for m,v in metrics.items()}))
    for role in (0,1):
        ri=CASES.index((role,'read'));wi=CASES.index((role,'write'))
        advantage.append(dict(role=role,change='G3_minus_G1_read_minus_write',
            metrics={m:stat(v[...,ri,2]-v[...,wi,2]-v[...,ri,0]+v[...,wi,0]) for m,v in metrics.items()}))
        for gi in range(3):
            allocation.append(dict(role=role,condition='read',reference='write',generation=gi+1,
                metrics={m:stat(v[...,ri,gi]-v[...,wi,gi]) for m,v in metrics.items()}))
            for timing in ('base','read','write'):
                ci=CASES.index((role,timing));pi=CASES.index((role,timing+'_copy'))
                copy_contrasts.append(dict(role=role,condition=timing,reference=timing+'_copy',generation=gi+1,
                    metrics={m:stat(v[...,ci,gi]-v[...,pi,gi]) for m,v in metrics.items()}))
                for left,right in ((timing+'_copy',timing+'_write_off'),
                                   (timing,timing+'_read_off'),(timing,timing+'_write_off')):
                    x=metrics['terminal_preference'][...,CASES.index((role,left)),gi]-metrics['terminal_preference'][...,CASES.index((role,right)),gi]
                    value=stat(x)
                    controls.append(dict(role=role,left=left,right=right,generation=gi+1,**value,
                        passes=value['pointwise_block_bootstrap_95'][0]>0))
    primary=stat(metrics['terminal_preference'][...,CASES.index((1,'read')),2]-
                 metrics['terminal_preference'][...,CASES.index((1,'write')),2])
    low,high=primary['pointwise_block_bootstrap_95']
    label='B_READ_ALLOCATION_FAVORED' if low>0 else 'B_WRITE_ALLOCATION_FAVORED' if high<0 else 'B_ALLOCATION_UNRESOLVED'
    passes=all(c['passes'] for c in controls)
    expected=dict(schema='l20_phase_budget_v1',primary_name='B_read_minus_write_G3_terminal_preference',primary=primary,
        primary_interval_classification=label,apparatus_qualified=passes,label=label if passes else 'APPARATUS_NOT_QUALIFIED',
        groups=groups,contrasts=contrasts,controls=controls,copy_contrasts=copy_contrasts,serial_changes=changes,advantage_changes=advantage,allocation_contrasts=allocation,
        independent_blocks=16,record_host_pairs=128,noise_replicates=2,terminal_cells=3072,stage_cells=9216,rewrites=3,
        cases=[list(c) for c in CASES],timings={k:list(v) for k,v in TIMINGS.items()},
        read_times={k:list(phase_config(k).read_times) for k in KINDS},
        write_times={k:list(phase_config(k).source_times) for k in KINDS},terminal_times=[0,1,100,300],
        metric_columns=['native_preference','best_own_R_shape'],bootstrap_seed=14620260918,bootstrap_draws=10000,
        secondary_intervals_multiplicity_adjusted=False,equivalence_test=False,autonomous_address_rule=False,
        fresh_founders=True,all_cases_retained=True,refits=0,carrier_bytes=2048,assay_enters_lineage=False,automatic_successor=False)
    physics.nested(summary,expected)
    return dict(passes=True,independent_blocks=16,terminal_cells=3072,stage_cells=9216,groups=72,contrasts=66,
        control_checks=54,copy_contrasts=18,serial_changes=24,advantage_changes=2,allocation_contrasts=6,new_dynamics=0)
