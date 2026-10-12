"""Independent P4 identity/topology, regional native-equation and matched-contrast audit."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import paper_topology_design as d
from analyze_paper_memory import Checks,labels
from analyze_paper_restoration import stable
from analyze_paper_sheet import (arrays,edges,rectangle,bank_outcome,qualify,
    expected_cases as p3_cases)


def expected_cases():
    cases=[]
    rows=[('replay','depol','edge',3,v,p,p,p,False,'main__depol__edge__s3__'+s,'replay__'+s)
          for s,v,p in (('neither','depol',60),('voltage','hypol',60),
                        ('expression','depol',1),('both','hypol',1))]
    def item(row):
        k,h,l,n,v,i,b,hp,f,src,ident=row
        return dict(id=ident or f'{k}__{h}__{l}__s{n}__{v}__i{i}__b{b}'+('__fine' if f else ''),
            kind=k,history=h,location=l,side=n,algorithm=v,internal=i,boundary=b,helper=hp,
            fine=f,bank=f'bank__{h}__edge',source=src)
    cases.extend(map(item,rows))
    cases.extend(dict(id='assay__'+l,kind='assay',label=l,source='assay__'+l,fine=False) for l in 'EM')
    rows=[('main',h,l,n,v,i,b,60,False,None,None) for h,l,n,v,i,b in itertools.product(
        ('depol','nbrDepol','hypol'),('edge','centre'),(2,3),('depol','hypol'),(1,60),(1,60))]
    rows += [('helper',h,l,3,v,1,1,1,False,None,None) for h,l,v in itertools.product(
        ('depol','nbrDepol','hypol'),('edge','centre'),('depol','hypol'))]
    rows += [(k,h,l,3,'depol',60,60,60,False,None,None) for k,h,l in itertools.product(
        ('blocked','cut'),('depol','nbrDepol','hypol'),('edge','centre'))]
    rows += [('main','depol',l,3,v,i,b,60,True,None,None) for l,v,i,b in itertools.product(
        ('edge','centre'),('depol','hypol'),(1,60),(1,60))]
    cases.extend(map(item,rows))
    cases.extend(dict(id='capacity__'+l,kind='capacity',label=l,source=s,fine=False) for l,s in (
        ('ordinary_E','reference'),('ordinary_M','reference'),
        ('restored_E','main__depol__edge__s3__both'),
        ('failed_M','main__depol__edge__s3__expression')))
    return cases


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
    # ALL inputs came from the same edge position, even when rehomed centrally.
    n=case.get('side',3)
    old=[f'original:r{r:02d}:c{c:02d}' for r in range(n) for c in range(5,5+n)]
    capacity=case['kind']=='capacity'
    fresh=[f'new:{i:02d}' for i in range(3)] if capacity else ['probe:00']
    if phase.startswith('onward_isolated'): return [1,len(fresh)],fresh
    if phase=='onward_contact':
        carriers=[old[i] for i in (0,1,n)]
        if case['kind']=='assay' or (capacity and case['label'].startswith('ordinary')):
            carriers=['reference:00','reference:01','reference:02']
        return [2,3] if capacity else [2,2],carriers+fresh
    if phase=='restoration':
        ids=[f'helper:r{r:02d}:c{c:02d}' for r in range(13) for c in range(13)]
        for i,name in zip(rectangle(0 if case['location']=='edge' else 5,5,n),old): ids[i]=name
        return [13,13],ids
    return [n,n],old


def settings(case,phase):
    if phase=='restoration':
        return case['algorithm'],case['helper'],0 if case['kind']=='blocked' else 1.25e-14,False,20000
    if phase=='onward_contact': return 'hypol',1,1.25e-14,False,20000
    return 'depol',1,0,True,10000


def regional_settings(case,phase,shape,ids):
    if phase=='restoration':
        patch=[i for i,name in enumerate(ids) if name.startswith('original:')]
        i,b,h,cut=case['internal'],case['boundary'],case['helper'],case['kind']=='cut'
    else:
        patch=[0,1,2] if phase=='onward_contact' else list(range(len(ids))) if phase.startswith('isolated_') else []
        i=b=h=1; cut=False
    members=set(patch); fr,to=edges(shape)
    region=np.array([1 if f in members and t in members else
                     2 if (f in members)!=(t in members) else 0 for f,t in zip(fr,to)],dtype=np.int8)
    power=np.array([{0:h,1:i,2:b}[int(v)] for v in region],dtype=float)
    available=np.array([0. if v==2 and cut else 1. for v in region])
    return region,power,available,dict(internal=i,boundary=b,helper=h,boundary_cut=cut)


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


def branch(folder,case,checks):
    run=folder.parent; inputs=run/'inputs'; result=json.loads((folder/'result.json').read_text())
    ck=lambda n,v:checks.add(case['id']+'/'+n,v)
    eq=lambda n,x,y:checks.equal(case['id']+'/'+n,x,y)
    ck('case',result['case']==case and result['execution_pass'])
    ck('no_retuning',not result['parameter_retuning'] and not result['outcome_dependent_selection'])
    ck('scope',not result['cell_division_simulated'] and not result['artificial_target_schedule'] and
        result['serial_relay_rounds']==0 and result['source_external_regional_intervention'])
    idx=result['ion_indices']
    expected_idx=dict(Na=0,K=1,Cl=2,P=3,snail=4,miR200_total=5,Zeb_mRNA_total=6,ZEB_prot=7,
        miR200_free=8,**{f'bound{i}':9+i for i in range(7)},ST=16)
    ck('indices',idx==expected_idx)
    names=['onward_contact','onward_isolated_1','onward_isolated_2']
    if case['kind'] not in ('assay','capacity'): names=['restoration','isolated_1','isolated_2']+names
    ck('phase_list',[p['phase'] for p in result['phases']]==names)
    data={p['phase']:audit_phase(folder,case,p,idx,checks) for p in result['phases']}
    ref=arrays(inputs/'reference','preparation')
    for name,a in data.items(): eq('common_bath/'+name,a['environment'],ref['environment'])
    E,M=ref['concentrations'][-1,:,168:169],ref['concentrations'][-1,:,1:2]
    eq('reference_labels',labels(np.concatenate((E,M),axis=1),idx),['E','M'])
    contact,first,second=[data[n] for n in ('onward_contact','onward_isolated_1','onward_isolated_2')]
    count=3 if case['kind']=='capacity' else 1
    eq('fresh_probe',contact['initial'][:,3:],np.repeat(M,count,axis=1))
    eq('probe_starts_M',labels(contact['initial'],idx)[3:],list('M'*count))
    eq('remove_all_carriers',first['initial'],contact['final'][:,3:])
    eq('probe_continuity',second['initial'],first['final'])
    retained_E=stable(first,second,idx,'E'); retained_M=stable(first,second,idx,'M')
    out=dict(probe_contact_labels=''.join(labels(contact['final'],idx)[3:]),
        probe_final_labels=''.join(labels(second['final'],idx)),probe_stable_E=bool(retained_E.all()),
        probe_stable_M=bool(retained_M.all()),recipient_stable_E_count=int(retained_E.sum()),
        recipient_stable_M_count=int(retained_M.sum()))
    diagnostics={}
    if case['kind']=='assay' or (case['kind']=='capacity' and case['label'].startswith('ordinary')):
        eq('ordinary_carriers',contact['initial'][:,:3],np.repeat(E if case['label'][-1]=='E' else M,3,axis=1))
    elif case['kind']=='capacity':
        prior=arrays(inputs/case['source'],'isolated_2')
        eq('actual_capacity_carriers',contact['initial'][:,:3],prior['final'][:,[0,1,3]])
    else:
        n=case['side']; take=rectangle(0,0,n,3); bank=inputs/case['bank']
        bank_case=next(c for c in p3_cases() if c['id']==case['bank'])
        bank_info=json.loads((bank/'result.json').read_text())
        ck('source_case',bank_info['case']==bank_case and bank_case['location']=='edge' and not bank_case['blocked'])
        old_ids=[f'original:r{r:02d}:c{c:02d}' for r in range(3) for c in range(5,8)]
        ck('source_ids',next(p['setup']['cell_ids'] for p in bank_info['phases']
            if p['phase']=='acquired_isolated_2')==old_ids)
        source=arrays(bank,'acquired_isolated_2')['final'][:,take]
        restoration,held1,held2=[data[n] for n in ('restoration','isolated_1','isolated_2')]
        positions=rectangle(0 if case['location']=='edge' else 5,5,n)
        eq('actual_acquired_state',restoration['initial'][:,positions],source)
        helpers=[i for i in range(169) if i not in positions]
        eq('fresh_helpers',restoration['initial'][:,helpers],np.repeat(E,len(helpers),axis=1))
        eq('helpers_start_E',labels(restoration['initial'],idx)[helpers],list('E'*len(helpers)))
        eq('withdrawal_no_reset',held1['initial'],restoration['final'][:,positions])
        eq('withdrawal_continuity',held2['initial'],held1['final'])
        eq('fixed_carriers_without_selection',contact['initial'][:,:3],held2['final'][:,[0,1,n]])
        source_mask=np.asarray(bank_outcome(bank,bank_case,idx)['acquired_M_mask'])[take]
        out.update(qualify(source_mask,stable(held1,held2,idx,'E'),out['probe_stable_E']))
        out.update(patch_contact_E=int(np.sum(labels(restoration['final'],idx)[positions]=='E')),
            helper_contact_M=int(np.sum(labels(restoration['final'],idx)[helpers]=='M')),
            carrier_final_labels=''.join(labels(held2['final'],idx)[[0,1,n]]))
        regions=restoration['edge_region_initial']; border=regions==2
        ck('border_count',int(border.sum())==(3 if case['location']=='edge' else 4)*n)
        ck('internal_count',int(np.sum(regions==1))==2*n*(n-1))
        diagnostics=dict(internal_edges=int(np.sum(regions==1)),boundary_edges=int(border.sum()),
            helper_edges=int(np.sum(regions==0)),
            potential_boundary_mirna_gate_sum={s:float(np.sum(restoration['voltage_gate_'+s][border]*
                restoration['expression_gate_'+s][border])) for s in ('initial','final')},
            potential_gate_sum_is_not_net_flux=True)
    if case['kind']=='capacity':
        out.update(carrier_start_labels=''.join(labels(contact['initial'],idx)[:3]),old_carriers=3,
            new_recipients=3,three_to_three_capacity=bool(retained_E.all()),serial_renewal_demonstrated=False)
    if case['kind'] in ('replay','assay'):
        old=inputs/case['source']
        old_result=json.loads((old/'result.json').read_text())
        ck('replay_phase_list',[p['phase'] for p in old_result['phases']]==names)
        extra={k+'_'+s for k in ('edge_region','edge_power','edge_available') for s in ('initial','final')}
        for name,value in data.items():
            original=arrays(old,name)
            ck('replay/'+name+'/keys',set(value)==set(original)|extra)
            for key,arr in original.items(): eq('replay/'+name+'/'+key,value[key],arr)
    return dict(case=case,outcomes=out,diagnostics=diagnostics),data,idx


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
    old=json.loads((run/'inputs/independent_audit.json').read_text())
    checks.add('predecessor_record',old['quality_gate'] and old['independent_check_count']==18941 and old['native_integrations']==465)
    reports,_,calls=audited_records(run,expected_cases()[:6],checks)
    for report in reports:
        c=report['case']
        if c['kind']=='assay': checks.add(c['id']+'/qualification',report['outcomes']['probe_stable_'+c['label']])
    checks.add('gate_counts',len(reports)==6 and calls==30)
    provenance=integrity(run,summary)
    return dict(quality_gate=all(checks.rows.values()) and all(provenance.values()),
        checks=checks.rows,integrity=provenance,branches=reports)


def contrasts(reports,checks):
    main=[r for r in reports if r['case']['kind']=='main' and not r['case']['fine']]
    fields=('history','location','side','algorithm','internal','boundary')
    result={}
    for varied,levels in (('location',('edge','centre')),('internal',(1,60)),
                          ('boundary',(1,60)),('algorithm',('depol','hypol'))):
        group={}
        for r in main:
            c=r['case']; key=tuple(c[f] for f in fields if f!=varied)
            group.setdefault(key,{})[c[varied]]=r
        pairs=[]
        for key,items in sorted(group.items()):
            if set(items)!=set(levels): checks.add('pairs/'+varied+'/'+str(key),False); continue
            left,right=[items[v] for v in levels]; lo,hi=left['outcomes'],right['outcomes']
            pairs.append(dict(left=left['case']['id'],right=right['case']['id'],
                full_chain=[lo['strict_full_patch_chain'],hi['strict_full_patch_chain']],
                right_minus_left={k:int(hi[k])-int(lo[k]) for k in (
                    'patch_stable_E','strict_full_patch_chain','strict_carrier_chain','helper_contact_M','recipient_stable_E_count')}))
        checks.add('pairs/'+varied+'/count',len(pairs)==48); result[varied]=pairs
    # Helper-power changes must be contrasted separately from internal/border interventions.
    helpers=[]
    for r in reports:
        c=r['case']
        if c['kind']!='helper': continue
        match=[m for m in main if all(m['case'][f]==c[f] for f in fields)]
        checks.add(c['id']+'/matching_main',len(match)==1)
        if match:
            helpers.append(dict(left=c['id'],right=match[0]['case']['id'],helper_power=[1,60],
                full_chain=[r['outcomes']['strict_full_patch_chain'],match[0]['outcomes']['strict_full_patch_chain']]))
    checks.add('helper_pairs/count',len(helpers)==12); result['helper']=helpers
    return result


def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks(); cases=expected_cases()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_topology_v1.json').read_text()))
    checks.add('registered_cases',summary['registered_cases']==cases)
    checks.add('case_set',len(summary['cases'])==146 and {r['id'] for r in summary['cases']}=={c['id'] for c in cases})
    checks.add('runner',summary.get('all_execution_valid',False))
    reports,endpoints,calls=audited_records(run,cases,checks); checks.add('calls',calls==858)
    gate=gate_audit(run); checks.add('gate/pass',gate['quality_gate'])
    checks.add('gate/saved',summary['gate']==gate==json.loads((run/'gate.json').read_text()) and
        d.digest(run/'gate.json')==summary['gate_sha256'])
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
        same=by[fid]==by[base]; checks.add(fid+'/fine',same and all(x['labels_agree'] for x in phases.values()))
        fine.append(dict(id=fid,baseline=base,outcomes_agree=same,phases=phases))
    checks.add('all_sixteen_finer',len(fine)==16)
    pairs=contrasts(reports,checks)
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    main=[b['outcomes'] for b in reports if b['case']['kind']=='main' and not b['case']['fine']]
    totals=dict(main_cases=len(main),eligible_patches=sum(b['patch_eligible'] for b in main),
        full_patch_chains=sum(b['strict_full_patch_chain'] for b in main),
        fixed_carrier_chains=sum(b['strict_carrier_chain'] for b in main),
        helper_spread_cases=sum(b['helper_contact_M']>0 for b in main))
    return dict(run=str(run),quality_gate=quality,ready_for_interpretation=quality,
        independent_check_count=len(checks.rows),checks=checks.rows,integrity=provenance,
        gate=gate,branches=reports,native_integrations=calls,fine_comparisons=fine,paired_contrasts=pairs,
        all_selected_fine_agree=len(fine)==16 and all(f['outcomes_agree'] and all(p['labels_agree'] for p in f['phases'].values()) for f in fine),
        totals=totals,positive_capacity_required=False,source_histories=3,all_source_locations='edge',
        independent_random_replicates=False,full_paper_replication=False,clinical_therapy=False,
        cell_division_simulated=False,autonomous_heredity_demonstrated=False,serial_relay_rounds=0)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    run=args.run.resolve()
    if run.parent!=d.ROOT/'runs' or not run.name.startswith('paper-topology-'): raise ValueError('Not a P4 run')
    report=analyze(run)
    if args.save: d.write_json(run/'independent_audit.json',report)
    if args.compact: report={k:v for k,v in report.items() if k not in ('checks','gate','fine_comparisons','paired_contrasts')}
    print(json.dumps(report,indent=2,allow_nan=False)); return 0 if report['quality_gate'] else 1


if __name__=='__main__': raise SystemExit(main())

