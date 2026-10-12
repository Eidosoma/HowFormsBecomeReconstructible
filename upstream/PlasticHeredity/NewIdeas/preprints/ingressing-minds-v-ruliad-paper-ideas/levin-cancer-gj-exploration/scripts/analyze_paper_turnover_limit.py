"""P16 independent reconstruction of clocks, loss patterns and registered selection."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import paper_turnover_limit_design as d
import analyze_paper_lineage_robustness as p12
import analyze_paper_tissue_dependence as p15
from analyze_paper_memory import Checks,labels
from analyze_paper_sheet import arrays,edges

INDEX=p12.INDEX
GRAPH=p12.GRAPH
STAGES=('baseline','screen','rna_controls','onward')
FOUNDERS=('written','ordinary','stock_E')
SCHEMES=('single','pair_center','pair_edge','wipe')
TAUS=(1,10,100,20000)
READOUTS=('open','rna','cut')

def spec(stage='screen',founder='written',scheme='single',tau=1,route='open',readout='',fine=False):
    if stage=='baseline':
        scheme='capacity' if readout else 'no_turn'; tau=0 if readout else 20000; route='open'
        if readout: founder='stock_E'
    parts=[stage,founder,scheme,str(tau),route]
    if readout: parts.append(readout)
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,founder=founder,
                scheme=scheme,tau=tau,route=route,readout=readout,fine=fine)
def expected_stage(stage,selection=None):
    if stage=='baseline':
        return [spec(stage,readout=k,fine=f) for f in (False,True) for k in READOUTS]+[
            spec(stage,h,fine=f) for f in (False,True) for h in FOUNDERS]
    if stage=='screen':
        return [spec(stage,h,s,t,fine=f) for f in (False,True) for h in FOUNDERS for s in SCHEMES for t in TAUS]
    if stage not in ('rna_controls','onward') or selection is None: raise ValueError('Missing stage/selection')
    return [spec(stage,h,s,selection[s]['tau'],r,k,f) for f in (False,True) for h in FOUNDERS
            for s in SCHEMES[:3] for r in (('rna',) if stage=='rna_controls' else ('open','rna'))
            for k in (('',) if stage=='rna_controls' else READOUTS)]
def expected_cases(last='onward',selection=None):
    return [c for s in STAGES[:STAGES.index(last)+1] for c in expected_stage(s,selection)]
def selection_from(by):
    chosen={}
    for scheme in SCHEMES[:3]:
        eligible=[]
        for tau in TAUS:
            rows=[by.get(spec('screen',h,scheme,tau,fine=f)['id'],{}) for h in ('written','ordinary') for f in (False,True)]
            if all(r.get('available') is True and r.get('retained_E') is True for r in rows): eligible.append(tau)
        chosen[scheme]=dict(tau=min(eligible) if eligible else 20000,
            reason='fastest_shared_retention' if eligible else 'no_shared_retention')
    return chosen

def parent(c):
    return spec('screen' if c['route']=='open' else 'rna_controls',c['founder'],c['scheme'],c['tau'],c['route'],fine=c['fine'])
def prefix(c): return 'p16:%s:%s:%s:%s'%(c['founder'],c['scheme'],c['tau'],c['route'])
def stock_ids(c): return [prefix(c)+':stock_E:%02d'%i for i in range(3)]
def new_id(c,cycle,pos): return prefix(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [prefix(c)+':pupil:%02d'%i for i in range(3)]
def source(c): return 'onward__%s__actual__patch__open'%c['founder']+('__fine' if c['fine'] else '')
def source_ids(c): return ['p15:%s:actual:patch:pupil:%02d'%(c['founder'],i) for i in range(3)]
def slots(scheme,tau):
    positions={'single':[[0],[1],[2]],'pair_center':[[0,2],[1]],'pair_edge':[[0,1],[2]],'wipe':[[0,1,2]]}[scheme]
    return [(cycle,pos,len(pos)*tau) for cycle in (0,1) for pos in positions]
def random_word(i):
    return int.from_bytes(hashlib.sha256(('P16_turnover_limit_v1|501|turnover|%d'%i).encode('ascii')).digest()[:8],'big')
def expected_draws(): return {'501':{'turnover':['%016x'%random_word(i) for i in range(6)]}}
def incoming(M,cycle,pos):
    value=M.copy(); value[7,0]=M[7,0]*(1+(random_word(cycle*3+pos)*51//(1<<64)-25)/100)
    return value

def stock_folder(run,fine):
    return run/'inputs/p15/inputs/p14/inputs/p13/inputs/p12/inputs/p11'/('stock'+('__fine' if fine else ''))
def stock(run,fine):
    value=arrays(stock_folder(run,fine),'preparation')['final']; return value[:,168:169],value[:,1:2]

def integrity(run,summary):
    try:
        h,f,i=summary['hashes_sha256'],summary['frozen_hashes_sha256'],summary['inputs']; required=d.input_paths()
        return dict(revision=summary['revision']==d.REVISION,
            complete_manifest=set(h)==set(d.execution_manifest()) and set(f)=={p.name for p in d.LOCAL_FILES} and set(i)==set(required),
            input_origins=all(Path(i[p]['source'])==path for p,path in required.items()),
            execution=all(d.digest(d.ROOT/p)==v for p,v in h.items()),
            frozen=all(d.digest(run/'frozen'/p)==v for p,v in f.items()),
            sources=all(d.digest(Path(v['source']))==v['sha256'] for v in i.values()),
            inputs=all(d.digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()))
    except (OSError,KeyError,RuntimeError): return dict(integrity_readable=False)

def audit_clock(data,rec,case,checks):
    ck=lambda name,value:checks.add(case['id']+'/'+rec['phase']+'/clock/'+name,value)
    base=.00005 if case['fine'] else .0001; horizon=rec['requested_horizon']
    sample=min(100,horizon/20); maximum=min(100,horizon/100)*(.5 if case['fine'] else 1)
    total=round(horizon/base); stride=round(sample/base); cap=round(maximum/base)
    meta=rec.get('clock',{})
    ck('method',meta.get('method')=='native_explicit_euler_bounded_clock_v1')
    ck('configuration',meta.get('base_step')==base and meta.get('sample_interval')==sample and
        meta.get('maximum_step')==maximum and meta.get('adaptive') is True and
        meta.get('integer_tick_clock') is True and meta.get('initial_and_final_samples') is True)
    ck('at_least_21_samples',len(data['times'])>=21)
    expected=np.array(list(range(0,total,stride))+[total],dtype=np.int64)
    ck('required_arrays',all(k in data for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')))
    if not all(k in data for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')): return
    step,proposed,shots=(data[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks'))
    ck('integer_traces',step.dtype==proposed.dtype==shots.dtype==np.dtype('int64') and
        step.ndim==proposed.ndim==shots.ndim==1 and len(step)==len(proposed)>0)
    ck('observations',np.array_equal(shots,expected) and np.array_equal(data['times'],expected*base))
    ck('observation_shape',len(data['times'])==len(data['concentrations'])==len(expected))
    ck('first_live_sample',np.array_equal(data['concentrations'][0],data['initial']))
    ck('last_live_sample',np.array_equal(data['concentrations'][-1],data['final']))
    ck('bounded_steps',np.all(step>0) and np.all(step<=cap) and np.all(proposed>=1))
    if step.ndim!=1 or proposed.shape!=step.shape or not len(step): return
    end=np.cumsum(step); before=np.concatenate(([0],end[:-1]))
    next_sample=np.minimum(((before//stride)+1)*stride,total)
    allowed=np.minimum(np.minimum(proposed,next_sample-before),np.minimum(total-before,cap))
    ck('exact_step_clipping',np.array_equal(step,allowed))
    ck('every_boundary_respected',np.all(before>=0) and np.all(end<=next_sample) and np.all(end<=total))
    ck('exact_final_tick',int(end[-1])==total==meta.get('total_ticks'))
    ck('exact_final_time',meta.get('actual_final_time')==horizon==data['times'][-1]
        and meta.get('requested_horizon')==horizon)
    ck('trace_counts',meta.get('iterations')==len(step) and meta.get('sample_count')==len(expected)
        and meta.get('capped_steps')==int(np.count_nonzero(step<proposed)))
    if 'isolated' in rec['phase']:
        ck('late_sample_count',int(np.count_nonzero(data['times']>=7500))==26)


def audit_phase(folder,case,rec,layout,checks):
    idx=INDEX
    name=rec['phase']; ck=lambda n,v:checks.add(case['id']+'/'+name+'/'+n,v)
    ck('hash',d.digest(folder/(name+'.npz'))==rec['sha256']); a=arrays(folder,name)
    shape,ids=layout['shape'],layout['ids']; algo='depol'
    power,kd,iso,horizon=(layout[k] for k in ('power','kd','isolated','horizon'))
    count=len(ids); setup=rec['setup']; fr,to=layout['fr'],layout['to']
    regions,powers,available,compartments=(layout[k] for k in ('regions','powers','available','compartments'))
    ck('compartments',setup['compartment_expression']==compartments)
    for side in ('initial','final'):
        for k,v in (('region',regions),('power',powers),('available',available)):
            ck('edge_'+k+'_'+side,np.array_equal(a['edge_'+k+'_'+side],v))
    ck('shape',a['initial'].shape==a['final'].shape==(17,count) and a['concentrations'].shape[1:]==(17,count))
    ck('ids',setup['cell_ids']==ids and len(set(ids))==count and setup['cells']==count)
    if layout['graph']:
        ck('geometry',setup['grid_shape'] is None and setup['storage_shape']==[1,6] and
            setup['orthogonal_only'] is False and setup['periodic'] is False and
            setup['network_mode']=='explicit_common_graph' and setup['explicit_edges']==[list(e) for e in GRAPH])
        ck('schedule_mask',setup['scheduled_pupils']==layout['active'] and setup['route']==layout['route'])
    else:
        ck('geometry',setup['grid_shape']==shape and setup['orthogonal_only'] is True and setup['periodic'] is False)
    ck('topology',np.array_equal(a['edge_from'],fr) and np.array_equal(a['edge_to'],to))
    times=a['times']
    ck('time_axis',times.ndim==1 and len(times)>=2 and len(times)==len(a['concentrations']) and
        times[0]>=0 and np.all(np.diff(times)>0) and np.any(times>=.75*horizon))
    ck('logical_interval',rec.get('logical_interval')==[layout['base'],layout['base']+horizon])
    ck('duration',rec['requested_horizon']==horizon and rec['last_sample_time']==times[-1] and rec['samples']==len(times))
    for key in ('initial','concentrations','final'):
        ck(key+'_finite',np.isfinite(a[key]).all() and np.min(a[key])>=0)
        ck(key+'_snail',np.all(a[key][...,idx['snail'],:]==72))
    ck('labels',''.join(labels(a['final'],idx))==rec['final_labels'])
    ck('snapshot_difference',float(np.max(np.abs(a['concentrations'][-1]-a['final'])))==rec['last_snapshot_live_difference'])
    ck('strategy',setup['algorithm']==algo and setup['power']==power and setup['mirna_kd']==kd and setup['isolated']==iso)
    ck('neighbor',not setup['neighbor_voltage_reading'] and setup['cell_voltage_gate_present']==(algo!='hypol'))
    ck('transport',not a['junction_diffusion'].any() if iso else a['junction_diffusion'][:4].any())
    ck('gate_inventory',setup['gate_classes']==dict(ic=[] if algo=='hypol' else ['set_Vmem_from_conc'],
        gj=['GJ_gate','tumor_overX_GJ_gate'],gd=['EMT_GRN_gate'],gj_add=['EMT_GJ_gate']))
    ck('integrator',setup['integrator']==dict(time_step=.00005 if case['fine'] else .0001,
        sim_integ_max_delt_cc=.0005 if case['fine'] else .001,
        sim_integ_max_delt_Vm=.00005 if case['fine'] else .0001,use_implicit=False))
    ck('expression_constants',setup['tumor_rule']==dict(x0=40.,M_ZEB_miR200=200000/18000,tness=1,GJ_OiET=.5))
    q=setup['voltage_constants']
    ck('voltage_constants',q['F']==96485 and q['cm']==.05 and
        np.isclose(q['cell_vol'],4*np.pi*(5e-6)**3/3,rtol=1e-14,atol=0) and
        np.isclose(q['cell_sa'],4*np.pi*(5e-6)**2,rtol=1e-14,atol=0))
    for key,value in (('A1',-110.),('A2',-110.),('VO1',-.0102),('VO2',-.0102)):
        ck('Cx45_'+key,np.all(a['gate_'+key]==value))
    ck('miRNA_size',np.all(a['gate_Gmin'][idx['miR200_total']]==0) and
        np.all(a['gate_Gdelta'][idx['miR200_total']]==1.56) and setup['mirna_transport']==dict(valence=-1,medium_size=True))
    ck('membrane_valences',np.array_equal(a['valences'],[1,1,-1,-1]+[0]*13))
    for side in ('initial','final'):
        value=a[side]; vm=(value*a['valences'][:,None]).sum(0)*96485*q['cell_vol']/(q['cell_sa']*.05)
        ck('vm_'+side,np.allclose(vm,a['vm_'+side],rtol=1e-12,atol=1e-14))
        dv=vm[fr]-vm[to]
        voltage=1.56/(1+np.exp(-110*(-dv+.0102))+np.exp(-110*(dv+.0102)))
        ck('voltage_'+side,np.allclose(voltage,a['voltage_gate_'+side],rtol=1e-10,atol=1e-12))
        mi,zeb,protein=(value[idx[k]] for k in ('miR200_total','Zeb_mRNA_total','ZEB_prot'))
        tp=(protein/(200000/18000+5))**10; tumor=1/(1+(mi/30)**10)*tp/(1+tp)
        lo=np.minimum(tumor[fr],tumor[to]); hi=np.maximum(tumor[fr],tumor[to])
        expression=(1+(lo+.5*(hi-lo))*(powers-1))*available
        ck('expression_'+side,np.allclose(expression,a['expression_gate_'+side],rtol=1e-12,atol=1e-12))
        potassium=np.ones(count)
        if algo!='hypol':
            ratio=(mi/(.001+zeb))**10; potassium=1+30*ratio/(1+ratio)
        ck('potassium_'+side,np.allclose(potassium,a['potassium_gate_'+side],rtol=1e-12,atol=1e-12))
    audit_clock(a,rec,case,checks)
    return a



def descriptor(name,ids,base,span,kind,route='open'):
    isolated=kind=='isolated'; shape=[2,3] if kind=='readout' else [1,3]
    fr,to=edges(shape); power=1 if isolated else 60
    kd=0 if isolated or route=='rna' else 1.25e-14; cut=kind=='readout' and route=='cut'
    members={0,1,2} if kind=='readout' else set()
    regions=np.array([1 if f in members and t in members else 2 if (f in members)!=(t in members) else 0
                      for f,t in zip(fr,to)],dtype=np.int8)
    return dict(name=name,ids=ids.copy(),shape=shape,base=base,horizon=span,graph=False,
        power=power,kd=kd,isolated=isolated,fr=fr,to=to,regions=regions,
        powers=np.full(len(fr),power,dtype=float),available=np.where((regions==2)&cut,0.,1.),
        compartments=dict(internal=power,boundary=power,helper=power,boundary_cut=cut))

class Reader(p12.Reader):
    def __init__(self,folder,c,checks):
        self.folder,self.c,self.checks=folder,c,checks
        self.result=json.loads((folder/'result.json').read_text()); self.records=self.result['phases']
        self.at=0; self.data={}; self.environment=arrays(stock_folder(folder.parent,c['fine']),'preparation')['environment']
    def take(self,layout,initial):
        name=layout['name']
        if self.at>=len(self.records): raise ValueError('Missing registered phase '+name)
        rec=self.records[self.at]; self.at+=1; self.ck(name+'/ordered_phase',rec['phase']==name)
        if rec['phase']!=name: raise ValueError('Unexpected phase order')
        value=audit_phase(self.folder,self.c,rec,layout,self.checks)
        self.eq(name+'/actual_initial',value['initial'],initial); self.eq(name+'/native_bath',value['environment'],self.environment)
        self.data[name]=value; return value['final']
    def finish(self,out):
        self.ck('exact_raw_inventory',{p.stem for p in self.folder.glob('*.npz')}=={p['phase'] for p in self.records})
        return super().finish(out)

def observation(data,positions): return p15.observation(data,positions)

def audit_turnover(rd,run,c):
    E,M=stock(run,c['fine']); base=0 if c['founder']=='stock_E' else 1180000
    if c['founder']=='stock_E': value=np.repeat(E,3,axis=1); ids=stock_ids(c)
    else:
        src=source(c); ids=source_ids(c); info=json.loads((run/'inputs/p15'/src/'result.json').read_text())
        rec=info['phases'][-1]
        rd.ck('source_identity_and_clock',rec['phase']=='isolated_2' and rec['setup']['cell_ids']==ids and
              rec['logical_interval']==[1170000,1180000])
        value=arrays(run/'inputs/p15'/src,'isolated_2')['final']
    original_ids=ids.copy(); source_labels=''.join(labels(value,INDEX)); rd.ck('source_E',source_labels=='EEE')
    observed={}; replacements=[]; cursor=base
    if c['stage']=='baseline':
        value=rd.take(descriptor('no_turnover',ids,cursor,120000,'chain'),value); cursor+=120000
        observed['no_turnover']=observation(rd.data['no_turnover'],range(3))
    else:
        for event,(cycle,positions,span) in enumerate(slots(c['scheme'],c['tau']),1):
            value=value.copy()
            for pos in positions:
                initial=incoming(M,cycle,pos); lab=str(labels(initial,INDEX)[0]); rd.ck('incoming_%d_%d_M'%(cycle,pos),lab=='M')
                old=ids[pos]; ids[pos]=new_id(c,cycle,pos); value[:,pos:pos+1]=initial
                replacements.append(dict(event=event,cycle=cycle,position=pos,removed=old,inserted=ids[pos],initial_label=lab))
            name='replacement_%02d'%event
            value=rd.take(descriptor(name,ids,cursor,span,'chain',c['route']),value); cursor+=span
            observed[name]=observation(rd.data[name],range(3))
        rd.ck('equal_burden_and_duration',len(replacements)==6 and cursor==base+6*c['tau'] and
              [sum(x['position']==p for x in replacements) for p in range(3)]==[2,2,2])
        rd.ck('all_original_carriers_removed',not set(original_ids)&set(ids))
    for i in (1,2):
        name='isolated_'+str(i); value=rd.take(descriptor(name,ids,cursor,10000,'isolated'),value); cursor+=10000
        observed[name]=observation(rd.data[name],range(3))
    continuous=all(all(v['stable_E']) for k,v in observed.items() if not k.startswith('isolated'))
    retained=all(all(observed['isolated_'+str(i)]['stable_E']) for i in (1,2))
    return dict(available=True,source_labels=source_labels,original_ids=original_ids,
        observations=observed,replacements=replacements,all_windows_E=continuous,
        retained_E=retained,continuous_renewal=continuous and retained,logical_end=cursor)

def audit_readout(rd,run,c):
    E,M=stock(run,c['fine'])
    if c['stage']=='baseline':
        donors=np.repeat(E,3,axis=1); ids=['p16:readout:stock_E:%02d'%i for i in range(3)]; base=0
    else:
        par=parent(c); path=run/par['id']; donors=arrays(path,'isolated_2')['final']
        ids=[new_id(c,1,i) for i in range(3)]
        base=(0 if c['founder']=='stock_E' else 1180000)+6*c['tau']+20000
        row=json.loads((path/'result.json').read_text())
        rd.ck('actual_turnover_parent',row['case']==par and row['phases'][-1]['setup']['cell_ids']==ids and
              row['phases'][-1]['logical_interval']==[base-10000,base] and row['outcome']['logical_end']==base)
    fresh=pupils(c); recipients=np.repeat(M,3,axis=1)
    initial_donors=''.join(labels(donors,INDEX)); initial_recipients=''.join(labels(recipients,INDEX))
    rd.ck('fresh_recipients_M',initial_recipients=='MMM')
    value=rd.take(descriptor('contact',ids+fresh,base,20000,'readout',c['readout']),np.concatenate((donors,recipients),axis=1))
    observed={'contact':observation(rd.data['contact'],range(3,6))}
    donor_end=''.join(labels(value[:,:3],INDEX)); value=value[:,3:]; rd.ck('all_donors_removed',not set(ids)&set(fresh))
    for i in (1,2):
        name='isolated_'+str(i)
        value=rd.take(descriptor(name,fresh,base+20000+(i-1)*10000,10000,'isolated'),value)
        observed[name]=observation(rd.data[name],range(3))
    if c['stage']=='baseline':
        src='readout__stock__stock_E__'+c['readout']+('__fine' if c['fine'] else '')
        for name,data in rd.data.items():
            archived=arrays(run/'inputs/p15'/src,name); rd.ck(name+'/replay_inventory',set(archived)==set(data))
            for key in archived: rd.eq(name+'/historical_replay/'+key,data[key],archived[key])
    success=all(all(observed['isolated_'+str(i)]['stable_E']) for i in (1,2))
    return dict(available=True,donor_initial_labels=initial_donors,recipient_initial_labels=initial_recipients,
        donor_end_labels=donor_end,observations=observed,transmitted_E=success,logical_end=base+40000)

def branch(folder,c,checks):
    rd=Reader(folder,c,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('clock',result['clock_method']=='native_explicit_euler_bounded_clock_v1' and
          result.get('clock_policy')=='phase_scaled_sampling_and_step_cap_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve',
        'full_source_transfer','only_registered_columns_replaced','registered_interval_selection')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('benchmark_prior_age_matched','autonomous_reproduction',
        'parameter_retuning','outcome_dependent_cell_selection','cross_branch_pooling','cell_division_simulated',
        'independent_biological_replicates','automatic_follow_on')))
    rd.ck('replay_scope',result.get('exact_P15_capacity_replay')==(c['stage']=='baseline' and bool(c['readout'])))
    out=audit_readout(rd,folder.parent,c) if c['readout'] else audit_turnover(rd,folder.parent,c)
    return rd.finish(out)

def stage_audit(run,stage):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    cases=expected_cases(stage,summary.get('selection')); records={r['id']:r for r in summary['cases']}
    branches=[]; by={}; endpoints={}; calls=0
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'; result=json.loads(path.read_text())
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and result==row['result'])
        report,data=branch(run/c['id'],c,checks); branches.append(report); by[c['id']]=report['outcome']
        endpoints[c['id']]=data; calls+=len(data)
    fine=p12.compare_fine(cases,by,endpoints,checks)
    chosen=selection_from(by) if stage!='baseline' else None
    if stage in ('rna_controls','onward'): checks.add('independent_selection',chosen==summary['selection'])
    history=summary.get('predecessor_audit',{})
    checks.add('history_checked',summary.get('predecessor_gate') is True and history.get('quality_gate') is True)
    checks.add('history_saved',history==json.loads((run/'predecessor_audit.json').read_text()) and
        d.digest(run/'predecessor_audit.json')==summary.get('predecessor_audit_sha256'))
    checks.add('draw_book',json.loads((run/'frozen/paper_turnover_limit_draws_v1.json').read_text())==expected_draws())
    checks.add('call_count',calls=={'baseline':36,'screen':612,'rna_controls':732,'onward':1056}[stage])
    checks.add('unique_case_records',len(records)==len(summary['cases']))
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    return dict(stage=stage,quality_gate=bool(quality),eligible=bool(quality),checks=checks.rows,
        integrity=provenance,branches=branches,fine_comparisons=fine,integration_calls=calls,
        cumulative_cases=len(branches),selection=chosen,eligibility_means_technical_permission_only=True)

def predecessor_audit(run):
    original=p15.analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p15/independent_audit.json').read_text())
    archived=p15.analyze(run/'inputs/p15'); archived['run']=str(d.PREDECESSOR)
    good=original==archived==saved and original['quality_gate'] and original['independent_check_count']==24043
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_matches_saved=archived==saved,
        prior_checks=original['independent_check_count'],prior_cases=original['completed_cases'],
        prior_calls=original['integration_calls'],actual_onward_recipient_sources=True)

def contrasts(by,selection):
    def pair(stage,h='written',s='single',t=1,r='open',k=''):
        return [by.get(spec(stage,h,s,t,r,k,f)['id'],{}) for f in (False,True)]
    def both(rows,key,value=True):
        return all(row.get('available') is True and row.get(key) is value for row in rows)
    positive=both(pair('baseline',k='open'),'transmitted_E')
    negative=all(both(pair('baseline',k=k),'transmitted_E',False) for k in ('rna','cut'))
    capacity=dict(open_transmission_both=positive,negative_controls_both=negative,qualified=positive and negative)
    baseline=[dict(founder=h,source_trials=1,retained_E_both=both(pair('baseline',h),'retained_E')) for h in FOUNDERS]
    screen=[]; selected=[]; chains=[]
    for h in FOUNDERS:
        for s in SCHEMES:
            for t in TAUS:
                rows=pair('screen',h,s,t)
                screen.append(dict(founder=h,scheme=s,tau=t,source_trials=1,
                    retained_E_both=both(rows,'retained_E'),all_windows_E_both=both(rows,'all_windows_E'),
                    continuous_renewal_both=both(rows,'continuous_renewal')))
        for s in SCHEMES[:3]:
            t=selection[s]['tau']; opened=pair('screen',h,s,t); blocked=pair('rna_controls',h,s,t,'rna')
            wipe=pair('screen',h,'wipe',t); erased=both(wipe,'retained_E',False)
            selected.append(dict(founder=h,scheme=s,tau=t,selection_reason=selection[s]['reason'],source_trials=1,
                retained_E_both=both(opened,'retained_E'),RNA_block_retained_E_both=both(blocked,'retained_E'),
                whole_loss_retained_E_both=both(wipe,'retained_E'),negative_wipe_both=erased,
                carrier_dependent_retention=both(opened,'retained_E') and erased,
                RNA_dependence=both(opened,'retained_E') and both(blocked,'retained_E',False)))
            for r,parents in (('open',opened),('rna',blocked)):
                onward=both(pair('onward',h,s,t,r,'open'),'transmitted_E')
                controls=all(both(pair('onward',h,s,t,r,k),'transmitted_E',False) for k in ('rna','cut'))
                raw=both(parents,'retained_E') and onward
                chains.append(dict(founder=h,scheme=s,tau=t,route=r,source_trials=1,
                    retained_E_both=both(parents,'retained_E'),onward_transmission_both=onward,
                    raw_retention_and_onward=raw,continuous_full_chain=both(parents,'continuous_renewal') and onward,
                    negative_wipe_both=erased,
                    control_qualified_transmission=onward and controls,
                    control_qualified_chain=raw and controls and erased,
                    benchmark_supported_chain=raw and controls and erased and capacity['qualified']))
    return dict(readout_capacity=capacity,no_turnover=baseline,screen_outcomes=screen,
                selected_contrasts=selected,chain_outcomes=chains)

def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_turnover_limit_v1.json').read_text()))
    selection=summary.get('selection')
    checks.add('registration',summary['registered_cases']==expected_cases(selection=selection))
    stages=summary.get('attempted_stages',[]); checks.add('all_stages',stages==list(STAGES))
    history=predecessor_audit(run)
    checks.add('predecessor_fresh',history['quality_gate'] and history==summary['predecessor_audit'])
    reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report
        checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==json.loads((run/(stage+'_audit.json')).read_text()) and
            d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    final=reports[stages[-1]]
    checks.add('case_count',len(summary['cases'])==234 and
        {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases(selection=selection)})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    checks.add('valid_stop',summary.get('completion_reason')=='all_registered_stages_completed')
    checks.add('selection',selection==reports['screen']['selection']==final['selection'])
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    by={b['case']['id']:b['outcome'] for b in final['branches']}
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=provenance,predecessor=history,
        stages=reports,completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],
        completion_reason=summary.get('completion_reason'),fine_comparisons=final['fine_comparisons'],
        all_fine_agree=all(p['agree'] for p in final['fine_comparisons']),selection=selection,
        **contrasts(by,selection),external_schedule=True,autonomous_reproduction=False,
        reused_P15_ancestry=True,independent_biological_replicates=False,benchmark_prior_age_matched=False,
        selected_followups_independently_confirmed=False,exact_turnover_threshold_established=False,
        automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    result=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',result)
    keys=('quality_gate','completed_cases','integration_calls','independent_check_count','all_fine_agree',
          'selection','readout_capacity','no_turnover','selected_contrasts','chain_outcomes','completion_reason')
    print(json.dumps({k:result.get(k) for k in keys} if args.compact else result,indent=2))
    return 0 if result['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
