"""Independent P5 renewal, complete turnover, gate-physics and provenance audit."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import paper_relay_design as d
from analyze_paper_memory import Checks,labels
from analyze_paper_restoration import stable
from analyze_paper_sheet import arrays,edges
import analyze_paper_topology as p4


def expected_cases():
    histories=('ordinary_E','ordinary_M','restored_E','failed_M')
    cases=[dict(id='replay__'+h,kind='replay',ancestry=h,source='capacity__'+h,route='open',fine=False)
           for h in histories]
    cases += [dict(id=f'relay__{h}__{route}'+('__fine' if f else ''),kind='relay',ancestry=h,
                   source='capacity__'+h,route=route,fine=f)
              for f,h,route in itertools.product((False,True),histories,('open','rna_blocked','border_cut'))]
    return cases


def phase_names(case):
    if case['kind']=='replay': return ['onward_contact','onward_isolated_1','onward_isolated_2']
    return [f'r{r:02d}_{part}' for r in range(2,13) for part in ('contact','isolated_1','isolated_2')]


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


def geometry(case,phase):
    contact=phase.endswith('_contact')
    if case['kind']=='replay':
        donor=['reference:00','reference:01','reference:02'] if case['ancestry'].startswith('ordinary') else [
            'original:r00:c05','original:r00:c06','original:r01:c05']
        fresh=['new:00','new:01','new:02']
    else:
        r=int(phase[1:3])
        donor=['new:00','new:01','new:02'] if r==2 else [f'relay:{r-1:02d}:{i:02d}' for i in range(3)]
        fresh=[f'relay:{r:02d}:{i:02d}' for i in range(3)]
    return ([2,3],donor+fresh) if contact else ([1,3],fresh)


def settings(case,phase):
    if phase.endswith('_contact'):
        return 'hypol',1,0 if case['route']=='rna_blocked' else 1.25e-14,False,20000
    return 'depol',1,0,True,10000


def regional_settings(case,phase,shape,ids):
    contact=phase.endswith('_contact')
    # Native right-then-down ordering in the 2 x 3 grid.
    regions=np.array([1,2,1,2,2,0,0] if contact else [0,0],dtype=np.int8)
    cut=contact and case['route']=='border_cut'
    available=np.where((regions==2)&cut,0.,1.)
    return regions,np.ones(len(regions)),available,dict(internal=1,boundary=1,helper=1,boundary_cut=cut)


def audit_phase(folder,case,rec,idx,checks):
    name=rec['phase']; prefix=case['id']+'/'+name+'/'
    ck=lambda n,v:checks.add(prefix+n,v)
    path=folder/(name+'.npz'); ck('hash',d.digest(path)==rec['sha256'])
    with np.load(path,allow_pickle=False) as stored: a=dict(stored)
    shape,ids=geometry(case,name); algo,power,kd,iso,horizon=settings(case,name)
    count=len(ids); setup=rec['setup']; fr,to=edges(shape)
    regions,powers,available,compartments=regional_settings(case,name,shape,ids)
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
    neighbor=algo=='nbrDepol' and not iso
    ck('neighbor',setup['neighbor_voltage_reading']==neighbor and setup['cell_voltage_gate_present']==(algo!='hypol'))
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
    # Native GRN temporarily assigns charge to free miRNA DURING transport,
    # then clears it; total/auxiliary RNA do not contribute to compute_Vm.
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
            ratio=(mi/(.001+zeb))**10; factor=(ratio/(1+ratio)).reshape(shape)
            if neighbor:
                tum=tumor.reshape(shape)
                factor[1:,:]=np.minimum(factor[1:,:],1-tum[:-1,:])
                factor[:,1:]=np.minimum(factor[:,1:],1-tum[:,:-1])
            potassium=1+30*factor.ravel()
        ck('potassium_'+side,np.allclose(potassium,a['potassium_gate_'+side],rtol=1e-12,atol=1e-12))
    return a


def round_outcome(number,data,idx,contact_name,first_name,second_name,historical=False):
    contact,first,second=[data[n] for n in (contact_name,first_name,second_name)]
    e,m=stable(first,second,idx,'E'),stable(first,second,idx,'M')
    return dict(round=number,historical=historical,carrier_start_labels=''.join(labels(contact['initial'],idx)[:3]),
        carrier_contact_labels=''.join(labels(contact['final'],idx)[:3]),
        recipient_start_labels=''.join(labels(contact['initial'],idx)[3:]),
        recipient_contact_labels=''.join(labels(contact['final'],idx)[3:]),
        recipient_final_labels=''.join(labels(second['final'],idx)),
        recipient_stable_E=int(e.sum()),recipient_stable_M=int(m.sum()),all_recipient_E=bool(e.all()),
        all_recipient_M=bool(m.all()))


def summarize_rounds(rounds):
    failed=next((r['round'] for r in rounds if not r['all_recipient_E']),None)
    new=[r for r in rounds if not r['historical']]
    return dict(total_rounds=len(rounds),historical_rounds=sum(r['historical'] for r in rounds),
        newly_simulated_rounds=len(new),first_failed_E_round=failed,
        unbroken_E_prefix=rounds[-1]['round'] if failed is None else failed-1,
        E_rounds=sum(r['all_recipient_E'] for r in rounds),
        E_rounds_after_first_failure=0 if failed is None else sum(r['all_recipient_E'] for r in rounds if r['round']>failed),
        all_rounds_E=all(r['all_recipient_E'] for r in rounds),
        all_new_rounds_E=all(r['all_recipient_E'] for r in new),
        final_recipient_E=rounds[-1]['recipient_stable_E'],
        final_recipient_M=rounds[-1]['recipient_stable_M'])


def historical_prefix(inputs,case,idx,checks):
    folder=inputs/case['source']; info=json.loads((folder/'result.json').read_text())
    ck=lambda n,v:checks.add(case['id']+'/historical/'+n,v)
    eq=lambda n,x,y:checks.equal(case['id']+'/historical/'+n,x,y)
    original=next(c for c in p4.expected_cases() if c['id']==case['source'])
    ck('case',info['case']==original and info['execution_pass'] and info['ion_indices']==idx)
    names=['onward_contact','onward_isolated_1','onward_isolated_2']
    ck('phases',[p['phase'] for p in info['phases']]==names)
    local=Checks()
    data={rec['phase']:p4.audit_phase(folder,original,rec,idx,local) for rec in info['phases']}
    for key,value in local.rows.items(): ck(key,value)
    stock=arrays(inputs/'p4_inputs/reference','preparation')
    E,M=stock['concentrations'][-1,:,168:169],stock['concentrations'][-1,:,1:2]
    for n,value in data.items(): eq('common_bath/'+n,value['environment'],stock['environment'])
    if case['ancestry'].startswith('ordinary'):
        founders=np.repeat(E if case['ancestry'].endswith('_E') else M,3,axis=1)
    else:
        founders=arrays(inputs/'p4_inputs'/original['source'],'isolated_2')['final'][:,[0,1,3]]
    eq('actual_founders',data[names[0]]['initial'][:,:3],founders)
    eq('fresh_M',data[names[0]]['initial'][:,3:],np.repeat(M,3,axis=1))
    eq('withdrawal_live',data[names[1]]['initial'],data[names[0]]['final'][:,3:])
    eq('hold_continuity',data[names[2]]['initial'],data[names[1]]['final'])
    return data,round_outcome(1,data,idx,*names,historical=True),M,stock['environment']


def branch(folder,case,checks):
    inputs=folder.parent/'inputs'; result=json.loads((folder/'result.json').read_text())
    ck=lambda n,v:checks.add(case['id']+'/'+n,v)
    eq=lambda n,x,y:checks.equal(case['id']+'/'+n,x,y)
    ck('case',result['case']==case and result['execution_pass'])
    ck('no_retuning',not result['parameter_retuning'] and not result['outcome_dependent_selection'])
    ck('scope',not result['cell_division_simulated'] and not result['artificial_target_schedule'] and
        result['external_handover_schedule'] and result['source_external_regional_intervention'] and
        not result['midway_rewriting'] and not result['stress_panel'])
    replay=case['kind']=='replay'
    ck('round_count_metadata',result['historical_rounds']==(0 if replay else 1) and
        result['newly_simulated_rounds']==(1 if replay else 11) and result['total_rounds']==(1 if replay else 12))
    idx=result['ion_indices']
    ck('indices',idx==dict(Na=0,K=1,Cl=2,P=3,snail=4,miR200_total=5,Zeb_mRNA_total=6,ZEB_prot=7,
        miR200_free=8,**{f'bound{i}':9+i for i in range(7)},ST=16))
    ck('phase_list',[p['phase'] for p in result['phases']]==phase_names(case))
    data={p['phase']:audit_phase(folder,case,p,idx,checks) for p in result['phases']}
    prefix,historical,M,bath=historical_prefix(inputs,case,idx,checks)
    for name,value in data.items(): eq('common_bath/'+name,value['environment'],bath)
    if replay:
        for name,value in data.items():
            ck('replay/'+name+'/keys',set(value)==set(prefix[name]))
            for key,arr in prefix[name].items(): eq('replay/'+name+'/'+key,value[key],arr)
        rounds=[round_outcome(1,data,idx,*phase_names(case))]
    else:
        rounds=[historical]; previous=prefix['onward_isolated_2']['final']
        for number in range(2,13):
            contact_name,first_name,second_name=[f'r{number:02d}_{part}' for part in ('contact','isolated_1','isolated_2')]
            contact,first,second=[data[n] for n in (contact_name,first_name,second_name)]
            eq(f'r{number:02d}/actual_incoming_carriers',contact['initial'][:,:3],previous)
            eq(f'r{number:02d}/fresh_M',contact['initial'][:,3:],np.repeat(M,3,axis=1))
            eq(f'r{number:02d}/starts_M',labels(contact['initial'],idx)[3:],list('MMM'))
            eq(f'r{number:02d}/complete_turnover',first['initial'],contact['final'][:,3:])
            eq(f'r{number:02d}/hold_continuity',second['initial'],first['final'])
            previous=second['final']
            rounds.append(round_outcome(number,data,idx,contact_name,first_name,second_name))
    return dict(case=case,outcomes=summarize_rounds(rounds),rounds=rounds),data,idx


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
    old=json.loads((run/'inputs/p4/independent_audit.json').read_text())
    checks.add('predecessor_record',old['quality_gate'] and old['independent_check_count']==42565 and old['native_integrations']==858)
    reports,_,calls=audited_records(run,expected_cases()[:4],checks)
    for report in reports:
        c=report['case']; out=report['rounds'][0]
        wanted='E' if c['ancestry'].endswith('_E') else 'M'
        checks.add(c['id']+'/prefix_qualification',out['all_recipient_'+wanted])
    checks.add('gate_counts',len(reports)==4 and calls==12)
    provenance=integrity(run,summary)
    return dict(quality_gate=all(checks.rows.values()) and all(provenance.values()),
        checks=checks.rows,integrity=provenance,branches=reports)


def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks(); cases=expected_cases()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_relay_v1.json').read_text()))
    checks.add('registered_cases',summary['registered_cases']==cases)
    checks.add('case_set',len(summary['cases'])==28 and {r['id'] for r in summary['cases']}=={c['id'] for c in cases})
    checks.add('runner',summary.get('all_execution_valid',False))
    reports,endpoints,calls=audited_records(run,cases,checks); checks.add('new_native_calls',calls==804)
    gate=gate_audit(run); checks.add('gate/pass',gate['quality_gate'])
    checks.add('gate/saved',summary['gate']==gate==json.loads((run/'gate.json').read_text()) and
        d.digest(run/'gate.json')==summary['gate_sha256'])
    by={b['case']['id']:b for b in reports}; fine=[]
    for c in cases:
        if not c['fine'] or c['id'] not in endpoints: continue
        fid=c['id']; base=fid.removesuffix('__fine')
        if base not in endpoints: checks.add(fid+'/base_present',False); continue
        phases={}
        for name,(value,labs) in endpoints[fid].items():
            old,oldlabs=endpoints[base][name]
            phases[name]=dict(labels_agree=bool(np.array_equal(labs,oldlabs)),
                maximum_absolute_difference=float(np.max(np.abs(value-old))),
                maximum_symmetric_relative_difference=float(np.max(np.abs(value-old)/np.maximum(1,np.maximum(np.abs(value),np.abs(old))))))
        same=by[fid]['outcomes']==by[base]['outcomes'] and by[fid]['rounds']==by[base]['rounds']
        checks.add(fid+'/fine',same and all(x['labels_agree'] for x in phases.values()))
        fine.append(dict(id=fid,baseline=base,outcomes_agree=same,phases=phases))
    checks.add('all_twelve_finer',len(fine)==12)
    new_rounds=sum(b['outcomes']['newly_simulated_rounds'] for b in reports if b['case']['kind']=='relay')
    checks.add('continuation_rounds',new_rounds==264)
    main=[b for b in reports if b['case']['kind']=='relay' and b['case']['route']=='open' and not b['case']['fine']]
    controls=[b for b in reports if b['case']['kind']=='relay' and b['case']['route']!='open' and not b['case']['fine']]
    totals=dict(main_lineages=len(main),open_lineages_E_through_12=sum(b['outcomes']['all_rounds_E'] for b in main),
        successful_E_ancestries=[b['case']['ancestry'] for b in main if b['outcomes']['all_rounds_E']],
        control_lineages=len(controls),controls_with_any_new_E_round=sum(any(r['all_recipient_E'] for r in b['rounds'][1:]) for b in controls),
        continuation_rounds_simulated=new_rounds,historical_prefix_rounds_per_lineage=1)
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    return dict(run=str(run),quality_gate=quality,ready_for_interpretation=quality,
        independent_check_count=len(checks.rows),checks=checks.rows,integrity=provenance,
        gate=gate,branches=reports,native_integrations=calls,fine_comparisons=fine,totals=totals,
        all_selected_fine_agree=len(fine)==12 and all(f['outcomes_agree'] and all(p['labels_agree'] for p in f['phases'].values()) for f in fine),
        positive_new_renewal_required=False,independent_random_replicates=False,
        historical_round_1_is_independent_replication=False,midway_rewriting=False,stress_panel=False,
        full_paper_replication=False,clinical_therapy=False,cell_division_simulated=False,
        autonomous_heredity_demonstrated=False,automatic_follow_on=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    run=args.run.resolve()
    if run.parent!=d.ROOT/'runs' or not run.name.startswith('paper-relay-'): raise ValueError('Not a P5 run')
    report=analyze(run)
    if args.save: d.write_json(run/'independent_audit.json',report)
    if args.compact: report={k:v for k,v in report.items() if k not in ('checks','gate','fine_comparisons')}
    print(json.dumps(report,indent=2,allow_nan=False)); return 0 if report['quality_gate'] else 1


if __name__=='__main__': raise SystemExit(main())

