"""Independent P31 state audit, exact archive replays and threshold diagnosis."""
import argparse,hashlib
from itertools import combinations
from pathlib import Path
import numpy as np
import p31_design as d
import analyze_p28 as p28
p27=p28.p27; p19=p27.p19; p21=p27.p21
Checks,labels,arrays,INDEX=p28.Checks,p28.labels,p28.arrays,p28.INDEX
Reader=p28.Reader
stock,incoming,new_id=p27.stock,p27.incoming,p27.new_id
window_routes,boundaries,first_challenge=p27.window_routes,p27.boundaries,p27.first_challenge

def prefix_spec(founder='written',source_fine=False,resolution=64):
    stage='prefix_replay' if resolution in (8,16) else 'prefix_refine'
    return dict(id='__'.join([stage,founder,'source_fine' if source_fine else 'source_coarse','r'+str(resolution)]),
        stage=stage,kind='prefix',founder=founder,fine=source_fine,source_fine=source_fine,resolution=resolution)
def spec(founder='written',condition='pause_15_100',source_fine=False,prefix_resolution=64,resolution=64):
    start,span={'baseline':(None,0),'pause_10_100':(10,100),'pause_15_100':(15,100),'pause_20_100':(20,100)}[condition]
    stage='replay' if prefix_resolution==resolution and resolution in (8,16) else 'refinement'
    return dict(id='__'.join([stage,founder,condition,'source_fine' if source_fine else 'source_coarse',
        'p'+str(prefix_resolution),'r'+str(resolution)]),stage=stage,founder=founder,condition=condition,
        panel='timing_grid',route='none',window='open' if start is None else condition,pause_start=start,pause_duration=span,
        draw='heldout_17021',replacements=5,readout='',fine=source_fine,source_fine=source_fine,resolution=resolution,
        kind='renewal',prefix_resolution=prefix_resolution)
def expected_stage(stage):
    histories=('written','ordinary'); schedules=('baseline','pause_10_100','pause_15_100','pause_20_100')
    if stage in ('prefix_replay','prefix_refine'):
        return [c for q in (8,16,32,64) for h in histories for f in (False,True) if (c:=prefix_spec(h,f,q))['stage']==stage]
    if stage=='replay':return [spec(h,k,f,q,q) for q in (8,16) for h in histories for k in schedules for f in (False,True)]
    if stage=='refinement':
        return ([spec(h,k,f,q,q) for q in (32,64) for h in histories for k in schedules for f in (False,True)]
            +[spec(h,'pause_15_100',f,p,q) for p,q in ((16,64),(32,64),(64,16),(64,32)) for h in histories for f in (False,True)])
    raise ValueError('Unknown P31 stage')
def expected_cases(last='refinement'):
    stages=('prefix_replay','prefix_refine','replay','refinement')
    return [c for stage in stages[:stages.index(last)+1] for c in expected_stage(stage)]
def prefix_source(c):return prefix_spec(c['founder'],c['source_fine'],c['prefix_resolution'])['id']
def p30_id(c,q):return 'renewal__'+c['founder']+'__'+c['condition']+'__heldout_17021__5__source_'+('fine' if c['fine'] else 'coarse')+'__q'+str(q)
def replay(c):
    if c['stage']=='prefix_replay':return 'p29/prefix_refine__'+c['founder']+'__source_'+('fine' if c['fine'] else 'coarse')+'__r'+str(c['resolution'])
    if c['stage']=='replay':return 'p30/'+p30_id(c,c['resolution'])
    return None
def anchor(c):
    if c['kind']=='renewal' and c['condition'] in ('baseline','pause_10_100','pause_20_100'):return 'p30/'+p30_id(c,16)
    return None

def founder_source(c): return 'p15/onward__'+c['founder']+'__actual__patch__open'+('__fine' if c['fine'] else '')

def stock_source(c): return 'p11/stock'+('__fine' if c['fine'] else '')

