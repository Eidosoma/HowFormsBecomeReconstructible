"""Independent P25 reconstruction and verified reuse of completed prior audits."""
import argparse
import hashlib
from pathlib import Path
import numpy as np
import p25_design as d
import analyze_p24 as p24

p22=p24.p22; p21=p22.p21; p19=p22.p19
Checks,labels,arrays,INDEX=p19.Checks,p19.labels,p19.arrays,p19.INDEX
STAGES=('controls','renewal','onward')

def spec(founder='written',condition='neighbour_rna',draw='legacy',replacements=5,readout='',fine=False):
    stage='controls' if condition=='reference' else 'onward' if readout else 'renewal'
    name='__'.join([stage,founder,condition,draw,str(replacements)]+([readout] if readout else []))+('__fine' if fine else '')
    return dict(id=name,stage=stage,founder=founder,condition=condition,panel='reference' if condition=='reference' else 'swaps',
        route='newcomer_protein' if condition=='reference' else condition,window='open',draw=draw,replacements=replacements,readout=readout,fine=fine)
def expected_stage(stage):
    if stage=='controls': return [spec(h,'reference',readout=q,fine=f) for f in (False,True) for h in ('written','ordinary') for q in ('open','rna','cut')]
    if stage=='renewal': return [spec(h,k,draw,n,fine=f) for f in (False,True) for h in ('written','ordinary') for k in ('neighbour_rna','newcomer_protein') for draw in ('legacy','heldout_17021','heldout_17022','legacy_first_17021','legacy_first_17022','heldout_17021_first_legacy','heldout_17022_first_legacy') for n in (5,11)]
    if stage=='onward': return [spec(c['founder'],c['condition'],c['draw'],c['replacements'],q,c['fine']) for c in expected_stage('renewal') for q in ('open','rna','cut')]
    raise ValueError('Unknown P25 stage')
def expected_cases(last='onward'): return [c for s in STAGES[:STAGES.index(last)+1] for c in expected_stage(s)]
def parent(c): return spec(c['founder'],c['condition'],c['draw'],c['replacements'],fine=c['fine'])
def stem(c): return 'p25:%s:%s:%s:%d'%(c['founder'],c['condition'],c['draw'],c['replacements'])
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:0'+str(i) for i in range(3)]
def source(c): return 'p24/inputs/p23/inputs/p22/inputs/p21/controls__'+c['founder']+'__component__none__0'+('__fine' if c['fine'] else '')
def reference_parent(c): return 'p24/inputs/p23/inputs/p22/replay__'+c['founder']+'__newcomer_protein__open__legacy__5'+('__fine' if c['fine'] else '')
def replay(c):
    suffix='__fine' if c['fine'] else ''
    if c['condition']=='reference': return dict(source='p24/controls__'+c['founder']+'__reference__legacy__5__'+c['readout']+suffix,phases=['contact','isolated_1','isolated_2'])
    if c['draw'] not in ('legacy','heldout_17021','heldout_17022'): return None
    panel='replay' if c['draw']=='legacy' and c['replacements']==5 else 'robust'
    parts=(['onward',panel] if c['readout'] else [panel])+[c['founder'],c['route'],'open',c['draw'],str(c['replacements'])]+([c['readout']] if c['readout'] else [])
    names=['contact','isolated_1','isolated_2'] if c['readout'] else ['replacement_%02d'%i for i in range(2,c['replacements']+2)]+['isolated_1','isolated_2']
    return dict(source='p24/inputs/p23/inputs/p22/'+'__'.join(parts)+suffix,phases=names)
def expected_word(draw,event):
    sources={'legacy':('legacy','legacy'),'heldout_17021':('heldout_17021','heldout_17021'),
        'heldout_17022':('heldout_17022','heldout_17022'),'legacy_first_17021':('heldout_17021','legacy'),
        'legacy_first_17022':('heldout_17022','legacy'),'heldout_17021_first_legacy':('legacy','heldout_17021'),
        'heldout_17022_first_legacy':('legacy','heldout_17022')}
    if draw not in sources or not 1<=event<=11: raise ValueError('Unregistered draw/event')
    source=sources[draw][0 if event==1 else 1]
    namespace,seed={'legacy':('P16_turnover_limit_v1',501),'heldout_17021':('P22_incoming_v1',17021),'heldout_17022':('P22_incoming_v1',17022)}[source]
    return int.from_bytes(hashlib.sha256(f'{namespace}|{seed}|turnover|{event}'.encode('ascii')).digest()[:8],byteorder='big')
