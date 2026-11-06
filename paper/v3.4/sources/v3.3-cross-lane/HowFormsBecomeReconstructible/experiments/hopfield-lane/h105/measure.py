"""Original-task curves, local capture fidelity and source/static diagnostics."""
import numpy as np
from h105 import model as m

TASK=(('query','query_correct','queries'),('exact','exact_correct','queries'),('complete','task_complete','tasks'),
    ('bits','bit_correct','bits'),('retained','initial_retained','queries'),('lost','initial_lost','queries'),('gained','initial_gained','queries'))
CAPTURE=(('output_exact','output_exact','queries'),('free_exact','free_exact','queries'),('output_bits','output_bits','output_total'),('free_bits','free_bits','free_total'))

def network(raw,tape,block):
    cases=[];fidelity=[];suppliers=[];stability=[]
    for g in range(5):
        for a,arm in enumerate(m.ARMS):
            for d in range(2):
                for f in range(2):
                    for r in range(2):
                        x=raw['assessments'][g,a,d,f,r];hit=x[:,48:]==tape['targets'][f];good=hit.sum(-1)>=14
                        initial=(raw['assessments'][0,a,d,f,r,:,48:]==tape['targets'][f]).sum(-1)>=14
                        cases.append(dict(block=block,arm=arm,g=g,draw=d,founder=f,lineage=r,queries=8,tasks=1,bits=128,
                            query_correct=int(good.sum()),exact_correct=int(hit.all(-1).sum()),task_complete=int(good.all()),bit_correct=int(hit.sum()),
                            initial_retained=int((initial&good).sum()),initial_lost=int((initial&~good).sum()),initial_gained=int((~initial&good).sum())))
                        if g and a<4:
                            reference=raw['suppliers'][g-1,a,f,r];same=x==reference
                            fidelity.append(dict(block=block,arm=arm,g=g,draw=d,founder=f,lineage=r,queries=8,output_total=128,free_total=448,
                                output_exact=int(same[:,48:].all(-1).sum()),free_exact=int(same[:,8:].all(-1).sum()),output_bits=int(same[:,48:].sum()),free_bits=int(same[:,8:].sum())))
                            fields=raw['static_fields'][g-1,a,d,f,r];fixed=np.where(fields>m.TOL,1,np.where(fields < -m.TOL,-1,reference))==reference
                            stability.append(dict(block=block,arm=arm,g=g,draw=d,founder=f,lineage=r,queries=8,free_total=448,
                                stable_free=int(fixed[:,8:].all(-1).sum()),stable_output=int(fixed[:,48:].all(-1).sum()),stable_free_bits=int(fixed[:,8:].sum())))
    for g in range(4):
        for a,arm in enumerate(m.WRITERS):
            for f in range(2):
                for r in range(2):
                    x=raw['suppliers'][g,a,f,r];hit=x[:,48:]==tape['targets'][f];hidden=x[:,8:48].astype(np.int64)
                    incoming=raw['records'][g,a,f,r];outgoing=raw['records'][g+1,a,f,r];body=m.effective(tape['base'],incoming,tape['supplier_mask'][g,f,r])
                    suppliers.append(dict(block=block,arm=arm,g=g,founder=f,lineage=r,queries=8,bits=128,query_correct=int((hit.sum(-1)>=14).sum()),
                        exact_correct=int(hit.all(-1).sum()),bit_correct=int(hit.sum()),hidden_distinct=len(np.unique(hidden,axis=0)),
                        hidden_absolute_overlap=float(np.abs(hidden@hidden.T)[np.triu_indices(8,1)].mean()/40),
                        incoming_norm=float(np.linalg.norm(incoming)),outgoing_norm=float(np.linalg.norm(outgoing)),
                        incoming_isolated=int((~(incoming!=0).any(-1)).sum()),outgoing_isolated=int((~(outgoing!=0).any(-1)).sum()),
                        body_isolated=int((np.abs(body).sum(-1)<=1e-12).sum())))
    return dict(cases=cases,fidelity=fidelity,suppliers=suppliers,stability=stability)

