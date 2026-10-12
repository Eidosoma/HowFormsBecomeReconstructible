"""Independent P3 topology, native gate, identity and full-chain qualification audit."""
import argparse
import json
from pathlib import Path

import numpy as np
import paper_sheet_design as d
from analyze_paper_memory import Checks, labels
from analyze_paper_restoration import stable


def expected_cases():
    # Independently enumerate the registered panel, not a runner-generated subset.
    out=[dict(id='reference',kind='reference',fine=False),dict(id='benchmark_625',kind='benchmark',fine=False)]
    out += [dict(id='assay__'+l,kind='assay',label=l,fine=False) for l in 'EM']
    pairs=[(a,l) for a in ('depol','nbrDepol','hypol') for l in ('edge','centre')]
    finer=[('depol','edge'),('nbrDepol','centre'),('hypol','edge')]
    for blocked,fine,settings in ((False,False,pairs),(True,False,pairs),(False,True,finer)):
        for a,l in settings:
            out.append(dict(id=f'bank__{a}__{l}'+('__blocked' if blocked else '')+('__fine' if fine else ''),
                kind='bank',history=a,location=l,blocked=blocked,fine=fine))
    rows=[('main',a,l,n,s,False) for a,l in pairs for n in (2,3)
          for s in ('neither','voltage','expression','both')]
    rows += [(k,a,l,3,s,False) for k,s in (('blocked','both'),('alone','neither')) for a,l in pairs]
    rows += [('main',a,l,n,'both',True) for a,l in finer for n in (2,3)]
    for kind,a,l,n,s,fine in rows:
        suffix='__fine' if fine else ''
        out.append(dict(id=f'{kind}__{a}__{l}__s{n}__{s}'+suffix,kind=kind,history=a,location=l,
            side=n,strategy=s,bank=f'bank__{a}__{l}'+suffix,fine=fine))
    return out


def integrity(run,summary):
    try:
        h,f,i=summary['hashes_sha256'],summary['frozen_hashes_sha256'],summary['inputs']
        return dict(revision=summary['revision']==d.REVISION,
            complete_manifest=set(h)==set(d.execution_manifest()) and set(f)=={p.name for p in d.LOCAL_FILES}
                and set(i)==set(d.input_paths()),
            execution=all(d.digest(d.ROOT/p)==v for p,v in h.items()),
            frozen=all(d.digest(run/'frozen'/p)==v for p,v in f.items()),
            sources=all(d.digest(Path(v['source']))==v['sha256'] for v in i.values()),
            inputs=all(d.digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()))
    except (OSError,KeyError,RuntimeError): return dict(integrity_readable=False)


def rectangle(row,col,side,cols=13):
    return [i*cols+j for i in range(row,row+side) for j in range(col,col+side)]


def edges(shape):
    rows,cols=shape; pairs=[]
    for i in range(rows*cols):
        if i%cols+1<cols: pairs.append((i,i+1))
        if i//cols+1<rows: pairs.append((i,i+cols))
    return np.asarray(pairs,dtype=int).reshape(-1,2).T


def geometry(case,phase):
    originals=[f'original:r{r:02d}:c{c:02d}' for r in range(13) for c in range(13)]
    if phase in ('preparation','acquisition'): return [13,13],originals
    if case['kind']=='bank':
        row=0 if case['location']=='edge' else 4
        return [3,3],[originals[i] for i in rectangle(row,5,3)]
    if phase in ('onward_isolated_1','onward_isolated_2'): return [1,1],['probe:00']
    if case['kind']=='assay': return [2,2],['reference:00','reference:01','reference:02','probe:00']
    n=case['side']; row=0 if case['location']=='edge' else 4
    ids=[originals[i] for i in rectangle(row,5,n)]
    if phase=='onward_contact': return [2,2],[ids[i] for i in (0,1,n)]+['probe:00']
    if phase=='restoration' and case['kind']!='alone':
        field=[f'helper:r{r:02d}:c{c:02d}' for r in range(13) for c in range(13)]
        positions=rectangle(0 if case['location']=='edge' else 5,5,n)
        for i,name in zip(positions,ids): field[i]=name
        return [13,13],field
    return [n,n],ids


def settings(case,phase):
    if phase=='preparation': return case.get('history','depol'),1,0,False,1000
    if phase=='acquisition': return case['history'],60,0 if case['blocked'] else 8.801117367933935e-16,False,20000
    if phase=='onward_contact': return 'hypol',1,1.25e-14,False,20000
    if phase=='restoration':
        if case['kind']=='alone': return 'depol',1,0,True,20000
        strategy=case['strategy']; algo='hypol' if strategy in ('voltage','both') else 'depol'
        power=1 if strategy in ('expression','both') else 60
        return algo,power,0 if case['kind']=='blocked' else 1.25e-14,False,20000
    return 'depol',1,0,True,10000


