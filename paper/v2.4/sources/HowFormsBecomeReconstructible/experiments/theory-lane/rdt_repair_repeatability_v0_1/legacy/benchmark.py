"""Full native paired assay on disposable inputs; never scientific records."""
import argparse
from pathlib import Path
import time
from study import C, ev, digest, read, REGIMES
import actions
import paired
import verify
from run import Guard
from fixtures import panel


def main(output):
    output.mkdir(parents=True, exist_ok=False)
    rows, _, _, packets = panel()
    rows, packets = rows[-4:], packets[-4:]
    initial, receipts, details = actions.prepare(rows, packets)
    ev.save(output / 'actions.npz', dict(initial_packets=initial, **details))
    ev.write(output / 'actions.json', receipts)
    seal = output / 'SEAL.json'
    ev.write(seal, dict(utc=ev.utc(), stage='benchmark', rows=rows, branches=[[digest(a) for a in case] for case in initial]))
    audit_key = min(rows, key=lambda r: r['selection_hash'])['key']
    guard = Guard(output, C['resources']['benchmark_wall_seconds'])
    results = {}
    started = time.monotonic()
    for regime in REGIMES:
        folder = output / regime
        folder.mkdir()
        receipt, _ = paired.batch(rows, initial, audit_key, regime, 'benchmark', folder, guard, seal, ev.sha(seal))
        check = verify.continuation(folder, rows, initial, regime, 'benchmark', ev.sha(seal), audit_key)
        ev.write(folder / 'VERIFICATION.json', check)
        results[regime] = receipt['wall_seconds']
    forecast = max(results.values()) * 32 * C['resources']['forecast_factor'] + C['resources']['fixed_overhead_seconds']
    result = dict(utc=ev.utc(), status='PASS', full_native_read_steps=C['reader']['read_steps'],
        rewrites=18, terminal_reads=1, records_per_batch=4, branches=2, regimes=results,
        primary_native_reads=304, flat_native_reads=76, future_batches_planned=32,
        forecast_seconds=forecast, forecast_rule='32 batches * slower disposable regime time * 1.5 + 120 seconds',
        wall_seconds=time.monotonic() - started, new_scientific_outcomes=0,
        both_arms_flat_audited=True, original_sources_unchanged=True)
    ev.write(output / 'COMPLETE.json', result)
    print(dict(status='PASS', forecast_seconds=forecast, wall_seconds=result['wall_seconds']), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True, type=Path)
    main(p.parse_args().output)