def prefix_incoming(M):
    word=int.from_bytes(hashlib.sha256(b'P16_turnover_limit_v1|501|turnover|0').digest()[:8],'big')
    value=M.copy(); value[7,0]=M[7,0]*(1+(word*51//2**64-25)/100); return value

def audit_prefix(rd,run,c):
    src=run/'inputs'/founder_source(c); record=d.read(src/'result.json'); old=record['phases'][-1]
    originals=['p15:%s:actual:patch:pupil:%02d'%(c['founder'],i) for i in range(3)]
    ids=originals.copy(); value=arrays(src,'isolated_2')['final'].copy(); before_labels=''.join(labels(value,INDEX))
    rd.ck('founder_lineage',old['phase']=='isolated_2' and old['logical_interval']==[1170000,1180000]
        and old['setup']['cell_ids']==originals and before_labels=='EEE')
    rd.ck('founder_hash',d.digest(src/'isolated_2.npz')==old['sha256'])
    _,M=stock(run,c['fine']); fresh=prefix_incoming(M); lab=str(labels(fresh,INDEX)[0]); rd.ck('incoming_M',lab=='M')
    ids[0]='p17:%s:100:open:replacement:0:0'%c['founder']; value[:,0:1]=fresh
    insert=dict(event=1,cycle=0,position=0,removed=originals[0],inserted=ids[0],initial_label=lab)
    rd.take(p19.descriptor('replacement_01',ids,1180000,100,'chain'),value)
    obs=p19.observation(rd.data['replacement_01'],range(3))
    expected=dict(founder_source=founder_source(c),stock_source=stock_source(c),
        founder_result_sha256=d.digest(src/'result.json'),founder_phase_sha256=d.digest(src/'isolated_2.npz'),
        stock_result_sha256=d.digest(run/'inputs'/stock_source(c)/'result.json'),
        stock_phase_sha256=d.digest(run/'inputs'/stock_source(c)/'preparation.npz'))
    rd.ck('prefix_provenance',rd.result['provenance']==expected)
    rd.ck('no_prefix_assembly',not (rd.folder/'assembly').exists())
    return dict(available=True,source_labels=before_labels,original_ids=originals,replacements=[insert],
        observations={'replacement_01':obs},fork_labels=obs['patch_labels'],focal_E_at_fork=obs['patch_labels'][0]=='E',logical_end=1180100)

def audit_assembly(rd,run,c):
    key=prefix_source(c); src=run/key; old=d.read(src/'result.json'); rec=old['phases'][0]
    before=arrays(src,'replacement_01')['final']; originals=['p15:%s:actual:patch:pupil:%02d'%(c['founder'],i) for i in range(3)]
    ids=['p17:%s:100:open:replacement:0:0'%c['founder']]+originals[1:]
    rd.ck('prefix_case',old['case']==prefix_spec(c['founder'],c['fine'],c['prefix_resolution']) and old['execution_pass'])
    rd.ck('prefix_identity_epoch',len(old['phases'])==1 and rec['phase']=='replacement_01'
        and rec['logical_interval']==[1180000,1180100] and rec['setup']['cell_ids']==ids and old['outcome']['original_ids']==originals)
    rd.ck('prefix_phase_hash',d.digest(src/'replacement_01.npz')==rec['sha256'])
    rows=[x for x in d.read(run/'summary.json')['cases'] if x['id']==key]
    rd.ck('actual_registered_prefix',len(rows)==1 and rows[0]['execution_pass'] and rows[0]['result']==old
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

def branch(folder,c,checks):
    rd=Reader(folder,c,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('source_factor',c['fine'] is c['source_fine'] and result['source_precision']==('fine' if c['fine'] else 'coarse'))
    rd.ck('resolution_factors',result['numerical_resolution']==c['resolution'] and result['prefix_resolution']==c.get('prefix_resolution',c['resolution']))
    rd.ck('clock',result['clock_method']=='native_explicit_euler_bounded_clock_v1' and result['clock_policy']=='independent_prefix_and_downstream_refinement_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve','independent_numerical_factors','numerical_parameters_refined','counterfactual_reconstruction')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('primary_state_edits_at_assembly','new_incoming_protein_draws','repeated_pause',
        'donors_clamped','readout_states_edited','autonomous_reproduction','cell_division_simulated','parameter_retuning',
        'independent_biological_replicates','outcome_dependent_selection','automatic_follow_on','original_P27_gate_changed','original_P30_gate_changed','new_onward_assays','full_historical_lineage_refined')))
    rd.ck('assembly_scope',result['algebraic_refresh_at_assembly'] is (c['kind']=='renewal') and result['segmented_first_challenge'] is (c['kind']=='renewal'))
    rd.ck('timing_scope',result['global_network_timing_intervention'] is (c['kind']=='renewal' and c['condition']!='baseline'))
    rd.ck('replay_provenance',result['historical_numeric_replay']==replay(c))
    rd.ck('anchor_provenance',result['historical_outcome_anchor']==anchor(c))
    out=(audit_prefix if c['kind']=='prefix' else audit_renewal)(rd,folder.parent,c)
    ref=replay(c)
    if ref:
        archived=d.read(folder.parent/'inputs'/ref/'result.json'); rd.ck('replay_outcome',out==archived['outcome'])
        for name,value in rd.data.items():
            old=arrays(folder.parent/'inputs'/ref,name); rd.ck(name+'/replay_inventory',set(value)==set(old))
            for key in old: rd.eq(name+'/historical_replay/'+key,value[key],old[key])
    return rd.finish(out)

def control_anchors(by,run,cases):
    rows=[]
    for c in cases:
        key=anchor(c)
        if key is None: continue
        old=d.read(run/'inputs'/key/'result.json')['outcome']; current=by.get(c['id'],{})
        keys=['retained_E','first_cell_sampled_behavior','first_cell_stable_E_after_second','complete_carrier_replacement']
        rows.append(dict(case=c,source=key,keys=keys,qualified=all(current.get(k)==old[k] for k in keys)))
    return rows

def shared_prefixes(run,cases,checks):
    rows=[]
    for left,right in combinations([c for c in cases if c['kind']=='renewal'],2):
        if not all(left[k]==right[k] for k in ('founder','source_fine','prefix_resolution','resolution')): continue
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

def prefix_pair(left,right,by,data):
    x,y=(data[c['id']]['replacement_01'] for c in (left,right))
    if not np.array_equal(x['times'],y['times']): raise ValueError('Prefix sampling changed')
    primary=list(range(8))+[16]; v,w=x['concentrations'][:,primary],y['concentrations'][:,primary]
    err=float(np.max(np.abs(v-w)/np.maximum(1,np.maximum(np.abs(v),np.abs(w)))))
    return dict(left=left['id'],right=right['id'],phase_inventory_agrees=set(data[left['id']])==set(data[right['id']]),
        outcomes_agree=by[left['id']]==by[right['id']],all_phase_labels_agree=bool(np.array_equal(labels(x['final'],INDEX),labels(y['final'],INDEX))),
        common_grid_diagnostics_agree=all(np.array_equal(labels(v,INDEX),labels(w,INDEX)) for v,w in zip(x['concentrations'],y['concentrations'])),
        max_primary_scaled_error=err)

def threshold_neighborhood(raw):
    # Native saved samples only, with the shared endpoint 175 included once.
    times=[]; mi=[]; zeb=[]; states=[]
    for name,start in (('challenge_15',150),('challenge_16',175)):
        x=raw[name]
        for t,value in zip(x['times'],x['concentrations']):
            at=float(start+t)
            if times and at==times[-1]:continue
            times.append(at); mi.append(float(value[5,2])); zeb.append(float(value[6,2])); states.append(str(labels(value,INDEX)[2]))
    if times!=[150+1.25*i for i in range(41)]:raise ValueError('Threshold diagnostic sample grid changed')
    delta=[m-z for m,z in zip(mi,zeb)]
    switches=[dict(from_label=states[i-1],to_label=states[i],bracket=[times[i-1],times[i]]) for i in range(1,41) if states[i]!=states[i-1]]
    at=times.index(175.)
    return dict(cell_column=2,times=times,miR200_total=mi,Zeb_mRNA_total=zeb,miR200_minus_Zeb=delta,
        E_margin=[x-2 for x in delta],labels=''.join(states),sampled_label_switches=switches,
        at_175=dict(label=states[at],miR200_minus_Zeb=delta[at],E_margin=delta[at]-2))
def pair(left,right,by,data):
    row=p28.pair(left,right,by,data)
    if left['condition']=='pause_15_100' or right['condition']=='pause_15_100':
        x,y=(threshold_neighborhood(data[c['id']]) for c in (left,right))
        row['target_neighborhood_labels_agree']=x['labels']==y['labels']
        row['target_neighborhood_switches_agree']=x['sampled_label_switches']==y['sampled_label_switches']
    return row

def acceptable(row):
    return bool(all(row[k] for k in ('phase_inventory_agrees','outcomes_agree','all_phase_labels_agree','common_grid_diagnostics_agree'))
        and row.get('target_neighborhood_labels_agree',True) and row.get('target_neighborhood_switches_agree',True)
        and row['max_primary_scaled_error']<=.01)
def contracted(previous,last):return bool(acceptable(last) and last['max_primary_scaled_error']<=previous['max_primary_scaled_error']+1e-12)

def baseline_report(by,data):
    rows=[]
    for h in ('written','ordinary'):
        for k in ('baseline','pause_10_100','pause_15_100','pause_20_100'):
            for f in (False,True):
                row=p28.pair(spec(h,k,f,8,8),spec(h,k,f,16,16),by,data)
                rows.append(dict(row,founder=h,condition=k,source_fine=f,qualified_under_P30_criteria=acceptable(row)))
    return rows

def convergence_report(by,data):
    adjacent=[]; prefixes=[]; upstream=[]; downstream=[]; joint=[]; sources=[]; prefix_sources=[]
    for h in ('written','ordinary'):
        for f in (False,True):
            rows=[prefix_pair(prefix_spec(h,f,x),prefix_spec(h,f,y),by,data) for x,y in ((8,16),(16,32),(32,64))]
            adjacent.extend(rows);prefixes.append(dict(founder=h,source_fine=f,previous=rows[-2],finest=rows[-1],converged=contracted(*rows[-2:])))
            for axis,target in (('upstream',upstream),('downstream',downstream)):
                cases=[spec(h,'pause_15_100',f,q,64) if axis=='upstream' else spec(h,'pause_15_100',f,64,q) for q in (16,32,64)]
                previous=pair(cases[0],cases[1],by,data);finest=pair(cases[1],cases[2],by,data)
                target.append(dict(founder=h,condition='pause_15_100',source_fine=f,axis=axis,previous=previous,finest=finest,converged=contracted(previous,finest)))
            for k in ('baseline','pause_10_100','pause_15_100','pause_20_100'):
                cases=[spec(h,k,f,q,q) for q in (16,32,64)]
                previous=pair(cases[0],cases[1],by,data);finest=pair(cases[1],cases[2],by,data)
                joint.append(dict(founder=h,condition=k,source_fine=f,axis='joint',previous=previous,finest=finest,converged=contracted(previous,finest)))
        row=prefix_pair(prefix_spec(h,False,64),prefix_spec(h,True,64),by,data)
        prefix_sources.append(dict(row,founder=h,source_robust=acceptable(row)))
        for k in ('baseline','pause_10_100','pause_15_100','pause_20_100'):
            row=pair(spec(h,k,False,64,64),spec(h,k,True,64,64),by,data)
            sources.append(dict(row,founder=h,condition=k,source_robust=acceptable(row)))
    converged=all(x['converged'] for x in prefixes+upstream+downstream+joint)
    robust=all(x['source_robust'] for x in prefix_sources+sources)
    diagnostics=[dict(case=c,**threshold_neighborhood(data[c['id']])) for c in expected_cases() if c['kind']=='renewal']
    return dict(prefix_adjacent_comparisons=adjacent,prefix_finest_comparisons=prefixes,
        upstream_finest_comparisons=upstream,downstream_finest_comparisons=downstream,joint_finest_comparisons=joint,
        prefix_source_comparisons=prefix_sources,source_precision_comparisons=sources,baseline_comparisons=baseline_report(by,data),
        threshold_diagnostics=diagnostics,all_finest_converged=converged,all_source_comparisons_agree=robust,
        focused_convergence_supported=bool(converged and robust),original_P27_quality_gate=False,original_P30_quality_gate=False,
        full_pause_panel_qualified=False,qualified_onward_transmission_established=False,full_historical_lineage_refined=False)

def predecessor_audit(run):
    evidence=d.completed_evidence();summary=d.read(run/'summary.json');integrity=d.integrity(run,summary)
    return dict(quality_gate=bool(evidence['diagnostic_archive_valid'] and all(integrity.values())),
        inherited=evidence,integrity=integrity,predecessor_repair_qualified=False,
        permits_diagnostic_study_only=True,historical_mathematical_audit_repeated=False)

def stage_audit(run,stage):
    summary=d.read(run/'summary.json'); checks=Checks(); cases=expected_cases(stage); records={r['id']:r for r in summary['cases']}
    branches=[]; by={}; data={}; calls=0
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and d.read(path)==row['result'])
        report,raw=branch(run/c['id'],c,checks); branches.append(report); by[c['id']]=report['outcome']; calls+=len(raw)
        data[c['id']]={name:{k:a[k] for k in ('times','concentrations','initial','final')} for name,a in raw.items()}
    count,wanted,controls={'prefix_replay':(8,8,0),'prefix_refine':(16,16,0),'replay':(48,848,24),'refinement':(96,2096,48)}[stage]
    checks.add('counts',len(branches)==count and calls==wanted)
    checks.add('unique_registered_records',len(records)==len(summary['cases']) and set(records).issubset({c['id'] for c in expected_cases()}) and {c['id'] for c in cases}.issubset(records))
    history=summary.get('predecessor_audit',{}); hp=run/'predecessor_audit.json'
    checks.add('diagnostic_history',summary['predecessor_gate'] and history.get('quality_gate') is True
        and history.get('predecessor_repair_qualified') is False and history==d.read(hp) and d.digest(hp)==summary['predecessor_audit_sha256'])
    anchors=control_anchors(by,run,cases); checks.add('anchors',len(anchors)==controls and all(x['qualified'] for x in anchors))
    prefixes=shared_prefixes(run,cases,checks) if len(branches)==count else []
    checks.add('prefix_count',len(prefixes)=={'prefix_replay':0,'prefix_refine':0,'replay':48,'refinement':96}[stage])
    baseline=baseline_report(by,data) if stage in ('replay','refinement') and len(branches)==count else []
    if baseline:
        failed={(x['founder'],x['condition'],x['source_fine']) for x in baseline if not x['qualified_under_P30_criteria']}
        checks.add('preserved_P30_failures',len(baseline)==16 and failed=={('written','pause_15_100',False),('written','pause_15_100',True),('ordinary','pause_15_100',True)})
    result=convergence_report(by,data) if stage=='refinement' and len(branches)==count else {}
    if result:
        checks.add('comparison_inventory',[len(result[k]) for k in ('prefix_adjacent_comparisons','prefix_finest_comparisons',
            'upstream_finest_comparisons','downstream_finest_comparisons','joint_finest_comparisons','prefix_source_comparisons','source_precision_comparisons','threshold_diagnostics')]==[12,4,4,4,16,2,8,80])
    integrity=d.integrity(run,summary)
    return dict(stage=stage,quality_gate=bool(all(checks.rows.values()) and all(integrity.values())),checks=checks.rows,integrity=integrity,
        branches=branches,integration_calls=calls,cumulative_cases=len(branches),anchor_controls=anchors,
        shared_schedule_prefix_comparisons=prefixes,baseline_comparisons=baseline,convergence=result,favorable_convergence_required_for_valid_diagnosis=False)

def analyze(run):
    summary=d.read(run/'summary.json'); checks=Checks(); reports={}
    checks.add('config',summary['config']==d.FIXED==d.read(run/'frozen/p31_delayed_pause_convergence/config.json'))
    checks.add('registration',summary['registered_cases']==expected_cases()); stages=summary['attempted_stages']
    checks.add('all_stages',stages==['prefix_replay','prefix_refine','replay','refinement'])
    history=predecessor_audit(run); checks.add('history',history['quality_gate'] and history==summary['predecessor_audit'])
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report
        # Later summaries contain later records; earlier saved reports audited the stage prefix only.
        checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==d.read(run/(stage+'_audit.json'))
            and d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    checks.add('all_cases',len(summary['cases'])==96 and {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases()})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary['all_execution_valid'] and summary['completion_reason']=='all_registered_stages_completed')
    integrity=d.integrity(run,summary); valid=bool(all(checks.rows.values()) and all(integrity.values()))
    final=reports.get('refinement',{}); result=final.get('convergence',{})
    return dict(run=str(run),quality_gate=valid,ready_for_interpretation=valid,checks=checks.rows,integrity=integrity,
        predecessor=history,stages=reports,completed_cases=len(summary['cases']),integration_calls=final.get('integration_calls',0),
        independent_check_count=len(checks.rows)+len(final.get('checks',{})),**result,
        focused_repair_qualified=bool(valid and result.get('focused_convergence_supported')),
        historical_mathematical_audit_repeated=False,scientific_scope='targeted_delayed_pause_numerical_diagnosis',automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);args=p.parse_args();run=args.run.absolute();d.check_run_path(run)
    report=analyze(run);d.write_json(run/'independent_audit.json',report)
    print({k:report.get(k) for k in ('quality_gate','completed_cases','integration_calls','independent_check_count','all_finest_converged','all_source_comparisons_agree','focused_repair_qualified')},flush=True)
    return 0 if report['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
