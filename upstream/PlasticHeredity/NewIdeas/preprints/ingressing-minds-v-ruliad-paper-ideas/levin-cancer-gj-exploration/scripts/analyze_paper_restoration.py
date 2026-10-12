"""Independent P2 array, mechanism, withdrawal and onward-restoration audit."""
import argparse
import json
from pathlib import Path

import numpy as np

import paper_restoration_design as d
from analyze_paper_memory import Checks, labels, expected_cases as p1_cases


def expected_cases():
    # Independent enumeration; never accept a shortened runner-generated panel.
    source='bridge__depol__s6__p60'
    replays=[source,'bridge__depol__s6__p8','bridge__hypol__s11__p60','bridge__nbrDepol__s11__p8']
    result=[dict(id='replay__'+s,kind='replay',source=s,fine=False) for s in replays]
    result += [dict(id='assay__'+l,kind='assay',label=l,source=source,fine=False) for l in ('E','M')]
    modes=[('neither','depol',60),('voltage','hypol',60),('expression','depol',1),('both','hypol',1)]
    settings=[('factorial',n,k,s,a,p,.5,False,False,False)
        for n in (2,6,11) for k in (1.25e-14,2e-13) for s,a,p in modes]
    settings += [('border',n,1.25e-14,s,a,p,0,False,False,False) for n in (2,6,11) for s,a,p in modes[:2]]
    settings += [('blocked',6,1.25e-14,s,a,p,.5,True,False,False) for s,a,p in modes]
    settings += [('alone',6,1.25e-14,s,a,p,.5,False,True,False) for s,a,p in modes[:2]]
    settings += [('factorial',6,k,s,a,p,.5,False,False,True) for k in (1.25e-14,2e-13)
                 for s,a,p in (modes if k==1.25e-14 else [modes[0],modes[3]])]
    for kind,n,k,s,a,p,oi,blocked,alone,fine in settings:
        result.append(dict(id=f'{kind}__s{n}__k{0 if k==1.25e-14 else 1}__{s}'+('__fine' if fine else ''),
            kind=kind,source=source,size=n,kd=k,strategy=s,algorithm=a,power=p,oi=oi,
            mirna_blocked=blocked,alone=alone,fine=fine))
    return result


def integrity(run, summary):
    try:
        manifests=summary['hashes_sha256'],summary['frozen_hashes_sha256'],summary['inputs']
        return dict(revision=summary['revision']==d.REVISION,
            complete_manifest=(set(manifests[0])==set(d.execution_manifest()) and
                set(manifests[1])=={p.name for p in d.LOCAL_FILES} and set(manifests[2])==set(d.input_paths())),
            execution=all(d.digest(d.ROOT/p)==h for p,h in manifests[0].items()),
            frozen=all(d.digest(run/'frozen'/p)==h for p,h in manifests[1].items()),
            sources=all(d.digest(Path(v['source']))==v['sha256'] for v in manifests[2].values()),
            inputs=all(d.digest(run/'inputs'/p)==v['sha256'] for p,v in manifests[2].items()))
    except (OSError,KeyError,RuntimeError):
        return dict(integrity_readable=False)


def source_arrays(inputs, name):
    folder=inputs/name
    info=json.loads((folder/'result.json').read_text())
    with np.load(folder/'preparation.npz',allow_pickle=False) as data:
        pre=data['concentrations'][-1].copy()
        bath=data['environment'].copy()
    with np.load(folder/'isolated_2.npz',allow_pickle=False) as data:
        held=data['final'].copy()
    return info,pre,held,bath


def expected_settings(case, phase, original):
    isolated=phase in ('isolated_1','isolated_2','onward_isolated_1','onward_isolated_2')
    if case['kind']=='replay':
        return original['algorithm'],original['power'],(0 if isolated else 8.801117367933935e-16),.5,isolated
    if phase=='restoration':
        iso=case['alone']
        return case['algorithm'],case['power'],(0 if iso or case['mirna_blocked'] else case['kd']),case['oi'],iso
    if phase=='onward_contact':
        return 'hypol',1,1.25e-14,.5,False
    return 'depol',1,0,.5,True


