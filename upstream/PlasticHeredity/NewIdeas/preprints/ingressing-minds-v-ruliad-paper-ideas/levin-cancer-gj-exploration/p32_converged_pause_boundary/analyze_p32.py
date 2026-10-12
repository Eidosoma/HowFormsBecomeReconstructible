"""Independently reconstruct P32 lineages, full-grid comparisons and transmission."""
import argparse
from itertools import combinations
from pathlib import Path
import numpy as np
import p32_design as d
import analyze_p29 as p29
import analyze_p31 as p31
p27=p29.p27; p26=p27.p26; p22=p27.p22; p21=p27.p21; p19=p27.p19
Checks,labels,arrays,INDEX,Reader=p29.Checks,p29.labels,p29.arrays,p29.INDEX,p29.Reader
windows,boundaries=p27.windows,p27.boundaries
stock,incoming,new_id,pupils=p27.stock,p27.incoming,p27.new_id,p27.pupils
window_routes,first_challenge,reference_parent=p27.window_routes,p27.first_challenge,p27.reference_parent
expected_draws,canonical_binding=p27.expected_draws,p27.canonical_binding
STAGES=('controls','renewal','onward')

def spec(founder='written',condition='pause_0_100',draw='legacy',replacements=5,readout='',fine=False,resolution=64):
    c=p27.spec(founder,condition,draw,replacements,readout,fine)
    c.update(id=c['id'].removesuffix('__fine')+'__source_'+('fine' if fine else 'coarse')+'__q'+str(resolution),
        source_fine=fine,resolution=resolution,prefix_resolution=None if condition=='reference' else resolution,
        kind='readout' if readout else 'renewal')
    return c

def expected_stage(stage):
    if stage=='controls': return [spec(h,'reference',readout=q,fine=f,resolution=r) for r in (32,64) for f in (False,True) for h in ('written','ordinary') for q in ('open','rna','cut')]
    if stage=='renewal': return [spec(h,k,draw,fine=f,resolution=r) for r in (32,64) for f in (False,True) for h in ('written','ordinary') for k in windows() for draw in ('legacy','heldout_17021')]
    if stage=='onward': return [spec(c['founder'],c['condition'],c['draw'],5,q,c['fine'],c['resolution']) for c in expected_stage('renewal') for q in ('open','rna','cut')]
    raise ValueError('Unknown P32 stage')
def expected_cases(last='onward'): return [c for s in STAGES[:STAGES.index(last)+1] for c in expected_stage(s)]
def parent(c): return spec(c['founder'],c['condition'],c['draw'],5,fine=c['fine'],resolution=c['resolution'])
def prefix_source(c): return 'p31/prefix_refine__'+c['founder']+'__source_'+('fine' if c['fine'] else 'coarse')+'__r'+str(c['prefix_resolution'])
def replay(c):
    if c['stage']=='renewal' and c['draw']=='heldout_17021' and c['condition'] in ('baseline','pause_10_100','pause_15_100','pause_20_100'):
        return 'p31/refinement__'+c['founder']+'__'+c['condition']+'__source_'+('fine' if c['fine'] else 'coarse')+'__p'+str(c['resolution'])+'__r'+str(c['resolution'])
    return None
anchor=p27.anchor

