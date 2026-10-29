"""D197 fresh pulse founders: qualification, fixed design, timing and detached panel."""

import argparse
from dataclasses import asdict
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
from . import l22_pulse_founders_block as block
from . import l22_pulse_founders_analysis as analysis
from . import l22_recipient_pulse_panel as previous
from . import l22_recipient_pulse_benchmark as benchmark
from . import l22_pulse_mechanism as diagnostic
from .io import canonical_digest,sha256_file,utc_now

model,WS,BASE,ROOT=block.model,block.WS,block.BASE,block.ROOT
BLOCKS,FUTURES=block.BLOCKS,block.FUTURES
CAP,HEADROOM,RESERVE=4*1024**3,64*1024**2,4*1024**3
BLOCK_BOUND,EXTRA_BOUND,QUAL_BOUND=512*1024**2,64*1024**2,512*1024**2
BOUND=4*BLOCK_BOUND+EXTRA_BOUND
ENV,READY='D197_STAGE','D197_READY_FD'
BENCHMARK_ALLOWANCE,BENCHMARK_GUARD=330,550
SCIENCE=(*previous.SCIENCE,'L22-active-form/PULSE_FOUNDERS_V1.md',
    'L22-active-form/PULSE_MECHANISM_V1.md','L22-active-form/PULSE_MECHANISM_RESULTS.md',
    'src/laws_confirmation/l22_pulse_founders.py','src/laws_confirmation/l22_pulse_founders_block.py',
    'src/laws_confirmation/l22_pulse_founders_analysis.py','scripts/check_l22_pulse_founders.py',
    'scripts/qualify_l22_pulse_founders.py','tests/test_l22_pulse_founders.py',
    'src/laws_confirmation/l22_yoked_separation_metrics.py','scripts/check_l22_yoked_separation.py')
TESTS=(*previous.TESTS,'tests/test_l22_pulse_founders.py')
REQUIRED=previous.REQUIRED | {'test_d197_admission','test_d197_source_gate','test_d197_exact_bridge',
    'test_d197_workflow_identity','test_d197_saved_no_dynamics','test_d197_saved_corruption',
    'test_d197_secondary_scores','test_d197_secondary_corruption','test_d197_primary_relabel',
    'test_d197_margin_aggregate','test_d197_margin_corruption','test_d197_resources','test_d197_design_freeze',
    'test_d197_budget','test_d197_failure_retained','test_d197_launch_startup_only','test_d197_write_once',
    'test_d197_execution_seal','test_d197_saved_stage','test_d197_stage_order','test_d197_bound'}
read,arrays,verify=block.read,block.arrays,block.verify


def target(path):
    if block.ROOT != ROOT: raise RuntimeError('block/executor roots diverged')
    return block.target(path)

def write(path, value):
    target(path); block.write(path, value)

def resources(allowance=0):
    assert ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve().is_relative_to(Path('/mnt/bioIce1').resolve())
    assert set(os.sched_getaffinity(0)) == {6} and os.getpriority(os.PRIO_PROCESS, 0) >= 10
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    for n in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        assert os.environ.get(n) == '1', n
    for n in ('TMPDIR', 'XDG_CACHE_HOME'):
        assert Path(os.environ[n]).resolve().is_relative_to(ROOT.resolve()), n
    for p in ROOT.rglob('*'):
        if p.is_symlink():
            parts = p.relative_to(ROOT).parts
            # Pytest keeps "current" aliases and our negative tests deliberately
            # construct links. They are retained evidence, never execution paths.
            assert len(parts) >= 4 and parts[0] == 'qualification'
            assert parts[1].startswith('workflow_attempt') and parts[2] == 'fixtures'
            fixture_root = ROOT/'qualification'/parts[1]/'fixtures'
            assert p.resolve().is_relative_to(fixture_root.resolve())
    size = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert size+allowance+HEADROOM < CAP
    assert shutil.disk_usage(ROOT).free >= RESERVE+allowance+HEADROOM
    return dict(bytes=size, cap_bytes=CAP, reserved_output_bytes=allowance, headroom_bytes=HEADROOM,
        free_volume_reserve_bytes=RESERVE, workers=1, numerical_threads=1, affinity=[6], nice=os.getpriority(os.PRIO_PROCESS, 0))

