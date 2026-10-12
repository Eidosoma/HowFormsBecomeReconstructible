"""Independent crossed contrasts, whole-block normalization and control checks."""
import numpy as np
from .placement_audit import CASES,KINDS,physics
from .phase_budget_analysis_check import stats


def pieces(a,b,c,d):
    return dict(natural_change=d-a,content_at_early=c-a,content_at_late=d-b,
        placement_on_early=b-a,placement_on_late=d-c,earlier_placement_on_late=c-d,
        interaction=(d-b)-(c-a),content_symmetric=(c+d-a-b)*.5,
        placement_symmetric=(b+d-a-c)*.5)


def check(summary,blocks,records):
    assert len(blocks)==len(records)==16
    names=('terminal_preference','terminal_reference_shape','outgoing_shape','shape_margin','guide_margin',
        'alternative_shape','canonical_own','canonical_alternative','canonical_margin')
    data={k:np.empty((16,4,2,32,3)) for k in names}
    for bi,b in enumerate(blocks):
        assert b['terminal_values'].shape==(4,2,32,3,4,2) and b['record_values'].shape==(4,2,32,3,7)
        data['terminal_preference'][bi]=b['terminal_values'][...,-1,0]
        data['terminal_reference_shape'][bi]=b['terminal_values'][...,-1,1]
        for col,name in enumerate(names[2:]):data[name][bi]=b['record_values'][...,col]
    draws=np.random.Generator(np.random.PCG64(14820260919)).integers(0,16,(10000,16))
    weights=np.stack([np.bincount(row,minlength=16) for row in draws]);stat=lambda x:stats(x,draws,weights)
    groups=[];contrasts=[];controls=[];copies=[];new_total=0
    for ci,(role,p,a,kind) in enumerate(CASES):
        for gi in range(3):
            modes=dict(natural_diagonal=0,identical_routed_bytes=0,new_assay=0);own=donor=0
            for bi in range(16):
                for life in range(4):
                    for noise in (0,1):
                        e=records[bi]['lives'][life]['cells'][noise][ci][gi]
                        modes[e['source_mode']]+=1
                        assert e['new_assay']==(e['source_mode']=='new_assay')
                        own+=e['natural_selector']['inferred_family']==role
                        donor+=e['address_selector']['inferred_family']==role
            new_total+=modes['new_assay'];y=data['terminal_preference'][...,ci,gi]
            profile=np.sum(np.stack([b['terminal_values'][:,:,ci,gi] for b in blocks]),axis=(0,1,2))/128
            groups.append(dict(role=role,packet_stop=p,address_stop=a,condition=kind,generation=gi+1,
                metrics={m:stat(v[...,ci,gi]) for m,v in data.items()},terminal_profile=profile.tolist(),
                negative=int(np.count_nonzero(y<0)),zero=int(np.count_nonzero(y==0)),cells=128,
                natural_own_guide=own,donor_own_guide=donor,new_assays=modes['new_assay'],source_modes=modes))
    for role in (0,1):
        for kind in KINDS:
            q=[CASES.index((role,p,a,kind)) for p in (1000,1300) for a in (1000,1300)]
            for g in range(3):
                parts={m:pieces(*(v[...,i,g] for i in q)) for m,v in data.items()}
                content=parts['terminal_preference']['content_symmetric'];placement=parts['terminal_preference']['placement_symmetric']
                np.testing.assert_allclose(content+placement,parts['terminal_preference']['natural_change'],atol=1e-12,rtol=0)
                values={name:{m:stat(part[name]) for m,part in parts.items()} for name in parts['terminal_preference']}
                signs={name:dict(positive=int(np.count_nonzero(x>0)),negative=int(np.count_nonzero(x<0)),
                    zero=int(np.count_nonzero(x==0))) for name,x in parts['terminal_preference'].items()}
                contrasts.append(dict(role=role,condition=kind,generation=g+1,decomposition=values,preference_signs=signs))
        for p in (1000,1300):
            for a in (1000,1300):
                for gi in range(3):
                    i=CASES.index((role,p,a,'intact'));j=CASES.index((role,p,a,'copy'))
                    copies.append(dict(role=role,packet_stop=p,address_stop=a,generation=gi+1,
                        metrics={m:stat(v[...,i,gi]-v[...,j,gi]) for m,v in data.items()}))
                    for left,right in (('copy','write_off'),('intact','read_off'),('intact','write_off')):
                        i=CASES.index((role,p,a,left));j=CASES.index((role,p,a,right))
                        s=stat(data['terminal_preference'][...,i,gi]-data['terminal_preference'][...,j,gi])
                        controls.append(dict(role=role,packet_stop=p,address_stop=a,generation=gi+1,left=left,right=right,
                            **s,passes=s['pointwise_block_bootstrap_95'][0]>0))
    i=CASES.index((1,1300,1000,'intact'));j=CASES.index((1,1300,1300,'intact'))
    p=stat(data['terminal_preference'][...,i,1]-data['terminal_preference'][...,j,1])
    lo,hi=p['pointwise_block_bootstrap_95'];qualified=all(c['passes'] for c in controls)
    label='B_G2_EARLIER_PLACEMENT_FAVORED' if lo>0 else 'B_G2_LATER_PLACEMENT_FAVORED' if hi<0 else 'B_G2_PLACEMENT_DIFFERENCE_UNRESOLVED'
    expected=dict(schema='l20_packet_placement_v1',primary_name='B_intact_G2_late_packet_early_minus_late_placement',
        primary=p,primary_interval_classification=label,apparatus_qualified=qualified,
        label=label if qualified else 'APPARATUS_NOT_QUALIFIED',groups=groups,decompositions=contrasts,
        controls=controls,copy_contrasts=copies,independent_blocks=16,record_host_pairs=128,noise_replicates=2,
        labelled_cells=12288,natural_diagonals=6144,new_assays=new_total,reused_labels=12288-new_total,new_founders=0,
        new_upstream_dynamics=0,cases=[list(c) for c in CASES],terminal_times=[0,1,100,300],
        bootstrap_seed=14820260919,bootstrap_draws=10000,secondary_intervals_multiplicity_adjusted=False,
        equivalence_test=False,fresh_cohort=False,same_extended_history=True,new_independent_noise=False,
        autonomous_address_repair=False,all_cases_retained=True,carrier_bytes=2048,refits=0,
        assay_enters_lineage=False,automatic_successor=False)
    physics.nested(summary,expected)
    assert len(groups)==96 and len(contrasts)==24 and len(controls)==72 and len(copies)==24
    return dict(passes=True,groups=96,decompositions=24,controls=72,copy_contrasts=24,independent_blocks=16,
        normalization=16,labelled_cells=12288,natural_diagonals=6144,new_assays=new_total,
        bootstrap_draws=10000,bootstrap_seed=14820260919,primary_independently_reconstructed=True)
