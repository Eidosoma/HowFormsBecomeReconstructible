"""Independent P11 audit: fresh preparation, actual carriers, rewriting and renewal."""
import argparse
import json
from pathlib import Path
import re
import numpy as np
import paper_editable_lineage_design as d
from analyze_paper_memory import Checks,labels
from analyze_paper_restoration import stable
from analyze_paper_sheet import arrays,edges
from analyze_paper_contact_clock_recovery import audit_clock
import analyze_paper_contact_clock_recovery as prior

GRAPH=((0,1),(0,2),(1,3),(2,3),(1,4),(2,4),(1,5),(2,5))
STAGES=('stocks','calibration','before','rewrite','after')
HISTORIES=('written','ordinary')
SEED='p10r/inputs/p9/inputs/p8/inputs/p7/inputs/p3/reference'
INDEX=dict(Na=0,K=1,Cl=2,P=3,snail=4,miR200_total=5,Zeb_mRNA_total=6,ZEB_prot=7,
           miR200_free=8,**{f'bound{i}':9+i for i in range(7)},ST=16)


def spec(kind,condition='',history='',fine=False,route=''):
    fields=[kind]+([history] if history else [])+([condition] if condition else [])+([route] if route else [])
    return dict(id='__'.join(fields)+('__fine' if fine else ''),kind=kind,condition=condition,
                history=history,fine=fine,route=route)


def expected_stage(stage):
    result=[]
    for fine in (False,True):
        if stage=='stocks': result.append(spec('stock',fine=fine))
        elif stage=='calibration':
            for condition in ('M_open','E_sham','M_rna','M_cut','no_cue'):
                result.append(spec('write_M',condition,fine=fine))
            result.append(spec('age_M',fine=fine))
            for condition in ('E_open','E_rna','E_cut','M_sham'):
                result.append(spec('calibration_E',condition,fine=fine))
        elif stage=='before':
            for h in HISTORIES:
                for r in ('open','rna','cut'): result.append(spec('before',history=h,fine=fine,route=r))
        elif stage=='rewrite':
            for h in HISTORIES:
                for c in ('E_open','M_sham','E_rna','E_cut','no_cue'): result.append(spec('rewrite_E',c,h,fine))
        elif stage=='after':
            for h in HISTORIES:
                for c,r in (('E_open','open'),('E_open','rna'),('E_open','cut'),('M_sham','open'),('no_cue','open')):
                    result.append(spec('after',c,h,fine,r))
        else: raise ValueError('Unknown P11 stage')
    return result


def expected_cases(last='after'):
    return [c for stage in STAGES[:STAGES.index(last)+1] for c in expected_stage(stage)]


def source_spec(c):
    f=c['fine']; k=c['kind']
    if k=='before':
        return (spec('write_M','M_open',fine=f),'writing_isolated_2') if c['history']=='written' else (spec('age_M',fine=f),'age_isolated_2')
    if k=='rewrite_E': return spec('before',history=c['history'],fine=f,route='open'),'r03_isolated_2'
    if k=='after': return spec('rewrite_E',c['condition'],c['history'],f),'writing_isolated_2'
    return spec('stock',fine=f),'preparation'


def pupil_ids(c,n):
    tag='calibration' if c['kind']=='calibration_E' else c['kind']+':'+c['history']
    return [f'p11:{tag}:pupil:{n:02d}:{i:02d}' for i in range(3)]


def carrier_ids(c):
    if c['kind'] in ('rewrite_E','after'): return pupil_ids(spec('before',history=c['history']),3)
    if c['kind']=='calibration_E': return [f'p11:calibration:teacher:{i:02d}' for i in range(3)]
    history=c['history'] if c['kind']=='before' else 'ordinary' if c['kind']=='age_M' else 'written'
    return [f'p11:{history}:founder:{i:02d}' for i in range(3)]


def max_rounds(c): return 1 if c['kind']=='calibration_E' else 3
def first_round(c): return 4 if c['kind']=='after' else 1
def is_relay(c): return c['kind'] in ('before','after','calibration_E')


def phase_names(c,nrounds=1):
    if c['kind']=='stock': return ['preparation']
    if not is_relay(c):
        prefix='age_' if c['kind']=='age_M' else 'writing_'
        return [prefix+x for x in ('contact','isolated_1','isolated_2')]
    start=first_round(c)
    return [f'r{n:02d}_'+part for n in range(start,start+nrounds)
            for part in ('segment_01','segment_02','segment_03','segment_04','isolated_1','isolated_2')]


