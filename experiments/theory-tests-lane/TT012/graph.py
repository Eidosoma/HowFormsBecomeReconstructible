"""Independent binary elimination and union-find parity checks."""
import itertools
from collections import Counter
import numpy as np
import support as s


def edges(side=16):
    return [(y*side+x, y*side+(x+1)%side) for y in range(side) for x in range(side)]+[
            (y*side+x, ((y+1)%side)*side+x) for y in range(side) for x in range(side)]


PINS=sorted(16*y+x for y0,x0 in [(7,1),(3,10),(11,10)] for y in range(y0,y0+2) for x in range(x0,x0+2))


def equations(pairs,rhs,pins=()):
    return [(1<<int(u))^(1<<int(v)) for u,v in pairs]+[1<<int(p) for p in pins],list(map(int,rhs))+[0]*len(pins)


def eliminate(n,rows,values):
    basis={};witness=[]
    for j,(r,b) in enumerate(zip(rows,values,strict=True)):
        r=int(r);b=int(b);proof=1<<j
        s.require(0<=r<1<<n and b in (0,1),'Binary equation')
        while r:
            p=(r&-r).bit_length()-1
            if p not in basis:
                basis[p]=(r,b,proof);break
            q,c,certificate=basis[p];r^=q;b^=c;proof^=certificate
        if not r and b and not witness:witness=[i for i in range(len(rows)) if proof>>i&1]
    def backsolve(free,homogeneous):
        answer=free
        for p,(r,b,_) in sorted(basis.items(),reverse=True):
            if ((r&answer).bit_count()&1)^(0 if homogeneous else b):answer^=1<<p
        return answer
    return dict(ok=not witness,rank=len(basis),witness=witness,
                solution=backsolve(0,False) if not witness else None,
                kernel=[backsolve(1<<i,True) for i in range(n) if i not in basis])


def union_find(n,pairs,rhs,pins=()):
    # Separate parity union-find; no elimination or source solver is called.
    parent=list(range(n+1));depth=[0]*(n+1);parity=[0]*(n+1);joins=0;ok=True
    def find(v):
        sign=0
        while parent[v]!=v:sign^=parity[v];v=parent[v]
        return v,sign
    for (u,v),b in list(zip(pairs,rhs,strict=True))+[((n,p),0) for p in pins]:
        ru,pu=find(u);rv,pv=find(v)
        if ru==rv:ok=ok and (pu^pv)==int(b);continue
        if depth[ru]>depth[rv]:ru,rv=rv,ru
        parent[ru]=rv;parity[ru]=pu^pv^int(b);joins+=1
        if depth[ru]==depth[rv]:depth[rv]+=1
    return dict(ok=ok,rank=joins)


def certificate(rows,rhs,indices,ok=False):
    if ok:s.require(not indices,'Feasible system has empty certificate');return
    s.require(bool(indices) and len(indices)==len(set(indices)),'Unique nonempty certificate')
    a=b=0
    for i in indices:
        s.require(type(i) is int and 0<=i<len(rows),'Certificate equation index')
        a^=rows[i];b^=rhs[i]
    s.require(a==0 and b==1,'Contradiction certificate equals 0=1')


def ambiguity(n,pairs,keep,backup,overlap,pins):
    # Dimension of backup changes modulo allowed whole-hybrid node switches.
    alignment_rows,_=equations([p for p,k in zip(pairs,overlap) if k],[0]*sum(overlap),pins)
    kernel=eliminate(n,alignment_rows,[0]*len(alignment_rows))['kernel']
    support=[(pair,is_backup) for pair,k,is_backup in zip(pairs,keep,backup) if k or is_backup]
    def image(bits,backup_only):
        answer=0
        for i,((u,v),is_backup) in enumerate(support):
            if (not backup_only or is_backup) and ((bits>>u)^(bits>>v))&1:answer^=1<<i
        return answer
    gauges=[image(1<<node,False) for node in range(n) if node not in pins]
    changes=[image(bits,True) for bits in kernel]
    rank=lambda rows:eliminate(len(support),rows,[0]*len(rows))['rank']
    return rank(gauges+changes)-rank(gauges)