def audit_assembly(rd,run,c):
    key=prefix_source(c); src=run/'inputs'/key; old=d.read(src/'result.json'); rec=old['phases'][0]
    before=arrays(src,'replacement_01')['final']; originals=['p15:%s:actual:patch:pupil:%02d'%(c['founder'],i) for i in range(3)]
    ids=['p17:%s:100:open:replacement:0:0'%c['founder']]+originals[1:]
    rd.ck('prefix_case',old['case']==p31.prefix_spec(c['founder'],c['fine'],c['prefix_resolution']) and old['execution_pass'])
    rd.ck('prefix_identity_epoch',len(old['phases'])==1 and rec['phase']=='replacement_01'
        and rec['logical_interval']==[1180000,1180100] and rec['setup']['cell_ids']==ids and old['outcome']['original_ids']==originals)
    rd.ck('prefix_phase_hash',d.digest(src/'replacement_01.npz')==rec['sha256'])
    rows=[x for x in d.read(run/'inputs/p31/summary.json')['cases'] if x['id']==key.removeprefix('p31/')]
    rd.ck('qualified_archived_prefix',len(rows)==1 and rows[0]['execution_pass'] and rows[0]['result']==old
        and rows[0]['result_sha256']==d.digest(src/'result.json'))
    expected=p27.canonical_binding(before); folder=rd.folder/'assembly'; saved=arrays(folder,'checkpoint'); meta=d.read(folder/'assembly.json')
    rd.ck('assembly_inventory',{p.name for p in folder.iterdir()}=={'checkpoint.npz','assembly.json'}
        and set(saved)=={'before','hybrid_before_refresh','assembled'})
    for name,value in (('before',before),('hybrid_before_refresh',before),('assembled',expected)): rd.eq('assembly/'+name,saved[name],value)
    rd.eq('refresh_preserves_primary',saved['assembled'][list(range(8))+[16]],before[list(range(8))+[16]])
    rd.eq('derived_not_independently_edited',saved['hybrid_before_refresh'][8:16],before[8:16])
    wanted=dict(source=key,source_result_sha256=d.digest(src/'result.json'),source_phase_sha256=d.digest(src/'replacement_01.npz'),
        source_epoch=1180100,common_logical_start=1180300,reanchor_without_integration=200,route='none',edited_primary_rows=[],
        edited_column=None,cell_ids=ids.copy(),original_ids=originals.copy(),algebraic_refresh=True,refresh_columns=[0,1,2],
        checkpoint_sha256=d.digest(folder/'checkpoint.npz'))
    rd.ck('assembly_metadata',meta==wanted)
    rd.ck('assembly_provenance',rd.result['provenance']['assembly']==wanted and rd.result['provenance']['assembly_metadata_sha256']==d.digest(folder/'assembly.json'))
    rd.ck('initial_EEE',''.join(labels(expected,INDEX))=='EEE')
    return expected,ids,originals

def audit_renewal(rd,run,c):
    value,ids,originals=audit_assembly(rd,run,c); initial=ids.copy(); lab=''.join(labels(value,INDEX))
    _,M=stock(run,c['fine']); observations={}; replacements=[]; cursor=1180300
    for event in range(1,c['replacements']+1):
        cycle,pos=divmod(event,3); x=incoming(M,c,event); incoming_label=str(labels(x,INDEX)[0]); rd.ck('incoming_%d_M'%event,incoming_label=='M')
        value=value.copy(); removed=ids[pos]; ids[pos]=new_id(c,cycle,pos); value[:,pos:pos+1]=x
        replacements.append(dict(event=event+1,cycle=cycle,position=pos,removed=removed,inserted=ids[pos],initial_label=incoming_label))
        name='replacement_%02d'%(event+1)
        if event==1:
            for number,route in enumerate(window_routes(c),1):
                horizon=boundaries()[number]-boundaries()[number-1]
                value=rd.take(p19.descriptor('challenge_%02d'%number,ids,cursor,horizon,'chain',route),value); cursor+=horizon
            first=first_challenge(rd.data,c); observations[name]=p19.observation(first,range(3))
        else:
            value=rd.take(p19.descriptor(name,ids,cursor,300,'chain'),value); cursor+=300
            observations[name]=p19.observation(rd.data[name],range(3))
    complete=not bool(set(ids)&set(originals+initial)); rd.ck('complete_carrier_replacement',complete)
    rd.ck('schedule',cursor==1180300+300*c['replacements'] and [x['position'] for x in replacements]==[i%3 for i in range(1,c['replacements']+1)])
    cursor=p19.holds(rd,ids,value,cursor,observations); diagnostic=p21.observed_behavior(first_challenge(rd.data,c))
    rd.ck('trajectory_diagnostics',rd.result['provenance']['trajectory_diagnostics']==diagnostic)
    rd.ck('provenance_inventory',set(rd.result['provenance'])=={'assembly','assembly_metadata_sha256','trajectory_diagnostics'})
    return dict(available=True,fork_ids=initial,original_ids=originals,assembly_labels=lab,observations=observations,
        replacements=replacements,retained_E=all(p19.masks(observations)),first_cell_label_after_second=observations['replacement_02']['patch_labels'][0],
        first_cell_stable_E_after_second=observations['replacement_02']['stable_E'][0],
        later_windows_E=all(all(v['stable_E']) for k,v in observations.items() if k.startswith('replacement')),
        complete_carrier_replacement=complete,logical_end=cursor,first_cell_sampled_behavior=diagnostic['sampled_behavior'],first_cell_M_observed=diagnostic['M_observed'])

