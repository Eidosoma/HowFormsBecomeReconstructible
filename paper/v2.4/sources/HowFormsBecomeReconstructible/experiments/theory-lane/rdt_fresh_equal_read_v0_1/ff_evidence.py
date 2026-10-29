"""Verify the boundary cohort and all forecasts before opening any future."""
from pathlib import Path
import math
from ff_common import C, P, NATIVE, REGIMES, MODELS, binding, identity, ledger, ev, read, require
import ff_selection
import pipeline
import verify_science
import fe_measurement


def attempt_rows(root, refs, spec):
    attempts={}
    for ref in refs:
        folder,value=ledger.referenced(root,ref)
        b=value['payload']['block']
        require(value['identity']==identity(spec,'acquire',block=b), 'Wrong acquisition identity')
        require(b not in attempts, 'Duplicate acquisition block')
        rows=read(folder/'ENROLLMENT.json')['rows']
        require(rows==value['payload']['rows'], 'Acquisition rows differ from commit')
        ff_selection.check_rows(b,rows,spec['scope']=='scientific')
        attempts[b]=rows
    return attempts


def seal_selection(root, refs, spec):
    attempts=attempt_rows(root,refs,spec)
    chosen=ff_selection.cohort(attempts,spec)
    require(chosen['complete'], 'Incomplete eligible cohort; no forecast or future permitted')
    folder=root/'selection';folder.mkdir()
    plan=dict(**chosen,spec=spec,binding=binding(),acquisitions=refs)
    ledger.atomic_json(folder/'COHORT.json',plan)
    ledger.commit(folder,identity(spec,'selection'),dict(blocks=chosen['blocks'],rows=chosen['rows']))
    return ledger.reference(root,folder)


def selection(root, ref, spec):
    folder,entry=ledger.referenced(root,ref,identity(spec,'selection'))
    plan=read(folder/'COHORT.json')
    require(plan['spec']==spec and plan['binding']==binding(), 'Cohort binding changed')
    require(entry['payload']==dict(blocks=plan['blocks'],rows=plan['rows']), 'Selection payload mismatch')
    return plan


def acquisition_source(root, plan, block, spec):
    refs=[r for r in plan['acquisitions'] if read(root/r['path']/'COMMIT.json')['payload']['block']==block]
    require(len(refs)==1, 'Missing or duplicate acquisition source')
    folder,entry=ledger.referenced(root,refs[0],identity(spec,'acquire',block=block))
    rows=[r for r in plan['rows'] if r['block']==block]
    require(rows==ff_selection.select(entry['payload']['rows']), 'Selected rows differ from boundary-only selection')
    verify_science.boundary(NATIVE,folder,rows,spec['scope']!='scientific')
    return folder,rows,pipeline.packets_for(folder,rows)


def verify_measurement(root, ref, rows, spec):
    block=rows[0]['block']
    folder,entry=ledger.referenced(root,ref,identity(spec,'measure',block=block))
    expected=[];native=flat=0
    for i,row in enumerate(rows):
        for regime in REGIMES:
            case=folder/f'case_{i:02d}_{regime}'
            forecast=fe_measurement.check_saved(case,row,regime)
            native+=128;flat+=4;expected.append(forecast)
    require(entry['payload']==dict(block=block,forecasts=expected,native_reads=native,flat_native_reads=flat),
            'Measurement aggregate or read cost differs')
    require(read(folder/'FORECASTS.json')==expected, 'Measurement forecast coverage differs')
    return expected


