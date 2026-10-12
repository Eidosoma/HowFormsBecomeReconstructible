"""Independent P9 audit: state continuity, overlapping time, replacement and stop rules."""
import argparse
import itertools
import json
from pathlib import Path
import re

import numpy as np
import paper_staged_relay_design as d
import analyze_paper_m_calibration as p7
import analyze_paper_calibrated_rewrite as p8
from analyze_paper_memory import Checks,labels
from analyze_paper_restoration import stable
from analyze_paper_sheet import arrays,edges


def old_case(layout):
    return dict(id=f'capacity__{layout}__depol__high__M_open',kind='capacity',layout=layout,
                algorithm='depol',anchor='high',condition='M_open',fine=False)


def expected_cases():
    cases=[dict(id='replay__'+l,kind='replay',layout=l,source=old_case(l)['id'],fine=False)
           for l in ('three_to_one','three_to_three')]
    combinations=list(itertools.product(('rewritten_ordinary_E','rewritten_restored_E','ordinary_M'),
        ('sequential','simultaneous_20','simultaneous_60','sequential_rna','sequential_cut')))
    combinations.append(('ordinary_E_sham','sequential'))
    for fine in (False,True):
        for founder,condition in combinations:
            cases.append(dict(id=f'relay__{founder}__{condition}'+('__fine' if fine else ''),
                kind='relay',founder=founder,condition=condition,fine=fine))
    return cases


def round_phase_names(case,number):
    parts=(['contact_1','contact_2','waiting_2','contact_3','waiting_3']
           if case['condition'].startswith('sequential') else
           ['contact','waiting'] if case['condition']=='simultaneous_20' else ['contact'])
    return [f'r{number:02d}_'+p for p in parts+['isolated_1','isolated_2']]


def phase_names(case,rounds=6):
    if case['kind']=='replay': return ['contact','isolated_1','isolated_2']
    return [p for n in range(1,rounds+1) for p in round_phase_names(case,n)]


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


def founder_ids(case):
    if case['founder'].startswith('rewritten_'): return [f'relay:06:{i:02d}' for i in range(3)]
    return [f'founder:{"E" if case["founder"]=="ordinary_E_sham" else "M"}:{i:02d}' for i in range(3)]


def parts(case,name):
    match=re.fullmatch(r'r([0-9]{2})_(.+)',name)
    if not match: raise ValueError('Unknown P9 phase')
    number=int(match[1]); part=match[2]
    if not 1<=number<=6 or name not in round_phase_names(case,number): raise ValueError('Unregistered P9 phase')
    return number,part


def geometry(case,name):
    number,part=parts(case,name)
    teachers=founder_ids(case) if number==1 else [f'pupil:{number-1:02d}:{i:02d}' for i in range(3)]
    pupils=[f'pupil:{number:02d}:{i:02d}' for i in range(3)]
    if part.startswith('contact_'): return [2,2],teachers+[pupils[int(part[-1])-1]]
    if part=='contact': return [2,3],teachers+pupils
    if part.startswith('waiting_'):
        count=int(part[-1])-1; return [1,count],pupils[:count]
    return [1,3],pupils


def settings(case,name):
    _,part=parts(case,name); contact=part.startswith('contact')
    horizon=60000 if part=='contact' and case['condition']=='simultaneous_60' else (
        10000 if part.startswith('isolated') else 40000 if part=='waiting' else 20000)
    return 'depol',60 if contact else 1,1.25e-14 if contact and case['condition']!='sequential_rna' else 0,not contact,horizon


def logical_interval(case,name):
    number,part=parts(case,name); base=(number-1)*80000
    if part.startswith('contact_') or part.startswith('waiting_'): start=(int(part[-1])-1)*20000
    elif part=='waiting': start=20000
    elif part.startswith('isolated'): start=60000 if part.endswith('1') else 70000
    else: start=0
    return [base+start,base+start+settings(case,name)[-1]]


def regional_settings(case,name):
    shape,_=geometry(case,name); fr,to=edges(shape); contact=parts(case,name)[1].startswith('contact')
    member={0,1,2} if contact else set()
    regions=np.array([1 if f in member and t in member else
        2 if (f in member)!=(t in member) else 0 for f,t in zip(fr,to)],dtype=np.int8)
    power=60 if contact else 1; cut=contact and case['condition']=='sequential_cut'
    available=np.array([0. if x==2 and cut else 1. for x in regions])
    return regions,np.full(len(regions),power,dtype=float),available,dict(
        internal=power,boundary=power,helper=power,boundary_cut=cut)


