"""Complete forecast-first workflow, with deterministic independently checked units."""
from contextlib import contextmanager
import hashlib

import numpy as np

from bridge import ROOT, P, e, ev, read
import acquisition
import fast_reader
import frozen_prediction
import futures
import ledger
import measurement
import probes
import scoring
import verify_science


def specification(mode):
    histories = P['acquisition']['histories']
    if mode == 'outcome':
        blocks = P['cohort']['blocks']
        keys = [[b,h,f,r] for b in blocks for h in histories for f in range(4) for r in range(4)]
        return dict(scope='scientific', stage='outcome', blocks=blocks, records_per_block=64, keys=keys)
    if mode == 'native_qualification':
        keys = [[-2,histories[0],0,0],[-2,histories[1],1,0],
                [-1,histories[2],2,0],[-1,histories[3],3,0]]
        return dict(scope='synthetic_qualification', stage='qualification', blocks=[-2,-1], records_per_block=2, keys=keys)
    raise ValueError('Undeclared cohort mode')


def identity(binding, spec, kind, **fields):
    return dict(binding=binding, scope=spec['scope'], stage=spec['stage'], kind=kind, **fields)


def unit(container, ident, work, guard):
    found = ledger.existing(container, ident)
    if found is not None:
        return found
    guard.check()
    folder = ledger.new_attempt(container)
    value = work(folder)
    committed = ledger.commit(folder, ident, value)
    guard.account(folder); guard.check()
    return folder, committed


def synthetic_packets():
    rng = np.random.default_rng(2026101601)
    random = rng.uniform(-1.,1.,(2,16,16)); random[rng.random(random.shape)<.2] = 0.
    field = np.where(np.indices((16,16)).sum(axis=0)%3==0,-1.,1.)
    structured = np.stack([.7*field*np.roll(field,-1,axis=ax) for ax in (1,0)])
    return np.stack([np.zeros_like(random),np.full_like(random,.6),structured,random])


def synthetic_acquisition(block, spec):
    packets = synthetic_packets()
    outgoing = np.repeat(np.repeat(e.native.encode(packets)[:,None,None],4,axis=1),4,axis=2)
    means = np.zeros((4,4,4,2,2)); target = np.array([[1.,-1.],[-1.,1.]])
    for h in range(4):
        for founder in range(4):
            means[h,founder] = (.1 if h%2==0 else .8)*(1 if founder%2==0 else -1)*target
    raw = dict(outgoing=outgoing,mean_ports=means)
    requested = {tuple(k) for k in spec['keys'] if k[0]==block}
    rows = [r for r in acquisition.boundary_records(block,raw) if tuple(r['key']) in requested]
    return raw, rows, dict(native_reads=0,flat_native_reads=0,synthetic=True,new_scientific_outcomes=0)


def acquisition_unit(root, block, spec, binding, guard):
    ident = identity(binding,spec,'acquisition',block=block)
    def work(folder):
        if spec['scope']=='scientific':
            raw, rows, receipt = acquisition.acquire(block,spec['stage'],folder,guard,legacy=False)
        else:
            raw, rows, receipt = synthetic_acquisition(block,spec)
        expected = [k for k in spec['keys'] if k[0]==block]
        if [r['key'] for r in rows] != expected:
            raise ValueError('Enrollment differs from the frozen complete block')
        ev.save(folder/'boundary.npz',raw)
        ev.write(folder/'ENROLLMENT.json',dict(rows=rows,receipt=receipt))
        audit = verify_science.boundary(ROOT,folder,rows,spec['scope']!='scientific')
        ev.write(folder/'VERIFICATION.json',audit)
        return dict(rows=rows,receipt=receipt)
    return unit(root/f'units/acquisition/block_{block:06d}',ident,work,guard)


def packets_for(folder, rows):
    commit = read(folder/'COMMIT.json')
    raw = ev.load(folder/'boundary.npz',commit['sha256']['boundary.npz'])
    values = []
    for row in rows:
        index = (P['acquisition']['histories'].index(row['history']),row['founder'],row['recipient'])
        packet = e.native.decode(raw['outgoing'][index])
        if hashlib.sha256(packet.tobytes()).hexdigest()!=row['packet_sha256']:
            raise ValueError('Wrong enrolled packet')
        values.append(packet)
    return values


@contextmanager
def accelerated():
    old = probes.read_batch; probes.read_batch = fast_reader.read_batch
    try:
        yield
    finally:
        probes.read_batch = old