def independent_scores(raw,tape,rows):
    assert {k:len(v) for k,v in rows.items()}==dict(cases=280,fidelity=128,suppliers=64,stability=128)
    for row in rows['cases']:
        a=m.ARMS.index(row['arm']);g,d,f,r=(row[k] for k in ('g','draw','founder','lineage'))
        current=raw['assessments'][g,a,d,f,r];first=raw['assessments'][0,a,d,f,r]
        counts=[sum(int(current[q,j])==int(tape['targets'][f,q,j-48]) for j in range(48,64)) for q in range(8)]
        initial=[sum(int(first[q,j])==int(tape['targets'][f,q,j-48]) for j in range(48,64))>=14 for q in range(8)];good=[v>=14 for v in counts]
        expected=dict(query_correct=sum(good),exact_correct=counts.count(16),task_complete=int(all(good)),bit_correct=sum(counts),
            initial_retained=sum(x and y for x,y in zip(initial,good)),initial_lost=sum(x and not y for x,y in zip(initial,good)),initial_gained=sum(not x and y for x,y in zip(initial,good)))
        for k,v in expected.items():assert row[k]==v
    for row in rows['fidelity']:
        a=m.WRITERS.index(row['arm']);g,d,f,r=(row[k] for k in ('g','draw','founder','lineage'))
        x=raw['assessments'][g,a,d,f,r];reference=raw['suppliers'][g-1,a,f,r]
        output=[sum(int(x[q,j])==int(reference[q,j]) for j in range(48,64)) for q in range(8)]
        free=[sum(int(x[q,j])==int(reference[q,j]) for j in range(8,64)) for q in range(8)]
        assert (row['output_exact'],row['free_exact'],row['output_bits'],row['free_bits'])==(output.count(16),free.count(56),sum(output),sum(free))
    for row in rows['stability']:
        a=m.WRITERS.index(row['arm']);g,d,f,r=(row[k] for k in ('g','draw','founder','lineage'))
        h=raw['static_fields'][g-1,a,d,f,r];reference=raw['suppliers'][g-1,a,f,r];counts=[];outputs=[]
        for q in range(8):
            flags=[(1 if h[q,j]>1e-12 else -1 if h[q,j]<-1e-12 else int(reference[q,j]))==int(reference[q,j]) for j in range(8,64)]
            counts.append(sum(flags));outputs.append(sum(flags[40:]))
        assert (row['stable_free'],row['stable_output'],row['stable_free_bits'])==(counts.count(56),outputs.count(16),sum(counts))
    for row in rows['suppliers']:
        a=m.WRITERS.index(row['arm']);g,f,r=(row[k] for k in ('g','founder','lineage'));x=raw['suppliers'][g,a,f,r]
        counts=[sum(int(x[q,j])==int(tape['targets'][f,q,j-48]) for j in range(48,64)) for q in range(8)]
        assert (row['query_correct'],row['exact_correct'],row['bit_correct'])==(sum(v>=14 for v in counts),counts.count(16),sum(counts))
        assert row['hidden_distinct']==len({tuple(map(int,x[q,8:48])) for q in range(8)})
        overlap=sum(abs(sum(int(x[a,j])*int(x[b,j]) for j in range(8,48))) for a in range(8) for b in range(a+1,8))/(28*40)
        assert abs(row['hidden_absolute_overlap']-overlap)<1e-15
        for name,record in (('incoming',raw['records'][g,a,f,r]),('outgoing',raw['records'][g+1,a,f,r])):
            assert abs(row[name+'_norm']-float(np.sqrt(np.sum(record**2))))<2e-13
            assert row[name+'_isolated']==sum(all(v==0 for v in record[j]) for j in range(64))
        body=tape['base']+raw['records'][g,a,f,r]*tape['supplier_mask'][g,f,r];body[:8,8:]*=2;body[8:,:8]*=2
        assert row['body_isolated']==sum(sum(abs(v) for v in body[j])<=1e-12 for j in range(64))
    return sum(len(v) for v in rows.values())