def audit_readout(rd,run,c):
    ref=c['condition']=='reference'; key=reference_parent(c) if ref else parent(c)['id']
    path=run/'inputs'/key if ref else run/key; old=d.read(path/'result.json')
    par=p22.spec('replay',c['founder'],'newcomer_protein',fine=c['fine']) if ref else parent(c)
    ids=['p22:replay:'+c['founder']+':newcomer_protein:open:legacy:5:replacement:1:'+str(i) for i in range(3)] if ref else [new_id(c,(c['replacements']-2)//3,i) for i in range(3)]
    originals=['p15:%s:actual:patch:pupil:%02d'%(c['founder'],i) for i in range(3)]
    fork=['p17:%s:100:open:replacement:0:0'%c['founder']]+originals[1:]
    base=1200300+300*c['replacements']; parent_obs={}; value=None
    rd.ck('parent_case',old['case']==par and old['execution_pass'] is True)
    rd.ck('parent_lineage',old['outcome']['original_ids']==originals and old['outcome']['fork_ids']==fork and old['outcome']['complete_carrier_replacement'] is True)
    for i,rec in enumerate(old['phases'][-2:],1):
        name='isolated_'+str(i); data=arrays(path,name)
        rd.ck('parent_'+name+'_identity_clock',rec['phase']==name and rec['setup']['cell_ids']==ids and rec['logical_interval']==[base-20000+(i-1)*10000,base-20000+i*10000] and rec['requested_horizon']==10000)
        rd.ck('parent_'+name+'_hash',d.digest(path/(name+'.npz'))==rec['sha256'])
        rd.ck('parent_'+name+'_shape',data['initial'].shape==data['final'].shape==(17,3))
        if value is not None: rd.eq('parent_holds_continuous',data['initial'],value)
        value=data['final']; parent_obs[name]=p19.observation(data,range(3))
        rd.ck('parent_'+name+'_observation',parent_obs[name]==old['outcome']['observations'][name])
    retained=all(p19.masks(parent_obs)); rd.ck('parent_retention',old['outcome']['retained_E'] is retained and (not ref or retained))
    rd.ck('parent_clock',old['outcome']['logical_end']==base)
    rd.ck('parent_provenance',rd.result['provenance']==dict(actual_parent=key,parent_result_sha256=d.digest(path/'result.json'),parent_phase_sha256=d.digest(path/'isolated_2.npz')))
    rd.ck('no_readout_assembly',not (rd.folder/'assembly').exists())
    _,M=stock(run,c['fine']); fresh=pupils(c); recipients=np.repeat(M,3,axis=1)
    donor_initial=''.join(labels(value,INDEX)); recipient_initial=''.join(labels(recipients,INDEX))
    rd.ck('fresh_M',recipient_initial=='MMM'); rd.ck('fresh_identities',len(set(ids+fresh))==6 and not set(fresh)&set(originals+fork))
    value=rd.take(p19.descriptor('contact',ids+fresh,base,20000,'readout',c['readout']),np.concatenate((value,recipients),axis=1))
    obs={'contact':p19.observation(rd.data['contact'],range(3,6))}; donor_end=''.join(labels(value[:,:3],INDEX))
    cursor=p19.holds(rd,fresh,value[:,3:],base+20000,obs)
    return dict(available=True,parent_retained_E=retained,donor_initial_labels=donor_initial,recipient_initial_labels=recipient_initial,
        donor_end_labels=donor_end,observations=obs,contact_stable_E=all(obs['contact']['stable_E']),transmitted_E=all(p19.masks(obs)),logical_end=cursor)

def branch(folder,c,checks):
    rd=Reader(folder,c,checks); result=rd.result; renewal=not bool(c['readout'])
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('source_factor',c['fine'] is c['source_fine'] and result['source_precision']==('fine' if c['fine'] else 'coarse'))
    rd.ck('resolution_factors',result['numerical_resolution']==c['resolution'] and result['prefix_resolution']==c['prefix_resolution'])
    rd.ck('clock',result['clock_method']=='native_explicit_euler_bounded_clock_v1' and result['clock_policy']=='joint_preparation_downstream_refinement_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve','independent_source_and_solver_factors',
        'numerical_parameters_refined','counterfactual_reconstruction','fixed_onward_schedules')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('primary_state_edits_at_assembly','new_incoming_protein_draws','repeated_pause',
        'donors_clamped','readout_states_edited','autonomous_reproduction','cell_division_simulated','parameter_retuning',
        'independent_biological_replicates','outcome_dependent_selection','automatic_follow_on','original_P27_gate_changed','original_P30_gate_changed',
        'full_historical_lineage_refined','full_grid_contraction_claimed')))
    rd.ck('assembly_scope',result['algebraic_refresh_at_assembly'] is renewal and result['segmented_first_challenge'] is renewal)
    rd.ck('onward_scope',result['new_onward_assays'] is (c['stage']=='onward'))
    rd.ck('timing_scope',result['global_network_timing_intervention'] is (renewal and c['condition']!='baseline'))
    rd.ck('replay_provenance',result['historical_numeric_replay']==replay(c))
    rd.ck('anchor_provenance',result['historical_outcome_anchor']==anchor(c))
    out=(audit_renewal if renewal else audit_readout)(rd,folder.parent,c)
    ref=replay(c)
    if ref:
        archived=d.read(folder.parent/'inputs'/ref/'result.json'); rd.ck('replay_outcome',out==archived['outcome'])
        for name,value in rd.data.items():
            old=arrays(folder.parent/'inputs'/ref,name); rd.ck(name+'/replay_inventory',set(value)==set(old))
            for key in old: rd.eq(name+'/historical_replay/'+key,value[key],old[key])
    return rd.finish(out)

