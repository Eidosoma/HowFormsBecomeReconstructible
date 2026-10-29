"""D196 bounded saved-state mechanism analysis. No simulator is imported."""

import argparse
import json
import math
import os
from pathlib import Path
import resource
import select
import shutil
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
from . import l22_pulse_mechanism_metrics as metrics
from .l22_yoked_separation import utc, read, digest, verify, arrays, field_hash

WS = Path(__file__).resolve().parents[2]
BASE = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation')
ROOT = BASE/'L22-pulse-mechanism-v1'
OLD = BASE/'L22-recipient-pulse-panel-v1'
OLD_RUN = 'l22_recipient_pulse_v1_panel_attempt1'
DATA, RECEIPTS = OLD/'outputs'/OLD_RUN, OLD/'runs'/OLD_RUN
IDS = {
    OLD/'FREEZE.json': 'ab30dbb2ff78bf9bbe0f58e874d3f68e5b1f231a078394aa3cdd9b4ddcddd2bf',
    RECEIPTS/'MANIFEST.json': '2e96e46776c103d3c220d022752eb5aad3d548e1b8bb787e1034800873115908',
    RECEIPTS/'COMPLETE.json': '91b42f866eb5a59da4af8181f88835572a887d2592b78de87b6182c8243e7a6c',
    DATA/'SUMMARY.json': '75f1e1252bf173ddceb7497c20012caea9a98fa072e0cd38334355b14333739b',
    OLD/'audits/status_2026-10-28_attempt1.json': 'fb0e76efd7008cf0a2874c1d3b430f25b286328e04c49b399b518f0fda70a7d3',
}
CAP, OUTPUT, HEADROOM, QUAL, RESERVE = 128*1024**2, 64*1024**2, 8*1024**2, 16*1024**2, 4*1024**3
SCIENCE = ('L22-active-form/PULSE_MECHANISM_V1.md', 'L22-active-form/RECIPIENT_PULSE_PANEL_RESULTS.md',
    'src/laws_confirmation/l22_pulse_mechanism.py', 'src/laws_confirmation/l22_pulse_mechanism_metrics.py',
    'src/laws_confirmation/l22_yoked_separation.py', 'src/laws_confirmation/l22_yoked_separation_metrics.py',
    'scripts/check_l22_yoked_separation.py', 'scripts/check_l22_pulse_mechanism.py',
    'scripts/qualify_l22_pulse_mechanism.py', 'tests/test_l22_pulse_mechanism.py')
REQUIRED = {'test_complete_extraction', 'test_source_corruption', 'test_score_corruption',
    'test_projection_labels', 'test_four_cell_contrast', 'test_complete_summary',
    'test_summary_corruption', 'test_original_bridge', 'test_no_dynamics_imports',
    'test_resources', 'test_write_once', 'test_budget', 'test_source_receipts',
    'test_freeze_drift', 'test_saved_check', 'test_failure_retained', 'test_launch_startup_only'}
ENV, READY = 'D196_DETACHED', 'D196_READY_FD'


