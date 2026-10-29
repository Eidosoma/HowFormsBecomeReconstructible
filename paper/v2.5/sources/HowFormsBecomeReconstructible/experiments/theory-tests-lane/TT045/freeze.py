"""Freeze fresh-future production after full excluded qualification."""
from common import *
import execute, math


def main():
    qp = ROOT/'checks/preflight_v1/COMPLETE.json'; bp = ROOT/'runs/qualification_v1/COMPLETE.json'
    pre, q = read(qp), read(bp); layout = read(ROOT/'LAYOUT.json'); code = inputs()
    assert pre['status'] == 'PASS' and q['status'] == 'COMPLETE' and q['serial_parallel_bitwise_equal']
    assert pre['inputs'] == q['inputs'] == code and q['environment'] == execute.environment()
    verify(pre['outputs']); verify(q['outputs']); verify(read(ROOT/'SOURCE_MANIFEST.json')['evidence'])
    small = min(b['physical'] for b in layout['groups']['excluded']['blocks'].values())
    production = layout['groups']['development']['blocks']
    waves = sum(max(production[str(i)]['physical'] for i in BLOCKS[k:k+2]) for k in (0, 2))
    forecast = math.ceil(1.5*q['seconds']*waves/small+60); assert forecast < MAX_FORECAST
    projected = layout['groups']['development']['forecast_output_bytes']+64*1024**2
    assert size()+projected < LIMIT and shutil.disk_usage(ROOT).free >= RESERVE+projected
    assert not (ROOT/'runs/futures_v1').exists()
    value = dict(study='TT045', frozen_utc=now(), inputs=code, evidence={str(p):sha(p) for p in (qp, bp)},
        environment=execute.environment(), cpus=[6, 7], workers=2, numerical_threads=1,
        blocks=BLOCKS, run_name='futures_v1', forecast_seconds=forecast, deadline_seconds=max(600, 2*forecast),
        forecast_rule='1.5 * measured two-block qualification seconds * production wave work / smaller excluded block work + 60',
        production_wave_physical_count=waves, smaller_excluded_block_physical_count=small,
        forecast_new_output_bytes=projected, study_output_ceiling_bytes=LIMIT, free_reserve_bytes=RESERVE,
        package_cap_bytes=BATCH_BYTES, source_population_exposed=True, source_states_reused=True,
        new_futures_per_fixed_state=16, fixed_fresh_states_per_record=4, fixed_continuing_states_per_record=1,
        independent_production_block_future_banks=64, feedback_gain=0., all_cases_retained=True,
        new_production_outcomes_generated=False, confirmatory=False, population_confirmation=False,
        baseline_assays_replayed_in_preflight=True, seed_manifest_sha256=sha(ROOT/'SEEDS.json'),
        primary='mix050; residual|all|all_masks|own; target at 900 and 1000; paired packet effects in C and F and state-by-packet interaction over new futures',
        monte_carlo_se_scope='conditional on fixed records; does not estimate population uncertainty',
        automatic_polling=False, automatic_retry=False, automatic_extension=False, automatic_successor=False)
    write(ROOT/'FREEZE.json', value); return value