def reference_controls(by):
    rows=[]
    for c in expected_stage('controls'):
        out=by.get(c['id'],{}); good=out.get('available') is True and out.get('parent_retained_E') is True and out.get('transmitted_E') is (c['readout']=='open')
        rows.append(dict(case=c,qualified=bool(good)))
    return rows

def anchor_controls(by,run,stage):
    rows=[]
    for c in expected_cases(stage):
        key=anchor(c)
        if key is None: continue
        old=d.read(run/'inputs'/key/'result.json')['outcome']; out=by.get(c['id'],{})
        keys=('parent_retained_E','transmitted_E') if c['readout'] else ('retained_E','first_cell_sampled_behavior','first_cell_stable_E_after_second')
        same=out.get('available') is True and all(out.get(k)==old[k] for k in keys)
        rows.append(dict(case=c,source=key,outcome_keys=list(keys),archived={k:old[k] for k in keys},qualified=bool(same)))
    return rows

def shared_prefixes(run,cases,checks):
    rows=[]
    for left,right in combinations([c for c in cases if c['kind']=='renewal'],2):
        if not all(left[k]==right[k] for k in ('founder','draw','source_fine','prefix_resolution','resolution')): continue
        names=[]
        for i,(x,y) in enumerate(zip(window_routes(left),window_routes(right)),1):
            if x!=y: break
            names.append('challenge_%02d'%i)
        if not names: continue
        same=True
        for name in names:
            x,y=arrays(run/left['id'],name),arrays(run/right['id'],name)
            equal=set(x)==set(y) and all(np.array_equal(x[k],y[k]) for k in x)
            checks.add(left['id']+'/shared_prefix/'+right['id']+'/'+name,equal); same &= equal
        rows.append(dict(left=left['id'],right=right['id'],phases=names,exact_numeric_agreement=bool(same)))
    return rows

