"""Independent P12 audit of fixed draws, exact dose, live lineage continuity and denominators."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import paper_lineage_robustness_design as d
import analyze_paper_editable_lineage as p11
from analyze_paper_memory import Checks,labels
from analyze_paper_restoration import stable
from analyze_paper_sheet import arrays,edges
from analyze_paper_contact_clock_recovery import audit_clock

INDEX=dict(Na=0,K=1,Cl=2,P=3,snail=4,miR200_total=5,Zeb_mRNA_total=6,ZEB_prot=7,
           miR200_free=8,**{f'bound{i}':9+i for i in range(7)},ST=16)
GRAPH=((0,1),(0,2),(1,3),(2,3),(1,4),(2,4),(1,5),(2,5))
STAGES=('baseline','timing','cells','combined','controls')
LEVELS=('mild','strong')
HISTORIES=('written','ordinary')
CONTROLS=('before_rna','before_cut','after_rna','after_cut','rewrite_sham','rewrite_none')
TEST_SEEDS=(201,202,203)

def spec(stage,label='',level='',seed=0,history='ordinary',route='open',fine=False):
    fields=[stage]+[str(v) for v in (label,level,seed,history,route) if v!='']
    return dict(id='__'.join(fields)+('__fine' if fine else ''),stage=stage,label=label,
                level=level,seed=seed,history=history,route=route,fine=fine)

def expected_stage(stage):
    out=[]
    for fine in (False,True):
        if stage=='baseline':
            out.extend(spec(stage,label=label,fine=fine) for label in ('M','E'))
        elif stage in ('timing','cells'):
            for level in ('mild','strong'):
                for label in ('M','E'):
                    for seed in (101,102): out.append(spec(stage,label,level,seed,fine=fine))
                    for route in ('rna','cut'): out.append(spec(stage,label,level,101,route=route,fine=fine))
        elif stage in ('combined','controls'):
            for history in ('written','ordinary'):
                for seed in (201,202,203):
                    kinds=('open',) if stage=='combined' else CONTROLS+(('founder_none',) if history=='written' else ())
                    for route in kinds: out.append(spec(stage,seed=seed,history=history,route=route,fine=fine))
        else: raise ValueError('Unknown stage')
    return out

def expected_cases(last='controls'):
    return [c for stage in STAGES[:STAGES.index(last)+1] for c in expected_stage(stage)]

def random_word(seed,domain,index):
    raw=('P12_lineage_robustness_v1|%d|%s|%d'%(seed,domain,index)).encode('ascii')
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],'big')

def expected_draws():
    domains=['timing:r%02d'%n for n in range(1,7)]+['protein:founder']+['protein:r%02d'%n for n in range(1,7)]
    return {str(s):{name:['%016x'%random_word(s,name,i) for i in range(3)] for name in domains}
            for s in (0,101,102,201,202,203)}

def challenge(c,selection):
    if c['stage']=='baseline': return None,None
    if c['stage']=='timing': return c['level'],None
    if c['stage']=='cells': return None,c['level']
    return selection['timing'],selection['cells']

def schedule(seed,n,level):
    cap={None:0,'mild':20,'strong':50}[level]
    gaps=[100*((random_word(seed,'timing:r%02d'%n,i)*(cap+1))//(1<<64)) if cap else 0 for i in range(3)]
    windows=[]; cursor=0
    for i,gap in enumerate(gaps):
        cursor+=gap; windows.append((cursor,cursor+20000)); cursor+=20000
    bounds=sorted({0,80000}|{x for pair in windows for x in pair})
    return [(left,right,[i for i,(start,stop) in enumerate(windows) if start<=left and right<=stop])
            for left,right in zip(bounds,bounds[1:])]

def incoming(stock,seed,role,level):
    cap={None:0,'mild':10,'strong':25}[level]
    values=np.repeat(stock,3,axis=1)
    for i in range(3):
        percent=(random_word(seed,'protein:'+role,i)*(2*cap+1)//(1<<64)-cap) if cap else 0
        values[7,i]=values[7,i]*(1+percent/100)
    return values

def root_id(c):
    if c['stage'] in ('combined','controls'): return 'p12:combined:%s:%d'%(c['history'],c['seed'])
    return 'p12:%s:%s:%s:%d'%(c['stage'],c['label'],c['level'],c['seed'])

def founders(c): return [root_id(c)+':founder:%02d'%i for i in range(3)]
def pupils(c,n): return [root_id(c)+':pupil:%02d:%02d'%(n,i) for i in range(3)]
def parent(c): return spec('combined',seed=c['seed'],history=c['history'],fine=c['fine'])

def archived_donor(c):
    suffix='__fine' if c['fine'] else ''
    if c['label']=='M':
        return 'age_M'+suffix,'age_isolated_2',['p11:ordinary:founder:%02d'%i for i in range(3)]
    return 'rewrite_E__ordinary__E_open'+suffix,'writing_isolated_2',[
        'p11:before:ordinary:pupil:03:%02d'%i for i in range(3)]

def stock(run,fine):
    x=arrays(run/'inputs/p11'/('stock'+('__fine' if fine else '')),'preparation')['final']
    return x[:,168:169],x[:,1:2]

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

def descriptor(name,ids,base,span,graph=False,active=(),route='open',cue=False,nocue=False,age=False):
    shape=[1,6] if graph else [3,3] if cue else [1,3]
    iso=not graph and not cue
    power=60 if graph or cue or nocue else 1
    if age: power=1
    kd=1.25e-14 if (graph and route!='rna') or cue else 0
    fr,to=np.array(GRAPH).T if graph else edges(shape)
    cut=graph and route=='cut'
    if graph:
        regions=np.array([1,1,2,2,2,2,2,2],dtype=np.int8)
        available=np.array([1.,1.]+[float(i in active and not cut) for i in range(3) for _ in range(2)])
    else:
        member=set(range(6)) if cue else set()
        regions=np.array([1 if f in member and t in member else 2 if (f in member)!=(t in member) else 0
                          for f,t in zip(fr,to)],dtype=np.int8)
        available=np.ones(len(fr))
    return dict(name=name,ids=ids,shape=shape,base=base,horizon=span,graph=graph,active=list(active),route=route,
        power=power,kd=kd,isolated=iso,fr=fr,to=to,regions=regions,powers=np.full(len(fr),power,dtype=float),
        available=available,compartments=dict(internal=power,boundary=power,helper=power,boundary_cut=cut))


def audit_phase(folder,case,rec,layout,checks):
    idx=INDEX
    name=rec['phase']; ck=lambda n,v:checks.add(case['id']+'/'+name+'/'+n,v)
    ck('hash',d.digest(folder/(name+'.npz'))==rec['sha256']); a=arrays(folder,name)
    shape,ids=layout['shape'],layout['ids']; algo='depol'
    power,kd,iso,horizon=(layout[k] for k in ('power','kd','isolated','horizon'))
    count=len(ids); setup=rec['setup']; fr,to=layout['fr'],layout['to']
    regions,powers,available,compartments=(layout[k] for k in ('regions','powers','available','compartments'))
    ck('compartments',setup['compartment_expression']==compartments)
    for side in ('initial','final'):
        for k,v in (('region',regions),('power',powers),('available',available)):
            ck('edge_'+k+'_'+side,np.array_equal(a['edge_'+k+'_'+side],v))
    ck('shape',a['initial'].shape==a['final'].shape==(17,count) and a['concentrations'].shape[1:]==(17,count))
    ck('ids',setup['cell_ids']==ids and len(set(ids))==count and setup['cells']==count)
    if layout['graph']:
        ck('geometry',setup['grid_shape'] is None and setup['storage_shape']==[1,6] and
            setup['orthogonal_only'] is False and setup['periodic'] is False and
            setup['network_mode']=='explicit_common_graph' and setup['explicit_edges']==[list(e) for e in GRAPH])
        ck('schedule_mask',setup['scheduled_pupils']==layout['active'] and setup['route']==layout['route'])
    else:
        ck('geometry',setup['grid_shape']==shape and setup['orthogonal_only'] is True and setup['periodic'] is False)
    ck('topology',np.array_equal(a['edge_from'],fr) and np.array_equal(a['edge_to'],to))
    times=a['times']
    ck('time_axis',times.ndim==1 and len(times)>=2 and len(times)==len(a['concentrations']) and
        times[0]>=0 and np.all(np.diff(times)>0) and np.any(times>=.75*horizon))
    ck('logical_interval',rec.get('logical_interval')==[layout['base'],layout['base']+horizon])
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



class Reader:
    def __init__(self,folder,c,selection,checks):
        self.folder,self.c,self.selection,self.checks=folder,c,selection,checks
        self.result=json.loads((folder/'result.json').read_text()); self.records=self.result['phases']
        self.at=0; self.data={}
        witness=arrays(folder.parent/'inputs/p11'/('stock'+('__fine' if c['fine'] else '')),'preparation')
        self.environment=witness['environment']
    def ck(self,name,value): self.checks.add(self.c['id']+'/'+name,value)
    def eq(self,name,x,y): self.checks.equal(self.c['id']+'/'+name,x,y)
    def take(self,layout,initial):
        name=layout['name']
        if self.at>=len(self.records): raise ValueError('Missing registered phase '+name)
        rec=self.records[self.at]; self.at+=1
        self.ck(name+'/ordered_phase',rec['phase']==name)
        if rec['phase']!=name: raise ValueError('Unexpected phase order')
        value=audit_phase(self.folder,self.c,rec,layout,self.checks)
        self.eq(name+'/actual_initial',value['initial'],initial)
        self.eq(name+'/native_bath',value['environment'],self.environment)
        self.data[name]=value
        return value['final']
    def masks(self,prefix):
        one,two=(self.data[prefix+x] for x in ('isolated_1','isolated_2'))
        return {lab:stable(one,two,INDEX,lab).tolist() for lab in ('E','M')}
    def finish(self,out):
        self.ck('indices',self.result['ion_indices']==(INDEX if out['available'] else None))
        self.ck('no_extra_phases',self.at==len(self.records))
        self.ck('independent_outcome',self.result['outcome']==out)
        return dict(case=self.c,outcome=out),self.data

def writer(rd,targets,ids,E,M,prefix,mode,desired,base):
    nocue=mode in ('none','age')
    cue=E if mode=='E' else M
    cueids=[root_id(rd.c)+':%s:cue:%02d'%(prefix,i) for i in range(6)]
    contact=rd.take(descriptor(prefix+'contact',ids if nocue else cueids+ids,base,20000,
        cue=not nocue,nocue=nocue,age=mode=='age'),
        targets if nocue else np.concatenate((np.repeat(cue,6,axis=1),targets),axis=1))
    held=rd.take(descriptor(prefix+'isolated_1',ids,base+20000,10000),contact if nocue else contact[:,6:])
    held=rd.take(descriptor(prefix+'isolated_2',ids,base+30000,10000),held)
    masks=rd.masks(prefix)
    return held,dict(name=prefix,desired=desired,retained_E=masks['E'],retained_M=masks['M'],qualified=all(masks[desired]))

def handover(rd,carry,ids,stock,timing,protein,n,desired,route,base):
    c=rd.c; fresh=pupils(c,n); initial=incoming(stock,c['seed'],'r%02d'%n,protein)
    initial_labels=''.join(labels(initial,INDEX)); value=np.concatenate((carry,initial),axis=1)
    prefix='r%02d_'%n; presignal=[None,None,None]
    slots=schedule(c['seed'],n,timing)
    rd.ck(prefix+'exact_dose',[sum(b-a for a,b,active in slots if i in active) for i in range(3)]==[20000]*3)
    rd.ck(prefix+'window',sum(b-a for a,b,active in slots)==80000 and slots[0][0]==0 and slots[-1][1]==80000)
    for slot,(start,end,active) in enumerate(slots,1):
        for i in active:
            if presignal[i] is None: presignal[i]=str(labels(value[:,3+i:4+i],INDEX)[0])
        value=rd.take(descriptor(prefix+'segment_%02d'%slot,ids+fresh,base+start,end-start,
                                graph=True,active=active,route=route),value)
    value=rd.take(descriptor(prefix+'isolated_1',fresh,base+80000,10000),value[:,3:])
    value=rd.take(descriptor(prefix+'isolated_2',fresh,base+90000,10000),value)
    masks=rd.masks(prefix); opposite='E' if desired=='M' else 'M'
    row=dict(round=n,desired=desired,retained_E=masks['E'],retained_M=masks['M'],
        initial_labels=initial_labels,presignal_labels=''.join(presignal),
        complete=all(masks[desired]) and initial_labels==opposite*3 and presignal==[opposite]*3,
        negative=all(masks[opposite]),logical_end=base+100000)
    return value,fresh,row

def held_mask(folder,prefix,lab):
    paths=[folder/(prefix+s+'.npz') for s in ('isolated_1','isolated_2')]
    if not all(p.exists() for p in paths): return False
    return bool(stable(arrays(folder,prefix+'isolated_1'),arrays(folder,prefix+'isolated_2'),INDEX,lab).all())

def round_qualified(folder,c,n,label,selection):
    if not held_mask(folder,'r%02d_'%n,label): return False
    opposite='E' if label=='M' else 'M'
    timing,_=challenge(c,selection)
    for j,(_,_,active) in enumerate(schedule(c['seed'],n,timing),1):
        if active:
            x=arrays(folder,'r%02d_segment_%02d'%(n,j))['initial']
            if ''.join(labels(x[:,[3+i for i in active]],INDEX))!=opposite*len(active): return False
    x=arrays(folder,'r%02d_segment_01'%n)['initial']
    return ''.join(labels(x[:,3:],INDEX))==opposite*3

def control_parent(c,run,selection):
    p=parent(c); folder=run/p['id']; kind=c['route']
    if kind.startswith('before'):
        return p['id'],'founder_isolated_2',founders(p),held_mask(folder,'founder_','M')
    if kind.startswith('after'):
        return p['id'],'rewrite_isolated_2',pupils(p,3),held_mask(folder,'rewrite_','E')
    available=all(round_qualified(folder,p,n,'M',selection) for n in range(1,4))
    return p['id'],'r03_isolated_2',pupils(p,3),available

def expected_selection(c,selection):
    if c['stage'] in ('baseline','timing'): return {}
    if c['stage']=='cells': return {'timing':selection.get('timing')}
    return selection

def branch(folder,c,selection,checks):
    run=folder.parent; rd=Reader(folder,c,selection,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('clock',result['clock_method']=='native_explicit_euler_bounded_clock_v1')
    rd.ck('selection',result['selection']==expected_selection(c,selection))
    rd.ck('positive_scope',all(result.get(k) is True for k in (
        'external_schedule','all_cells_evolve','only_new_cells_perturbed','shared_audited_stock')))
    rd.ck('negative_scope',all(result.get(k) is False for k in (
        'independent_biological_replicates','fine_is_independent_trial','autonomous_reproduction',
        'parameter_retuning','outcome_dependent_cell_selection','carrier_reset','automatic_follow_on')))
    rd.ck('new_writing',result.get('initial_writing_resimulated')==(c['stage']=='combined'))
    E,M=stock(run,c['fine']); timing,protein=challenge(c,selection)
    if c['stage'] in ('baseline','timing','cells'):
        source,name,ids=archived_donor(c); carry=arrays(run/'inputs/p11'/source,name)['final']
        _,_,row=handover(rd,carry,ids,E if c['label']=='M' else M,timing,protein,1,c['label'],c['route'],0)
        out=dict(available=True,rounds=[row],complete=row['complete'],negative=row['negative'])
        if c['stage']=='baseline':
            ref=('before__ordinary__open' if c['label']=='M' else 'after__ordinary__E_open__open')+('__fine' if c['fine'] else '')
            oldnum=1 if c['label']=='M' else 4
            for phase,x in rd.data.items():
                old=arrays(run/'inputs/p11'/ref,phase.replace('r01_','r%02d_'%oldnum))
                rd.ck(phase+'/exact_replay',set(x)==set(old) and all(np.array_equal(v,old[k]) for k,v in x.items()))
        return rd.finish(out)
    if c['stage']=='controls':
        kind=c['route']
        if kind=='founder_none':
            initial=incoming(E,c['seed'],'founder',protein)
            _,w=writer(rd,initial,founders(c),E,M,'founder_','none','E',0)
            return rd.finish(dict(available=True,rounds=[],writer=w,negative=all(w['retained_E'])))
        source,name,ids,available=control_parent(c,run,selection)
        if not available: return rd.finish(dict(available=False,rounds=[],negative=False,skip_reason='parent_prefix_unavailable'))
        carry=arrays(run/source,name)['final']
        if kind.startswith(('before','after')):
            before=kind.startswith('before'); number=1 if before else 4
            _,_,row=handover(rd,carry,ids,E if before else M,timing,protein,number,'M' if before else 'E',
                            kind.rsplit('_',1)[-1],40000 if before else 380000)
            return rd.finish(dict(available=True,rounds=[row],negative=row['negative']))
        _,w=writer(rd,carry,ids,E,M,'rewrite_','M' if kind=='rewrite_sham' else 'none','E',340000)
        return rd.finish(dict(available=True,rounds=[],writer=w,negative=all(w['retained_M'])))
    initial=incoming(E if c['history']=='written' else M,c['seed'],'founder',protein); ids=founders(c)
    carry,w=writer(rd,initial,ids,E,M,'founder_','M' if c['history']=='written' else 'age','M',0)
    rounds=[]; out=dict(available=True,founder=w,rewrite=None,rounds=rounds,before_complete=False,
                       complete=False,stop_reason='founder_not_M')
    if not w['qualified']: return rd.finish(out)
    for n in range(1,4):
        carry,ids,row=handover(rd,carry,ids,E,timing,protein,n,'M','open',40000+(n-1)*100000)
        rounds.append(row); out['stop_reason']='before_round_%d_incomplete'%n
        if not row['complete']: return rd.finish(out)
    out['before_complete']=True
    carry,w=writer(rd,carry,ids,E,M,'rewrite_','E','E',340000)
    out.update(rewrite=w,stop_reason='rewrite_not_E')
    if not w['qualified']: return rd.finish(out)
    for n in range(4,7):
        carry,ids,row=handover(rd,carry,ids,M,timing,protein,n,'E','open',380000+(n-4)*100000)
        rounds.append(row); out['stop_reason']='after_round_%d_incomplete'%n
        if not row['complete']: return rd.finish(out)
    out.update(complete=True,stop_reason='six_handover_chain_complete')
    return rd.finish(out)

def selection_from_outcomes(mode,by):
    levels={}
    for level in LEVELS:
        rows=[c for c in expected_stage(mode) if c['level']==level]
        levels[level]=all(by.get(c['id'],{}).get('complete' if c['route']=='open' else 'negative',False) for c in rows)
    selected=next((x for x in ('strong','mild') if levels[x]),None)
    return selected,levels

def compare_fine(cases,by,endpoints,checks):
    result=[]
    for c in cases:
        if not c['fine']: continue
        fid=c['id']; base=fid.removesuffix('__fine')
        if base not in by or fid not in by:
            checks.add(fid+'/fine_present',False); continue
        coarse,fine=endpoints[base],endpoints[fid]; common=set(coarse)&set(fine)
        differences={name:dict(labels_agree=bool(np.array_equal(labels(coarse[name]['final'],INDEX),labels(fine[name]['final'],INDEX))),
            max_absolute_difference=float(np.max(np.abs(coarse[name]['final']-fine[name]['final']))))
            for name in sorted(common)}
        agree=set(coarse)==set(fine) and by[base]==by[fid] and all(x['labels_agree'] for x in differences.values())
        checks.add(fid+'/fine',agree)
        result.append(dict(id=fid,baseline=base,agree=agree,phases=differences))
    checks.add('fine_comparison_count',len(result)==sum(c['fine'] for c in cases))
    return result

def stage_audit(run,stage):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    records={r['id']:r for r in summary['cases']}; cases=expected_cases(stage)
    by={}; endpoints={}; branches=[]; calls=0; selection=summary.get('selection',{})
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'; result=json.loads(path.read_text())
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and result==row['result'])
        report,data=branch(run/c['id'],c,selection,checks)
        branches.append(report); by[c['id']]=report['outcome']; endpoints[c['id']]=data; calls+=len(data)
    fine=compare_fine(cases,by,endpoints,checks)
    if stage!='baseline':
        checks.add('baseline_qualified',all(by.get(c['id'],{}).get('complete',False) for c in expected_stage('baseline')))
    for mode in ('timing','cells'):
        if STAGES.index(mode)<STAGES.index(stage):
            chosen,_=selection_from_outcomes(mode,by)
            checks.add('selection/'+mode,selection.get(mode)==chosen)
            if stage in ('combined','controls'): checks.add('selected/'+mode,chosen is not None)
    history=summary.get('predecessor_audit',{})
    checks.add('history_checked',summary.get('predecessor_gate') is True and history.get('quality_gate') is True)
    checks.add('history_saved',history==json.loads((run/'predecessor_audit.json').read_text()) and
               d.digest(run/'predecessor_audit.json')==summary.get('predecessor_audit_sha256'))
    checks.add('draw_book',json.loads((run/'frozen/paper_lineage_robustness_draws_v1.json').read_text())==expected_draws())
    checks.add('call_ceiling',calls<=1746)
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    selected=None; qualifies={}
    if stage in ('timing','cells'): selected,qualifies=selection_from_outcomes(stage,by)
    eligible=all(by.get(c['id'],{}).get('complete',False) for c in expected_stage('baseline')) if stage=='baseline' else (
        selected is not None if stage in ('timing','cells') else True)
    # Store compact final states only; arrays are never duplicated into JSON.
    return dict(stage=stage,quality_gate=bool(quality),eligible=bool(quality and eligible),selected=selected,
        level_qualification=qualifies,checks=checks.rows,integrity=provenance,branches=branches,
        fine_comparisons=fine,integration_calls=calls,cumulative_cases=len(branches))

def predecessor_audit(run):
    original=p11.analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p11/independent_audit.json').read_text())
    archived=p11.analyze(run/'inputs/p11'); archived['run']=str(d.PREDECESSOR)
    good=original==archived==saved and original['quality_gate'] and original['independent_check_count']==27610
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_matches_saved=archived==saved,
        prior_checks=original['independent_check_count'],prior_cases=original['completed_cases'],
        prior_calls=original['integration_calls'],shared_stock_and_replay_sources=True)

def trial_counts(by):
    trials=[]; counts=[]
    for history in HISTORIES:
        for seed in TEST_SEEDS:
            pair=[spec('combined',seed=seed,history=history,fine=f) for f in (False,True)]
            ctrls=[c for c in expected_stage('controls') if c['seed']==seed and c['history']==history]
            success=all(by.get(c['id'],{}).get('complete',False) for c in pair)
            available=all(by.get(c['id'],{}).get('available',False) for c in ctrls)
            negative=all(by.get(c['id'],{}).get('negative',False) for c in ctrls)
            trials.append(dict(history=history,seed=seed,raw_success_both=success,
                controls_available_both=available,controls_negative_both=negative,
                control_qualified=success and available and negative,
                stop_reasons=[by.get(c['id'],{}).get('stop_reason','not_run') for c in pair]))
        rows=[r for r in trials if r['history']==history]
        counts.append(dict(history=history,challenge_trials=3,raw_successes=sum(r['raw_success_both'] for r in rows),
                           control_qualified_successes=sum(r['control_qualified'] for r in rows)))
    return trials,counts

def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_lineage_robustness_v1.json').read_text()))
    checks.add('registration',summary['registered_cases']==expected_cases())
    stages=summary.get('attempted_stages',[])
    checks.add('stage_prefix',bool(stages) and stages==list(STAGES[:len(stages)]))
    history=predecessor_audit(run)
    checks.add('predecessor_fresh',history['quality_gate'] and history==summary['predecessor_audit'])
    reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report
        checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==json.loads((run/(stage+'_audit.json')).read_text()) and
            d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    last=stages[-1]; final=reports[last]; cases=expected_cases(last)
    checks.add('case_count',len(summary['cases'])==len(cases) and {r['id'] for r in summary['cases']}=={c['id'] for c in cases})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    choice={mode:reports[mode]['selected'] for mode in ('timing','cells') if mode in reports}
    checks.add('final_selection',choice==summary['selection'])
    expected_reason='combined_and_controls_completed' if last=='controls' else (
        'no_qualified_combined_challenge' if last=='cells' and any(v is None for v in choice.values()) else
        'baseline_not_qualified' if last=='baseline' and not final['eligible'] else None)
    checks.add('valid_stop',expected_reason is not None and summary.get('completion_reason')==expected_reason)
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    by={b['case']['id']:b['outcome'] for b in final['branches']}
    trials,counts=trial_counts(by) if last=='controls' else ([],[])
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=provenance,predecessor=history,
        stages=reports,completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],
        completion_reason=summary.get('completion_reason'),selection=choice,
        fine_comparisons=final['fine_comparisons'],all_fine_agree=all(p['agree'] for p in final['fine_comparisons']),
        trials=trials,trial_counts=counts,external_schedule=True,autonomous_reproduction=False,
        shared_stock=True,independent_biological_replicates=False,unique_PH_demonstrated=False,
        probability_estimate_precision_claim=False,automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    result=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',result)
    keys=('quality_gate','completed_cases','integration_calls','independent_check_count',
          'all_fine_agree','selection','trial_counts','completion_reason')
    print(json.dumps({k:result.get(k) for k in keys} if args.compact else result,indent=2))
    return 0 if result['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