def target(path):
    p = Path(path)
    if ROOT.is_symlink() or ROOT.resolve() not in p.resolve().parents: raise ValueError('external stage only')
    if any(x.is_symlink() for x in (p, *p.parents) if x == ROOT or ROOT in x.parents): raise ValueError('symlink output')
    if p.exists(): raise FileExistsError(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def write(p, value):
    with target(p).open('x') as f: json.dump(value, f, sort_keys=True, allow_nan=False, separators=(',', ':')); f.write('\n')

def save(p, value):
    with target(p).open('xb') as f: np.savez_compressed(f, **value)

def resources(allowance=0):
    assert ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve().is_relative_to(Path('/mnt/bioIce1').resolve())
    assert set(os.sched_getaffinity(0)) == {6} and os.getpriority(os.PRIO_PROCESS, 0) >= 10
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'): assert os.environ.get(k) == '1'
    for k in ('TMPDIR', 'XDG_CACHE_HOME'): assert Path(os.environ[k]).resolve().is_relative_to(ROOT.resolve())
    for p in ROOT.rglob('*'):
        if p.is_symlink():
            parts = p.relative_to(ROOT).parts
            assert len(parts) >= 4 and parts[0] == 'qualification' and parts[1].startswith('workflow_attempt') and parts[2] == 'fixtures'
            assert p.resolve().is_relative_to((ROOT/'qualification'/parts[1]/'fixtures').resolve())
    size = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert size+allowance+HEADROOM < CAP and shutil.disk_usage(ROOT).free >= RESERVE+allowance+HEADROOM
    return dict(bytes=size, cap_bytes=CAP, reserved_bytes=allowance, headroom_bytes=HEADROOM,
        free_volume_reserve_bytes=RESERVE, workers=1, numerical_threads=1, affinity=[6], nice=os.getpriority(os.PRIO_PROCESS, 0))

def source_evidence():
    verify(IDS); f, d = read(OLD/'FREEZE.json'), read(RECEIPTS/'COMPLETE.json')
    m = read(RECEIPTS/'MANIFEST.json')
    assert d['status'] == 'COMPLETE' and d['verification']['passes'] and not (RECEIPTS/'FAILED.json').exists()
    assert d['freeze_sha256'] == m['freeze_sha256'] == digest(OLD/'FREEZE.json')
    assert d['manifest_sha256'] == digest(RECEIPTS/'MANIFEST.json') and d['summary_sha256'] == digest(DATA/'SUMMARY.json')
    assert len(f['inputs']) == 34673 and len(d['output_sha256']) == 981
    assert f['blocks'] == list(metrics.BLOCKS)
    assert set(d['output_sha256']) == {str(p) for p in DATA.rglob('*') if p.is_file()}
    assert set(d['block_receipts_sha256']) == {str(RECEIPTS/f'BLOCK_{i}.json') for i in metrics.BLOCKS}
    values = f['inputs'] | d['output_sha256'] | d['block_receipts_sha256'] | {str(p): h for p, h in IDS.items()}
    verify(values)
    for i in metrics.BLOCKS:
        r, c = read(RECEIPTS/f'BLOCK_{i}.json'), read(DATA/f'tissue_{i}'/'CHECK.json')
        assert r['status'] == 'COMPLETE' and r['index'] == i and r['verification']['passes'] and r['full_replay'] == c
        assert r['freeze_sha256'] == digest(OLD/'FREEZE.json') and c['passes'] and c['index'] == i
        assert r['verification']['donor_barrier_verified'] and c['records'] == 16 and c['repair_paths'] == 32
        assert set(r['output_sha256']) == {str(p) for p in (DATA/f'tissue_{i}').rglob('*') if p.is_file()}
        assert all(d['output_sha256'][p] == h for p, h in r['output_sha256'].items())
    audit = read(OLD/'audits/status_2026-10-28_attempt1.json')
    assert audit['status'] == 'SAVED_CHECK_PASSED' and audit['verification'] == d['verification']
    assert audit['complete_sha256'] == digest(RECEIPTS/'COMPLETE.json') and audit['new_dynamics'] == 0
    return values

def load_family(directory, family, parents=4, draws=4):
    assert family in metrics.FAMILIES
    packets = arrays(directory/'packets.npz'); assert len(packets) == 37
    codes = arrays(directory/'source/original.npz')['codes']
    traces, raws, readers, records = {}, {}, {}, {}
    for role in metrics.ROLES:
        name = f'{family}__{role}__LL'
        traces[role] = arrays(directory/'traces'/(name+'.npz'))['reference']
        header = read(directory/'traces'/(name+'.json'))
        assert header['packet'] == family and header['stream'] == role and header['frame_count'] == 1001
        assert header['frames_sha256'] == field_hash(traces[role])
        raws[role], readers[role], records[role] = {}, {}, {}
        metadata = {}
        for arm in metrics.ARMS:
            name = f'{family}__{role}__{arm}'; raw = arrays(directory/'repairs'/(name+'.npz'))
            meta = read(directory/'repairs'/(name+'.json')); metadata[arm] = meta
            assert meta['spec'] == dict(packet=family,kind=arm) and meta['index'] == header['index'] and meta['stream'] == role
            assert meta['body_theta_fixed'] and not meta['body_free'] and meta['body_sweeps'] == 1000 and meta['writer_sweeps'] == 1000
            enabled = arm.endswith('_pulse')
            assert meta['pulse'] == dict(enabled=enabled,step=501 if enabled else None,rows=[4,12],columns=[4,12],operation='sign_inversion_V_only',random_draws=0)
            np.testing.assert_array_equal(packets[name],raw['s1000_theta']); raws[role][arm] = raw
        assert len({v['rng_final'] for v in metadata.values()}) == 1
        assert len({v['snapshot_sha256'] for v in metadata.values()}) == 1
        for future in metrics.FUTURES:
            mapping,saved=read(directory/future/'read_map.json'),read(directory/future/'records.json')
            assert len(mapping)==len(saved)==37
            readers[role][future],records[role][future]={},{};births=[]
            for arm in metrics.ARMS:
                name=f'{family}__{role}__{arm}';link=mapping[name]
                assert link['packet_sha256']==field_hash(packets[name]) and link['disabled'] is False
                assert Path(link['assay']).name==link['assay']
                path=directory/future/(link['assay']+'.npz');raw=arrays(path);meta=read(path.with_suffix('.json'))
                births.append(meta['birth_rng_final'])
                np.testing.assert_array_equal(raw['s0_theta'],np.repeat(packets[name],draws,axis=0))
                readers[role][future][arm],records[role][future][arm]=raw,saved[name]
            assert all(b==births[0] for b in births)
    return dict(traces=traces,raws=raws,readers=readers,records=records,codes=codes)


def bridge_original(result, original):
    assert original['blocks']==list(metrics.BLOCKS) and original['records']==result['records']
    c=metrics.checker()
    for family in metrics.FAMILIES:
        for future,prior in [*original['by_future'].items(),('both',original['new_only'])]:
            for role,view in [*prior['by_role'].items(),('role_mean',prior['role_mean'])]:
                for section,names,old_section in [('behavior',metrics.ARMS,'arms'),('contrast',metrics.CONTRASTS,'contrasts')]:
                    for name in names:
                        current=result['views'][f'{section}|{family}|{role}|{future}|{name}'];oldrow=view[old_section][family+'__'+name]
                        for dimension in ('mean','by_block','by_message','by_block_message','leave_one_block_out'):
                            def select(x):
                                if isinstance(x,dict):return {k:x[k] for k in metrics.BEHAVIOR[:4]}
                                return [select(v) for v in x]
                            c.close(select(current[dimension]),select(oldrow[dimension]))
                        if section=='contrast':
                            now=result['transitions'][f'contrast|{family}|{role}|{future}|{name}']
                            c.close(now,{k:oldrow['transitions']['pooled'][k] for k in metrics.BEHAVIOR[:3]})
    return dict(passes=True,original_four_cells_and_five_contrasts_bridged=True,new_dynamics=0)


def test_receipt(path):
    suites = list(ET.parse(path).getroot().iter('testsuite'))
    assert suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped'))
    cases = [x for s in suites for x in s.findall('testcase')]
    assert len(cases) >= 30 and REQUIRED <= {x.get('name').split('[')[0] for x in cases}
    assert not any(list(x.iter(k)) for x in cases for k in ('failure', 'error', 'skipped'))
    return dict(cases=len(cases), seconds=sum(float(s.get('time', 0)) for s in suites), path=str(path), sha256=digest(path))

def qualification(directory):
    assert directory.resolve().is_relative_to((ROOT/'qualification').resolve())
    m, d = read(directory/'MANIFEST.json'), read(directory/'COMPLETE.json')
    assert d['status'] == 'COMPLETE' and d['inputs_unchanged'] and not (directory/'FAILED.json').exists()
    assert d['manifest_sha256'] == digest(directory/'MANIFEST.json')
    verify(m['inputs']); verify(d['artifacts'])
    assert {str(WS/p) for p in SCIENCE} <= set(m['inputs'])
    assert (directory/'tests.xml').stat().st_mtime_ns >= max((WS/p).stat().st_mtime_ns for p in SCIENCE)
    tests = test_receipt(directory/'tests.xml'); assert tests == d['tests']
    b = read(directory/'BENCHMARK.json')
    assert b['passes'] and b['families'] == 1 and b['records'] == 16 and b['new_dynamics'] == 0
    assert math.isfinite(b['seconds']) and b['seconds'] > 0
    return m['inputs'] | d['artifacts'] | {str(directory/'COMPLETE.json'): digest(directory/'COMPLETE.json')}, tests, b

def budget(seconds):
    assert math.isfinite(seconds) and seconds > 0
    allowance = 16*seconds+180
    return dict(full_synthetic_family_seconds=seconds, eight_family_serial_seconds=8*seconds,
                allowance_seconds=allowance, detached_required=allowance > 600,
                guard_seconds=max(550, math.ceil(allowance+60)) if allowance > 600 else 550)

def prepare(directory):
    resources(OUTPUT); assert not (ROOT/'FREEZE.json').exists() and not (ROOT/'outputs').exists()
    q, tests, b = qualification(directory)
    inputs = source_evidence() | q | {str(WS/p): digest(WS/p) for p in SCIENCE}
    assert all(inputs[p] == h for p, h in q.items()); verify(inputs)
    value = dict(schema='d196_saved_pulse_mechanism_freeze_v1', frozen_utc=utc(), inputs=inputs,
        science=list(SCIENCE), blocks=list(metrics.BLOCKS), families=list(metrics.FAMILIES), roles=list(metrics.ROLES),
        futures=list(metrics.FUTURES), times=list(metrics.TIMES), read_times=list(metrics.READ_TIMES),
        pair_fields=list(metrics.FIELDS), behavior_fields=list(metrics.BEHAVIOR), keys=sorted(metrics.specs()),
        tests=tests, budget=budget(b['seconds']), resources=resources(OUTPUT), python=sys.version, numpy=np.__version__,
        retrospective=True, new_dynamics=0, automatic_polling=False, automatic_retry=False, automatic_successor=False)
    write(ROOT/'FREEZE.json', value)
    return dict(status='FROZEN', frozen_utc=value['frozen_utc'], inputs=len(inputs), freeze_sha256=digest(ROOT/'FREEZE.json'),
        tests=tests, budget=value['budget'], resources=value['resources'])

def frozen():
    f = read(ROOT/'FREEZE.json'); verify(f['inputs'])
    assert f['schema'] == 'd196_saved_pulse_mechanism_freeze_v1' and f['science'] == list(SCIENCE)
    for k, wanted in (('blocks', metrics.BLOCKS), ('families', metrics.FAMILIES), ('roles', metrics.ROLES),
                      ('futures', metrics.FUTURES), ('times', metrics.TIMES), ('read_times', metrics.READ_TIMES),
                      ('pair_fields', metrics.FIELDS), ('behavior_fields', metrics.BEHAVIOR)):
        assert f[k] == list(wanted)
    assert f['keys'] == sorted(metrics.specs()) and f['budget'] == budget(f['budget']['full_synthetic_family_seconds'])
    assert f['python'] == sys.version and f['numpy'] == np.__version__ and f['resources']['cap_bytes'] == CAP
    assert f['retrospective'] and f['new_dynamics'] == 0
    assert all(f[k] is False for k in ('automatic_polling', 'automatic_retry', 'automatic_successor'))
    return f

def saved_check():
    blocks={i:arrays(ROOT/'outputs'/f'tissue_{i}.npz') for i in metrics.BLOCKS}
    value=read(ROOT/'outputs/SUMMARY.json')
    for data in blocks.values():metrics.validate(data)
    assert metrics.summary(blocks)==value
    checked=metrics.checker().summary(blocks,value);checked.update(bridge_original(value,read(DATA/'SUMMARY.json')))
    assert {p.name for p in (ROOT/'outputs').iterdir()} == {'SUMMARY.json','CHECK.json'} | {f'tissue_{i}.npz' for i in metrics.BLOCKS}
    proof=read(ROOT/'outputs/CHECK.json')
    assert proof['passes'] and set(proof['blocks'])=={str(i) for i in metrics.BLOCKS}
    for block in proof['blocks'].values():
        assert set(block)==set(metrics.FAMILIES)
        for family,p in block.items():
            selected={k:v for k,v in metrics.specs().items() if k.split('|')[1]==family}
            pair_rows=sum(int(np.prod(shape[:-1])) for k,(shape,_) in selected.items() if k.split('|')[0] in ('chain','event_route','event','reader'))
            projection_rows=sum(shape[0] for k,(shape,_) in selected.items() if 'projection' in k.split('|')[0])
            assert p['passes'] and p['new_dynamics']==0 and p['scalar_max_error']<=2e-12
            assert p['field_pairs']==pair_rows and p['projection_rows']==projection_rows and p['score_rows']==1024
    return checked | dict(outputs=6,records=64,source_dynamics_advanced=0)


def run():
    f = frozen(); resources(OUTPUT)
    assert not any((ROOT/p).exists() for p in ('outputs', 'MANIFEST.json', 'COMPLETE.json', 'FAILED.json'))
    if f['budget']['detached_required']: assert os.environ.get(ENV) == '1' and os.getsid(0) == os.getpid()
    started = time.monotonic(); write(ROOT/'MANIFEST.json', dict(started_utc=utc(), freeze_sha256=digest(ROOT/'FREEZE.json'), new_dynamics=0))
    fd = os.environ.pop(READY, None)
    if fd is not None: os.write(int(fd), b'READY\n'); os.close(int(fd))
    target(ROOT/'outputs/SUMMARY.json')
    def guard():
        if time.monotonic()-started > f['budget']['guard_seconds']: raise TimeoutError('bounded saved analysis; retain evidence')
    try:
        proof = {}
        for i in metrics.BLOCKS:
            derived, checks = {}, {}
            for family in metrics.FAMILIES:
                bundle = load_family(DATA/f'tissue_{i}', family)
                values, checks[family] = metrics.extract(bundle, family, guard=guard)
                derived.update(values); del bundle, values
            metrics.validate(derived)
            save(ROOT/'outputs'/f'tissue_{i}.npz', derived)
            reloaded = arrays(ROOT/'outputs'/f'tissue_{i}.npz')
            for k in derived: np.testing.assert_array_equal(derived[k], reloaded[k])
            proof[str(i)] = checks; del derived, reloaded
            resources(); guard(); print(json.dumps(dict(stage='block_checked', index=i, seconds=time.monotonic()-started)), flush=True)
        blocks = {i: arrays(ROOT/'outputs'/f'tissue_{i}.npz') for i in metrics.BLOCKS}
        value = metrics.summary(blocks); metrics.checker().summary(blocks, value)
        bridge_original(value, read(DATA/'SUMMARY.json'))
        write(ROOT/'outputs/SUMMARY.json', value)
        write(ROOT/'outputs/CHECK.json', dict(passes=True, blocks=proof, new_dynamics=0))
        checked = saved_check(); frozen(); resources(); guard()
        done = dict(status='COMPLETE', completed_utc=utc(), seconds=time.monotonic()-started,
            freeze_sha256=digest(ROOT/'FREEZE.json'), manifest_sha256=digest(ROOT/'MANIFEST.json'),
            summary_sha256=digest(ROOT/'outputs/SUMMARY.json'), verification=checked,
            output_sha256={str(p): digest(p) for p in (ROOT/'outputs').iterdir()},
            resources=resources(), peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            new_dynamics=0, retrospective=True, fitted_models=0, automatic_polling=False, automatic_retry=False, automatic_successor=False)
        write(ROOT/'COMPLETE.json', done)
        return done
    except Exception:
        write(ROOT/'FAILED.json', dict(status='FAILED', failed_utc=utc(), traceback=traceback.format_exc(),
                                      retained=True, automatic_retry=False, automatic_successor=False)); raise

def audit():
    resources(); frozen(); d = read(ROOT/'COMPLETE.json')
    assert d['status'] == 'COMPLETE' and not (ROOT/'FAILED.json').exists()
    assert d['freeze_sha256'] == read(ROOT/'MANIFEST.json')['freeze_sha256'] == digest(ROOT/'FREEZE.json')
    assert d['manifest_sha256'] == digest(ROOT/'MANIFEST.json') and d['summary_sha256'] == digest(ROOT/'outputs/SUMMARY.json')
    verify(d['output_sha256']); assert set(d['output_sha256']) == {str(p) for p in (ROOT/'outputs').iterdir()}
    checked = saved_check(); assert checked == d['verification']
    result = dict(status='SAVED_CHECK_PASSED', checked_utc=utc(), complete_sha256=digest(ROOT/'COMPLETE.json'), **checked)
    write(ROOT/'SAVED_CHECK.json', result)
    return result

def launch():
    f = frozen(); resources(OUTPUT)
    assert not any((ROOT/p).exists() for p in ('MANIFEST.json', 'outputs', 'logs/run.log', 'logs/launch.json'))
    rd, wr = os.pipe()
    try:
        with target(ROOT/'logs/run.log').open('xb') as out:
            p = subprocess.Popen([sys.executable, '-u', '-m', 'laws_confirmation.l22_pulse_mechanism', '--run'],
                stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, cwd=WS, start_new_session=True,
                env=dict(os.environ, **{ENV: '1', READY: str(wr)}), pass_fds=(wr,))
    finally: os.close(wr)
    ready = select.select([rd], [], [], 30)[0]; message = os.read(rd, 64) if ready else b''; os.close(rd)
    result = dict(status='DETACHED_STARTED' if message == b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        acknowledged_utc=utc(), pid=p.pid, budget=f['budget'], workers=1, affinity=[6], nice=10,
        automatic_polling=False, automatic_retry=False, automatic_successor=False)
    write(ROOT/'logs/launch.json', result); return result

def main():
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--prepare', type=Path); g.add_argument('--run', action='store_true')
    g.add_argument('--audit', action='store_true'); g.add_argument('--launch', action='store_true')
    a = p.parse_args(); result = prepare(a.prepare.resolve()) if a.prepare else audit() if a.audit else launch() if a.launch else run()
    print(json.dumps(result, sort_keys=True), flush=True)

if __name__ == '__main__': main()
