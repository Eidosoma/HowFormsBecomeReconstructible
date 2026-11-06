"""External observers; no score is available to an access policy or writer."""
import numpy as np
from h106 import model as m

TASK=(('query','query_correct','queries'),('exact','exact_correct','queries'),('complete','task_complete','tasks'),('bits','bit_correct','bits'),
    ('pre_query','pre_query_correct','queries'),('pre_exact','pre_exact_correct','queries'),('pre_bits','pre_bit_correct','bits'),('endpoint_fixed','endpoint_fixed','queries'))
CAPTURE=(('output_exact','output_exact','queries'),('free_exact','free_exact','queries'),('output_bits','output_bits','output_total'),('free_bits','free_bits','free_total'))

def network(raw,tape,block):
    cases=[];fidelity=[];suppliers=[];stability=[]
    for g in range(5):
        for p,policy in enumerate(m.POLICIES):
            for d in range(2):
                fields=raw[f'assay_g{g}_p{p}_d{d}_endpoint_fields'];selected=raw[f'assay_g{g}_p{p}_d{d}_selected_attempt']
                for a,branch in enumerate(m.BRANCHES):
                    for f in range(2):
                        for r in range(2):
                            x=raw['assessments'][g,p,a,d,f,r];pre=raw['preparations'][g,p,a,d,f,r];hit=x[:,48:]==tape['targets'][f];phit=pre[:,48:]==tape['targets'][f]
                            h=fields[a,f,r];fixed=np.where(h>m.TOL,1,np.where(h < -m.TOL,-1,x))==x
                            cases.append(dict(block=block,reader=policy,branch=branch,g=g,draw=d,founder=f,lineage=r,queries=8,tasks=1,bits=128,
                                query_correct=int((hit.sum(-1)>=14).sum()),exact_correct=int(hit.all(-1).sum()),task_complete=int((hit.sum(-1)>=14).all()),bit_correct=int(hit.sum()),
                                pre_query_correct=int((phit.sum(-1)>=14).sum()),pre_exact_correct=int(phit.all(-1).sum()),pre_bit_correct=int(phit.sum()),
                                endpoint_fixed=int(fixed[:,8:].all(-1).sum()),second_selected=int((selected[a,f,r]==1).sum())))
                            if g and a<3:
                                same=x==raw['suppliers'][g-1,a,f,r]
                                fidelity.append(dict(block=block,reader=policy,branch=branch,g=g,draw=d,founder=f,lineage=r,queries=8,output_total=128,free_total=448,
                                    output_exact=int(same[:,48:].all(-1).sum()),free_exact=int(same[:,8:].all(-1).sum()),output_bits=int(same[:,48:].sum()),free_bits=int(same[:,8:].sum())))
        if not g:continue
        for a,branch in enumerate(m.POLICIES):
            for d in range(2):
                for f in range(2):
                    for r in range(2):
                        x=raw['suppliers'][g-1,a,f,r];h=raw['static_fields'][g-1,a,d,f,r];same=np.where(h>m.TOL,1,np.where(h < -m.TOL,-1,x))==x
                        stability.append(dict(block=block,branch=branch,g=g,draw=d,founder=f,lineage=r,queries=8,free_total=448,
                            stable_free=int(same[:,8:].all(-1).sum()),stable_output=int(same[:,48:].all(-1).sum()),stable_free_bits=int(same[:,8:].sum())))
    for g in range(4):
        for p,policy in enumerate(m.POLICIES):
            for f in range(2):
                for r in range(2):
                    x=raw['suppliers'][g,p,f,r];pre=raw[f'supplier_g{g}_p{p}_phase0_final'][f,r];hit=x[:,48:]==tape['targets'][f];phit=pre[:,48:]==tape['targets'][f];hidden=x[:,8:48].astype(np.int64)
                    suppliers.append(dict(block=block,branch=policy,g=g,founder=f,lineage=r,queries=8,bits=128,
                        query_correct=int((hit.sum(-1)>=14).sum()),exact_correct=int(hit.all(-1).sum()),bit_correct=int(hit.sum()),pre_query_correct=int((phit.sum(-1)>=14).sum()),
                        hidden_distinct=len(np.unique(hidden,axis=0)),hidden_absolute_overlap=float(np.abs(hidden@hidden.T)[np.triu_indices(8,1)].mean()/40),
                        second_selected=int((raw[f'supplier_g{g}_p{p}_selected_attempt'][f,r]==1).sum())))
    return dict(cases=cases,fidelity=fidelity,stability=stability,suppliers=suppliers)