def parts(c,name):
    if not is_relay(c):
        if name not in phase_names(c): raise ValueError('Unknown fixed phase')
        return 0,name
    match=re.fullmatch(r'r([0-9]{2})_(.+)',name)
    if not match or name not in phase_names(c,max_rounds(c)): raise ValueError('Unregistered relay phase')
    return int(match[1]),match[2]


def is_graph(c,name): return is_relay(c) and parts(c,name)[1].startswith('segment')
def no_cue(c): return c['kind']=='age_M' or c['condition']=='no_cue'


def geometry(c,name):
    n,part=parts(c,name)
    if c['kind']=='stock':
        return [13,13],[f'original:r{r:02d}:c{k:02d}' for r in range(13) for k in range(13)]
    if is_relay(c):
        ids=carrier_ids(c) if n==first_round(c) else pupil_ids(c,n-1)
        pupils=pupil_ids(c,n)
        return ([1,6],ids+pupils) if is_graph(c,name) else ([1,3],pupils)
    ids=carrier_ids(c)
    if name.endswith('_contact') and not no_cue(c):
        return [3,3],[f'p11:{c["kind"]}:{c["history"]}:cue:{i:02d}' for i in range(6)]+ids
    return [1,3],ids


def relay_route(c):
    if c['kind']=='calibration_E':
        suffix=c['condition'].rsplit('_',1)[-1]
        return suffix if suffix in ('rna','cut') else 'open'
    return c['route']


def phase_active(c,name):
    if not is_graph(c,name): return []
    slot=int(name[-2:])-1
    return [slot] if slot<3 else []


def phase_edges(c,name):
    return np.array(GRAPH).T if is_graph(c,name) else edges(geometry(c,name)[0])


def settings(c,name):
    if c['kind']=='stock': return 'depol',1,0,False,1000
    if is_graph(c,name): return 'depol',60,0 if relay_route(c)=='rna' else 1.25e-14,False,20000
    if name.endswith('_contact'):
        if c['kind']=='age_M': return 'depol',1,0,True,20000
        return 'depol',60,0 if no_cue(c) or c['condition'].endswith('_rna') else 1.25e-14,no_cue(c),20000
    return 'depol',1,0,True,10000


def logical_interval(c,name):
    if c['kind']=='stock': return [0,1000]
    if not is_relay(c):
        base=340000 if c['kind']=='rewrite_E' else 0
        offset=0 if name.endswith('_contact') else 20000 if name.endswith('_1') else 30000
        return [base+offset,base+offset+(20000 if offset==0 else 10000)]
    n,part=parts(c,name)
    base=(40000 if c['kind']=='before' else 380000 if c['kind']=='after' else 0)+(n-first_round(c))*100000
    if part.startswith('segment'): offset=20000*(int(part[-2:])-1); span=20000
    else: offset=80000 if part.endswith('_1') else 90000; span=10000
    return [base+offset,base+offset+span]


def regional_settings(c,name):
    _,power,_,_,_=settings(c,name); fr,to=phase_edges(c,name)
    cut=(is_graph(c,name) and relay_route(c)=='cut') or (
        not is_relay(c) and name.endswith('_contact') and c['condition'].endswith('_cut'))
    if is_graph(c,name):
        regions=np.array([1,1]+[2]*6,dtype=np.int8); active=phase_active(c,name)
        available=np.array([1.,1.]+[float(i in active and not cut) for i in range(3) for _ in range(2)])
    else:
        member=set(range(6)) if c['kind'] in ('write_M','rewrite_E') and name.endswith('_contact') and not no_cue(c) else set()
        regions=np.array([1 if f in member and t in member else 2 if (f in member)!=(t in member) else 0
                          for f,t in zip(fr,to)],dtype=np.int8)
        available=np.array([0. if r==2 and cut else 1. for r in regions])
    return regions,np.full(len(fr),power,dtype=float),available,dict(internal=power,boundary=power,helper=power,boundary_cut=cut)


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
    if is_graph(case,name):
        ck('geometry',setup['grid_shape'] is None and setup['storage_shape']==[1,6] and
            setup['orthogonal_only'] is False and setup['periodic'] is False and
            setup['network_mode']=='explicit_common_graph' and setup['explicit_edges']==[list(e) for e in GRAPH])
        ck('schedule_mask',setup['scheduled_pupils']==phase_active(case,name) and setup['route']==relay_route(case))
    else:
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
    audit_clock(a,rec,case,checks)
    return a