def pair(left,right,by,data):
    x,y=data[left['id']],data[right['id']]; phases={}; scaled=0.
    primary=list(range(8))+[16]
    for name in x:
        a,b=x[name],y[name]
        if name not in y: raise ValueError('Missing comparison phase')
        if not np.array_equal(a['times'],b['times']): raise ValueError('Comparison sampling changed')
        first,last=a['concentrations'][:,primary,:],b['concentrations'][:,primary,:]
        denom=np.maximum(1.,np.maximum(np.abs(first),np.abs(last)))
        error=float(np.max(np.abs(first-last)/denom)); scaled=max(scaled,error)
        phases[name]=dict(labels_agree=bool(np.array_equal(labels(a['final'],INDEX),labels(b['final'],INDEX))),
            max_primary_scaled_error=error,max_absolute_difference=float(np.max(np.abs(a['final']-b['final']))))
    common_left=None if left['readout'] else p21.observed_behavior(first_challenge(x,left))
    common_right=None if right['readout'] else p21.observed_behavior(first_challenge(y,right))
    result=dict(left=left['id'],right=right['id'],phase_inventory_agrees=set(x)==set(y),
        outcomes_agree=by[left['id']]==by[right['id']],
        all_phase_labels_agree=all(p['labels_agree'] for p in phases.values()),
        common_grid_diagnostics_agree=common_left==common_right,
        max_primary_scaled_error=scaled,phases=phases)
    if not left['readout'] and left['condition']=='pause_15_100':
        first,last=(p31.threshold_neighborhood(data[c['id']]) for c in (left,right))
        result.update(target_neighborhood_labels_agree=first['labels']==last['labels'],
            target_neighborhood_switches_agree=first['sampled_label_switches']==last['sampled_label_switches'])
    return result

def comparisons(cases,by,data,checks):
    numerical=[]; sources=[]; ids={c['id'] for c in cases}
    for c in cases:
        if c['resolution']==32:
            high=spec(c['founder'],c['condition'],c['draw'],5,c['readout'],c['fine'],64)
            if high['id'] not in ids: continue
            row=pair(c,high,by,data); row['agree']=p31.acceptable(row); numerical.append(row)
            checks.add(c['id']+'/numerical_agreement',row['agree'])
        if not c['fine'] and c['resolution']==64:
            fine=spec(c['founder'],c['condition'],c['draw'],5,c['readout'],True,64)
            if fine['id'] not in ids: continue
            row=pair(c,fine,by,data); row['agree']=p31.acceptable(row); sources.append(row)
            checks.add(c['id']+'/source_agreement',row['agree'])
    return numerical,sources

def predecessor_audit(run):
    evidence=d.completed_evidence(); integrity=d.integrity(run,d.read(run/'summary.json'))
    return dict(quality_gate=bool(evidence['p31_repair_qualified'] and all(integrity.values())),
        inherited=evidence,integrity=integrity,predecessor_repair_qualified=True,
        original_P27_quality_gate=False,original_P30_quality_gate=False,historical_mathematical_audit_repeated=False)