def forecast(row, regime, raw):
    models = read(ROOT/'FROZEN_MODELS.json')
    q = float(raw['successor_passed'].mean()); direct = float(raw['direct_passed'].mean())
    values = {name:frozen_prediction.predict(row['boundary'],extra,models[name])
              for name,extra in [('candidate',q),('direct_rival',direct),('tt008',None)]}
    return dict(**row,regime=regime,q_rewrite=q,q_direct=direct,probabilities=values)


def measurement_unit(root,row,packet,regime,spec,binding,guard):
    ident = identity(binding,spec,'measurement',key=row['key'],regime=regime)
    history = P['acquisition']['histories'].index(row['history'])
    container = root/f"units/measurement/block_{row['block']:06d}/h{history}_f{row['founder']}_r{row['recipient']}_{regime}"
    def work(folder):
        with accelerated():
            raw, receipt = measurement.measure(packet,row['rule'],row['key'],regime,spec['stage'],
                                               folder/'probe',guard,indices=list(range(32)))
        prediction = forecast(row,regime,raw)
        ev.write(folder/'FORECAST.json',prediction)
        check = verify_science.measurement(folder,row,prediction,P['reader'],read(ROOT/'FROZEN_MODELS.json'))
        ev.write(folder/'VERIFICATION.json',check)
        return dict(forecast=prediction,native_reads=receipt['native_reads'],flat_native_reads=receipt['flat_native_reads'])
    return unit(container,ident,work,guard)


def forecast_block(root,block,spec,binding,guard,on_event):
    ident = identity(binding,spec,'forecast_block',block=block)
    def work(folder):
        source, acq = acquisition_unit(root,block,spec,binding,guard)
        rows = acq['payload']['rows']; packets = packets_for(source,rows)
        refs = []; predictions = []
        for row,packet in zip(rows,packets,strict=True):
            for regime in scoring.REGIMES:
                path, result = measurement_unit(root,row,packet,regime,spec,binding,guard)
                refs.append(ledger.reference(root,path)); predictions.append(result['payload']['forecast'])
                on_event('measurement_committed',dict(block=block,key=row['key'],regime=regime))
        ev.write(folder/'FORECASTS.json',predictions)
        payload = dict(block=block,acquisition=ledger.reference(root,source),measurements=refs,
                       records=len(rows),case_regimes=len(predictions))
        return payload
    return unit(root/f'units/forecast_blocks/block_{block:06d}',ident,work,guard)


def verify_forecast_block(root,folder,value,spec,binding,independent=False):
    block = value['payload']['block']; expected = [k for k in spec['keys'] if k[0]==block]
    source, acq = ledger.referenced(root,value['payload']['acquisition'],identity(binding,spec,'acquisition',block=block))
    rows = acq['payload']['rows']
    if [r['key'] for r in rows] != expected:
        raise ValueError('Incomplete boundary block')
    if independent:
        verify_science.boundary(ROOT,source,rows,spec['scope']!='scientific')
    recorded = read(folder/'FORECASTS.json'); rebuilt = []
    expected_pairs = [(row,regime) for row in rows for regime in scoring.REGIMES]
    if len(value['payload']['measurements']) != len(expected_pairs):
        raise ValueError('Incomplete forecast block')
    for ref,(row,regime) in zip(value['payload']['measurements'],expected_pairs,strict=True):
        path, entry = ledger.referenced(root,ref,identity(binding,spec,'measurement',key=row['key'],regime=regime))
        prediction = read(path/'FORECAST.json')
        if prediction != entry['payload']['forecast'] or prediction['key']!=row['key'] or prediction['regime']!=regime:
            raise ValueError('Forecast content or order changed')
        if independent:
            verify_science.measurement(path,row,prediction,P['reader'],read(ROOT/'FROZEN_MODELS.json'))
        rebuilt.append(prediction)
    if recorded != rebuilt:
        raise ValueError('Block forecasts are not the committed per-record forecasts')
    return source,rows,recorded


def seal_forecasts(root,spec,binding,guard):
    """Verify the entire declared cohort before permitting any continuation."""
    block_refs = []
    for block in spec['blocks']:
        found = ledger.existing(root/f'units/forecast_blocks/block_{block:06d}',identity(binding,spec,'forecast_block',block=block))
        if found is None:
            raise ValueError('Incomplete cohort: future barrier remains closed')
        folder,value = found
        verify_forecast_block(root,folder,value,spec,binding)
        block_refs.append(ledger.reference(root,folder))
    ident = identity(binding,spec,'global_forecast_seal')
    def work(folder):
        seal = dict(utc=ev.utc(),binding=binding,scope=spec['scope'],spec=spec,
                    forecast_blocks=block_refs,records=len(spec['keys']),case_regimes=2*len(spec['keys']),
                    all_forecasts_and_evidence_verified_before_any_future=True)
        ev.write(folder/'FORECAST_SEAL.json',seal)
        return dict(records=len(spec['keys']),forecast_blocks=block_refs)
    folder,value = unit(root/'units/forecast_seal',ident,work,guard)
    seal = read(folder/'FORECAST_SEAL.json')
    if seal['spec']!=spec or seal['binding']!=binding or seal['forecast_blocks']!=block_refs:
        raise ValueError('The global forecast seal changed')
    return folder/'FORECAST_SEAL.json',ev.sha(folder/'FORECAST_SEAL.json'),block_refs


