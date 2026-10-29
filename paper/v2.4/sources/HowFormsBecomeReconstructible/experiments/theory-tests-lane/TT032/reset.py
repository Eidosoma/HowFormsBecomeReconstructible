"""Physical initializer; no task labels or observations accepted."""
from common import *
import design


def initial(data,resting,variant):
    if set(data)!={'injured_V','incoming','fresh'} or variant not in design.RESETS or not np.isfinite(resting):
        raise ValueError('declared physical reset inputs required')
    v,theta,fresh=data['injured_V'],data['incoming'],data['fresh']
    model.boundary.field(v,4);model.boundary.field(theta,4)
    if fresh.dtype!=np.bool_ or fresh.shape!=v.shape or not np.all(fresh.sum((1,2))==128):
        raise ValueError('half-body physical mask required')
    r=v.copy()
    if variant=='uniform':r-=resting/2
    elif variant=='corrected':r[fresh]-=resting
    else:r[~fresh]-=resting
    return dict(V=v.copy(),ema=np.zeros_like(v),R=r,theta=theta.copy())


def physical(own,source,jitter,resting):
    if source not in design.BODIES:raise ValueError('declared body source required')
    donor=((np.arange(16)//4+2)%4)*4+np.arange(16)%4
    v=own['injured_V'] if source=='own' else own['injured_V'][donor] if source=='foreign' else resting+jitter
    return dict(injured_V=v.copy(),incoming=own['incoming'].copy(),fresh=own['fresh'].copy())


def state_bytes(state):
    assert set(state)==set(KEYS)
    return b''.join(state[k].tobytes() for k in KEYS)