def storage_bound():
    prior=benchmark.storage_bound();per=prior['total']+16*1024**2
    assert per<BLOCK_BOUND
    return dict(original_per_block=prior,secondary_allowance_per_block=16*1024**2,per_block=per,
        blocks=4,total=4*per+EXTRA_BOUND)


def imported_paths():
    block.checker();model.source.api();analysis.geometry.checker()
    return previous.imported_paths() | {WS/n for n in SCIENCE if n.endswith('.py')}


def prior_evidence():
    identities={str(diagnostic.ROOT/'FREEZE.json'):'734b2eeff5c307d9b757c689a22379ec9be681779bddd6850fc190264ef0a982',
        str(diagnostic.ROOT/'COMPLETE.json'):'d4b5d8d119d04102bac0186d58df7c3d05bee1ba2ec66d588971c694c1464a4c',
        str(diagnostic.ROOT/'MANIFEST.json'):'ca04d51729d4f4645b8f57a90689f745e2cd81b62691e5ac9b175c350d032fa7',
        str(diagnostic.ROOT/'outputs/SUMMARY.json'):'c1d6c9f43cdb82e95586bff0d3bc2dbd40dd62679d66af897b7fddb7c34d8304',
        str(diagnostic.ROOT/'SAVED_CHECK.json'):'f0cfda4fca431addc794686fd7a2f94c796ff22e89e804d0d9436c0b0d1551d5'}
    verify(identities);f=read(diagnostic.ROOT/'FREEZE.json');d=read(diagnostic.ROOT/'COMPLETE.json');a=read(diagnostic.ROOT/'SAVED_CHECK.json')
    assert d['status']=='COMPLETE' and d['verification']['passes'] and a['status']=='SAVED_CHECK_PASSED' and a['passes']
    assert a['complete_sha256']==sha256_file(diagnostic.ROOT/'COMPLETE.json')
    assert d['freeze_sha256']==sha256_file(diagnostic.ROOT/'FREEZE.json')
    assert d['manifest_sha256']==sha256_file(diagnostic.ROOT/'MANIFEST.json')
    assert d['summary_sha256']==sha256_file(diagnostic.ROOT/'outputs/SUMMARY.json')
    assert set(d['output_sha256'])=={str(p) for p in (diagnostic.ROOT/'outputs').iterdir()}
    values=f['inputs'] | d['output_sha256'] | identities;verify(values);return values


def test_receipt(xml):
    assert xml.resolve().is_relative_to(ROOT.resolve())
    suites = list(ET.parse(xml).getroot().iter('testsuite'))
    assert suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped'))
    cases = [c for s in suites for c in s.findall('testcase')]
    assert len(cases) == sum(int(s.get('tests', 0)) for s in suites) and len(cases) >= 300
    assert REQUIRED <= {c.get('name').split('[')[0] for c in cases}
    assert not any(list(c.iter(k)) for c in cases for k in ('failure', 'error', 'skipped'))
    return dict(path=str(xml), sha256=sha256_file(xml), cases=len(cases), seconds=sum(float(s.get('time', 0)) for s in suites))

def qualification_evidence(directory):
    assert directory.resolve().is_relative_to((ROOT/'qualification').resolve())
    assert (directory/'COMPLETE.json').exists() and not (directory/'FAILED.json').exists()
    m, d = read(directory/'MANIFEST.json'), read(directory/'COMPLETE.json')
    assert d['status'] == 'COMPLETE' and d['inputs_unchanged'] and d['main_cohort_started'] is False
    assert d['manifest_sha256'] == sha256_file(directory/'MANIFEST.json')
    verify(m['inputs']); verify(d['artifacts'])
    tests = test_receipt(directory/'tests.xml'); assert tests == d['tests']
    paths = imported_paths() | {WS/n for n in SCIENCE}
    assert {str(p) for p in paths} <= set(m['inputs'])
    assert (directory/'tests.xml').stat().st_mtime_ns >= max(p.stat().st_mtime_ns for p in paths)
    inputs = m['inputs'] | d['artifacts'] | {str(directory/n): sha256_file(directory/n) for n in ('MANIFEST.json', 'COMPLETE.json')}
    return inputs, tests

