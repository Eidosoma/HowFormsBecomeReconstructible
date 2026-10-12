"""D149 fixed primary, absolute arm performance and complete controls."""
import numpy as np
from .component_system import CASES,KINDS,EDITS,RECORD_NAMES
from .phase_budget_analysis import stats
from . import placement_review as fields

SEED=14920260919
TERMINAL_NAMES=('terminal_preference','terminal_reference_own','terminal_reference_alternative','continuous_V_margin')


def contrasts(u,a,p,m):
    return dict(attenuate_minus_sham_mean=a-(p+m)/2,attenuate_minus_untouched=a-u,
        sham_mean_minus_untouched=(p+m)/2-u,sham_plus_minus_minus=p-m,
        sham_plus_minus_untouched=p-u,sham_minus_minus_untouched=m-u)


def arrays(blocks):
    assert len(blocks)==16
    t=np.stack([b['terminal_values'] for b in blocks]);r=np.stack([b['record_values'] for b in blocks])
    assert t.shape==(16,4,2,32,3,4,4) and r.shape==(16,4,2,32,3,10)
    assert np.isfinite(t).all() and np.isfinite(r).all()
    data={k:t[...,-1,j] for j,k in enumerate(TERMINAL_NAMES)}
    data.update({k:r[...,j] for j,k in enumerate(RECORD_NAMES)})
    return data,t


def summarize(blocks,records):
    assert len(records)==16
    data,t=arrays(blocks);draws=np.random.default_rng(SEED).integers(0,16,(10000,16))
    stat=lambda x:stats(x,draws)
    groups=[];comparisons=[];controls=[];copies=[];accounting=[];codes=[]
    for ci,(role,edit,kind) in enumerate(CASES):
        c=fields.codes(np.stack([b['terminal_states'][:,:,ci,:,:,0] for b in blocks]),role);codes.append(c)
        counts=np.stack([(c==j).sum(axis=-1) for j in range(3)],-1)
        np.testing.assert_array_equal((counts[...,1]-counts[...,2])/256,t[...,ci,:, :,0])
        for gi in range(3):
            y=data['terminal_preference'][...,ci,gi]
            entries=[m['lives'][l]['cells'][n][ci][gi] for m in records for l in range(4) for n in (0,1)]
            groups.append(dict(role=role,edit=edit,condition=kind,generation=gi+1,
                metrics={k:stat(v[...,ci,gi]) for k,v in data.items()},cells=128,
                terminal_profile=t[...,ci,gi,:,:].mean(axis=(0,1,2)).tolist(),
                count_profile=counts[...,gi,:,:].mean(axis=(0,1,2)).tolist(),
                negative=int((y<0).sum()),zero=int((y==0).sum()),
                degenerate=sum(e['degenerate'] for e in entries),new_assays=sum(e['new_assay'] for e in entries),
                source_modes={mode:sum(e['source_mode']==mode for e in entries) for mode in ('untouched','identical_bytes','new_assay')}))
    for role in (0,1):
        for kind in KINDS:
            ids=[CASES.index((role,e,kind)) for e in EDITS]
            for gi in range(3):
                parts={k:contrasts(*(v[...,i,gi] for i in ids)) for k,v in data.items()}
                comparisons.append(dict(role=role,condition=kind,generation=gi+1,
                    contrasts={name:{k:stat(v[name]) for k,v in parts.items()} for name in parts['terminal_preference']},
                    preference_signs={name:dict(positive=int((x>0).sum()),negative=int((x<0).sum()),zero=int((x==0).sum()))
                        for name,x in parts['terminal_preference'].items()}))
                for e,i in zip(EDITS[1:],ids[1:]):
                    table=fields.transitions(codes[i][...,gi,-1,:],codes[ids[0]][...,gi,-1,:])
                    contribution=fields.parts(table)
                    np.testing.assert_array_equal(contribution[...,-1]/256,data['terminal_preference'][...,i,gi]-data['terminal_preference'][...,ids[0],gi])
                    accounting.append(dict(role=role,condition=kind,generation=gi+1,edit=e,
                        rows='untouched_quiet_own_alternative',columns='edited_quiet_own_alternative',
                        summed_transition_table=table.sum(axis=(0,1,2)).tolist(),
                        individual_tables=table.tolist(),
                        contributions={k:stat(contribution[...,j]/256) for j,k in enumerate(('strong_switch','activation','deactivation','total'))}))
        for edit in EDITS:
            idx=lambda k:CASES.index((role,edit,k))
            for gi in range(3):
                copies.append(dict(role=role,edit=edit,generation=gi+1,
                    metrics={k:stat(v[...,idx('intact'),gi]-v[...,idx('copy'),gi]) for k,v in data.items()}))
                for left,right in (('copy','write_off'),('intact','read_off'),('intact','write_off')):
                    value=stat(data['terminal_preference'][...,idx(left),gi]-data['terminal_preference'][...,idx(right),gi])
                    controls.append(dict(role=role,edit=edit,generation=gi+1,left=left,right=right,
                        **value,apparatus_gate=edit=='untouched',passes=value['pointwise_block_bootstrap_95'][0]>0))
    p=next(c['contrasts']['attenuate_minus_sham_mean']['terminal_preference'] for c in comparisons
        if (c['role'],c['condition'],c['generation'])==(1,'intact',2))
    lo,hi=p['pointwise_block_bootstrap_95'];qualified=all(c['passes'] for c in controls if c['apparatus_gate'])
    label='B_G2_ATTENUATION_FAVORED' if lo>0 else 'B_G2_SHAMS_FAVORED' if hi<0 else 'B_G2_COMPONENT_DIFFERENCE_UNRESOLVED'
    new=sum(g['new_assays'] for g in groups)
    return dict(schema='l20_competing_component_v1',primary_name='B_intact_G2_attenuate_minus_sham_mean',
        primary=p,primary_interval_classification=label,apparatus_qualified=qualified,
        label=label if qualified else 'APPARATUS_NOT_QUALIFIED',groups=groups,comparisons=comparisons,
        controls=controls,copy_contrasts=copies,transition_accounting=accounting,
        independent_blocks=16,record_host_pairs=128,noise_replicates=2,labelled_cells=12288,untouched=3072,
        new_assays=new,reused_labels=12288-new,new_founders=0,new_upstream_dynamics=0,
        cases=[list(c) for c in CASES],terminal_times=[0,1,100,300],bootstrap_seed=SEED,bootstrap_draws=10000,
        secondary_intervals_multiplicity_adjusted=False,equivalence_test=False,fresh_cohort=False,
        same_extended_history=True,new_independent_noise=False,autonomous_repair=False,
        all_cases_retained=True,carrier_bytes=2048,refits=0,assay_enters_lineage=False,
        analyst_supplied_edit=True,rerouted_after_edit=False,automatic_successor=False)
