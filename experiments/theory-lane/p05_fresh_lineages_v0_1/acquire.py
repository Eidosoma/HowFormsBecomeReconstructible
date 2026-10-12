"""Native E016 consistent teaching, without the unused teaching regimes."""
import numpy as np
from lineage_dynamics import PORTS,RULES,CUES,stream,encode,paired_founders,neighbors


def teach(block,cfg):
    births=[];ends=[];captures=[];total=np.zeros((4,2,16,16))
    for cue,polarity in zip(CUES,(1.,-1.)):
        random=stream('E016',block,'teach',0)
        birth=polarity*cfg['birth_sd']*paired_founders(random.standard_normal((2,16,16)))
        value=birth.copy();births.append(birth)
        target=np.stack((np.full(4,cue),RULES*cue,-RULES*cue),axis=1)
        for p in range(3):value[:,PORTS[p]]=target[:,p,None]
        states=[]
        for t in range(cfg['teach_steps']):
            noise=polarity*paired_founders(random.standard_normal((2,16,16)))
            drift=value-value**3+cfg['teacher_gain']*(neighbors(value,np.ones((2,16,16)))/4.-value)
            value=np.clip(value+cfg['dt']*drift+cfg['noise']*noise,-2.,2.)
            for p in range(3):value[:,PORTS[p]]=target[:,p,None]
            if t>=cfg['teach_steps']-cfg['capture_steps']:
                states.append(value.copy());x=np.tanh(cfg['writer_beta']*value)
                total+=np.stack((x*np.roll(x,-1,-1),x*np.roll(x,-1,-2)),axis=-3)
        ends.append(value);captures.append(np.stack(states))
    weights=total/(2*cfg['capture_steps'])
    return dict(birth=np.stack(births),end=np.stack(ends),capture_states=np.stack(captures),weights=weights,acquired=encode(weights))
