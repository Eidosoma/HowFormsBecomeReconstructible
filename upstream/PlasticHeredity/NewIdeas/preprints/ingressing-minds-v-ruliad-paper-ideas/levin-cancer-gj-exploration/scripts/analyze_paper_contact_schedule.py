"""Independent P10 audit: graph, clocks, actual live carriers and conditional selection."""
import argparse
import json
from pathlib import Path
import re
import numpy as np
import paper_contact_schedule_design as d
import analyze_paper_m_calibration as p7
import analyze_paper_staged_relay as p9
from analyze_paper_memory import Checks,labels
from analyze_paper_restoration import stable
from analyze_paper_sheet import arrays,edges

# Independent protocol transcription; do not derive audits from runner schedules.
GRAPH=((0,1),(0,2),(1,3),(2,3),(1,4),(2,4),(1,5),(2,5))
WINDOWS=dict(sequential=((0,20000),(20000,40000),(40000,60000)),
    simultaneous=((0,20000),(0,20000),(0,20000)),
    overlap_25=((0,20000),(15000,35000),(30000,50000)),
    overlap_50=((0,20000),(10000,30000),(20000,40000)),
    gaps_10=((0,20000),(30000,50000),(60000,80000)),
    short_10=((0,10000),(20000,30000),(40000,50000)),
    uneven=((0,20000),(18000,38000),(41000,61000)))
PRIORITY=('simultaneous','overlap_50','overlap_25','uneven','gaps_10','short_10')
HISTORIES=('rewritten_restored_E','ordinary_M')
LINEAGE='relay__rewritten_restored_E__sequential'


def case_spec(kind,founder,schedule,route,fine):
    return dict(id='__'.join((kind,founder,schedule,route))+('__fine' if fine else ''),
                kind=kind,founder=founder,schedule=schedule,route=route,fine=fine)


def old_case(layout):
    return dict(id=f'capacity__{layout}__depol__high__M_open',kind='capacity',layout=layout,
                algorithm='depol',anchor='high',condition='M_open',fine=False)


def expected_cases(selected=()):
    cases=[dict(id='replay__'+l,kind='replay',layout=l,source=old_case(l)['id'],fine=False)
           for l in ('three_to_one','three_to_three')]
    for fine in (False,True):
        cases.extend(case_spec('calibration',h,'single',r,fine) for h,r in
            [('ordinary_M','open'),('ordinary_M','rna'),('ordinary_M','cut'),('ordinary_E_sham','open')])
    for fine in (False,True):
        cases.extend(case_spec('screen',h,s,'open',fine) for h in HISTORIES+('ordinary_E_sham',) for s in WINDOWS)
        cases.extend(case_spec('screen',h,'sequential',r,fine) for h in HISTORIES for r in ('rna','cut'))
    cases.extend(case_spec('continuation',h,s,r,fine) for fine in (False,True)
                 for s in selected for h in HISTORIES for r in ('open','rna','cut'))
    return cases


def intervals(schedule):
    windows=((0,20000),(-1,-1),(-1,-1)) if schedule=='single' else WINDOWS[schedule]
    end=20000 if schedule=='single' else 80000
    boundaries=sorted({0,end}|{t for pair in windows for t in pair if t>=0})
    return [(start,stop,[i for i,(a,b) in enumerate(windows) if a<=start and stop<=b])
            for start,stop in zip(boundaries,boundaries[1:])]


def round_phase_names(case,number):
    return [f'r{number:02d}_segment_{i:02d}' for i in range(1,len(intervals(case['schedule']))+1)]+[
        f'r{number:02d}_isolated_1',f'r{number:02d}_isolated_2']


def phase_names(case,nrounds=1):
    if case['kind']=='replay': return ['contact','isolated_1','isolated_2']
    start=2 if case['kind']=='continuation' else 1
    return [p for n in range(start,start+nrounds) for p in round_phase_names(case,n)]


def parts(case,name):
    match=re.fullmatch(r'r([0-9]{2})_(.+)',name)
    if not match: raise ValueError('Invalid P10 phase name')
    n=int(match[1]); part=match[2]
    if n not in (range(2,7) if case['kind']=='continuation' else [1]) or name not in round_phase_names(case,n):
        raise ValueError('Unregistered P10 phase')
    return n,part


