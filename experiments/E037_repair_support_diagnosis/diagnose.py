"""E037: exploratory diagnosis of all saved E036 histories; no dynamics.
Execution may use stdout only while the experiment filesystem is full.
All scientific inputs are read-only. No scientific success criterion is introduced.
"""
import argparse, hashlib, io, json, os, sys, time
from pathlib import Path
import numpy as np
from common import cap_cpus, rng, sha, utc
from E015_functional_inheritance.audit import verify
from E032_renewal_failure_diagnosis import metrics as prior, audit as independent

CONDITIONS = ('standard_preserve','standard_rewrite','contrast_preserve','contrast_rewrite',
              'original_standard_preserve','contrast_read_blocked','contrast_write_blocked','protected_copy','masked_copy')
HORIZONS = (0,1,3,8,16)
GRAPH_CONDITIONS = (0,1,2,3,4,8)
REPAIR_FIELDS = ('available','returning','returning_nonzero','returning_strong','returning_abs_sum',
                'available_weak_nonzero','weak_promoted','weak_erased',
                'available_zero','zero_restored','zero_promoted','zero_abs_sum',
                'young_weak','young_promoted','young_erased','young_abs_before','young_abs_after')
RATIOS = {'returning_nonzero_rate':(2,1),'returning_strong_rate':(3,1),'returning_mean_abs':(4,1),
          'weak_promotion_rate':(6,5),'weak_erasure_rate':(7,5),
          'zero_restoration_rate':(9,8),'zero_promotion_rate':(10,8),'zero_mean_abs':(11,8),
          'young_promotion_rate':(13,12),'young_erasure_rate':(14,12),
          'young_mean_abs_before':(15,12),'young_mean_abs_after':(16,12)}
GRAPH_FIELDS = ('nonzero_output_fraction','nonzero_all_outputs','strong_output_fraction','strong_all_outputs')

def load(source, name, complete):
    path = source/name
    assert sha(path) == complete['outputs_sha256'][name], name
    with np.load(path, allow_pickle=False) as z: values = {k:z[k] for k in z.files}
    if '__index__' in values:
        meta = json.loads(values.pop('__index__').tobytes())
        assert meta['format'] in ('E031_compact_v1','E036_source_v1')
        assert set(values) == set(meta['retained'])
        for key,v in values.items():
            actual = dict(shape=list(v.shape),dtype=v.dtype.str,sha256=hashlib.sha256(v.tobytes(order='C')).hexdigest())
            assert actual == meta['arrays'][key], (name,key)
    assert all(np.isfinite(v).all() for v in values.values())
    return values

def repair(old,new,live,last_live,last_return):
    returning = live & ~last_live
    weak = live & (abs(old)>0) & (abs(old)<=.5)
    zero = live & (old==0)
    young = weak & last_return
    total = lambda a:a.sum(axis=(-3,-2,-1))
    values = (live,returning,returning&(new!=0),returning&(abs(new)>.5),returning*abs(new),
              weak,weak&(abs(new)>.5),weak&(new==0),
              zero,zero&(new!=0),zero&(abs(new)>.5),zero*abs(new),
              young,young&(abs(new)>.5),young&(new==0),young*abs(old),young*abs(new))
    return np.stack([total(x) for x in values],axis=-1).astype(float),returning

def repair_audit(old,new,live,last_live,last_return):
    rows=[]
    for i in np.ndindex(new.shape[:-3]):
        a,b,ok,previous,returned = [x[i].ravel() for x in (old,new,live,last_live,last_return)]
        returning=ok & ~previous
        weak=ok & (a!=0) & (abs(a)<=.5)
        zero=ok & (a==0)
        young=weak & returned
        count=np.count_nonzero
        rows.append([count(ok),count(returning),count(b[returning]),count(abs(b[returning])>.5),abs(b[returning]).sum(),
                     count(weak),count(abs(b[weak])>.5),count(b[weak]==0),
                     count(zero),count(b[zero]),count(abs(b[zero])>.5),abs(b[zero]).sum(),
                     count(young),count(abs(b[young])>.5),count(b[young]==0),abs(a[young]).sum(),abs(b[young]).sum()])
    return np.asarray(rows).reshape(*new.shape[:-3],len(REPAIR_FIELDS))

def graph(weights):
    results=[]
    for threshold in (0.,.5):
        support=(abs(weights)>threshold).astype(float)
        primary=prior.graph_features(support)
        np.testing.assert_array_equal(primary,independent.graph(support))
        results.append(primary)
    return np.concatenate(results,axis=-1)

