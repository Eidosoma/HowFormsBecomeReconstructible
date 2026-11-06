"""Same constrained objective, tighter solve, and an extended-precision convergence control."""
import numpy as np
from h093 import model as legacy,dynamics
from h097.compiler import validate_mask,project,copy
RIDGE=.1
MAX_ITERATIONS=512
PRECISIONS=('candidate','refined')
TOLERANCES=dict(candidate=1e-14,refined=1e-18)

def statistics(patterns,target,prior,mask,record,iterations,identity=False):
    gradient=project(patterns.T@(patterns@record-target)/len(patterns),mask)+RIDGE*(record-prior)
    norm=float(np.linalg.norm(gradient));assert norm<=5e-10
    return dict(iterations=int(iterations),normal_residual=norm,
        field_error=float(np.square(patterns@record-target).sum()/len(patterns)),prior_distance=float(np.square(record-prior).sum()),
        starting_field_error=float(np.square(patterns@prior-target).sum()/len(patterns)),identity_preserved=int(identity))

def solve(patterns,target,prior,mask,precision='candidate'):
    assert precision in PRECISIONS
    assert patterns.ndim==2 and target.shape==patterns.shape and prior.shape==mask.shape==(patterns.shape[1],)*2
    assert np.array_equal(prior,prior.T) and np.all(prior[~mask]==0)
    dtype=np.float64 if precision=='candidate' else np.longdouble
    if precision=='refined':assert np.finfo(dtype).eps<np.finfo(np.float64).eps/1000
    p=np.asarray(patterns,dtype=dtype);t=np.asarray(target,dtype=dtype);before=np.asarray(prior,dtype=dtype);n=len(p)
    def action(x):return project(p.T@(p@x)/n,mask)+dtype(RIDGE)*x
    rhs=project(p.T@(t-p@before)/n,mask)
    correction=np.zeros_like(before);residual=rhs.copy();direction=residual.copy();squared=np.sum(residual*residual)
    cutoff=dtype(str(TOLERANCES[precision]))*max(dtype(1),np.sqrt(squared));iterations=0
    while np.sqrt(squared)>cutoff:
        assert iterations<MAX_ITERATIONS,'precision-controlled writer did not converge'
        q=action(direction);denominator=np.sum(direction*q);assert denominator>0
        alpha=squared/denominator;correction+=alpha*direction;residual-=alpha*q
        updated=np.sum(residual*residual);direction=residual+(updated/squared)*direction;squared=updated;iterations+=1
    record=np.asarray(before+correction,dtype=np.float64)
    return record,statistics(patterns,target,prior,mask,record,iterations)


def constrain(packet,precision='candidate'):
    assert set(packet)=={'completion','mask','available','prior_record','mode'} and precision in PRECISIONS
    completion,mask,available,prior_record,mode=(packet[k] for k in ('completion','mask','available','prior_record','mode'))
    validate_mask(mask,available);assert mode in ('rewrite','copy_repair')
    ideal=legacy.compile_record(completion,'neural');record={k:v.copy() for k,v in ideal.items()};record['interaction_weights']*=available
    patterns=np.concatenate((legacy.X,completion['outputs']),axis=1).astype(float)
    # Form exactly the same float64 target as H097; refine only the linear solve.
    target=dynamics.fields(ideal,patterns)-dynamics.factor_fields(record,patterns)
    if mode=='rewrite':assert prior_record is None;prior=ideal['J']*mask
    else:assert prior_record is not None and set(prior_record)==set(ideal);prior=prior_record['J']*mask
    identity=np.array_equal(mask,~np.eye(128,dtype=bool)) and bool(available.all()) and np.array_equal(prior,ideal['J'])
    if identity:
        # The fully available ideal prior is already the mathematical zero-loss solution.
        record['J']=prior.copy();stats=statistics(patterns,target,prior,mask,record['J'],0,True)
        assert stats['normal_residual']<=2e-12 and stats['field_error']<=1e-24
    else:record['J'],stats=solve(patterns,target,prior,mask,precision)
    dynamics.validate(record);assert np.all(record['J'][~mask]==0) and np.all(record['interaction_weights'][~available]==0)
    assert stats['field_error']+RIDGE*stats['prior_distance']<=stats['starting_field_error']+1e-9
    return record,stats
