"""Freeze production only after full excluded qualification and measured bounds."""
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
    forecast = math.ceil(1.5*q['seconds']*waves/small + 60); assert forecast < 4*3600
    projected = layout['groups']['development']['forecast_output_bytes'] + 64*1024**2
    assert size()+projected < LIMIT and shutil.disk_usage(ROOT).free >= RESERVE+projected
    assert not (ROOT/'runs/crossover_v1').exists()
    value = dict(study='TT044', frozen_utc=now(), inputs=code, evidence={str(p):sha(p) for p in (qp, bp)},
                 environment=execute.environment(), cpus=[6, 7], workers=2, numerical_threads=1,
                 blocks=BLOCKS, run_name='crossover_v1', forecast_seconds=forecast, deadline_seconds=max(600, 2*forecast),
                 forecast_rule='1.5 * measured two-block excluded seconds * production wave work / smaller excluded block work + 60',
                 production_wave_physical_count=waves, smaller_excluded_block_physical_count=small,
                 forecast_new_output_bytes=projected, study_output_ceiling_bytes=LIMIT, free_reserve_bytes=RESERVE,
                 source_population_exposed=True, source_forcing_reused=True, fresh_indices_per_block=4, continuing_indices_per_block=1, feedback_gain=0.,
                 new_receiving_conditions=True, new_independent_future_draws=0, baseline_assays_replayed=True,
                 new_production_outcomes_generated=False, confirmatory=False, all_cases_retained=True,
                 primary='mix050; residual|all|all_masks|own; target at 900 and 1000; packet effects in CC/CF/FC/FF; state and forcing contrasts; three-way interaction and both ordered decompositions',
                 automatic_polling=False, automatic_retry=False, automatic_extension=False, automatic_successor=False)
    write(ROOT/'FREEZE.json', value); return value
