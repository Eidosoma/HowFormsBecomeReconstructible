"""Fixed32 successor and fixed8 direct reads, with two disjoint repeats."""
import hashlib
import resource
import time

import numpy as np

from bridge import P, e, audit, ev
import probes


def measure(packet, rule, key, regime, stage, output, deadline, indices=None):
    indices=list(range(64)) if indices is None else list(indices)
    if not indices or len(indices)!=len(set(indices)) or any(j<0 or j>=64 for j in indices):
        raise ValueError('Distinct indices within the two frozen32-probe repeats required')
    original=packet.copy();start=time.monotonic();cpu=time.process_time()
    names=('mask','birth','end','windows','outgoing')
    data={f'{branch}_{name}':[] for branch in ('writer','successor','direct') for name in names}
    direct_indices=[];forcing=[];audits=[]
    # Groups never mix a direct-control index with a successor-only index.
    batches=[]
    for j in indices:
        direct=j%32<8
        if not batches or len(batches[-1])==4 or (batches[-1][0]%32<8)!=direct:
            batches.append([])
        batches[-1].append(j)
    for batch in batches:
        deadline.check()
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>P['resources']['maximum_resident_bytes']:
            raise MemoryError('Frozen memory ceiling')
        wa=[probes.environment(stage,key,j,'writer',regime) for j in batch]
        eb=[probes.environment(stage,key,j,'evaluation',regime) for j in batch]
        first=probes.read_batch(np.repeat(packet[None,None],len(batch),axis=0),wa)
        direct=batch[0]%32<8
        incoming=np.stack([np.stack([packet,w[0]]) if direct else w for w in first['outgoing']])
        second=probes.read_batch(incoming,eb)
        for local,index in enumerate(batch):
            writer={k:v[local] for k,v in first.items()};evaluation={k:v[local] for k,v in second.items()}
            if index in (0,32):
                flat=audit.read_write(packet[None],*wa[local],P['reader'],P['writer']['beta'])
                probes.compare(writer,flat)
                flat_input=np.stack([packet,flat['outgoing'][0]])
                flat_eval=audit.read_write(flat_input,*eb[local],P['reader'],P['writer']['beta'])
                probes.compare(evaluation,flat_eval)
                audits.append(dict(probe=index,flat_native_reads=3,byte_exact=True))
            sources=[('writer',wa[local],writer),('successor',eb[local],{k:v[-1:] for k,v in evaluation.items()})]
            if direct:
                direct_indices.append(index)
                sources.append(('direct',eb[local],{k:v[:1] for k,v in evaluation.items()}))
            for branch,environment,value in sources:
                data[branch+'_mask'].append(environment[0]);data[branch+'_birth'].append(environment[1])
                for name in ('end','windows','outgoing'):
                    # Native windows are frames x branches x cues x ports.
                    data[branch+'_'+name].append(value[name] if branch=='writer' or name!='windows'
                        else evaluation[name][:,-1:] if branch=='successor' else evaluation[name][:,:1])
            forcing.append(dict(probe=index,purposes={purpose:{name:hashlib.sha256(a.tobytes()).hexdigest()
                for name,a in zip(('mask','birth','noise'),environment)}
                for purpose,environment in [('writer',wa[local]),('evaluation',eb[local])]}))
        if not np.array_equal(original,packet):raise ArithmeticError('Protected original changed')
    arrays={k:np.stack(v) for k,v in data.items()}
    arrays.update(packet=packet.copy(),probes=np.array(indices,np.int64),direct_probes=np.array(direct_indices,np.int64))
    for branch in ('writer','successor','direct'):
        aligned,margins,passed=probes.task(arrays[branch+'_windows'],rule)
        arrays.update({branch+'_aligned':aligned,branch+'_margins':margins,branch+'_passed':passed})
    digest=ev.save(output.with_suffix('.npz'),arrays)
    receipt=dict(key=key,rule=rule,regime=regime,stage=stage,raw_sha256=digest,
        forcing=forcing,audits=audits,native_reads=2*len(indices)+len(direct_indices),
        flat_native_reads=3*len(audits),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,
        new_future_outcomes=0)
    ev.write(output.with_suffix('.json'),receipt)
    return arrays,receipt
