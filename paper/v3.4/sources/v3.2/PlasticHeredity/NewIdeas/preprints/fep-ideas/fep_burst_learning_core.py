"""Finite hidden-error model, exact planning and predeclared training selection."""
from fractions import Fraction as F
from functools import lru_cache
import itertools
import math

MUS=(0,1,2,4,8,16)
K=F(19568652557,204800000000)


def canonical(values):
    g=math.gcd(*values)
    assert g>0
    return tuple(v//g for v in values),g


class Model:
    def __init__(self,T,alphas=(F(0),F(3,4)),rho=F(1,2)):
        self.T,self.alphas,self.rho=T,tuple(alphas),rho;self.M=len(alphas)
        self.D=math.lcm(*(20*a.denominator for a in alphas));assert self.D%(20*self.M)==0
        self.states=tuple((e,tau,z) for e in range(self.M) for tau in range(T+1) for z in (0,1))
        self.transitions=[]
        for a in alphas:
            p01=F(1,20)*(1-a);p11=F(1,20)+F(19,20)*a
            self.transitions.append(((int((1-p01)*self.D),int(p01*self.D)),(int((1-p11)*self.D),int(p11*self.D))))
        block=[T*(rho.denominator-rho.numerator)]+[rho.numerator]*T
        self.prior=canonical([block[tau]*(19 if z==0 else 1) for _,tau,z in self.states])[0]
        self.step=lru_cache(None)(self._step)

    def _step(self,t,w,label,frozen):
        values=[v if label is None or label==(int(0<tau<=t)^z) else 0 for v,(_,tau,z) in zip(w,self.states)]
        if frozen:
            marginal=[sum(values[i] for i,(_,j,_) in enumerate(self.states) if j==tau) for tau in range(self.T+1)]
            raw=[marginal[tau]*(19 if z==0 else 1) for _,tau,z in self.states]
            new,g=canonical(raw);return new,g*(self.D//(20*self.M))
        raw=[]
        for j in range(0,len(values),2):
            e=self.states[j][0];matrix=self.transitions[e]
            raw.extend(values[j]*matrix[0][z]+values[j+1]*matrix[1][z] for z in (0,1))
        return canonical(raw)

    def belief_fields(self,t,w):
        total=sum(w);q=F(sum(v for v,(_,tau,_) in zip(w,self.states) if 0<tau<=t),total)
        posterior=[]
        for d in (0,1):
            selected=[(v,tau) for v,(_,tau,z) in zip(w,self.states) if d==(int(0<tau<=t)^z)]
            posterior.append(F(sum(v for v,tau in selected if 0<tau<=t),sum(v for v,_ in selected)))
        return dict(q_orientation=q,post_orientation=posterior,
            q_error=F(sum(v for v,(_,_,z) in zip(w,self.states) if z),total),
            q_persistent=F(sum(v for v,(e,_,_) in zip(w,self.states) if e==self.M-1),total))


class Oracle:
    def __init__(self,m,mu,frozen=False):
        self.m,self.mu,self.frozen=m,F(mu),frozen;self.cache={}
        odd=list(range(1,m.T+1,2));num=len(odd)
        utility={t:[(F(1,m.T) if tau==0 else F(1,num) if tau in odd else F(0))
            +(F(m.T,1)/(m.rho*num*(m.T-tau+1)) if tau in odd and tau<=t else 0)
            +(self.mu/((1-m.rho)*m.T) if tau==0 else 0) for _,tau,_ in m.states] for t in range(1,m.T+1)}
        self.den=math.lcm(*(x.denominator for row in utility.values() for x in row))
        self.coeff={t:tuple(int(v*self.den) for v in row) for t,row in utility.items()}

    def scores(self,t,w):
        m=self.m;co=self.coeff[t];power=m.D**(m.T-t)
        total=sum(v*c for v,c in zip(w,co))
        forward=sum(v*c for v,c,(_,tau,z) in zip(w,co,m.states) if int(0<tau<=t)^z)
        if t==m.T:return dict(B=total,F=10*forward,R=10*(total-forward))
        new,g=m.step(t,w,None,self.frozen);future=g*self.value(t+1,new)
        buy=total*power
        for label in (0,1):
            new,g=m.step(t,w,label,self.frozen);buy+=g*self.value(t+1,new)
        return dict(B=buy,F=10*forward*power+future,R=10*(total-forward)*power+future)

    def value(self,t,w):
        key=t,w
        if key not in self.cache:
            if len(self.cache)>250000:raise RuntimeError('Predeclared 250000 Bellman-state ceiling exceeded')
            self.cache[key]=min(self.scores(t,w).values())
        return self.cache[key]

    def root(self):return F(self.value(1,self.m.prior),10*self.den*sum(self.m.prior)*self.m.D**(self.m.T-1))

    def graph(self):
        m=self.m;nodes=[];index={}
        def visit(t,w):
            if t>m.T:return None
            if (t,w) in index:return index[t,w]
            i=len(nodes);index[t,w]=i;nodes.append(None)
            scores=self.scores(t,w);action=min(('B','F','R'),key=lambda a:scores[a])
            children={str(d):visit(t+1,m.step(t,w,d,self.frozen)[0]) if t<m.T else None for d in (0,1)} if action=='B' else {'N':visit(t+1,m.step(t,w,None,self.frozen)[0]) if t<m.T else None}
            nodes[i]=dict(t=t,weights=w,action=action,children=children,**m.belief_fields(t,w))
            return i
        visit(1,m.prior);return nodes


def graph_for_schedule(m,mask):
    nodes=[];index={}
    def visit(t,w):
        if t>m.T:return None
        if (t,w) in index:return index[t,w]
        i=len(nodes);index[t,w]=i;nodes.append(None)
        risk=sum(v for v,(_,tau,z) in zip(w,m.states) if int(0<tau<=t)^z)
        action='B' if mask>>(t-1)&1 else 'F' if 2*risk<=sum(w) else 'R'
        children={str(d):visit(t+1,m.step(t,w,d,False)[0]) if t<m.T else None for d in (0,1)} if action=='B' else {'N':visit(t+1,m.step(t,w,None,False)[0]) if t<m.T else None}
        nodes[i]=dict(t=t,weights=w,action=action,children=children,**m.belief_fields(t,w))
        return i
    visit(1,m.prior);return nodes


def floor_graph(m):
    return [dict(t=t,weights=m.prior,action='F',children={'N':t if t<m.T else None},**m.belief_fields(t,m.prior)) for t in range(1,m.T+1)]


def conservative(T):
    nodes=[];index={}
    def visit(t,direction,count):
        if t>T:return None
        key=t,direction,count
        if key in index:return index[key]
        i=len(nodes);index[key]=i;nodes.append(None)
        action='B' if t%2==0 else 'R' if direction else 'F'
        children={}
        if action=='B':
            for d in (0,1):
                new_direction=direction if d==direction or not count else d
                new_count=0 if d==direction or count else 1
                children[str(d)]=visit(t+1,new_direction,new_count)
        else:children['N']=visit(t+1,direction,count)
        nodes[i]=dict(t=t,action=action,children=children,direction=direction,opposite_count=count)
        return i
    visit(1,0,0);return nodes


def physical(graph,T,tau,alpha):
    b=alpha.denominator;a=alpha.numerator;D=20*b;den=20*D**(T-1)
    transition=((19*b+a,b-a),(19*(b-a),b+19*a))
    mass=[[0,0] for _ in graph];mass[0]=[19,1];counts=[0,0,0,0];terminal=0
    for i in sorted(range(len(graph)),key=lambda j:graph[j]['t']):
        n=graph[i];t=n['t'];post=tau is not None and t>=tau;buy=n['action']=='B';lift=D**(T-t)
        for z,p in enumerate(mass[i]):
            if not p:continue
            d=int(post)^z;e=int(not buy and d!=int(n['action']=='R'))
            counts[0]+=p*lift*e;counts[1]+=p*lift*buy
            if post:counts[2]+=p*lift*e;counts[3]+=p*lift*buy
            child=n['children'][str(d) if buy else 'N']
            if t==T:assert child is None;terminal+=p
            else:
                for zz,prob in enumerate(transition[z]):mass[child][zz]+=p*prob
    assert terminal==den
    e,b,pe,pb=[F(v,den) for v in counts]
    return dict(onset=tau,cost=e+b/10,errors=e,purchases=b,post_cost=pe+pb/10,post_errors=pe,post_purchases=pb,
                recovery=None if tau is None else (pe+pb/10)/(T-tau+1))


def training(graph,T):
    odd=list(range(1,T+1,2));out={}
    for alpha in (F(0),F(3,4)):
        ws=[physical(graph,T,tau,alpha) for tau in [None,*odd]]
        s=ws[0]['cost']/T;b=s/2+sum(w['cost'] for w in ws[1:])/(2*len(odd)*T)
        r=sum(w['recovery'] for w in ws[1:])/len(odd)
        out[str(alpha)]=dict(worlds=ws,stable=s,B_odd=b,R_odd=r,C=b+r)
    return dict(settings=out,C=sum(x['C'] for x in out.values())/2,
                S=[out[str(a)]['stable'] for a in (F(0),F(3,4))])


def solve3(matrix,vector):
    rows=[[F(v) for v in row]+[F(y)] for row,y in zip(matrix,vector)]
    for col in range(3):
        pivot=next((j for j in range(col,3) if rows[j][col]),None)
        if pivot is None:return None
        rows[col],rows[pivot]=rows[pivot],rows[col];d=rows[col][col];rows[col]=[v/d for v in rows[col]]
        for j in range(3):
            if j!=col:
                scale=rows[j][col];rows[j]=[v-scale*w for v,w in zip(rows[j],rows[col])]
    return tuple(row[-1] for row in rows)


def select_pool(records,budget=K):
    names=sorted(records);vertices={}
    def candidate(cs):
        cs=tuple((n,F(w)) for n,w in cs if w)
        if not cs or any(w<0 for _,w in cs) or sum(w for _,w in cs)!=1:return
        stable=[sum(w*records[n]['S'][j] for n,w in cs) for j in (0,1)]
        if any(s>budget for s in stable):return
        cost=sum(w*records[n]['C'] for n,w in cs)
        vertices[cs]=dict(components=[dict(policy=n,weight=w) for n,w in cs],C=cost,S=stable)
    for n in names:candidate([(n,1)])
    for a,b in itertools.combinations(names,2):
        for j in (0,1):
            gap=records[b]['S'][j]-records[a]['S'][j]
            if gap:
                w=(budget-records[a]['S'][j])/gap
                candidate([(a,1-w),(b,w)])
    for ns in itertools.combinations(names,3):
        weights=solve3([[1]*3,*[[records[n]['S'][j] for n in ns] for j in (0,1)]],[1,budget,budget])
        if weights is not None:candidate(zip(ns,weights))
    assert vertices,'Always-follow floor must be feasible'
    best=min(vertices.values(),key=lambda r:(r['C'],len(r['components']),tuple(c['policy'] for c in r['components']),tuple(c['weight'] for c in r['components'])))
    return dict(selected=best,vertices=list(vertices.values()),objective='mean training B_odd+R_odd',constraints=[budget,budget])