def fixtures():
    old=np.zeros((1,2,16,16));new=old.copy();live=np.ones_like(old,bool)
    last_live=live.copy();last_return=np.zeros_like(live)
    old.flat[:6]=[0.,.01,.5,.7,-.01,0.]
    new.flat[:6]=[.001,.8,0.,.7,0.,.9]
    last_live.flat[0]=False;last_live.flat[5]=False
    last_return.flat[1]=True;last_return.flat[4]=True
    a,_=repair(old,new,live,last_live,last_return);b=repair_audit(old,new,live,last_live,last_return)
    np.testing.assert_allclose(a,b,rtol=1e-14,atol=1e-12)
    expected={'returning':2,'returning_nonzero':2,'returning_strong':1,'available_weak_nonzero':3,
              'weak_promoted':1,'weak_erased':2,'zero_restored':2,'zero_promoted':1,
              'young_weak':2,'young_promoted':1,'young_erased':1}
    for key,value in expected.items():assert a[0,REPAIR_FIELDS.index(key)]==value,key
    x=np.zeros((1,2,16,16));x[...,0,:,:]=1e-300;x[...,1,:,:]=.5
    np.testing.assert_array_equal(graph(x),[[1.,1.,0.,0.]])
    # The previous diagnostic independently checks cutoff, output-class and transition definitions.
    from E032_renewal_failure_diagnosis.tests import DiagnosticTests
    import unittest
    result=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromTestCase(DiagnosticTests))
    assert result.wasSuccessful()
    return dict(new_repair_fixture=True,nonzero_graph_fixture=True,prior_tests=result.testsRun)

def extract(source,block,complete):
    source_values=load(source,f'source_{block:06d}.npz',complete)
    first=load(source,f'boundary_{block:06d}_g1.npz',complete)
    R=first['outgoing'].shape[2]
    original=np.repeat(prior.decode(source_values['acquired'][1])[:,None],R,axis=1)
    old=np.repeat(original[None],9,axis=0)
    live=np.ones_like(old,bool);returned=np.zeros_like(live)
    packet=[prior.packet_features(old,old,original,live,True)]
    np.testing.assert_array_equal(packet[0],independent.record(old,old,original,live,True))
    graphs=[graph(old[list(GRAPH_CONDITIONS)])];repairs=[];bodies=[]
    for g in range(1,17):
        raw=first if g==1 else load(source,f'boundary_{block:06d}_g{g}.npz',complete)
        new=prior.decode(raw['outgoing'])
        last_live=live
        live=np.broadcast_to(prior.available(raw['renewal_mask']),new.shape).copy()
        live[7]=True
        # Independently check physical availability using endpoint indices.
        mask=raw['renewal_mask']
        for axis in (0,1):
            for y in range(16):
                for x in range(16):
                    yy,xx=(y,(x+1)%16) if axis==0 else ((y+1)%16,x)
                    np.testing.assert_array_equal(live[0,...,axis,y,x],~(mask[...,y,x]|mask[...,yy,xx]))
        f=prior.packet_features(old,new,original,live)
        np.testing.assert_array_equal(f,independent.record(old,new,original,live))
        r,new_return=repair(old,new,live,last_live,returned)
        np.testing.assert_allclose(r,repair_audit(old,new,live,last_live,returned),rtol=1e-14,atol=1e-12)
        np.testing.assert_array_equal(r[...,[0,1,2,3,5,6,7,8,9,10,12,13,14]],
                                      repair_audit(old,new,live,last_live,returned)[...,[0,1,2,3,5,6,7,8,9,10,12,13,14]])
        for c in (0,2,4):
            np.testing.assert_array_equal(raw['retained_edges'][c],live[c]&(abs(old[c])>.5))
            np.testing.assert_array_equal(raw['eligible_edges'][c],live[c]&(abs(old[c])<=.5))
            assert not f[c,...,[11,12]].any()
        b=prior.output_features(raw['developed_mean_ports'],prior.RULES[None,:,None])
        np.testing.assert_array_equal(b,independent.output(raw['developed_mean_ports'],prior.RULES[None,:,None]))
        packet.append(f);repairs.append(r);bodies.append(b)
        if g in HORIZONS:graphs.append(graph(new[list(GRAPH_CONDITIONS)]))
        old=new;returned=new_return
    bodies=np.stack(bodies)
    transitions=prior.transitions(bodies[...,0])
    np.testing.assert_array_equal(transitions,independent.history(bodies[...,0]))
    terminal=[]
    for h in HORIZONS:
        raw=load(source,f'assay_{block:06d}_h{h}.npz',complete)
        n=1 if h==0 else 9
        ports=raw['mean_ports'][n:,:,:,:,:,0,:].transpose(0,1,2,4,3,5)
        if h==0:ports=np.repeat(ports,9,axis=0)
        out=prior.output_features(ports,prior.RULES[None,:,None,None])
        np.testing.assert_array_equal(out,independent.output(ports,prior.RULES[None,:,None,None]))
        terminal.append(out)
    cases=load(source,f'cases_{block:06d}.npz',complete)
    np.testing.assert_array_equal(bodies[...,0],cases['body_correct'].all(axis=-1))
    np.testing.assert_array_equal(bodies[...,5],cases['body_margin'].min(axis=-1))
    return dict(packet=np.stack(packet),repair=np.stack(repairs),body=bodies,
                graph=np.stack(graphs),terminal=np.stack(terminal),transitions=transitions)

