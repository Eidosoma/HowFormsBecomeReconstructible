"""Bounded saved-data analysis, with measured admission and immutable outputs."""
import argparse
from datetime import datetime, timezone
import math
import os
import shutil
import signal
import sys
import time
import traceback
import numpy as np
from common import *
import diagnose
import report


def environment():
    return dict(python=sys.version, numpy=np.__version__, numerical_threads={k:os.environ.get(k) for k in
        ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})


def inputs():
    names = ('common.py','diagnose.py','report.py','execute.py','qualify.py','resources.py','prepare.py','PROTOCOL.md','SOURCE_MANIFEST.json')
    return {str(p):sha(p) for p in [ROOT/n for n in names]+[LANE/'run_python.sh']}


def expected(role, blocks):
    c,d,f,m = (2,8,2,3) if role == 'diagnosis' else (1,1,1,1)
    body = blocks*c*f*m*9*16
    return dict(status='PASS', source_rows=body*d, source_bodies=body,
        paired_receiving_draws=blocks*c*f*m*16*d, fixed_output_pairs=blocks*c*f*m*16,
        record_positions=blocks*f*m*16, prefix_pairs=blocks*c*f*m,
        shared_checkpoint_arrays=blocks*c*f*m*12, short_gate_hold_arrays=blocks*c*f*m*2,
        all_controls_reconciled=blocks*f*m*9, new_dynamics=0, new_receiving_assays=0)


def retain(folder, value):
    folder.mkdir(parents=True, exist_ok=False)
    for key,name in (('pairs','PAIRS.json'),('cases','FIXED_OUTPUT_PAIRS.json'),('records','RECORD_POSITIONS.json'),
        ('aggregate','AGGREGATE.json'),('context','CONTEXT.json'),('prefix_proof','PREFIX_CHECK.json'),
        ('verification','CHECK.json'),('timing','TIMING.json')):
        write_json(folder/name, value[key])


def join_context(target, source):
    for key,value in source.items():
        if key not in target:
            target[key] = json.loads(serialized(value)); continue
        for name,v in value.items():
            if isinstance(v,dict):
                for label,n in v.items(): target[key][name][label] += n
            else: target[key][name] += v


def control_table(value, original):
    result = {}
    for key,v in value.items():
        f,d,b,a = key.split('|'); cell = original['panel'][f][d][b][a]
        r = cell['receiving']['overall']; body = cell['body_vs_preservation']['overall']
        assert v['n'] == r['n'] and v['changes'] == r['pair_changes'] and v['record_changes'] == r['record_changes']
        assert v['body_n'] == body['n'] and v['body_changes'] == body['pair_changes']
        for k in ('incoming','outgoing'): assert abs(v[k]/(12*v['n'])-r[k]) <= 2e-15
        for k in ('incoming','outgoing'): assert abs(v['body_'+k]/(12*v['body_n'])-body[k]) <= 2e-15
        result[key] = dict(receiving_n=v['n'], original=v['original']/(12*v['n']),
            incoming=v['incoming']/(12*v['n']), outgoing=v['outgoing']/(12*v['n']),
            effect=(v['outgoing']-v['incoming'])/(12*v['n']), changes=v['changes'], record_changes=v['record_changes'],
            body_n=v['body_n'], body_incoming=v['body_incoming']/(12*v['body_n']),
            body_outgoing=v['body_outgoing']/(12*v['body_n']), body_changes=v['body_changes'])
    return result


