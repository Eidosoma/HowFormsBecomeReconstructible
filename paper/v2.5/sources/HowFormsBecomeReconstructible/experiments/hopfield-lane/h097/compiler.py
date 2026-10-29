"""A fixed symmetric, topology-constrained ridge fit to learned-pattern fields."""
import numpy as np
from h093 import model as legacy,dynamics
RIDGE=.1
RELATIVE_TOL=1e-12
MAX_ITERATIONS=512

def validate_mask(mask,available):
    assert mask.shape==(128,128) and mask.dtype==np.dtype('bool')
    assert np.array_equal(mask,mask.T) and not np.diag(mask).any()
    assert available.shape==(48,) and available.dtype==np.dtype('bool')

def project(a,mask):return .5*(a+a.T)*mask

def solve(patterns,target,prior,mask):
    """Solve for a symmetric allowed correction; no prediction target enters here."""
    assert patterns.ndim==2 and target.shape==patterns.shape and prior.shape==mask.shape==(patterns.shape[1],)*2
    assert np.array_equal(prior,prior.T) and np.all(prior[~mask]==0)
    n=len(patterns)
    def action(x):return project(patterns.T@(patterns@x)/n,mask)+RIDGE*x
    rhs=project(patterns.T@(target-patterns@prior)/n,mask)
    correction=np.zeros_like(prior);residual=rhs.copy();direction=residual.copy();squared=float(np.sum(residual*residual))
    cutoff=RELATIVE_TOL*max(1.,float(np.linalg.norm(rhs)));iterations=0
    while np.sqrt(squared)>cutoff:
        assert iterations<MAX_ITERATIONS,'constrained writer did not converge'
        q=action(direction);denominator=float(np.sum(direction*q));assert denominator>0
        alpha=squared/denominator;correction+=alpha*direction;residual-=alpha*q
        updated=float(np.sum(residual*residual));direction=residual+(updated/squared)*direction;squared=updated;iterations+=1
    record=prior+correction
    gradient=project(patterns.T@(patterns@record-target)/n,mask)+RIDGE*(record-prior)
    norm=float(np.linalg.norm(gradient));assert norm<=5e-10
    return record,dict(iterations=iterations,normal_residual=norm,
        field_error=float(np.square(patterns@record-target).sum()/n),prior_distance=float(np.square(record-prior).sum()),
        starting_field_error=float(np.square(patterns@prior-target).sum()/n))

def constrain(packet):
    assert set(packet)=={'completion','mask','available','prior_record','mode'}
    completion,mask,available,prior_record,mode=(packet[k] for k in ('completion','mask','available','prior_record','mode'))
    validate_mask(mask,available);assert mode in ('rewrite','copy_repair')
    ideal=legacy.compile_record(completion,'neural');record={k:v.copy() for k,v in ideal.items()}
    record['interaction_weights']*=available
    patterns=np.concatenate((legacy.X,completion['outputs']),axis=1).astype(float)
    target=dynamics.fields(ideal,patterns)-dynamics.factor_fields(record,patterns)
    if mode=='rewrite':
        assert prior_record is None;prior=ideal['J']*mask
    else:
        assert prior_record is not None and set(prior_record)==set(ideal);prior=prior_record['J']*mask
    record['J'],stats=solve(patterns,target,prior,mask)
    dynamics.validate(record);assert np.all(record['J'][~mask]==0) and np.all(record['interaction_weights'][~available]==0)
    assert stats['field_error']+RIDGE*stats['prior_distance']<=stats['starting_field_error']+1e-9
    return record,stats

def copy(packet):
    assert set(packet)=={'record','mask','available'}
    record,mask,available=(packet[k] for k in ('record','mask','available'));validate_mask(mask,available)
    result={k:v.copy() for k,v in record.items()};result['J']*=mask;result['interaction_weights']*=available
    dynamics.validate(result);return result
