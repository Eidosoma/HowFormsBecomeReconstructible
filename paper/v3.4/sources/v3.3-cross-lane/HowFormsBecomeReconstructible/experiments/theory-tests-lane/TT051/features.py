"""Whitelisted finite boundary features. No outcomes, probes or RNG are read."""
from io_utils import *

PORTS=np.zeros((3,16,16),bool)
for p,(y,x) in enumerate(((7,1),(3,10),(11,10))):PORTS[p,y:y+2,x:x+2]=True
FREE=~PORTS.any(axis=0)
B11=('aligned_plus_a','aligned_plus_b','aligned_minus_a','aligned_minus_b','current_margin','current_pass',
     'unsigned_access','history_single','history_spaced','history_clustered','signed_transfer')
ANCESTOR=('aligned_plus_a','aligned_plus_b','aligned_minus_a','aligned_minus_b','current_margin','current_pass',
          'unsigned_access','signed_transfer','packet_nonzero_fraction','packet_negative_mass',
          'packet_isolated_fraction','body_zero_contrast_fraction')
FAMILIES=('class_history','boundary','cheap_all','no_history','no_body_expression',
          'no_signed_record','no_packet_summaries','plus_parent','plus_grandparent')

def decode(packet):
    a=np.asarray(packet)
    if a.dtype==np.uint8:
        assert a.shape==(4096,);a=np.frombuffer(a.tobytes(),dtype='<f8').reshape(2,16,16)
    assert a.shape==(2,16,16) and a.dtype==np.float64 and np.isfinite(a).all()
    return a.copy()

def directed(w):return np.stack((w[0],np.roll(w[0],1,-1),w[1],np.roll(w[1],1,-2)))
def connectivity(w):
    adjacency=[[] for _ in range(256)]
    for d,y,x in np.ndindex(2,16,16):
        if w[d,y,x]==0:continue
        a=16*y+x;b=16*y+(x+1)%16 if d==0 else 16*((y+1)%16)+x
        adjacency[a].append(b);adjacency[b].append(a)
    reached=set(np.flatnonzero(PORTS[0]));stack=list(reached)
    while stack:
        for b in adjacency[stack.pop()]:
            if b not in reached:reached.add(b);stack.append(b)
    return np.array([i in reached for i in range(256)]).reshape(16,16)

def transfer(w,rule):
    raw=directed(w);den=abs(raw).sum(axis=0);k=np.divide(raw,den,out=np.zeros_like(raw),where=den>0)
    results=[]
    for operator in (k,abs(k)):
        z=np.zeros((16,16));z[PORTS[0]]=1
        for _ in range(64):
            z=(operator[0]*np.roll(z,-1,-1)+operator[1]*np.roll(z,1,-1)
               +operator[2]*np.roll(z,-1,-2)+operator[3]*np.roll(z,1,-2));z[PORTS[0]]=1
        results.append([float(z[PORTS[p]].mean()) for p in (1,2)])
    return min(rule*results[0][0],-rule*results[0][1]),min(results[1])