def design():
    return dict(schema='d197_fresh_pulse_design_v1',blocks=list(BLOCKS),disposable=block.DISPOSABLE,
        qualification=block.QUALIFICATION,config=asdict(block.CONFIG),readout_config=asdict(block.READOUT),
        pulse=model.pulse_contract(block.CONFIG,True),futures=list(FUTURES),roles=list(block.ROLES),
        paths={n:dict(stream=r,**asdict(spec)) for n,(r,spec) in block.paths().items()},
        packets=list(block.packet_names()),comparisons=model.comparisons(),
        primary='own_minus_partner_preference_interaction',secondary='target_minus_strongest_other_margin_interaction',
        benchmark_excluded=True,prospective=True,confirmatory=False,source_regenerated=True,
        automatic_polling=False,automatic_retry=False,automatic_successor=False,
        analytical_bound=storage_bound(),cap_bytes=CAP,python=sys.version,numpy=np.__version__)


def prepare(directory):
    resources(BOUND+BLOCK_BOUND);assert not (ROOT/'FREEZE.json').exists() and not (ROOT/'outputs').exists()
    q,tests=qualification_evidence(directory);fresh=read(ROOT/'FRESHNESS.json')
    assert fresh['indices']==[*BLOCKS,block.DISPOSABLE] and fresh['visible_path_hits']==[]
    assert fresh['main_sources_generated']==0 and fresh['benchmark_source_generated'] is False
    inputs=prior_evidence() | q | {str(p):sha256_file(p) for p in imported_paths() | {WS/n for n in SCIENCE}}
    assert all(inputs[p]==h for p,h in q.items())
    inputs[str(ROOT/'FRESHNESS.json')]=sha256_file(ROOT/'FRESHNESS.json');verify(inputs)
    value=dict(frozen_utc=utc_now(),design=design(),inputs=inputs,tests=tests,
        imported_repository_modules=sorted(map(str,imported_paths())),resources=resources(BOUND+BLOCK_BOUND))
    write(ROOT/'FREEZE.json',value)
    return dict(status='DESIGN_FROZEN',frozen_utc=value['frozen_utc'],freeze_sha256=sha256_file(ROOT/'FREEZE.json'),
        inputs=len(inputs),modules=len(value['imported_repository_modules']),tests=tests,design=value['design'],resources=value['resources'])


def frozen():
    f=read(ROOT/'FREEZE.json');verify(f['inputs']);assert canonical_digest(f['design'])==canonical_digest(design())
    assert set(f['imported_repository_modules'])==set(map(str,imported_paths()))
    assert set(f['imported_repository_modules'])<=set(f['inputs'])
    return f


def budget(seconds):
    assert np.isfinite(seconds) and seconds>0
    return dict(benchmark_seconds=seconds,serial_reference_seconds=4*seconds,
        allowance_seconds=8*seconds+180,detached_required=8*seconds+180>600)


def stage_ids(stage):
    if stage=='benchmark':return (block.DISPOSABLE,)
    if stage=='panel':return BLOCKS
    raise ValueError('declared benchmark or panel')


def paths(stage):return ROOT/'runs'/stage,ROOT/'outputs'/stage