def summarize(directory, indices, role, custody):
    aggregate = {}; context = {}; proofs = []
    for index in indices:
        folder = directory/f'tissue_{index}'
        diagnose.merge(aggregate, read_json(folder/'AGGREGATE.json'))
        join_context(context, read_json(folder/'CONTEXT.json'))
        proofs.append(read_json(folder/'CHECK.json'))
    proof = {k:sum(p[k] for p in proofs) for k in proofs[0] if k != 'status'}; proof['status'] = 'PASS'
    assert proof == expected(role, len(indices))
    old_job = UPSTREAM/'runs'/('confirmation_v1' if role == 'diagnosis' else 'benchmark_v1')
    old = custody.json(old_job/'SUMMARY.json')
    controls = control_table(context, old)
    panel = diagnose.finish(aggregate)
    for key,levels in panel.items():
        f,d = key.split('|'); parent = old['panel'][f][d]['own']
        for level in LEVELS:
            v = levels[level]['all']
            assert abs(v['recipient_effects']['extra_writing']['pooled_effect']+parent[SELECTED[1]]['receiving_vs_full']['overall']['effect']) <= 2e-15
            for grain in ('recipient_effects', 'body_effects'):
                if v[grain] is None: continue
                assert abs(v[grain]['full_vs_preservation']['pooled_effect']-v[grain]['short_vs_preservation']['pooled_effect']-v[grain]['extra_writing']['pooled_effect']) <= 2e-15
            for prefix in ('history:', 'injury:', 'history_injury:', 'message:'):
                assert sum(g['n'] for name,g in levels[level].items() if name.startswith(prefix)) == v['n']
        assert levels['receiving_draw']['all']['n'] == levels['fixed_output_pair']['all']['n']*(8 if role=='diagnosis' else 1)
        assert levels['fixed_output_pair']['all']['n'] == levels['record_position']['all']['n']*(2 if role=='diagnosis' else 1)
    return dict(study='TT029', role=role, classification='EXPOSED_SAVED_DATA_DIAGNOSIS',
        blocks=list(indices), groups=list(GROUPS), levels=list(LEVELS), verification=proof,
        panel=panel, source_controls=controls, source_registered_inference=old.get('registered_inference'),
        all_cases_and_paired_harms_retained=True, new_confirmation=False, fitted_policy=False,
        new_significance_tests=False, new_dynamics=0, new_receiving_assays=0,
        eight_draw_signs_are_observations_not_precise_capacities=True,
        zero_corruption_slots_repeat_physical_bodies=True, automatic_successor=False)


def freeze():
    q = read_json(ROOT/'checks/qualification_v1/COMPLETE.json')
    bench = read_json(ROOT/'checks/benchmark_v1/COMPLETE.json')
    manifest = read_json(ROOT/'SOURCE_MANIFEST.json')
    assert q['status'] == bench['status'] == 'PASS'
    assert q['inputs'] == bench['inputs'] == inputs()
    # Component-specific scaling avoids multiplying checkpoint I/O by receiving draws.
    timings = bench['block_timings']
    row_rate = max(v['source_seconds']/v['source_row_bytes'] for v in timings)
    analysis_rate = max(v['analysis_seconds']/16 for v in timings)
    prefix_rate = max(v['prefix_seconds'] for v in timings)
    source_bytes = sum(Path(p).stat().st_size for p in manifest['production_files'] if Path(p).name in ('ROWS.json','BODIES.json'))
    estimate = row_rate*source_bytes + analysis_rate*98304 + prefix_rate*768
    forecast = math.ceil(1.5*estimate+120)
    value = dict(status='FROZEN_EXPOSED_SAVED_ANALYSIS', recorded_utc=now(), inputs=inputs(),
        evidence=dict(manifest['evidence'], **{str(ROOT/'checks/qualification_v1/COMPLETE.json'):sha(ROOT/'checks/qualification_v1/COMPLETE.json'),
            str(ROOT/'checks/benchmark_v1/COMPLETE.json'):sha(ROOT/'checks/benchmark_v1/COMPLETE.json')}),
        environment=environment(), blocks=list(BLOCKS), source_population_already_exposed=True,
        planned_verification=expected('diagnosis',64), forecast_seconds=forecast,
        forecast_components=dict(source_seconds=row_rate*source_bytes, analysis_seconds=analysis_rate*98304,
            prefix_seconds=prefix_rate*768, safety_multiplier=1.5, overhead_seconds=120),
        deadline_seconds=600 if forecast<=600 else 2*forecast+600,
        detached_required=forecast>600, workers=1, numerical_threads=1, output_byte_limit=2*1024**3,
        new_dynamics=0, new_receiving_assays=0, no_new_population_cases=True,
        automatic_polling=False, automatic_retry=False, automatic_extension=False, automatic_successor=False)
    write_json(ROOT/'FREEZE.json', value)
    print({k:v for k,v in value.items() if k not in ('inputs','evidence','blocks','environment')}, flush=True)