def founder_ids(case):
    if case['kind']=='continuation': return [f'p10:pupil:01:{i:02d}' for i in range(3)]
    if case['founder']=='rewritten_restored_E': return [f'pupil:06:{i:02d}' for i in range(3)]
    return [f'p10:founder:{"E" if case["founder"]=="ordinary_E_sham" else "M"}:{i:02d}' for i in range(3)]


def geometry(case,name):
    n,part=parts(case,name); first=2 if case['kind']=='continuation' else 1
    teachers=founder_ids(case) if n==first else [f'p10:pupil:{n-1:02d}:{i:02d}' for i in range(3)]
    pupils=[f'p10:pupil:{n:02d}:{i:02d}' for i in range(3)]
    return ([1,6],teachers+pupils) if part.startswith('segment') else ([1,3],pupils)


def phase_active(case,name):
    _,part=parts(case,name)
    return intervals(case['schedule'])[int(part[-2:])-1][2] if part.startswith('segment') else []


def phase_edges(case,name):
    if parts(case,name)[1].startswith('segment'): return np.array(GRAPH).T
    return edges([1,3])


def settings(case,name):
    _,part=parts(case,name); contact=part.startswith('segment')
    span=intervals(case['schedule'])[int(part[-2:])-1] if contact else None
    return 'depol',60 if contact else 1,1.25e-14 if contact and case['route']!='rna' else 0,not contact,span[1]-span[0] if contact else 10000


def logical_interval(case,name):
    n,part=parts(case,name); base=(n-1)*100000
    if part.startswith('segment'): start,stop,_=intervals(case['schedule'])[int(part[-2:])-1]
    else:
        start=(20000 if case['kind']=='calibration' else 80000)+(int(part[-1])-1)*10000; stop=start+10000
    return [base+start,base+stop]


def regional_settings(case,name):
    contact=parts(case,name)[1].startswith('segment')
    power=60 if contact else 1; cut=contact and case['route']=='cut'
    regions=np.array([1,1]+[2]*6 if contact else [0,0],dtype=np.int8)
    active=phase_active(case,name)
    available=np.array([1.,1.]+[float(i in active and not cut) for i in range(3) for _ in range(2)] if contact else [1.,1.])
    return regions,np.full(len(regions),power,dtype=float),available,dict(
        internal=power,boundary=power,helper=power,boundary_cut=cut)


def integrity(run,summary):
    try:
        h,f,i=summary['hashes_sha256'],summary['frozen_hashes_sha256'],summary['inputs']; required=d.input_paths()
        return dict(revision=summary['revision']==d.REVISION,
            complete_manifest=set(h)==set(d.execution_manifest()) and set(f)=={p.name for p in d.LOCAL_FILES} and set(i)==set(required),
            input_origins=all(Path(i[p]['source'])==source for p,source in required.items()),
            execution=all(d.digest(d.ROOT/p)==v for p,v in h.items()),
            frozen=all(d.digest(run/'frozen'/p)==v for p,v in f.items()),
            sources=all(d.digest(Path(v['source']))==v['sha256'] for v in i.values()),
            inputs=all(d.digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()))
    except (OSError,KeyError,RuntimeError): return dict(integrity_readable=False)


