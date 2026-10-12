"""Phased native qualification, prediction sealing and prospective execution."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import auditor as audit
import forecast
import measure
import native
import support as s

PLAN=s.read(s.HERE/'plan.json')


def save_arrays(path,values):
    index={k:dict(shape=list(v.shape),dtype=v.dtype.str,sha256=hashlib.sha256(v.tobytes()).hexdigest()) for k,v in values.items()}
    with path.open('xb') as f:np.savez_compressed(f,**values,__index__=np.frombuffer(json.dumps(index).encode(),np.uint8))


def load_arrays(path):
    with np.load(path,allow_pickle=False) as z:
        index=json.loads(z['__index__'].tobytes());s.require(set(z.files)==set(index)|{'__index__'},'Indexed array names')
        values={k:z[k] for k in index}
    for k,v in values.items():
        s.require(index[k]==dict(shape=list(v.shape),dtype=v.dtype.str,sha256=hashlib.sha256(v.tobytes()).hexdigest()),'Indexed array commitment '+k)
        if v.dtype.kind=='f':s.require(np.isfinite(v).all(),'Nonfinite native evidence')
    return values


def codes(generation):return [int(generation in schedule) for schedule in PLAN['tolerance_generations']]


def teach(folder,block,cfg):
    began=time.monotonic();raw=native.teaching(block,cfg);receipt=audit.equal(raw,audit.teaching(block,cfg),'teaching')
    save_arrays(folder/'teaching.npz',raw);receipt.update(seconds=time.monotonic()-began)
    initial=np.repeat(raw['acquired'][:,None],cfg['recipients'],axis=1)
    return np.repeat(initial[None],4,axis=0),receipt,sum(v.nbytes for v in raw.values())


def rebuild(folder,packets,block,generation,cfg,cycle):
    began=time.monotonic();raw=native.rebuild(packets,block,generation,codes(generation),cfg,cycle,PLAN['tolerance'])
    receipt=audit.equal(raw,audit.rebuild(packets,block,generation,codes(generation),cfg,cycle,PLAN['tolerance']),f'g{generation}')
    name=f'boundary_g{generation:02d}.npz';save_arrays(folder/name,raw)
    receipt.update(generation=generation,seconds=time.monotonic()-began,file=name,file_sha256=s.sha(folder/name),writer_codes=codes(generation))
    return raw,receipt


def assay(folder,packets,block,cfg,cycle):
    began=time.monotonic();raw=native.assay(packets,block,32,cfg,cycle)
    receipt=audit.equal(raw,audit.assay(packets,block,32,cfg,cycle),'terminal')
    save_arrays(folder/'assay_h32.npz',raw);receipt.update(seconds=time.monotonic()-began,file_sha256=s.sha(folder/'assay_h32.npz'))
    return raw,receipt


def known_expected(generation=None):
    s.require(generation is None or generation in range(3,33),'Known saved generation')
    name=f'boundary_034000_g{generation}.npz' if generation is not None else 'assay_034000_h32.npz'
    spacing=load_arrays(s.HERE/'qualification_sources/spacing'/name);pulse=load_arrays(s.HERE/'qualification_sources/pulse'/name)
    # The original generation-3 branch files were assembled from a shared body
    # and did not retain its birth state. This is the only accepted omission.
    shared=['masks']+([] if generation==3 else ['birth'])
    branch=['end','mean_ports']+([] if generation is None else ['outgoing'])
    for label,values in [('spacing',spacing),('pulse',pulse)]:
        s.require(('birth' in values)==(generation!=3),'Known birth schema '+label)
        s.require(set(shared+branch)<=set(values),'Known retained fields '+label)
    audit.equal({k:spacing[k] for k in shared},{k:pulse[k] for k in shared},'known_common_inputs')
    result={k:spacing[k] for k in shared}
    choices=[(spacing,0),(pulse,2),(spacing,1),(spacing,2)]+([] if generation is not None else [(spacing,3)])
    for field in branch:result[field]=np.stack([values[field][slot] for values,slot in choices])
    return result


def check_known(raw,generation=None):
    expected=known_expected(generation)
    native_fields={'masks','birth','end','mean_ports'}|({'outgoing'} if generation is not None else set())
    s.require(set(raw)==native_fields,'Complete independently replayed native fields')
    unretained=sorted(set(raw)-set(expected))
    s.require(unretained==(['birth'] if generation==3 else []),'Explicit historical omission only')
    label=f'saved_generation_{generation}' if generation is not None else 'saved_terminal'
    receipt=audit.equal({k:raw[k] for k in expected},expected,label)
    receipt.update(historically_unretained_fields=unretained,
        independent_replay_fields=sorted(native_fields))
    return receipt


def qualify_known(output,status):
    folder=output/'known_qualification';folder.mkdir();block=PLAN['qualification_block'];cfg=PLAN['native_config'];cycle=PLAN['native_cycle']
    status('known_qualification_teaching',block=block);packets,teaching,_=teach(folder,block,cfg);receipts=[];prior_checks=[]
    for generation in range(1,33):
        status('known_qualification_rebuild',block=block,generation=generation)
        raw,receipt=rebuild(folder,packets,block,generation,cfg,cycle);receipts.append(receipt);packets=raw['outgoing']
        if generation>=3:prior_checks.append(check_known(raw,generation))
        if generation==14:
            rows,_=measure.records(block,raw);saved={s.key(r):r for r in s.records() if r['block']==block}
            for row in rows:
                for name in [*s.FIELDS,'unsigned_access','signed_transfer']:s.close(row[name],saved[s.key(row)][name],1e-13,'Known forecast feature')
    status('known_qualification_terminal',block=block);terminal,receipt=assay(folder,packets,block,cfg,cycle);receipts.append(receipt)
    prior_checks.append(check_known(terminal))
    result=dict(status='PASS',block=block,teaching=teaching,replays=receipts,saved_boundary_and_assay_checks=prior_checks,
        source_scope='All four histories, every stored generation 3–32 boundary and terminal; independent nonlinear carried-state replay includes teaching and generations 1–32.',
        new_test_outcomes_generated=False)
    s.dump(folder/'COMPLETE.json',result);return dict(status='PASS',block=block,complete_sha256=s.sha(folder/'COMPLETE.json'))


def benchmark(output,status):
    folder=output/'benchmark';folder.mkdir();cfg=PLAN['native_config'];cycle=PLAN['native_cycle'];block=PLAN['excluded_technical_block']
    status('excluded_full_size_teaching');packets,teacher,teacher_bytes=teach(folder,block,cfg);times=[];sizes=[]
    for generation in [3,14]:
        status('excluded_full_size_rebuild',generation=generation);raw,receipt=rebuild(folder,packets,block,generation,cfg,cycle)
        times.append(receipt['seconds']);sizes.append(sum(v.nbytes for v in raw.values()));packets=raw['outgoing']
    status('excluded_full_size_terminal');terminal,final=assay(folder,packets,block,cfg,cycle)
    elapsed=PLAN['forecast_safety_factor']*((PLAN['scientific_blocks']+1)*(32*max(times)+final['seconds']+teacher['seconds'])+120)
    storage=int(1.5*(PLAN['scientific_blocks']+1)*(teacher_bytes+32*max(sizes)+sum(v.nbytes for v in terminal.values()))+PLAN['storage_reserve_bytes'])
    result=dict(status='PASS',excluded_block=block,rebuild_and_replay_seconds=times,teacher_and_replay_seconds=teacher['seconds'],
        terminal_assay_and_replay_seconds=final['seconds'],forecast_seconds=elapsed,formula=PLAN['forecast_formula'],storage_required_bytes=storage,
        maximum_forecast_seconds=PLAN['maximum_forecast_seconds'],runtime_capacity_pass=elapsed<=PLAN['maximum_forecast_seconds'],
        native_test_outcomes_generated=False,full_size_rebuild_replays=2,full_size_terminal_replays=1)
    s.dump(output/'benchmark.json',result);return result


def prefix(output,block,status):
    folder=output/f'blocks/{block}';folder.mkdir(parents=True,exist_ok=False);cfg=PLAN['native_config'];cycle=PLAN['native_cycle'];began=time.monotonic()
    status('test_prefix_teaching',block=block);packets,teacher,_=teach(folder,block,cfg);receipts=[]
    for generation in range(1,15):
        status('test_prefix_rebuild',block=block,generation=generation);raw,receipt=rebuild(folder,packets,block,generation,cfg,cycle)
        receipts.append(receipt);packets=raw['outgoing']
    rows,weights=measure.records(block,raw);s.csv_write(folder/'features.csv',rows)
    s.dump(folder/'PREFIX_COMPLETE.json',dict(status='PASS',block=block,utc=s.utc(),seconds=time.monotonic()-began,teaching=teacher,replays=receipts,
        boundary_sha256=s.sha(folder/'boundary_g14.npz'),features_sha256=s.sha(folder/'features.csv'),future_generated=False))
    return rows,weights


def predictions(rows,packets):
    fits=s.read(s.HERE/'FROZEN_MODELS.json');results=[]
    for name,fit in fits.items():
        spec=fit['spec'];kind=spec['kind'] if spec['family']=='logistic' else 'expression_unsigned';x,columns=forecast.design(rows,kind)
        s.require(columns==fit['columns'],'Frozen feature order')
        if spec['family']=='logistic':p=forecast.logistic_predict(x,fit)
        else:p=forecast.kernel_predict([x]+([packets] if spec['kind']=='packet_plus_expression' else []),fit)
        s.require(np.isfinite(p).all() and ((p>=0)&(p<=1)).all(),'Prediction probability range')
        for row,value in zip(rows,p,strict=True):results.append(dict(model=name,**{k:row[k] for k in s.KEYS},probability=float(value)))
    return results


def seal(output,rows,packets,blocks):
    s.require(len(rows)==4096 and len({s.key(r) for r in rows})==4096,'Prediction cohort identity')
    s.require({r['block'] for r in rows}==set(blocks),'Prediction block set')
    s.require(not any(output.glob('blocks/*/FUTURE_STARTED.json')) and not any(output.glob('blocks/*/assay_h32.npz')),'Premature future generation')
    values=predictions(rows,packets);s.csv_write(output/'features.csv',rows);s.csv_write(output/'predictions.csv',values)
    seals={}
    for block in blocks:
        folder=output/f'blocks/{block}';receipt=s.read(folder/'PREFIX_COMPLETE.json')
        for name,key in [('features.csv','features_sha256'),('boundary_g14.npz','boundary_sha256')]:s.require(s.sha(folder/name)==receipt[key],'Changed prefix evidence')
        seals[str(block)]=s.sha(folder/'PREFIX_COMPLETE.json')
    s.dump(output/'PREDICTION_SEAL.json',dict(status='SEALED_BEFORE_ANY_NEW_CONTINUATION',sealed_utc=s.utc(),blocks=blocks,records=4096,predictions=len(values),
        predictions_sha256=s.sha(output/'predictions.csv'),features_sha256=s.sha(output/'features.csv'),prefix_completion_sha256=seals,
        registration_sha256=s.sha(s.HERE/'REGISTRATION.json'),models_sha256=s.sha(s.HERE/'FROZEN_MODELS.json'),future_generated=False))
    return dict(predictions=len(values),seal_sha256=s.sha(output/'PREDICTION_SEAL.json'))


def continuation(output,block,status):
    seal=s.read(output/'PREDICTION_SEAL.json');s.require(s.sha(output/'predictions.csv')==seal['predictions_sha256'],'Prediction seal changed')
    folder=output/f'blocks/{block}';s.require(s.sha(folder/'PREFIX_COMPLETE.json')==seal['prefix_completion_sha256'][str(block)],'Prefix seal changed')
    started=s.utc();s.require(datetime.fromisoformat(started)>=datetime.fromisoformat(seal['sealed_utc']),'Clock/seal chronology')
    s.dump(folder/'FUTURE_STARTED.json',dict(block=block,utc=started,prediction_seal_sha256=s.sha(output/'PREDICTION_SEAL.json')))
    packets=load_arrays(folder/'boundary_g14.npz')['outgoing'];cfg=PLAN['native_config'];cycle=PLAN['native_cycle'];receipts=[]
    for generation in range(15,33):
        status('test_continuation_rebuild',block=block,generation=generation);raw,receipt=rebuild(folder,packets,block,generation,cfg,cycle)
        receipts.append(receipt);packets=raw['outgoing']
    status('test_terminal_assay',block=block);raw,receipt=assay(folder,packets,block,cfg,cycle);receipts.append(receipt)
    s.csv_write(folder/'terminal.csv',measure.terminal(block,raw));s.dump(folder/'COMPLETE.json',dict(status='PASS',block=block,utc=s.utc(),replays=receipts,
        assay_sha256=s.sha(folder/'assay_h32.npz'),terminal_table_sha256=s.sha(folder/'terminal.csv'),prediction_seal_sha256=s.sha(output/'PREDICTION_SEAL.json')))


def scientific(output,status):
    result=qualify_known(output,status);s.require(result['status']=='PASS','Known full qualification')
    blocks=list(range(PLAN['first_block'],PLAN['last_block']+1));rows=[];packets=[]
    for block in blocks:
        r,p=prefix(output,block,status);rows.extend(r);packets.extend(p)
    status('sealing_all_test_predictions');receipt=seal(output,rows,np.array(packets),blocks)
    for block in blocks:continuation(output,block,status)
    return dict(status='PASS',blocks_completed=blocks,known_qualification=result,prediction_seal=receipt,native_rebuild_replays=65*32,teaching_replays=65,terminal_replays=65)