def saved_stage(stage,cfg=block.CONFIG,rcfg=block.READOUT):
    ids=stage_ids(stage);rd,od=paths(stage);count=0
    assert {p.name for p in (od/'physical').iterdir()}=={f'tissue_{i}' for i in ids}
    assert {p.name for p in (od/'secondary').iterdir()}=={f'tissue_{i}' for i in ids}
    expected_top={'physical','secondary','PRIMARY.json'} | ({'MARGINS.json'} if stage=='panel' else set())
    assert {p.name for p in od.iterdir()}==expected_top
    for index in ids:
        d,s=od/'physical'/f'tissue_{index}',od/'secondary'/f'tissue_{index}'
        receipt=read(rd/f'BLOCK_{index}.json');assert receipt['status']=='COMPLETE' and receipt['index']==index
        assert receipt['freeze_sha256']==sha256_file(ROOT/'FREEZE.json') and receipt['full_replay']==read(d/'CHECK.json')
        verify(receipt['output_sha256'])
        assert set(receipt['output_sha256'])=={str(p) for base in (d,s) for p in base.rglob('*') if p.is_file()}
        checked=block.saved_check(d,index,cfg,rcfg);assert receipt['verification']==checked
        margins,proof=analysis.extract_margins(d,index,cfg,rcfg)
        assert proof==read(s/'CHECK.json')==receipt['secondary_verification']
        assert {p.name for p in s.iterdir()}=={f+'.npz' for f in FUTURES}|{'CHECK.json'}
        for future in FUTURES:
            loaded=arrays(s/(future+'.npz'));assert set(loaded)==set(margins[future])
            for name,a in margins[future].items():np.testing.assert_array_equal(loaded[name],a)
        count+=len(receipt['output_sha256'])
    if stage=='panel':
        primary=analysis.primary(analysis.load_primary(od/'physical'),cfg.replicates,rcfg.draws)
        margin=analysis.margins(analysis.load_margins(od/'secondary'),cfg.replicates,rcfg.draws)
        assert primary==read(od/'PRIMARY.json') and margin==read(od/'MARGINS.json');count+=2
    else:
        assert read(od/'PRIMARY.json')==read(od/'physical'/f'tissue_{block.DISPOSABLE}'/'SUMMARY.json');count+=1
    return dict(passes=True,stage=stage,blocks=len(ids),records=4*cfg.replicates*len(ids),
        physical_paths=32*len(ids),named_reads=74*len(ids),comparisons=32,
        primary_unchanged=True,secondary_margin=True,complete_controls=True,
        output_files=count,new_dynamics=0,new_founders=0,prospective=True,benchmark_excluded=True)


def execute_blocks(stage,cfg=block.CONFIG,rcfg=block.READOUT,guard=lambda:None):
    ids=stage_ids(stage);rd,od=paths(stage);assert not od.exists();target(od/'PRIMARY.json')
    for pos,index in enumerate(ids):
        resources((len(ids)-pos)*BLOCK_BOUND+EXTRA_BOUND)
        d,s=od/'physical'/f'tissue_{index}',od/'secondary'/f'tissue_{index}'
        proof=block.run_block(d,index,cfg,rcfg);guard()
        checked=block.saved_check(d,index,cfg,rcfg)
        margins,mp=analysis.extract_margins(d,index,cfg,rcfg)
        for future,values in margins.items():block.save(s/(future+'.npz'),values)
        write(s/'CHECK.json',mp)
        write(rd/f'BLOCK_{index}.json',dict(status='COMPLETE',index=index,completed_utc=utc_now(),
            freeze_sha256=sha256_file(ROOT/'FREEZE.json'),full_replay=proof,verification=checked,secondary_verification=mp,
            output_sha256={str(p):sha256_file(p) for base in (d,s) for p in sorted(base.rglob('*')) if p.is_file()}))
        print(__import__('json').dumps(dict(stage=stage,index=index,checked_blocks=pos+1,total_blocks=len(ids))),flush=True);guard()
    if stage=='panel':
        write(od/'PRIMARY.json',analysis.primary(analysis.load_primary(od/'physical'),cfg.replicates,rcfg.draws))
        write(od/'MARGINS.json',analysis.margins(analysis.load_margins(od/'secondary'),cfg.replicates,rcfg.draws))
    else:write(od/'PRIMARY.json',read(od/'physical'/f'tissue_{block.DISPOSABLE}'/'SUMMARY.json'))
    return saved_stage(stage,cfg,rcfg)