def audit_phase(folder,case,rec,idx,checks):
    name=rec['phase']; ck=lambda n,v:checks.add(case['id']+'/'+name+'/'+n,v)
    ck('hash',d.digest(folder/(name+'.npz'))==rec['sha256']); a=arrays(folder,name)
    shape,ids=geometry(case,name); algo,power,kd,iso,horizon=settings(case,name)
    count=len(ids); setup=rec['setup']; fr,to=phase_edges(case,name)
    regions,powers,available,compartments=regional_settings(case,name)
    ck('compartments',setup['compartment_expression']==compartments)
    for side in ('initial','final'):
        for k,v in (('region',regions),('power',powers),('available',available)):
            ck('edge_'+k+'_'+side,np.array_equal(a['edge_'+k+'_'+side],v))
    ck('shape',a['initial'].shape==a['final'].shape==(17,count) and a['concentrations'].shape[1:]==(17,count))
    ck('ids',setup['cell_ids']==ids and len(set(ids))==count and setup['cells']==count)
    if not iso:
        ck('geometry',setup['grid_shape'] is None and setup['storage_shape']==[1,6] and
            setup['orthogonal_only'] is False and setup['periodic'] is False and
            setup['network_mode']=='explicit_common_graph' and setup['explicit_edges']==[list(e) for e in GRAPH])
        ck('schedule_mask',setup['scheduled_pupils']==phase_active(case,name) and setup['route']==case['route'])
    else:
        ck('geometry',setup['grid_shape']==[1,3] and setup['orthogonal_only'] is True and setup['periodic'] is False)
    ck('topology',np.array_equal(a['edge_from'],fr) and np.array_equal(a['edge_to'],to))
    times=a['times']
    ck('time_axis',times.ndim==1 and len(times)>=2 and len(times)==len(a['concentrations']) and
        times[0]>=0 and np.all(np.diff(times)>0) and np.any(times>=.75*horizon))
    ck('logical_interval',rec.get('logical_interval')==logical_interval(case,name))
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
    return a


def stock(run):
    x=arrays(run/'inputs/p9/inputs/p8/inputs/p7/inputs/p3/reference','preparation')
    return x['concentrations'][-1,:,168:169],x['concentrations'][-1,:,1:2],x['environment']


def founder_source(run,case,E,M):
    if case['kind']=='continuation':
        source=case_spec('screen',case['founder'],case['schedule'],'open',case['fine'])['id']
        return arrays(run/source,'r01_isolated_2')['final']
    if case['founder']=='rewritten_restored_E':
        return arrays(run/'inputs/p9'/LINEAGE,'r06_isolated_2')['final']
    return np.repeat(E if case['founder']=='ordinary_E_sham' else M,3,axis=1)