def audit_phase(folder,case,rec,idx,checks):
    name=rec['phase']; ck=lambda n,v:checks.add(case['id']+'/'+name+'/'+n,v)
    ck('hash',d.digest(folder/(name+'.npz'))==rec['sha256']); a=arrays(folder,name)
    shape,ids=geometry(case,name); algo,power,kd,iso,horizon=settings(case,name)
    count=len(ids); setup=rec['setup']; fr,to=edges(shape)
    regions,powers,available,compartments=regional_settings(case,name)
    ck('compartments',setup['compartment_expression']==compartments)
    for side in ('initial','final'):
        for k,v in (('region',regions),('power',powers),('available',available)):
            ck('edge_'+k+'_'+side,np.array_equal(a['edge_'+k+'_'+side],v))
    ck('shape',a['initial'].shape==a['final'].shape==(17,count) and a['concentrations'].shape[1:]==(17,count))
    ck('ids',setup['cell_ids']==ids and len(set(ids))==count and setup['cells']==count)
    ck('geometry',setup['grid_shape']==shape and setup['orthogonal_only'] is True and setup['periodic'] is False)
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
    x=arrays(run/'inputs/p8/inputs/p7/inputs/p3/reference','preparation')
    return x['concentrations'][-1,:,168:169],x['concentrations'][-1,:,1:2],x['environment']


def founder_source(run,case,E,M):
    h=case['founder']
    if h.startswith('rewritten_'):
        return arrays(run/'inputs/p8'/('rewrite__'+h.removeprefix('rewritten_')+'__M_open'),'writing_isolated_2')['final']
    return np.repeat(E if h=='ordinary_E_sham' else M,3,axis=1)


