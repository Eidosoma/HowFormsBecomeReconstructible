"""Independent D149 paired contrast, block interval and transition checker."""
import numpy as np
from .component_audit import CASES,KINDS,EDITS,physics,prior
from .phase_budget_analysis_check import stats


def pieces(u,a,p,m):
    return dict(attenuate_minus_sham_mean=(2*a-p-m)/2,attenuate_minus_untouched=a-u,
        sham_mean_minus_untouched=(p+m-2*u)/2,sham_plus_minus_minus=p-m,
        sham_plus_minus_untouched=p-u,sham_minus_minus_untouched=m-u)


def categories(v,role):
    templates=prior.prior.targets();mask=templates[0]!=templates[1]
    field=v[...,mask];own=(field>0)==(templates[role][mask]>0)
    result=np.zeros(field.shape,np.int8);active=np.abs(field)>.2
    result[active&own]=1;result[active&~own]=2
    return result


def table_and_parts(before,after):
    table=np.empty(before.shape[:-1]+(3,3),np.int64)
    for i in range(3):
        for j in range(3):table[...,i,j]=np.count_nonzero((before==i)&(after==j),axis=-1)
    switch=2*(table[...,2,1]-table[...,1,2]);activation=table[...,0,1]-table[...,0,2]
    deactivation=table[...,2,0]-table[...,1,0]
    total=np.sum(np.where(after==1,1,np.where(after==2,-1,0))-np.where(before==1,1,np.where(before==2,-1,0)),axis=-1)
    np.testing.assert_array_equal(switch+activation+deactivation,total)
    return table,np.stack((switch,activation,deactivation,total),-1)