def branch(folder,case,checks):
    run=folder.parent; result=json.loads((folder/'result.json').read_text())
    ck=lambda n,v:checks.add(case['id']+'/'+n,v); eq=lambda n,x,y:checks.equal(case['id']+'/'+n,x,y)
    ck('case',result['case']==case and result['execution_pass'])
    ck('scope',all(result[k] for k in ('external_schedule','all_cells_evolve')) and
        result['explicit_non_lattice_extension']==(case['kind']!='replay') and
        not any(result[k] for k in ('teachers_retained_between_rounds','cell_division_simulated','parameter_retuning',
            'outcome_dependent_cell_selection','cross_branch_pooling','extra_M_supplementation',
            'screen_prefix_is_independent_replication','automatic_follow_on')))
    idx=result['ion_indices']; ck('indices',idx==dict(Na=0,K=1,Cl=2,P=3,snail=4,miR200_total=5,
        Zeb_mRNA_total=6,ZEB_prot=7,miR200_free=8,**{f'bound{i}':9+i for i in range(7)},ST=16))
    rounds=[]; continuation=case['kind']=='continuation'
    ck('shared_prefix',result['shared_screen_rounds']==int(continuation))
    if case['kind']=='replay':
        ck('phase_list',[p['phase'] for p in result['phases']]==phase_names(case))
        ck('replay_scope',result['rounds']==[] and result['newly_simulated_rounds']==0 and result['stop_reason']=='historical_replay')
        old=old_case(case['layout']); source=run/'inputs/p9/inputs/p8/inputs/p7'/old['id']; data={}
        for rec in result['phases']:
            name=rec['phase']; local=Checks(); data[name]=p7.audit_phase(folder,old,rec,idx,local)
            for key,value in local.rows.items(): ck('native/'+key,value)
            original=arrays(source,name); ck('replay/'+name+'/keys',set(data[name])==set(original))
            for key,value in original.items(): eq('replay/'+name+'/'+key,data[name][key],value)
        _,nd,_=p7.layout(old)
        out=p7.outcome(data['contact'],data['isolated_1'],data['isolated_2'],idx,nd)
    else:
        nrounds=len(result['rounds']); first=2 if continuation else 1
        ck('round_count',1<=nrounds<=(5 if continuation else 1) and result['newly_simulated_rounds']==nrounds)
        ck('phase_list',[p['phase'] for p in result['phases']]==phase_names(case,nrounds))
        data={p['phase']:audit_phase(folder,case,p,idx,checks) for p in result['phases']}
        E,M,bath=stock(run); carry=founder_source(run,case,E,M)
        for name,value in data.items(): eq('bath/'+name,value['environment'],bath)
        if continuation:
            source=case_spec('screen',case['founder'],case['schedule'],'open',case['fine'])['id']
            original=json.loads((run/source/'result.json').read_text())
            ck('prefix_identity',original['case']==case_spec('screen',case['founder'],case['schedule'],'open',case['fine']))
            ck('prefix_retention',stable(arrays(run/source,'r01_isolated_1'),arrays(run/source,'r01_isolated_2'),idx,'M').all())
        for n in range(first,first+nrounds):
            prefix=f'r{n:02d}_'; current=np.concatenate((carry,np.repeat(E,3,axis=1)),axis=1)
            teacher_trace=[]; presignal=[None,None,None]
            for slot,(_,_,active) in enumerate(intervals(case['schedule']),1):
                name=prefix+f'segment_{slot:02d}'; c=data[name]
                eq(name+'/all_six_live_states',c['initial'],current)
                teacher_trace.append(dict(segment=slot,start=''.join(labels(c['initial'][:,:3],idx)),
                    end=''.join(labels(c['final'][:,:3],idx))))
                for i in active:
                    if presignal[i] is None: presignal[i]=str(labels(c['initial'][:,3+i:4+i],idx)[0])
                current=c['final']
            one,two=data[prefix+'isolated_1'],data[prefix+'isolated_2']
            eq(prefix+'all_teachers_removed_all_pupils_kept',one['initial'],current[:,3:])
            eq(prefix+'hold_continuity',two['initial'],one['final']); carry=two['final']
            m,e=stable(one,two,idx,'M'),stable(one,two,idx,'E')
            end=logical_interval(case,prefix+'isolated_2')[-1]
            rounds.append(dict(round=n,retained_M_by_pupil=m.tolist(),retained_E_by_pupil=e.tolist(),
                all_recipient_M=bool(m.all()),all_recipient_E=bool(e.all()),
                retained_M=int(m.sum()),retained_E=int(e.sum()),teacher_segments=teacher_trace,
                presignal_labels=presignal,pupil_before_holds_labels=''.join(labels(one['initial'],idx)),
                pupil_final_labels=''.join(labels(two['final'],idx)),logical_end=end))
            ck(prefix+'record',result['rounds'][n-first]==dict(round=n,retained_M=m.tolist(),complete=bool(m.all()),logical_end=end))
        failed=[x['round'] for x in rounds if not x['all_recipient_M']]
        complete=continuation and nrounds==5 and not failed
        if continuation:
            ck('stop_at_first_failure',(not failed and nrounds==5) or failed==[first+nrounds-1])
        reason='six_complete_rounds' if complete else 'first_incomplete_round' if continuation else 'single_round'
        ck('stop_reason',result['stop_reason']==reason)
        last=rounds[-1]
        out=dict(complete_six_rounds=complete,new_rounds=nrounds,
            successful_new_rounds=nrounds-int(bool(failed)),shared_screen_rounds=int(continuation),
            first_incomplete_round=failed[0] if failed else None,
            all_recipient_M=last['all_recipient_M'],all_recipient_E=last['all_recipient_E'],
            retained_M_by_pupil=last['retained_M_by_pupil'],retained_E_by_pupil=last['retained_E_by_pupil'],
            all_presignal_E=all(v in ('E',None) for row in rounds for v in row['presignal_labels']),
            teachers_always_M=all(s['start']==s['end']=='MMM' for row in rounds for s in row['teacher_segments']))
    return dict(case=case,rounds=rounds,outcomes=out),data,idx