def audit_phase(folder,case,rec,idx,ids,original,checks):
    name=rec['phase']
    ck=lambda n,v: checks.add(case['id']+'/'+name+'/'+n,v)
    path=folder/(name+'.npz')
    ck('hash',d.digest(path)==rec['sha256'])
    with np.load(path,allow_pickle=False) as data:
        a=dict(data)
    setup=rec['setup']
    count=len(ids)
    algo,power,kd,oi,iso=expected_settings(case,name,original)
    horizon=20000 if name in ('restoration','onward_contact') else 10000
    ck('ids',setup['cell_ids']==ids and len(set(ids))==count)
    ck('shape',setup['cells']==count and a['initial'].shape==a['final'].shape==(len(idx),count)
       and a['concentrations'].shape[1:]==(len(idx),count))
    t=a['times']
    ck('times',t.ndim==1 and len(t)>=2 and len(t)==len(a['concentrations']) and
       t[0]>=0 and np.all(np.diff(t)>0) and bool(np.any(t>=.75*horizon)) and
       t[-1]==rec['last_sample_time'])
    ck('duration',rec['requested_horizon']==horizon and rec['samples']==len(t))
    for key in ('initial','concentrations','final'):
        ck(key+'_finite_nonnegative',np.isfinite(a[key]).all() and np.min(a[key])>=0)
        ck(key+'_snail',np.all(a[key][...,idx['snail'],:]==72))
    ck('native_labels',''.join(labels(a['final'],idx))==rec['final_labels'])
    ck('snapshot_difference',float(np.max(np.abs(a['concentrations'][-1]-a['final'])))==rec['last_snapshot_live_difference'])
    ck('line_topology',np.array_equal(a['edge_from'],np.arange(count-1)) and
       np.array_equal(a['edge_to'],np.arange(1,count)))
    ck('strategy',setup['algorithm']==algo and setup['power']==power and setup['mirna_kd']==kd
       and setup['isolated']==iso)
    neighbor=algo=='nbrDepol' and not iso
    ck('no_hidden_neighbor',setup['neighbor_voltage_reading']==neighbor)
    ck('cell_gate',setup['cell_voltage_gate_present']==(algo!='hypol'))
    ck('transport',not np.any(a['junction_diffusion']) if iso else bool(np.any(a['junction_diffusion'][:4])))
    ck('gate_inventory',setup['gate_classes']==dict(ic=[] if algo=='hypol' else ['set_Vmem_from_conc'],
        gj=['GJ_gate','tumor_overX_GJ_gate'],gd=['EMT_GRN_gate'],gj_add=['EMT_GJ_gate']))
    ck('integrator',setup['integrator']==dict(time_step=.00005 if case['fine'] else .0001,
        sim_integ_max_delt_cc=.0005 if case['fine'] else .001,
        sim_integ_max_delt_Vm=.00005 if case['fine'] else .0001,use_implicit=False))
    ck('expression_constants',setup['tumor_rule']==dict(x0=40.,M_ZEB_miR200=200000/18000,tness=1,GJ_OiET=oi))
    q=setup['voltage_constants']
    ck('voltage_constants',q['F']==96485 and q['cm']==.05 and
       np.isclose(q['cell_vol'],4*np.pi*(5e-6)**3/3,rtol=1e-14,atol=0) and
       np.isclose(q['cell_sa'],4*np.pi*(5e-6)**2,rtol=1e-14,atol=0))
    for k,v in (('A1',-110.),('A2',-110.),('VO1',-.0102),('VO2',-.0102)):
        ck('Cx45_'+k,np.all(a['gate_'+k]==v))
    ck('miRNA_size',np.all(a['gate_Gmin'][idx['miR200_total']]==0) and np.all(a['gate_Gdelta'][idx['miR200_total']]==1.56))
    for side in ('initial','final'):
        value=a[side]
        vm=(value*a['valences'][:,None]).sum(axis=0)*96485*q['cell_vol']/(q['cell_sa']*.05)
        ck('vm_'+side,np.allclose(vm,a['vm_'+side],rtol=1e-12,atol=1e-14))
        dv=vm[:-1]-vm[1:]
        voltage=1.56/(1+np.exp(-110*(-dv+.0102))+np.exp(-110*(dv+.0102)))
        ck('voltage_gate_'+side,np.allclose(voltage,a['voltage_gate_'+side],rtol=1e-10,atol=1e-12))
        mi,zeb,protein=(value[idx[n]] for n in ('miR200_total','Zeb_mRNA_total','ZEB_prot'))
        tp=(protein/(200000/18000+5))**10
        tumor=(1/(1+(mi/30)**10))*tp/(1+tp)
        lo=np.minimum(tumor[:-1],tumor[1:]); hi=np.maximum(tumor[:-1],tumor[1:])
        expression=1+(lo+oi*(hi-lo))*(power-1)
        ck('expression_'+side,np.allclose(expression,a['expression_gate_'+side],rtol=1e-12,atol=1e-12))
        potassium=np.ones(count)
        if algo!='hypol':
            hr=(mi/(.001+zeb))**10
            factor=hr/(1+hr)
            if neighbor:
                factor[1:]=np.minimum(factor[1:],1-tumor[:-1])
            potassium=1+30*factor
        ck('potassium_'+side,np.allclose(potassium,a['potassium_gate_'+side],rtol=1e-12,atol=1e-12))
    return a