def expected_draws(): return {k:['%016x'%expected_word(k,i) for i in range(1,12)] for k in ('legacy','heldout_17021','heldout_17022','legacy_first_17021','legacy_first_17022','heldout_17021_first_legacy','heldout_17022_first_legacy')}
def incoming(M,c,event):
    result=M.copy(); pct=(expected_word(c['draw'],event)*51)//(1<<64)-25
    result[7,0]=M[7,0]*(1+pct/100); return result
def stock(run,fine): return p24.stock(run/'inputs/p24',fine)
canonical_binding=p22.canonical_binding
first_challenge=p22.first_challenge

class Reader(p19.Reader):
    def __init__(self,folder,c,checks):
        self.folder,self.c,self.checks=folder,c,checks; self.result=d.read(folder/'result.json')
        self.records=self.result['phases']; self.at=0; self.data={}
        self.environment=arrays(p19.stock_folder(folder.parent/'inputs/p24/inputs/p23/inputs/p22/inputs/p21/inputs/p20/inputs/p19',c['fine']),'preparation')['environment']

def audit_assembly(rd,run,c):
    src=run/'inputs'/source(c); old=d.read(src/'result.json'); source_meta=d.read(src/'assembly/assembly.json')
    checkpoint=arrays(src/'assembly','checkpoint'); before,after=checkpoint['before'],checkpoint['after']
    rd.ck('source_case',old['case']==p21.spec(founder=c['founder'],target='none',mask=0,fine=c['fine']))
    originals=['p15:%s:actual:patch:pupil:%02d'%(c['founder'],i) for i in range(3)]
    ids=['p17:%s:100:open:replacement:0:0'%c['founder']]+originals[1:]
    rd.ck('source_identity',source_meta['cell_ids']==ids and old['outcome']['original_ids']==originals)
    rd.ck('source_epoch',source_meta['common_logical_start']==1180300)
    rd.ck('source_archive',source_meta==old['provenance']['assembly'] and
        d.digest(src/'assembly/assembly.json')==old['provenance']['assembly_metadata_sha256'] and
        d.digest(src/'assembly/checkpoint.npz')==source_meta['checkpoint_sha256'])
    rd.ck('source_shape',before.shape==after.shape==(17,3))
    rd.ck('fixed_inputs',np.all(before[4]==72) and np.all(after[4]==72) and not before[16].any() and not after[16].any())
    pos=0 if c['route'].startswith('newcomer_') else 2 if c['route'].startswith('neighbour_') else None
    suffix=c['route'].split('_')[-1]; rows={'none':[],'protein':[7],'rna':[5,6],'mir200':[5],'zebmrna':[6]}[suffix]
    hybrid=before.copy()
    for row in rows: hybrid[row,pos]=after[row,pos]
    expected=canonical_binding(hybrid); folder=rd.folder/'assembly'; saved=arrays(folder,'checkpoint'); meta=d.read(folder/'assembly.json')
    rd.ck('assembly_inventory',{p.name for p in folder.iterdir()}=={'checkpoint.npz','assembly.json'} and set(saved)=={'before','after','hybrid_before_refresh','assembled'})
    for name,value in (('before',before),('after',after),('hybrid_before_refresh',hybrid),('assembled',expected)): rd.eq('assembly/'+name,saved[name],value)
    rd.eq('refresh_preserves_primary',saved['assembled'][list(range(8))+[16]],hybrid[list(range(8))+[16]])
    rd.eq('derived_not_independently_edited',saved['hybrid_before_refresh'][8:16],before[8:16])
    rd.eq('discarded_column_before',saved['hybrid_before_refresh'][:,1],before[:,1])
    for j in range(3):
        for row in list(range(8))+[16]:
            if j!=pos or row not in rows: rd.ck('untouched_%d_%d'%(row,j),saved['hybrid_before_refresh'][row,j]==before[row,j])
    expected_meta=dict(source=source(c),source_result_sha256=d.digest(src/'result.json'),
        source_checkpoint_sha256=d.digest(src/'assembly/checkpoint.npz'),source_metadata_sha256=d.digest(src/'assembly/assembly.json'),
        route=c['route'],edited_primary_rows=rows,edited_column=pos,cell_ids=ids.copy(),original_ids=originals.copy(),
        common_logical_start=1180300,algebraic_refresh=True,refresh_columns=[0,1,2],checkpoint_sha256=d.digest(folder/'checkpoint.npz'))
    rd.ck('assembly_metadata',meta==expected_meta)
    rd.ck('assembly_provenance',rd.result['provenance']['assembly']==expected_meta and
        rd.result['provenance']['assembly_metadata_sha256']==d.digest(folder/'assembly.json'))
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
    rd.ck('clock',result.get('clock_method')=='native_explicit_euler_bounded_clock_v1' and result.get('clock_policy')=='phase_scaled_sampling_and_step_cap_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve','counterfactual_reconstruction','fixed_onward_schedules')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('new_random_draws','repeated_preparation','repeated_pause','donors_clamped','readout_states_edited',
        'autonomous_reproduction','cell_division_simulated','parameter_retuning','independent_biological_replicates','outcome_dependent_selection','automatic_follow_on')))
    rd.ck('refresh_scope',result.get('algebraic_refresh_at_assembly') is renewal)
    rd.ck('primary_edit_scope',result.get('primary_state_edits_at_assembly') is renewal)
    rd.ck('segmentation_scope',result.get('segmented_first_challenge') is False)
    rd.ck('timing_scope',result.get('global_network_timing_intervention') is False)
    rd.ck('draw_scope',result.get('first_draw_swap') is (renewal and c['draw'] not in ('legacy','heldout_17021','heldout_17022')))
    out=(audit_renewal if renewal else audit_readout)(rd,folder.parent,c)
    ref=replay(c); rd.ck('replay_provenance',result.get('historical_numeric_replay')==ref)
    if ref:
        for name in ref['phases']:
            data=rd.data[name]; historical=arrays(folder.parent/'inputs'/ref['source'],name)
            rd.ck(name+'/replay_inventory',set(data)==set(historical))
            for key in historical: rd.eq(name+'/historical_replay/'+key,data[key],historical[key])
    return rd.finish(out)