def seal_forecasts(root, spec, selection_ref, measurement_refs):
    require(not (root/'units/future').exists(), 'Future evidence precedes global forecast seal')
    plan=selection(root,selection_ref,spec)
    # Reconstruct enrollment from every committed attempt, including surplus ones.
    rebuilt=ff_selection.cohort(attempt_rows(root,plan['acquisitions'],spec),spec)
    require(all(plan[k]==v for k,v in rebuilt.items()), 'Cohort differs from first eligible blocks')
    require(len(measurement_refs)==len(plan['blocks']), 'Incomplete forecasts: barrier remains closed')
    forecasts=[];seen=[]
    for ref in measurement_refs:
        _,entry=ledger.referenced(root,ref)
        block=entry['payload']['block'];seen.append(block)
        _,rows,_=acquisition_source(root,plan,block,spec)
        forecasts.extend(verify_measurement(root,ref,rows,spec))
    require(seen==plan['blocks'], 'Missing, reordered or duplicate forecast blocks')
    check_model_coverage(forecasts)
    folder=root/'forecast_seal';folder.mkdir()
    value=dict(utc=ev.utc(),spec=spec,binding=binding(),selection=selection_ref,
        blocks=plan['blocks'],rows=plan['rows'],forecasts=forecasts,measurements=measurement_refs,
        all_forecasts_independently_checked_before_any_future=True)
    ledger.atomic_json(folder/'FORECAST_SEAL.json',value)
    ledger.commit(folder,identity(spec,'forecast_seal'),dict(records=len(plan['rows']),forecasts=len(forecasts)))
    return dict(path=str((folder/'FORECAST_SEAL.json').relative_to(root)),sha256=ev.sha(folder/'FORECAST_SEAL.json'),
                ref=ledger.reference(root,folder))


def check_seal(root, ref, spec):
    path=ledger.child(root,ref['path'])
    require(path.exists() and ev.sha(path)==ref['sha256'], 'An unchanged full-cohort forecast seal is required')
    folder,entry=ledger.referenced(root,ref['ref'],identity(spec,'forecast_seal'))
    require(path==folder/'FORECAST_SEAL.json', 'Wrong sealed file')
    seal=read(path)
    require(seal['binding']==binding() and seal['spec']==spec and
        seal['all_forecasts_independently_checked_before_any_future'], 'Forecast seal binding differs')
    require(len(seal['blocks'])==spec['eligible_blocks'] and len(set(seal['blocks']))==len(seal['blocks']),
            'Incomplete forecast cohort')
    require(len(seal['measurements'])==len(seal['blocks']), 'Incomplete measurement block references')
    keys=[tuple(r['key']) for r in seal['rows']]
    require(len(keys)==len(set(keys)) and sorted({r['block'] for r in seal['rows']})==seal['blocks'], 'Sealed cohort identities differ')
    pairs=[(tuple(f['key']),f['regime']) for f in seal['forecasts']]
    require(len(pairs)==len(set(pairs)) and set(pairs)=={(k,g) for k in keys for g in REGIMES}, 'Incomplete sealed forecasts')
    require(entry['payload']==dict(records=len(keys),forecasts=len(pairs)), 'Seal counts differ')
    check_model_coverage(seal['forecasts'])
    return path,seal


def verify_future(root, ref, rows, rep, spec, seal_ref):
    block=rows[0]['block']
    folder,entry=ledger.referenced(root,ref,identity(spec,'future',block=block,replicate=rep,seal_sha256=seal_ref['sha256']))
    audit_key=min(rows,key=lambda r:r['selection_hash'])['key'];outcomes=[];native=flat=0
    for regime in REGIMES:
        case=folder/regime;labels=read(case/'OUTCOMES.json');receipt=read(case/'future.json')
        require(receipt['stage']==C['stage']+f'/replicate_{rep}', 'Wrong future replicate stream')
        verify_science.continuation(case,rows,labels,P['reader'],seal_ref['sha256'],audit_key)
        outcomes.extend(dict(**y,replicate=rep) for y in labels)
        native+=receipt['native_reads'];flat+=receipt['flat_native_reads']
    require(entry['payload']==dict(block=block,replicate=rep,outcomes=outcomes,native_reads=native,flat_native_reads=flat),
            'Future aggregate or read cost differs')
    return outcomes


def check_model_coverage(forecasts):
    require(all(set(f.get('probabilities', {})) == set(MODELS) and all(math.isfinite(p) and 0 <= p <= 1 for p in f['probabilities'].values()) for f in forecasts), 'All five finite fixed forecasts are required before any future')
