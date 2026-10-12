"""Check every saved pair with independent GF(2) elimination and raw array logic."""
import csv
import numpy as np
from common import ROOT, arrays, read, sha, stamp, write
from gf2 import ambiguity_rank, constraint_rows, eliminate


def decode(packet):
    return np.frombuffer(packet.tobytes(),dtype='<f8').reshape(2,16,16)


def endpoints():
    u=[];v=[]
    for axis in (0,1):
        for y in range(16):
            for x in range(16):
                u.append(16*y+x)
                v.append(16*y+(x+1)%16 if axis==0 else 16*((y+1)%16)+x)
    return np.array(u),np.array(v)


def pins():
    return [16*y+x for y0,x0 in ((7,1),(3,10),(11,10))
            for y in range(y0,y0+2) for x in range(x0,x0+2)]


def equivalence(a,b,u,v,port_cells):
    assert np.array_equal(abs(a),abs(b))
    support = a.ravel()!=0
    coefficients = constraint_rows(u[support],v[support],port_cells)
    rhs = list((a.ravel()[support]<0)^(b.ravel()[support]<0))+[0]*len(port_cells)
    return eliminate(256,coefficients,rhs)['ok']


def certificate(n,u,v,rhs,port_cells,indices,ok):
    if ok:
        assert not indices
        return
    coefficients = constraint_rows(u,v,port_cells)
    values = list(rhs)+[0]*len(port_cells)
    row=0;value=0
    assert len(indices)==len(set(indices)) and indices
    for index in indices:
        row ^= coefficients[index]; value ^= int(values[index])
    assert row==0 and value==1


def run():
    result=ROOT/'results_v1'
    before=read(result/'START.json')
    for name,digest in before['files_sha256'].items():
        assert sha(ROOT/name)==digest,(name,'changed after audit start')
    binding=read(ROOT/'SOURCE_BINDINGS.json')['bindings']['inputs/prepared/COMPLETE.json']
    source=__import__('pathlib').Path(binding['source']).parent
    assert sha(source/'COMPLETE.json')==binding['sha256']
    receipt=read(source/'COMPLETE.json')
    with (result/'cases.csv').open() as f:rows=list(csv.DictReader(f))
    certs={r['key']:r for r in read(result/'certificates.json')}
    comparisons=read(result/'donor_comparisons.json')
    saved=arrays(result/'alignments.npz')
    u,v=endpoints(); port_cells=pins(); panel={}
    checked=0;accepted=0;paired=0;equivalent_pairs=0
    counts={name:dict(pairs=0,unpinned_ok=0,pinned_ok=0,own_equivalent=0,
                     outgoing_balanced=0,donor_balanced=0,incoming_balanced=0,
                     obstructions={},free_bit_counts={},ambiguity_dimensions={})
            for name in ('all','same_task','opposite_task')}
    for row in rows:
        block,case=int(row['block']),int(row['case'])
        if block not in panel:
            name=f'cases_{block:06d}.npz'
            panel[block]=arrays(source/name,receipt['outputs_sha256'][name])
        data=panel[block]
        d=0 if row['donor']=='same_task' else 1
        key=f'b{block}_c{case}_d{d}'
        outgoing=decode(data['packets'][case,1]); donor=decode(data['donor_packets'][case,d])
        overlap=(outgoing.ravel()!=0)&(donor.ravel()!=0)
        rhs=(outgoing.ravel()[overlap]<0)^(donor.ravel()[overlap]<0)
        assert np.array_equal(np.flatnonzero(overlap),certs[key]['overlap_indices'])
        plain=eliminate(256,constraint_rows(u[overlap],v[overlap]),rhs)
        fixed=eliminate(256,constraint_rows(u[overlap],v[overlap],port_cells),list(rhs)+[0]*12)
        assert plain['ok']==(row['unpinned_ok']=='True')
        assert fixed['ok']==(row['pinned_ok']=='True')
        assert 256-plain['rank']==int(row['unpinned_free_bits'])
        for label,sol,port in (('unpinned',plain,[]),('pinned',fixed,port_cells)):
            certificate(256,u[overlap],v[overlap],rhs,port,certs[key][label+'_witness'],sol['ok'])
        reason='none' if fixed['ok'] else ('port' if plain['ok'] else 'cycle')
        assert row['obstruction']==reason
        incoming=decode(data['packets'][case,0]); own=decode(data['packets'][case,3])
        balanced={}
        for label,w in (('outgoing',outgoing),('donor',donor),('incoming',incoming)):
            support=w.ravel()!=0
            balanced[label]=eliminate(256,constraint_rows(u[support],v[support]),w.ravel()[support]<0)['ok']
            assert balanced[label]==(row[label+'_balanced']=='True')
        if fixed['ok']:
            free=256-fixed['rank']
            assert free==int(row['pinned_free_bits'])
            common=data['common_edges'][case]
            dimension=ambiguity_rank(256,u,v,outgoing.ravel()!=0,common.ravel(),overlap,port_cells)
            assert dimension==int(row['ambiguity_dimension'])
            bits=saved[key+'_alignment']
            assert not bits[port_cells].any()
            assert np.array_equal(bits[u[overlap]]^bits[v[overlap]],rhs)
            h=outgoing.copy()
            sign=1-2*(bits[u].astype(int)^bits[v].astype(int))
            h[common]=abs(incoming[common])*np.where(donor[common]<0,-1,1)*sign.reshape(2,16,16)[common]
            assert np.array_equal(h,saved[key+'_hybrid'])
            own_ok=equivalence(h,own,u,v,port_cells)
            assert own_ok==(row['own_equivalent']=='True')
            accepted+=1
        for group in ('all',row['donor']):
            c=counts[group];c['pairs']+=1;c['unpinned_ok']+=plain['ok'];c['pinned_ok']+=fixed['ok']
            c['obstructions'][reason]=c['obstructions'].get(reason,0)+1
            for label,ok in balanced.items():c[label+'_balanced']+=ok
            if fixed['ok']:
                c['own_equivalent']+=own_ok
                for label,value in (('free_bit_counts',free),('ambiguity_dimensions',dimension)):
                    c[label][str(value)]=c[label].get(str(value),0)+1
        checked+=1
    for item in comparisons:
        keys=[f"b{item['block']}_c{item['case']}_d{d}_hybrid" for d in (0,1)]
        both=all(k in saved for k in keys)
        assert both==item['both_admissible']
        if both:
            ok=equivalence(saved[keys[0]],saved[keys[1]],u,v,port_cells)
            assert ok==item['aligned_donors_equivalent'];paired+=1;equivalent_pairs+=ok
        else:assert item['aligned_donors_equivalent'] is None
    summary=read(result/'analysis.json')
    for group,values in counts.items():assert summary[group]==values,(group,summary[group],values)
    assert checked==128 and len(comparisons)==summary['cases']==64
    assert paired==summary['both_donors_admissible'] and equivalent_pairs==summary['aligned_donors_equivalent']
    report=dict(status='PASS',at_utc=stamp(),pairs_checked=checked,admissible_checked=accepted,
        all_certificates_checked=True,all_ambiguity_ranks_checked=True,all_summaries_checked=True,
        method='Independent GF(2) elimination; no alignment or audit imports.',
        independent_institution=False,
        files_sha256={p.name:sha(p) for p in result.iterdir() if p.is_file()},
        code_sha256={n:sha(ROOT/n) for n in ('verify.py','gf2.py','common.py')})
    write(result/'VERIFICATION.json',report)
    print({k:v for k,v in report.items() if not k.endswith('sha256')})


if __name__=='__main__':
    run()