def reference_controls(by):
    rows=[]
    for c in expected_stage('controls'):
        out=by.get(c['id'],{}); good=out.get('available') is True and out.get('parent_retained_E') is True and out.get('transmitted_E') is (c['readout']=='open')
        rows.append(dict(case=c,qualified=bool(good)))
    return rows
def legacy_controls(by):
    rows=[]
    for c in expected_stage('renewal'):
        if c['draw'] in ('legacy','heldout_17021','heldout_17022'):
            out=by.get(c['id'],{}); good=out.get('available') is True and out.get('retained_E') is (c['condition']=='newcomer_protein' or c['draw']=='legacy')
            rows.append(dict(case=c,qualified=bool(good)))
    return rows
def prefix_comparisons(data,checks):
    rows=[]; phases=['replacement_%02d'%i for i in range(2,7)]
    for c in expected_stage('renewal'):
        if c['replacements']!=11: continue
        short=spec(c['founder'],c['condition'],c['draw'],5,fine=c['fine']); matches=[]
        for name in phases:
            left=data[short['id']][name]; right=data[c['id']][name]
            same=set(left)==set(right); checks.add(c['id']+'/prefix/'+name+'/inventory',same); matches.append(same)
            for key in left:
                equal=key in right and np.array_equal(left[key],right[key]); matches.append(equal)
                checks.add(c['id']+'/prefix/'+name+'/'+key,equal)
        rows.append(dict(short=short['id'],long=c['id'],phases=phases,exact_numeric_agreement=all(matches)))
    return rows

