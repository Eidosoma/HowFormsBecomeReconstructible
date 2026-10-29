"""Independent constrained-record equations, actual ancestry and full trajectory replay."""
import numpy as np
from h077.audit import exact_projector
from h091 import audit as old
from h092.audit import infer,native_read
from h093 import reference as polynomial
from h094 import reference
from h097 import model as m

def metadata(raw,graph,check):
    assert set(graph)=={'records','reads','lineages','locals','cases'}
    records=graph['records'];reads=graph['reads'];assert len(records)==367
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
        for p in (m.READERS if route in m.NEURAL_ROUTES else ('direct',)) for g in range(3) for b in range(4)}
    assert len(lineages)==len(graph['lineages'])==240 and set(lineages)==expected
    expected={(o,route,p,g,b) for o in m.ORIGINS for route in ('copy','copy_repair',*m.BASELINES)
        for p in m.READERS for g in (1,2) for b in range(4)}
    assert len(local)==len(graph['locals'])==192 and set(local)==expected
    for scope,entries in (('lineage',lineages),('local',local)):
        for (origin,route,policy,g,b),item in entries.items():
            node=records[item['record']];kind='neural' if route in m.NEURAL_ROUTES else route
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
    assert seen==set(expected_cases) and len(seen)==960
    # Copying changes neither its coefficients nor its future record when expression policy changes.
    for origin in m.ORIGINS:
        for g in range(3):
            for b in range(4):
                a=lineages[origin,'copy','ordinary',g,b];z=lineages[origin,'copy','pair',g,b]
                for key in m.SCHEMAS['neural']:check.same(values[a['record']][key],values[z['record']][key],'complete copy policy invariance')
    return values,data


def shifted_factor(matrix,check):
    """LL^T=J+gamma I; the diagonal shift cancels for every binary-state energy difference."""
    j=np.asarray(matrix,dtype=np.longdouble);n=len(j)
    gamma=np.max(np.sum(np.abs(j),axis=1))+1
    shifted=j+gamma*np.eye(n,dtype=np.longdouble);lower=np.zeros_like(j)
    for k in range(n):
        diagonal=shifted[k,k]-np.sum(lower[k,:k]**2)
        assert diagonal>0
        lower[k,k]=np.sqrt(diagonal)
        lower[k+1:,k]=(shifted[k+1:,k]-lower[k+1:,:k]@lower[k,:k])/lower[k,k]
    check.same(lower@lower.T,shifted,'independent diagonal-shift factorization',2e-14)
    return lower