def audit_phase(folder,case,rec,idx,checks):
    name=rec['phase']; prefix=case['id']+'/'+name+'/'
    ck=lambda n,v:checks.add(prefix+n,v)
    path=folder/(name+'.npz'); ck('hash',d.digest(path)==rec['sha256'])
    with np.load(path,allow_pickle=False) as stored: a=dict(stored)
    shape,ids=geometry(case,name); algo,power,kd,iso,horizon=settings(case,name)
    count=len(ids); setup=rec['setup']; fr,to=edges(shape)
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
        expression=1+(lo+.5*(hi-lo))*(power-1)
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


def arrays(folder,phase):
    with np.load(folder/(phase+'.npz'),allow_pickle=False) as a: return dict(a)


def bank_outcome(folder,case,idx):
    pre=arrays(folder,'preparation'); contact=arrays(folder,'acquisition')
    first=arrays(folder,'acquired_isolated_1'); second=arrays(folder,'acquired_isolated_2')
    take=rectangle(0 if case['location']=='edge' else 4,5,3)
    qualified=((labels(pre['initial'],idx)[take]=='E') & (labels(contact['initial'],idx)[take]=='E') &
        (labels(contact['final'],idx)[take]=='M') & stable(first,second,idx,'M'))
    return dict(sample_started_E=int(np.sum(labels(contact['initial'],idx)[take]=='E')),
        sample_contact_M=int(np.sum(labels(contact['final'],idx)[take]=='M')),
        sample_stable_M=int(np.sum(stable(first,second,idx,'M'))),
        acquired_M_mask=qualified.tolist(),acquired_M_count=int(qualified.sum()),
        all_sample_acquired_M=bool(qualified.all()))


def qualify(source_mask,retained_E,probe_E):
    """Never count a never-acquired E cell as restored; keep all cases in denominator."""
    n=int(np.sqrt(len(source_mask))); carriers=[0,1,n]
    source=np.asarray(source_mask,dtype=bool); restored=np.asarray(retained_E,dtype=bool)
    return dict(patch_acquired_M=int(source.sum()),patch_eligible=bool(source.all()),
        patch_stable_E=int(restored.sum()),all_patch_stably_E=bool(restored.all()),
        acquired_then_restored_cells=int((source & restored).sum()),
        fixed_carriers_eligible=bool(source[carriers].all()),
        fixed_carriers_stably_E=bool(restored[carriers].all()),
        strict_full_patch_chain=bool(source.all() and restored.all() and probe_E),
        strict_carrier_chain=bool(source[carriers].all() and restored[carriers].all() and probe_E))


