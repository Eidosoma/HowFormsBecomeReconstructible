"""Current-read actions only; no future inputs or file access."""
import numpy as np


def classify(windows,rules):
    x=np.asarray(windows);rules=np.asarray(rules)
    if x.ndim!=5 or x.shape[2:]!=(4,2,2) or len(x)!=len(rules) or not np.isin(rules,[-1,1]).all():
        raise ValueError('Packet x frame x four policies x cue x port windows required')
    if not np.isfinite(x).all():raise ValueError('Finite native windows required')
    aligned=x.mean(axis=1)*rules[:,None,None,None]*np.array([[1.,-1.],[-1.,1.]])
    correct=aligned.min(axis=(-2,-1))>.25
    opposite=aligned.max(axis=(-2,-1))<-.25
    if (correct&opposite).any():raise ArithmeticError('Incompatible task identities')
    return correct.astype(np.uint8),correct.astype(np.int8)-opposite.astype(np.int8),aligned


def actions(passed,order):
    y=np.asarray(passed);rank=np.asarray(order)
    if y.shape!=(4,4) or not np.isin(y,[0,1]).all():raise ValueError('Four packets by four binary policy outcomes required')
    if rank.shape!=(4,) or rank.dtype.kind not in 'iu' or sorted(rank.tolist())!=[0,1,2,3]:raise ValueError('Uniform permutation input required')
    result=np.zeros((4,4),bool);result[:,0]=True;result[:,2]=y[:,2]==1
    result[rank[:int(result[:,2].sum())],1]=True
    return result


def advance(incoming,outgoing,passed,order):
    a=actions(passed,order)
    if incoming.shape!=outgoing.shape or incoming.shape!=(4,4,2,16,16):
        raise ValueError('Four native packets per initial record required')
    return np.where(a[:,:,None,None,None],outgoing,incoming).copy(),a