def record_checks(raw,graph,values,data,check):
    refs={};factors={};fitted={};projected={};factor_cache={};packet_indices=[];seen_fits=set();max_normal=0.;max_factor=0.
    x=raw['inputs'];arch=raw['architecture_mask'];available=raw['architecture_available']
    for node in graph['records']:
        i,kind,operation=node['id'],node['kind'],node['operation'];record=values[i];g=node['generation']
        if kind=='neural':
            j=record['J'];assert j.shape==(128,128) and j.dtype==np.dtype('float64') and np.isfinite(j).all()
            check.same(j,j.T,'symmetric physical couplings');check.same(np.diag(j),np.zeros(128),'zero self coupling')
            if g>=0:
                assert not j[~arch[g]].any() and not record['interaction_weights'][~available[g]].any()
            assert record['interaction_masks'].dtype==np.dtype('int8') and record['interaction_masks'].shape==(48,)
            assert record['interaction_weights'].dtype==np.dtype('float64') and record['interaction_weights'].shape==(48,)
        if operation=='erase':
            assert node['packet_index']==-1
            for v in record.values():check.same(v,np.zeros_like(v),'whole-record erasure')
        elif operation=='copy':
            assert kind=='neural' and node['packet_index']==-1 and node['parent_record']<i
            parent=values[node['parent_record']]
            check.same(record['J'],parent['J']*arch[g],'actual physical copy after common edge loss')
            check.same(record['interaction_masks'],parent['interaction_masks'],'copied interaction masks')
            check.same(record['interaction_weights'],parent['interaction_weights']*available[g],'physical copy after common channel loss')
        else:
            assert operation in ('founder','write');pi=node['packet_index'];packet_indices.append(pi)
            y=raw['packet_outputs'][pi];assert y.shape==(8,48) and np.isin(y,[-1,1]).all()
            if operation=='founder':
                assert g==0 and node['parent_record']==node['parent_read']==-1
                check.same(y,raw['responses_'+node['origin']][m.TRAIN],'only eight founder observations')
            else:
                parent=graph['reads'][node['parent_read']]
                assert parent['generation']==g-1 and parent['birth']==node['birth'] and node['parent_record']<i
                check.same(y,m.response(data[parent['id']],parent['kind'],node['parent_reader'])[m.TRAIN],'only eight actual parent emissions')
            signature=y.tobytes()
            if signature not in fitted:fitted[signature]=infer(y)
            masks,signs,prediction=fitted[signature]
            for key,wanted in (('masks',masks),('signs',signs),('outputs',prediction)):
                check.same(raw['completion_'+key][pi],wanted,'independent scalar completion '+key)
            if kind=='neural':
                key=prediction.tobytes()
                if key not in projected:
                    patterns=np.concatenate((x,prediction),axis=1).astype(np.int64);p,rank=exact_projector(patterns)
                    check.same(patterns@p,patterns.astype(np.longdouble),'generated pattern span',2e-13)
                    ideal=p.copy();np.fill_diagonal(ideal,0);projected[key]=(patterns,ideal)
                patterns,ideal=projected[key]
                weights=np.asarray([int(s) if (int(k)&3) and (int(k)&12) else 0 for k,s in zip(masks,signs)],dtype=np.longdouble)
                check.same(record['interaction_masks'],masks,'learned rule masks')
                check.same(record['interaction_weights'],weights*available[g],'only available interaction channels')
                desired=dict(J=ideal,interaction_masks=masks,interaction_weights=weights)
                limited=dict(desired,interaction_weights=weights*available[g])
                target=polynomial.fields(desired,patterns)-polynomial.factor_fields(limited,patterns)
                repair=node['route']=='copy_repair'
                prior=(values[node['parent_record']]['J'].astype(np.longdouble) if repair else ideal)*arch[g]
                actual=j.astype(np.longdouble);err=patterns@actual-target
                grad=patterns.T@err/16;grad=(grad+grad.T)*arch[g]/2+np.longdouble('.1')*(actual-prior)
                normal=float(np.sqrt(np.sum(grad**2)));assert normal<=5e-10,('constrained writer normal equation',normal)
                max_normal=max(max_normal,normal);check.count+=1
                expected=dict(normal_residual=normal,field_error=float(np.sum(err**2)/16),
                    prior_distance=float(np.sum((actual-prior)**2)),starting_field_error=float(np.sum((patterns@prior-target)**2)/16))
                for name,wanted in expected.items():check.same(raw['compiler_'+name][pi],np.asarray(wanted),'independent fit diagnostic '+name,2e-9)
                assert expected['field_error']+.1*expected['prior_distance']<=expected['starting_field_error']+1e-9
                assert 0<=int(raw['compiler_iterations'][pi])<=512
                parent_sig=m.digest(values[node['parent_record']]) if repair else ''
                cachekey=(m.digest(dict(masks=masks,signs=signs,outputs=prediction)),g,'copy_repair' if repair else 'rewrite',parent_sig)
                check.same(raw['compiler_fit_executed'][pi],np.asarray(int(cachekey not in seen_fits)),'executed versus cached solver accounting');seen_fits.add(cachekey)
            else:
                for name in ('iterations','normal_residual','field_error','prior_distance','starting_field_error','fit_executed'):
                    assert raw['compiler_'+name][pi]==0
                if kind=='parity_erm':
                    check.same(record['masks'],masks,'native fitted masks');check.same(record['signs'],signs,'native fitted signs')
                elif kind=='nearest_history':
                    check.same(record['inputs'],x,'native public grid');check.same(record['outputs'],prediction,'native generated responses')
                else:
                    mean=np.asarray([sum(int(v) for v in x[:,k])/16 for k in range(80)])
                    check.same(record['mean'],mean,'public-grid center');basis=record['basis'];assert basis.shape==(80,6)
                    check.same(basis.T@basis,np.eye(6),'orthonormal input span',2e-12)
                    check.same((x-mean)@basis@basis.T,x-mean,'complete public input span',2e-12)
                    z=(x-mean)@basis;columns=[np.ones(16)]+[z[:,k] for k in range(6)]
                    if kind=='quadratic_ls':columns += [z[:,k]*z[:,l] for k in range(6) for l in range(k,6)]
                    check.same(record['coeff'],np.linalg.pinv(np.column_stack(columns),rcond=1e-12)@prediction,'independent native generated-response fit',2e-12)
        if kind=='neural':
            refs[i]=dict(J=j.astype(np.longdouble),interaction_masks=record['interaction_masks'].copy(),interaction_weights=record['interaction_weights'].astype(np.longdouble))
            key=j.tobytes()
            if key not in factor_cache:factor_cache[key]=shifted_factor(j,check)
            factors[i]=factor_cache[key]
    assert sorted(packet_indices)==list(range(298)) and len(raw['packet_outputs'])==298
    return refs,factors,max_normal