def stage_audit(run,stage):
    summary=d.read(run/'summary.json'); checks=Checks(); cases=expected_cases(stage); records={r['id']:r for r in summary['cases']}
    branches=[]; by={}; data={}; calls=0
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and d.read(path)==row['result'])
        report,raw=branch(run/c['id'],c,checks); branches.append(report); by[c['id']]=report['outcome']; calls+=len(raw)
        data[c['id']]={name:{k:x[k] for k in ('times','concentrations','initial','final')} for name,x in raw.items()}
    count,wanted,anchors_wanted,nums,srcs={'controls':(24,72,0,12,6),'renewal':(232,5480,80,116,58),'onward':(856,7352,320,428,214)}[stage]
    checks.add('counts',len(branches)==count and calls==wanted)
    checks.add('unique_registered_records',len(records)==len(summary['cases']) and set(records).issubset({c['id'] for c in expected_cases()}) and {c['id'] for c in cases}.issubset(records))
    history=summary.get('predecessor_audit',{}); hp=run/'predecessor_audit.json'
    checks.add('qualified_history',summary['predecessor_gate'] and history.get('quality_gate') is True
        and history.get('predecessor_repair_qualified') is True and history==d.read(hp) and d.digest(hp)==summary['predecessor_audit_sha256'])
    checks.add('draw_book',d.read(run/'frozen/p32_converged_pause_boundary/draws.json')==expected_draws())
    controls=reference_controls(by); checks.add('references',len(controls)==24 and all(x['qualified'] for x in controls))
    anchors=anchor_controls(by,run,stage); checks.add('anchors',len(anchors)==anchors_wanted and all(x['qualified'] for x in anchors))
    complete=len(branches)==count
    prefixes=shared_prefixes(run,cases,checks) if complete and stage!='controls' else []
    checks.add('prefix_count',len(prefixes)==(0 if stage=='controls' else 576))
    numerical,sources=comparisons(cases,by,data,checks) if complete else ([],[])
    checks.add('comparison_counts',len(numerical)==nums and len(sources)==srcs)
    checks.add('replay_count',sum(replay(c) is not None for c in cases)==(0 if stage=='controls' else 32))
    threshold=[dict(case=c,**p31.threshold_neighborhood(data[c['id']])) for c in cases if c['stage']=='renewal' and c['condition']=='pause_15_100'] if complete else []
    checks.add('threshold_diagnostic_count',len(threshold)==(0 if stage=='controls' else 16))
    integrity=d.integrity(run,summary)
    return dict(stage=stage,quality_gate=bool(all(checks.rows.values()) and all(integrity.values())),checks=checks.rows,integrity=integrity,
        branches=branches,integration_calls=calls,cumulative_cases=len(branches),reference_controls=controls,anchor_controls=anchors,
        shared_schedule_prefix_comparisons=prefixes,numerical_comparisons=numerical,source_comparisons=sources,threshold_diagnostics=threshold,
        favorable_novel_outcomes_required=False)

def contrasts(by,inherited,controls_qualified):
    capacity=inherited.get('inherited_readout_capacity_qualified') is True; wipe=inherited.get('inherited_wipe_qualified') is True
    def outcomes(c,readout=''):
        return [by.get(spec(c['founder'],c['condition'],c['draw'],5,readout,f,q)['id'],{}) for f in (False,True) for q in (32,64)]
    def both(c,key,value=True,readout=''):
        return all(x.get('available') is True and x.get(key) is value for x in outcomes(c,readout))
    grid=[]; index={}
    for c in expected_stage('renewal'):
        if c['fine'] or c['resolution']!=64: continue
        retained=both(c,'retained_E')
        reads={q:True if both(c,'transmitted_E',True,q) else False if both(c,'transmitted_E',False,q) else None for q in ('open','rna','cut')}
        old=outcomes(c); behavior=old[0].get('first_cell_sampled_behavior') if all(x.get('available') and x.get('first_cell_sampled_behavior')==old[0].get('first_cell_sampled_behavior') for x in old) else 'missing_or_disagree'
        qualified=retained and reads['open'] is True and reads['rna'] is False and reads['cut'] is False and controls_qualified and capacity and wipe
        row=dict(founder=c['founder'],condition=c['condition'],draw=c['draw'],replacements=5,total_cycles=2,
            pause_start=c['pause_start'],pause_duration=c['pause_duration'],retained_E_all_variants=retained,
            retained_E_false_all_variants=both(c,'retained_E',False),readout_transmission_all_variants=reads,
            first_cell_sampled_behavior_all_variants=behavior,later_windows_E_all_variants=both(c,'later_windows_E'),
            complete_carrier_replacement_all_variants=both(c,'complete_carrier_replacement'),qualified_chain=bool(qualified))
        grid.append(row); index[(c['founder'],c['draw'],c['condition'])]=row
    for row in grid:
        baseline=index[(row['founder'],row['draw'],'baseline')]
        negative=baseline['retained_E_false_all_variants'] and all(x is False for x in baseline['readout_transmission_all_variants'].values())
        row['matched_baseline_negative']=negative
        row['pause_specific_chain']=bool(row['pause_duration']>0 and row['qualified_chain'] and negative)
    boundaries=[]
    for h in ('written','ordinary'):
        for draw in ('legacy','heldout_17021'):
            duration=[dict(duration=t,qualified=index[(h,draw,'pause_0_'+str(t))]['pause_specific_chain']) for t in (5,10,15,20,25)]
            delayed=[dict(start=t,qualified=index[(h,draw,'pause_'+str(t)+'_100')]['pause_specific_chain']) for t in (0,5,10,15,20,25)]
            good_duration=[x['duration'] for x in duration if x['qualified']]; good_start=[x['start'] for x in delayed if x['qualified']]
            ds=[x['qualified'] for x in duration]; ts=[x['qualified'] for x in delayed]
            boundaries.append(dict(founder=h,draw=draw,duration_pattern=duration,delayed_start_pattern=delayed,
                smallest_tested_successful_duration=min(good_duration) if good_duration else None,
                latest_tested_successful_start_for_duration_100=max(good_start) if good_start else None,
                duration_monotone_on_tested_grid=ds==sorted(ds),delay_monotone_on_tested_grid=ts==sorted(ts,reverse=True)))
    across=[dict(condition=k,pause_start=v[0],pause_duration=v[1],
        qualified_across_all_backgrounds=all(index[(h,draw,k)]['pause_specific_chain'] for h in ('written','ordinary') for draw in ('legacy','heldout_17021')))
        for k,v in windows().items() if k!='baseline']
    return dict(inherited_readout_capacity_qualified=capacity,inherited_wipe_qualified=wipe,timing_grid=grid,
        tested_boundaries=boundaries,across_backgrounds=across,exact_threshold_claimed=False,monotonicity_assumed=False)