def stock(run,fine):
    x=arrays(run/spec('stock',fine=fine)['id'],'preparation')
    return x['final'][:,168:169],x['final'][:,1:2]


def branch(folder,c,checks):
    run=folder.parent; result=json.loads((folder/'result.json').read_text())
    ck=lambda n,v:checks.add(c['id']+'/'+n,v); eq=lambda n,x,y:checks.equal(c['id']+'/'+n,x,y)
    ck('case',result['case']==c and result['execution_pass'] is True)
    ck('indices',result['ion_indices']==INDEX); idx=result['ion_indices']
    ck('positive_scope',all(result.get(k) is True for k in ('all_new_integrations_bounded','external_schedule','all_cells_evolve')))
    ck('negative_scope',all(result.get(k) is False for k in ('historical_endpoint_used_as_founder',
        'teachers_retained_between_rounds','cues_retained_after_writing','cell_division_simulated',
        'parameter_retuning','outcome_dependent_cell_selection','cross_branch_pooling',
        'extra_donor_supplementation','independent_random_replicates','automatic_follow_on')))
    ck('clock_method',result['clock_method']=='native_explicit_euler_bounded_clock_v1')
    if c['kind']=='stock': ck('no_historical_source',result['source_case'] is None and result['source_phase'] is None)
    else:
        src,phase=source_spec(c); ck('source_binding',result['source_case']==src['id'] and result['source_phase']==phase)
    rounds=result['rounds']
    ck('round_count',(1<=len(rounds)<=max_rounds(c)) if is_relay(c) else rounds==[])
    ck('phase_list',[p['phase'] for p in result['phases']]==phase_names(c,len(rounds) if is_relay(c) else 1))
    data={p['phase']:audit_phase(folder,c,p,idx,checks) for p in result['phases']}
    witness=arrays(run/'inputs'/SEED,'preparation')
    for name,value in data.items(): eq('native_bath/'+name,value['environment'],witness['environment'])
    derived=[]
    if c['kind']=='stock':
        eq('fresh_native_initialization',data['preparation']['initial'],witness['initial'])
        x=data['preparation']['final']; pair=labels(x[:,[168,1]],idx)
        out=dict(stock_E_label=str(pair[0]),stock_M_label=str(pair[1]),ready=bool(np.array_equal(pair,['E','M'])))
    else:
        E,M=stock(run,c['fine'])
        src,srcphase=source_spec(c)
        if c['kind'] in ('write_M','age_M','rewrite_E'):
            prefix='age_' if c['kind']=='age_M' else 'writing_'
            one,two,three=(data[prefix+n] for n in ('contact','isolated_1','isolated_2'))
            offset=0 if no_cue(c) else 6
            source=arrays(run/src['id'],srcphase)['final'] if c['kind']=='rewrite_E' else np.repeat(M if c['kind']=='age_M' else E,3,axis=1)
            eq('all_actual_targets',one['initial'][:,offset:],source)
            eq('target_start_labels',labels(one['initial'],idx)[offset:],list('EEE' if c['kind']=='write_M' else 'MMM'))
            if not no_cue(c):
                cue=E if c['condition'].startswith('E') else M
                eq('fresh_cues',one['initial'][:,:6],np.repeat(cue,6,axis=1))
            eq('remove_all_cues',two['initial'],one['final'][:,offset:])
            eq('hold_continuity',three['initial'],two['final'])
            e,m=stable(two,three,idx,'E'),stable(two,three,idx,'M')
            out=dict(retained_E=e.tolist(),retained_M=m.tolist(),all_E=bool(e.all()),all_M=bool(m.all()),
                     final_labels=''.join(labels(three['final'],idx)))
        else:
            desired='M' if c['kind']=='before' else 'E'; opposite='E' if desired=='M' else 'M'
            recipient=E if opposite=='E' else M
            carry=(np.repeat(M if c['condition']=='M_sham' else E,3,axis=1) if c['kind']=='calibration_E'
                   else arrays(run/src['id'],srcphase)['final'])
            out_rounds=[]
            for index in range(len(rounds)):
                n=first_round(c)+index; prefix=f'r{n:02d}_'
                start=data[prefix+'segment_01']
                eq(prefix+'actual_teachers',start['initial'][:,:3],carry)
                eq(prefix+'fresh_opposite_recipients',start['initial'][:,3:],np.repeat(recipient,3,axis=1))
                eq(prefix+'recipient_start_labels',labels(start['initial'],idx)[3:],list(opposite*3))
                presignal=[]
                for slot in range(1,5):
                    name=prefix+f'segment_{slot:02d}'
                    if slot>1: eq(name+'/all_six_continuous',data[name]['initial'],data[prefix+f'segment_{slot-1:02d}']['final'])
                    if slot<=3: presignal.append(str(labels(data[name]['initial'],idx)[slot+2]))
                last=data[prefix+'segment_04']; one=data[prefix+'isolated_1']; two=data[prefix+'isolated_2']
                eq(prefix+'remove_every_teacher',one['initial'],last['final'][:,3:])
                eq(prefix+'two_holds_continuous',two['initial'],one['final'])
                e,m=stable(one,two,idx,'E'),stable(one,two,idx,'M')
                target=m if desired=='M' else e; opposite_mask=e if desired=='M' else m
                derived.append(dict(round=n,desired=desired,retained=target.tolist(),complete=bool(target.all()),
                    presignal_labels=''.join(presignal),logical_end=logical_interval(c,prefix+'isolated_2')[1]))
                out_rounds.append(dict(round=n,retained_E=e.tolist(),retained_M=m.tolist(),
                    teachers_at_end=''.join(labels(last['final'],idx)[:3]),pupils_at_end=''.join(labels(two['final'],idx)),
                    all_opposite=bool(opposite_mask.all())))
                carry=two['final']
            ck('round_records',rounds==derived)
            ck('no_continue_after_failure',all(r['complete'] for r in derived[:-1]))
            ck('no_early_stop',not derived[-1]['complete'] or len(derived)==max_rounds(c))
            out=dict(complete_all=bool(len(derived)==max_rounds(c) and all(r['complete'] for r in derived)),
                all_presignal_opposite=all(r['presignal_labels']==opposite*3 for r in derived),
                first_round_negative=bool(len(derived)==1 and out_rounds[-1]['all_opposite']),
                round_outcomes=out_rounds)
    expected_stop=('complete_registered_rounds' if derived and derived[-1]['complete'] else 'first_incomplete_round') if is_relay(c) else 'fixed_phase_complete'
    ck('stop_reason',result['stop_reason']==expected_stop)
    return dict(case=c,rounds=derived,outcomes=out),data,idx


