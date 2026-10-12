"""Paired native assessments and separate intended/opposite endpoint scores."""
import numpy as np
from reader import generators,read_fixed,scores


def evaluate(packets,masks,founders,recipients,block,replicates,cfg):
    raw=read_fixed(packets,masks,founders,recipients,generators(cfg,block,replicates),cfg['reader'],cfg['budgets'],cfg['settling_steps'])
    intended=scores(raw['mean_ports'],founders,cfg['reader']['margin'])
    opposite=scores(raw['mean_ports'],founders^1,cfg['reader']['margin'])
    assert not (intended['both_pass']&opposite['both_pass']).any()
    return dict(birth=raw['birth'],end=raw['end'][0],mean_ports=raw['mean_ports'][0],port_windows=raw['port_windows'][0],
        min_margin=intended['min_margin'][0],both_pass=intended['both_pass'][0],
        opposite_margin=opposite['min_margin'][0],opposite_pass=opposite['both_pass'][0])


def experiment(data,block,cfg):
    raw=evaluate(data['packets'],data['masks'],data['founders'],data['recipients'],block,cfg['replicates'],cfg)
    control=evaluate(data['packets'],data['original_masks'],data['founders'],data['recipients'],block,cfg['original_replicates'],cfg)
    raw.update({'control_'+k:v for k,v in control.items()});raw['budgets']=np.array(cfg['budgets'])
    return raw