def first_challenge_comparisons(data,checks):
    rows=[]
    for c in expected_stage('renewal'):
        if c['draw']!='legacy': continue
        for partner in ('17021','17022'):
            for left_draw,right_draw in (('legacy','heldout_'+partner+'_first_legacy'),('heldout_'+partner,'legacy_first_'+partner)):
                left_case=spec(c['founder'],c['condition'],left_draw,c['replacements'],fine=c['fine'])
                right_case=spec(c['founder'],c['condition'],right_draw,c['replacements'],fine=c['fine'])
                left=data[left_case['id']]['replacement_02']; right=data[right_case['id']]['replacement_02']; matches=[set(left)==set(right)]
                prefix=left_case['id']+'/same_first/'+right_draw
                checks.add(prefix+'/inventory',matches[0])
                for key in left:
                    equal=key in right and np.array_equal(left[key],right[key]); matches.append(equal); checks.add(prefix+'/'+key,equal)
                rows.append(dict(left=left_case['id'],right=right_case['id'],phase='replacement_02',exact_numeric_agreement=all(matches)))
    return rows

def stage_audit(run,stage):
    summary=d.read(run/'summary.json'); checks=Checks(); cases=expected_cases(stage); records={r['id']:r for r in summary['cases']}
    branches=[]; by={}; endpoints={}; calls=0
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'; value=d.read(path)
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and value==row['result'])
        report,data=branch(run/c['id'],c,checks); branches.append(report); by[c['id']]=report['outcome']; endpoints[c['id']]=data; calls+=len(data)
    fine=p19.p18.p12.compare_fine(cases,by,endpoints,checks); history=summary.get('predecessor_audit',{})
    checks.add('history_checked',summary.get('predecessor_gate') is True and history.get('quality_gate') is True and history.get('historical_mathematical_audit_repeated') is False)
    checks.add('history_saved',history==d.read(run/'predecessor_audit.json') and d.digest(run/'predecessor_audit.json')==summary.get('predecessor_audit_sha256'))
    n,k={'controls':(12,36),'renewal':(124,1156),'onward':(460,2164)}[stage]
    checks.add('counts',len(branches)==n and calls==k); checks.add('unique_records',len(records)==len(summary['cases']))
    checks.add('registered_records',set(records).issubset({c['id'] for c in expected_cases()}))
    checks.add('draw_book',d.read(run/'frozen/p25_neighbour_first_draw/draws.json')==expected_draws())
    controls=reference_controls(by); checks.add('reference_controls_qualified',all(x['qualified'] for x in controls))
    legacy=legacy_controls(by) if stage!='controls' else []
    prefixes=prefix_comparisons(endpoints,checks) if stage!='controls' and len(branches)==n else []
    first_pairs=first_challenge_comparisons(endpoints,checks) if stage!='controls' and len(branches)==n else []
    checks.add('first_challenge_pair_count',len(first_pairs)==(0 if stage=='controls' else 64))
    checks.add('legacy_controls_qualified',all(x['qualified'] for x in legacy))
    checks.add('prefix_count',len(prefixes)==(0 if stage=='controls' else 56))
    integrity=d.integrity(run,summary)
    return dict(stage=stage,quality_gate=bool(all(checks.rows.values()) and all(integrity.values())),checks=checks.rows,integrity=integrity,
        branches=branches,fine_comparisons=fine,integration_calls=calls,cumulative_cases=len(branches),reference_controls=controls,
        legacy_controls=legacy,length_prefix_comparisons=prefixes,first_challenge_comparisons=first_pairs,favorable_novel_outcomes_required=False)