def summarize(all_data,ids,reference):
    draws=rng('E037','bootstrap','saved_repair').integers(0,len(ids),(10000,len(ids)))
    series={}
    def stat(key,n,d):
        assert key not in series
        nb,db=n[draws].sum(axis=1),d[draws].sum(axis=1);valid=db>0
        series[key]=dict(mean=float(n.sum()/d.sum()) if d.sum() else None,
                        ci95=np.quantile(nb[valid]/db[valid],[.025,.975]).tolist() if valid.any() else None,
                        block_numerators=n.tolist(),block_denominators=d.tolist())
    definitions={'packet':prior.PACKET_FIELDS,'repair':REPAIR_FIELDS,'body':prior.OUTPUT_FIELDS,
                 'terminal':prior.OUTPUT_FIELDS,'graph':GRAPH_FIELDS,'transitions':prior.TRANSITION_FIELDS}
    for kind,arr in all_data.items():
        fields=definitions[kind]
        policies=GRAPH_CONDITIONS if kind=='graph' else range(7) if kind in ('body','transitions') else range(9)
        for t in range(arr.shape[1]):
            g=HORIZONS[t] if kind in ('graph','terminal') else t if kind=='packet' else t+1
            for c,policy in enumerate(policies):
                for d in range(3) if kind=='terminal' else (None,):
                    x=arr[:,t,c,:,:,d,:] if d is not None else arr[:,t,c]
                    prefix=f'{kind}.g{g}.{CONDITIONS[policy]}.'+(('intact','scattered','square')[d]+'.' if d is not None else '')
                    for k,field in enumerate(fields):
                        n=x[...,k].sum(axis=(1,2));den=np.full(len(ids),x.shape[1]*x.shape[2])
                        stat(prefix+field,n,den)
                    if kind=='repair':
                        for field,(num,den) in RATIOS.items():
                            stat(prefix+field,x[...,num].sum(axis=(1,2)),x[...,den].sum(axis=(1,2)))
    for g in range(1,17):
        for c in CONDITIONS[:7]:
            assert series[f'body.g{g}.{c}.both_correct']['mean']==reference['body_reading'][str(g)][c]['both_cues']['mean']
    for g in HORIZONS:
        for c in CONDITIONS:
            for d in ('intact','scattered','square'):
                assert series[f'terminal.g{g}.{c}.{d}.both_correct']['mean']==reference['groups'][str(g)]['local_strength']['initial' if g==0 else c]['both_cues'][d]['own']['mean']

    # Independently reproduce every bootstrap interval from stored block totals,
    # with a separately constructed generator and transposed sample matrix.
    key=json.dumps(["E037","bootstrap","saved_repair"],separators=(",",":")).encode()
    check_draw=np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16],"little"))).integers(0,len(ids),(10000,len(ids))).T
    for value in series.values():
        n=np.array(value["block_numerators"],dtype=float)
        d=np.array(value["block_denominators"],dtype=float)
        counts=n[check_draw].sum(axis=0);den=d[check_draw].sum(axis=0);ok=den>0
        mean=float(np.sum(n)/np.sum(d)) if np.sum(d) else None
        bounds=np.percentile(counts[ok]/den[ok],[2.5,97.5]).tolist() if ok.any() else None
        assert mean==value["mean"]
        if bounds is None:assert value["ci95"] is None
        else:np.testing.assert_allclose(bounds,value["ci95"],rtol=1e-14,atol=1e-12)

    return series