def packet_body(packet,end,mask,means,history,rule):
    w=decode(packet);end=np.asarray(end);mask=np.asarray(mask);means=np.asarray(means)
    assert end.shape==(2,16,16) and mask.shape==(16,16) and mask.dtype==bool and means.shape==(2,2)
    assert np.isfinite(end).all() and np.isfinite(means).all() and history in HISTORIES and rule in (-1,1)
    aligned=means*rule*np.array([[1.,-1.],[-1.,1.]])
    signed,unsigned=transfer(w,rule);minimum=float(aligned.min());h=HISTORIES.index(history)
    v=dict(zip(B11,[*aligned.ravel(),minimum,float(minimum>.25),unsigned,float(h==1),float(h==2),float(h==3),signed]))
    groups={k:'expression' for k in B11[:6]};groups.update({k:'history' for k in B11[7:10]})
    groups.update(unsigned_access='unsigned_transfer',signed_transfer='signed_record')
    def add(name,value,group):v[name]=float(value);groups[name]=group
    for name,flag in [('positive_subthreshold',0<minimum<=.25),('zero',minimum==0),('negative',minimum<0)]:
        add('class_'+name,flag,'expression_class')
    for i in range(4):
        for j in range(i,4):add(f'port_product_{i}_{j}',aligned.ravel()[i]*aligned.ravel()[j],'expression')
    aw=abs(w);active=w!=0;nonzero=aw[active];mass=float(aw.sum());raw=directed(w);den=abs(raw).sum(axis=0)
    k=np.divide(raw,den,out=np.zeros_like(raw),where=den>0);degree=(raw!=0).sum(axis=0)
    square=(k*k).sum(axis=0);neff=np.divide(1.,square,out=np.zeros_like(square),where=square>0)
    reach=connectivity(w)
    h,vv=w;cycle=np.stack((h,np.roll(vv,-1,-1),np.roll(h,-1,-2),vv))
    valid=(cycle!=0).all(axis=0);negative=(np.signbit(cycle).sum(axis=0)%2)==1
    values=dict(nonzero_fraction=active.mean(),negative_fraction=np.count_nonzero(w<0)/max(1,np.count_nonzero(active)),
        negative_mass=float(aw[w<0].sum())/mass if mass else 0.,mean_abs=aw.mean(),std_abs=aw.std(),maximum_abs=aw.max(),
        median_nonzero_abs=np.median(nonzero) if len(nonzero) else 0.,
        q10_nonzero_abs=np.quantile(nonzero,.1) if len(nonzero) else 0.,q90_nonzero_abs=np.quantile(nonzero,.9) if len(nonzero) else 0.,
        isolated_fraction=(degree[FREE]==0).mean(),degree_one_fraction=(degree[FREE]==1).mean(),degree_mean=degree[FREE].mean(),
        mean_log_strength=np.log1p(den[FREE]).mean(),strength_cv=den[FREE].std()/den[FREE].mean() if den[FREE].mean() else 0.,
        effective_degree=neff[FREE].mean(),signed_cancellation=abs(k.sum(axis=0))[FREE].mean(),
        input_reachable_fraction=reach[FREE].mean(),output_a_reachable=reach[PORTS[1]].mean(),output_b_reachable=reach[PORTS[2]].mean(),
        plaquette_frustration=np.count_nonzero(valid&negative)/max(1,np.count_nonzero(valid)),valid_plaquette_fraction=valid.mean())
    for name,value in values.items():add('packet_'+name,value,'signed_record' if name in ('negative_fraction','negative_mass','signed_cancellation','plaquette_frustration') else 'packet_summary')
    x=np.tanh(3.*end);d=(x[0]-x[1])/2;common=(x[0]+x[1])/2;live=FREE&~mask
    physical=np.stack((~mask&~np.roll(mask,-1,-1),~mask&~np.roll(mask,-1,-2)))
    q=np.stack((d*np.roll(d,-1,-1),d*np.roll(d,-1,-2)))
    conflict=(q!=0)&(w!=0)&(np.signbit(q)!=np.signbit(w))
    normmass=abs(k).sum();confmass=(abs(k)*directed(conflict)).sum()/normmass if normmass else 0.
    body=dict(abs_contrast=float(abs(d[live]).mean()) if live.any() else 0.,zero_contrast_fraction=float((d[live]==0).mean()) if live.any() else 0.,
        abs_common=float(abs(common[live]).mean()) if live.any() else 0.,raw_abs_contrast=float(abs((end[0]-end[1])[live]/2).mean()) if live.any() else 0.,
        abs_activity=float(abs(end[:,live]).mean()) if live.any() else 0.,saturation_fraction=float((abs(end[:,live])==2).mean()) if live.any() else 0.,
        exact_fallback_fraction=float(np.count_nonzero((q==0)&physical)/max(1,np.count_nonzero(physical))),conflict_mass=confmass)
    for name,value in body.items():add('body_'+name,value,'body_signed' if name=='conflict_mass' else 'body')
    return v,groups

def context(values,groups,injury,regime):
    assert isinstance(injury,int) and 0<=injury<=244 and regime in ('matched','independent')
    v=dict(values);g=dict(groups);d=(injury-24)/12;n=float(regime=='independent')
    for name,value in [('injury',d),('noise',n),('injury_noise',d*n),('injury_squared',d*d),('injury_squared_noise',d*d*n)]:
        v['condition_'+name]=value;g['condition_'+name]='condition'
    for name in ('current_margin','current_pass','unsigned_access','signed_transfer','body_abs_contrast','packet_plaquette_frustration'):
        for suffix,value in [('injury',d),('noise',n)]:
            key=name+'_by_'+suffix;v[key]=values[name]*value;g[key]=groups[name]
    return v,g

def columns(groups,family):
    assert family in FAMILIES
    result=[]
    for name,g in groups.items():
        original=name in B11
        if family=='class_history':include=g in ('expression_class','history','condition')
        elif family=='boundary':include=original or g=='condition'
        else:
            include=g not in ('parent','grandparent')
            if family=='no_history' and g=='history':include=False
            if family=='no_body_expression' and g in ('expression','expression_class','body','body_signed'):include=False
            if family=='no_signed_record' and g in ('signed_record','body_signed'):include=False
            if family=='no_packet_summaries' and (name.startswith('packet_') or name.startswith('packet_') and '_by_' in name):include=False
            if family in ('plus_parent','plus_grandparent') and g=='parent':include=True
            if family=='plus_grandparent' and g=='grandparent':include=True
        if include:result.append(name)
    return result