def network(raw,graph,cohort,block,condition):
    check=old.pair_audit.Audit();tape=m.tapes(cohort,block)
    for key,value in tape.items():check.same(raw[key],value,'committed '+key)
    check.same(raw['inputs'],m.X,'public feature grid');check.same(raw['training_indices'],m.TRAIN,'teaching split');check.same(raw['heldout_indices'],m.TEST,'unseen split')
    mask=tape['body_mask'].copy();available=tape['body_available'].copy()
    if condition=='intact':mask[:]=~np.eye(128,dtype=bool);available[:]=True
    check.same(raw['architecture_mask'],mask,'common physical edge mask');check.same(raw['architecture_available'],available,'common nonlinear channel availability')
    assert all(mask[g].sum()//2==(8128 if condition=='intact' or g==0 else 4064) for g in range(3))
    assert all(available[g].sum()==(48 if condition=='intact' or g==0 else 24) for g in range(3))
    values,data=metadata(raw,graph,check);refs,factors,residual=record_checks(raw,graph,values,data,check)
    neural=native=0
    for node in graph['reads']:
        record=values[node['record']];saved=data[node['id']]
        if node['kind']=='neural':
            reference.trajectory(raw,node,record,saved,refs[node['record']],factors[node['record']],check);neural+=1
        else:check.max_field_error=max(check.max_field_error,native_read(raw,node,record,saved,check));native+=1
    for entry in graph['lineages']:
        if entry['route']=='parity_erm':check.same(data[entry['read']]['final'],raw['responses_'+entry['origin']],'separate native parity ceiling remains exact')
    assert check.max_field_error<=2e-11
    return dict(passed=True,numerical_checks=check.count,records=367,writer_packets=298,completion_packets=298,
        lineage_nodes=240,local_nodes=192,assay_cases=960,unique_neural_reads=neural,unique_native_reads=native,
        pair_energy_comparisons=check.pair_comparisons,single_energy_comparisons=check.single_comparisons,
        max_writer_normal_residual=residual,max_field_error=check.max_field_error,max_pair_energy_error=check.max_pair_error,
        minimum_decision_boundary_distance=check.boundary_minimum,all_new_trajectories_replayed=True,
        all_actual_packets_verified=True,heldout_truth_excluded_from_writing=True,physical_constraints_verified=True)