def branch(folder,case,checks):
    run=folder.parent; result=json.loads((folder/'result.json').read_text())
    ck=lambda n,v:checks.add(case['id']+'/'+n,v); eq=lambda n,x,y:checks.equal(case['id']+'/'+n,x,y)
    ck('case',result['case']==case and result['execution_pass'])
    ck('scope',not any(result[k] for k in ('teachers_retained_between_rounds','waiting_cells_frozen',
        'parameter_retuning','outcome_dependent_cell_selection','cell_division_simulated',
        'extra_M_supplementation','cross_branch_pooling','founder_prefix_is_new_replication',
        'stress_panel','automatic_follow_on')) and result['external_handover_schedule'] and result['registered_stop_on_incomplete'])
    idx=result['ion_indices']; ck('indices',idx==dict(Na=0,K=1,Cl=2,P=3,snail=4,miR200_total=5,
        Zeb_mRNA_total=6,ZEB_prot=7,miR200_free=8,**{f'bound{i}':9+i for i in range(7)},ST=16))
    rounds=[]
    if case['kind']=='replay':
        ck('phase_list',[p['phase'] for p in result['phases']]==phase_names(case))
        ck('replay_scope',result['rounds']==[] and result['newly_simulated_rounds']==0 and
            result['unattempted_rounds']==0 and result['stop_reason']=='historical_replay' and not result['donor_reuse_within_round'])
        old=old_case(case['layout']); source=run/'inputs/p8/inputs/p7'/old['id']; data={}
        for rec in result['phases']:
            name=rec['phase']; local=Checks(); data[name]=p7.audit_phase(folder,old,rec,idx,local)
            for key,value in local.rows.items(): ck('native/'+key,value)
            original=arrays(source,name); ck('replay/'+name+'/keys',set(data[name])==set(original))
            for key,value in original.items(): eq('replay/'+name+'/'+key,data[name][key],value)
        _,nd,_=p7.layout(old)
        out=p7.outcome(data['contact'],data['isolated_1'],data['isolated_2'],idx,nd)
    else:
        nrounds=len(result['rounds']); ck('round_count',1<=nrounds<=6 and result['newly_simulated_rounds']==nrounds)
        ck('phase_list',[p['phase'] for p in result['phases']]==phase_names(case,nrounds))
        ck('teacher_reuse',result['donor_reuse_within_round']==case['condition'].startswith('sequential'))
        data={p['phase']:audit_phase(folder,case,p,idx,checks) for p in result['phases']}
        E,M,bath=stock(run); carry=founder_source(run,case,E,M)
        for name,value in data.items(): eq('bath/'+name,value['environment'],bath)
        first=round_phase_names(case,1)[0]
        eq('founder_labels',labels(data[first]['initial'][:,:3],idx),list('EEE' if case['founder']=='ordinary_E_sham' else 'MMM'))
        for number in range(1,nrounds+1):
            prefix=f'r{number:02d}_'; contacts=[]; teachers=carry.copy(); pupils=np.empty((17,0)); pupil_contact=[]; waiting=[]
            if case['condition'].startswith('sequential'):
                for slot in range(3):
                    name=prefix+f'contact_{slot+1}'; c=data[name]
                    eq(name+'/live_teachers',c['initial'][:,:3],teachers)
                    eq(name+'/fresh_E',c['initial'][:,3:4],E)
                    eq(name+'/fresh_E_label',labels(c['initial'][:,3:4],idx),['E'])
                    teachers=c['final'][:,:3].copy()
                    contacts.append(dict(slot=slot+1,start=''.join(labels(c['initial'][:,:3],idx)),
                                         end=''.join(labels(teachers,idx))))
                    pupil_contact.extend(labels(c['final'][:,3:4],idx))
                    if slot:
                        wait_name=prefix+f'waiting_{slot+1}'; wait=data[wait_name]
                        eq(wait_name+'/live_waiting_pupils',wait['initial'],pupils); pupils=wait['final']
                        waiting.append(dict(phase=wait_name,pupil_slots=list(range(slot)),
                            initial_labels=''.join(labels(wait['initial'],idx)),final_labels=''.join(labels(wait['final'],idx))))
                    pupils=np.concatenate((pupils,c['final'][:,3:4]),axis=1)
            else:
                name=prefix+'contact'; c=data[name]
                eq(name+'/live_teachers',c['initial'][:,:3],teachers)
                eq(name+'/fresh_E',c['initial'][:,3:],np.repeat(E,3,axis=1))
                eq(name+'/fresh_E_labels',labels(c['initial'][:,3:],idx),list('EEE'))
                contacts.append(dict(slot=1,start=''.join(labels(c['initial'][:,:3],idx)),
                                     end=''.join(labels(c['final'][:,:3],idx))))
                pupils=c['final'][:,3:]; pupil_contact=list(labels(pupils,idx))
                if case['condition']=='simultaneous_20':
                    wait=data[prefix+'waiting']; eq(prefix+'waiting/live_pupils',wait['initial'],pupils); pupils=wait['final']
                    waiting.append(dict(phase=prefix+'waiting',pupil_slots=[0,1,2],
                        initial_labels=''.join(labels(wait['initial'],idx)),final_labels=''.join(labels(wait['final'],idx))))
            one,two=data[prefix+'isolated_1'],data[prefix+'isolated_2']
            eq(prefix+'all_teachers_removed_all_pupils_kept',one['initial'],pupils)
            eq(prefix+'hold_continuity',two['initial'],one['final']); carry=two['final']
            m,e=stable(one,two,idx,'M'),stable(one,two,idx,'E')
            report=dict(round=number,teacher_contacts=contacts,pupil_waiting=waiting,pupil_contact_labels=''.join(pupil_contact),
                pupil_before_holds_labels=''.join(labels(one['initial'],idx)),pupil_final_labels=''.join(labels(two['final'],idx)),
                retained_M=int(m.sum()),retained_E=int(e.sum()),retained_M_by_pupil=m.tolist(),retained_E_by_pupil=e.tolist(),
                contact_M_not_retained=int(((np.array(pupil_contact)=='M') & ~m).sum()),
                all_recipient_M=bool(m.all()),all_recipient_E=bool(e.all()),partial_M=bool(0<m.sum()<3),logical_end=number*80000)
            rounds.append(report)
            ck(prefix+'record',result['rounds'][number-1]==dict(round=number,retained_M=m.tolist(),complete=bool(m.all()),logical_end=number*80000))
        failed=[x['round'] for x in rounds if not x['all_recipient_M']]
        complete=nrounds==6 and not failed
        ck('stop_at_first_failure',not failed and nrounds==6 or failed==[nrounds])
        ck('stop_reason',result['stop_reason']==('six_complete_rounds' if complete else 'first_incomplete_round'))
        ck('unattempted_rounds',result['unattempted_rounds']==6-nrounds)
        out=dict(complete_six_rounds=complete,successful_rounds=nrounds-int(bool(failed)),
            completed_rounds=nrounds,first_incomplete_round=failed[0] if failed else None,
            unattempted_rounds=6-nrounds,final_retained_M=rounds[-1]['retained_M'],
            newly_exposed_pupils=3*nrounds,all_pupils_E_in_first_round=rounds[0]['all_recipient_E'])
        if case['founder']=='ordinary_M' and not case['fine'] and case['condition'] in ('sequential','simultaneous_20'):
            layout='three_to_one' if case['condition']=='sequential' else 'three_to_three'
            original=arrays(run/'inputs/p8/inputs/p7'/old_case(layout)['id'],'contact'); current=data[first]
            ck('P7_first_contact/keys',set(current)==set(original))
            for key,value in original.items(): eq('P7_first_contact/'+key,current[key],value)
        if case['founder'].startswith('rewritten_') and not case['fine'] and case['condition']=='sequential':
            source='rewrite__'+case['founder'].removeprefix('rewritten_')+'__M_open'
            original=arrays(run/'inputs/p8'/source,'probe_contact'); current=data[first]
            ck('P8_first_contact/keys',set(current)==set(original))
            for key,value in original.items(): eq('P8_first_contact/'+key,current[key],value)
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
    saved=json.loads((run/'inputs/p8/independent_audit.json').read_text())
    checks.add('P8_saved_pass',saved['quality_gate'] and saved['independent_check_count']==16949 and saved['native_integrations']==351)
    prior=json.loads((run/'inputs/p8/summary.json').read_text()); histories=[]
    for h in ('ordinary_E','restored_E'):
        ident='rewrite__'+h+'__M_open'; folder=run/'inputs/p8'/ident
        old=next(c for c in p8.expected_cases() if c['id']==ident); record=next(c for c in prior['cases'] if c['id']==ident)
        checks.add('P8/'+ident+'/frozen',record['execution_pass'] and d.digest(folder/'result.json')==record['result_sha256'] and
                   json.loads((folder/'result.json').read_text())==record['result'])
        local=Checks(); report,data,idx=p8.branch(folder,old,local)
        for k,v in local.rows.items(): checks.add('P8/'+k,v)
        checks.add('P8/'+ident+'/qualified_source',report['outcomes']['complete_rewriting_and_transfer'])
        info=record['result']; ids=next(p['setup']['cell_ids'] for p in info['phases'] if p['phase']=='writing_isolated_2')
        checks.equal('P8/'+ident+'/founder_ids',ids,[f'relay:06:{i:02d}' for i in range(3)])
        checks.add('P8/'+ident+'/retained_all_M',stable(data['writing_isolated_1'],data['writing_isolated_2'],idx,'M').all())
        histories.append(report)
    original=json.loads((run/'inputs/p8/inputs/p7/summary.json').read_text()); archived=[]
    for case in expected_cases()[:2]:
        old=old_case(case['layout']); folder=run/'inputs/p8/inputs/p7'/old['id']
        rec=next(x for x in original['cases'] if x['id']==old['id'])
        checks.add('P7/'+old['id']+'/frozen',rec['execution_pass'] and d.digest(folder/'result.json')==rec['result_sha256'] and
                   json.loads((folder/'result.json').read_text())==rec['result'])
        local=Checks(); report,_,_=p7.branch(folder,old,local)
        for k,v in local.rows.items(): checks.add('P7/'+k,v)
        key='all_recipient_M' if case['layout']=='three_to_one' else 'all_recipient_E'
        checks.add('P7/'+old['id']+'/known_outcome',report['outcomes'][key]); archived.append(report)
    reports,_,calls=audited_records(run,expected_cases()[:2],checks)
    checks.add('replay_count',len(reports)==2 and calls==6)
    provenance=integrity(run,summary)
    return dict(quality_gate=all(checks.rows.values()) and all(provenance.values()),checks=checks.rows,
                integrity=provenance,branches=reports,historical_branches=archived,founder_histories=histories)


