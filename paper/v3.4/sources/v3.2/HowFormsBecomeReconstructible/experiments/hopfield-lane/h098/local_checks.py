"""Numerical regression checks, including H097's saved failing reader."""
from pathlib import Path
import json,time
import numpy as np
from h007.io import save,checksum
from h093.fixtures import rejects
from h093 import dynamics as polynomial
from h094 import dynamics,reference
from h083.audit import reference_deltas,Audit
from h097 import audit
from h098 import model as m,compiler as c

def solver_checks(out,tape):
    gen=np.random.default_rng(9709701);n=8;p=gen.normal(size=(11,n));target=gen.normal(size=p.shape)
    mask=np.triu(gen.random((n,n))>.5,1);mask|=mask.T
    prior=c.project(gen.normal(size=(n,n)),mask);j,stats=c.solve(p,target,prior,mask)
    edges=list(zip(*np.where(np.triu(mask,1))));basis=np.zeros((len(edges),n,n))
    for k,(i,l) in enumerate(edges):basis[k,i,l]=basis[k,l,i]=1
    design=np.stack([(p@b).ravel() for b in basis],axis=1)
    v=np.linalg.solve(design.T@design/len(p)+2*c.RIDGE*np.eye(len(edges)),design.T@(target-p@prior).ravel()/len(p))
    expected=prior+np.einsum('k,kij->ij',v,basis);np.testing.assert_allclose(j,expected,rtol=0,atol=2e-11)
    direction=c.project(gen.normal(size=(n,n)),mask);probe=prior+.2*direction;eps=1e-6
    loss=lambda x:np.square(p@x-target).sum()/len(p)+c.RIDGE*np.square(x-prior).sum()
    gradient=c.project(p.T@(p@probe-target)/len(p),mask)+c.RIDGE*(probe-prior)
    finite=(loss(probe+eps*direction)-loss(probe-eps*direction))/(2*eps)
    assert abs(finite-2*np.sum(gradient*direction))<1e-7
    completion=m.complete(dict(observed_inputs=m.X[m.TRAIN],observed_outputs=tape['responses_own'][m.TRAIN]))
    full=~np.eye(128,dtype=bool);available=np.ones(48,dtype=bool);ideal=m.compile_record(completion,'neural')
    intact,_=c.constrain(dict(completion=completion,mask=full,available=available,prior_record=None,mode='rewrite'))
    repaired,_=c.constrain(dict(completion=completion,mask=full,available=available,prior_record=ideal,mode='copy_repair'))
    for k in ideal:np.testing.assert_array_equal(ideal[k],intact[k]);np.testing.assert_array_equal(ideal[k],repaired[k])
    lost,loss_info=c.constrain(dict(completion=completion,mask=tape['body_mask'][1],available=tape['body_available'][1],prior_record=None,mode='rewrite'))
    repaired,_=c.constrain(dict(completion=completion,mask=tape['body_mask'][1],available=tape['body_available'][1],prior_record=ideal,mode='copy_repair'))
    for k in lost:np.testing.assert_array_equal(lost[k],repaired[k])
    copied=c.copy(dict(record=ideal,mask=tape['body_mask'][1],available=tape['body_available'][1]))
    copied2=c.copy(dict(record=copied,mask=full,available=available))
    for k in copied:np.testing.assert_array_equal(copied[k],copied2[k])
    assert not lost['J'][~tape['body_mask'][1]].any() and not lost['interaction_weights'][~tape['body_available'][1]].any()
    rejects(lambda:c.constrain(dict(completion=completion,mask=full,available=available,prior_record=None,mode='rewrite',true_labels=tape['responses_own'])))
    check=Audit();factor=audit.shifted_factor(lost['J'],check);state=gen.choice([-1,1],size=(2,128)).astype(np.int8)
    a=reference_deltas(lost['J'],state);b=reference_deltas(lost['J'],state,factor)
    for x,y in zip(a,b):check.same(x,y,'shifted factor versus direct changed energies',2e-11)
    with (out/'solver_raw.npz').open('xb') as f:np.savez_compressed(f,small_result=j,small_reference=expected,lost_J=lost['J'],lost_weights=lost['interaction_weights'],lost_mask=tape['body_mask'][1],state=state,factor=factor)
    return ['symmetric constrained solver agrees with an independent dense edge-basis solve',
        'nonstationary finite-difference derivative verifies the declared objective gradient',
        'intact reconstruction and repair preserve the H093 ideal exactly',
        'identical available priors give identical reconstruction and repair; both obey forbidden coefficients',
        'physical copying cannot restore destroyed values when availability returns',
        'writer rejects a hidden target and shifted-factor pair energies agree with direct energies']