def audited_records(run,cases,checks):
    summary=json.loads((run/'summary.json').read_text()); records={r['id']:r for r in summary['cases']}
    reports=[]; endpoints={}; calls=0
    for c in cases:
        rec=records.get(c['id']); checks.add(c['id']+'/record',rec is not None and rec['execution_pass'])
        if rec is None or not rec['execution_pass']: continue
        path=run/c['id']/'result.json'
        checks.add(c['id']+'/result_frozen',d.digest(path)==rec['result_sha256'] and json.loads(path.read_text())==rec['result'])
        report,data,idx=branch(run/c['id'],c,checks); reports.append(report); calls+=len(data)
        endpoints[c['id']]={n:(v['initial'],v['final'],labels(v['final'],idx)) for n,v in data.items()}
    return reports,endpoints,calls


def gate_audit(run):
    run=Path(run); checks=Checks(); summary=json.loads((run/'summary.json').read_text())
    checks.add('predecessor_gate',summary['predecessor_gate'])
    saved=json.loads((run/'inputs/p9/independent_audit.json').read_text())
    checks.add('P9_saved_pass',saved['quality_gate'] and saved['independent_check_count']==19424 and saved['native_integrations']==398)
    prior=json.loads((run/'inputs/p9/summary.json').read_text())
    old=next(c for c in p9.expected_cases() if c['id']==LINEAGE)
    record=next(c for c in prior['cases'] if c['id']==LINEAGE); folder=run/'inputs/p9'/LINEAGE
    checks.add('P9/selected_record_frozen',record['execution_pass'] and
        d.digest(folder/'result.json')==record['result_sha256'] and json.loads((folder/'result.json').read_text())==record['result'])
    local=Checks(); history,data,idx=p9.branch(folder,old,local)
    for k,v in local.rows.items(): checks.add('P9/'+k,v)
    checks.add('P9/six_renewals',history['outcomes']['complete_six_rounds'] and len(history['rounds'])==6)
    checks.add('P9/final_group_MMM',stable(data['r06_isolated_1'],data['r06_isolated_2'],idx,'M').all())
    ids=next(p['setup']['cell_ids'] for p in record['result']['phases'] if p['phase']=='r06_isolated_2')
    checks.equal('P9/final_ids',ids,[f'pupil:06:{i:02d}' for i in range(3)])
    original=json.loads((run/'inputs/p9/inputs/p8/inputs/p7/summary.json').read_text())
    for case in expected_cases()[:2]:
        source=old_case(case['layout']); folder=run/'inputs/p9/inputs/p8/inputs/p7'/source['id']
        row=next(x for x in original['cases'] if x['id']==source['id'])
        checks.add('P7/'+source['id']+'/frozen',row['execution_pass'] and d.digest(folder/'result.json')==row['result_sha256'] and
            json.loads((folder/'result.json').read_text())==row['result'])
        local=Checks(); report,_,_=p7.branch(folder,source,local)
        for k,v in local.rows.items(): checks.add('P7/'+k,v)
        checks.add('P7/'+source['id']+'/known_outcome',report['outcomes'][
            'all_recipient_M' if case['layout']=='three_to_one' else 'all_recipient_E'])
    reports,_,calls=audited_records(run,expected_cases()[:2],checks)
    checks.add('replay_count',len(reports)==2 and calls==6)
    provenance=integrity(run,summary)
    return dict(quality_gate=all(checks.rows.values()) and all(provenance.values()),checks=checks.rows,
                integrity=provenance,branches=reports,founder_history=history)


