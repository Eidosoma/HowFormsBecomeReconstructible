"""D148 crossed attribution, one G2 placement primary, complete controls."""
import numpy as np
from .placement_system import CASES,KINDS
from .phase_budget_analysis import stats

SEED=14820260919
METRICS=('terminal_preference','outgoing_shape','shape_margin','guide_margin','alternative_shape',
    'canonical_own','canonical_alternative','canonical_margin','terminal_reference_shape')


def arrays(blocks):
    assert len(blocks)==16
    terminal=np.stack([b['terminal_values'] for b in blocks]);record=np.stack([b['record_values'] for b in blocks])
    assert terminal.shape==(16,4,2,32,3,4,2) and record.shape==(16,4,2,32,3,7)
    assert np.isfinite(terminal).all() and np.isfinite(record).all()
    result=dict(terminal_preference=terminal[...,-1,0],terminal_reference_shape=terminal[...,-1,1])
    result.update({m:record[...,j] for j,m in enumerate(METRICS[1:-1])})
    return result


def decompose(ee,el,le,ll):
    return dict(natural_change=ll-ee,content_at_early=le-ee,content_at_late=ll-el,
        placement_on_early=el-ee,placement_on_late=ll-le,earlier_placement_on_late=le-ll,
        interaction=ll-le-el+ee,content_symmetric=((le-ee)+(ll-el))/2,
        placement_symmetric=((el-ee)+(ll-le))/2)


def summarize(blocks,records):
    assert len(records)==16
    data=arrays(blocks);draws=np.random.default_rng(SEED).integers(0,16,(10000,16))
    groups=[];contrasts=[];controls=[];copies=[]
    for ci,(role,pstop,astop,kind) in enumerate(CASES):
        for gi in range(3):
            entries=[records[b]['lives'][l]['cells'][n][ci][gi] for b in range(16) for l in range(4) for n in (0,1)]
            y=data['terminal_preference'][...,ci,gi]
            groups.append(dict(role=role,packet_stop=pstop,address_stop=astop,condition=kind,generation=gi+1,
                metrics={m:stats(v[...,ci,gi],draws) for m,v in data.items()},
                terminal_profile=np.stack([b['terminal_values'][:,:,ci,gi] for b in blocks]).mean(axis=(0,1,2)).tolist(),
                negative=int((y<0).sum()),zero=int((y==0).sum()),cells=128,
                natural_own_guide=sum(e['natural_selector']['inferred_family']==role for e in entries),
                donor_own_guide=sum(e['address_selector']['inferred_family']==role for e in entries),
                new_assays=sum(e['new_assay'] for e in entries),
                source_modes={k:sum(e['source_mode']==k for e in entries) for k in ('natural_diagonal','identical_routed_bytes','new_assay')}))
    for role in (0,1):
        for kind in KINDS:
            indices=[CASES.index((role,p,a,kind)) for p,a in ((1000,1000),(1000,1300),(1300,1000),(1300,1300))]
            for gi in range(3):
                parts={m:decompose(*(v[...,i,gi] for i in indices)) for m,v in data.items()}
                values={name:{m:stats(part[name],draws) for m,part in parts.items()} for name in parts['terminal_preference']}
                signs={name:dict(positive=int((x>0).sum()),negative=int((x<0).sum()),zero=int((x==0).sum()))
                    for name,x in parts['terminal_preference'].items()}
                np.testing.assert_allclose(parts['terminal_preference']['content_symmetric']+parts['terminal_preference']['placement_symmetric'],
                    parts['terminal_preference']['natural_change'],atol=1e-12,rtol=0)
                contrasts.append(dict(role=role,condition=kind,generation=gi+1,decomposition=values,preference_signs=signs))
        for p in (1000,1300):
            for a in (1000,1300):
                for gi in range(3):
                    idx=lambda k:CASES.index((role,p,a,k))
                    copies.append(dict(role=role,packet_stop=p,address_stop=a,generation=gi+1,
                        metrics={m:stats(v[...,idx('intact'),gi]-v[...,idx('copy'),gi],draws) for m,v in data.items()}))
                    for left,right in (('copy','write_off'),('intact','read_off'),('intact','write_off')):
                        y=data['terminal_preference'];value=stats(y[...,idx(left),gi]-y[...,idx(right),gi],draws)
                        controls.append(dict(role=role,packet_stop=p,address_stop=a,generation=gi+1,left=left,right=right,
                            **value,passes=value['pointwise_block_bootstrap_95'][0]>0))
    primary=next(r['decomposition']['earlier_placement_on_late']['terminal_preference'] for r in contrasts
        if (r['role'],r['condition'],r['generation'])==(1,'intact',2))
    lo,hi=primary['pointwise_block_bootstrap_95'];qualified=all(c['passes'] for c in controls)
    label='B_G2_EARLIER_PLACEMENT_FAVORED' if lo>0 else 'B_G2_LATER_PLACEMENT_FAVORED' if hi<0 else 'B_G2_PLACEMENT_DIFFERENCE_UNRESOLVED'
    new=sum(r['new_assays'] for r in groups)
    return dict(schema='l20_packet_placement_v1',primary_name='B_intact_G2_late_packet_early_minus_late_placement',
        primary=primary,primary_interval_classification=label,apparatus_qualified=qualified,
        label=label if qualified else 'APPARATUS_NOT_QUALIFIED',groups=groups,decompositions=contrasts,
        controls=controls,copy_contrasts=copies,independent_blocks=16,record_host_pairs=128,noise_replicates=2,
        labelled_cells=12288,natural_diagonals=6144,new_assays=new,reused_labels=12288-new,new_founders=0,
        new_upstream_dynamics=0,cases=[list(c) for c in CASES],terminal_times=[0,1,100,300],
        bootstrap_seed=SEED,bootstrap_draws=10000,secondary_intervals_multiplicity_adjusted=False,
        equivalence_test=False,fresh_cohort=False,same_extended_history=True,new_independent_noise=False,
        autonomous_address_repair=False,all_cases_retained=True,carrier_bytes=2048,refits=0,
        assay_enters_lineage=False,automatic_successor=False)
