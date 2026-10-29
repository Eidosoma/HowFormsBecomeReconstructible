"""Excluded native replay, corruption, pairing and analysis qualification."""
import copy
import os
import signal
import time
import traceback
from common import *
import analysis
import audit
import design
import execute
import kernel
import run

def main():
    output = ROOT/'checks/qualification_v1'; output.mkdir(parents=True, exist_ok=False); tick = time.monotonic()
    checks = []
    def passed(name): checks.append(name)
    def rejects(name, call):
        try: call()
        except (AssertionError, ValueError, TypeError): passed(name); return
        raise AssertionError('invalid case accepted: '+name)
    def expire(*_): raise TimeoutError('600-second excluded qualification limit')
    signal.signal(signal.SIGALRM, expire); signal.alarm(600)
    inputs = runtime_hashes()
    write_json(output/'RUNNING.json', dict(started_utc=now(), inputs=inputs, production_outcomes_generated=False))
    execute.snapshot_code(output)
    try:
        source_check(); baseline_check(); passed('verified native source and every saved packet route')
        random = read_json(ROOT/'RANDOMNESS.json'); assert random['status'] == 'PASS'
        for row in random['addresses']:
            assert design.address(row['role'], row['index'], row['history'], row['draw']) == audit.address(row['role'], row['index'], row['history'], row['draw']) == row['address']
        passed('independent addresses and prior-stream collision checks')
        cfg, rcfg = design.configs('qualification'); index = DISPOSABLE[0]; ctx = model.source.context(index, cfg)
        packets, _ = run.baseline('qualification', index, 0, 'residual'); packet = packets['initial'].tobytes()
        key = design.address('qualification', index, 0, 0)
        raw, meta = kernel.read(ctx, packet, key, rcfg)
        native = model.boundary.fresh_read(dict(ctx, index=key), packet, rcfg)
        assert identities(raw) == identities(native['raw'])
        assert meta == {k: v for k, v in native.items() if k not in ('raw', 'metrics')}
        passed('byte-exact native adapter equivalence including birth ema and scores')
        audit.read(ctx, packet, rcfg, 'qualification', index, 0, 0, raw, meta, True)
        passed('independent native physical replay')
        runtime = kernel.runtime_context(ctx)
        rejects('body state cannot enter receiver', lambda: kernel.physical_read(runtime | {'V': raw['s0_V']}, packet, key, rcfg))
        rejects('task codes cannot enter receiver', lambda: kernel.physical_read(runtime | {'codes': ctx['codes']}, packet, key, rcfg))
        rejects('wrong byte length rejected', lambda: kernel.physical_read(runtime, packet[:-8], key, rcfg))
        rejects('array instead of bytes rejected', lambda: kernel.physical_read(runtime, packets['initial'], key, rcfg))
        nonfinite = packets['initial'].copy(); nonfinite.flat[0] = np.nan
        rejects('nonfinite packet rejected', lambda: kernel.physical_read(runtime, nonfinite.tobytes(), key, rcfg))
        changed_codes = ctx['codes'][[2, 3, 0, 1]].copy()
        relabeled, _ = kernel.read(dict(ctx, codes=changed_codes), packet, key, rcfg)
        for step in cfg.times:
            for name in KEYS: ref.exact(raw[f's{step}_{name}'], relabeled[f's{step}_{name}'], 'labels absent from dynamics')
        passed('changing observer labels leaves all physical arrays exact')
        bad = {k: v.copy() for k, v in raw.items()}; bad['s1_V'].flat[0] = np.nextafter(bad['s1_V'].flat[0], np.inf)
        rejects('one-ULP dynamics corruption rejected', lambda: audit.read(ctx, packet, rcfg, 'qualification', index, 0, 0, bad, meta, True))
        bad = {k: v.copy() for k, v in raw.items()}; bad['s0_R'].flat[0] = 1.
        rejects('hidden receiving memory rejected', lambda: audit.read(ctx, packet, rcfg, 'qualification', index, 0, 0, bad, meta, False))
        bad = {k: v.copy() for k, v in raw.items()}; bad['s1_theta'].flat[0] = np.nextafter(bad['s1_theta'].flat[0], np.inf)
        rejects('packet mutation rejected', lambda: audit.read(ctx, packet, rcfg, 'qualification', index, 0, 0, bad, meta, False))
        bad = {k: v.copy() for k, v in raw.items()}; bad['correctness'][0, 0] = 1.-bad['correctness'][0, 0]
        rejects('wrong receiving score rejected', lambda: audit.read(ctx, packet, rcfg, 'qualification', index, 0, 0, bad, meta, False))
        rejects('wrong recipient address rejected', lambda: audit.read(ctx, packet, rcfg, 'qualification', index, 0, 1, raw, meta, False))
        serial = output/'serial'; serial.mkdir()
        for index in DISPOSABLE: run.block(serial/f'tissue_{index}', index, 'qualification')
        parallel = output/'parallel'; parallel.mkdir()
        cpus = sorted(os.sched_getaffinity(0))[-2:]; assert len(cpus) == 2
        execute.batch(parallel, DISPOSABLE, 'qualification', cpus)
        count = 0
        for index in DISPOSABLE:
            left = serial/f'tissue_{index}'; right = parallel/f'tissue_{index}'
            assert run.saved(left) == run.saved(right)
            assert read_json(left/'ROWS.json') == read_json(right/'ROWS.json')
            for path in left.rglob('*.npz'):
                assert identities(arrays(path)) == identities(arrays(right/path.relative_to(left))); count += 1
        assert count == design.expected('qualification', 2)['native_batches']
        passed('serial and two-worker full checkpoint/row equivalence')
        summary, conditional = analysis.summary(serial, 'qualification')
        second, _ = analysis.summary(parallel, 'qualification'); assert serialized(summary) == serialized(second)
        passed('all-case paired summary and preservation equivalence')
        records = [r for i in DISPOSABLE for r in read_json(serial/f'tissue_{i}/ROWS.json')]
        rejects('duplicate or missing case rejected', lambda: analysis.validate(records[:-1]+records[:1], 'qualification', DISPOSABLE))
        bad = copy.deepcopy(records); bad[0]['effect'] += .25
        rejects('incorrect paired difference rejected', lambda: analysis.validate(bad, 'qualification', DISPOSABLE))
        bad = copy.deepcopy(records)
        preserve = next(r for r in bad if r['arm'] == 'zero_off'); preserve['outgoing_version'] = 'full_on_01'
        rejects('wrong preservation alias rejected', lambda: analysis.validate(bad, 'qualification', DISPOSABLE))
        mixed = copy.deepcopy(records); scores = (0., .25, 1/3, .5, 1.)
        for r in mixed:
            start = (r['world']+r['draw']+r['history']) % 5
            stride = 0 if r['arm'] == 'zero_off' else design.ARMS.index(r['arm'])+1
            r['initial'] = scores[start]
            r['incoming'] = scores[(start+stride*(r['cycle']-1)) % 5]
            r['outgoing'] = scores[(start+stride*r['cycle']) % 5]
            r['effect'] = r['outgoing']-r['incoming']; r['cumulative_effect'] = r['outgoing']-r['initial']
        mixed_summary = analysis.summarize(mixed, 'qualification', DISPOSABLE)
        for family in design.FAMILIES:
            for arm in design.WRITING:
                changes = mixed_summary['families'][family]['arms'][arm]['final_minus_initial']['draw_changes']
                assert changes['improved'] > 0 and changes['worsened'] > 0
        passed('mixed outcomes with three-way ties and exact rational telescoping')
        # Native scoring can form a three-way tie within its absolute tolerance.
        field = np.broadcast_to(.6e-12*ctx['codes'][0]+.3e-12*ctx['codes'][2], (16, 16, 16)).copy()
        observed = reader.measure(ctx, field, rcfg)[1]
        assert observed['correctness'][0, 0] == 1/3
        ref.scores(ctx['codes'], dict(observed, **{f's{cfg.sweeps}_V': field}), rcfg)
        passed('native near-zero three-way tolerance tie independently scored')
        write_json(output/'SUMMARY.json', summary); write_json(output/'MIXED_SUMMARY.json', mixed_summary)
        write_json(output/'CONDITIONAL.json', conditional)
        for value in (summary, mixed_summary):
            assert analysis.report(value) == analysis.report(json.loads(serialized(value)))
        passed('report survives sorted JSON roundtrip and retains all conditions')
        verify(inputs)
        result = dict(status='PASS', completed_utc=now(), seconds=time.monotonic()-tick, checks=checks,
            serial_parallel_array_files=count, new_production_receiving_draws=0, inputs=inputs, environment=execute.environment(),
            verification=design.expected('qualification', 2),
            outputs={str(p): sha(p) for p in sorted(output.rglob('*')) if p.is_file()})
        write_json(output/'COMPLETE.json', result)
        write_json(ROOT/'QUALIFICATION.json', dict(path=str(output/'COMPLETE.json'), sha256=sha(output/'COMPLETE.json')))
        print(json.dumps({k: v for k, v in result.items() if k not in ('inputs', 'outputs')}, sort_keys=True))
    except BaseException:
        write_json(output/'FAILED.json', dict(status='FAILED', failed_utc=now(), traceback=traceback.format_exc())); raise
    finally: signal.alarm(0)

if __name__ == '__main__': main()
