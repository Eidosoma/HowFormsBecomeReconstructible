"""Read-only diagnosis of audited E021 boundaries; no simulator imports."""
import argparse
import csv
import heapq
import json
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, finish, new_run, sha, utc
import numpy as np

CONDITIONS = ('renewed', 'intact_renewed', 'protected_copy', 'masked_copy', 'read_blocked', 'write_blocked')
ACTIVE = (0, 1, 4, 5)
RULES = np.array([1., -1., 1., -1.])
CUES = np.array([1., -1.])
PORTS = np.zeros((3, 16, 16), dtype=bool)
for p, (r, c) in enumerate(((7, 1), (3, 10), (11, 10))):
    PORTS[p, r:r+2, c:c+2] = True
SOURCES = np.flatnonzero(PORTS[0])
TARGETS = np.flatnonzero(PORTS[1] | PORTS[2])
NEIGHBORS = []
for r in range(16):
    for c in range(16):
        NEIGHBORS.append(((r*16+(c+1)%16, 0, r, c),
            (r*16+(c-1)%16, 0, r, (c-1)%16),
            (((r+1)%16)*16+c, 1, r, c),
            (((r-1)%16)*16+c, 1, (r-1)%16, c)))


def decode(packet):
    assert packet.dtype == np.uint8 and packet.shape[-1] == 4096
    return np.frombuffer(packet.tobytes(), dtype='<f8').reshape(*packet.shape[:-1], 2, 16, 16)


def encode(weights):
    return np.ascontiguousarray(weights, dtype='<f8').view(np.uint8).reshape(*weights.shape[:-3], 4096)


def edges(mask):
    alive = ~mask
    return np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)


def ports(v):
    return np.stack([v[..., p].mean(axis=-1) for p in PORTS[1:]], axis=-1)


def margin(values):
    desired = RULES[:, None, None]*CUES[None, None, :]
    return np.minimum(desired*values[..., 0], -desired*values[..., 1])


def widest(weights):
    """Maximum bottleneck paths, using reciprocal absolute edge magnitudes."""
    absolute = np.abs(weights)
    capacity = np.zeros(256)
    capacity[SOURCES] = np.inf
    queue = [(-np.inf, int(i)) for i in SOURCES]
    heapq.heapify(queue)
    while queue:
        negative, node = heapq.heappop(queue)
        value = -negative
        if value < capacity[node]:
            continue
        for neighbor, direction, r, c in NEIGHBORS[node]:
            candidate = min(value, absolute[direction, r, c])
            if candidate > capacity[neighbor]:
                capacity[neighbor] = candidate
                heapq.heappush(queue, (-candidate, neighbor))
    output = capacity[TARGETS]
    return dict(reachable_output_cells=int((output > 0).sum()),
        source_component_cells=int((capacity > 0).sum()),
        weakest_output_path_capacity=float(output.min()),
        mean_output_path_capacity=float(output.mean()))


def flood(weights, threshold):
    """Independent array flood fill for checking the graph calculation."""
    reached = PORTS[0].copy()
    h, v = np.abs(weights) > threshold
    for _ in range(256):
        old = reached.copy()
        reached |= np.roll(old & h, 1, -1)
        reached |= np.roll(old, -1, -1) & h
        reached |= np.roll(old & v, 1, -2)
        reached |= np.roll(old, -1, -2) & v
        if np.array_equal(old, reached):
            return reached
    raise AssertionError('Flood fill did not converge')