def branch(folder,case,checks):
    run=folder.parent; result=json.loads((folder/'result.json').read_text())
    ck=lambda n,v:checks.add(case['id']+'/'+n,v)
    eq=lambda n,x,y:checks.equal(case['id']+'/'+n,x,y)
    ck('case',result['case']==case and result['execution_pass'])
    ck('no_retuning',not result['parameter_retuning'] and not result['outcome_dependent_selection'])
    ck('no_reproduction',not result['cell_division_simulated'] and not result['artificial_target_schedule'])
    idx=result['ion_indices']
    expected_idx=dict(Na=0,K=1,Cl=2,P=3,snail=4,miR200_total=5,Zeb_mRNA_total=6,ZEB_prot=7,
        miR200_free=8,**{f'bound{i}':9+i for i in range(7)},ST=16)
    old=json.loads((run/'inputs/pilot/result.json').read_text())
    ck('indices',idx==old['ion_indices']==expected_idx)
    names=['onward_contact','onward_isolated_1','onward_isolated_2']
    if case['kind']=='reference': names=['preparation']
    elif case['kind']=='bank': names=['preparation','acquisition','acquired_isolated_1','acquired_isolated_2']
    elif case['kind']!='assay': names=['restoration','isolated_1','isolated_2']+names
    ck('phase_list',[p['phase'] for p in result['phases']]==names)
    data={p['phase']:audit_phase(folder,case,p,idx,checks) for p in result['phases']}
    ref=data['preparation'] if case['kind']=='reference' else arrays(run/'reference','preparation')
    for name,a in data.items(): eq('common_bath/'+name,a['environment'],ref['environment'])
    E,M=ref['concentrations'][-1,:,168:169],ref['concentrations'][-1,:,1:2]
    if case['kind'] in ('reference','bank'):
        with np.load(run/'inputs/pilot/endpoints.npz',allow_pickle=False) as old_arrays:
            fresh=np.repeat(old_arrays['initial'][:,6:7],169,axis=1)
            fresh[:,rectangle(0 if case.get('location','edge')=='edge' else 4,1,4)]=old_arrays['initial'][:,:1]
        eq('native_start',data['preparation']['initial'],fresh)
        if case['kind']=='reference':
            eq('reference_E',labels(E,idx),['E']); eq('reference_M',labels(M,idx),['M'])
            return dict(case=case,outcomes=dict(reference_labels='EM')),data,idx
        contact=data['acquisition']; take=rectangle(0 if case['location']=='edge' else 4,5,3)
        eq('native_snapshot_start',contact['initial'],data['preparation']['concentrations'][-1])
        eq('remove_all_sources',data['acquired_isolated_1']['initial'],contact['final'][:,take])
        eq('acquisition_hold_continuity',data['acquired_isolated_2']['initial'],data['acquired_isolated_1']['final'])
        return dict(case=case,outcomes=bank_outcome(folder,case,idx)),data,idx
    contact=data['onward_contact']; first=data['onward_isolated_1']; second=data['onward_isolated_2']
    eq('fresh_probe',contact['initial'][:,3:4],M); eq('probe_starts_M',labels(contact['initial'],idx)[3:4],['M'])
    eq('remove_all_carriers',first['initial'],contact['final'][:,3:4]); eq('probe_continuity',second['initial'],first['final'])
    out=dict(probe_contact_label=str(labels(contact['final'],idx)[3]),
        probe_final_label=str(labels(second['final'],idx)[0]),probe_stable_E=bool(stable(first,second,idx,'E')[0]),
        probe_stable_M=bool(stable(first,second,idx,'M')[0]))
    if case['kind']=='assay': eq('ordinary_carriers',contact['initial'][:,:3],np.repeat(E if case['label']=='E' else M,3,axis=1))
    else:
        n=case['side']; take=rectangle(0,0,n,3); bank=run/case['bank']
        bank_case=next(c for c in expected_cases() if c['id']==case['bank'])
        source=arrays(bank,'acquired_isolated_2')['final'][:,take]
        restoration=data['restoration']; isolated1=data['isolated_1']; isolated2=data['isolated_2']
        positions=list(range(n*n)) if case['kind']=='alone' else rectangle(0 if case['location']=='edge' else 5,5,n)
        eq('actual_acquired_state',restoration['initial'][:,positions],source)
        helpers=[i for i in range(restoration['initial'].shape[1]) if i not in positions]
        if helpers:
            eq('common_fresh_helpers',restoration['initial'][:,helpers],np.repeat(E,len(helpers),axis=1))
            eq('helpers_start_E',labels(restoration['initial'],idx)[helpers],list('E'*len(helpers)))
        eq('withdrawal_no_reset',isolated1['initial'],restoration['final'][:,positions])
        eq('withdrawal_continuity',isolated2['initial'],isolated1['final'])
        eq('fixed_carriers_without_selection',contact['initial'][:,:3],isolated2['final'][:,[0,1,n]])
        source_mask=np.asarray(bank_outcome(bank,bank_case,idx)['acquired_M_mask'])[take]
        retained=stable(isolated1,isolated2,idx,'E')
        out.update(qualify(source_mask,retained,out['probe_stable_E']))
        out.update(patch_contact_E=int(np.sum(labels(restoration['final'],idx)[positions]=='E')),
            helper_contact_M=int(np.sum(labels(restoration['final'],idx)[helpers]=='M')),
            carrier_final_labels=''.join(labels(isolated2['final'],idx)[[0,1,n]]))
    return dict(case=case,outcomes=out),data,idx


def benchmark(run,checks):
    folder=run/'benchmark_625'; result=json.loads((folder/'result.json').read_text())
    old=json.loads((run/'inputs/pilot/result.json').read_text())
    ck=lambda n,v:checks.add('benchmark_625/'+n,v)
    ck('case',result['case']==old['case']==dict(id='benchmark_625',kind='isolation',strategy='none',
        kd=1.25e-14,dimensions=[1,25,25],expected_fixed=True))
    ck('counts',result['final_state_counts']==old['final_state_counts']==dict(E=625,M=0,X=0))
    ck('native_pass',result['pass'] and result['observed_fixed'] and result['pass_comparison'])
    ck('integrator',result['integrator']==old['integrator'])
    ck('calls',len(result['audits'])==2 and [r['requested_horizon'] for r in result['audits']]==[500,20000])
    for name in ('endpoints.npz','trajectory-0.npz','trajectory-1.npz'):
        with np.load(folder/name,allow_pickle=False) as x,np.load(run/'inputs/pilot'/name,allow_pickle=False) as y:
            ck(name+'/keys',set(x.files)==set(y.files))
            for key in y.files: ck(name+'/'+key,np.array_equal(x[key],y[key]))
    return dict(case=next(c for c in expected_cases() if c['kind']=='benchmark'),outcomes=dict(exact_native_replay=True))