def stable(first,second,idx,label):
    def check(a):
        late=labels(a['concentrations'][a['times']>=7500],idx)
        return (labels(a['final'],idx)==label) & (np.mean(late==label,axis=0)>=.95)
    return check(first)&check(second)


def branch(folder,case,checks):
    run=folder.parent
    info,pre,held,bath=source_arrays(run/'inputs',case['source'])
    result=json.loads((folder/'result.json').read_text())
    ck=lambda n,v:checks.add(case['id']+'/'+n,v)
    eq=lambda n,a,b:checks.equal(case['id']+'/'+n,a,b)
    original=next(c for c in p1_cases() if c['id']==case['source'])
    ck('source_case',info['case']==original)
    idx=result['ion_indices']
    ck('indices',idx==info['ion_indices'])
    ck('case',result['case']==case and result['execution_pass'])
    ck('no_retuning',not result['parameter_retuning'] and not result['outcome_dependent_selection'])
    ck('no_reproduction',not result['cell_division_simulated'] and not result['artificial_target_schedule'])
    source_ids=[f'original:{i:02d}' for i in range(original['tumor_size'],25)]
    ck('source_ids',next(r['setup']['cell_ids'] for r in info['phases'] if r['phase']=='isolated_2')==source_ids)
    names=['onward_contact','onward_isolated_1','onward_isolated_2']
    if case['kind'] not in ('replay','assay'):
        names=['restoration','isolated_1','isolated_2']+names
    ck('phase_list',[r['phase'] for r in result['phases']]==names)
    arrays={}
    for rec in result['phases']:
        name=rec['phase']
        if case['kind']=='replay':
            fresh=[f'onward:{i:02d}' for i in range(14)]
            ids=source_ids[:2]+fresh if name=='onward_contact' else fresh
        elif name=='restoration':
            n=case['size']
            ids=source_ids[:n]+([] if case['alone'] else [f'helper:{i:02d}' for i in range(25-n)])
        elif name in ('isolated_1','isolated_2'):
            ids=source_ids[:case['size']]
        elif name=='onward_contact':
            donors=['reference:00','reference:01'] if case['kind']=='assay' else source_ids[:2]
            ids=[donors[0],'probe:00',donors[1]]
        else:
            ids=['probe:00']
        arrays[name]=audit_phase(folder,case,rec,idx,ids,original,checks)
        eq('same_bath/'+name,arrays[name]['environment'],bath)
    if case['kind']=='replay':
        for name,a in arrays.items():
            with np.load(run/'inputs'/case['source']/(name+'.npz'),allow_pickle=False) as old:
                ck('replay_keys/'+name,set(a)==set(old.files))
                for key in a:
                    eq('replay/'+name+'/'+key,a[key],old[key])
        return dict(case=case,outcomes=dict(replayed_final_labels=''.join(labels(arrays['onward_isolated_2']['final'],idx)))),arrays,idx
    contact=arrays['onward_contact']
    eq('fresh_probe_M',contact['initial'][:,1:2],pre[:,:1])
    eq('probe_starts_M',labels(contact['initial'],idx)[1:2],list('M'))
    eq('probe_removed_donors',arrays['onward_isolated_1']['initial'],contact['final'][:,1:2])
    eq('probe_hold_continuity',arrays['onward_isolated_2']['initial'],arrays['onward_isolated_1']['final'])
    out=dict(probe_contact_label=str(labels(contact['final'],idx)[1]),
        probe_final_label=str(labels(arrays['onward_isolated_2']['final'],idx)[0]),
        probe_stable_E=bool(stable(arrays['onward_isolated_1'],arrays['onward_isolated_2'],idx,'E')[0]),
        probe_stable_M=bool(stable(arrays['onward_isolated_1'],arrays['onward_isolated_2'],idx,'M')[0]))
    if case['kind']=='assay':
        ref=pre[:,original['tumor_size']:original['tumor_size']+1] if case['label']=='E' else pre[:,:1]
        eq('reference_donors',contact['initial'][:,[0,2]],np.repeat(ref,2,axis=1))
    else:
        n=case['size']; restoration=arrays['restoration']
        eq('actual_exposed_start',restoration['initial'][:,:n],held[:,:n])
        eq('acquired_M_not_relabelled',labels(held[:,:n],idx),list('M'*n))
        if not case['alone']:
            eq('fresh_helpers',restoration['initial'][:,n:],np.repeat(pre[:,6:7],25-n,axis=1))
            eq('helpers_initially_E',labels(restoration['initial'],idx)[n:],list('E'*(25-n)))
        eq('withdrawal_no_reset',arrays['isolated_1']['initial'],restoration['final'][:,:n])
        eq('withdrawal_hold_continuity',arrays['isolated_2']['initial'],arrays['isolated_1']['final'])
        eq('fixed_carriers_even_if_failed',contact['initial'][:,[0,2]],arrays['isolated_2']['final'][:,:2])
        retained=stable(arrays['isolated_1'],arrays['isolated_2'],idx,'E')
        out.update(patch_size=n,patch_contact_E=int(np.sum(labels(restoration['final'],idx)[:n]=='E')),
            helper_contact_M=int(np.sum(labels(restoration['final'],idx)[n:]=='M')),
            patch_stable_E=int(retained.sum()),all_patch_stably_E=bool(retained.all()),
            carrier_labels=''.join(labels(arrays['isolated_2']['final'],idx)[:2]),
            two_carriers_stably_E=bool(retained[:2].all()),
            strict_onward_restoration=bool(retained[:2].all() and out['probe_stable_E']))
    mechanism={}
    if case['kind'] not in ('replay','assay') and not case['alone']:
        a=arrays['restoration']; border=case['size']-1
        for side in ('initial','final'):
            mechanism[side]=dict(border_dv=float(a['vm_'+side][border+1]-a['vm_'+side][border]),
                border_voltage_gate=float(a['voltage_gate_'+side][border]),
                border_expression=float(a['expression_gate_'+side][border]),
                patch_internal_expression_mean=float(np.mean(a['expression_gate_'+side][:border])),
                helper_internal_expression_mean=float(np.mean(a['expression_gate_'+side][border+1:])))
    return dict(case=case,outcomes=out,mechanism=mechanism),arrays,idx