def analyze(run):
    summary=d.read(run/'summary.json'); checks=Checks(); reports={}
    checks.add('config',summary['config']==d.FIXED==d.read(run/'frozen/p32_converged_pause_boundary/config.json'))
    checks.add('registration',summary['registered_cases']==expected_cases()); stages=summary['attempted_stages']
    checks.add('all_stages',stages==list(STAGES)); history=predecessor_audit(run)
    checks.add('history',history['quality_gate'] and history==summary['predecessor_audit'])
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report
        checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==d.read(run/(stage+'_audit.json')) and d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    checks.add('all_cases',len(summary['cases'])==856 and {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases()})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary['all_execution_valid'] and summary['completion_reason']=='all_registered_stages_completed')
    integrity=d.integrity(run,summary); quality=bool(all(checks.rows.values()) and all(integrity.values()))
    final=reports.get('onward',{}); by={b['case']['id']:b['outcome'] for b in final.get('branches',[])}
    inherited=d.read(run/'inputs/p26/independent_audit.json')
    controls_ok=quality and all(x['qualified'] for x in final.get('reference_controls',[])+final.get('anchor_controls',[]))
    return dict(run=str(run),quality_gate=quality,ready_for_interpretation=quality,checks=checks.rows,integrity=integrity,
        predecessor=history,stages=reports,completed_cases=len(summary['cases']),integration_calls=final.get('integration_calls',0),
        independent_check_count=len(checks.rows)+len(final.get('checks',{})),
        numerical_comparisons=final.get('numerical_comparisons',[]),source_comparisons=final.get('source_comparisons',[]),
        all_numerical_agree=len(final.get('numerical_comparisons',[]))==428 and all(x['agree'] for x in final.get('numerical_comparisons',[])),
        all_source_comparisons_agree=len(final.get('source_comparisons',[]))==214 and all(x['agree'] for x in final.get('source_comparisons',[])),
        shared_schedule_prefix_comparisons=final.get('shared_schedule_prefix_comparisons',[]),
        threshold_diagnostics=final.get('threshold_diagnostics',[]),
        **contrasts(by,inherited,controls_ok),original_P27_quality_gate=False,original_P30_quality_gate=False,
        full_grid_contraction_claimed=False,full_historical_lineage_refined=False,
        historical_mathematical_audit_repeated=False,scientific_scope='converged_full_short_pause_boundary_and_onward_transmission',
        autonomous_reproduction=False,independent_biological_replicates=False,automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);args=p.parse_args();run=args.run.absolute();d.check_run_path(run)
    report=analyze(run);d.write_json(run/'independent_audit.json',report)
    print({k:report.get(k) for k in ('quality_gate','completed_cases','integration_calls','independent_check_count','all_numerical_agree','all_source_comparisons_agree','tested_boundaries')},flush=True)
    return 0 if report['quality_gate'] else 1
if __name__=='__main__':raise SystemExit(main())
