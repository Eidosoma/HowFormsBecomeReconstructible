"""Derive the first previously measured repeat; never generate a future label."""
import hashlib
import shutil

import numpy as np

from bridge import ROOT, P, ev, read
import ledger
import verify_science


def first_repeat(raw):
    if raw['probes'].tolist() != list(range(64)) or raw['direct_probes'].tolist() != list(range(8))+list(range(32,40)):
        raise ValueError('Expected two complete frozen measurement repeats')
    result = {}
    for name, value in raw.items():
        if name == 'packet':
            result[name] = value.copy()
        elif name == 'direct_probes' or name.startswith('direct_'):
            result[name] = value[:8].copy()
        else:
            result[name] = value[:32].copy()
    return result


def checked_selection(enrolled, selected):
    recovered = []
    for block in P['cohort']['blocks']:
        for current in (0,1):
            group = sorted([r for r in enrolled if r['block']==block and r['current_pass']==current],
                           key=lambda r:r['selection_hash'])
            rules = [[r for r in group if r['rule']==rule] for rule in (-1,1)]
            recovered.extend([r[0] for r in rules] if all(rules) else group[:2])
    if recovered != selected or len(selected) != 63 or len({tuple(r['key']) for r in selected}) != 63:
        raise ValueError('The previously frozen boundary-only selection changed')
    if any(not any(r['block']==b and r['current_pass']==c for r in selected)
           for b in P['cohort']['blocks'] for c in (0,1)):
        raise ValueError('Both expression classes are required in every acquisition block')


def prepare():
    source = ROOT.parent/P['cohort']['source']
    complete = read(source/'COMPLETE.json')
    decision = read(source.parent.parent/'DECISION.json')
    if ev.sha(source/'COMPLETE.json') != decision['evidence']['runs/pilot_v1/COMPLETE.json']:
        raise ValueError('Source completion differs from its verified closeout')
    if complete['status'] != 'COMPLETE' or complete['new_future_outcomes'] != 0 or not complete['independent_audit_pass']:
        raise ValueError('Verified source without future outcomes required')
    if ev.sha(source/'OUTPUTS.json') != complete['output_manifest_sha256']:
        raise ValueError('Source output manifest changed')
    hashes = read(source/'OUTPUTS.json')['sha256']
    original = {}
    def checked(name):
        path = source/name
        if ev.sha(path) != hashes[name]:
            raise ValueError('Source evidence changed: '+name)
        original[name] = dict(path=str(path),sha256=hashes[name])
        return path
    selected = read(checked('SELECTION.json'))['records']
    enrolled = read(checked('ENROLLMENT.json'))['records']
    cases = read(checked('CASES.json'))
    prior = read(checked('FORECASTS.json'))
    checked_selection(enrolled,selected)
    expected = {(tuple(r['key']),regime) for r in selected for regime in ('matched','independent')}
    def indexed(values):
        mapping = {(tuple(r['key']),r['regime']):r for r in values}
        if len(mapping) != len(values) or set(mapping) != expected:
            raise ValueError('Incomplete or duplicate source case panel')
        return mapping
    case_map, prior_map = indexed(cases), indexed(prior)
    cohort = ROOT/'cohort'; cohort.mkdir()
    models = read(ROOT/'FROZEN_MODELS.json')
    if ev.sha(ROOT/'FROZEN_MODELS.json') != P['models_sha256']:
        raise ValueError('Fixed coefficients changed')
    boundaries = {}
    for block in P['cohort']['blocks']:
        path = checked(f'acquisition/boundary_{block:06d}_g14.npz')
        folder = cohort/'boundaries'/f'block_{block:06d}'; folder.mkdir(parents=True)
        shutil.copy2(path,folder/'boundary.npz')
        rows = [r for r in selected if r['block']==block]
        verify_science.boundary(ROOT,folder,rows)
        boundaries[block] = ev.load(path,hashes[str(path.relative_to(source))])
    predictions, packets, references = [], [], []
    for index,row in enumerate(selected):
        key = tuple(row['key'])
        h = P['acquisition']['histories'].index(row['history'])
        encoded = boundaries[row['block']]['outgoing'][h,row['founder'],row['recipient']]
        packet = np.frombuffer(encoded.tobytes(),dtype='<f8').reshape(2,16,16).copy()
        if hashlib.sha256(packet.tobytes()).hexdigest() != row['packet_sha256']:
            raise ValueError('Source packet does not match selected record')
        packets.append(packet)
        for regime in ('matched','independent'):
            case = case_map[(key,regime)]; forecast = prior_map[(key,regime)]
            name = 'measurements/'+case['source']
            path = checked(name+'.npz'); receipt_path = checked(name+'.json')
            receipt = read(receipt_path)
            if receipt['key'] != row['key'] or receipt['regime'] != regime or receipt['raw_sha256'] != ev.sha(path):
                raise ValueError('Source measurement receipt mismatch')
            arrays = first_repeat(ev.load(path,case['raw_sha256']))
            if arrays['packet'].tobytes() != packet.tobytes():
                raise ValueError('Measured packet differs from the acquired boundary')
            folder = cohort/'measurements'/f'case_{index:03d}_{regime}'; folder.mkdir(parents=True)
            digest = ev.save(folder/'probe.npz',arrays)
            derived = dict(receipt,raw_sha256=digest,native_reads=72,flat_native_reads=3,
                forcing=receipt['forcing'][:32],audits=[a for a in receipt['audits'] if a['probe']==0],
                source_raw_sha256=case['raw_sha256'],first_repeat_only=True,new_native_reads=0,
                cost_scope='Native read counts describe the retained historical repeat, not new compute.')
            ev.write(folder/'probe.json',derived)
            prediction = dict(**row,regime=regime,q_rewrite=forecast['q_rewrite'][0],
                q_direct=forecast['q_direct'][0],probabilities={m:v[0] for m,v in forecast['probabilities'].items()})
            verification = verify_science.measurement(folder,row,prediction,P['reader'],models)
            ev.write(folder/'FORECAST.json',prediction); ev.write(folder/'VERIFICATION.json',verification)
            predictions.append(prediction)
            references.append(dict(key=row['key'],regime=regime,folder=str(folder.relative_to(ROOT))))
    ev.save(cohort/'PACKETS.npz',dict(packets=np.stack(packets)))
    ev.write(cohort/'ROWS.json',selected);ev.write(cohort/'FORECASTS.json',predictions)
    ev.write(cohort/'REFERENCES.json',references)
    for name in ('COMPLETE.json','OUTPUTS.json','SELECTION.json','FORECASTS.json','CASES.json'):
        shutil.copy2(source/name,ROOT/'context'/('source_'+name))
    ev.write(ROOT/'SOURCE_DATA.json',dict(source_complete_sha256=ev.sha(source/'COMPLETE.json'),
        source_manifest_sha256=ev.sha(source/'OUTPUTS.json'),source_files=original,
        source_future_outcomes=0,first_repeat_indices=list(range(32)),source_records_selected_before_measurements=True))
    result = dict(utc=ev.utc(),status='PASS',records=len(selected),blocks=16,case_regimes=len(predictions),
        source_files_verified=len(original),first_repeat_predictions_independently_checked=True,
        boundary_only_selection_reproduced=True,new_native_reads=0,new_model_fits=0,new_future_outcomes=0)
    ledger.atomic_json(ROOT/'CACHE_VERIFICATION.json',result)
    print(result,flush=True)


if __name__ == '__main__':
    prepare()
