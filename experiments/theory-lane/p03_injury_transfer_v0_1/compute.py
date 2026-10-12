"""Shape adapter; native dynamics and scoring stay in the checked reader."""
import numpy as np
from reader import generators,read_fixed,scores


def experiment(source,block,cfg):
    n=len(source['founders']);r=len(cfg['replicates']);v=len(cfg['variants'])
    founders=np.tile(source['founders'],2)
    raw=read_fixed(np.tile(source['packets'],(2,1,1)),source['masks'].reshape(2*n,r,16,16),
        founders,np.tile(source['recipients'],2),generators(cfg,block,cfg['replicates']),
        cfg['reader'],cfg['budgets'],cfg['settling_steps'])
    score=scores(raw['mean_ports'],founders,cfg['reader']['margin'])
    return dict(birth=raw['birth'].reshape(2,n,r,2,16,16),
        end=raw['end'][0].reshape(2,n,v,r,2,16,16),
        mean_ports=raw['mean_ports'][0].reshape(2,n,v,r,2,2),
        port_windows=raw['port_windows'][0].reshape(cfg['reader']['observe_steps'],2,n,v,r,2,2).transpose(1,0,2,3,4,5,6),
        min_margin=score['min_margin'][0].reshape(2,n,v,r),both_pass=score['both_pass'][0].reshape(2,n,v,r),
        budgets=np.array(cfg['budgets']))
