"""Independent record fits, explicit ancestry, extended-precision trajectory replay."""
import numpy as np
from h077.audit import exact_projector
from h081.legacy_audit import Audit as TrajectoryAudit
from h083 import audit as pair_audit
from h089 import model as m


def metadata(raw,graph,check):
    assert set(graph)=={'records','reads','lineages','locals','cases'}
    records=graph['records'];reads=graph['reads'];assert len(records)==303
    assert [r['id'] for r in records]==list(range(len(records)))
    assert [r['id'] for r in reads]==list(range(len(reads)))
    for kind in m.KINDS:
        for nodes in (records,reads):assert [r['index'] for r in nodes if r['kind']==kind]==list(range(sum(r['kind']==kind for r in nodes)))
    values={r['id']:m.get_record(raw,graph,r['id']) for r in records}
    data={r['id']:m.get_read(raw,graph,r['id']) for r in reads}
    def alias(record,read,g,b):
        rr=reads[read];assert rr['kind']==records[record]['kind'] and rr['generation']==g and rr['birth']==b
        for key,value in values[record].items():check.same(value,values[rr['record']][key],'content-addressed read alias')
    key=lambda r:(r['origin'],r['route'],r['policy'],r['generation'],r['birth'])
    lineages={key(r):r for r in graph['lineages']};local={key(r):r for r in graph['locals']}
    expected={(o,route,p,g,b) for o in m.ORIGINS for route in m.ROUTES
        for p in (m.READERS if route in ('rewrite','copy') else ('direct',)) for g in range(3) for b in range(4)}
    assert len(lineages)==len(graph['lineages'])==192 and set(lineages)==expected
    expected={(o,route,p,g,b) for o in m.ORIGINS for route in ('copy',*m.BASELINES)
        for p in m.READERS for g in (1,2) for b in range(4)}
    assert len(local)==len(graph['locals'])==160 and set(local)==expected
    for scope,entries in (('lineage',lineages),('local',local)):
        for (origin,route,policy,g,b),item in entries.items():
            node=records[item['record']];kind='neural' if route in ('rewrite','copy') else route
            assert node['origin']==origin and node['kind']==kind
            alias(item['record'],item['read'],g,b)
            if g==0:
                assert scope=='lineage' and node['operation']=='founder' and node['generation']==0
            else:
                assert node['scope']==scope and node['route']==route and node['policy']==policy
                assert node['generation']==g and node['birth']==b
                parent=lineages[origin,'rewrite' if scope=='local' else route,policy,g-1,b]
                assert node['parent_record']==parent['record'] and node['parent_read']==parent['read']
                assert node['parent_reader']==policy and node['operation']==('copy' if route=='copy' else 'write')
    erased={r['kind']:r['id'] for r in records if r['operation']=='erase'};assert set(erased)==set(m.KINDS)
    expected_cases={}
    for scope,entries in (('lineage',lineages),('local',local)):
        for (origin,route,p,g,b),item in entries.items():
            if origin!='own':continue
            kind=records[item['record']]['kind']
            for source in ('own','donor','erased'):
                record=erased[kind] if source=='erased' else entries[source,route,p,g,b]['record']
                for reader in m.READERS if kind=='neural' else ('direct',):
                    expected_cases[scope,route,p,g,b,source,reader]=record
    seen=set()
    for case in graph['cases']:
        key=tuple(case[k] for k in ('scope','route','policy','generation','birth','source','reader'))
        assert key not in seen and expected_cases[key]==case['record'];seen.add(key)
        alias(case['record'],case['read'],case['generation'],case['birth'])
    assert seen==set(expected_cases) and len(seen)==720
    # Copying changes neither its coefficients nor its future record when expression policy changes.
    for origin in m.ORIGINS:
        for g in range(3):
            for b in range(4):
                a=lineages[origin,'copy','ordinary',g,b];z=lineages[origin,'copy','pair',g,b]
                check.same(values[a['record']]['J'],values[z['record']]['J'],'copy policy invariance')
    return values,data