def check(summary,blocks,records):
    assert len(blocks)==len(records)==16
    t=np.stack([b['terminal_values'] for b in blocks]);r=np.stack([b['record_values'] for b in blocks])
    assert t.shape==(16,4,2,32,3,4,4) and r.shape==(16,4,2,32,3,10)
    names=('terminal_preference','terminal_reference_own','terminal_reference_alternative','continuous_V_margin',
        'mean','rms','own_axis_rms','competing_axis_rms','residual_rms','edit_rms',
        'canonical_own','canonical_alternative','best_own','best_alternative')
    data={k:(t[...,-1,j] if j<4 else r[...,j-4]) for j,k in enumerate(names)}
    draws=np.random.Generator(np.random.PCG64(14920260919)).integers(0,16,(10000,16))
    weights=np.stack([np.bincount(d,minlength=16) for d in draws]);stat=lambda x:stats(x,draws,weights)
    groups=[];comparisons=[];controls=[];copies=[];accounting=[];codes=[]
    for ci,(role,edit,kind) in enumerate(CASES):
        code=categories(np.stack([b['terminal_states'][:,:,ci,:,:,0] for b in blocks]),role);codes.append(code)
        counts=np.stack([np.count_nonzero(code==j,axis=-1) for j in range(3)],-1)
        np.testing.assert_array_equal((counts[...,1]-counts[...,2])/256,t[...,ci,:,:,0])
        for g in range(3):
            entries=[records[b]['lives'][l]['cells'][n][ci][g] for b in range(16) for l in range(4) for n in (0,1)]
            y=data['terminal_preference'][...,ci,g]
            groups.append(dict(role=role,edit=edit,condition=kind,generation=g+1,
                metrics={k:stat(v[...,ci,g]) for k,v in data.items()},cells=128,
                terminal_profile=(np.sum(t[...,ci,g,:,:],axis=(0,1,2))/128).tolist(),
                count_profile=(np.sum(counts[...,g,:,:],axis=(0,1,2))/128).tolist(),
                negative=int(np.count_nonzero(y<0)),zero=int(np.count_nonzero(y==0)),
                degenerate=sum(e['degenerate'] for e in entries),new_assays=sum(e['new_assay'] for e in entries),
                source_modes={mode:sum(e['source_mode']==mode for e in entries) for mode in ('untouched','identical_bytes','new_assay')}))
    for role in (0,1):
        for kind in KINDS:
            ids=[CASES.index((role,e,kind)) for e in EDITS]
            for g in range(3):
                p={k:pieces(*(v[...,i,g] for i in ids)) for k,v in data.items()}
                comparisons.append(dict(role=role,condition=kind,generation=g+1,
                    contrasts={name:{k:stat(v[name]) for k,v in p.items()} for name in p['terminal_preference']},
                    preference_signs={name:dict(positive=int(np.count_nonzero(x>0)),negative=int(np.count_nonzero(x<0)),zero=int(np.count_nonzero(x==0)))
                        for name,x in p['terminal_preference'].items()}))
                for edit,i in zip(EDITS[1:],ids[1:]):
                    table,contrib=table_and_parts(codes[ids[0]][...,g,-1,:],codes[i][...,g,-1,:])
                    np.testing.assert_array_equal(contrib[...,-1]/256,data['terminal_preference'][...,i,g]-data['terminal_preference'][...,ids[0],g])
                    accounting.append(dict(role=role,condition=kind,generation=g+1,edit=edit,
                        rows='untouched_quiet_own_alternative',columns='edited_quiet_own_alternative',
                        summed_transition_table=np.sum(table,axis=(0,1,2)).tolist(),individual_tables=table.tolist(),
                        contributions={k:stat(contrib[...,j]/256) for j,k in enumerate(('strong_switch','activation','deactivation','total'))}))
        for edit in EDITS:
            ids={k:CASES.index((role,edit,k)) for k in KINDS}
            for g in range(3):
                copies.append(dict(role=role,edit=edit,generation=g+1,
                    metrics={k:stat(v[...,ids['intact'],g]-v[...,ids['copy'],g]) for k,v in data.items()}))
                for left,right in (('copy','write_off'),('intact','read_off'),('intact','write_off')):
                    value=stat(data['terminal_preference'][...,ids[left],g]-data['terminal_preference'][...,ids[right],g])
                    controls.append(dict(role=role,edit=edit,generation=g+1,left=left,right=right,
                        **value,apparatus_gate=edit=='untouched',passes=value['pointwise_block_bootstrap_95'][0]>0))
    a,p,m=(CASES.index((1,e,'intact')) for e in EDITS[1:])
    primary=stat(data['terminal_preference'][...,a,1]-.5*data['terminal_preference'][...,p,1]-.5*data['terminal_preference'][...,m,1])
    lo,hi=primary['pointwise_block_bootstrap_95'];qualified=all(c['passes'] for c in controls if c['apparatus_gate'])
    label='B_G2_ATTENUATION_FAVORED' if lo>0 else 'B_G2_SHAMS_FAVORED' if hi<0 else 'B_G2_COMPONENT_DIFFERENCE_UNRESOLVED'
    new=sum(row['new_assays'] for row in groups)
    expected=dict(schema='l20_competing_component_v1',primary_name='B_intact_G2_attenuate_minus_sham_mean',
        primary=primary,primary_interval_classification=label,apparatus_qualified=qualified,
        label=label if qualified else 'APPARATUS_NOT_QUALIFIED',groups=groups,comparisons=comparisons,
        controls=controls,copy_contrasts=copies,transition_accounting=accounting,independent_blocks=16,
        record_host_pairs=128,noise_replicates=2,labelled_cells=12288,untouched=3072,new_assays=new,
        reused_labels=12288-new,new_founders=0,new_upstream_dynamics=0,cases=[list(c) for c in CASES],
        terminal_times=[0,1,100,300],bootstrap_seed=14920260919,bootstrap_draws=10000,
        secondary_intervals_multiplicity_adjusted=False,equivalence_test=False,fresh_cohort=False,
        same_extended_history=True,new_independent_noise=False,autonomous_repair=False,
        all_cases_retained=True,carrier_bytes=2048,refits=0,assay_enters_lineage=False,
        analyst_supplied_edit=True,rerouted_after_edit=False,automatic_successor=False)
    physics.nested(summary,expected)
    return dict(passes=True,groups=96,comparisons=24,controls=72,apparatus_gate_checks=18,copy_contrasts=24,
        transition_groups=72,independent_blocks=16,normalization=16,labelled_cells=12288,new_assays=new,
        bootstrap_seed=14920260919,bootstrap_draws=10000,primary_independently_reconstructed=True)