def compare_fine(cases,reports,endpoints,checks):
    by={r['case']['id']:r for r in reports}; comparisons=[]
    for c in cases:
        fid=c['id']
        if not c['fine']: continue
        base=fid.removesuffix('__fine')
        if fid not in endpoints or base not in endpoints:
            checks.add(fid+'/fine_present',False); continue
        first=phase_names(c)[0]
        if c['kind']!='continuation':
            checks.equal(fid+'/same_frozen_start',endpoints[fid][first][0],endpoints[base][first][0])
        common=set(endpoints[fid]) & set(endpoints[base]); phases={}
        for name in sorted(common):
            _,value,labs=endpoints[fid][name]; _,old,oldlabs=endpoints[base][name]
            phases[name]=dict(labels_agree=bool(np.array_equal(labs,oldlabs)),
                maximum_absolute_difference=float(np.max(np.abs(value-old))),
                maximum_symmetric_relative_difference=float(np.max(np.abs(value-old)/np.maximum(1,np.maximum(np.abs(value),np.abs(old))))))
        names_agree=set(endpoints[fid])==set(endpoints[base])
        same=by[fid]['rounds']==by[base]['rounds'] and by[fid]['outcomes']==by[base]['outcomes']
        agree=names_agree and same and all(p['labels_agree'] for p in phases.values())
        checks.add(fid+'/fine',agree)
        comparisons.append(dict(id=fid,baseline=base,agree=agree,phase_names_agree=names_agree,outcomes_agree=same,phases=phases))
    checks.add('fine_comparison_count',len(comparisons)==sum(c['fine'] for c in cases))
    return comparisons


def calibration_audit(run):
    run=Path(run); checks=Checks(); cases=expected_cases()[2:10]
    reports,endpoints,calls=audited_records(run,cases,checks)
    checks.add('calibration_count',len(reports)==8 and calls==24)
    fine=compare_fine(cases,reports,endpoints,checks); by={r['case']['id']:r['outcomes'] for r in reports}
    conditions=[]
    for c in cases:
        out=by.get(c['id'],{}); positive=c['founder']=='ordinary_M' and c['route']=='open'
        eligible=(out.get('retained_M_by_pupil')==[True,False,False] and
                  out.get('retained_E_by_pupil')==[False,True,True] and out.get('teachers_always_M',False)
                  and out.get('all_presignal_E',False)) if positive else out.get('all_recipient_E',False)
        conditions.append(dict(id=c['id'],eligible=bool(eligible)))
    provenance=integrity(run,json.loads((run/'summary.json').read_text()))
    quality=all(checks.rows.values()) and all(provenance.values())
    return dict(quality_gate=quality,eligible=bool(quality and all(c['eligible'] for c in conditions)),
        checks=checks.rows,integrity=provenance,branches=reports,fine_comparisons=fine,
        conditions=conditions,native_integrations=calls,negative_eligibility_is_valid=True)


def choose_schedules(by):
    """Only predeclared screen outcomes enter selection, never continuation results."""
    eligibility=[]
    def out(h,s,route,fine):
        return by.get(case_spec('screen',h,s,route,fine)['id'],{}).get('outcomes',{})
    for schedule in WINDOWS:
        shared=all(out(h,schedule,'open',f).get('all_recipient_M',False) and
                   out(h,schedule,'open',f).get('all_presignal_E',False) for h in HISTORIES for f in (False,True))
        sham=all(out('ordinary_E_sham',schedule,'open',f).get('all_recipient_E',False) for f in (False,True))
        blocked=all(out(h,schedule,r,f).get('all_recipient_E',False) for h in HISTORIES
                    for r in ('rna','cut') for f in (False,True)) if schedule=='sequential' else None
        eligibility.append(dict(schedule=schedule,both_founders_retained_M=bool(shared),sham_negative=bool(sham),
            baseline_controls_negative=blocked,eligible=bool(shared and sham and blocked is not False)))
    eligible={x['schedule'] for x in eligibility if x['eligible']}
    selected=['sequential'] if 'sequential' in eligible else []
    alternative=next((s for s in PRIORITY if s in eligible),None)
    if alternative: selected.append(alternative)
    return selected,eligibility


def screen_audit(run):
    run=Path(run); checks=Checks(); cases=expected_cases()[10:60]
    reports,endpoints,calls=audited_records(run,cases,checks)
    checks.add('screen_count',len(reports)==50 and calls==sum(len(phase_names(c)) for c in cases))
    fine=compare_fine(cases,reports,endpoints,checks)
    selected,eligibility=choose_schedules({r['case']['id']:r for r in reports})
    provenance=integrity(run,json.loads((run/'summary.json').read_text()))
    quality=all(checks.rows.values()) and all(provenance.values())
    return dict(quality_gate=quality,selected=selected if quality else [],candidate_eligibility=eligibility,
        checks=checks.rows,integrity=provenance,branches=reports,fine_comparisons=fine,native_integrations=calls,
        selection_requires_both_founders=True,no_candidate_substitution=True)


