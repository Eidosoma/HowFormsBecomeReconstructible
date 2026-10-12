"""Complete continuation replay using qualified indexed-neighbor arithmetic."""
import numpy as np
import core as c
import support as s

def writer(body,mask,beta):
    """Flat edge endpoints independently reconstruct the exact writer and diagnostics."""
    a=np.tanh(beta*body).reshape(len(body),16,2,256)
    right=np.array([16*(i//16)+(i+1)%16 for i in range(256)])
    down=(np.arange(256)+16)%256
    difference=(a[:,:,0]-a[:,:,1])/2
    q=np.stack([difference*difference[...,neighbor] for neighbor in (right,down)],axis=-2)
    common=np.stack([a*a[...,neighbor] for neighbor in (right,down)],axis=-2).mean(axis=2)
    live=~mask.reshape(16,256)
    available=np.stack([live&live[:,neighbor] for neighbor in (right,down)],axis=-2)
    weights=np.where(available,np.where(q==0,common,q),0.)
    packets=np.ascontiguousarray(weights,dtype='<f8').view(np.uint8).reshape(len(body),16,4096)
    return packets,q,available,(right,down)

def mechanism(body,mask,previous_mask,beta):
    packet,q,available,neighbors=writer(body,mask,beta)
    returned=(previous_mask&~mask).reshape(16,256)
    incident=np.stack([returned|returned[:,neighbor] for neighbor in neighbors],axis=-2)&available
    result={}
    for label,scope in [('available_edges',available),('returning_edges',incident)]:
        result[label]=np.broadcast_to(scope,q.shape).sum(axis=(-2,-1))
        key='fallback_edges' if label=='available_edges' else 'returning_fallback_edges'
        result[key]=((q==0)&scope).sum(axis=(-2,-1))
    return result

def replay(packets,identity,generation,cfg,rhos=None):
    """Each branch has its own forcing correlation; all share masks and reset."""
    B=len(packets);dc=cfg['development_config'];cycle=cfg['cycle']
    s.require(packets.shape==(B,16,4096),'Whole branch panel')
    mask=c.masks(identity,f'E022_renewal_g{generation}',4)[:,:,1]
    w=c.decode(packets.reshape(B,4,4,4096))*c.available(mask)
    edges=c.edge_views(w[:,:,:,None]);base=c.rng('E022',identity,'develop',generation)
    shape=(2,4,16,16);birth=dc['birth_sd']*c.cues(base.standard_normal(shape))
    value=np.repeat(birth[None],B,axis=0);alive=(~mask)[None,:,:,None]
    cue=c.CUES.reshape(1,1,1,2,1);value*=alive;value[...,c.PORTS[0]]=cue
    innovation=None;moments=np.zeros((3,6));late=[]
    if rhos is not None:
        s.require(len(rhos)==B,'One correlation per branch')
        innovation=c.rng(cfg['innovation_namespace'],identity,'innovation',generation)
        innovation.standard_normal(shape)
    for step in range(cycle['read_steps']):
        z=base.standard_normal(shape)
        if innovation is None:
            noise=c.cues(z)[None]
        else:
            e=innovation.standard_normal(shape);seconds={}
            for i,rho in enumerate((1.,.999,0.)):
                y=z.copy() if rho==1. else rho*z+np.sqrt(1.-rho*rho)*e
                seconds[rho]=y
                moments[i]+=np.array([z.sum(),y.sum(),(z*z).sum(),(y*y).sum(),(z*y).sum(),z.size])
            first=c.paired(z)
            noise=np.stack([np.stack((first,c.paired(seconds[rho])),axis=2) for rho in rhos])
        value=c.step(value,edges,noise,dc,step>=cycle['settling_steps'])
        value*=alive;value[...,c.PORTS[0]]=cue
        if step>=cycle['read_steps']-dc['observe_steps']:late.append(c.read_ports(value))
    end=value.reshape(B,16,2,16,16);mask=mask.reshape(16,16,16)
    outgoing=writer(end,mask,dc['writer_beta'])[0]
    windows=np.stack(late).reshape(dc['observe_steps'],B,16,2,2)
    result=dict(masks=mask,birth=birth.reshape(16,2,16,16),end=end,outgoing=outgoing,
                port_windows=windows,mean_ports=windows.mean(axis=0))
    if innovation is not None:result['noise_moments']=moments
    return result

def compare(actual,expected,fields,label):
    for key in fields:s.equal(actual[key],expected[key],label+'/'+key)
    return dict(status='PASS',label=label,arrays=len(fields),
                sha256={key:s.descriptor(actual[key])['sha256'] for key in fields})

FIELDS=('masks','birth','end','outgoing','port_windows','mean_ports')

def union(serial,noise,gi):
    values={}
    for key in FIELDS:
        if key in ('masks','birth'):
            s.equal(serial[key][gi],noise[key][gi],'Shared '+key);values[key]=serial[key][gi]
        elif key=='port_windows':
            s.equal(serial[key][gi][:,[0,2]],noise[key][gi][:,:2],'Matched windows')
            values[key]=np.concatenate((serial[key][gi],noise[key][gi][:,2:]),axis=1)
        else:
            s.equal(serial[key][gi][[0,2]],noise[key][gi][:2],'Matched '+key)
            values[key]=np.concatenate((serial[key][gi],noise[key][gi][2:]),axis=0)
    return values
