"""Read a fixed exposed E051 cohort and compare writers on identical bodies."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time
import traceback

import numpy as np
import core

ROOT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for piece in iter(lambda:f.read(1048576),b''):
            h.update(piece)
    return h.hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    with Path(path).open('x') as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def read_retained(path, keys):
    with np.load(path,allow_pickle=False) as f:
        index=json.loads(f['__index__'].tobytes())
        values={key:f[key] for key in keys}
    for key,value in values.items():
        expected=index['arrays'][key]
        assert list(value.shape)==expected['shape'] and value.dtype.str==expected['dtype'],(str(path),key,'descriptor')
        assert hashlib.sha256(value.tobytes()).hexdigest()==expected['sha256'],(str(path),key,'commitment')
    return values,index


def encoded(weights):
    return np.ascontiguousarray(weights,dtype='<f8').view(np.uint8).reshape(*weights.shape[:-3],4096)


def same(a,b,context):
    assert a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes(),context


def extract(output,benchmark):
    started=time.perf_counter()
    cfg=json.loads((ROOT/'config.json').read_text())
    run=(ROOT/cfg['source_run']).resolve()
    native=json.loads((run/'manifest.json').read_text())
    contract=native['contract']
    assert contract['config']['side']==16 and contract['config']['recipients']==4
    assert contract['config']['writer_beta']==3. and contract['tolerance']==cfg['tolerance']
    conditions=[p+'/'+w for p in cfg['pairings'] for w in cfg['source_writers']]
    indices=[contract['conditions'].index(c) for c in conditions]
    original_cases=cfg['blocks']
    blocks=original_cases[:1] if benchmark else original_cases
    generations=[1] if benchmark else cfg['generations']
    output.mkdir(parents=True,exist_ok=False)
    metadata=dict(status='RUNNING',analysis='RETROSPECTIVE_DEVELOPMENT',started_at_utc=stamp(),
        benchmark=benchmark,blocks=blocks,generations=generations,conditions=conditions,
        config=cfg,config_sha256=sha(ROOT/'config.json'),
        code_sha256={n:sha(ROOT/n) for n in ('core.py','extract.py')},
        environment=dict(python=platform.python_version(),numpy=np.__version__,numerical_threads=1),
        raw_data=[],checks=dict(retained_commitments=0,actual_packets=0,initial_common_bodies=0,
                              current_scores=0,next_scores=0,terminal_scores=0),
        native_simulator_steps=0,
        interpretation='Writer counterfactuals and linear transfer only. Future outcomes are observed-policy outcomes, not outcomes under counterfactual sign restoration.')
    write_json(output/'START.json',metadata)
    # Check the scientific run's frozen source identities, without importing it.
    verified_sources={}
    for relative in ('E051_cue_pairing_robustness/model.py','E051_cue_pairing_robustness/PROTOCOL.md',
                     'E022_reader_compensation/model.py','E015_functional_inheritance/model.py'):
        path=run/'inputs'/relative
        actual=sha(path)
        assert actual==native['inputs_sha256'][relative],relative
        verified_sources[relative]=actual
    metadata['verified_frozen_native_sources']=verified_sources
    rows_written=0
    try:
        with (output/'features.csv').open('x',newline='') as target:
            writer=None
            for block in blocks:
                source_path=run/f'source_{block:06d}.npz'
                with np.load(source_path,allow_pickle=False) as source:
                    ports=source['ports'];rules=source['rules'];cues=source['cues']
                assert ports.shape==(3,16,16) and rules.shape==(4,) and cues.tolist()==[1.,-1.]
                flat_rules=np.broadcast_to(rules[None,:,None],(len(indices),4,4)).reshape(-1)
                metadata['raw_data'].append(dict(path=str(source_path),sha256=sha(source_path),read_fields=['ports','rules','cues']))
                cases_path=run/f'cases_{block:06d}.npz'
                with np.load(cases_path,allow_pickle=False) as f:
                    cases={k:f[k] for k in ('body_correct','body_margin','body_ports',
                        'assay_h32_correct','assay_h32_margin','assay_h32_ports')}
                metadata['raw_data'].append(dict(path=str(cases_path),sha256=sha(cases_path),read_fields=list(cases)))
                terminal_path=run/f'assay_{block:06d}_h32.npz'
                terminal_raw,_=read_retained(terminal_path,['mean_ports'])
                metadata['checks']['retained_commitments']+=1
                same(terminal_raw['mean_ports'][indices],cases['assay_h32_ports'][indices],'terminal mean ports')
                terminal_ports=terminal_raw['mean_ports'][indices][:,:,:,:,1,:].reshape(-1,2,2)
                terminal_margin,terminal_pass,all_margins=core.score_ports(terminal_ports,flat_rules,contract['config']['margin'])
                np.testing.assert_array_equal(terminal_pass,cases['assay_h32_correct'][indices][:,:,:,:,1].all(axis=-1).ravel())
                np.testing.assert_array_equal(all_margins,cases['assay_h32_margin'][indices][:,:,:,:,1].reshape(-1,2))
                metadata['checks']['terminal_scores']+=len(terminal_pass)
                metadata['raw_data'].append(dict(path=str(terminal_path),sha256=sha(terminal_path),read_fields=['mean_ports']))
                for generation in generations:
                    path=run/f'boundary_{block:06d}_g{generation}.npz'
                    raw,_=read_retained(path,['end','masks','mean_ports','outgoing'])
                    metadata['checks']['retained_commitments']+=4
                    end=raw['end'][indices]
                    if generation==1:
                        for p in range(len(cfg['pairings'])):
                            same(end[2*p],end[2*p+1],('initial common body',block,p))
                            metadata['checks']['initial_common_bodies']+=16
                    body=end.reshape(-1,2,16,16)
                    mask=np.broadcast_to(raw['masks'][None],(len(indices),4,4,16,16)).reshape(-1,16,16)
                    values,pair=core.features(body,mask,ports,flat_rules,cfg['linear_transfer_steps'],cfg['tolerance'])
                    actual=np.empty_like(pair['exact']).reshape(len(indices),4,4,2,16,16)
                    for n,condition in enumerate(conditions):
                        name='exact' if condition.endswith('/exact_rewrite') else 'tolerance'
                        actual[n]=pair[name].reshape(len(indices),4,4,2,16,16)[n]
                    same(encoded(actual),raw['outgoing'][indices],('actual outgoing',block,generation))
                    metadata['checks']['actual_packets']+=len(body)
                    current_ports=raw['mean_ports'][indices].reshape(-1,2,2)
                    same(raw['mean_ports'][indices],cases['body_ports'][generation-1,indices],('current ports',block,generation))
                    current_margin,current_pass,current_all=core.score_ports(current_ports,flat_rules,contract['config']['margin'])
                    np.testing.assert_array_equal(current_all,cases['body_margin'][generation-1,indices].reshape(-1,2))
                    np.testing.assert_array_equal(current_pass,cases['body_correct'][generation-1,indices].all(axis=-1).ravel())
                    metadata['checks']['current_scores']+=len(body)
                    if generation<32:
                        next_ports=cases['body_ports'][generation,indices].reshape(-1,2,2)
                        next_margin,next_pass,next_all=core.score_ports(next_ports,flat_rules,contract['config']['margin'])
                        np.testing.assert_array_equal(next_all,cases['body_margin'][generation,indices].reshape(-1,2))
                        np.testing.assert_array_equal(next_pass,cases['body_correct'][generation,indices].all(axis=-1).ravel())
                        metadata['checks']['next_scores']+=len(body)
                    for n,condition in enumerate(conditions):
                        pairing,policy=condition.split('/')
                        actual_name='exact' if policy=='exact_rewrite' else 'tolerance'
                        for founder in range(4):
                            for recipient in range(4):
                                i=n*16+founder*4+recipient
                                row=dict(block=block,generation=generation,pairing=pairing,source_writer=policy,
                                    founder=founder,recipient=recipient,rule=float(rules[founder]),
                                    current_margin=float(current_margin[i]),current_pass=int(current_pass[i]),
                                    next_margin=float(next_margin[i]) if generation<32 else '',
                                    next_pass=int(next_pass[i]) if generation<32 else '',
                                    terminal_margin=float(terminal_margin[i]),terminal_pass=int(terminal_pass[i]))
                                row.update({k:float(v[i]) for k,v in values.items()})
                                for key in ('signed_transfer','unsigned_access','conflict_mass'):
                                    row['actual_'+key]=row[actual_name+'_'+key]
                                if writer is None:
                                    writer=csv.DictWriter(target,fieldnames=list(row));writer.writeheader()
                                writer.writerow(row);rows_written+=1
                    metadata['raw_data'].append(dict(path=str(path),sha256=sha(path),read_fields=['end','masks','mean_ports','outgoing','__index__']))
                print(json.dumps(dict(block=block,rows_written=rows_written,elapsed_seconds=round(time.perf_counter()-started,3))),flush=True)
        metadata.update(status='COMPLETE',completed_at_utc=stamp(),rows_written=rows_written,
            elapsed_seconds=time.perf_counter()-started,features_sha256=sha(output/'features.csv'))
        write_json(output/'COMPLETE.json',metadata)
    except BaseException:
        write_json(output/'FAILED.json',dict(status='FAILED',at_utc=stamp(),rows_written=rows_written,traceback=traceback.format_exc()))
        raise
    print(json.dumps(dict(status=metadata['status'],rows=rows_written,seconds=metadata['elapsed_seconds'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--benchmark',action='store_true')
    args=parser.parse_args()
    extract(args.output,args.benchmark)
