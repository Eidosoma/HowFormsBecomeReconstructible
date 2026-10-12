"""Independent P8 audit: actual lineage targets, cue removal and one fresh probe."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import paper_calibrated_rewrite_design as d
import analyze_paper_m_calibration as p7
import analyze_paper_relay as p5
from analyze_paper_memory import Checks,labels
from analyze_paper_restoration import stable
from analyze_paper_sheet import arrays,edges


def old_case(layout):
    return dict(id=f'capacity__{layout}__depol__high__M_open',kind='capacity',layout=layout,
                algorithm='depol',anchor='high',condition='M_open',fine=False)


def expected_cases():
    cases=[dict(id='replay__'+l,kind='replay',layout=l,source=old_case(l)['id'],fine=False)
           for l in ('six_to_three','three_to_one','three_to_three')]
    cases += [dict(id='age__E'+('__fine' if f else ''),kind='age',fine=f) for f in (False,True)]
    cases += [dict(id=f'rewrite__{h}__{c}'+('__fine' if f else ''),kind='rewrite',background=h,condition=c,fine=f)
        for f,h,c in itertools.product((False,True),('fresh_E','aged_E','ordinary_E','restored_E'),
            ('M_open','E_sham','M_write_rna','M_write_cut','no_cue','M_probe_rna','M_probe_cut'))]
    return cases


def phase_names(case):
    if case['kind']=='replay': return ['contact','isolated_1','isolated_2']
    if case['kind']=='age': return ['age_1','age_2','age_3']
    return [stage+'_'+part for stage in ('writing','probe') for part in ('contact','isolated_1','isolated_2')]


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


def target_ids(case):
    if case['kind']=='age' or case.get('background')=='aged_E': return [f'aged:{i:02d}' for i in range(3)]
    if case['background']=='fresh_E': return [f'target:fresh:{i:02d}' for i in range(3)]
    return [f'relay:06:{i:02d}' for i in range(3)]


def geometry(case,name):
    ids=target_ids(case)
    if case['kind']=='age': return [1,3],ids
    if name=='writing_contact' and case['condition']!='no_cue': return [3,3],[f'cue:{i:02d}' for i in range(6)]+ids
    if name.startswith('writing'): return [1,3],ids
    return ([2,2],ids+['probe:00']) if name=='probe_contact' else ([1,1],['probe:00'])


def settings(case,name):
    if case['kind']=='age': return 'depol',1,0,True,20000 if name=='age_1' else 10000
    if name=='writing_contact':
        c=case['condition']; return 'depol',60,0 if c in ('M_write_rna','no_cue') else 1.25e-14,c=='no_cue',20000
    if name=='probe_contact': return 'depol',60,0 if case['condition']=='M_probe_rna' else 1.25e-14,False,20000
    return 'depol',1,0,True,10000


def regional_settings(case,name):
    shape,_=geometry(case,name); fr,to=edges(shape)
    if name=='writing_contact' and case['condition']!='no_cue': member=set(range(6))
    elif name=='probe_contact': member=set(range(3))
    else: member=set()
    regions=np.array([1 if f in member and t in member else
        2 if (f in member)!=(t in member) else 0 for f,t in zip(fr,to)],dtype=np.int8)
    power=60 if name.endswith('_contact') else 1
    cut=(name=='writing_contact' and case.get('condition')=='M_write_cut') or (
        name=='probe_contact' and case.get('condition')=='M_probe_cut')
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
    a=arrays(run/'inputs/p7/inputs/p3/reference','preparation')
    return a['concentrations'][-1,:,168:169],a['concentrations'][-1,:,1:2],a['environment']


def target_source(run,case,E):
    h=case['background']
    if h=='fresh_E': return np.repeat(E,3,axis=1)
    if h=='aged_E': return arrays(run/('age__E'+('__fine' if case['fine'] else '')),'age_3')['final']
    return arrays(run/'inputs/p5'/('relay__'+h+'__open'),'r06_isolated_2')['final']


def branch(folder,case,checks):
    run=folder.parent; result=json.loads((folder/'result.json').read_text())
    ck=lambda n,v:checks.add(case['id']+'/'+n,v); eq=lambda n,x,y:checks.equal(case['id']+'/'+n,x,y)
    ck('case',result['case']==case and result['execution_pass'])
    ck('scope',not any(result[k] for k in ('parameter_retuning','outcome_dependent_selection',
        'cell_division_simulated','artificial_target_schedule','cue_cells_retained','serial_relay',
        'stress_panel','return_to_E','automatic_follow_on')) and result['external_handover_schedule'])
    ck('history_counts',result['historical_rounds']==(6 if case.get('background') in ('ordinary_E','restored_E') else 0) and
        result['newly_simulated_writing_events']==int(case['kind']=='rewrite') and
        result['new_onward_handovers']==int(case['kind']=='rewrite'))
    idx=result['ion_indices']; ck('indices',idx==dict(Na=0,K=1,Cl=2,P=3,snail=4,miR200_total=5,
        Zeb_mRNA_total=6,ZEB_prot=7,miR200_free=8,**{f'bound{i}':9+i for i in range(7)},ST=16))
    ck('phase_list',[p['phase'] for p in result['phases']]==phase_names(case))
    writing=probe=None
    if case['kind']=='replay':
        old=old_case(case['layout']); data={}; source=run/'inputs/p7'/old['id']
        for rec in result['phases']:
            name=rec['phase']; local=Checks(); data[name]=p7.audit_phase(folder,old,rec,idx,local)
            for k,v in local.rows.items(): ck('native/'+k,v)
            original=arrays(source,name); ck('replay/'+name+'/keys',set(data[name])==set(original))
            for key,value in original.items(): eq('replay/'+name+'/'+key,data[name][key],value)
        _,nd,_=p7.layout(old)
        out=p7.outcome(data['contact'],data['isolated_1'],data['isolated_2'],idx,nd)
    else:
        data={p['phase']:audit_phase(folder,case,p,idx,checks) for p in result['phases']}
        E,M,bath=stock(run)
        for name,value in data.items(): eq('common_bath/'+name,value['environment'],bath)
        if case['kind']=='age':
            one,two,three=[data[n] for n in phase_names(case)]
            eq('fresh_E_start',one['initial'],np.repeat(E,3,axis=1))
            eq('age_continuity_2',two['initial'],one['final']); eq('age_continuity_3',three['initial'],two['final'])
            e,m=stable(two,three,idx,'E'),stable(two,three,idx,'M')
            out=dict(final_labels=''.join(labels(three['final'],idx)),retained_E=int(e.sum()),
                retained_M=int(m.sum()),all_E=bool(e.all()),additional_elapsed_units=40000)
        else:
            contact,one,two=[data['writing_'+n] for n in ('contact','isolated_1','isolated_2')]
            nocue=case['condition']=='no_cue'; start=0 if nocue else 6
            source=target_source(run,case,E)
            eq('actual_target_start',contact['initial'][:,start:],source)
            eq('targets_start_E',labels(contact['initial'],idx)[start:],list('EEE'))
            if not nocue:
                cue=E if case['condition']=='E_sham' else M
                eq('fresh_cue_stock',contact['initial'][:,:6],np.repeat(cue,6,axis=1))
                eq('cue_start_labels',labels(contact['initial'],idx)[:6],list(('E' if case['condition']=='E_sham' else 'M')*6))
            eq('all_cues_removed_targets_retained',one['initial'],contact['final'][:,start:])
            eq('writing_hold_continuity',two['initial'],one['final'])
            e,m=stable(one,two,idx,'E'),stable(one,two,idx,'M')
            writing=dict(target_start_labels=''.join(labels(contact['initial'],idx)[start:]),
                target_contact_labels=''.join(labels(contact['final'],idx)[start:]),
                cue_contact_labels=''.join(labels(contact['final'],idx)[:start]),
                target_final_labels=''.join(labels(two['final'],idx)),retained_E=int(e.sum()),retained_M=int(m.sum()),
                all_targets_E=bool(e.all()),all_targets_M=bool(m.all()),partial_M=bool(0<m.sum()<3))
            pc,po,pt=[data['probe_'+n] for n in ('contact','isolated_1','isolated_2')]
            eq('probe_actual_held_targets',pc['initial'][:,:3],two['final'])
            eq('probe_fresh_E',pc['initial'][:,3:4],E); eq('probe_starts_E',labels(pc['initial'],idx)[3:],['E'])
            eq('probe_remove_all_targets',po['initial'],pc['final'][:,3:4])
            eq('probe_hold_continuity',pt['initial'],po['final'])
            probe=p7.outcome(pc,po,pt,idx,3)
            out=dict(complete_M_rewriting=writing['all_targets_M'],onward_M_acquisition=probe['all_recipient_M'],
                complete_rewriting_and_transfer=bool(writing['all_targets_M'] and probe['all_recipient_M']),
                partial_rewriting=writing['partial_M'])
            if case['background']=='fresh_E' and case['condition']=='M_open' and not case['fine']:
                for name in ('contact','isolated_1','isolated_2'):
                    original=arrays(run/'inputs/p7/capacity__six_to_three__depol__high__M_open',name)
                    current=data['writing_'+name]; ck('P7_matched/'+name+'/keys',set(current)==set(original))
                    for key,value in original.items(): eq('P7_matched/'+name+'/'+key,current[key],value)
    return dict(case=case,writing=writing,probe=probe,outcomes=out),data,idx


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


def historical_lineages(run,checks):
    original=json.loads((run/'inputs/p5/summary.json').read_text())
    saved=json.loads((run/'inputs/p5/independent_audit.json').read_text()); E,M,bath=stock(run)
    prior=arrays(run/'inputs/p5/inputs/p4_inputs/reference','preparation')
    checks.equal('p5/same_stock',prior['concentrations'][-1],arrays(run/'inputs/p7/inputs/p3/reference','preparation')['concentrations'][-1])
    checks.equal('p5/same_bath',prior['environment'],bath); reports=[]
    for h in ('ordinary_E','restored_E'):
        ident='relay__'+h+'__open'; folder=run/'inputs/p5'/ident
        case=next(c for c in p5.expected_cases() if c['id']==ident)
        rec=next(r for r in original['cases'] if r['id']==ident); result=json.loads((folder/'result.json').read_text())
        ck=lambda n,v:checks.add('p5/'+ident+'/'+n,v); eq=lambda n,x,y:checks.equal('p5/'+ident+'/'+n,x,y)
        ck('result',rec['execution_pass'] and rec['result']==result and d.digest(folder/'result.json')==rec['result_sha256'])
        ck('case',result['case']==case and result['execution_pass']); idx=result['ion_indices']
        names=['r05_isolated_2','r06_contact','r06_isolated_1','r06_isolated_2']; data={}
        for name in names:
            phase=next(p for p in result['phases'] if p['phase']==name); local=Checks()
            data[name]=p5.audit_phase(folder,case,phase,idx,local)
            for k,v in local.rows.items(): ck('native/'+k,v)
            eq('common_bath/'+name,data[name]['environment'],bath)
        contact,one,two=[data[n] for n in names[1:]]
        eq('actual_round_five_input',contact['initial'][:,:3],data['r05_isolated_2']['final'])
        eq('fresh_round_six_M',contact['initial'][:,3:],np.repeat(M,3,axis=1))
        eq('remove_round_five',one['initial'],contact['final'][:,3:])
        eq('round_six_hold_continuity',two['initial'],one['final'])
        ck('round_six_retained_E',stable(one,two,idx,'E').all())
        report=next(b for b in saved['branches'] if b['case']['id']==ident)
        ck('six_recorded_E_rounds',[r['round'] for r in report['rounds'][:6]]==list(range(1,7)) and
            all(r['all_recipient_E'] for r in report['rounds'][:6]))
        reports.append(dict(ancestry=h,source=ident,source_round=6,retained_E=3,cell_elapsed_units=40000))
    return reports


def gate_audit(run):
    run=Path(run); checks=Checks(); summary=json.loads((run/'summary.json').read_text())
    checks.add('predecessor_gate',summary['predecessor_gate'])
    for key,n,calls in (('p7',14506,295),('p5',42065,804)):
        old=json.loads((run/'inputs'/key/'independent_audit.json').read_text())
        checks.add(key+'/predecessor_record',old['quality_gate'] and old['independent_check_count']==n and old['native_integrations']==calls)
    archived=[]; original=json.loads((run/'inputs/p7/summary.json').read_text())
    for case in expected_cases()[:3]:
        old=old_case(case['layout']); folder=run/'inputs/p7'/old['id']
        rec=next(r for r in original['cases'] if r['id']==old['id'])
        checks.add(old['id']+'/source_record',rec['execution_pass'] and d.digest(folder/'result.json')==rec['result_sha256'] and
            json.loads((folder/'result.json').read_text())==rec['result'])
        local=Checks(); report,_,_=p7.branch(folder,old,local)
        for k,v in local.rows.items(): checks.add('p7/history/'+k,v)
        target='all_recipient_E' if case['layout']=='three_to_three' else 'all_recipient_M'
        checks.add(old['id']+'/known_outcome',report['outcomes'][target]); archived.append(report)
    histories=historical_lineages(run,checks)
    reports,_,calls=audited_records(run,expected_cases()[:3],checks)
    checks.add('replay_counts',len(reports)==3 and calls==9); provenance=integrity(run,summary)
    return dict(quality_gate=all(checks.rows.values()) and all(provenance.values()),checks=checks.rows,
        integrity=provenance,branches=reports,historical_branches=archived,lineage_sources=histories)


def age_gate_audit(run):
    run=Path(run); checks=Checks(); summary=json.loads((run/'summary.json').read_text())
    checks.add('replay_gate',bool((summary.get('gate') or {}).get('quality_gate')))
    reports,_,calls=audited_records(run,expected_cases()[3:5],checks)
    checks.add('age_counts',len(reports)==2 and calls==6)
    for b in reports: checks.add(b['case']['id']+'/eligible_E',b['outcomes']['all_E'])
    if len(reports)==2: checks.add('age_fine_outcomes',reports[0]['outcomes']==reports[1]['outcomes'])
    provenance=integrity(run,summary)
    return dict(quality_gate=all(checks.rows.values()) and all(provenance.values()),checks=checks.rows,integrity=provenance,branches=reports)


def qualify(conditions):
    required={'M_open','E_sham','M_write_rna','M_write_cut','no_cue','M_probe_rna','M_probe_cut'}
    if set(conditions)!=required or not conditions['M_open']['outcomes']['complete_rewriting_and_transfer']: return False
    for c in ('E_sham','M_write_rna','M_write_cut','no_cue'):
        if not (conditions[c]['writing']['all_targets_E'] and conditions[c]['probe']['all_recipient_E']): return False
    return all(conditions[c]['writing']['all_targets_M'] and conditions[c]['probe']['all_recipient_E']
               for c in ('M_probe_rna','M_probe_cut'))


def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks(); cases=expected_cases()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_calibrated_rewrite_v1.json').read_text()))
    checks.add('registered_cases',summary['registered_cases']==cases)
    checks.add('case_set',len(summary['cases'])==61 and {r['id'] for r in summary['cases']}=={c['id'] for c in cases})
    checks.add('runner',summary.get('all_execution_valid',False))
    reports,endpoints,calls=audited_records(run,cases,checks); checks.add('native_calls',calls==351)
    gates={}
    for key,fun in (('gate',gate_audit),('age_gate',age_gate_audit)):
        gate=fun(run); checks.add(key+'/pass',gate['quality_gate']); gates[key]=gate
        checks.add(key+'/saved',summary[key]==gate==json.loads((run/(key+'.json')).read_text()) and
            d.digest(run/(key+'.json'))==summary[key+'_sha256'])
    by={b['case']['id']:b for b in reports}; fine=[]
    for c in cases:
        fid=c['id']
        if not c['fine'] or fid not in endpoints: continue
        base=fid.removesuffix('__fine')
        if base not in endpoints: checks.add(fid+'/base_present',False); continue
        phases={}
        if c.get('background')!='aged_E':
            first=phase_names(c)[0]; checks.equal(fid+'/same_start',endpoints[fid][first][0],endpoints[base][first][0])
        for name,(_,value,labs) in endpoints[fid].items():
            _,old,oldlabs=endpoints[base][name]
            phases[name]=dict(labels_agree=bool(np.array_equal(labs,oldlabs)),
                maximum_absolute_difference=float(np.max(np.abs(value-old))),
                maximum_symmetric_relative_difference=float(np.max(np.abs(value-old)/np.maximum(1,np.maximum(np.abs(value),np.abs(old))))))
        same=all(by[fid][k]==by[base][k] for k in ('writing','probe','outcomes'))
        agree=same and all(p['labels_agree'] for p in phases.values()); checks.add(fid+'/fine',agree)
        fine.append(dict(id=fid,baseline=base,outcomes_agree=same,agree=agree,phases=phases))
    checks.add('all_twenty_nine_finer',len(fine)==29); fine_by={r['baseline']:r for r in fine}
    contrasts=[]; conditions=('M_open','E_sham','M_write_rna','M_write_cut','no_cue','M_probe_rna','M_probe_cut')
    for h in ('fresh_E','aged_E','ordinary_E','restored_E'):
        prefix='rewrite__'+h+'__'
        coarse={c:{k:by[prefix+c][k] for k in ('writing','probe','outcomes')} for c in conditions if prefix+c in by}
        refined={c:{k:by[prefix+c+'__fine'][k] for k in ('writing','probe','outcomes')} for c in conditions if prefix+c+'__fine' in by}
        agree=all(fine_by.get(prefix+c,{}).get('agree',False) for c in conditions)
        contrasts.append(dict(background=h,conditions=coarse,fine_conditions=refined,fine_agreement=agree,
            control_qualified_chain=bool(qualify(coarse) and qualify(refined) and agree)))
        for suffix in ('','__fine'):
            for c in ('M_probe_rna','M_probe_cut'):
                main,control=prefix+'M_open'+suffix,prefix+c+suffix
                if main not in endpoints or control not in endpoints: continue
                for name in ('writing_contact','writing_isolated_1','writing_isolated_2'):
                    checks.equal(control+'/same_writing/'+name,endpoints[main][name][1],endpoints[control][name][1])
    main=[b for b in reports if b['case']['kind']=='rewrite' and not b['case']['fine'] and b['case']['condition']=='M_open']
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    return dict(run=str(run),quality_gate=quality,ready_for_interpretation=quality,
        independent_check_count=len(checks.rows),checks=checks.rows,integrity=provenance,**gates,
        branches=reports,native_integrations=calls,fine_comparisons=fine,contrasts=contrasts,
        totals=dict(main_backgrounds=len(main),main_complete_M_rewrites=sum(b['outcomes']['complete_M_rewriting'] for b in main),
            main_onward_M_acquisitions=sum(b['outcomes']['onward_M_acquisition'] for b in main),
            main_complete_rewriting_and_transfer=sum(b['outcomes']['complete_rewriting_and_transfer'] for b in main),
            control_qualified_backgrounds=[c['background'] for c in contrasts if c['control_qualified_chain']],
            new_writing_events=sum(b['case']['kind']=='rewrite' for b in reports),new_onward_handovers=sum(b['case']['kind']=='rewrite' for b in reports)),
        all_selected_fine_agree=len(fine)==29 and all(f['agree'] for f in fine),
        positive_new_rewriting_required=False,positive_new_transfer_required=False,
        age_match_is_not_exposure_match=True,cell_age_is_not_lineage_age=True,
        historical_prefix_is_new_replication=False,independent_random_replicates=False,
        serial_renewal_demonstrated=False,autonomous_heredity_demonstrated=False,
        stress_panel=False,return_to_E=False,cell_division_simulated=False,
        full_paper_replication=False,clinical_therapy=False,automatic_follow_on=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    report=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',report)
    output={k:report[k] for k in ('quality_gate','independent_check_count','native_integrations','totals','all_selected_fine_agree')} if args.compact else report
    print(json.dumps(output,indent=2)); return 0 if report['quality_gate'] else 1


if __name__=='__main__': raise SystemExit(main())