def run(out,parent,tape):
    out=Path(out);out.mkdir(exist_ok=False);parent=Path(parent);tick=time.perf_counter()
    tests=solver_checks(out,tape)
    gen=np.random.default_rng(98098);p=gen.normal(size=(13,8));target=gen.normal(size=p.shape)
    mask=np.triu(gen.random((8,8))>.4,1);mask|=mask.T;prior=c.project(gen.normal(size=(8,8)),mask)
    fits={level:c.solve(p,target,prior,mask,level) for level in c.PRECISIONS}
    edges=list(zip(*np.where(np.triu(mask,1))));basis=np.zeros((len(edges),8,8))
    for k,(i,j) in enumerate(edges):basis[k,i,j]=basis[k,j,i]=1
    a=np.stack([(p@v).ravel() for v in basis],axis=1)
    coeff=np.linalg.solve(a.T@a/len(p)+2*c.RIDGE*np.eye(len(edges)),a.T@(target-p@prior).ravel()/len(p))
    expected=prior+np.einsum('k,kij->ij',coeff,basis)
    for level,(actual,info) in fits.items():np.testing.assert_allclose(actual,expected,rtol=0,atol=2e-11)
    tests.append('candidate and extended-precision solvers agree with an independent dense edge-basis solution')
    source=parent/'main/new_raw/block_013_loss.npz';graphpath=parent/'main/paths/block_013_loss.json'
    pins={str(p):checksum(p) for p in (source,graphpath,parent/'freeze.json',parent/'FAILED.json')}
    with np.load(source,allow_pickle=False) as f:raw={k:f[k] for k in f.files}
    graph=json.loads(graphpath.read_text());node=graph['reads'][95];meta=graph['records'][node['record']]
    assert meta['id']==296 and meta['route']=='rewrite' and meta['packet_index']==244
    completion=m.complete(dict(observed_inputs=m.X[m.TRAIN],observed_outputs=raw['packet_outputs'][244]))
    for k,v in completion.items():np.testing.assert_array_equal(v,raw['completion_'+k][244])
    original=m.get_record(raw,graph,296);saved=m.get_read(raw,graph,95)
    readpacket=dict(record=original,birth=raw['birth'][2,3],observed_history=m.X,
        **{'orders_'+p:raw['orders_'+p][2] for p in ('context','gap','query')})
    produced=dynamics.read(readpacket)
    for k,v in produced.items():np.testing.assert_array_equal(v,saved[k])
    tests.append('the original production reader exactly reproduces all saved failing-reader arrays')
    results={};records={};reads={};checks=0
    for level in c.PRECISIONS:
        record,stats=c.constrain(dict(completion=completion,mask=raw['architecture_mask'][2],available=raw['architecture_available'][2],prior_record=None,mode='rewrite'),level)
        assert not stats['identity_preserved'];records[level]=record;reads[level]=dynamics.read(dict(readpacket,record=record))
        ref={k:v.astype(np.longdouble) if k!='interaction_masks' else v for k,v in record.items()}
        check=Audit();factor=audit.shifted_factor(record['J'],check)
        reference.trajectory(raw,node,record,reads[level],ref,factor,check)
        results[level]=dict(**stats,numerical_checks=check.count,minimum_decision_boundary_distance=check.boundary_minimum,
            max_field_error=check.max_field_error,max_pair_energy_error=check.max_pair_error)
        checks+=check.count
    discrete=[]
    for k,v in reads['candidate'].items():
        if v.dtype.kind in 'biu':np.testing.assert_array_equal(v,reads['refined'][k],err_msg=k);discrete.append(k)
    tests.append('both corrected precisions pass the original strict field/energy/threshold audit on the failing reader')
    tests.append('all corrected discrete traces, choices and endpoint flags agree across precisions')
    full=~np.eye(128,dtype=bool);available=np.ones(48,dtype=bool);ideal=m.compile_record(completion,'neural')
    for level in c.PRECISIONS:
        for mode,prior_record in [('rewrite',None),('copy_repair',ideal)]:
            record,stats=c.constrain(dict(completion=completion,mask=full,available=available,prior_record=prior_record,mode=mode),level)
            assert stats['identity_preserved'] and stats['iterations']==0
            for k,v in ideal.items():np.testing.assert_array_equal(v,record[k])
        wrong={k:v.copy() for k,v in ideal.items()};wrong['J'][:]=0
        _,stats=c.constrain(dict(completion=completion,mask=full,available=available,prior_record=wrong,mode='copy_repair'),level)
        assert not stats['identity_preserved'] and stats['iterations']>0
    tests.append('both precisions preserve the ideal intact record exactly and still solve a nonideal repair prior')
    arrays={level+'__record_'+k:v for level in c.PRECISIONS for k,v in records[level].items()}
    arrays.update({level+'__read_'+k:v for level in c.PRECISIONS for k,v in reads[level].items()})
    with (out/'known_failure_recheck.npz').open('xb') as f:np.savez_compressed(f,**arrays)
    with np.load(out/'known_failure_recheck.npz',allow_pickle=False) as f:
        for k,v in arrays.items():np.testing.assert_array_equal(f[k],v)
    for path,pin in pins.items():assert checksum(path)==pin
    result=dict(passed=True,count=len(tests),tests=tests,precision_settings=c.TOLERANCES,
        known_failure_results=results,discrete_reader_arrays_compared=len(discrete),numerical_checks=checks,
        maximum_candidate_refined_coupling_difference=float(np.max(np.abs(records['candidate']['J']-records['refined']['J']))),
        response_bits_changed_from_failed_record={p:int(np.count_nonzero(reads['candidate'][p+'_final'][...,80:]!=saved[p+'_final'][...,80:])) for p in ('ordinary','pair')},
        original_bindings=pins,original_unchanged=True,thresholds_unchanged=True,elapsed_seconds=time.perf_counter()-tick)
    save(out/'result.json',result);return result
