"""Follow-up saved-data scale check prompted by weak restored generation-two links."""
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, finish, new_run, sha
import numpy as np


def describe(values):
    x = np.concatenate(values)
    return dict(count=len(x), mean=float(x.mean()),
        quantiles={str(q):float(np.quantile(x,q)) for q in (0, .01, .1, .5, .9, .99, 1)},
        fraction_above={str(t):float((x > t).mean()) for t in (0, 1e-12, 1e-6, .01, .1, .5)})


def main():
    started = time.monotonic()
    cap_cpus(1)
    run = HERE.parent/'runs/confirmation_v1'
    prior = HERE/'rebuilding_leads_v1'
    check_inputs(run); check_inputs(prior)
    hashes = json.loads((prior/'summary.json').read_text())['source_boundary_sha256']
    output = new_run(HERE/'rebuilding_link_scale_v1', [Path(__file__), ROOT/'common.py', ROOT/'run_python.sh',
        prior/'summary.json', prior/'COMPLETE.json', run/'COMPLETE.json'],
        dict(kind='post_hoc_followup_description', estimated_seconds=120, blocks=list(range(23000,23032)),
            generations=[1,2,3], candidate='strength_compensated',
            thresholds=[0,1e-12,1e-6,.01,.1,.5], quantiles=[0,.01,.1,.5,.9,.99,1],
            causal_claim=False, new_trajectories=False, workers=1, numerical_threads=1))
    values = {g:{name:[] for name in ('restored_magnitude','shared_magnitude','live_read_denominator')}
        for g in (1,2,3)}
    for block in range(23000,23032):
        cumulative = np.ones((4,4,2,16,16), bool)
        for g in (1,2,3):
            path = run/f'boundary_{block:06d}_g{g}.npz'
            assert sha(path) == hashes[path.name]
            with np.load(path, allow_pickle=False) as arrays:
                packet = np.ascontiguousarray(arrays['outgoing'][2])
                weights = packet.view('<f8').reshape(4,4,2,16,16)
                mask = arrays['renewal_mask']
                denominators = arrays['read_denominators'][2]
            alive = ~mask
            current = np.stack((alive & np.roll(alive,-1,-1),alive & np.roll(alive,-1,-2)),axis=-3)
            cumulative &= current
            values[g]['restored_magnitude'].append(np.abs(weights[current & ~cumulative]))
            values[g]['shared_magnitude'].append(np.abs(weights[cumulative]))
            values[g]['live_read_denominator'].append(denominators[alive])
    groups = {str(g):{name:(describe(parts) if sum(len(x) for x in parts) else None)
        for name,parts in group.items()} for g,group in values.items()}
    dump(output/'summary.json',dict(kind='post_hoc_link_scale_description', generations=groups,
        independent_blocks=32, pooled_edge_and_cell_descriptions_not_independent_observations=True,
        new_functional_tests=False, caveat='Scale checks do not distinguish useful weak signals from numerical/noise sensitivity.'))
    check_inputs(run); check_inputs(prior)
    finish(output,started,dict(source_boundaries_verified=96))
    print(json.dumps(dict(seconds=time.monotonic()-started,generations=groups),indent=2))


if __name__ == '__main__': main()
