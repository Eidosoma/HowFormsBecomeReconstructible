"""Same-size two-profile Bayesian model and expanded exact policy pools."""
from fractions import Fraction as F

import fep_burst_alltiming_core as old
import fep_burst_pool_core as pool

K,MUS=pool.K,pool.MUS
DEVELOPMENT=old.PROFILES
HOLDOUT={
    'constant_10':(F(1,10),)*9,'constant_70':(F(7,10),)*9,
    'onset_after_3':(F(0),)*2+(F(9,10),)*7,
    'offset_after_3':(F(9,10),)*2+(F(0),)*7,
    'onset_after_7':(F(0),)*6+(F(9,10),)*3,
    'offset_after_7':(F(9,10),)*6+(F(0),)*3,
    'paired_low':tuple(map(F,('0','0','9/10','9/10','0','0','9/10','9/10','0'))),
    'paired_high':tuple(map(F,('9/10','9/10','0','0','9/10','9/10','0','0','9/10'))),
}


def generation(T):
    return {'training_00':(F(0),)*(T-1),
            'alternating_high':tuple(F(9,10) if t%2 else F(0) for t in range(1,T))}


class Model(old.previous.Model):
    def __init__(self,T):
        super().__init__(T,alphas=(F(0),F(9,10)))
        self.patterns=tuple(generation(T).values())

    def _step(self,t,w,label,frozen):
        if frozen:
            return super()._step(t,w,label,True)
        values=[v if label is None or label==(int(0<tau<=t)^z) else 0 for v,(_,tau,z) in zip(w,self.states)]
        raw=[]
        for j in range(0,len(values),2):
            e=self.states[j][0]
            matrix=self.transitions[int(e==1 and t%2==1)]
            raw.extend(values[j]*matrix[0][z]+values[j+1]*matrix[1][z] for z in (0,1))
        return old.previous.canonical(raw)

    def belief_fields(self,t,w):
        fields=super().belief_fields(t,w)
        fields['q_pattern']=fields.pop('q_persistent')
        return fields


Oracle=old.Oracle


def training(graph,T):
    settings={n:pool.cost_record(graph,p,T) for n,p in generation(T).items()}
    return dict(settings=settings,C=sum(v['summary']['J'] for v in settings.values())/2,
                S=[v['summary']['stable'] for v in settings.values()])


def names(family,expanded=True):
    original=pool.names(family)
    return original[:-1]+(tuple('target_'+n for n in original[:-1]) if expanded else ())+original[-1:]


def problem(records,hybrid,family,expanded=True):
    components=names(family,expanded);other,floor=components[:-1],components[-1:][0]
    A=[[F(1)]*len(other)+[F(0)]];b=[F(1)];ids=['weights:sum']
    for label in DEVELOPMENT:
        ps=records[label];fs,fr=[ps[floor]['summary'][k] for k in ('stable','R')]
        s=[ps[n]['summary']['stable']-fs for n in other]
        r=[ps[n]['summary']['R']-fr for n in other]
        A.extend((s+[F(0)],s+[F(1)],r+[F(1)],r+[F(1)]))
        b.extend((K-fs,K-fs+1,F(1,10)-fr+1,hybrid[label]-fr+1))
        ids.extend(label+':'+k for k in ('hard_budget','stable','always_recovery','hybrid_recovery'))
    return dict(A=A,b=b,c=[F(0)]*len(other)+[F(1)],row_ids=ids,
        variables=list(other)+['shifted_margin'],floor=floor,profiles=list(DEVELOPMENT),budget=K)


def same_behavior(left,right):
    seen=set();stack=[(0,0)]
    while stack:
        i,j=stack.pop()
        if (i,j) in seen:continue
        seen.add((i,j));a,b=left[i],right[j]
        if any(a[k]!=b[k] for k in ('t','action')) or set(a['children'])!=set(b['children']):return False
        if F(a['q_orientation'])!=F(b['q_orientation']) or tuple(map(F,a['post_orientation']))!=tuple(map(F,b['post_orientation'])):return False
        for label,x in a['children'].items():
            y=b['children'][label]
            if (x is None)!=(y is None):return False
            if x is not None:stack.append((x,y))
    return True