def run_stage(stage):
    ids=stage_ids(stage);frozen();resources(len(ids)*BLOCK_BOUND+EXTRA_BOUND)
    assert os.environ.get(ENV)==stage
    if stage=='panel':execution_frozen();assert os.getsid(0)==os.getpid()
    rd,od=paths(stage);assert not rd.exists() and not od.exists();started=time.monotonic()
    try:
        write(rd/'MANIFEST.json',dict(stage=stage,started_utc=utc_now(),freeze_sha256=sha256_file(ROOT/'FREEZE.json'),
            execution_freeze_sha256=sha256_file(ROOT/'EXECUTION_FREEZE.json') if stage=='panel' else None,
            blocks=list(ids),primary='preference',secondary='margin',automatic_successor=False))
        fd=os.environ.pop(READY,None)
        if fd is not None:os.write(int(fd),b'READY\n');os.close(int(fd))
        def guard():
            if stage=='benchmark' and time.monotonic()-started>BENCHMARK_GUARD:raise TimeoutError('bounded timing block; retain failure')
        checked=execute_blocks(stage,guard=guard);frozen();resources();guard()
        output_hashes={str(p):sha256_file(p) for p in sorted(od.rglob('*')) if p.is_file()}
        size=sum(sum(a.nbytes for a in arrays(p).values()) for p in od.rglob('*.npz'))
        assert size<len(ids)*storage_bound()['per_block']+EXTRA_BOUND
        done=dict(status='COMPLETE',stage=stage,completed_utc=utc_now(),seconds=time.monotonic()-started,
            freeze_sha256=sha256_file(ROOT/'FREEZE.json'),manifest_sha256=sha256_file(rd/'MANIFEST.json'),
            execution_freeze_sha256=sha256_file(ROOT/'EXECUTION_FREEZE.json') if stage=='panel' else None,
            primary_sha256=sha256_file(od/'PRIMARY.json'),margin_sha256=sha256_file(od/'MARGINS.json') if stage=='panel' else None,
            verification=checked,output_sha256=output_hashes,
            block_receipts_sha256={str(rd/f'BLOCK_{i}.json'):sha256_file(rd/f'BLOCK_{i}.json') for i in ids},
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            uncompressed_array_bytes=size,resources=resources(),new_founders=len(ids),source_regenerated=True,
            main_cohort_started=(stage=='panel'),automatic_polling=False,automatic_retry=False,automatic_successor=False)
        write(rd/'COMPLETE.json',done)
        return {k:v for k,v in done.items() if k not in ('output_sha256','block_receipts_sha256')}
    except Exception as exc:
        write(rd/'FAILED.json',dict(status='FAILED',failed_utc=utc_now(),error=str(exc),traceback=traceback.format_exc(),
            retained=True,automatic_retry=False,automatic_successor=False));raise


def audit(stage):
    frozen();resources();rd,od=paths(stage);ids=stage_ids(stage);d=read(rd/'COMPLETE.json');m=read(rd/'MANIFEST.json')
    assert d['status']=='COMPLETE' and d['stage']==stage and not (rd/'FAILED.json').exists()
    assert {p.name for p in rd.iterdir()}=={'MANIFEST.json','COMPLETE.json'}|{f'BLOCK_{i}.json' for i in ids}
    assert d['freeze_sha256']==m['freeze_sha256']==sha256_file(ROOT/'FREEZE.json')
    assert d['manifest_sha256']==sha256_file(rd/'MANIFEST.json') and d['primary_sha256']==sha256_file(od/'PRIMARY.json')
    assert set(d['output_sha256'])=={str(p) for p in od.rglob('*') if p.is_file()};verify(d['output_sha256'])
    assert set(d['block_receipts_sha256'])=={str(rd/f'BLOCK_{i}.json') for i in ids};verify(d['block_receipts_sha256'])
    if stage=='panel':
        execution_frozen();assert d['execution_freeze_sha256']==m['execution_freeze_sha256']==sha256_file(ROOT/'EXECUTION_FREEZE.json')
        assert d['margin_sha256']==sha256_file(od/'MARGINS.json')
    checked=saved_stage(stage);assert checked==d['verification']
    result=dict(status='SAVED_CHECK_PASSED',checked_utc=utc_now(),stage=stage,complete_sha256=sha256_file(rd/'COMPLETE.json'),verification=checked,new_dynamics=0)
    write(ROOT/'audits'/(stage+'.json'),result);return result


