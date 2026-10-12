from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_active_form_pilot_panel as panel

b, model = panel.benchmark, panel.model


@pytest.fixture(scope='module')
def miniature(tmp_path_factory):
    root = tmp_path_factory.mktemp('panel_miniature')
    cfg = replace(model.CONFIG, replicates=1, settle=3, imprint=6, sweeps=4, times=(0,1,4))
    rcfg = replace(model.READOUT, parents=1, draws=2, sweeps=4, times=(0,1,4))
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(b,'ROOT',root)
        patch.setattr(panel,'ROOT',root)
        old = b.run_block(root/'benchmark',model.DISPOSABLE,cfg,rcfg)
        new = panel.run_block(root/'panel',model.DISPOSABLE,cfg,rcfg)
    return SimpleNamespace(root=root,old=old,new=new,cfg=cfg,rcfg=rcfg)


def test_workflow_matches_frozen_benchmark():
    assert panel.workflow_equivalence()['remaining_workflow_exact']
    assert model.BLOCKS == (30056,30057,30058,30059)
    assert panel.CPUS == (0,1,2,3)


def test_miniature_panel_matches_benchmark(miniature):
    e = miniature
    before, after = deepcopy(e.old), deepcopy(e.new)
    before.pop('seconds'); after.pop('seconds')
    assert before == after
    for p in (e.root/'benchmark').glob('*.npz'):
        old, new = b.arrays(p), b.arrays(e.root/'panel'/p.name)
        assert set(old) == set(new)
        for key in old: b.checker().exact(old[key],new[key])
    for name in ('records.json','contrasts.json','read_map.json'):
        assert json.loads((e.root/'benchmark'/name).read_text()) == json.loads((e.root/'panel'/name).read_text())
    assert panel.saved_check(e.root/'panel',model.DISPOSABLE,e.cfg,e.rcfg)['passes']


@pytest.mark.parametrize('kind', ['role','config','replay','count','alias_count','control','map_hash',
                                  'map_flag','map_alias','arm','label','score','contrast','initial',
                                  'packet','final_theta','packet_output','extra_file','missing_file'])
def test_saved_panel_tampering_rejected(miniature, tmp_path, kind):
    # Fixtures are disposable; copying and deliberate corruption are test data.
    import shutil
    e=miniature
    directory=tmp_path/'tampered'
    shutil.copytree(e.root/'panel',directory)
    filename='CHECK.json'
    value=json.loads((directory/filename).read_text())
    if kind=='role': value['source_role']='confirmation'
    elif kind=='config': value['config']['sweeps']+=1
    elif kind=='replay': value['repair_checks']['common__own__live']['native_state_max_abs']=.1
    elif kind=='count': value['records']+=1
    elif kind=='alias_count': value['exact_alias_checks']-=1
    elif kind=='control': value['positive_control_accuracy_by_message']['intact_parent'][0]+=.1
    elif kind in ('map_hash','map_flag','map_alias'):
        filename='read_map.json';value=json.loads((directory/filename).read_text())
        if kind=='map_hash': value['reader_off']['packet_sha256']='bad'
        elif kind=='map_flag': value['reader_off']['disabled']=False
        else: value['reader_off']['assay']=value['input__common']['assay']
    elif kind in ('arm','label','score'):
        filename='records.json';value=json.loads((directory/filename).read_text())
        if kind=='arm': value.pop('common__own__live')
        elif kind=='label': value['common__own__live'][0]['message']=3
        else: value['common__own__live'][0]['preference']+=.1
    elif kind=='contrast':
        filename='contrasts.json';value=json.loads((directory/filename).read_text())
        value['common__source']['right']='common__own__live'
    elif kind in ('initial','packet_output'):
        filename='repair_common__own__live.npz';value=b.arrays(directory/filename)
        value['s0_R' if kind=='initial' else 's4_theta'].flat[0]+=.1
    elif kind=='packet':
        filename='packets.npz';value=b.arrays(directory/filename);value['common__own__live'].flat[0]+=.1
    elif kind=='final_theta':
        mapping=json.loads((directory/'read_map.json').read_text())
        filename=mapping['common__own__live']['assay']+'.npz';value=b.arrays(directory/filename)
        value['s4_theta'].flat[0]+=.1
    elif kind=='extra_file': (directory/'extra.txt').write_text('undeclared')
    elif kind=='missing_file': (directory/'before.npz').unlink()
    if kind not in ('extra_file','missing_file'):
        if filename.endswith('.npz'):
            with (directory/filename).open('wb') as out: np.savez_compressed(out,**value)
        else: (directory/filename).write_text(json.dumps(value))
    with pytest.raises((AssertionError,KeyError,FileNotFoundError)):
        panel.saved_check(directory,model.DISPOSABLE,e.cfg,e.rcfg)


@pytest.mark.parametrize('kind', ['parent','original','boundary','keys'])
def test_source_identity_rejects_change(miniature, monkeypatch, kind):
    e=miniature
    values=[b.arrays(e.root/'panel'/(n+'.npz')) for n in ('parent','original','boundary')]
    def load(path):
        if path.name=='parent.npz': return values[0]
        return values[2] if panel.boundary_run.RUN_ID in str(path) else values[1]
    monkeypatch.setattr(panel,'arrays',load)
    panel.source_same(model.BLOCKS[0],*values)
    changed=deepcopy(values)
    if kind=='keys': changed[0]['secret']=np.zeros(1)
    else: next(iter(changed[('parent','original','boundary').index(kind)].values())).flat[0]+=.1
    with pytest.raises(AssertionError): panel.source_same(model.BLOCKS[0],*changed)


