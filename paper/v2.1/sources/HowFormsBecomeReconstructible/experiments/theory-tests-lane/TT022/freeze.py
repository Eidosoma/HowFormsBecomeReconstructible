"""Freeze exposed-cohort serial development after qualification and timing."""
from dataclasses import asdict
from pathlib import Path
import shutil
import subprocess
import time
import traceback

from common import *
import design
import execute


def reserve():
    upstream = Path('/home/robert/Random-Replications/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas')
    roots = [LANE.parent, upstream]
    command = ['rg', '--files', '--hidden', '-g', '*.json', '-g', '*.jsonl', '-g', '*.py', '-g', '*.md',
               '-g', '*.txt', '-g', '!**/.git/**', '-g', '!**/.cache/**', '-g', '!**/.venv/**', *map(str, roots)]
    names = subprocess.run(command, capture_output=True, text=True, check=True).stdout.splitlines()
    scanned = {}; excluded = []; collisions = []
    for name in sorted(set(names)):
        p = Path(name)
        if p.is_relative_to(ROOT): continue
        if p.stat().st_size > 2*1024**2: excluded.append(str(p)); continue
        data = p.read_bytes(); scanned[str(p)] = hashlib.sha256(data).hexdigest()
        if design.TAG.encode() in data: collisions.append(str(p))
    result = dict(status='PASS' if not collisions else 'COLLISION', recorded_utc=now(), namespace=design.TAG,
        roots=list(map(str, roots)), scanned_files_sha256=scanned, excluded_large_files=excluded, collisions=collisions,
        limitation='Bounded accessible metadata/code search; exposed starting records; no independent custody or technical blinding.')
    write_json(ROOT/'RESERVATION.json', result); assert not collisions, collisions
    return result


def main():
    attempt = ROOT/'freeze_attempts/v1'; attempt.mkdir(parents=True, exist_ok=False)
    try:
        assert not (ROOT/'FREEZE.json').exists() and not (ROOT/'runs'/execute.PANEL).exists()
        inputs = runtime_hashes(); source_check(); baseline_check()
        qp = read_json(ROOT/'QUALIFICATION.json'); qpath = Path(qp['path'])
        assert qp['status'] == 'PASS' and qp['sha256'] == sha(qpath)
        q = read_json(qpath); bpath = ROOT/'runs'/execute.BENCHMARK/'COMPLETE.json'; b = read_json(bpath)
        assert q['status'] == 'PASS' and b['status'] == 'COMPLETE'
        assert q['inputs'] == b['inputs'] == inputs
        assert q['environment'] == b['environment'] == execute.environment()
        verify(q['outputs']); verify(b['outputs'])
        forecast = b['seconds']*160+120; deadline = int(3*forecast+600)
        storage = b['retained_bytes']*16*1.5
        assert forecast < 16*3600 and deadline < 48*3600, 'time admission'
        assert storage < execute.RUN_LIMIT, 'storage projection admission'
        assert shutil.disk_usage(ROOT).free >= execute.RUN_LIMIT+execute.RESERVE
        resources = read_json(ROOT/'PRELAUNCH_RESOURCE_CHECK.json')
        assert resources['admission_pass'] and resources['planned_workers'] == 2
        reservation = reserve()
        cfg, rcfg = design.configs('development')
        evidence = {str(p): sha(p) for p in (qpath, bpath, ROOT/'PRELAUNCH_RESOURCE_CHECK.json', ROOT/'RESERVATION.json')}
        evidence.update(read_json(ROOT/'BASELINE_MANIFEST.json')['evidence'])
        result = dict(status='FROZEN_EXPOSED_STARTING_RECORD_DEVELOPMENT', study='TT022', frozen_utc=now(),
            blocks=list(BLOCKS), policies=list(design.POLICIES), families=list(design.FAMILIES),
            futures=design.FUTURES, generations=design.GENERATIONS, records_per_family=64,
            chains_per_policy_family=256, population_blocks=4, namespace=design.TAG,
            config=asdict(cfg), readout=asdict(rcfg), inputs=inputs, evidence=evidence,
            environment=execute.environment(), cpus=b['cpus'], workers=2, numerical_threads=1,
            primary='common:capture_vs_ordinary:terminal', comparisons=design.comparisons(),
            forecast_seconds=forecast, deadline_seconds=deadline, estimated_output_bytes=storage,
            run_byte_limit=execute.RUN_LIMIT, free_reserve_bytes=execute.RESERVE,
            starting_record_outcomes_exposed=True, scientific_serial_futures_generated=False,
            fresh_population_confirmation=False, significance_verdict=False,
            automatic_polling=False, automatic_retry=False, automatic_successor=False)
        write_json(ROOT/'FREEZE.json', result)
        write_json(attempt/'COMPLETE.json', dict(status='PASS', completed_utc=now(), freeze_sha256=sha(ROOT/'FREEZE.json')))
        print(json.dumps(dict(status=result['status'], inputs=len(inputs), forecast_seconds=forecast,
            deadline_seconds=deadline, estimated_output_bytes=storage,
            searched_files=len(reservation['scanned_files_sha256'])), sort_keys=True), flush=True)
    except BaseException as error:
        write_json(attempt/'FAILED.json', dict(status='FAILED', failed_utc=now(), error=repr(error),
            traceback=traceback.format_exc(), automatic_retry=False))
        raise


if __name__ == '__main__': main()