def independent_scores(raw,tape,rows):
    assert {k:len(v) for k,v in rows.items()}==dict(cases=720,fidelity=288,stability=96,suppliers=48)
    def counts(x,target):return [sum(int(x[q,j])==int(target[q,j-48]) for j in range(48,64)) for q in range(8)]
    for row in rows['cases']:
        p=m.POLICIES.index(row['reader']);a=m.BRANCHES.index(row['branch']);g,d,f,r=(row[k] for k in ('g','draw','founder','lineage'))
        x=raw['assessments'][g,p,a,d,f,r];pre=raw['preparations'][g,p,a,d,f,r];v=counts(x,tape['targets'][f]);u=counts(pre,tape['targets'][f])
        expected=dict(query_correct=sum(z>=14 for z in v),exact_correct=v.count(16),task_complete=int(all(z>=14 for z in v)),bit_correct=sum(v),
            pre_query_correct=sum(z>=14 for z in u),pre_exact_correct=u.count(16),pre_bit_correct=sum(u))
        h=raw[f'assay_g{g}_p{p}_d{d}_endpoint_fields'][a,f,r]
        expected['endpoint_fixed']=sum(all((1 if h[q,j]>1e-12 else -1 if h[q,j]<-1e-12 else int(x[q,j]))==int(x[q,j]) for j in range(8,64)) for q in range(8))
        expected['second_selected']=sum(v==1 for v in raw[f'assay_g{g}_p{p}_d{d}_selected_attempt'][a,f,r])
        for k,v in expected.items():assert row[k]==v
    for row in rows['fidelity']:
        p=m.POLICIES.index(row['reader']);a=m.POLICIES.index(row['branch']);g,d,f,r=(row[k] for k in ('g','draw','founder','lineage'))
        x=raw['assessments'][g,p,a,d,f,r];ref=raw['suppliers'][g-1,a,f,r]
        output=[sum(int(x[q,j])==int(ref[q,j]) for j in range(48,64)) for q in range(8)];free=[sum(int(x[q,j])==int(ref[q,j]) for j in range(8,64)) for q in range(8)]
        assert (row['output_exact'],row['free_exact'],row['output_bits'],row['free_bits'])==(output.count(16),free.count(56),sum(output),sum(free))
    for row in rows['stability']:
        a=m.POLICIES.index(row['branch']);g,d,f,r=(row[k] for k in ('g','draw','founder','lineage'));ref=raw['suppliers'][g-1,a,f,r];h=raw['static_fields'][g-1,a,d,f,r]
        counts_free=[];counts_output=[]
        for q in range(8):
            flags=[(1 if h[q,j]>1e-12 else -1 if h[q,j]<-1e-12 else int(ref[q,j]))==int(ref[q,j]) for j in range(8,64)]
            counts_free.append(sum(flags));counts_output.append(sum(flags[40:]))
        assert (row['stable_free'],row['stable_output'],row['stable_free_bits'])==(counts_free.count(56),counts_output.count(16),sum(counts_free))
    for row in rows['suppliers']:
        p=m.POLICIES.index(row['branch']);g,f,r=(row[k] for k in ('g','founder','lineage'));x=raw['suppliers'][g,p,f,r];pre=raw[f'supplier_g{g}_p{p}_phase0_final'][f,r]
        v=counts(x,tape['targets'][f]);u=counts(pre,tape['targets'][f])
        assert (row['query_correct'],row['exact_correct'],row['bit_correct'],row['pre_query_correct'])==(sum(z>=14 for z in v),v.count(16),sum(v),sum(z>=14 for z in u))
        assert row['hidden_distinct']==len({tuple(map(int,x[q,8:48])) for q in range(8)})
        overlap=sum(abs(sum(int(x[a,j])*int(x[b,j]) for j in range(8,48))) for a in range(8) for b in range(a+1,8))/(28*40)
        assert abs(row['hidden_absolute_overlap']-overlap)<1e-15
        assert row['second_selected']==sum(z==1 for z in raw[f'supplier_g{g}_p{p}_selected_attempt'][f,r])
    return sum(len(v) for v in rows.values())