def record_checks(raw,graph,values,data,check):
    references={};projectors={};cache={};parity_fits={};max_error=0.;packet_indices=[]
    for node in graph['records']:
        i,kind,operation=node['id'],node['kind'],node['operation'];record=values[i]
        if operation=='erase':
            assert node['packet_index']==-1
            for value in record.values():check.same(value,np.zeros_like(value),'whole native record erasure')
            if kind=='neural':references[i]=projectors[i]=np.zeros((128,128),dtype=np.longdouble)
            continue
        if operation=='copy':
            assert kind=='neural' and node['packet_index']==-1 and node['parent_record']<i
            check.same(record['J'],values[node['parent_record']]['J'],'exact actual parent coefficient copy')
            references[i]=references[node['parent_record']];projectors[i]=projectors[node['parent_record']];continue
        assert operation in ('founder','write')
        packet_indices.append(node['packet_index']);y=raw['packet_outputs'][node['packet_index']]
        assert y.shape==(8,48) and np.isin(y,[-1,1]).all()
        if operation=='founder':
            assert node['generation']==0 and node['parent_record']==node['parent_read']==-1
            check.same(y,raw['responses_'+node['origin']][m.TRAIN],'founder teaching observations')
        else:
            assert node['generation'] in (1,2) and node['parent_record']<i
            parent=graph['reads'][node['parent_read']]
            assert parent['generation']==node['generation']-1 and parent['birth']==node['birth']
            expected=m.response(data[parent['id']],parent['kind'],node['parent_reader'])[m.TRAIN]
            check.same(y,expected,'writer packet contains all actual parent emissions')
        if kind=='neural':
            signature=y.tobytes()
            if signature not in cache:
                patterns=np.concatenate((m.X[m.TRAIN],y),axis=1).astype(np.int64)
                projection,rank=exact_projector(patterns)
                check.same(patterns@projection,patterns.astype(np.longdouble),'written span',2e-13)
                check.same(projection@projection,projection,'idempotent written projector',2e-13)
                ref=projection.copy();np.fill_diagonal(ref,0);cache[signature]=(projection,ref)
            projectors[i],references[i]=cache[signature]
            check.same(record['J'],references[i],'independent rational projection writer',4e-14)
            check.same(record['J'],record['J'].T,'symmetric inherited record')
            check.same(np.diag(record['J']),np.zeros(128),'no diagonal self interaction')
            max_error=max(max_error,float(np.max(np.abs(record['J']-references[i]))))
        elif kind=='nearest_history':
            check.same(record['inputs'],m.X[m.TRAIN],'native stored observed inputs')
            check.same(record['outputs'],y,'native stored actual outputs')
        elif kind=='parity_erm':
            signature=y.tobytes()
            if signature not in parity_fits:
                candidates=[]
                for mask in range(16):
                    for sign in (1,-1):
                        predicted=[sign*int(np.prod([int(x[site]) for bit,site in enumerate((0,16,32,56)) if (mask>>bit)&1])) for x in m.X[m.TRAIN]]
                        candidates.append((mask,sign,predicted))
                masks=[];signs=[]
                for col in range(48):
                    best=None;selected=None
                    for mask,sign,predicted in candidates:
                        error=sum(int(value)!=int(truth) for value,truth in zip(predicted,y[:,col]))
                        if best is None or error<best:best=error;selected=(mask,sign)
                    masks.append(selected[0]);signs.append(selected[1])
                parity_fits[signature]=(masks,signs)
            masks,signs=parity_fits[signature]
            check.same(record['masks'],np.asarray(masks),'exhaustive scalar parity fit with fixed ties')
            check.same(record['signs'],np.asarray(signs),'exhaustive parity signs')
        else:
            mean=np.asarray([sum(int(v) for v in m.X[m.TRAIN][:,j])/8 for j in range(80)])
            check.same(record['mean'],mean,'input-only center')
            basis=record['basis'];check.same(basis.T@basis,np.eye(4),'orthonormal input basis',2e-12)
            check.same((m.X[m.TRAIN]-mean)@basis@basis.T,m.X[m.TRAIN]-mean,'complete learned input span',2e-12)
            z=(m.X[m.TRAIN]-mean)@basis;columns=[np.ones(8)]+[z[:,j] for j in range(4)]
            if kind=='quadratic_ls':columns += [z[:,j]*z[:,k] for j in range(4) for k in range(j,4)]
            fitted=np.linalg.pinv(np.column_stack(columns),rcond=1e-12)@y
            check.same(record['coeff'],fitted,'independent minimum-norm emitted-packet fit',2e-12)
    assert sorted(packet_indices)==list(range(len(raw['packet_outputs'])))
    return references,projectors,max_error


def trajectory(raw,node,record,data,reference,projector,check):
    g,b=node['generation'],node['birth'];x=raw['inputs'];j=record['J']
    auditor=TrajectoryAudit('delayed');auditor.reference=reference
    initial=np.broadcast_to(raw['birth'][g,b],(16,1,128))
    for phase,state,indices,values,count in (
        ('context',initial,m.base.CONTEXT,x[:,None,:32],4),
        ('gap',data['context_final'],np.asarray([],dtype=int),np.empty((16,1,0),dtype=np.int8),4),
        ('query',data['gap_final'],m.base.QUERY,x[:,None,32:],8)):
        packet=dict(record=j,state=state,orders=raw['orders_'+phase][g],clamp_indices=indices,clamp_values=values,active_sweeps=count)
        if phase=='query':packet['feedback']=m.scheduled.FEEDBACK['delayed']
        auditor.segment(data,phase+'_',packet)
    move={k[5:]:v for k,v in data.items() if k.startswith('kick_')}
    _,deltas=pair_audit.neighborhood(j,reference,projector,data['query_final'],move,check)
    pair_audit.selection(reference,data['query_final'],move,deltas,check)
    for reader,state in (('ordinary',data['query_final']),('pair',move['after'])):
        packet=dict(record=j,state=state,orders=raw['orders_query'][g],clamp_indices=m.base.QUERY,
            clamp_values=x[:,None,32:],active_sweeps=8)
        auditor.segment(data,reader+'_',packet)
        check.same(data[reader+'_clamp_work'],np.zeros((8,16,1)),'continuation clamp already held')
        delta=data[reader+'_final_energy']-m.base.energy(j,data['query_final'])
        wanted=(data[reader+'_end_energy']-data[reader+'_start_energy']).sum(0)
        if reader=='pair':wanted=wanted+move['realized_delta']
        check.same(delta,wanted,'pair and continuation energy ledger',2e-11)
    return auditor