def checks():
    assert widest(np.zeros((2, 16, 16)))['reachable_output_cells'] == 0
    assert widest(np.ones((2, 16, 16)))['weakest_output_path_capacity'] == 1
    # A single wraparound path from input (7,1) to output (3,10), bottleneck .2.
    w = np.zeros((2, 16, 16))
    w[0, 7, [0, 15, 14, 13, 12, 11, 10]] = -.8
    w[1, 3:7, 10] = .2
    result = widest(w)
    assert result['reachable_output_cells'] == 2  # (3,10), (4,10)
    assert result['mean_output_path_capacity'] == .05
    for threshold in (0., .1, .2, .7, .9):
        reached = flood(w, threshold)
        expected = 2 if threshold < .2 else 0
        assert int(reached[TARGETS//16, TARGETS%16].sum()) == expected
    generator = np.random.default_rng(21092026)
    for _ in range(3):
        w = generator.choice([0., -.8, -.3, .1, .6], size=(2, 16, 16))
        # Inspect full capacity field through independent thresholds by scaling
        # each test to the returned minimum over all output cells.
        result = widest(w)
        assert result['reachable_output_cells'] == int(flood(w, 0)[PORTS[1] | PORTS[2]].sum())
        for threshold in (0., .1, .3, .6, .8):
            assert (result['weakest_output_path_capacity'] > threshold) == bool(flood(w, threshold)[PORTS[1] | PORTS[2]].all())
    desired = RULES[:, None, None]*CUES[None, None, :]
    p = np.stack((desired, -desired), axis=-1)
    assert (margin(p) > .25).all()
    assert not (margin(-p) > .25).any()
    return dict(graph_zero_full_wraparound_and_threshold_checks=True, rule_cue_axes_checked=True)


def packet_metrics(weights, prefix):
    result = {prefix+'_mean_abs': float(np.abs(weights).mean()),
        prefix+'_zero_fraction': float((weights == 0).mean())}
    result.update({prefix+'_'+k: v for k, v in widest(weights).items()})
    return result


def transitions(a, b):
    a, b = np.asarray(a, dtype=bool), np.asarray(b, dtype=bool)
    return dict(success_success=int((a & b).sum()), success_failure=int((a & ~b).sum()),
        failure_success=int((~a & b).sum()), failure_failure=int((~a & ~b).sum()))


def error_type(values, rule, cue):
    a, b = values
    if min(abs(a), abs(b)) <= .25:
        return 'weak_output'
    if a*b > 0:
        return 'same_positive' if a > 0 else 'same_negative'
    return 'correct' if a*rule*cue > .25 else 'reversed'


def analyze(run, output):
    started = time.monotonic()
    cap_cpus(1)
    assert run.is_relative_to(ROOT) and output.is_relative_to(HERE)
    assert not output.exists()
    complete, audit, scientific = [json.loads((run/name).read_text()) for name in
        ('COMPLETE.json', 'INDEPENDENT_AUDIT.json', 'summary.json')]
    job = json.loads((HERE.parent/'jobs'/run.name/'status.json').read_text())
    assert complete['status'] == job['status'] == 'COMPLETE' and audit['status'] == 'PASS'
    assert sha(run/'COMPLETE.json') == audit['complete_sha256'] == job['scientific_complete_sha256']
    assert sha(run/'INDEPENDENT_AUDIT.json') == job['audit_sha256']
    check_inputs(run)
    assert scientific['conditions'] == list(CONDITIONS)
    assert scientific['cfg']['margin'] == .25 and scientific['cfg']['writer_beta'] == 3
    units = dict(blocks=len(scientific['blocks']), founders=scientific['founders'], lineages=scientific['lineages'])
    new_run(output, [Path(__file__), HERE/'BOUNDARY_DIAGNOSIS.md', ROOT/'common.py', ROOT/'run_python.sh',
        run/'COMPLETE.json', run/'INDEPENDENT_AUDIT.json', run/'summary.json', run/'manifest.json'],
        dict(experiment='E021', analysis='post_hoc_saved_boundary_diagnosis', source=str(run.relative_to(ROOT)),
            new_simulation=False, numerical_threads=1, units=units))
    dump(output/'status.json', dict(status='RUNNING', utc=utc()))
    fixture = checks()
    checked = {}

    def verify(name):
        value = sha(run/name)
        assert value == complete['outputs_sha256'][name], name
        checked[name] = value

    verify('summary.json')
    verify('observations.csv')
    observations = {}
    for row in csv.DictReader((run/'observations.csv').open(newline='')):
        if row['arm'] == 'own' and row['damage'] == 'intact':
            key = tuple(int(row[k]) for k in ('block', 'horizon', 'founder', 'lineage', 'cue')) + (row['condition'],)
            assert key not in observations
            observations[key] = row
    rows, initial = [], []
    for block in scientific['blocks']:
        name = f'source_{block:06d}.npz'
        verify(name)
        with np.load(run/name, allow_pickle=False) as raw:
            assert np.array_equal(raw['ports'], PORTS)
            source = np.repeat(raw['acquired'][1, :, None], scientific['cfg']['recipients'], axis=1)
        cumulative = np.ones((4, scientific['cfg']['recipients'], 2, 16, 16), dtype=bool)
        previous = np.repeat(source[None], 6, axis=0)
        for f in range(4):
            for r in range(scientific['cfg']['recipients']):
                initial.append(dict(block=block, founder=f, lineage=r, **packet_metrics(decode(source[f, r]), 'packet')))
        for generation in (1, 2, 3):
            name = f'boundary_{block:06d}_g{generation}.npz'
            verify(name)
            with np.load(run/name, allow_pickle=False) as raw:
                incoming, outgoing, effective, masks, body_masks, body, late, computed = [raw[k] for k in
                    ('incoming', 'outgoing', 'read_packets', 'renewal_mask', 'body_masks', 'developed_end', 'developed_late_ports', 'computed_packets')]
            assert np.array_equal(incoming, previous)
            assert (masks.sum(axis=(-2, -1)) == 24).all()
            assert not (masks & PORTS.any(axis=0)).any()
            assert not body_masks[1].any()
            assert np.array_equal(body_masks[[0, 2, 3]], np.repeat(masks[None], 3, axis=0))
            assert np.array_equal(body*np.expand_dims(body_masks, 3), np.zeros_like(body))
            survivor = edges(masks)
            newly_available = ~cumulative & survivor
            cumulative &= survivor
            x = np.tanh(3*body)
            rebuilt = np.stack((x*np.roll(x, -1, -1), x*np.roll(x, -1, -2)), axis=-3).mean(axis=3)
            assert np.array_equal(encode(rebuilt), computed)
            assert np.array_equal(outgoing[[0, 1, 4]], computed[[0, 1, 2]])
            assert not outgoing[5].any()
            assert np.array_equal(outgoing[2], source)
            assert np.array_equal(outgoing[3], encode(decode(source)*cumulative))
            expected_read = encode(decode(incoming[list(ACTIVE)])*edges(body_masks))
            expected_read[2] = 0
            assert np.array_equal(effective, expected_read)
            iw, ow, ew = decode(incoming), decode(outgoing), decode(effective)
            p_late, p_end = late.mean(axis=0), ports(body)
            m_late, m_end = margin(p_late), margin(p_end)
            assay = None
            if generation in (1, 3):
                name = f'assay_{block:06d}_h{generation}.npz'
                verify(name)
                with np.load(run/name, allow_pickle=False) as raw:
                    assert np.array_equal(raw['packets'][:, :, :, 0], outgoing)
                    assay = raw['late_ports'].mean(axis=0)[:, :, :, :, 0, 0]
            for f in range(4):
                for r in range(scientific['cfg']['recipients']):
                    geometry = widest(survivor[f, r].astype(float))
                    for n, condition in enumerate(CONDITIONS):
                        row = dict(block=block, generation=generation, condition=condition, founder=f, lineage=r,
                            current_physical_reachable_output_cells=geometry['reachable_output_cells'] if n in (0, 4, 5) else (8 if n == 1 else None),
                            current_physical_source_component_cells=geometry['source_component_cells'] if n in (0, 4, 5) else (256 if n == 1 else None),
                            accumulated_erased_edge_fraction=float((~cumulative[f, r]).mean()))
                        row.update(packet_metrics(iw[n, f, r], 'incoming'))
                        row.update(packet_metrics(ow[n, f, r], 'outgoing'))
                        common_nonzero = (iw[n, f, r] != 0) & (ow[n, f, r] != 0)
                        row['rewritten_edge_mean_abs_change'] = float(np.abs(ow[n, f, r]-iw[n, f, r]).mean())
                        row['sign_change_fraction_common_nonzero'] = float((np.sign(iw[n, f, r][common_nonzero]) != np.sign(ow[n, f, r][common_nonzero])).mean()) if common_nonzero.any() else None
                        row['previously_erased_now_available_mean_abs'] = float(np.abs(ow[n, f, r][newly_available[f, r]]).mean()) if newly_available[f, r].any() else None
                        row['never_erased_edge_mean_abs'] = float(np.abs(ow[n, f, r][cumulative[f, r]]).mean())
                        row.update(body_late_both=None, body_end_both=None, body_late_cues_correct=None,
                            body_late_mean_margin=None, body_mean_abs_alive=None, body_cue_opposition_fraction_alive=None,
                            body_positive_cue_error=None, body_negative_cue_error=None, assay_both=None)
                        if n in ACTIVE:
                            a = ACTIVE.index(n)
                            alive = ~body_masks[a, f, r]
                            v = body[a, f, r]
                            row.update(packet_metrics(ew[a, f, r], 'effective'))
                            row.update(body_late_both=bool((m_late[a, f, r] > .25).all()),
                                body_end_both=bool((m_end[a, f, r] > .25).all()),
                                body_late_cues_correct=int((m_late[a, f, r] > .25).sum()),
                                body_late_mean_margin=float(m_late[a, f, r].mean()),
                                body_mean_abs_alive=float(np.abs(v[:, alive]).mean()),
                                body_cue_opposition_fraction_alive=float((v[0, alive]*v[1, alive] < 0).mean()),
                                body_positive_cue_error=error_type(p_late[a, f, r, 0], RULES[f], 1),
                                body_negative_cue_error=error_type(p_late[a, f, r, 1], RULES[f], -1))
                        if assay is not None:
                            successes = []
                            for c, cue in enumerate((1, -1)):
                                original = observations[(block, generation, f, r, cue, condition)]
                                assert np.array_equal(assay[n, f, r, c], [float(original['output_A']), float(original['output_B'])])
                                m = min(RULES[f]*cue*assay[n, f, r, c, 0], -RULES[f]*cue*assay[n, f, r, c, 1])
                                assert m == float(original['margin']) and (m > .25) == bool(int(original['success']))
                                successes.append(m > .25)
                            row['assay_both'] = bool(all(successes))
                        rows.append(row)
            previous = outgoing
        print(f'Analyzed block {block}', flush=True)
    variable_seconds = time.monotonic()-started
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (output/'lineages.csv').open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    groups = {}
    for generation in (1, 2, 3):
        groups[str(generation)] = {}
        for condition in CONDITIONS:
            selected = [r for r in rows if r['generation'] == generation and r['condition'] == condition]
            group = dict(lineages=len(selected))
            for key in fields:
                if key in ('block', 'generation', 'condition', 'founder', 'lineage'):
                    continue
                values = [r.get(key) for r in selected if r.get(key) is not None]
                if values and not isinstance(values[0], str):
                    group[key] = dict(mean=float(np.mean(values)), minimum=float(np.min(values)), maximum=float(np.max(values)))
                    if key in ('body_late_both', 'body_end_both', 'assay_both'):
                        group[key]['successes'] = int(sum(values))
            if condition in ('renewed', 'intact_renewed', 'read_blocked', 'write_blocked'):
                group['end_vs_late_disagreements'] = sum(r['body_late_both'] != r['body_end_both'] for r in selected)
                errors = [r[k] for r in selected for k in ('body_positive_cue_error', 'body_negative_cue_error')]
                group['individual_cue_error_counts'] = {k: errors.count(k) for k in sorted(set(errors))}
                if generation in (1, 3):
                    group['body_late_to_assay'] = transitions([r['body_late_both'] for r in selected], [r['assay_both'] for r in selected])
            if generation in (1, 3):
                original = scientific['groups'][str(generation)][condition]['both_cues']['intact']['own']
                assert group['assay_both']['mean'] == original['mean']
                for bi, block in enumerate(scientific['blocks']):
                    assert np.mean([r['assay_both'] for r in selected if r['block'] == block]) == original['block_means'][bi]
            for prefix in ('current_physical', 'incoming', 'effective', 'outgoing'):
                key = prefix+'_reachable_output_cells'
                if key in group:
                    group[prefix+'_any_output_disconnected'] = sum(r[key] < 8 for r in selected)
            groups[str(generation)][condition] = group
    serial = {}
    for condition in CONDITIONS:
        ordered = {g: [r for r in rows if r['generation'] == g and r['condition'] == condition] for g in (1, 2, 3)}
        serial[condition] = {'assay_h1_to_h3': transitions([r['assay_both'] for r in ordered[1]], [r['assay_both'] for r in ordered[3]])}
        if condition in ('renewed', 'intact_renewed', 'read_blocked', 'write_blocked'):
            for a, b in ((1, 2), (2, 3)):
                serial[condition][f'body_g{a}_to_g{b}'] = transitions([r['body_late_both'] for r in ordered[a]], [r['body_late_both'] for r in ordered[b]])
    result = dict(status='DESCRIPTIVE_SAVED_DATA_REVIEW', utc=utc(), units=units, new_simulation=False,
        source_scientific_status=scientific['status'], source_full_qualification=scientific['full_renewal_qualified'],
        graph_checks=fixture, groups=groups, serial_transitions=serial,
        initial_packet_mean_abs=float(np.mean([r['packet_mean_abs'] for r in initial])),
        initial_weakest_output_path_capacity=float(np.mean([r['packet_weakest_output_path_capacity'] for r in initial])),
        all_immediate_capture_bytes_and_serial_boundaries_verified=True,
        all_existing_intact_terminal_rows_and_block_means_reproduced=True,
        source_outputs_verified=len(checked), variable_seconds=variable_seconds,
        limits=['Post-hoc descriptive counts; no new confirmatory endpoint.',
            'Read-end body outputs are not independent fresh-body function.',
            'Absolute-weight path capacity ignores signs and is not sufficient for correct routing.',
            'No generation-2 terminal assay exists; no value is imputed.',
            'Associations do not separate causes or demonstrate a successful rescue.'])
    dump(output/'summary.json', result)
    dump(output/'provenance.json', dict(source_complete_sha256=sha(run/'COMPLETE.json'), source_audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
        consumed_source_outputs=checked, frozen_source_inputs_verified=True, script_sha256=sha(Path(__file__))))
    render(output, result)
    dump(output/'status.json', dict(status='COMPLETE', utc=utc(), seconds=time.monotonic()-started))
    finish(output, started, dict(analysis='saved_boundary_diagnosis', new_simulation=False))
    print(json.dumps(dict(output=str(output.relative_to(ROOT)), variable_seconds=variable_seconds,
        total_seconds=time.monotonic()-started, source_outputs_verified=len(checked), diagnostic_rows=len(rows)), indent=2))


def render(output, result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    groups = result['groups']
    n = result['units']['lineages']
    lines = ['# E021 saved-boundary diagnosis', '', '**Post-hoc descriptive analysis; no new simulation.**', '',
        f"All {result['units']['blocks']} blocks and {n} lineages retained in every chain.", '',
        'Body outputs are measured inside renewal bodies; terminal assays use separate intact bodies.', '',
        '| Generation | Chain | Read-window both cues | Read-end both cues | Intact terminal assay |',
        '| --- | --- | --- | --- | --- |']
    for g in ('1', '2', '3'):
        for c in CONDITIONS:
            d = groups[g][c]
            def cell(key):
                return f"{d[key]['successes']}/{n} ({100*d[key]['mean']:.1f}%)" if key in d else '—'
            lines.append(f"| {g} | {c} | {cell('body_late_both')} | {cell('body_end_both')} | {cell('assay_both')} |")
    lines += ['', 'All exact immediate captures and serial packet links were verified against the saved data.', '',
        '| Generation | Chain | Mean absolute outgoing weight | Mean weakest-output path capacity | Any output disconnected |',
        '| --- | --- | --- | --- | --- |']
    for g in ('1', '2', '3'):
        for c in CONDITIONS:
            d = groups[g][c]
            lines.append(f"| {g} | {c} | {d['outgoing_mean_abs']['mean']:.4f} | {d['outgoing_weakest_output_path_capacity']['mean']:.4f} | {d['outgoing_any_output_disconnected']}/{n} |")
    lines += ['', 'Physical-lattice disconnections (any of eight output cells unreachable from all input cells): '+
        ', '.join(f"generation {g}: {groups[g]['renewed']['current_physical_any_output_disconnected']}/{n}" for g in ('1', '2', '3'))+'.', '',
        'Path capacities use absolute weights and ignore signs; connected paths do not establish correct function.', '',
        '## Damaged-renewal transitions', '']
    for g in ('1', '3'):
        lines.append(f"Generation {g}, read-window output → terminal assay: `{json.dumps(groups[g]['renewed']['body_late_to_assay'], sort_keys=True)}`.")
        lines.append('')
    lines += ['Serial transitions: `'+json.dumps(result['serial_transitions']['renewed'], sort_keys=True)+'`.', '',
        '## Limits', '', *['- '+v for v in result['limits']], '',
        '[Per-lineage rows](lineages.csv), [full statistics](summary.json), [provenance](provenance.json), [figure](diagnosis.png).', '']
    (output/'REPORT.md').write_text('\n'.join(lines))
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    colors = {'renewed':'#176b9c', 'intact_renewed':'#23945b', 'protected_copy':'#777777', 'masked_copy':'#b96c24'}
    for c, label in [('renewed','Damaged body: read window'), ('intact_renewed','Intact body: read window')]:
        axes[0].plot([1, 2, 3], [100*groups[str(g)][c]['body_late_both']['mean'] for g in (1, 2, 3)], 'o-', color=colors[c], label=label)
    axes[0].plot([1, 3], [100*groups[str(g)]['renewed']['assay_both']['mean'] for g in (1, 3)], 's--', color='#8e3a83', label='Damaged renewal: intact assay')
    axes[0].set(ylabel='Both cues correct (%)', ylim=(-3, 103), title='Where outputs fail')
    for c in colors:
        label = c.replace('_', ' ')
        axes[1].plot([0, 1, 2, 3], [result['initial_packet_mean_abs']]+[groups[str(g)][c]['outgoing_mean_abs']['mean'] for g in (1, 2, 3)], 'o-', color=colors[c], label=label)
        axes[2].plot([0, 1, 2, 3], [result['initial_weakest_output_path_capacity']]+[groups[str(g)][c]['outgoing_weakest_output_path_capacity']['mean'] for g in (1, 2, 3)], 'o-', color=colors[c], label=label)
    axes[1].set(ylabel='Mean absolute edge weight', title='Outgoing record magnitude')
    axes[2].set(ylabel='Mean weakest-output path capacity', title='Absolute-weight path capacity')
    for ax in axes:
        ax.set_xlabel('Replacement generation')
        ax.set_xticks([0, 1, 2, 3] if ax is not axes[0] else [1, 2, 3])
        ax.grid(alpha=.2)
        ax.legend(fontsize=7, loc='best')
    fig.suptitle('E021 saved evidence — descriptive, no new dynamics')
    fig.tight_layout()
    fig.savefig(output/'diagnosis.png', dpi=180)
    fig.savefig(output/'diagnosis.svg')
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    destination = Path(args.output).resolve()
    try:
        analyze(Path(args.source).resolve(), destination)
    except BaseException:
        # Never alter an already completed analysis, including on a refused rerun.
        if destination.is_relative_to(HERE) and (destination/'status.json').exists() and not (destination/'COMPLETE.json').exists():
            dump(destination/'FAILED.json', dict(status='FAILED', utc=utc(), traceback=traceback.format_exc()))
            dump(destination/'status.json', dict(status='FAILED', utc=utc()))
        raise
