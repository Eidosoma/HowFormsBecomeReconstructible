"""Full native read/assay replay using only already observed control packets."""
import json
from pathlib import Path
import time
import traceback

import numpy as np

import dynamics as d
from evidence import ROOT, check_assay, check_boundary, equal, native, sha, stamp, verify_sources, write_json


def main():
    cfg = json.loads((ROOT/'config.json').read_text())
    source = verify_sources(cfg)
    output = ROOT/'benchmark'
    output.mkdir(exist_ok=False)
    start = dict(status='RUNNING', at_utc=stamp(), config_sha256=sha(ROOT/'config.json'),
        code_sha256={n: sha(ROOT/n) for n in ('dynamics.py', 'evidence.py', 'benchmark.py')},
        intervention_dynamics=False, numerical_threads=1)
    write_json(output/'START.json', start)
    try:
        block = cfg['benchmark']['block']
        reference_indices = [0, 1, 0]
        g3, hash3 = native(source/f'boundary_{block:06d}_g3.npz', ('end', 'masks', 'outgoing'))
        equal(g3['end'][0], g3['end'][1], 'common generation-3 body')
        packets, _ = d.capture(g3['end'][reference_indices], g3['masks'], cfg['benchmark']['writers'],
                               cfg['config'], cfg['tolerance'])
        equal(packets, g3['outgoing'][reference_indices], 'generation-3 control capture')
        before = time.perf_counter()
        raw = d.rebuild(packets, block, 4, cfg['benchmark']['writers'], cfg['config'], cfg['cycle'], cfg['tolerance'])
        rebuild_seconds = time.perf_counter()-before
        g4, hash4 = native(source/f'boundary_{block:06d}_g4.npz', ('masks', 'birth', 'end', 'mean_ports', 'outgoing'))
        boundary_checks = check_boundary(raw, g4, (0, 1, 2), tuple(reference_indices))
        g32, hash32 = native(source/f'boundary_{block:06d}_g32.npz', ('outgoing',))
        before = time.perf_counter()
        assay = d.assay(g32['outgoing'][reference_indices], block, 32, cfg['config'], cfg['cycle'])
        assay_seconds = time.perf_counter()-before
        terminal, hasha = native(source/f'assay_{block:06d}_h32.npz', ('masks', 'birth', 'end', 'mean_ports'))
        assay_checks = check_assay(assay, terminal, (0, 1, 2, 3), (0, 1, 0, 35))
        forecast = 1.5*len(cfg['blocks'])*((cfg['terminal_generation']-cfg['branch_generation'])*rebuild_seconds+assay_seconds)+120
        report = dict(status='COMPLETE', completed_at_utc=stamp(), **{k: v for k, v in start.items() if k != 'status'},
            common_body_and_capture_checks=2, boundary_array_checks=boundary_checks,
            terminal_array_checks=assay_checks, byte_equal=True, rebuild_seconds=rebuild_seconds,
            assay_seconds=assay_seconds, forecast_cpu_seconds=forecast,
            forecast_description='1.5 times timed complete compute, plus 120 seconds for input checks, compression and analysis',
            within_development_cost_ceiling=forecast <= cfg['forecast_ceiling_cpu_seconds'],
            raw_sha256={f'boundary_{block:06d}_g3.npz': hash3, f'boundary_{block:06d}_g4.npz': hash4,
                        f'boundary_{block:06d}_g32.npz': hash32, f'assay_{block:06d}_h32.npz': hasha})
        write_json(output/'COMPLETE.json', report)
        print(json.dumps(report, indent=2))
    except BaseException:
        write_json(output/'FAILED.json', dict(status='FAILED', at_utc=stamp(), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
