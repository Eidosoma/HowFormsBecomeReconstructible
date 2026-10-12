"""Independent D167 direct-template and saved-algebra checks; no simulator."""
import hashlib
import numpy as np
from . import passive_stages as m


def same(got,want):
    if isinstance(want,dict):
        assert isinstance(got,dict) and set(got)==set(want)
        for key in want:same(got[key],want[key])
    elif isinstance(want,(list,tuple)):
        assert isinstance(got,(list,tuple)) and len(got)==len(want)
        for x,y in zip(got,want):same(x,y)
    elif want is None or isinstance(want,(str,bool,int)):
        assert got==want and (type(got) is bool if isinstance(want,bool) else True)
    else:
        assert np.shape(got)==np.shape(want)
        np.testing.assert_allclose(got,want,atol=2e-10,rtol=0)


def packet(b):
    shape=b.shape[:-1]+(16,16)
    return np.frombuffer(b.tobytes(),dtype='<f8').reshape(shape)


def templates():
    a=np.ones((16,16));a[8:]=-1
    b=np.ones((16,16));b[:,4:8]=-1;b[:,12:16]=-1
    return np.stack((a,b))


def gather(raw):
    by_name={'input':packet(raw['input']),'routed':packet(raw['routed']),
        'outgoing':packet(raw['outgoing']),'terminal_packet':packet(raw['terminal_packet']),
        'tanh_write_R':np.tanh(raw['write_states'][:,:,:,3,2])}
    for label,key,times,names in [('read','read_states',(0,1,100,101,300),('V','ema','R')),
        ('write','write_states',(0,1,300,1000),('V','ema','R','theta')),
        ('final','terminal_states',(0,1,100,300),('V','ema','R'))]:
        for ti,t in enumerate(times):
            for ki,name in enumerate(names):by_name[f'{label}:{t}:{name}']=raw[key][:,:,:,ti,ki]
    assert set(by_name)==set(m.STAGES) and len(by_name)==48
    return np.stack([by_name[k] for k in m.STAGES],axis=3)


def direct(x,guide):
    base=templates();target=np.stack([np.roll(base[0],i,axis=0) for i in range(16)]+[
        np.roll(base[1],i,axis=1) for i in range(8)]).reshape(24,256)
    result=np.empty((4,4,2,48,5));scores=[]
    for life in range(4):
        flat=x[life].reshape(-1,256);centered=flat-flat.sum(1)[:,None]/256
        sd=np.sqrt(np.sum(centered**2,1)/256);scale=np.where(sd>0,sd,1)
        normal=centered/scale[:,None]
        g=guide[life]-guide[life].sum(axis=(1,2))[:,None,None]/256
        g/=np.sqrt(np.sum(g*g,axis=(1,2))/256)[:,None,None]
        bank=np.stack([np.roll(g[r],(i,j),(0,1)) for r in range(2) for i in range(16) for j in range(16)]).reshape(512,256)
        score=(normal@bank.T/256).reshape(4,2,48,2,16,16);scores.append(score)
        best=(normal@target.T/256).reshape(4,2,48,24)
        canonical=(normal@base.reshape(2,256).T/256).reshape(4,2,48,2)
        peaks=np.stack((best[...,:16].max(-1),best[...,16:].max(-1)),-1)
        guide_peak=np.amax(score,axis=(-2,-1))
        for gidx in range(4):
            own=gidx//2;other=1-own
            result[life,gidx,...,0]=peaks[gidx,...,own]
            result[life,gidx,...,1]=peaks[gidx,...,other]
            result[life,gidx,...,2]=guide_peak[gidx,...,own]-guide_peak[gidx,...,other]
            result[life,gidx,...,3]=canonical[gidx,...,own]-canonical[gidx,...,other]
        result[life,...,4]=np.sqrt(np.sum(flat*flat,axis=1)/256).reshape(4,2,48)
    return result,np.stack(scores)