def gate_audit(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    records={r['id']:r for r in summary['cases']}
    checks.add('predecessor_gate',summary['predecessor_gate'])
    reports=[]
    for c in expected_cases()[:6]:
        rec=records.get(c['id'])
        checks.add(c['id']+'/record',rec is not None and rec['execution_pass'])
        if rec is None or not rec['execution_pass']:
            continue
        report,_,_=branch(run/c['id'],c,checks); reports.append(report)
        if c['kind']=='assay':
            checks.add(c['id']+'/assay_qualification',report['outcomes']['probe_stable_'+c['label']])
    provenance=integrity(run,summary)
    return dict(quality_gate=all(checks.rows.values()) and all(provenance.values()) and len(reports)==6,
        checks=checks.rows,integrity=provenance,branches=reports)


def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    records={r['id']:r for r in summary['cases']}
    cases=expected_cases()
    checks.add('registered_cases',summary['config']['cases']==cases)
    checks.add('full_config',summary['config']==dict(d.FIXED,cases=cases) and
        summary['config']==json.loads((run/'frozen/paper_restoration_v1.json').read_text()))
    checks.add('case_set',set(records)=={c['id'] for c in cases} and len(summary['cases'])==48)
    checks.add('runner',summary.get('all_execution_valid',False))
    reports=[]; endpoints={}; calls=0
    for c in cases:
        rec=records.get(c['id']); checks.add(c['id']+'/record',rec is not None and rec['execution_pass'])
        if rec is None or not rec['execution_pass']:
            continue
        report,arrays,idx=branch(run/c['id'],c,checks); reports.append(report); calls+=len(arrays)
        endpoints[c['id']]={n:(a['final'],labels(a['final'],idx)) for n,a in arrays.items()}
    checks.add('integration_count',calls==270)
    gate=gate_audit(run)
    checks.add('gate_pass',gate['quality_gate'])
    checks.add('stored_gate',gate==summary['gate']==json.loads((run/'gate.json').read_text()) and
               d.digest(run/'gate.json')==summary['gate_sha256'])
    by_id={r['case']['id']:r for r in reports}; fine=[]
    for c in cases:
        if not c['fine'] or c['id'] not in endpoints:
            continue
        fine_id=c['id']; base=fine_id.removesuffix('__fine')
        comparisons={}
        for name,(a,la) in endpoints[fine_id].items():
            b,lb=endpoints[base][name]
            comparisons[name]=dict(labels_agree=bool(np.array_equal(la,lb)),
                maximum_absolute_difference=float(np.max(np.abs(a-b))),
                maximum_symmetric_relative_difference=float(np.max(np.abs(a-b)/np.maximum(1,np.maximum(np.abs(a),np.abs(b))))))
        same=by_id[fine_id]['outcomes']==by_id[base]['outcomes']
        checks.add(fine_id+'/fine',same and all(p['labels_agree'] for p in comparisons.values()))
        fine.append(dict(id=fine_id,baseline=base,outcomes_agree=same,phases=comparisons))
    checks.add('six_fine',len(fine)==6)
    provenance=integrity(run,summary)
    quality=all(checks.rows.values()) and all(provenance.values())
    return dict(run=str(run),quality_gate=quality,ready_for_interpretation=quality,
        independent_check_count=len(checks.rows),checks=checks.rows,integrity=provenance,
        gate=gate,branches=reports,fine_comparisons=fine,native_integrations=calls,
        all_selected_fine_agree=len(fine)==6 and all(f['outcomes_agree'] and
            all(v['labels_agree'] for v in f['phases'].values()) for f in fine),
        full_paper_replication=False,cell_division_simulated=False,clinical_therapy=False,
        autonomous_heredity_demonstrated=False,acquisition_histories_used=1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path); parser.add_argument('--save',action='store_true')
    parser.add_argument('--compact',action='store_true'); args=parser.parse_args(); run=args.run.resolve()
    if run.parent!=d.ROOT/'runs' or not run.name.startswith('paper-restoration-'):
        raise ValueError('Audit must address its own P2 output')
    report=analyze(run)
    if args.save: d.write_json(run/'independent_audit.json',report)
    if args.compact: report={k:v for k,v in report.items() if k not in ('checks','gate','fine_comparisons')}
    print(json.dumps(report,indent=2,allow_nan=False))
    return 0 if report['quality_gate'] else 1


if __name__=='__main__':
    raise SystemExit(main())
