"""Matched endpoints, actual supplying-body diagnostics and individual reversals."""
import numpy as np
from h103 import model as m

def flags(raw,tape):
    observed=raw['assessments'][...,48:]
    target=tape['targets'][None,None,None,None,:,None,:,:]
    bits=observed==target;hits=bits.sum(-1);query=hits>=14
    return dict(bit=bits,query=query,exact=hits==16,task=query.all(-1))
def network(raw,tape,variants,block):
    f=flags(raw,tape);cases=[];effects=[];mechanism=[];transitions=[];u=variants.index('unchanged')
    for g in range(5):
        for vi,variant in enumerate(variants):
            for ci,route in enumerate(m.ROUTES):
                for d in range(2):
                    for founder in range(2):
                        for lineage in range(2):
                            idx=(g,vi,ci,d,founder,lineage)
                            cases.append(dict(block=block,variant=variant,route=route,g=g,draw=d,founder=founder,lineage=lineage,
                                query_correct=int(f['query'][idx].sum()),queries=8,exact_correct=int(f['exact'][idx].sum()),
                                task_correct=int(f['task'][idx]),tasks=1,bit_correct=int(f['bit'][idx].sum()),bits=128))
                if vi!=u:
                    values={}
                    for unit in ('query','exact','task','bit'):
                        a,b=f[unit][g,vi,ci],f[unit][g,u,ci]
                        values[unit+'_gains']=int(np.count_nonzero(a&~b));values[unit+'_losses']=int(np.count_nonzero(~a&b))
                    effects.append(dict(block=block,variant=variant,route=route,g=g,**values))
                for founder in range(2):
                    for lineage in range(2):
                        record=raw['records'][g,vi,ci,founder,lineage];original=raw['initial_record'][founder]
                        current=raw['records'][g,u,ci,founder,lineage];degrees=np.count_nonzero(record,axis=1)
                        entry=dict(block=block,variant=variant,route=route,g=g,founder=founder,lineage=lineage,
                            nonzero_edges=int(np.count_nonzero(record)//2),record_isolated_cells=int((degrees==0).sum()),
                            newly_record_isolated_cells=int(((degrees==0)&np.any(original!=0,axis=1)).sum()),
                            norm=float(np.linalg.norm(record)),absolute_mass=float(np.abs(record).sum()/2),
                            distance_from_unchanged=float(np.linalg.norm(record-current)),exact_same_record=int(np.array_equal(record,current)))
                        if g<4:
                            body=raw['supplying_bodies'][g,vi,ci,founder,lineage];integer=body.astype(int)
                            w=m.effective(tape['base'],record,tape['writer_mask'][g,founder,lineage])
                            entry.update(supplying_body_isolated_cells=int((np.abs(w).sum(-1)<=1e-12).sum()),
                                constant_hidden_cells=int((np.abs(integer[:,8:48].sum(0))==8).sum()),
                                distinct_hidden_patterns=int(len(np.unique(body[:,8:48],axis=0))),
                                mean_hidden_pattern_similarity=float(np.abs(integer[:,8:48]@integer[:,8:48].T)[np.triu_indices(8,1)].mean()/40),
                                writer_query_correct=int(((body[:,48:]==tape['targets'][founder]).sum(-1)>=14).sum()),
                                writer_bits_different_from_unchanged=int(np.count_nonzero(body!=raw['supplying_bodies'][g,u,ci,founder,lineage])))
                        else:entry.update(supplying_body_isolated_cells=-1,constant_hidden_cells=-1,distinct_hidden_patterns=-1,
                            mean_hidden_pattern_similarity=-1.,writer_query_correct=-1,writer_bits_different_from_unchanged=-1)
                        mechanism.append(entry)
                if vi!=u and g:
                    for unit in ('query','task'):
                        immediate=f[unit][0,vi,ci].astype(int)-f[unit][0,u,ci].astype(int)
                        later=f[unit][g,vi,ci].astype(int)-f[unit][g,u,ci].astype(int)
                        for a in (-1,0,1):
                            for b in (-1,0,1):
                                transitions.append(dict(block=block,variant=variant,route=route,g=g,unit=unit,immediate_effect=a,later_effect=b,
                                    cases=int(np.count_nonzero((immediate==a)&(later==b)))))
    return dict(cases=cases,effects=effects,mechanism=mechanism,transitions=transitions)
def independent_scores(raw,tape,variants,rows):
    count=0
    for r in rows['cases']:
        state=raw['assessments'][r['g'],variants.index(r['variant']),m.ROUTES.index(r['route']),r['draw'],r['founder'],r['lineage'],:,48:]
        hits=[sum(int(a)==int(b) for a,b in zip(x,y)) for x,y in zip(state,tape['targets'][r['founder']])]
        assert r['query_correct']==sum(h>=14 for h in hits) and r['exact_correct']==sum(h==16 for h in hits)
        assert r['task_correct']==int(all(h>=14 for h in hits)) and r['bit_correct']==sum(hits);count+=1
    f=flags(raw,tape);u=variants.index('unchanged')
    for r in rows['effects']:
        v,c,g=variants.index(r['variant']),m.ROUTES.index(r['route']),r['g']
        for unit in ('task','query','exact','bit'):
            pairs=list(zip(f[unit][g,v,c].flat,f[unit][g,u,c].flat))
            assert r[unit+'_gains']==sum(bool(a) and not bool(b) for a,b in pairs)
            assert r[unit+'_losses']==sum(not bool(a) and bool(b) for a,b in pairs)
        count+=1
    for r in rows['transitions']:
        v,c,g=variants.index(r['variant']),m.ROUTES.index(r['route']),r['g'];x=f[r['unit']]
        pairs=zip(x[0,v,c].flat,x[0,u,c].flat,x[g,v,c].flat,x[g,u,c].flat)
        assert r['cases']==sum(int(a)-int(b)==r['immediate_effect'] and int(z)-int(w)==r['later_effect'] for a,b,z,w in pairs);count+=1
    return count