def execute():
    frozen = read_json(ROOT/'FREEZE.json')
    assert inputs() == frozen['inputs'] and environment() == frozen['environment']
    verify(frozen['evidence'])
    resource = read_json(ROOT/'RESOURCE_CHECK.json')
    assert resource['admission_pass'] and 0 <= (datetime.now(timezone.utc)-datetime.fromisoformat(resource['recorded_utc'])).total_seconds() < 180
    assert set(environment()['numerical_threads'].values()) == {'1'}
    os.sched_setaffinity(0, {resource['cpu']}); os.nice(10)
    output = ROOT/'runs/diagnosis_v1'; output.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic()
    def expire(*_): raise TimeoutError('TT029 bounded saved-data analysis deadline')
    signal.signal(signal.SIGALRM, expire); signal.alarm(frozen['deadline_seconds'])
    try:
        write_json(output/'RUNNING.json', dict(status='RUNNING', started_utc=now(), pid=os.getpid(),
            freeze_sha256=sha(ROOT/'FREEZE.json'), inputs=inputs(), deadline_seconds=frozen['deadline_seconds'],
            cpu=resource['cpu'], workers=1, numerical_threads=1, new_dynamics=0, automatic_polling=False))
        if frozen['detached_required']:
            assert os.environ.get('TT029_DETACHED') == '1', 'detached host launch required by measured forecast'
        manifest = read_json(ROOT/'SOURCE_MANIFEST.json')
        custody = Custody(dict(manifest['production_files'], **manifest['evidence']))
        for index in BLOCKS:
            value = diagnose.process(UPSTREAM/f'runs/confirmation_v1/tissue_{index}', custody)
            retain(output/f'tissue_{index}', value)
            if (index-BLOCKS[0]+1)%16 == 0: print(json.dumps(dict(stage='saved_blocks_analyzed', blocks=index-BLOCKS[0]+1)), flush=True)
        summary = summarize(output, BLOCKS, 'diagnosis', custody)
        write_json(output/'SUMMARY.json', summary)
        write_json(output/'CONTROL_TABLE.json', summary['source_controls'])
        with (output/'REPORT.md').open('x') as stream: stream.write(report.render(summary))
        assert report.render(read_json(output/'SUMMARY.json')) == (output/'REPORT.md').read_text()
        verify(custody.consumed); verify(frozen['inputs']); verify(frozen['evidence'])
        write_json(output/'CONSUMED_SOURCE_FILES.json', custody.consumed)
        outputs = {str(p):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
        retained = sum(Path(p).stat().st_size for p in outputs)
        assert retained < frozen['output_byte_limit'] and shutil.disk_usage(ROOT).free >= 2*1024**3
        receipt = dict(status='COMPLETE', completed_utc=now(), seconds=time.monotonic()-tick,
            freeze_sha256=sha(ROOT/'FREEZE.json'), inputs=inputs(), outputs=outputs,
            consumed_source_files=len(custody.consumed), retained_bytes=retained,
            verification=summary['verification'], source_files_unchanged=True,
            full_control_table_reconciled=True, source_population_already_exposed=True,
            new_significance_tests=False, new_dynamics=0, new_receiving_assays=0,
            no_selected_policy=True, report_roundtrip_pass=True, automatic_retry=False, automatic_successor=False)
        write_json(output/'COMPLETE.json', receipt); signal.alarm(0)
        print({k:v for k,v in receipt.items() if k not in ('inputs','outputs')}, flush=True)
    except BaseException as error:
        write_json(output/'FAILED.json', dict(status='FAILED', failed_utc=now(), error=repr(error),
            traceback=traceback.format_exc(), automatic_retry=False, new_dynamics=0))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('mode', choices=('freeze','execute'))
    args = parser.parse_args()
    freeze() if args.mode == 'freeze' else execute()