def run(data,output):
    root=s.HERE/'source/alignment/results';rows=s.table(root/'cases.csv')
    certs={r['key']:r for r in s.read(root/'certificates.json')};pairs=edges();seen=set();receipts=[];old_order_rejections=0
    totals={g:dict(pairs=0,unpinned_ok=0,pinned_ok=0,obstructions=Counter(),free_bit_counts={},ambiguity_dimensions={},
                  own_equivalent=0,outgoing_balanced=0,donor_balanced=0,incoming_balanced=0) for g in ['all','same_task','opposite_task']}
    for row in rows:
        block,case=int(row['block']),int(row['case']);d=data[block]
        donor_index=['same_task','opposite_task'].index(row['donor']);key=f'b{block}_c{case}_d{donor_index}'
        s.require(key not in seen and key in certs,'Unique alignment pair');seen.add(key)
        w=np.frombuffer(d['packets'][case,1].tobytes(),'<f8');donor=np.frombuffer(d['donor_packets'][case,donor_index].tobytes(),'<f8')
        overlap=[i for i in range(512) if w[i]!=0 and donor[i]!=0]
        s.require(overlap==certs[key]['overlap_indices'],'Exact overlap order')
        selected=[pairs[i] for i in overlap];rhs=[int((w[i]<0)!=(donor[i]<0)) for i in overlap]
        for field,array in [('history','histories'),('founder','founders'),('recipient','recipients')]:
            s.require(int(row[field])==int(d[array][case]),'Alignment metadata '+field)
        for field,value in [('overlap_edges',len(overlap)),('kept_edges',int(np.count_nonzero(w))),('common_edges',int(d['common_edges'][case].sum()))]:
            s.require(int(row[field])==value,'Alignment edge count')
        solutions={}
        for label,pins in [('unpinned',[]),('pinned',PINS)]:
            matrix,values=equations(selected,rhs,pins);sol=eliminate(256,matrix,values);uf=union_find(256,selected,rhs,pins)
            s.require(sol['ok']==uf['ok'] and sol['rank']==uf['rank'],'Independent solvers agree')
            s.require(str(sol['ok'])==row[label+'_ok'],'Published feasibility')
            certificate(matrix,values,certs[key][label+'_witness'],sol['ok'])
            if not sol['ok']:certificate(matrix,values,sol['witness'])
            solutions[label]=sol
        plain,fixed=solutions['unpinned'],solutions['pinned']
        old_pins=[16*y+x for y0,x0 in [(7,1),(3,10),(11,10)] for y in range(y0,y0+2) for x in range(x0,x0+2)]
        wrong_rows,wrong_values=equations(selected,rhs,old_pins)
        try:certificate(wrong_rows,wrong_values,certs[key]['pinned_witness'],fixed['ok'])
        except ValueError:old_order_rejections+=1
        s.require(int(row['unpinned_free_bits'])==256-plain['rank'],'Coefficient nullity retained, not a feasible alignment count')
        reason='none' if fixed['ok'] else 'port' if plain['ok'] else 'cycle'
        s.require(row['obstruction']==reason,'Obstruction classification')
        # Source reports no admissible cases. A discrepancy stops this audit;
        # it must be reviewed instead of silently adapting the branch to outcomes.
        s.require(not fixed['ok'],'Unexpected admissible source pair needs discrepancy review')
        s.require(all(row[k]=='' for k in ['pinned_free_bits','ambiguity_dimension','own_equivalent']),'Infeasible quantities are undefined')
        balance={}
        for label,values in [('outgoing',w),('donor',donor),('incoming',np.frombuffer(d['packets'][case,0].tobytes(),'<f8'))]:
            ids=[i for i in range(512) if values[i]!=0];matrix,signs=equations([pairs[i] for i in ids],[int(values[i]<0) for i in ids])
            balance[label]=eliminate(256,matrix,signs)['ok'];s.require(str(balance[label])==row[label+'_balanced'],'Balance check')
        for group in ['all',row['donor']]:
            total=totals[group];total['pairs']+=1;total['unpinned_ok']+=plain['ok'];total['pinned_ok']+=fixed['ok'];total['obstructions'][reason]+=1
            for label,value in balance.items():total[label+'_balanced']+=value
        receipts.append(dict(key=key,overlap_edges=len(overlap),coefficient_rank=plain['rank'],unpinned_feasible=plain['ok'],
                             pinned_feasible=fixed['ok'],published_certificates_checked=2,independent_unpinned_witness=plain['witness']))
    expected={f'b{b}_c{i}_d{j}' for b,d in data.items() for i in range(len(d['founders'])) for j in [0,1]}
    s.require(seen==set(certs)==expected and len(seen)==128,'Every recipient donor pair')
    source=s.read(root/'analysis.json')
    for group in totals:s.require(source[group]==totals[group],'Alignment group summary')
    comparisons=s.read(root/'donor_comparisons.json')
    s.require(len(comparisons)==64 and {(r['block'],r['case']) for r in comparisons}=={(b,i) for b,d in data.items() for i in range(len(d['founders']))},'Every donor comparison')
    s.require(all(r['both_admissible'] is False and r['aligned_donors_equivalent'] is None for r in comparisons),'No admissible donor comparison')
    s.require(not s.arrays(root/'alignments.npz'),'No unearned saved alignment')
    s.require(source['cases']==64 and source['both_donors_admissible']==source['aligned_donors_equivalent']==source['new_task_outcomes']==0,'Alignment totals')
    for b in data:s.require(source['source_arrays_sha256'][f'cases_{b:06d}.npz']==s.sha(s.HERE/f'source/p05/inputs/prepared/cases_{b:06d}.npz'),'Alignment source identity')
    s.dump(output/'pair_certificates.json',receipts)
    result=dict(status='PASS',pairs=128,published_certificates_checked=256,independent_contradictions=128,
                unpinned_feasible=0,pinned_feasible=0,groups=totals,ambiguous_or_unique_alignment_dimensions='NOT_APPLICABLE_INFEASIBLE',
                source_verifier_pin_order_failure_preserved=True,certificates_rejected_with_old_pin_order=old_order_rejections,new_task_outcomes=0)
    s.require(old_order_rejections>0,'Original verifier pin-order failure reproduced')
    s.dump(output/'ALIGNMENT_AUDIT.json',result);return result