def audited_records(run,cases,checks):
    summary=json.loads((run/'summary.json').read_text()); records={r['id']:r for r in summary['cases']}
    reports=[]; endpoints={}; calls=0
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and json.loads(path.read_text())==row['result'])
        report,data,idx=branch(run/c['id'],c,checks); reports.append(report); calls+=len(data)
        endpoints[c['id']]={n:(x['initial'],x['final'],labels(x['final'],idx)) for n,x in data.items()}
    return reports,endpoints,calls


def compare_fine(cases,reports,endpoints,checks):
    by={r['case']['id']:r for r in reports}; comparisons=[]
    for c in cases:
        fid=c['id']
        if not c['fine']: continue
        base=fid.removesuffix('__fine')
        if fid not in endpoints or base not in endpoints:
            checks.add(fid+'/fine_present',False); continue
        first=phase_names(c)[0]
        if c['kind']=='stock':
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



def eligibility(stage,by):
    requirements=[]
    for c in expected_stage(stage):
        out=by.get(c['id'],{}); k=c['kind']
        if stage=='stocks': value=out.get('ready',False)
        elif stage=='calibration':
            if k=='write_M': value=out.get('all_M' if c['condition']=='M_open' else 'all_E',False)
            elif k=='age_M': value=out.get('all_M',False)
            elif c['condition']=='E_open': value=out.get('complete_all',False) and out.get('all_presignal_opposite',False)
            else: value=out.get('first_round_negative',False)
        elif stage=='before':
            value=(out.get('complete_all',False) and out.get('all_presignal_opposite',False)) if c['route']=='open' else out.get('first_round_negative',False)
        elif stage=='rewrite': value=out.get('all_E' if c['condition']=='E_open' else 'all_M',False)
        else:
            main=c['condition']=='E_open' and c['route']=='open'
            value=(out.get('complete_all',False) and out.get('all_presignal_opposite',False)) if main else out.get('first_round_negative',False)
        requirements.append(dict(id=c['id'],qualified=bool(value)))
    return requirements