def preferences(raw):
    v=raw['terminal_states'][:,:,:,:,0];result=np.zeros((4,4,2,4))
    for life in range(4):
        for group in range(4):
            for copy in range(2):
                for t in range(4):
                    field=v[life,group,copy,t];valid=np.abs(field)>.2
                    counts=[np.count_nonzero(((field>0)==(pattern>0))&valid) for pattern in templates()]
                    result[life,group,copy,t]=(counts[group//2]-counts[1-group//2])/256
    return result


def block(raw,got,meta=None):
    m.validate(raw);assert set(got)=={'fields','preference'}
    x=gather(raw);want,scores=direct(x,raw['guide']);pref=preferences(raw)
    same(got['fields'],want);same(got['preference'],pref)
    assert got['fields'].dtype==got['preference'].dtype==np.float64
    np.testing.assert_array_equal(raw['input'][:,:,0],raw['input'][:,:,1])
    np.testing.assert_array_equal(raw['routed'][:,:,0],raw['routed'][:,:,1])
    for g in range(4):np.testing.assert_array_equal(raw['input'][:,g,0],raw['founder_packets'][:,g//2])
    np.testing.assert_array_equal(raw['write_states'][:,:,:,0,:3],raw['read_states'][:,:,:,-1])
    np.testing.assert_array_equal(raw['write_states'][:,:,:,0,3],0)
    for a,b in ((0,1),(2,3)):
        np.testing.assert_array_equal(raw['read_states'][:,a],raw['read_states'][:,b])
        np.testing.assert_array_equal(raw['write_states'][:,a,:,:2],raw['write_states'][:,b,:,:2])
    for key in ('read_states','terminal_states'):
        for j in (1,2):np.testing.assert_array_equal(raw[key][:,:,:,0,j],raw[key][:,:,:,0,0])
        assert not np.array_equal(raw[key][:,:,0,0],raw[key][:,:,1,0])
    assert not np.array_equal(raw['read_states'][:,:,:,0],raw['terminal_states'][:,:,:,0])
    bounded=x[:,:,:,m.STAGES.index('tanh_write_R')]
    centered=bounded-bounded.mean(axis=(-2,-1),keepdims=True)
    sd=np.sqrt(np.mean(centered**2,axis=(-2,-1),keepdims=True));assert np.all(sd>1e-9)
    same(packet(raw['outgoing']),centered*(.3/np.maximum(sd,1e-9)))
    for life in range(4):
        for g in range(4):
            for copy in range(2):
                for phase,(supplied,routed,label) in enumerate((('input','routed','selector'),('outgoing','terminal_packet','terminal_selector'))):
                    sc=scores[life,g,copy,m.STAGES.index(supplied)]
                    same(raw['scores'][life,g,copy,phase],sc)
                    maxima=sc.max(axis=(1,2));tie=abs(maxima[0]-maxima[1])<=1e-12
                    family=-1 if tie else int(np.argmax(maxima))
                    shift=(0,0) if tie else tuple(int(v) for v in np.argwhere(abs(sc[family]-maxima[family])<=1e-12)[0])
                    before=packet(raw[supplied][life,g,copy]);after=packet(raw[routed][life,g,copy])
                    np.testing.assert_array_equal(after,np.roll(before,tuple(-v for v in shift),(0,1)))
                    if meta is not None:
                        item=meta['lives'][life]['cycles'][g][copy][label]
                        assert item['inferred_family']==family and item['family_tie']==tie
                        assert item['chosen_forward_shift']==list(shift)
                        same(item['family_maxima'],maxima.tolist())
                        assert item['input_sha256']==hashlib.sha256(raw[supplied][life,g,copy].tobytes()).hexdigest()
                        assert item['output_sha256']==hashlib.sha256(raw[routed][life,g,copy].tobytes()).hexdigest()
    ix={k:m.STAGES.index(k) for k in ('input','routed','outgoing','terminal_packet','final:300:V')}
    first=want[:,:,:,ix['input']];out=want[:,:,:,ix['outgoing']]
    initial=np.stack((first[...,0],first[...,0]-first[...,1],first[...,2],want[:,:,:,ix['routed'],3]),-1)
    end=np.stack((out[...,0],out[...,0]-out[...,1],out[...,2],want[:,:,:,ix['terminal_packet'],3],
        pref[...,-1],want[:,:,:,ix['final:300:V'],4]),-1)
    for b in range(2):same(raw['initial_features'],initial[:,:,b])
    same(raw['diagnostic_features'],end)
    return dict(passes=True,fields=1536,measurements=7680,preferences=128,packet_routes=64,
        max_measurement_error=float(np.max(abs(got['fields']-want))),outcomes_used=False,new_dynamics=0)


def describe(x,ids):
    n=len(ids);means=x.sum(1)/4;g=means[:,1]-means[:,0];avg=g.sum()/n
    copy=x.sum(axis=(0,1))/(n*4);sd=np.sqrt(np.sum((x-copy)**2,axis=(0,1))/(n*4))
    omitted=np.array([np.sum(g[np.arange(n)!=i])/(n-1) for i in range(n)])
    top=max(range(n),key=lambda i:abs(g[i]));total=np.abs(g).sum()
    return dict(copy_mean=copy.tolist(),copy_sd=sd.tolist(),gap_mean=float(avg),
        gap_sd=float(np.sqrt(np.sum((g-avg)**2)/n)),mean_absolute_gap=float(np.abs(g).sum()/n),
        founder_means=means.tolist(),founder_gap=g.tolist(),gap_minimum=float(min(g)),gap_maximum=float(max(g)),
        positive=sum(v>1e-12 for v in g),negative=sum(v<-1e-12 for v in g),numerical_zero=sum(abs(v)<=1e-12 for v in g),
        omitted_founder_means=omitted.tolist(),omission_minimum=float(min(omitted)),omission_maximum=float(max(omitted)),
        largest_absolute_founder=int(ids[top]),largest_absolute_share=float(abs(g[top])/total) if total else None)


def check_row(got,d,p,di,pi,**labels):
    a,b=describe(d,di),describe(p,pi)
    same(got,dict(**labels,development=a,pilot=b,gap_change=b['gap_mean']-a['gap_mean'],
        copy_mean_change=[y-x for x,y in zip(a['copy_mean'],b['copy_mean'])]))


def summary(s,a,di,pi):
    m.validate_panel(a,di,pi)
    assert s['schema']=='d167_passive_stages_v1' and s['development_ids']==di.tolist() and s['pilot_ids']==pi.tolist()
    assert s['groups']==list(m.GROUPS) and s['stages']==list(m.STAGES) and s['metrics']==list(m.METRICS)
    assert s['reference_chain']==list(m.CHAIN) and s['final_times']==[0,1,100,300] and s['sign_tolerance']==1e-12
    assert len(s['field_rows'])==960 and len(s['preference_rows'])==16 and len(s['transition_rows'])==260
    assert s['fields_measured']==1536*(len(di)+len(pi)) and s['diagnostic_copies']==32*(len(di)+len(pi))
    for k in ('new_fits','new_forecasts','new_dynamics','new_diagnostic_cycles','new_founders'):assert s[k]==0
    for k in ('outcomes_used','forecasts_used','prospective_evidence','confidence_intervals','automatic_successor'):assert s[k] is False
    for k in ('all_cases_retained','post_test_explanation','source_primary_unchanged'):assert s[k] is True
    d,p=a['development_fields'],a['pilot_fields']
    for g,name in enumerate(m.GROUPS):
        for j,stage in enumerate(m.STAGES):
            for k,metric in enumerate(m.METRICS):
                check_row(s['field_rows'][g*240+j*5+k],d[:,:,g,:,j,k],p[:,:,g,:,j,k],di,pi,group=name,stage=stage,metric=metric)
        for j,t in enumerate((0,1,100,300)):
            check_row(s['preference_rows'][g*4+j],a['development_preference'][:,:,g,:,j],a['pilot_preference'][:,:,g,:,j],di,pi,group=name,time=t)
        for j,(left,right) in enumerate(zip(m.CHAIN,m.CHAIN[1:])):
            u,v=m.STAGES.index(left),m.STAGES.index(right)
            for k,metric in enumerate(m.METRICS):
                check_row(s['transition_rows'][g*65+j*5+k],d[:,:,g,:,v,k]-d[:,:,g,:,u,k],
                    p[:,:,g,:,v,k]-p[:,:,g,:,u,k],di,pi,group=name,left=left,right=right,metric=metric)
    return dict(passes=True,field_rows=960,preference_rows=16,transition_rows=260,all_cases_retained=True,outcomes_used=False)
