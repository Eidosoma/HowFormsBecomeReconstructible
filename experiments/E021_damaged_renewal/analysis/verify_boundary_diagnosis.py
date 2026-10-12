"""Independent recount and threshold-closure checks of the saved diagnosis."""
import csv
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, sha, utc
import numpy as np


def reachable(weights, threshold=0.):
    # An explicit symmetric adjacency matrix and repeated boolean closure;
    # this does not use the diagnostic's heap algorithm or neighbor table.
    nodes = np.arange(256).reshape(16, 16)
    u = nodes.ravel()
    adjacency = np.zeros((256, 256))
    for axis, direction in ((1, 0), (0, 1)):
        v = np.roll(nodes, -1, axis=axis).ravel()
        adjacency[u, v] = adjacency[v, u] = np.abs(weights[direction]).ravel()
    links = adjacency > threshold
    reached = np.zeros((16, 16), dtype=bool)
    reached[7:9, 1:3] = True
    reached = reached.ravel()
    for _ in range(256):
        new = reached | links[reached].any(axis=0)
        if np.array_equal(new, reached):
            return reached.reshape(16, 16)
        reached = new
    raise AssertionError('Closure failed to converge')


def main():
    started = time.monotonic()
    cap_cpus(1)
    destination = HERE/'boundary_diagnosis_verification_v1.json'
    assert not destination.exists()
    source = HERE.parent/'runs/damage_v1'
    analysis = HERE/'boundary_diagnosis_v1'
    receipts = {}
    for path in (HERE/'boundary_benchmark_v1', analysis):
        check_inputs(path)
        complete = json.loads((path/'COMPLETE.json').read_text())
        for name, digest in complete['outputs_sha256'].items():
            assert sha(path/name) == digest, (path, name)
        receipts[path.name] = dict(complete_sha256=sha(path/'COMPLETE.json'), outputs_verified=len(complete['outputs_sha256']))
    check_inputs(source)
    original = json.loads((source/'COMPLETE.json').read_text())
    provenance = json.loads((analysis/'provenance.json').read_text())
    assert provenance['source_complete_sha256'] == sha(source/'COMPLETE.json')
    assert provenance['source_audit_sha256'] == sha(source/'INDEPENDENT_AUDIT.json')
    for name, digest in provenance['consumed_source_outputs'].items():
        assert digest == original['outputs_sha256'][name] == sha(source/name), name
    summary = json.loads((analysis/'summary.json').read_text())
    rows = list(csv.DictReader((analysis/'lineages.csv').open(newline='')))
    indexed = {(int(r['block']), int(r['generation']), r['condition'], int(r['founder']), int(r['lineage'])): r for r in rows}
    assert len(indexed) == len(rows) == 9216
    for g, conditions in summary['groups'].items():
        for condition, group in conditions.items():
            selected = [r for r in rows if r['generation'] == g and r['condition'] == condition]
            assert len(selected) == group['lineages'] == 512
            for key in ('body_late_both', 'body_end_both', 'assay_both'):
                if key in group:
                    assert sum(r[key] == 'True' for r in selected) == group[key]['successes']
            if 'body_late_to_assay' in group:
                for before, after, name in ((True, True, 'success_success'), (True, False, 'success_failure'),
                    (False, True, 'failure_success'), (False, False, 'failure_failure')):
                    assert sum(r['body_late_both'] == str(before) and r['assay_both'] == str(after) for r in selected) == group['body_late_to_assay'][name]
    targets = np.zeros((16, 16), dtype=bool)
    targets[3:5, 10:12] = True
    targets[11:13, 10:12] = True
    graph_count = 0
    for block in range(19000, 19032):
        for generation in (1, 2, 3):
            with np.load(source/f'boundary_{block:06d}_g{generation}.npz', allow_pickle=False) as raw:
                packet, effective, mask = raw['outgoing'], raw['read_packets'], raw['renewal_mask']
            weights = np.frombuffer(packet.tobytes(), dtype='<f8').reshape(6, 4, 4, 2, 16, 16)
            reading = np.frombuffer(effective.tobytes(), dtype='<f8').reshape(4, 4, 4, 2, 16, 16)
            for f in range(4):
                for r in range(4):
                    alive = ~mask[f, r]
                    physical = np.stack((alive & np.roll(alive, -1, 1), alive & np.roll(alive, -1, 0)))
                    reached = reachable(physical.astype(float))
                    row = indexed[(block, generation, 'renewed', f, r)]
                    assert int(reached[targets].sum()) == int(row['current_physical_reachable_output_cells'])
                    assert int(reached.sum()) == int(row['current_physical_source_component_cells'])
                    graph_count += 1
                    for condition, prefix, w in [('renewed', 'effective', reading[0, f, r]),
                        ('renewed', 'outgoing', weights[0, f, r]), ('masked_copy', 'outgoing', weights[3, f, r]),
                        ('intact_renewed', 'outgoing', weights[1, f, r])]:
                        row = indexed[(block, generation, condition, f, r)]
                        reached = reachable(w)
                        assert int(reached[targets].sum()) == int(row[prefix+'_reachable_output_cells'])
                        assert int(reached.sum()) == int(row[prefix+'_source_component_cells'])
                        capacity = float(row[prefix+'_weakest_output_path_capacity'])
                        if capacity > 0:
                            assert reachable(w, np.nextafter(capacity, -np.inf))[targets].all()
                        assert not reachable(w, capacity)[targets].all()
                        graph_count += 1
        print(f'Independently checked block {block}', flush=True)
    forecast = json.loads((HERE/'boundary_diagnosis_forecast_v1.json').read_text())
    assert forecast['analysis_code_sha256'] == sha(HERE/'diagnose_boundaries.py')
    assert forecast['analysis_plan_sha256'] == sha(HERE/'BOUNDARY_DIAGNOSIS.md')
    assert forecast['benchmark_complete_sha256'] == receipts['boundary_benchmark_v1']['complete_sha256']
    predecessors = json.loads((HERE/'closeout_v1.json').read_text())['predecessor_frozen_inputs_unchanged']
    for relative in predecessors:
        check_inputs(ROOT/relative)
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
        if json.loads(p.read_text()).get('status') in ('PREPARED', 'RUNNING')]
    assert not active
    result = dict(status='PASS', utc=utc(), seconds=time.monotonic()-started,
        verification_code_sha256=sha(Path(__file__)), analysis_receipts=receipts,
        consumed_source_hashes_rechecked=len(provenance['consumed_source_outputs']),
        lineage_rows_recounted=len(rows), independently_checked_graphs=graph_count,
        method='Explicit symmetric adjacency matrix; boolean reachability at zero, reported bottleneck, and preceding representable value.',
        source_complete_sha256=sha(source/'COMPLETE.json'), source_audit_sha256=sha(source/'INDEPENDENT_AUDIT.json'),
        source_and_predecessor_frozen_inputs_unchanged=predecessors,
        figure_visually_inspected=True, active_experiment_jobs=active, new_simulation=False)
    with destination.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
