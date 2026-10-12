"""Independent P6 state, identity, routing, native-equation and provenance audit."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import paper_rewrite_design as d
import analyze_paper_relay as p5
from analyze_paper_memory import Checks, labels
from analyze_paper_restoration import stable
from analyze_paper_sheet import arrays, edges


def expected_cases():
    histories=('ordinary_E','restored_E')
    cases=[dict(id='replay__'+h,kind='replay',ancestry=h,source='relay__'+h+'__open',fine=False) for h in histories]
    cases += [dict(id='assay__'+l+('__fine' if f else ''),kind='assay',label=l,fine=f)
              for f,l in itertools.product((False,True),'EM')]
    conditions=('M_open','E_sham','M_write_rna','M_write_cut','no_cue','M_relay_rna','M_relay_cut')
    cases += [dict(id=f'rewrite__{h}__{mode}__{c}'+('__fine' if f else ''),kind='rewrite',
                   ancestry=h,source='relay__'+h+'__open',algorithm=mode,condition=c,fine=f)
              for f,h,mode,c in itertools.product((False,True),histories,('depol','hypol'),conditions)]
    return cases


def phase_names(case):
    parts=('contact','isolated_1','isolated_2')
    if case['kind']=='replay': return ['r07_'+p for p in parts]
    if case['kind']=='assay': return ['onward_'+p for p in parts]
    return ['writing_'+p for p in parts]+[f'r{r:02d}_{p}' for r in range(7,13) for p in parts]


def integrity(run,summary):
    try:
        h,f,i=summary['hashes_sha256'],summary['frozen_hashes_sha256'],summary['inputs']
        required=d.input_paths()
        return dict(revision=summary['revision']==d.REVISION,
            complete_manifest=set(h)==set(d.execution_manifest()) and
                set(f)=={p.name for p in d.LOCAL_FILES} and set(i)==set(required),
            input_origins=all(Path(i[p]['source'])==source for p,source in required.items()),
            execution=all(d.digest(d.ROOT/p)==v for p,v in h.items()),
            frozen=all(d.digest(run/'frozen'/p)==v for p,v in f.items()),
            sources=all(d.digest(Path(v['source']))==v['sha256'] for v in i.values()),
            inputs=all(d.digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()))
    except (OSError,KeyError,RuntimeError): return dict(integrity_readable=False)


def geometry(case,name):
    old=[f'relay:06:{i:02d}' for i in range(3)]
    if name.startswith('writing'):
        if name=='writing_contact' and case['condition']!='no_cue':
            return [2,3],old+[f'cue:{i:02d}' for i in range(3)]
        return [1,3],old
    if case['kind']=='assay':
        donor=[f'reference:{i:02d}' for i in range(3)]; fresh=[f'new:{i:02d}' for i in range(3)]
    elif case['kind']=='replay':
        donor=old; fresh=[f'relay:07:{i:02d}' for i in range(3)]
    else:
        number=int(name[1:3])
        donor=old if number==7 else [f'rewrite:{number-1:02d}:{i:02d}' for i in range(3)]
        fresh=[f'rewrite:{number:02d}:{i:02d}' for i in range(3)]
    return ([2,3],donor+fresh) if name.endswith('_contact') else ([1,3],fresh)


def settings(case,name):
    if name=='writing_contact':
        c=case['condition']
        return case['algorithm'],60,0 if c in ('M_write_rna','no_cue') else 1.25e-14,c=='no_cue',20000
    if name.endswith('_contact'):
        return ('hypol',1,1.25e-14,False,20000) if case['kind']=='replay' else (
            'depol',60,0 if case.get('condition')=='M_relay_rna' else 1.25e-14,False,20000)
    return 'depol',1,0,True,10000


def regional_settings(case,name,shape):
    fr,to=edges(shape); contact=name.endswith('_contact') and shape==[2,3]
    member={0,1,2} if contact else set()
    region=np.array([1 if f in member and t in member else
                     2 if (f in member)!=(t in member) else 0 for f,t in zip(fr,to)],dtype=np.int8)
    power=60 if name=='writing_contact' or (contact and case['kind']!='replay') else 1
    c=case.get('condition')
    cut=contact and ((name=='writing_contact' and c=='M_write_cut') or
                    (name!='writing_contact' and c=='M_relay_cut'))
    available=np.array([0. if x==2 and cut else 1. for x in region])
    return region,np.full(len(region),power,dtype=float),available,dict(
        internal=power,boundary=power,helper=power,boundary_cut=cut)


def audit_phase(folder,case,rec,idx,checks):
    name=rec['phase']; prefix=case['id']+'/'+name+'/'
    ck=lambda n,v:checks.add(prefix+n,v)
    path=folder/(name+'.npz'); ck('hash',d.digest(path)==rec['sha256'])
    a=arrays(folder,name)
    shape,ids=geometry(case,name); algo,power,kd,iso,horizon=settings(case,name)
    count=len(ids); setup=rec['setup']; fr,to=edges(shape)
    regions,powers,available,compartments=regional_settings(case,name,shape)
    ck('compartments',setup['compartment_expression']==compartments)
    for endpoint in ('initial','final'):
        ck('edge_region_'+endpoint,np.array_equal(a['edge_region_'+endpoint],regions))
        ck('edge_power_'+endpoint,np.array_equal(a['edge_power_'+endpoint],powers))
        ck('edge_available_'+endpoint,np.array_equal(a['edge_available_'+endpoint],available))
    ck('shape',a['initial'].shape==a['final'].shape==(17,count) and a['concentrations'].shape[1:]==(17,count))
    ck('ids',setup['cell_ids']==ids and len(set(ids))==count and setup['cells']==count)
    ck('geometry',setup['grid_shape']==shape and setup['orthogonal_only'] is True and setup['periodic'] is False)
    ck('topology',np.array_equal(a['edge_from'],fr) and np.array_equal(a['edge_to'],to))
    ck('degree',np.array_equal(np.bincount(np.r_[a['edge_from'],a['edge_to']],minlength=count),
                              np.bincount(np.r_[fr,to],minlength=count)))
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
        np.all(a['gate_Gdelta'][idx['miR200_total']]==1.56) and
        setup['mirna_transport']==dict(valence=-1,medium_size=True))
    ck('membrane_valences',np.array_equal(a['valences'],[1,1,-1,-1]+[0]*13))
    for side in ('initial','final'):
        value=a[side]; vm=(value*a['valences'][:,None]).sum(0)*96485*q['cell_vol']/(q['cell_sa']*.05)
        ck('vm_'+side,np.allclose(vm,a['vm_'+side],rtol=1e-12,atol=1e-14))
        dv=vm[fr]-vm[to]
        voltage=1.56/(1+np.exp(-110*(-dv+.0102))+np.exp(-110*(dv+.0102)))
        ck('voltage_'+side,np.allclose(voltage,a['voltage_gate_'+side],rtol=1e-10,atol=1e-12))
        mi,zeb,protein=(value[idx[k]] for k in ('miR200_total','Zeb_mRNA_total','ZEB_prot'))
        tp=(protein/(200000/18000+5))**10
        tumor=1/(1+(mi/30)**10)*tp/(1+tp)
        lo=np.minimum(tumor[fr],tumor[to]); hi=np.maximum(tumor[fr],tumor[to])
        expression=(1+(lo+.5*(hi-lo))*(powers-1))*available
        ck('expression_'+side,np.allclose(expression,a['expression_gate_'+side],rtol=1e-12,atol=1e-12))
        potassium=np.ones(count)
        if algo!='hypol':
            ratio=(mi/(.001+zeb))**10; potassium=1+30*ratio/(1+ratio)
        ck('potassium_'+side,np.allclose(potassium,a['potassium_gate_'+side],rtol=1e-12,atol=1e-12))
    return a


def stock(inputs):
    a=arrays(inputs/'p5/inputs/p4_inputs/reference','preparation')
    return a['concentrations'][-1,:,168:169],a['concentrations'][-1,:,1:2],a['environment']


def summarize_rounds(rounds,rewritten):
    failed=next((r['round'] for r in rounds if not r['all_recipient_M']),None)
    good=all(r['all_recipient_M'] for r in rounds)
    return dict(new_handover_rounds=len(rounds),first_failed_M_round=failed,
        unbroken_M_handovers=len(rounds) if failed is None else failed-rounds[0]['round'],
        M_rounds=sum(r['all_recipient_M'] for r in rounds),
        M_rounds_after_first_failure=0 if failed is None else sum(r['all_recipient_M'] for r in rounds if r['round']>failed),
        all_new_rounds_M=good,complete_rewrite_and_relay=bool(rewritten and good),
        final_recipient_E=rounds[-1]['recipient_stable_E'],final_recipient_M=rounds[-1]['recipient_stable_M'])


def reference_comparison(case,writing,rounds):
    """A fixed qualitative comparator, not a learned model or success gate."""
    if case['kind']=='replay': return []
    state=case.get('label','E'); checks=[]
    if writing is not None:
        c=case['condition']
        state='M' if c in ('M_open','M_relay_rna','M_relay_cut') else 'E'
        checks.append(dict(checkpoint='writing',predicted=state*3,
            observed=writing['final_labels'],stable_target_count=writing['retained_'+state],
            agree=writing['final_labels']==state*3 and writing['retained_'+state]==3))
    for row in rounds:
        if case.get('condition') in ('M_relay_rna','M_relay_cut'): state='E'
        checks.append(dict(checkpoint='round_'+str(row['round']),predicted=state*3,
            observed=row['recipient_final_labels'],stable_target_count=row['recipient_stable_'+state],
            agree=row['recipient_final_labels']==state*3 and row['recipient_stable_'+state]==3))
    return checks


def branch(folder,case,checks):
    inputs=folder.parent/'inputs'; result=json.loads((folder/'result.json').read_text())
    ck=lambda n,v:checks.add(case['id']+'/'+n,v)
    eq=lambda n,x,y:checks.equal(case['id']+'/'+n,x,y)
    ck('case',result['case']==case and result['execution_pass'])
    ck('no_retuning',not result['parameter_retuning'] and not result['outcome_dependent_selection'])
    ck('scope',not result['cell_division_simulated'] and not result['artificial_target_schedule'] and
        result['external_handover_schedule'] and result['source_external_regional_intervention'] and
        result['midway_rewriting']==(case['kind']=='rewrite') and not result['cue_cells_retained'] and
        not result['stress_panel'] and not result['return_to_E'])
    ck('round_metadata',result['historical_rounds']==(0 if case['kind']=='assay' else 6) and
        result['newly_simulated_handover_rounds']==(6 if case['kind']=='rewrite' else 1))
    idx=result['ion_indices']
    ck('indices',idx==dict(Na=0,K=1,Cl=2,P=3,snail=4,miR200_total=5,Zeb_mRNA_total=6,ZEB_prot=7,
        miR200_free=8,**{f'bound{i}':9+i for i in range(7)},ST=16))
    ck('phase_list',[p['phase'] for p in result['phases']]==phase_names(case))
    data={p['phase']:audit_phase(folder,case,p,idx,checks) for p in result['phases']}
    E,M,bath=stock(inputs)
    for name,value in data.items(): eq('common_bath/'+name,value['environment'],bath)
    if case['kind']=='assay': previous=np.repeat(E if case['label']=='E' else M,3,axis=1)
    else:
        previous=arrays(inputs/'p5'/case['source'],'r06_isolated_2')['final']
        eq('source_labels_E',labels(previous,idx),list('EEE'))
    writing=None
    if case['kind']=='rewrite':
        contact,one,two=[data['writing_'+n] for n in ('contact','isolated_1','isolated_2')]
        eq('writing/actual_round_six_carriers',contact['initial'][:,:3],previous)
        if case['condition']!='no_cue':
            cue=E if case['condition']=='E_sham' else M
            eq('writing/fresh_cue',contact['initial'][:,3:],np.repeat(cue,3,axis=1))
            eq('writing/cue_labels',labels(contact['initial'],idx)[3:],list('EEE' if case['condition']=='E_sham' else 'MMM'))
        eq('writing/cue_withdrawal',one['initial'],contact['final'][:,:3])
        eq('writing/hold_continuity',two['initial'],one['final'])
        e,m=stable(one,two,idx,'E'),stable(one,two,idx,'M')
        writing=dict(carrier_start_labels=''.join(labels(contact['initial'],idx)[:3]),
            carrier_contact_labels=''.join(labels(contact['final'],idx)[:3]),
            cue_final_labels=''.join(labels(contact['final'],idx)[3:]),
            retained_E=int(e.sum()),retained_M=int(m.sum()),all_carriers_M=bool(m.all()),
            all_carriers_E=bool(e.all()),final_labels=''.join(labels(two['final'],idx)))
        previous=two['final']
    rounds=[]
    for number in range(7,13) if case['kind']=='rewrite' else [7]:
        prefix='onward' if case['kind']=='assay' else f'r{number:02d}'
        names=[prefix+'_'+part for part in ('contact','isolated_1','isolated_2')]
        contact,one,two=[data[n] for n in names]
        eq(prefix+'/actual_incoming_carriers',contact['initial'][:,:3],previous)
        eq(prefix+'/fresh_recipients',contact['initial'][:,3:],np.repeat(M if case['kind']=='replay' else E,3,axis=1))
        eq(prefix+'/initial_recipient_labels',labels(contact['initial'],idx)[3:],list('MMM' if case['kind']=='replay' else 'EEE'))
        eq(prefix+'/complete_turnover',one['initial'],contact['final'][:,3:])
        eq(prefix+'/hold_continuity',two['initial'],one['final'])
        previous=two['final']; rounds.append(p5.round_outcome(number,data,idx,*names))
        if case['kind']=='replay':
            for n in names:
                old=arrays(inputs/'p5'/case['source'],n)
                ck('replay/'+n+'/keys',set(data[n])==set(old))
                for key,value in old.items(): eq('replay/'+n+'/'+key,data[n][key],value)
    return dict(case=case,writing=writing,rounds=rounds,reference_checks=reference_comparison(case,writing,rounds),
        outcomes=summarize_rounds(rounds,writing is not None and writing['all_carriers_M'])),data,idx


def audited_records(run,cases,checks):
    summary=json.loads((run/'summary.json').read_text()); records={r['id']:r for r in summary['cases']}
    reports=[]; endpoints={}; calls=0
    for c in cases:
        rec=records.get(c['id']); checks.add(c['id']+'/record',rec is not None and rec['execution_pass'])
        if rec is None or not rec['execution_pass']: continue
        path=run/c['id']/'result.json'
        checks.add(c['id']+'/result_frozen',d.digest(path)==rec['result_sha256'] and json.loads(path.read_text())==rec['result'])
        report,data,idx=branch(run/c['id'],c,checks); reports.append(report); calls+=len(data)
        endpoints[c['id']]={n:(v['final'],labels(v['final'],idx)) for n,v in data.items()}
    return reports,endpoints,calls


def gate_audit(run):
    run=Path(run); checks=Checks(); summary=json.loads((run/'summary.json').read_text())
    checks.add('predecessor_gate',summary['predecessor_gate'])
    old=json.loads((run/'inputs/p5/independent_audit.json').read_text())
    checks.add('predecessor_record',old['quality_gate'] and old['independent_check_count']==42065 and old['native_integrations']==804)
    archived=[]
    old_summary=json.loads((run/'inputs/p5/summary.json').read_text())
    for h in ('ordinary_E','restored_E'):
        ident='relay__'+h+'__open'; original=next(c for c in p5.expected_cases() if c['id']==ident)
        folder=run/'inputs/p5'/ident; record=next(c for c in old_summary['cases'] if c['id']==ident)
        checks.add('history/'+ident+'/result',record['execution_pass'] and
            d.digest(folder/'result.json')==record['result_sha256'] and json.loads((folder/'result.json').read_text())==record['result'])
        local=Checks(); report,_,_=p5.branch(folder,original,local)
        for key,value in local.rows.items(): checks.add('history/'+key,value)
        checks.add('history/'+ident+'/six_E_rounds',all(r['all_recipient_E'] for r in report['rounds'][:6]))
        archived.append(report)
    reports,_,calls=audited_records(run,expected_cases()[:2],checks)
    checks.add('gate_counts',len(reports)==2 and calls==6)
    for report in reports: checks.add(report['case']['id']+'/known_E',report['rounds'][0]['all_recipient_E'])
    provenance=integrity(run,summary)
    return dict(quality_gate=all(checks.rows.values()) and all(provenance.values()),
        checks=checks.rows,integrity=provenance,branches=reports,historical_branches=archived)


def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks(); cases=expected_cases()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_rewrite_v1.json').read_text()))
    checks.add('registered_cases',summary['registered_cases']==cases)
    checks.add('case_set',len(summary['cases'])==62 and {r['id'] for r in summary['cases']}=={c['id'] for c in cases})
    checks.add('runner',summary.get('all_execution_valid',False))
    reports,endpoints,calls=audited_records(run,cases,checks); checks.add('new_native_calls',calls==1194)
    gate=gate_audit(run); checks.add('gate/pass',gate['quality_gate'])
    checks.add('gate/saved',summary['gate']==gate==json.loads((run/'gate.json').read_text()) and
        d.digest(run/'gate.json')==summary['gate_sha256'])
    by={b['case']['id']:b for b in reports}; fine=[]
    for c in cases:
        fid=c['id']
        if not c['fine'] or fid not in endpoints: continue
        base=fid.removesuffix('__fine')
        if base not in endpoints: checks.add(fid+'/base_present',False); continue
        phases={}
        for name,(value,labs) in endpoints[fid].items():
            old,oldlabs=endpoints[base][name]
            phases[name]=dict(labels_agree=bool(np.array_equal(labs,oldlabs)),
                maximum_absolute_difference=float(np.max(np.abs(value-old))),
                maximum_symmetric_relative_difference=float(np.max(np.abs(value-old)/np.maximum(1,np.maximum(np.abs(value),np.abs(old))))))
        same=all(by[fid][k]==by[base][k] for k in ('writing','rounds','outcomes','reference_checks'))
        checks.add(fid+'/fine',same and all(x['labels_agree'] for x in phases.values()))
        fine.append(dict(id=fid,baseline=base,outcomes_agree=same,phases=phases))
    checks.add('all_thirty_finer',len(fine)==30)
    new_rounds=sum(len(b['rounds']) for b in reports if b['case']['kind']=='rewrite')
    checks.add('continuation_rounds',new_rounds==336)
    coarse=[b for b in reports if b['case']['kind']=='rewrite' and not b['case']['fine']]
    main=[b for b in coarse if b['case']['condition']=='M_open']
    contrasts=[]
    for h,mode in itertools.product(('ordinary_E','restored_E'),('depol','hypol')):
        subset={b['case']['condition']:b for b in coarse if b['case']['ancestry']==h and b['case']['algorithm']==mode}
        if len(subset)!=7: continue
        contrasts.append(dict(ancestry=h,algorithm=mode,conditions={c:dict(writing=b['writing'],outcomes=b['outcomes']) for c,b in subset.items()}))
    totals=dict(main_branches=len(main),main_durable_M_rewrites=sum(b['writing']['all_carriers_M'] for b in main),
        main_complete_rewrite_and_six_handovers=sum(b['outcomes']['complete_rewrite_and_relay'] for b in main),
        coarse_controls=len(coarse)-len(main),continuation_rounds_simulated=new_rounds,
        historical_rounds_reused_per_branch=6,new_rounds_per_branch=6)
    reference_checks=[v for b in reports if not b['case']['fine'] for v in b['reference_checks']]
    checks.add('reference_checkpoint_count',len(reference_checks)==198)
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    return dict(run=str(run),quality_gate=quality,ready_for_interpretation=quality,
        independent_check_count=len(checks.rows),checks=checks.rows,integrity=provenance,gate=gate,
        branches=reports,native_integrations=calls,fine_comparisons=fine,totals=totals,contrasts=contrasts,
        binary_reference=dict(name='always_copy_open_route_v1',coarse_checkpoints=len(reference_checks),
            matching_checkpoints=sum(v['agree'] for v in reference_checks),
            mismatch_is_not_new_mechanism=True,agreement_required=False),
        capacity_diagnostics=[b for b in reports if b['case']['kind']=='assay' and not b['case']['fine']],
        all_selected_fine_agree=len(fine)==30 and all(f['outcomes_agree'] and all(p['labels_agree'] for p in f['phases'].values()) for f in fine),
        positive_new_rewrite_required=False,positive_new_capacity_required=False,
        independent_random_replicates=False,historical_prefix_is_new_replication=False,
        same_readout_as_P5=False,midway_rewriting=True,return_to_E=False,stress_panel=False,
        cell_division_simulated=False,autonomous_heredity_demonstrated=False,
        full_paper_replication=False,clinical_therapy=False,automatic_follow_on=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    report=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',report)
    output={k:report[k] for k in ('quality_gate','independent_check_count','native_integrations','totals','all_selected_fine_agree')} if args.compact else report
    print(json.dumps(output,indent=2))
    return 0 if report['quality_gate'] else 1


if __name__=='__main__': raise SystemExit(main())
