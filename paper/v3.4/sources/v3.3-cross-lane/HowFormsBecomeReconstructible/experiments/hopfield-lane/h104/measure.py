"""Task and captured-pattern fidelity are separate observers."""
import numpy as np
from h104 import model as m

METRICS=(('task_query','task_query_correct','queries'),('task_exact','task_exact_correct','queries'),
    ('task_complete','task_complete','tasks'),('task_bits','task_bit_correct','task_bits'),
    ('captured_output_exact','captured_output_exact','queries'),('captured_free_exact','captured_free_exact','queries'),
    ('captured_output_bits','captured_output_bits','task_bits'),('captured_free_bits','captured_free_bits','free_bits'))

def network(raw,tape,block):
    rows=[];supplier=[];static=[]
    for b,name in enumerate(m.BRANCHES):
        for i,injury in enumerate(m.INJURIES):
            for u,birth in enumerate(m.BIRTHS):
                for d in range(2):
                    for f in range(2):
                        for r in range(2):
                            x=raw['assessments'][b,i,u,d,f,r];ref=raw['reference'][b,f,r]
                            task=(x[:,48:]==tape['targets'][f]);output=(x[:,48:]==ref[:,48:]);free=(x[:,8:]==ref[:,8:])
                            good=task.sum(-1)>=14
                            rows.append(dict(block=block,branch=name,injury=injury,birth=birth,draw=d,founder=f,recipient=r,
                                queries=8,tasks=1,task_bits=128,free_bits=448,task_query_correct=int(good.sum()),
                                task_exact_correct=int(task.all(-1).sum()),task_complete=int(good.all()),task_bit_correct=int(task.sum()),
                                captured_output_exact=int(output.all(-1).sum()),captured_free_exact=int(free.all(-1).sum()),
                                captured_output_bits=int(output.sum()),captured_free_bits=int(free.sum())))
            for d in range(2):
                for f in range(2):
                    for r in range(2):
                        h=raw['static_fields'][b,i,d,f,r];old=raw['reference'][b,f,r]
                        same=np.where(h>m.TOL,1,np.where(h < -m.TOL,-1,old))==old
                        static.append(dict(block=block,branch=name,injury=injury,draw=d,founder=f,recipient=r,queries=8,
                            stable_free=int(same[:,8:].all(-1).sum()),stable_output=int(same[:,48:].all(-1).sum()),
                            stable_free_bits=int(same[:,8:].sum()),free_bits=448))
    for f in range(2):
        for r in range(2):
            x=raw['supplier_final'][f,r];good=(x[:,48:]==tape['targets'][f]);z=x[:,8:48].astype(np.int64)
            supplier.append(dict(block=block,founder=f,recipient=r,queries=8,task_query_correct=int((good.sum(-1)>=14).sum()),
                task_exact_correct=int(good.all(-1).sum()),task_bit_correct=int(good.sum()),task_bits=128,
                hidden_distinct=int(len(np.unique(z,axis=0))),hidden_absolute_overlap=float(np.abs(z@z.T)[np.triu_indices(8,1)].mean()/40)))
    return dict(cases=rows,suppliers=supplier,stability=static)

def independent_scores(raw,tape,rows):
    assert len(rows['cases'])==352 and len(rows['stability'])==176 and len(rows['suppliers'])==4
    for row in rows['cases']:
        b=m.BRANCHES.index(row['branch']);i=m.INJURIES.index(row['injury']);u=m.BIRTHS.index(row['birth'])
        d,f,r=(row[k] for k in ('draw','founder','recipient'));x=raw['assessments'][b,i,u,d,f,r];ref=raw['reference'][b,f,r]
        task=[];outputs=[];free=[]
        for q in range(8):
            task.append(sum(int(x[q,j])==int(tape['targets'][f,q,j-48]) for j in range(48,64)))
            outputs.append(sum(int(x[q,j])==int(ref[q,j]) for j in range(48,64)))
            free.append(sum(int(x[q,j])==int(ref[q,j]) for j in range(8,64)))
        expected=dict(queries=8,tasks=1,task_bits=128,free_bits=448,task_query_correct=sum(v>=14 for v in task),
            task_exact_correct=task.count(16),task_complete=int(all(v>=14 for v in task)),task_bit_correct=sum(task),
            captured_output_exact=outputs.count(16),captured_free_exact=free.count(56),captured_output_bits=sum(outputs),captured_free_bits=sum(free))
        for key,value in expected.items():assert row[key]==value,(key,row)
    for row in rows['stability']:
        b=m.BRANCHES.index(row['branch']);i=m.INJURIES.index(row['injury']);d,f,r=(row[k] for k in ('draw','founder','recipient'))
        h=raw['static_fields'][b,i,d,f,r];ref=raw['reference'][b,f,r];counts=[];outs=[]
        for q in range(8):
            flags=[]
            for j in range(8,64):
                value=1 if h[q,j]>1e-12 else -1 if h[q,j]<-1e-12 else int(ref[q,j])
                flags.append(value==int(ref[q,j]))
            counts.append(sum(flags));outs.append(sum(flags[40:]))
        assert row['stable_free']==counts.count(56) and row['stable_output']==outs.count(16) and row['stable_free_bits']==sum(counts)
    for row in rows['suppliers']:
        f,r=row['founder'],row['recipient'];x=raw['supplier_final'][f,r]
        counts=[sum(int(x[q,j])==int(tape['targets'][f,q,j-48]) for j in range(48,64)) for q in range(8)]
        assert row['task_query_correct']==sum(v>=14 for v in counts) and row['task_exact_correct']==counts.count(16)
        assert row['task_bit_correct']==sum(counts)
        distinct={tuple(map(int,x[q,8:48])) for q in range(8)};assert row['hidden_distinct']==len(distinct)
        overlap=sum(abs(sum(int(x[a,j])*int(x[b,j]) for j in range(8,48))) for a in range(8) for b in range(a+1,8))/(28*40)
        assert abs(row['hidden_absolute_overlap']-overlap)<1e-15
    return sum(len(v) for v in rows.values())