def fixtures():
    checked=0
    for labels in itertools.product([-1,0,1],repeat=3):
        pairs=[p for p,k in zip([(0,1),(1,2),(0,2)],labels) if k]
        rhs=[int(k<0) for k in labels if k]
        for pinned in range(8):
            pins=[i for i in range(3) if pinned>>i&1];rows,values=equations(pairs,rhs,pins)
            truth=[x for x in range(8) if all((r&x).bit_count()%2==v for r,v in zip(rows,values))]
            a=eliminate(3,rows,values);b=union_find(3,pairs,rhs,pins)
            s.require(a['ok']==b['ok']==bool(truth) and a['rank']==b['rank'],'Exhaustive small graph')
            if truth:s.require(a['solution'] in truth and len(truth)==2**(3-a['rank']),'Solution and nullity')
            else:certificate(rows,values,a['witness'])
            checked+=1
    # Exhaustive quotient classification: absent, kept nonoverlap, overlap, backup.
    pairs=[(0,1),(1,2),(0,2)];quotients=0
    for labels in itertools.product(range(4),repeat=3):
        keep=[k in [1,2] for k in labels];backup=[k==3 for k in labels];overlap=[k==2 for k in labels]
        for pinned in range(8):
            pins=[i for i in range(3) if pinned>>i&1]
            assignments=[x for x in range(8) if not any(x>>p&1 for p in pins)]
            support=[(p,b) for p,k,b in zip(pairs,keep,backup) if k or b]
            edge_image=lambda x,restricted:sum((((x>>u)^(x>>v))&1)<<i for i,((u,v),b) in enumerate(support) if not restricted or b)
            gauge={edge_image(x,False) for x in assignments}
            candidates={edge_image(x,True) for x in assignments if all(not ((x>>u)^(x>>v))&1 for (u,v),on in zip(pairs,overlap) if on)}
            classes={min(v^g for g in gauge) for v in candidates}
            s.require(2**ambiguity(3,pairs,keep,backup,overlap,pins)==len(classes),'Exhaustive observable quotient')
            quotients+=1
    rows,values=equations([(0,1)],[1],[0,1]);certificate(rows,values,[0,1,2])
    rejected=0
    for bad in [[],[0,0,1,2],[99],[0,1]]:
        try:certificate(rows,values,bad)
        except ValueError:rejected+=1
    s.require(rejected==4,'Corrupted certificate rejection')
    return dict(parity_systems=checked,exhaustive_quotient_systems=quotients,corruption_rejections=rejected)