def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_contact_schedule_v1.json').read_text()))
    gate=gate_audit(run); calibration=calibration_audit(run)
    checks.add('gate/pass',gate['quality_gate']); checks.add('calibration/quality',calibration['quality_gate'])
    def saved(name,value):
        checks.add(name+'/saved',summary[name]==value==json.loads((run/(name+'.json')).read_text()) and
                   d.digest(run/(name+'.json'))==summary[name+'_sha256'])
    saved('gate',gate); saved('calibration_audit',calibration)
    screen=None; selected=[]
    if calibration['eligible']:
        screen=screen_audit(run); selected=screen['selected']; checks.add('screen/quality',screen['quality_gate'])
        saved('screen_audit',screen)
        checks.add('completion_reason',summary.get('completion_reason')==(
            'selected_continuations_completed' if selected else 'no_eligible_schedule'))
    else:
        checks.add('no_downstream_after_ineligible_graph',summary.get('screen_audit') is None and summary.get('completion_reason')=='common_graph_not_qualified')
    checks.add('selection',summary['selected']==selected)
    all_cases=expected_cases(selected); cases=all_cases if calibration['eligible'] else all_cases[:10]
    checks.add('registered_cases',summary['registered_cases']==all_cases)
    checks.add('case_set',len(summary['cases'])==len(cases) and {x['id'] for x in summary['cases']}=={c['id'] for c in cases})
    checks.add('runner',summary.get('all_execution_valid',False))
    reports,endpoints,calls=audited_records(run,cases,checks)
    checks.add('native_calls',calls==sum(len(phase_names(b['case'],len(b['rounds']))) for b in reports))
    fine=compare_fine([c for c in cases if c['kind']!='replay'],reports,endpoints,checks)
    by={b['case']['id']:b for b in reports}; contrasts=[]
    for s in selected:
        for h in HISTORIES:
            resolutions={}
            for f in (False,True):
                outcomes={r:by.get(case_spec('continuation',h,s,r,f)['id'],{}).get('outcomes',{}) for r in ('open','rna','cut')}
                qualified=outcomes['open'].get('complete_six_rounds',False) and all(
                    outcomes[r].get('new_rounds')==1 and outcomes[r].get('all_recipient_E',False) for r in ('rna','cut'))
                resolutions['fine' if f else 'coarse']=dict(outcomes=outcomes,control_qualified_renewal=bool(qualified))
            contrasts.append(dict(schedule=s,founder=h,resolutions=resolutions,
                control_qualified_in_both_resolutions=all(v['control_qualified_renewal'] for v in resolutions.values())))
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    total_rounds=sum(len(b['rounds']) for b in reports if b['case']['kind'] in ('screen','continuation'))
    return dict(run=str(run),quality_gate=quality,ready_for_interpretation=quality,independent_check_count=len(checks.rows),
        checks=checks.rows,integrity=provenance,gate=gate,calibration=calibration,screen=screen,
        branches=reports,native_integrations=calls,fine_comparisons=fine,
        all_selected_fine_agree=all(x['agree'] for x in fine),contrasts=contrasts,
        totals=dict(executed_cases=len(summary['cases']),graph_eligible=calibration['eligible'],selected_schedules=selected,
            newly_simulated_screen_and_continuation_rounds=total_rounds,new_pupils_exposed=3*total_rounds,
            control_qualified_six_round_renewals=sum(x['control_qualified_in_both_resolutions'] for x in contrasts)),
        positive_new_renewal_required=False,history_prefix_is_new_replication=False,
        independent_random_replicates=False,external_schedule=True,explicit_non_lattice_extension=True,
        autonomous_reproduction=False,clinical_therapy=False,unique_PH_demonstrated=False,automatic_follow_on=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    report=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',report)
    output={k:report[k] for k in ('quality_gate','independent_check_count','native_integrations','totals','all_selected_fine_agree')} if args.compact else report
    print(json.dumps(output,indent=2)); return 0 if report['quality_gate'] else 1


if __name__=='__main__': raise SystemExit(main())