def selected(series):
    result={}
    for c in CONDITIONS:
        result[c]={}
        for g in (1,3,4,5,6,7,8,12,16):
            row={}
            for kind,fields in [('packet',('nonzero','strong','physical_strong_lost','weak_promoted','changed_sign_nonzero')),
                                ('repair',tuple(RATIOS))]:
                for field in fields:row[kind+'.'+field]=series[f'{kind}.g{g}.{c}.{field}']['mean']
            if c in CONDITIONS[:7]:
                for field in prior.OUTPUT_FIELDS[:4]+('cue_amplitude_A','cue_amplitude_B'):
                    row['body.'+field]=series[f'body.g{g}.{c}.{field}']['mean']
            if g in HORIZONS:
                for field in prior.OUTPUT_FIELDS[:4]:
                    row['terminal.'+field]=series[f'terminal.g{g}.{c}.scattered.{field}']['mean']
                if CONDITIONS.index(c) in GRAPH_CONDITIONS:
                    for field in GRAPH_FIELDS:row['graph.'+field]=series[f'graph.g{g}.{c}.{field}']['mean']
            result[c][g]=row
    return result

def execute(mode,output=None):
    cap_cpus(8);started=time.monotonic()
    tests=fixtures()
    source=Path('E036_serial_cue_capture_v2/runs')/('fixture_v1' if mode=='benchmark' else 'serial_v1')
    complete=json.loads((source/'COMPLETE.json').read_text())
    manifest=verify(source)
    source_audit=json.loads((source/'INDEPENDENT_AUDIT.json').read_text())
    assert source_audit['status']=='PASS'
    ids=[900036] if mode=='benchmark' else list(range(28000,28032))
    reference=json.loads((source/'summary.json').read_text())
    assert reference['blocks']==ids
    data=[];extraction_start=time.monotonic()
    for block in ids:data.append(extract(source,block,complete))
    extraction_seconds=time.monotonic()-extraction_start
    all_data={key:np.stack([d[key] for d in data]) for key in data[0]}
    summary_start=time.monotonic()
    series=summarize(all_data,ids,reference)
    summary=dict(experiment='E037',status='TECHNICAL_ONLY' if mode=='benchmark' else 'EXPLORATORY_DIAGNOSIS_COMPLETE',
                 utc=utc(),mode=mode,blocks=ids,lineages=len(ids)*4*all_data['packet'].shape[4],no_new_trajectories=True,
                 causal_claim_established=False,conditions=CONDITIONS,graph_conditions=GRAPH_CONDITIONS,horizons=HORIZONS,
                 fields=dict(packet=prior.PACKET_FIELDS,repair=REPAIR_FIELDS,graph=GRAPH_FIELDS,body=prior.OUTPUT_FIELDS,
                             terminal=prior.OUTPUT_FIELDS,transitions=prior.TRANSITION_FIELDS),
                 repair_ratios=RATIOS,series=series,source_complete_sha256=sha(source/'COMPLETE.json'),
                 source_audit_sha256=sha(source/'INDEPENDENT_AUDIT.json'),source_inputs_sha256=manifest['inputs_sha256'],
                 validation=dict(fixtures=tests,source_hashes_verified=True,all_measurements_independently_checked=True,
                                 source_body_terminal_means_reproduced=True,all_bootstrap_intervals_recomputed=True),
                 extraction_and_measurement_verification_seconds=extraction_seconds,
                 summarization_seconds=time.monotonic()-summary_start)
    payload=json.dumps(summary,sort_keys=True,allow_nan=False).encode()
    estimates=dict(summary_bytes=len(payload),measurement_bytes=sum(a.nbytes for a in all_data.values()))
    if output is not None:
        output=Path(output);assert not output.exists();output.mkdir(parents=True)
        (output/'summary.json').write_bytes(payload+b'\n')
        for block,d in zip(ids,data):np.savez_compressed(output/f'measurements_{block:06d}.npz',**d)
        (output/'audit.json').write_text(json.dumps(summary['validation'],indent=2)+'\n')
    receipt=dict(mode=mode,status=summary['status'],seconds=time.monotonic()-started,
                 extraction_and_audit_seconds=extraction_seconds,summarization_seconds=summary['summarization_seconds'],
                 storage_estimates=estimates,summary_sha256=hashlib.sha256(payload).hexdigest(),
                 persisted=output is not None,validation=summary['validation'])
    if mode=='benchmark':
        receipt['forecast_seconds']=1.5*extraction_seconds*32*2+120
    print(json.dumps(receipt),flush=True)
    if mode=='scientific':print(json.dumps(selected(series),sort_keys=True),flush=True)
    return summary,all_data,receipt

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('benchmark','scientific'),required=True)
    parser.add_argument('--output')
    args=parser.parse_args()
    execute(args.mode,args.output)