def predecessor_audit(run):
    saved=d.read(run/'inputs/p24/independent_audit.json'); old=d.read(run/'inputs/p24/summary.json'); status=d.read(run/'inputs/p24_job/status.json')
    pins=all(d.digest(run/'inputs/p24'/n)==h for n,h in d.PINS.items()) and d.digest(run/'inputs/p24_job/status.json')==d.STATUS_PIN
    stages=all(d.read(run/'inputs/p24'/(s+'_audit.json'))==old['gates'][s]==saved['stages'][s] and d.digest(run/'inputs/p24'/(s+'_audit.json'))==old['gate_hashes'][s] and saved['stages'][s]['quality_gate'] and all(saved['stages'][s]['checks'].values()) for s in ('controls','renewal','onward'))
    qualified=saved['quality_gate'] and saved['ready_for_interpretation'] and all(saved['checks'].values()) and all(saved['integrity'].values()) and saved['all_fine_agree'] and len(saved['fine_comparisons'])==134 and all(x['agree'] for x in saved['fine_comparisons'])
    qualified=qualified and saved['independent_check_count']==114346 and saved['completed_cases']==268 and saved['integration_calls']==1380 and old['registered_cases']==p24.expected_cases() and old['all_execution_valid'] and status['phase']=='complete' and status['exit_code']==0
    archive=all(d.integrity(run,d.read(run/'summary.json')).values())
    return dict(quality_gate=bool(pins and stages and qualified and archive),policy='pinned_completed_evidence_and_all_input_hashes_v1',
        pinned_reports_match=pins,saved_stage_reports_match=stages,saved_report_qualified=bool(qualified),archive_byte_identical=archive,
        prior_checks=saved['independent_check_count'],prior_cases=saved['completed_cases'],prior_calls=saved['integration_calls'],
        historical_mathematical_audit_repeated=False,reference_is_independent_backup=False,historical_files_rewritten=False)

def contrasts(by,inherited,controls_qualified):
    capacity=inherited.get('inherited_readout_capacity_qualified') is True; wipe=inherited.get('inherited_wipe_qualified') is True
    def outcomes(c,readout=''):
        return [by.get(spec(c['founder'],c['condition'],c['draw'],c['replacements'],readout,f)['id'],{}) for f in (False,True)]
    def both(c,key,value=True,readout=''):
        return all(x.get('available') is True and (x.get(key) is value if isinstance(value,bool) else x.get(key)==value) for x in outcomes(c,readout))
    grid=[]; indexed={}
    for c in expected_stage('renewal'):
        if c['fine']: continue
        retained=both(c,'retained_E'); reads={q:True if both(c,'transmitted_E',True,q) else False if both(c,'transmitted_E',False,q) else None for q in ('open','rna','cut')}
        parents=outcomes(c); behavior=parents[0].get('first_cell_sampled_behavior') if parents[0].get('available') and parents[1].get('available') and parents[0].get('first_cell_sampled_behavior')==parents[1].get('first_cell_sampled_behavior') else 'missing_or_disagree'
        qualified=retained and reads['open'] is True and reads['rna'] is False and reads['cut'] is False and controls_qualified and capacity and wipe
        row=dict(founder=c['founder'],condition=c['condition'],draw=c['draw'],replacements=c['replacements'],total_cycles=(c['replacements']+1)//3,
            retained_E_both=retained,retained_E_false_both=both(c,'retained_E',False),readout_transmission_both=reads,
            first_cell_sampled_behavior_both=behavior,first_cell_E_by_300_both=both(c,'first_cell_label_after_second','E'),
            first_cell_non_E_by_300_both=all(x.get('available') is True and x.get('first_cell_label_after_second') in ('M','X') for x in parents),
            first_cell_stable_E_after_second_both=both(c,'first_cell_stable_E_after_second'),later_windows_E_both=both(c,'later_windows_E'),
            complete_carrier_replacement_both=both(c,'complete_carrier_replacement'),qualified_chain=bool(qualified))
        row['negative_retention_and_readouts']=row['retained_E_false_both'] and all(v is False for v in reads.values())
        grid.append(row); indexed[c['founder'],c['condition'],c['draw'],c['replacements']]=row
    comparisons=[]
    for h in ('written','ordinary'):
        for condition in ('neighbour_rna','newcomer_protein'):
            for partner in ('17021','17022'):
                for n in (5,11):
                    keys=['legacy','heldout_'+partner,'legacy_first_'+partner,'heldout_'+partner+'_first_legacy']
                    historical,heldout,high_first,low_first=[indexed[h,condition,key,n] for key in keys]
                    disrupted=historical['retained_E_both'] and high_first['retained_E_false_both']
                    rescued=heldout['retained_E_false_both'] and low_first['retained_E_both']
                    chain_switch=historical['qualified_chain'] and heldout['negative_retention_and_readouts'] and high_first['negative_retention_and_readouts'] and low_first['qualified_chain']
                    first_switch=historical['first_cell_E_by_300_both'] and heldout['first_cell_non_E_by_300_both'] and high_first['first_cell_non_E_by_300_both'] and low_first['first_cell_E_by_300_both']
                    comparisons.append(dict(founder=h,condition=condition,partner='heldout_'+partner,replacements=n,profiles=keys,
                        higher_first_disrupts_retention=bool(disrupted),historical_first_rescues_retention=bool(rescued),
                        retention_reciprocal_switch=bool(disrupted and rescued),qualified_reciprocal_switch=bool(chain_switch),
                        first_challenge_E_switch=bool(first_switch),all_four_chains_qualified=all(indexed[h,condition,key,n]['qualified_chain'] for key in keys)))
    histories=[]
    for h in ('written','ordinary'):
        neighbour=[x for x in comparisons if x['founder']==h and x['condition']=='neighbour_rna']
        newcomer=[x for x in grid if x['founder']==h and x['condition']=='newcomer_protein']
        histories.append(dict(founder=h,all_neighbour_reciprocal_switches=all(x['qualified_reciprocal_switch'] for x in neighbour),
            all_neighbour_first_challenge_switches=all(x['first_challenge_E_switch'] for x in neighbour),
            newcomer_all_sequences_qualified=all(x['qualified_chain'] for x in newcomer)))
    return dict(inherited_readout_capacity_qualified=capacity,inherited_wipe_qualified=wipe,swap_grid=grid,
        reciprocal_comparisons=comparisons,history_summaries=histories,
        neighbour_reciprocal_switch_both_histories=all(x['all_neighbour_reciprocal_switches'] for x in histories),
        neighbour_first_challenge_switch_both_histories=all(x['all_neighbour_first_challenge_switches'] for x in histories),
        newcomer_preservation_both_histories=all(x['newcomer_all_sequences_qualified'] for x in histories))