def audited_records(run,cases,checks):
    summary=json.loads((run/'summary.json').read_text()); records={r['id']:r for r in summary['cases']}
    reports=[]; endpoints={}; calls=0
    for c in cases:
        rec=records.get(c['id']); checks.add(c['id']+'/record',rec is not None and rec['execution_pass'])
        if rec is None or not rec['execution_pass']: continue
        path=run/c['id']/'result.json'
        checks.add(c['id']+'/result_frozen',d.digest(path)==rec['result_sha256'] and json.loads(path.read_text())==rec['result'])
        if c['kind']=='benchmark': reports.append(benchmark(run,checks)); calls+=2; continue
        report,data,idx=branch(run/c['id'],c,checks); reports.append(report); calls+=len(data)
        endpoints[c['id']]={n:(v['final'],labels(v['final'],idx)) for n,v in data.items()}
    return reports,endpoints,calls


def gate_audit(run):
    run=Path(run); checks=Checks(); summary=json.loads((run/'summary.json').read_text())
    checks.add('predecessor_gate',summary['predecessor_gate'])
    reports,_,calls=audited_records(run,expected_cases()[:4],checks)
    for report in reports:
        c=report['case']
        if c['kind']=='assay': checks.add(c['id']+'/qualification',report['outcomes']['probe_stable_'+c['label']])
    checks.add('gate_counts',len(reports)==4 and calls==9)
    provenance=integrity(run,summary)
    return dict(quality_gate=all(checks.rows.values()) and all(provenance.values()),
        checks=checks.rows,integrity=provenance,branches=reports)


def bank_gate(run):
    run=Path(run); checks=Checks(); summary=json.loads((run/'summary.json').read_text())
    checks.add('previous_gate',bool((summary.get('gate') or {}).get('quality_gate')))
    reports,_,calls=audited_records(run,expected_cases()[4:19],checks)
    checks.add('bank_counts',len(reports)==15 and calls==60)
    provenance=integrity(run,summary)
    return dict(quality_gate=all(checks.rows.values()) and all(provenance.values()),
        checks=checks.rows,integrity=provenance,branches=reports,positive_acquisition_required=False)


def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks(); cases=expected_cases()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_sheet_v1.json').read_text()))
    checks.add('registered_cases',summary['registered_cases']==cases)
    checks.add('case_set',len(summary['cases'])==85 and {r['id'] for r in summary['cases']}=={c['id'] for c in cases})
    checks.add('runner',summary.get('all_execution_valid',False))
    reports,endpoints,calls=audited_records(run,cases,checks); checks.add('calls',calls==465)
    gate=gate_audit(run); banks=bank_gate(run)
    for key,value in (('gate',gate),('bank_gate',banks)):
        checks.add(key+'/pass',value['quality_gate'])
        checks.add(key+'/saved',summary[key]==value==json.loads((run/(key+'.json')).read_text()) and
            d.digest(run/(key+'.json'))==summary[key+'_sha256'])
    by={b['case']['id']:b['outcomes'] for b in reports}; fine=[]
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
        same=by[fid]==by[base]
        checks.add(fid+'/fine',same and all(x['labels_agree'] for x in phases.values()))
        fine.append(dict(id=fid,baseline=base,outcomes_agree=same,phases=phases))
    checks.add('all_nine_finer',len(fine)==9)
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    main=[b['outcomes'] for b in reports if b['case']['kind']=='main' and not b['case']['fine']]
    totals=dict(main_cases=len(main),eligible_patches=sum(b['patch_eligible'] for b in main),
        full_patch_chains=sum(b['strict_full_patch_chain'] for b in main),
        fixed_carrier_chains=sum(b['strict_carrier_chain'] for b in main),
        helper_spread_cases=sum(b['helper_contact_M']>0 for b in main))
    return dict(run=str(run),quality_gate=quality,ready_for_interpretation=quality,
        independent_check_count=len(checks.rows),checks=checks.rows,integrity=provenance,
        gate=gate,bank_gate=banks,branches=reports,native_integrations=calls,fine_comparisons=fine,
        all_selected_fine_agree=len(fine)==9 and all(f['outcomes_agree'] and all(p['labels_agree'] for p in f['phases'].values()) for f in fine),
        totals=totals,acquisition_conditions=6,independent_random_replicates=False,
        full_paper_replication=False,clinical_therapy=False,cell_division_simulated=False,
        autonomous_heredity_demonstrated=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    run=args.run.resolve()
    if run.parent!=d.ROOT/'runs' or not run.name.startswith('paper-sheet-'): raise ValueError('Not a P3 run')
    report=analyze(run)
    if args.save: d.write_json(run/'independent_audit.json',report)
    if args.compact: report={k:v for k,v in report.items() if k not in ('checks','gate','bank_gate','fine_comparisons')}
    print(json.dumps(report,indent=2,allow_nan=False)); return 0 if report['quality_gate'] else 1


if __name__=='__main__': raise SystemExit(main())