def test_no_partial_panel_summary():
    with pytest.raises(AssertionError): panel.panel_summary({})
    with pytest.raises(AssertionError): panel.panel_summary({model.BLOCKS[0]:None})


def test_full_descriptive_summary_and_record_addresses():
    arms={name:dict(accuracy=.5,partner_accuracy=.25,preference=.25,projection_gap=.2,
        sign_fidelity=.6,theta_corr_parent=.3,theta_corr_partner=.2) for name in model.plan()}
    for packet in ('common','residual'):
        for body in model.boundary.BODIES: arms[f'{packet}__{body}__average']=dict(next(iter(arms.values())))
    for name in ('input__common','input__residual','intact_parent','supplied_positive','reader_off'):
        arms[name]=dict(next(iter(arms.values())))
    data={}
    for index in model.BLOCKS:
        records={name:[dict(world=i,message=i//4,replicate=i%4,**value) for i in range(16)] for name,value in arms.items()}
        proof={'positive_control_accuracy_by_message':{'reader_off':[.25]*4}}
        meta={name:dict(body_and_native_writer_seconds=1.,averaging_writer_seconds=.1) for name in model.plan()}
        data[index]=(records,model.comparisons(records),proof,meta)
    report=panel.panel_summary(data)
    assert report['records']==64 and len(report['arm_summaries'])==51
    assert len(report['equal_block_contrasts'])==20 and len(report['block_contrasts'])==4
    assert report['confirmation'] is report['serial_renewal'] is report['automatic_successor'] is False
    for item in report['equal_block_contrasts'].values():
        assert all(v==0 for v in item['mean'].values())
    data[model.BLOCKS[0]][0]['input__common'][0]['replicate']=2
    with pytest.raises(AssertionError): panel.panel_summary(data)


@pytest.mark.parametrize('index,cpu', [(model.DISPOSABLE,0),(30060,0),(30056,1),(30057,0),(True,0)])
def test_worker_rejects_undeclared_assignments(index,cpu):
    with pytest.raises(ValueError): panel.worker(index,cpu)


def test_production_worker_requires_detached_stage(monkeypatch):
    monkeypatch.delenv(panel.ENV,raising=False)
    with pytest.raises(AssertionError): panel.worker(model.BLOCKS[0],0)
    with pytest.raises(AssertionError): panel.execute()


def test_resource_bound_and_measured_timing():
    budget=panel.budget(dict(completed_utc='2026-10-12T13:34:07.669752+00:00',uncompressed_array_bytes=97775744),
        dict(started_utc='2026-10-12T13:29:32.761347+00:00'))
    assert budget['measured_benchmark_seconds']==274.908405
    assert budget['storage_upper_bound_bytes']==540409856
    assert budget['detached_allowance_seconds']>600
    assert budget['workers']==4 and budget['numerical_threads']==1


@pytest.mark.parametrize('kind',['capacity','reserve','affinity'])
def test_panel_resources_fail_closed(monkeypatch,kind):
    monkeypatch.setattr(b,'resources',lambda:dict(bytes=0,affinity=[0]))
    monkeypatch.setattr(b.shutil,'disk_usage',lambda _:SimpleNamespace(free=100*1024**3))
    if kind=='capacity':
        with pytest.raises(AssertionError): panel.resources(b.CAP)
    elif kind=='reserve':
        monkeypatch.setattr(b.shutil,'disk_usage',lambda _:SimpleNamespace(free=b.RESERVE))
        with pytest.raises(AssertionError): panel.resources()
    else:
        monkeypatch.setattr(b,'resources',lambda:dict(bytes=0,affinity=[5]))
        with pytest.raises(AssertionError): panel.resources()


def test_panel_launch_acknowledges_only(tmp_path,monkeypatch):
    monkeypatch.setattr(panel,'ROOT',tmp_path);monkeypatch.setattr(b,'ROOT',tmp_path)
    f={'budget':{'storage_upper_bound_bytes':1,'detached_allowance_seconds':730}}
    monkeypatch.setattr(panel,'frozen',lambda:f)
    monkeypatch.setattr(panel,'resources',lambda allowance=0:dict(bytes=0))
    monkeypatch.setattr(panel.os,'sched_getaffinity',lambda _:{0,1,2,3})
    b.write_json(panel.freeze_path(),f)
    captured={}
    def spawn(args,**kwargs):
        captured.update(kwargs)
        os.write(int(kwargs['env'][panel.READY]),b'READY\n')
        return SimpleNamespace(pid=123456)
    monkeypatch.setattr(panel.subprocess,'Popen',spawn)
    result=panel.launch()
    assert result['status']=='DETACHED_STARTED' and result['workers']==4
    assert result['automatic_polling'] is result['automatic_retry'] is result['automatic_successor'] is False
    assert captured['start_new_session'] and captured['env'][panel.ENV]=='panel'
    assert not (tmp_path/'runs'/panel.RUN).exists()
    with pytest.raises(AssertionError): panel.launch()


def test_panel_has_no_scientific_cli_knobs():
    source=Path(panel.__file__).read_text()
    assert "group.add_argument('--prepare'" in source
    assert "group.add_argument('--launch'" in source
    assert "group.add_argument('--execute'" in source
    assert 'add_argument(\'--blocks' not in source
    assert 'add_argument(\'--sweeps' not in source