def native_read(raw,node,record,data,check):
    kind=node['kind'];x=raw['inputs'];g,b=node['generation'],node['birth']
    if kind=='parity_erm':
        fields=np.asarray([[int(record['signs'][j])*int(np.prod([int(row[site]) for bit,site in enumerate((0,16,32,56)) if (int(record['masks'][j])>>bit)&1])) for j in range(48)] for row in x],dtype=np.longdouble)
        nearest=np.full(16,-1,dtype=int)
    elif kind=='nearest_history':
        distances=[[sum((float(u)-float(v))**2 for u,v in zip(row,example)) for example in record['inputs']] for row in x]
        nearest=np.asarray([min(range(8),key=lambda i:row[i]) for row in distances])
        fields=record['outputs'][nearest].astype(np.longdouble)
    else:
        z=(x.astype(np.longdouble)-record['mean'].astype(np.longdouble))@record['basis'].astype(np.longdouble)
        columns=[np.ones(16,dtype=np.longdouble)]+[z[:,j] for j in range(4)]
        if kind=='quadratic_ls':columns += [z[:,j]*z[:,k] for j in range(4) for k in range(j,4)]
        fields=np.column_stack(columns)@record['coeff'].astype(np.longdouble);nearest=np.full(16,-1,dtype=int)
    check.same(data['fields'],fields,'independent native read field',2e-11)
    check.same(data['nearest'],nearest,'independent nearest index')
    wanted=check.decide(fields,np.broadcast_to(raw['birth'][g,b,80:],(16,48)))
    check.same(data['final'],wanted,'independent native threshold and birth tie')
    return float(np.max(np.abs(data['fields']-fields)))


def network(raw,graph,cohort,block):
    check=pair_audit.Audit()
    for key,value in m.tapes(cohort,block).items():check.same(raw[key],value,'committed '+key)
    check.same(raw['inputs'],m.X,'fixed observed alphabet')
    check.same(raw['training_indices'],m.TRAIN,'fixed training split');check.same(raw['heldout_indices'],m.TEST,'fixed held-out split')
    assert set(m.TRAIN).isdisjoint(set(m.TEST)) and set(np.r_[m.TRAIN,m.TEST])==set(range(16))
    assert len(np.unique(m.dictionary(m.X[m.TRAIN]).T,axis=0))==32,'all signed parity rules identifiable'
    for origin in m.ORIGINS:
        y=raw['responses_'+origin];assert y.shape==(16,48) and np.isin(y,[-1,1]).all() and not y.sum(0).any()
        assert len(np.unique(y,axis=0))==16
    values,data=metadata(raw,graph,check)
    references,projectors,max_record_error=record_checks(raw,graph,values,data,check)
    trajectory_checks=0;max_field_error=0.;neural_reads=0;native_reads=0
    for node in graph['reads']:
        record=values[node['record']];saved=data[node['id']]
        if node['kind']=='neural':
            a=trajectory(raw,node,record,saved,references[node['record']],projectors[node['record']],check)
            trajectory_checks+=a.checks;max_field_error=max(max_field_error,a.max_field_error)
            check.boundary_minimum=min(check.boundary_minimum,a.boundary_minimum);neural_reads+=1
        else:max_field_error=max(max_field_error,native_read(raw,node,record,saved,check));native_reads+=1
    for entry in graph['lineages']:
        if entry['route']=='parity_erm':
            check.same(data[entry['read']]['final'],raw['responses_'+entry['origin']],'ordinary rule learner proves exact learnability through both handoffs')
    assert max_field_error<=2e-11
    return dict(passed=True,numerical_checks=check.count+trajectory_checks,records=len(graph['records']),
        writer_packets=len(raw['packet_outputs']),lineage_nodes=len(graph['lineages']),local_nodes=len(graph['locals']),
        assay_cases=len(graph['cases']),unique_neural_reads=neural_reads,unique_native_reads=native_reads,
        pair_energy_comparisons=check.pair_comparisons,single_energy_comparisons=check.single_comparisons,
        max_projection_record_error=max_record_error,max_field_error=max_field_error,max_pair_energy_error=check.max_pair_error,
        minimum_decision_boundary_distance=check.boundary_minimum,actual_handoffs_per_lineage=2,
        propagated_lineages=64,independent_networks=1,copy_invariance=True,all_emitted_packets_verified=True,all_aliases_verified=True,
        target_free_writers=True,heldout_excluded_from_writing=True,rule_identifiable=True,parity_positive_control_exact=True,all_unique_trajectories_replayed=True)