def seal_execution():
    frozen();resources(BOUND);assert not (ROOT/'EXECUTION_FREEZE.json').exists() and not paths('panel')[0].exists()
    rd,od=paths('benchmark');d=read(rd/'COMPLETE.json');a=read(ROOT/'audits/benchmark.json')
    assert d['status']=='COMPLETE' and d['verification']['passes'] and a['status']=='SAVED_CHECK_PASSED'
    assert a['complete_sha256']==sha256_file(rd/'COMPLETE.json') and a['verification']==d['verification']
    assert set(d['output_sha256'])=={str(p) for p in od.rglob('*') if p.is_file()}
    inputs=d['output_sha256']|d['block_receipts_sha256']|{str(p):sha256_file(p) for p in [rd/'MANIFEST.json',rd/'COMPLETE.json',ROOT/'audits/benchmark.json']}
    verify(inputs);assert saved_stage('benchmark')==d['verification']
    value=dict(schema='d197_execution_seal_v1',frozen_utc=utc_now(),design_freeze_sha256=sha256_file(ROOT/'FREEZE.json'),
        blocks=list(BLOCKS),disposable=block.DISPOSABLE,benchmark_sha256=sha256_file(rd/'COMPLETE.json'),
        inputs=inputs,budget=budget(d['seconds']),resources=resources(BOUND),scientific_design_changed=False,
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write(ROOT/'EXECUTION_FREEZE.json',value);return {k:v for k,v in value.items() if k!='inputs'}


def execution_frozen():
    f=read(ROOT/'EXECUTION_FREEZE.json');verify(f['inputs'])
    assert f['schema']=='d197_execution_seal_v1' and f['design_freeze_sha256']==sha256_file(ROOT/'FREEZE.json')
    assert f['blocks']==list(BLOCKS) and f['disposable']==block.DISPOSABLE and f['scientific_design_changed'] is False
    d=read(paths('benchmark')[0]/'COMPLETE.json')
    assert f['benchmark_sha256']==sha256_file(paths('benchmark')[0]/'COMPLETE.json') and f['budget']==budget(d['seconds'])
    assert all(f[k] is False for k in ('automatic_polling','automatic_retry','automatic_successor'))
    return f


def launch():
    frozen();f=execution_frozen();resources(BOUND);assert not paths('panel')[0].exists() and not paths('panel')[1].exists()
    rd,wr=os.pipe()
    try:
        with target(ROOT/'logs/panel.log').open('xb') as log:
            proc=subprocess.Popen([sys.executable,'-u','-m','laws_confirmation.l22_pulse_founders','--run','panel'],
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=WS,start_new_session=True,
                env=dict(os.environ,**{ENV:'panel',READY:str(wr)}),pass_fds=(wr,))
    finally:os.close(wr)
    ready=select.select([rd],[],[],60)[0];message=os.read(rd,64) if ready else b'';os.close(rd)
    value=dict(status='DETACHED_STARTED' if message==b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        acknowledged_utc=utc_now(),pid=proc.pid,budget=f['budget'],workers=1,affinity=[6],nice=10,
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write(ROOT/'logs/panel_launch.json',value);return value


def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--prepare',type=Path);g.add_argument('--run',choices=('benchmark','panel'))
    g.add_argument('--audit',choices=('benchmark','panel'));g.add_argument('--seal',action='store_true');g.add_argument('--launch',action='store_true')
    a=p.parse_args()
    result=prepare(a.prepare.resolve()) if a.prepare else run_stage(a.run) if a.run else audit(a.audit) if a.audit else seal_execution() if a.seal else launch()
    print(__import__('json').dumps(result,sort_keys=True),flush=True)

if __name__=='__main__':main()