def qualify(conditions,sham):
    if not conditions.get('sequential',{}).get('complete_six_rounds',False): return False
    if not sham.get('all_pupils_E_in_first_round',False) or sham.get('completed_rounds')!=1: return False
    return all(conditions.get(c,{}).get('all_pupils_E_in_first_round',False) and
               conditions[c].get('completed_rounds')==1 for c in ('sequential_rna','sequential_cut'))


def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks(); cases=expected_cases()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_staged_relay_v1.json').read_text()))
    checks.add('registered_cases',summary['registered_cases']==cases)
    checks.add('case_set',len(summary['cases'])==34 and {x['id'] for x in summary['cases']}=={c['id'] for c in cases})
    checks.add('runner',summary.get('all_execution_valid',False))
    reports,endpoints,calls=audited_records(run,cases,checks)
    expected_calls=sum(len(phase_names(x['case'],len(x['rounds']))) for x in reports)
    checks.add('native_calls',calls==expected_calls and 188<=calls<=1098)
    gate=gate_audit(run); checks.add('gate/pass',gate['quality_gate'])
    checks.add('gate/saved',summary['gate']==gate==json.loads((run/'gate.json').read_text()) and d.digest(run/'gate.json')==summary['gate_sha256'])
    by={b['case']['id']:b for b in reports}; fine=[]
    for c in cases:
        fid=c['id']
        if not c['fine'] or fid not in endpoints: continue
        base=fid.removesuffix('__fine')
        if base not in endpoints: checks.add(fid+'/base_present',False); continue
        first=round_phase_names(c,1)[0]; checks.equal(fid+'/same_frozen_start',endpoints[fid][first][0],endpoints[base][first][0])
        common=set(endpoints[fid]) & set(endpoints[base]); phases={}
        for name in sorted(common):
            _,value,labs=endpoints[fid][name]; _,old,oldlabs=endpoints[base][name]
            phases[name]=dict(labels_agree=bool(np.array_equal(labs,oldlabs)),
                maximum_absolute_difference=float(np.max(np.abs(value-old))),
                maximum_symmetric_relative_difference=float(np.max(np.abs(value-old)/np.maximum(1,np.maximum(np.abs(value),np.abs(old))))))
        names_agree=set(endpoints[fid])==set(endpoints[base])
        same=by[fid]['rounds']==by[base]['rounds'] and by[fid]['outcomes']==by[base]['outcomes']
        agree=names_agree and same and all(p['labels_agree'] for p in phases.values())
        checks.add(fid+'/fine',agree); fine.append(dict(id=fid,baseline=base,agree=agree,phase_names_agree=names_agree,outcomes_agree=same,phases=phases))
    checks.add('all_sixteen_finer',len(fine)==16); fine_by={x['baseline']:x for x in fine}
    sham_id='relay__ordinary_E_sham__sequential'
    sham=by.get(sham_id,{}).get('outcomes',{}); fsham=by.get(sham_id+'__fine',{}).get('outcomes',{})
    contrasts=[]
    for h in ('rewritten_ordinary_E','rewritten_restored_E','ordinary_M'):
        prefix='relay__'+h+'__'; conditions=('sequential','simultaneous_20','simultaneous_60','sequential_rna','sequential_cut')
        coarse={c:by[prefix+c]['outcomes'] for c in conditions if prefix+c in by}
        refined={c:by[prefix+c+'__fine']['outcomes'] for c in conditions if prefix+c+'__fine' in by}
        agree=all(fine_by.get(prefix+c,{}).get('agree',False) for c in conditions) and fine_by.get(sham_id,{}).get('agree',False)
        contrasts.append(dict(founder=h,conditions=coarse,fine_conditions=refined,fine_agreement=agree,
            control_qualified_renewal=bool(qualify(coarse,sham) and qualify(refined,fsham) and agree)))
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    main=[b for b in reports if b['case']['kind']=='relay' and not b['case']['fine'] and
          b['case']['condition']=='sequential' and b['case']['founder']!='ordinary_E_sham']
    return dict(run=str(run),quality_gate=quality,ready_for_interpretation=quality,independent_check_count=len(checks.rows),
        checks=checks.rows,integrity=provenance,gate=gate,branches=reports,native_integrations=calls,
        fine_comparisons=fine,all_selected_fine_agree=len(fine)==16 and all(x['agree'] for x in fine),contrasts=contrasts,
        totals=dict(main_founders=len(main),main_six_round_renewals=sum(x['outcomes']['complete_six_rounds'] for x in main),
            main_successful_rounds={x['case']['founder']:x['outcomes']['successful_rounds'] for x in main},
            control_qualified_founders=[x['founder'] for x in contrasts if x['control_qualified_renewal']],
            new_handover_rounds=sum(len(b['rounds']) for b in reports),
            new_pupils_exposed=sum(3*len(b['rounds']) for b in reports)),
        ordinary_E_sham=sham,positive_new_renewal_required=False,
        stop_on_first_incomplete_is_preregistered=True,history_prefix_is_new_replication=False,
        independent_random_replicates=False,external_schedule=True,autonomous_reproduction=False,
        clinical_therapy=False,unique_PH_demonstrated=False,automatic_follow_on=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    report=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',report)
    output={k:report[k] for k in ('quality_gate','independent_check_count','native_integrations','totals','all_selected_fine_agree')} if args.compact else report
    print(json.dumps(output,indent=2)); return 0 if report['quality_gate'] else 1


if __name__=='__main__': raise SystemExit(main())
