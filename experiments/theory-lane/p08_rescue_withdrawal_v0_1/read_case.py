"""Selected-case spatial replay, paired across interventions and checked by flat replay."""
import numpy as np
import lineage_dynamics as dynamics


def replay(packets,mask,case,identity,generation,cfg):
    f,r=divmod(case,4);parameters=cfg['reader'];cycle=cfg['cycle']
    weights=dynamics.decode(packets)*dynamics.available_edges(mask)
    denominator=dynamics.incident(abs(weights))
    base=dynamics.stream('E022',identity,'develop',generation)
    innovation=dynamics.stream(cfg['innovation_namespace'],identity,'innovation',generation)
    x=parameters['birth_sd']*base.standard_normal((2,4,16,16))[f//2,r]
    innovation.standard_normal((2,4,16,16))
    birth=np.stack((x,x.copy()));value=np.repeat(birth[None],len(packets),axis=0)
    alive=~mask;value*=alive;value[...,dynamics.PORTS[0]]=dynamics.CUES[None,:,None]
    late=[]
    for t in range(cycle['read_steps']):
        z=base.standard_normal((2,4,16,16))[f//2,r]
        e=innovation.standard_normal((2,4,16,16))[f//2,r]
        noise=np.stack((z,0.*z+1.*e))  # rho=0, native ongoing-cue convention
        value=dynamics.step(value,weights[:,None],denominator[:,None],noise,parameters,t>=cycle['settling_steps'])
        value*=alive;value[...,dynamics.PORTS[0]]=dynamics.CUES[None,:,None]
        if t>=cycle['read_steps']-parameters['observe_steps']:late.append(dynamics.read_ports(value))
    windows=np.stack(late)
    return dict(birth=birth,end=value,port_windows=windows,mean_ports=windows.mean(axis=0))