def stage_audit(run,stage):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    cases=expected_cases(stage); reports,endpoints,calls=audited_records(run,cases,checks)
    fine=compare_fine(cases,reports,endpoints,checks); by={b['case']['id']:b['outcomes'] for b in reports}
    requirements=eligibility(stage,by)
    for earlier in STAGES[:STAGES.index(stage)]:
        checks.add('qualified_predecessor/'+earlier,all(r['qualified'] for r in eligibility(earlier,by)))
    predecessor=summary.get('predecessor_audit',{})
    checks.add('history_checked',summary.get('predecessor_gate') is True and predecessor.get('quality_gate') is True)
    checks.add('history_saved',predecessor==json.loads((run/'predecessor_audit.json').read_text()) and
        d.digest(run/'predecessor_audit.json')==summary.get('predecessor_audit_sha256'))
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    return dict(stage=stage,quality_gate=bool(quality),eligible=bool(quality and all(r['qualified'] for r in requirements)),
        requirements=requirements,checks=checks.rows,integrity=provenance,branches=reports,
        fine_comparisons=fine,integration_calls=calls,cumulative_cases=len(reports))


def predecessor_audit(run):
    saved=json.loads((run/'inputs/p10r/independent_audit.json').read_text())
    original=prior.analyze(d.PREDECESSOR); archived=prior.analyze(run/'inputs/p10r')
    archived['run']=str(d.PREDECESSOR)
    good=original==archived==saved and original['quality_gate'] and original['independent_check_count']==47340
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_matches_saved=archived==saved,
        prior_checks=original['independent_check_count'],prior_calls=original['native_integrations'],
        history_is_audit_input_only=True)


def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_editable_lineage_v1.json').read_text()))
    checks.add('registration',summary['registered_cases']==expected_cases())
    stages=summary.get('attempted_stages',[])
    checks.add('stage_prefix',bool(stages) and stages==list(STAGES[:len(stages)]))
    history=predecessor_audit(run)
    checks.add('predecessor_fresh',history['quality_gate'] and history==summary['predecessor_audit'])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report
        checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==json.loads((run/(stage+'_audit.json')).read_text()) and
            d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
        if stage!=stages[-1]: checks.add(stage+'/eligible_before_proceeding',report['eligible'])
    last=stages[-1]; expected=expected_cases(last); final=reports[last]
    checks.add('case_count',len(summary['cases'])==len(expected) and
        {r['id'] for r in summary['cases']}=={c['id'] for c in expected})
    checks.add('gates_complete',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    checks.add('valid_stop',summary.get('completion_reason')=='after_completed' if last=='after' else
        summary.get('completion_reason')==last+'_not_qualified' and not final['eligible'])
    checks.add('bounded_calls',final['integration_calls']<=722)
    provenance=integrity(run,summary)
    quality=all(checks.rows.values()) and all(provenance.values())
    qualified=[]
    if last=='after':
        by={b['case']['id']:b['outcomes'] for b in final['branches']}
        after_req={r['id']:r['qualified'] for r in eligibility('after',by)}
        for h in HISTORIES:
            qualified.append(dict(history=h,qualified=all(after_req[c['id']] for c in expected_stage('after') if c['history']==h)))
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),
        checks=checks.rows,independent_check_count=len(checks.rows)+len(final['checks']),
        integrity=provenance,predecessor=history,stages=reports,integration_calls=final['integration_calls'],
        completed_cases=len(summary['cases']),completion_reason=summary.get('completion_reason'),
        fine_comparisons=final['fine_comparisons'],all_fine_agree=all(x['agree'] for x in final['fine_comparisons']),
        editable_lineages=qualified,control_qualified_editable_lineages=sum(x['qualified'] for x in qualified),
        newly_simulated_rounds=sum(len(b['rounds']) for b in final['branches']),
        all_new_integrations_bounded=True,historical_endpoint_used_as_founder=False,
        independent_random_replicates=False,external_schedule=True,autonomous_reproduction=False,
        unique_PH_demonstrated=False,automatic_follow_on=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    report=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',report)
    names=('quality_gate','completed_cases','integration_calls','independent_check_count',
           'all_fine_agree','editable_lineages','completion_reason')
    print(json.dumps({k:report.get(k) for k in names} if args.compact else report,indent=2))
    return 0 if report['quality_gate'] else 1


if __name__=='__main__': raise SystemExit(main())