def analyze(run):
    summary=d.read(run/'summary.json'); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==d.read(run/'frozen/p25_neighbour_first_draw/config.json'))
    checks.add('registration',summary['registered_cases']==expected_cases()); stages=summary.get('attempted_stages',[])
    checks.add('all_stages',stages==list(STAGES)); history=predecessor_audit(run)
    checks.add('predecessor_evidence',history['quality_gate'] and history==summary['predecessor_audit']); reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report; checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==d.read(run/(stage+'_audit.json')) and d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    final=reports[stages[-1]]
    checks.add('case_count',len(summary['cases'])==460 and {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases()})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    checks.add('valid_stop',summary.get('completion_reason')=='all_registered_stages_completed')
    integrity=d.integrity(run,summary); quality=all(checks.rows.values()) and all(integrity.values())
    by={b['case']['id']:b['outcome'] for b in final['branches']}; inherited=d.read(run/'inputs/p24/independent_audit.json')
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=integrity,predecessor=history,stages=reports,
        completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],fine_comparisons=final['fine_comparisons'],
        all_fine_agree=all(x['agree'] for x in final['fine_comparisons']),length_prefix_comparisons=final['length_prefix_comparisons'],
        first_challenge_comparisons=final['first_challenge_comparisons'],
        **contrasts(by,inherited,all(x['qualified'] for x in final['reference_controls']+final['legacy_controls'])),
        historical_mathematical_audit_repeated=False,primary_state_edits_at_assembly=True,repeated_preparation=False,repeated_pause=False,
        outcome_dependent_selection=False,autonomous_reproduction=False,independent_biological_replicates=False,automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path); args=p.parse_args()
    run=args.run.absolute(); d.check_run_path(run); report=analyze(run); d.write_json(run/'independent_audit.json',report)
    print({k:report.get(k) for k in ('quality_gate','completed_cases','integration_calls','independent_check_count','all_fine_agree','history_summaries')},flush=True)
    return 0 if report['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