def future_unit(root,rows,packets,audit_key,regime,spec,binding,guard,seal_path,seal_sha):
    keys = [r['key'] for r in rows];block = keys[0][0]
    first = keys[0]; h = P['acquisition']['histories'].index(first[1])
    ident = identity(binding,spec,'future',keys=keys,regime=regime,forecast_seal_sha256=seal_sha)
    container = root/f'units/future/block_{block:06d}/h{h}_f{first[2]}_r{first[3]}_{regime}'
    def work(folder):
        receipt,outcomes = futures.batch(rows,packets,audit_key,regime,spec['stage'],folder/'future',
                                          guard,seal_path,seal_sha)
        ev.write(folder/'OUTCOMES.json',outcomes)
        check = verify_science.continuation(folder,rows,outcomes,P['reader'],seal_sha,audit_key)
        ev.write(folder/'VERIFICATION.json',check)
        return dict(outcomes=outcomes,native_reads=receipt['native_reads'],flat_native_reads=receipt['flat_native_reads'])
    return unit(container,ident,work,guard)


def run(root,spec,binding,guard,on_event=lambda *_:None):
    """A resume revisits only hash-valid commits under the identical binding."""
    for block in spec['blocks']:
        forecast_block(root,block,spec,binding,guard,on_event)
        on_event('forecast_block_committed',dict(block=block))
    seal_path,seal_sha,block_refs = seal_forecasts(root,spec,binding,guard)
    on_event('forecasts_sealed',dict(seal_sha256=seal_sha))
    future_refs = []
    for ref in block_refs:
        folder,value = ledger.referenced(root,ref)
        source,rows,_ = verify_forecast_block(root,folder,value,spec,binding)
        packets = packets_for(source,rows); audit_key = min(rows,key=lambda r:r['selection_hash'])['key']
        for offset in range(0,len(rows),4):
            batch_rows = rows[offset:offset+4]; batch_packets = packets[offset:offset+4]
            for regime in scoring.REGIMES:
                path,entry = future_unit(root,batch_rows,batch_packets,audit_key,regime,spec,binding,
                                         guard,seal_path,seal_sha)
                future_refs.append(dict(ref=ledger.reference(root,path),rows=batch_rows,audit_key=audit_key))
                on_event('future_batch_committed',dict(block=rows[0]['block'],offset=offset,regime=regime))
    # No primary score is evaluated until every continuation is committed.
    forecasts, outcomes = [], []
    for ref in block_refs:
        folder,value = ledger.referenced(root,ref)
        _,_,predictions = verify_forecast_block(root,folder,value,spec,binding,independent=True)
        forecasts.extend(predictions)
    for item in future_refs:
        folder,value = ledger.referenced(root,item['ref'])
        labels = read(folder/'OUTCOMES.json')
        if labels != value['payload']['outcomes']:
            raise ValueError('Committed outcomes changed')
        verify_science.continuation(folder,item['rows'],labels,P['reader'],seal_sha,item['audit_key'])
        outcomes.extend(labels)
    result = scoring.analyze(forecasts,outcomes,spec)
    audit = verify_science.analysis(forecasts,outcomes,result,spec['blocks'])
    final_identity = identity(binding,spec,'final',forecast_seal_sha256=seal_sha)
    def work(folder):
        ev.write(folder/'ANALYSIS.json',result);ev.write(folder/'VERIFICATION.json',audit)
        ev.write(folder/'FUTURE_REFERENCES.json',[v['ref'] for v in future_refs])
        with (folder/'REPORT.md').open('x') as stream:stream.write(scoring.report(result))
        return dict(decision=result['decision'],scope=spec['scope'],records=len(spec['keys']),
            case_regimes=2*len(spec['keys']),forecast_seal_path=str(seal_path.relative_to(root)),
            forecast_seal_sha256=seal_sha,independent_analysis_verified=True,new_model_fits=0)
    folder,value = unit(root/'units/final',final_identity,work,guard)
    return dict(**value['payload'],final_reference=ledger.reference(root,folder))
