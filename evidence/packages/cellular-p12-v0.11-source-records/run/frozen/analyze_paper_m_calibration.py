"""Independent P7 audit: routing, native equations, raw replays and actual recipients."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import paper_m_calibration_design as d
import analyze_paper_sheet as p3
import analyze_paper_rewrite as p6
from analyze_paper_memory import Checks,labels
from analyze_paper_restoration import stable
from analyze_paper_sheet import arrays,edges


def expected_cases():
    cases=[dict(id='replay__p3_M_acquisition',kind='replay',source='p3',fine=False),
           dict(id='replay__p6_M_failure',kind='replay',source='p6',fine=False)]
    for f,l,m,k,c in itertools.product((False,True),('three_to_three','three_to_one','six_to_three'),
            ('depol','hypol'),('low','high'),('M_open','E_sham','M_rna','M_cut')):
        cases.append(dict(id=f'capacity__{l}__{m}__{k}__{c}'+('__fine' if f else ''),
            kind='capacity',layout=l,algorithm=m,anchor=k,condition=c,fine=f))
    return cases


def source_spec(run,case):
    if case['source']=='p3':
        return run/'inputs/p3/bank__depol__edge',dict(id='bank__depol__edge',kind='bank',
            history='depol',location='edge',blocked=False,fine=False),p3
    return run/'inputs/p6/assay__M',dict(id='assay__M',kind='assay',label='M',fine=False),p6


def phase_names(case):
    if case['kind']!='replay': return ['contact','isolated_1','isolated_2']
    if case['source']=='p3': return ['preparation','acquisition','acquired_isolated_1','acquired_isolated_2']
    return ['onward_contact','onward_isolated_1','onward_isolated_2']


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


def layout(case):
    return {'three_to_three':([2,3],3,3),'three_to_one':([2,2],3,1),'six_to_three':([3,3],6,3)}[case['layout']]


def geometry(case,name):
    shape,nd,nr=layout(case)
    fresh=[f'recipient:{i:02d}' for i in range(nr)]
    return (shape,[f'donor:{i:02d}' for i in range(nd)]+fresh) if name=='contact' else ([1,nr],fresh)


def settings(case,name):
    if name!='contact': return 'depol',1,0,True,10000
    kd=0 if case['condition']=='M_rna' else {'low':8.801117367933935e-16,'high':1.25e-14}[case['anchor']]
    return case['algorithm'],60,kd,False,20000


def regional_settings(case,name):
    shape,_=geometry(case,name); fr,to=edges(shape); _,nd,_=layout(case)
    members=set(range(nd)) if name=='contact' else set()
    regions=np.array([1 if f in members and t in members else
        2 if (f in members)!=(t in members) else 0 for f,t in zip(fr,to)],dtype=np.int8)
    cut=name=='contact' and case['condition']=='M_cut'; power=60 if name=='contact' else 1
    available=np.array([0. if x==2 and cut else 1. for x in regions])
    return regions,np.full(len(regions),power,dtype=float),available,dict(internal=power,boundary=power,helper=power,boundary_cut=cut)


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


def outcome(contact,one,two,idx,nd):
    e,m=stable(one,two,idx,'E'),stable(one,two,idx,'M')
    begin=labels(contact['initial'],idx); end=labels(contact['final'],idx); n=len(m)
    acquired=(begin[nd:]=='E') & m
    return dict(donor_start_labels=''.join(begin[:nd]),donor_contact_labels=''.join(end[:nd]),
        recipient_start_labels=''.join(begin[nd:]),recipient_contact_labels=''.join(end[nd:]),
        recipient_final_labels=''.join(labels(two['final'],idx)),recipients=n,
        retained_E=int(e.sum()),retained_M=int(m.sum()),acquired_M=int(acquired.sum()),
        all_recipient_E=bool(e.all()),all_recipient_M=bool(acquired.all()),
        partial_M=bool(0<acquired.sum()<n),contact_M_not_retained=int(((end[nd:]=='M') & ~m).sum()))


def branch(folder,case,checks):
    result=json.loads((folder/'result.json').read_text()); ck=lambda n,v:checks.add(case['id']+'/'+n,v)
    eq=lambda n,x,y:checks.equal(case['id']+'/'+n,x,y)
    ck('case',result['case']==case and result['execution_pass'])
    ck('scope',not any(result[k] for k in ('parameter_retuning','outcome_dependent_selection',
        'cell_division_simulated','artificial_target_schedule','donors_retained','serial_relay',
        'midway_rewriting','stress_panel','automatic_follow_on')) and result['external_handover_schedule'] and
        result['newly_simulated_handovers']==(0 if case['kind']=='replay' else 1))
    idx=result['ion_indices']; ck('indices',idx==dict(Na=0,K=1,Cl=2,P=3,snail=4,miR200_total=5,
        Zeb_mRNA_total=6,ZEB_prot=7,miR200_free=8,**{f'bound{i}':9+i for i in range(7)},ST=16))
    ck('phase_list',[p['phase'] for p in result['phases']]==phase_names(case))
    if case['kind']=='replay':
        source,oldcase,module=source_spec(folder.parent,case); data={}
        for rec in result['phases']:
            name=rec['phase']; local=Checks(); data[name]=module.audit_phase(folder,oldcase,rec,idx,local)
            for k,v in local.rows.items(): ck('native/'+k,v)
            old=arrays(source,name); ck('replay/'+name+'/keys',set(data[name])==set(old))
            for key,value in old.items(): eq('replay/'+name+'/'+key,data[name][key],value)
        last=data[phase_names(case)[-1]]
        out=dict(final_labels=''.join(labels(last['final'],idx)))
    else:
        data={p['phase']:audit_phase(folder,case,p,idx,checks) for p in result['phases']}
        _,nd,nr=layout(case); contact,one,two=[data[n] for n in phase_names(case)]
        stock=arrays(folder.parent/'inputs/p3/reference','preparation')
        E=stock['concentrations'][-1,:,168:169]; M=stock['concentrations'][-1,:,1:2]
        for name,value in data.items(): eq('bath/'+name,value['environment'],stock['environment'])
        donor=E if case['condition']=='E_sham' else M
        eq('ordinary_donors',contact['initial'][:,:nd],np.repeat(donor,nd,axis=1))
        eq('fresh_recipients',contact['initial'][:,nd:],np.repeat(E,nr,axis=1))
        eq('donor_start_labels',labels(contact['initial'],idx)[:nd],list(('E' if case['condition']=='E_sham' else 'M')*nd))
        eq('recipient_start_E',labels(contact['initial'],idx)[nd:],list('E'*nr))
        eq('donors_removed_actual_recipients',one['initial'],contact['final'][:,nd:])
        eq('hold_live_continuity',two['initial'],one['final'])
        out=outcome(contact,one,two,idx,nd)
        if not case['fine'] and (case['layout'],case['algorithm'],case['anchor'],case['condition'])==(
                'three_to_three','depol','high','M_open'):
            for name,value in data.items():
                old=arrays(folder.parent/'inputs/p6/assay__M','onward_'+name)
                ck('P6_matched/'+name+'/keys',set(value)==set(old))
                for key,x in old.items(): eq('P6_matched/'+name+'/'+key,value[key],x)
    return dict(case=case,outcomes=out),data,idx


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
    checks.add('predecessor_gate',summary['predecessor_gate']); archived=[]
    for c,n,calls in zip(expected_cases()[:2],(18941,56484),(465,1194)):
        folder,oldcase,module=source_spec(run,c); key=c['source']
        old=json.loads((run/'inputs'/key/'independent_audit.json').read_text())
        checks.add(key+'/predecessor_record',old['quality_gate'] and old['independent_check_count']==n and old['native_integrations']==calls)
        old_summary=json.loads((run/'inputs'/key/'summary.json').read_text())
        rec=next(r for r in old_summary['cases'] if r['id']==oldcase['id'])
        checks.add(key+'/source_result',rec['execution_pass'] and d.digest(folder/'result.json')==rec['result_sha256'] and
            json.loads((folder/'result.json').read_text())==rec['result'])
        local=Checks(); report,data,idx=module.branch(folder,oldcase,local)
        for name,value in local.rows.items(): checks.add(key+'/history/'+name,value)
        if key=='p3':
            checks.add('p3/known_positive',report['outcomes']['all_sample_acquired_M'] and report['outcomes']['acquired_M_count']==9)
        else:
            out=report['rounds'][0]
            checks.add('p6/known_negative',out['all_recipient_E'] and out['recipient_stable_M']==0 and
                ''.join(labels(data['onward_contact']['final'],idx)[:3])=='EEE')
        archived.append(report)
    reference=run/'inputs/p3/reference'
    original_summary=json.loads((run/'inputs/p3/summary.json').read_text())
    rec=next(c for c in original_summary['cases'] if c['id']=='reference')
    checks.add('p3/reference_record',rec['execution_pass'] and d.digest(reference/'result.json')==rec['result_sha256'] and
        json.loads((reference/'result.json').read_text())==rec['result'])
    oldcase=next(c for c in p3.expected_cases() if c['id']=='reference')
    local=Checks(); p3.branch(reference,oldcase,local)
    for name,value in local.rows.items(): checks.add('p3/stock/'+name,value)
    stock3=arrays(reference,'preparation')
    stock6=arrays(run/'inputs/p6/inputs/p5/inputs/p4_inputs/reference','preparation')
    checks.equal('same_P3_P6_prepared_states',stock3['concentrations'][-1],stock6['concentrations'][-1])
    checks.equal('same_P3_P6_bath',stock3['environment'],stock6['environment'])
    reports,_,calls=audited_records(run,expected_cases()[:2],checks)
    checks.add('replay_counts',len(reports)==2 and calls==7)
    provenance=integrity(run,summary)
    return dict(quality_gate=all(checks.rows.values()) and all(provenance.values()),checks=checks.rows,
        integrity=provenance,branches=reports,historical_branches=archived)


def qualify(outcomes):
    return (set(outcomes)=={'M_open','E_sham','M_rna','M_cut'} and outcomes['M_open']['all_recipient_M'] and
            all(outcomes[c]['all_recipient_E'] for c in ('E_sham','M_rna','M_cut')))


def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks(); cases=expected_cases()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_m_calibration_v1.json').read_text()))
    checks.add('registered_cases',summary['registered_cases']==cases)
    checks.add('case_set',len(summary['cases'])==98 and {r['id'] for r in summary['cases']}=={c['id'] for c in cases})
    checks.add('runner',summary.get('all_execution_valid',False))
    reports,endpoints,calls=audited_records(run,cases,checks); checks.add('native_calls',calls==295)
    gate=gate_audit(run); checks.add('gate/pass',gate['quality_gate'])
    checks.add('gate/saved',summary['gate']==gate==json.loads((run/'gate.json').read_text()) and d.digest(run/'gate.json')==summary['gate_sha256'])
    by={b['case']['id']:b for b in reports}; fine=[]
    for c in cases:
        fid=c['id']
        if not c['fine'] or fid not in endpoints: continue
        base=fid.removesuffix('__fine')
        if base not in endpoints: checks.add(fid+'/base_present',False); continue
        phases={}
        checks.equal(fid+'/identical_start',endpoints[fid]['contact'][0],endpoints[base]['contact'][0])
        for name,(_,value,labs) in endpoints[fid].items():
            _,old,oldlabs=endpoints[base][name]
            phases[name]=dict(labels_agree=bool(np.array_equal(labs,oldlabs)),
                maximum_absolute_difference=float(np.max(np.abs(value-old))),
                maximum_symmetric_relative_difference=float(np.max(np.abs(value-old)/np.maximum(1,np.maximum(np.abs(value),np.abs(old))))))
        same=by[fid]['outcomes']==by[base]['outcomes']; agree=same and all(v['labels_agree'] for v in phases.values())
        checks.add(fid+'/fine',agree); fine.append(dict(id=fid,baseline=base,outcomes_agree=same,agree=agree,phases=phases))
    checks.add('all_forty_eight_finer',len(fine)==48); fine_by={r['baseline']:r for r in fine}
    contrasts=[]
    for l,m,k in itertools.product(('three_to_three','three_to_one','six_to_three'),('depol','hypol'),('low','high')):
        prefix=f'capacity__{l}__{m}__{k}__'; conds=('M_open','E_sham','M_rna','M_cut')
        coarse={c:by[prefix+c]['outcomes'] for c in conds if prefix+c in by}
        refined={c:by[prefix+c+'__fine']['outcomes'] for c in conds if prefix+c+'__fine' in by}
        agrees=all(fine_by.get(prefix+c,{}).get('agree',False) for c in conds)
        good=bool(qualify(coarse) and qualify(refined) and agrees)
        contrasts.append(dict(layout=l,algorithm=m,anchor=k,conditions=coarse,fine_conditions=refined,
            fine_agreement=agrees,qualified=good,same_size= l=='three_to_three'))
    candidates=[{k:c[k] for k in ('layout','algorithm','anchor','same_size')} for c in contrasts if c['qualified']]
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    return dict(run=str(run),quality_gate=quality,ready_for_interpretation=quality,
        independent_check_count=len(checks.rows),checks=checks.rows,integrity=provenance,gate=gate,
        branches=reports,native_integrations=calls,fine_comparisons=fine,contrasts=contrasts,candidates=candidates,
        totals=dict(new_one_handover_cases=sum(b['case']['kind']=='capacity' for b in reports),
            qualified_conditions=len(candidates),same_size_candidates=sum(c['same_size'] for c in candidates),
            unequal_size_candidates=sum(not c['same_size'] for c in candidates)),
        all_selected_fine_agree=len(fine)==48 and all(f['agree'] for f in fine),
        positive_new_capacity_required=False,zero_kd_anchor_controls_physically_duplicate=True,
        independent_random_replicates=False,serial_renewal_demonstrated=False,midway_rewriting=False,
        stress_panel=False,cell_division_simulated=False,autonomous_heredity_demonstrated=False,
        full_paper_replication=False,clinical_therapy=False,automatic_follow_on=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    report=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',report)
    output={k:report[k] for k in ('quality_gate','independent_check_count','native_integrations','totals','all_selected_fine_agree')} if args.compact else report
    print(json.dumps(output,indent=2)); return 0 if report['quality_gate'] else 1


if __name__=='__main__': raise SystemExit(main())
