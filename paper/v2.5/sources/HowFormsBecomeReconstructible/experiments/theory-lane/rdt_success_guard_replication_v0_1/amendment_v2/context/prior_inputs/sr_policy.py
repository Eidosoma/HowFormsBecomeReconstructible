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


def actions(history,passed):
    h=np.asarray(history);y=np.asarray(passed)
    if y.shape!=(len(h),4) or not np.isin(h,[0,1]).all() or not np.isin(y,[0,1]).all():
        raise ValueError('Fixed binary history and each policy own current outcome required')
    return np.stack([np.ones(len(h),bool),(h==0)|(y[:,1]==1),y[:,2]==1,np.zeros(len(h),bool)],axis=1)


def advance(incoming,outgoing,history,passed):
    a=actions(history,passed)
    if incoming.shape!=outgoing.shape or incoming.shape!=(len(history),4,2,16,16):
        raise ValueError('Four native packets per initial record required')
    return np.where(a[:,:,None,None,None],outgoing,incoming).copy(),a
