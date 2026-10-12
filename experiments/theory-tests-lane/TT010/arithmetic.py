"""Independent arithmetic reused from the completed TT009 audit."""

import math

import numpy as np

import support as s

BOOTSTRAP={}

def average(values):
    values=list(values);return math.fsum(values)/len(values)

def wilson(k,n):
    z=1.959963984540054;center=k+z*z/2;distance=z*math.sqrt(k*(n-k)/n+z*z/4)
    return max(0.,(center-distance)/(n+z*z)),min(1.,(center+distance)/(n+z*z))

def summary(values,cfg,signs=False):
    values=list(map(float,values));s.require(len(values)==8,'Eight original block units')
    seed=cfg['bootstrap_seed']
    if seed not in BOOTSTRAP:
        draws=np.random.Generator(np.random.PCG64(seed)).integers(0,8,(20000,8))
        BOOTSTRAP[seed]=np.stack([(draws==i).sum(axis=1) for i in range(8)],axis=1)
    resampled=np.sort(BOOTSTRAP[seed]@np.array(values)/8)
    def quantile(p):
        position=p*19999;index=math.floor(position);fraction=position-index
        return float(resampled[index]*(1-fraction)+resampled[index+1]*fraction)
    result=dict(mean=average(values),by_block={str(b):v for b,v in zip(cfg['blocks'],values,strict=True)},descriptive_block_bootstrap_95=[quantile(.025),quantile(.975)])
    if signs:result.update(positive_blocks=sum(v>0 for v in values),negative_blocks=sum(v<0 for v in values),tied_blocks=sum(v==0 for v in values))
    return result

def endpoint(data):
    windows=data['port_windows'];s.require(windows.shape[1]==32,'Thirty-two observations per endpoint')
    means=np.empty_like(data['mean_ports'])
    for frame in range(len(means)):
        for idx in np.ndindex(means[frame].shape):means[(frame,*idx)]=math.fsum(float(x) for x in windows[(frame,slice(None),*idx)])/32
    error=s.close(means,data['mean_ports'],1e-12,'Scalar raw-window means')
    margins=np.empty(means.shape[:-2])
    for frame,case,variant,rep in np.ndindex(margins.shape):
        founder=int(data['founders'][case]);rule=1 if founder%2==0 else -1
        margins[frame,case,variant,rep]=min(float(means[frame,case,variant,rep,c,p])*rule*(1 if c==0 else -1)*(1 if p==0 else -1) for c in range(2) for p in range(2))
    s.close(margins,data['min_margin'],1e-12,'Scalar raw-window margins');passed=margins>.25
    s.equal(passed,data['both_pass'],'Every independent strict endpoint')
    s.require(not passed[:,:,-1].any(),'Zero-record failure control')
    s.equal(data['mean_ports'][:,:,-1,:,0],data['mean_ports'][:,:,-1,:,1],'Zero-record cue equality')
    return means,margins,passed,error

def compare_tree(expected,actual,label):
    if isinstance(expected,dict):
        s.require(set(expected)==set(actual),'Summary fields '+label)
        for k in expected:compare_tree(expected[k],actual[k],label+'/'+k)
    elif isinstance(expected,list):
        s.require(isinstance(actual,list) and len(expected)==len(actual),'List schema '+label)
        for i,(first,second) in enumerate(zip(expected,actual,strict=True)):compare_tree(first,second,label+'/'+str(i))
    elif isinstance(expected,(bool,np.bool_)):s.require(isinstance(actual,bool) and bool(expected)==actual,'Boolean verdict '+label)
    elif isinstance(expected,(int,float,np.number)):s.close(expected,actual,1e-12,label)
    else:s.require(expected==actual,'Metadata '+label)

def compare_table(rows,path,keys):
    expected={tuple(str(r[k]) for k in keys):r for r in rows};actual=s.table(path)
    s.require(len(expected)==len(rows)==len(actual),'Table row count '+str(path));seen=set()
    for row in actual:
        key=tuple(row[k] for k in keys);s.require(key in expected and key not in seen,'Table identity '+str(path));seen.add(key)
        truth=expected[key];s.require(set(row)==set(truth),'Table columns '+str(path))
        for k,v in truth.items():
            if isinstance(v,str):s.require(row[k]==v,'Table label '+k)
            else:s.close(float(row[k]),float(v),1e-12,'Table value '+k)
    return len(rows)
