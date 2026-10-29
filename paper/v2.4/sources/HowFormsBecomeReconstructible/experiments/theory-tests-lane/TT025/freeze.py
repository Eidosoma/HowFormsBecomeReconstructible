"""Freeze only after excluded qualification, benchmark and resource admission."""
from datetime import datetime, timezone
from dataclasses import asdict
import math
import shutil
from common import *
import design
import execute

def main():
    assert not (ROOT/'FREEZE.json').exists() and not (ROOT/'runs'/execute.PANEL).exists()
    inputs = runtime_hashes(); source_check(); baseline_check()
    pointer = read_json(ROOT/'QUALIFICATION.json'); qpath = Path(pointer['path'])
    assert sha(qpath) == pointer['sha256']; qualification = read_json(qpath)
    bpath = ROOT/'runs'/execute.BENCHMARK/'COMPLETE.json'; benchmark = read_json(bpath)
    assert qualification['status'] == 'PASS' and benchmark['status'] == 'COMPLETE'
    assert qualification['inputs'] == benchmark['inputs'] == inputs
    assert qualification['environment'] == benchmark['environment'] == execute.environment()
    verify(qualification['outputs']); verify(benchmark['outputs'])
    resource = read_json(ROOT/'PRELAUNCH_RESOURCE_CHECK.json')
    assert resource['admission_pass'] and resource['planned_workers'] == 2
    assert (datetime.now(timezone.utc)-datetime.fromisoformat(resource['recorded_utc'])).total_seconds() < 180
    scale = design.expected('development', 4)['native_batches']/benchmark['verification']['native_batches']
    forecast = benchmark['seconds']*scale*1.5+180
    deadline = max(600, math.ceil(3*forecast+600))
    storage = math.ceil(benchmark['retained_bytes']*scale*1.3+64*1024**2)
    assert forecast < 16*3600 and deadline < 48*3600 and storage < execute.RUN_LIMIT
    assert shutil.disk_usage(ROOT).free >= execute.RUN_LIMIT+execute.RESERVE
    cfg, rcfg = design.configs('development')
    evidence = dict(read_json(ROOT/'BASELINE_MANIFEST.json')['evidence'])
    evidence.update({str(p): sha(p) for p in (qpath, bpath, ROOT/'PRELAUNCH_RESOURCE_CHECK.json')})
    frozen = dict(status='FROZEN_EXPOSED_CASE_PAIRED_RECEIVING_DEVELOPMENT', study='TT025', frozen_utc=now(),
        blocks=list(BLOCKS), families=list(design.FAMILIES), arms=list(design.ARMS), history_futures=4, new_draws=4, cycles=8,
        config=asdict(cfg), readout=asdict(rcfg), primary='residual:subtract_on:final_minus_initial',
        population_blocks=4, records_per_family=64, record_bytes=2048, namespace=design.TAG,
        forecast_seconds=forecast, deadline_seconds=deadline, estimated_output_bytes=storage,
        inputs=inputs, evidence=evidence, environment=execute.environment(), cpus=benchmark['cpus'], workers=2, numerical_threads=1,
        planned_verification=design.expected('development', 4), run_byte_limit=execute.RUN_LIMIT, free_reserve_bytes=execute.RESERVE,
        starting_records_and_history_exposed=True, new_production_receiving_draws_generated=False,
        fresh_population_confirmation=False, significance_verdict=False, body_or_label_enters_physics=False,
        automatic_polling=False, automatic_retry=False, automatic_successor=False, automatic_sample_extension=False)
    write_json(ROOT/'FREEZE.json', frozen)
    print(json.dumps({k: frozen[k] for k in ('status', 'forecast_seconds', 'deadline_seconds', 'estimated_output_bytes', 'planned_verification')}, sort_keys=True))
if __name__ == '__main__': main()
