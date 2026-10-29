"""Fixed-pattern probes on the actual constrained record; no projector-floor claim."""
import numpy as np
from h083.audit import Audit
from h093 import dynamics,reference
from h097 import model as m

def extract(raw,graph):
    ids=[];packets=[];states=[];fields=[];fixed=[];energies=[];check=Audit();cache={}
    for node in graph['records']:
        if node['kind']!='neural' or node['operation']=='erase':continue
        ancestor=node
        while ancestor['packet_index']<0:ancestor=graph['records'][ancestor['parent_record']]
        pi=ancestor['packet_index'];record=m.get_record(raw,graph,node['id'])
        patterns=np.stack([np.concatenate((m.X,y),axis=1) for y in (raw['completion_outputs'][pi],raw['responses_'+node['origin']])])
        key=(m.digest(record),patterns.tobytes())
        if key not in cache:
            ref={k:v.astype(np.longdouble) if k!='interaction_masks' else v for k,v in record.items()}
            h=dynamics.fields(record,patterns);eh=reference.fields(ref,patterns)
            check.same(h,eh,'independent learned and true pattern fields',2e-11)
            e=dynamics.energy(record,patterns);ee=reference.energy(ref,patterns)
            check.same(e,ee,'actual constrained-pattern energy',2e-11)
            expected=check.decide(eh,patterns)==patterns
            actual=np.where(h>dynamics.base.TOL,1,np.where(h < -dynamics.base.TOL,-1,patterns))==patterns
            check.same(actual,expected,'independent constrained-pattern fixedness')
            cache[key]=(h,actual,e)
        h,f,e=cache[key];ids.append(node['id']);packets.append(pi);states.append(patterns);fields.append(h);fixed.append(f);energies.append(e)
    assert len(ids)==162
    return dict(record_ids=np.asarray(ids,dtype=np.int64),source_packets=np.asarray(packets,dtype=np.int64),
        states=np.stack(states),fields=np.stack(fields),fixed=np.stack(fixed),energies=np.stack(energies)),dict(checks=check.count,minimum_boundary_distance=check.boundary_minimum)


def tables(raw,graph,bundle,block,literal=False):
    count=lambda a:sum(bool(v) for v in np.asarray(a).flat) if literal else int(np.count_nonzero(a))
    rows=[]
    for i,rid in enumerate(bundle['record_ids']):
        node=graph['records'][int(rid)];fields=bundle['fields'][i];states=bundle['states'][i];fixed=bundle['fixed'][i]
        for j,name in enumerate(('learned','true')):
            for panel,queries in m.PANELS.items():
                f=fixed[j,queries];margin=states[j,queries]*fields[j,queries]
                row={k:node[k] for k in ('origin','scope','route','policy','generation','birth')}
                row.update(block=block,record_id=int(rid),packet_index=int(bundle['source_packets'][i]),pattern_set=name,panel=panel,
                    patterns=8,full_fixed=count(f.all(-1)),context_fixed=count(f[:,:32].all(-1)),
                    response_fixed=count(f[:,80:].all(-1)),query_conditional_fixed=count(f[:,np.r_[0:32,80:128]].all(-1)),
                    unstable_coordinates=count(~f),minimum_signed_field=float(min(margin.flat)))
                rows.append(row)
    assert len(rows)==648;return rows


def verify(raw,graph,bundle):
    """Rebuild retained diagnostic arrays with independent long-double fields."""
    check=Audit()
    assert bundle['states'].shape==bundle['fields'].shape==bundle['fixed'].shape==(162,2,16,128)
    for i,rid in enumerate(bundle['record_ids']):
        node=graph['records'][int(rid)];record=m.get_record(raw,graph,int(rid));ref={k:v.astype(np.longdouble) if k!='interaction_masks' else v for k,v in record.items()}
        ancestor=node
        while ancestor['packet_index']<0:ancestor=graph['records'][ancestor['parent_record']]
        assert int(bundle['source_packets'][i])==ancestor['packet_index']
        wanted=np.stack([np.concatenate((m.X,y),axis=1) for y in (raw['completion_outputs'][ancestor['packet_index']],raw['responses_'+node['origin']])])
        check.same(bundle['states'][i],wanted,'retained learned and true patterns')
        h=reference.fields(ref,wanted);check.same(bundle['fields'][i],h,'reloaded independent pattern fields',2e-11)
        check.same(bundle['fixed'][i],check.decide(h,wanted)==wanted,'reloaded independent pattern fixedness')
        check.same(bundle['energies'][i],reference.energy(ref,wanted),'reloaded independent pattern energies',2e-11)
    return check.count
