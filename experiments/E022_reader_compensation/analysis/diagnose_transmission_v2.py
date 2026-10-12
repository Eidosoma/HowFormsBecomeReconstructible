"""Post-hoc E022 saved-state review. No simulator is imported or executed."""
import argparse
from collections import Counter, deque
import csv
import json
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, finish, new_run, sha, utc
from E021_damaged_renewal.analysis.diagnose_boundaries import (
    decode, encode, edges, ports, margin, widest, checks, transitions, error_type,
    PORTS, RULES, CUES, SOURCES, TARGETS, NEIGHBORS)
import numpy as np

CONDITIONS = ('baseline', 'degree_compensated', 'strength_compensated', 'intact_renewed',
              'protected_copy', 'masked_copy', 'read_blocked', 'write_blocked')
ACTIVE = (0, 1, 2, 3, 6, 7)
DAMAGE = ('intact', 'scattered', 'square')


def signed_graph(weights, rule):
    """Multi-source signed traversal, with every input constrained to +1."""
    labels = np.zeros(256, dtype=np.int8)
    labels[SOURCES] = 1
    queue = deque(int(i) for i in SOURCES)
    conflict = False
    while queue:
        node = queue.popleft()
        for neighbor, direction, r, c in NEIGHBORS[node]:
            w = weights[direction, r, c]
            if w == 0:
                continue
            expected = int(labels[node]) * (1 if w > 0 else -1)
            if labels[neighbor] == 0:
                labels[neighbor] = expected
                queue.append(neighbor)
            elif labels[neighbor] != expected:
                conflict = True
    connected = bool((labels[TARGETS] != 0).all())
    aligned = connected and not conflict and bool(
        (labels[np.flatnonzero(PORTS[1])] == rule).all() and
        (labels[np.flatnonzero(PORTS[2])] == -rule).all())
    return dict(signed_source_consistent=not conflict, signed_all_outputs_aligned=aligned)


def signed_checks():
    spins = np.ones((16, 16)); spins[PORTS[2]] = -1
    w = np.stack((spins*np.roll(spins, -1, 1), spins*np.roll(spins, -1, 0)))
    assert signed_graph(w, 1) == dict(signed_source_consistent=True, signed_all_outputs_aligned=True)
    assert not signed_graph(w, -1)['signed_all_outputs_aligned']
    w[0, 0, 0] *= -1
    assert not signed_graph(w, 1)['signed_source_consistent']
    assert not signed_graph(np.zeros_like(w), 1)['signed_all_outputs_aligned']
    return True


def incident(w):
    h, v = w
    return h + np.roll(h, 1, 1) + v + np.roll(v, 1, 0)


def mean_or_none(values):
    return float(np.mean(values)) if np.size(values) else None


def aggregate(rows):
    excluded = {'block', 'founder', 'lineage', 'condition', 'damage'}
    result = dict(lineages=len(rows))
    for key in rows[0] if rows else []:
        if key in excluded:
            continue
        values = [r[key] for r in rows if r[key] is not None]
        if values and not isinstance(values[0], str):
            result[key] = dict(mean=float(np.mean(values)), minimum=float(np.min(values)), maximum=float(np.max(values)))
            if isinstance(values[0], (bool, np.bool_)):
                result[key]['count'] = int(sum(values))
    return result


def write_csv(path, rows):
    with path.open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def analyze(run, output):
    started = time.monotonic()
    cap_cpus(1)
    assert run.is_relative_to(ROOT) and output.is_relative_to(HERE) and not output.exists()
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
    inputs = [Path(__file__), HERE/'verify_transmission_v2.py', HERE/'TRANSMISSION_DIAGNOSIS.md',
        ROOT/'E021_damaged_renewal/analysis/diagnose_boundaries.py',
        ROOT/'E021_damaged_renewal/analysis/verify_boundary_diagnosis.py', ROOT/'common.py', ROOT/'run_python.sh']
    inputs += [run/name for name in ('COMPLETE.json', 'INDEPENDENT_AUDIT.json', 'summary.json', 'manifest.json')]
    new_run(output, inputs, dict(experiment='E022', analysis='post_hoc_transmission_diagnosis',
        source=str(run.relative_to(ROOT)), new_simulation=False, units=units))
    dump(output/'status.json', dict(status='RUNNING', utc=utc()))
    fixture = dict(**checks(), signed_known_graphs=signed_checks())
    checked = {}

    def verify(name):
        digest = sha(run/name)
        assert digest == complete['outputs_sha256'][name], name
        checked[name] = digest

    for name in ('summary.json', 'observations.csv', 'body_observations.csv'):
        verify(name)
    terminal_csv, body_csv = {}, {}
    with (run/'observations.csv').open(newline='') as handle:
        for r in csv.DictReader(handle):
            if r['horizon'] == '1' and r['arm'] == 'own':
                key = (int(r['block']), r['condition'], int(r['founder']), int(r['lineage']), int(r['cue']), r['damage'])
                assert key not in terminal_csv
                terminal_csv[key] = r
    with (run/'body_observations.csv').open(newline='') as handle:
        for r in csv.DictReader(handle):
            key = (int(r['block']), r['condition'], int(r['founder']), int(r['lineage']), int(r['cue']))
            assert key not in body_csv
            body_csv[key] = r
    boundary_rows, terminal_rows = [], []
    for block in scientific['blocks']:
        for name in (f'source_{block:06d}.npz', f'boundary_{block:06d}_g1.npz', f'assay_{block:06d}_h1.npz'):
            verify(name)
        with np.load(run/f'source_{block:06d}.npz', allow_pickle=False) as raw:
            assert np.array_equal(raw['ports'], PORTS)
            source = np.repeat(raw['acquired'][1, :, None], scientific['cfg']['recipients'], axis=1)
        with np.load(run/f'boundary_{block:06d}_g1.npz', allow_pickle=False) as raw:
            incoming, outgoing, effective, erased, masks, body_masks, body, late, computed, denominators = [raw[k] for k in
                ('incoming', 'outgoing', 'read_packets', 'erased_packets', 'renewal_mask', 'body_masks',
                 'developed_end', 'developed_late_ports', 'computed_packets', 'read_denominators')]
        assert np.array_equal(incoming, np.repeat(source[None], 8, axis=0))
        assert (masks.sum(axis=(-2, -1)) == 24).all() and not (masks & PORTS.any(axis=0)).any()
        assert not body_masks[3].any()
        assert np.array_equal(body_masks[[0, 1, 2, 4, 5]], np.repeat(masks[None], 5, axis=0))
        assert not (body*body_masks[:, :, :, None]).any() and not erased.any()
        x = np.tanh(3*body)
        products = np.stack((x*np.roll(x, -1, -1), x*np.roll(x, -1, -2)), axis=-3)
        assert np.array_equal(encode(products.mean(axis=3)), computed)
        assert np.array_equal(outgoing[[0, 1, 2, 3, 6]], computed[[0, 1, 2, 3, 4]])
        assert not outgoing[7].any() and np.array_equal(outgoing[4], source)
        assert np.array_equal(outgoing[5], encode(decode(source)*edges(masks)))
        expected_read = encode(decode(incoming[list(ACTIVE)])*edges(body_masks)); expected_read[4] = 0
        assert np.array_equal(effective, expected_read)
        original, weights = decode(source), decode(outgoing)
        body_window, body_end = late.mean(axis=0), ports(body)
        body_window_margin, body_end_margin = margin(body_window), margin(body_end)
        with np.load(run/f'assay_{block:06d}_h1.npz', allow_pickle=False) as raw:
            assert np.array_equal(raw['packets'][:, :, :, 0], outgoing)
            terminal_masks = raw['masks']
            terminal_window = raw['late_ports'].mean(axis=0)[..., 0, :]
            terminal_end = raw['end'][..., 0, :, :]
        assert not terminal_masks[:, :, 0].any()
        for f in range(4):
            for r in range(scientific['cfg']['recipients']):
                surviving = edges(masks[f, r])
                physical = [widest(edges(terminal_masks[f, r, d]).astype(float)) for d in range(3)]
                for n, condition in enumerate(CONDITIONS):
                    w, ref = weights[n, f, r], original[f, r]
                    support = np.ones_like(surviving) if n in (3, 4) else surviving
                    common = (w != 0) & (ref != 0)
                    row = dict(block=block, condition=condition, founder=f, lineage=r,
                        outgoing_mean_abs=float(np.abs(w).mean()), outgoing_zero_edges=int((w == 0).sum()),
                        physically_deleted_edges=int((~support).sum()),
                        additional_zero_edges=int(((w == 0) & support).sum()),
                        surviving_mean_abs=float(np.abs(w[support]).mean()),
                        original_surviving_mean_abs=float(np.abs(ref[support]).mean()),
                        survivor_mean_abs_change=float(np.abs(w[support]-ref[support]).mean()),
                        sign_change_fraction=mean_or_none(np.sign(w[common]) != np.sign(ref[common])),
                        body_window_both=None, body_end_both=None, body_cue_score_disagreements=None,
                        body_window_mean_margin=None, body_end_mean_margin=None,
                        body_cue_opposition=None, body_edge_cue_sign_conflict=None,
                        body_mean_abs_alive=None, reading_output_denominator_mean=None)
                    if n in ACTIVE:
                        a = ACTIVE.index(n); alive = ~body_masks[a, f, r]
                        prod = products[a, f, r]
                        ep = edges(body_masks[a, f, r])
                        row.update(body_window_both=bool((body_window_margin[a, f, r] > .25).all()),
                            body_end_both=bool((body_end_margin[a, f, r] > .25).all()),
                            body_cue_score_disagreements=int(((body_window_margin[a, f, r] > .25) != (body_end_margin[a, f, r] > .25)).sum()),
                            body_window_mean_margin=float(body_window_margin[a, f, r].mean()),
                            body_end_mean_margin=float(body_end_margin[a, f, r].mean()),
                            body_cue_opposition=float((body[a, f, r, 0, alive]*body[a, f, r, 1, alive] < 0).mean()),
                            body_edge_cue_sign_conflict=float((prod[0, ep]*prod[1, ep] < 0).mean()),
                            body_mean_abs_alive=float(np.abs(body[a, f, r][:, alive]).mean()),
                            reading_output_denominator_mean=float(denominators[a, f, r][PORTS[1] | PORTS[2]].mean()))
                        for c, cue in enumerate((1, -1)):
                            saved = body_csv[(block, condition, f, r, cue)]
                            assert np.array_equal(body_window[a, f, r, c], [float(saved['output_A']), float(saved['output_B'])])
                            assert body_window_margin[a, f, r, c] == float(saved['margin'])
                            assert (body_window_margin[a, f, r, c] > .25) == bool(int(saved['success']))
                    boundary_rows.append(row)
                    for d, damage in enumerate(DAMAGE):
                        ew = w*edges(terminal_masks[f, r, d])
                        pg = widest(ew); sg = signed_graph(ew, RULES[f])
                        values = terminal_window[n, f, r, :, d]
                        end = terminal_end[n, f, r, :, d]
                        m = np.minimum(RULES[f]*CUES*values[:, 0], -RULES[f]*CUES*values[:, 1])
                        ep = ports(end)
                        em = np.minimum(RULES[f]*CUES*ep[:, 0], -RULES[f]*CUES*ep[:, 1])
                        for c, cue in enumerate((1, -1)):
                            saved = terminal_csv[(block, condition, f, r, cue, damage)]
                            assert np.array_equal(values[c], [float(saved['output_A']), float(saved['output_B'])])
                            assert m[c] == float(saved['margin']) and (m[c] > .25) == bool(int(saved['success']))
                        strength = incident(np.abs(ew)); supported = strength > 0
                        both = bool((m > .25).all())
                        failure = 'success' if both else ('disconnected' if pg['reachable_output_cells'] < 8 else
                            'signed_component_conflict' if not sg['signed_source_consistent'] else
                            'output_cell_sign_mismatch' if not sg['signed_all_outputs_aligned'] else 'compatible_graph_failed')
                        terminal_rows.append(dict(block=block, condition=condition, founder=f, lineage=r, damage=damage,
                            assay_both=both, assay_end_both=bool((em > .25).all()),
                            mean_margin=float(m.mean()), positive_cue_error=error_type(values[0], RULES[f], 1),
                            negative_cue_error=error_type(values[1], RULES[f], -1), failure_class=failure,
                            effective_nonzero_edges=int((ew != 0).sum()), effective_mean_abs=float(np.abs(ew).mean()),
                            output_incident_mean=float(strength[PORTS[1] | PORTS[2]].mean()),
                            output_incident_min=float(strength[PORTS[1] | PORTS[2]].min()),
                            end_cue_opposition_supported=mean_or_none(end[0, supported]*end[1, supported] < 0),
                            physical_reachable_output_cells=physical[d]['reachable_output_cells'],
                            physical_source_component_cells=physical[d]['source_component_cells'], **pg, **sg))
        print(f'Analyzed block {block}', flush=True)
    variable_seconds = time.monotonic()-started
    write_csv(output/'boundaries.csv', boundary_rows); write_csv(output/'terminal.csv', terminal_rows)
    result = summarize(boundary_rows, terminal_rows, scientific, units, fixture, checked, variable_seconds)
    dump(output/'summary.json', result)
    dump(output/'provenance.json', dict(source_complete_sha256=sha(run/'COMPLETE.json'),
        source_audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), consumed_source_outputs=checked,
        frozen_source_inputs_verified=True, script_sha256=sha(Path(__file__))))
    render(output, result)
    dump(output/'status.json', dict(status='COMPLETE', utc=utc(), seconds=time.monotonic()-started))
    finish(output, started, dict(analysis='saved_transmission_diagnosis', new_simulation=False))
    print(json.dumps(dict(output=str(output.relative_to(ROOT)), variable_seconds=variable_seconds,
        seconds=time.monotonic()-started, source_outputs_verified=len(checked), boundary_rows=len(boundary_rows), terminal_rows=len(terminal_rows)), indent=2))


def summarize(boundaries, terminals, scientific, units, fixture, checked, seconds):
    groups = {}
    for condition in CONDITIONS:
        b = [r for r in boundaries if r['condition'] == condition]
        group = dict(boundary=aggregate(b), terminal={}, body_to_terminal={}, intact_to_terminal={})
        if condition in scientific['body_reading']:
            expected = scientific['body_reading'][condition]['both_cues']
            assert group['boundary']['body_window_both']['mean'] == expected['mean']
            for i, block in enumerate(scientific['blocks']):
                assert np.mean([r['body_window_both'] for r in b if r['block'] == block]) == expected['block_means'][i]
            group['body_window_to_end'] = transitions([r['body_window_both'] for r in b], [r['body_end_both'] for r in b])
            group['body_individual_cue_disagreements'] = sum(r['body_cue_score_disagreements'] for r in b)
        intact = [r for r in terminals if r['condition'] == condition and r['damage'] == 'intact']
        for damage in DAMAGE:
            t = [r for r in terminals if r['condition'] == condition and r['damage'] == damage]
            stats = aggregate(t)
            expected = scientific['groups']['1'][condition]['both_cues'][damage]['own']
            assert stats['assay_both']['mean'] == expected['mean']
            for i, block in enumerate(scientific['blocks']):
                assert np.mean([r['assay_both'] for r in t if r['block'] == block]) == expected['block_means'][i]
            stats['failure_classes'] = dict(Counter(r['failure_class'] for r in t))
            stats['individual_cue_errors'] = dict(Counter(r[k] for r in t for k in ('positive_cue_error', 'negative_cue_error')))
            stats['any_output_disconnected'] = sum(r['reachable_output_cells'] < 8 for r in t)
            stats['physical_any_output_disconnected'] = sum(r['physical_reachable_output_cells'] < 8 for r in t)
            stats['success_descriptive'] = aggregate([r for r in t if r['assay_both']])
            stats['failure_descriptive'] = aggregate([r for r in t if not r['assay_both']])
            group['terminal'][damage] = stats
            if condition in scientific['body_reading']:
                group['body_to_terminal'][damage] = transitions([r['body_end_both'] for r in b], [r['assay_both'] for r in t])
            group['intact_to_terminal'][damage] = transitions([r['assay_both'] for r in intact], [r['assay_both'] for r in t])
        groups[condition] = group
    paired = {}
    for other in CONDITIONS:
        if other == 'strength_compensated': continue
        paired[other] = {}
        for damage in DAMAGE:
            a = [r['assay_both'] for r in terminals if r['condition'] == other and r['damage'] == damage]
            b = [r['assay_both'] for r in terminals if r['condition'] == 'strength_compensated' and r['damage'] == damage]
            paired[other][damage] = transitions(a, b)
    return dict(status='DESCRIPTIVE_SAVED_DATA_REVIEW', utc=utc(), units=units, new_simulation=False,
        source_scientific_status=scientific['status'], source_primary=scientific['primary'],
        source_full_qualification=scientific['full_compensation_qualified'], checks=fixture,
        groups=groups, other_to_strength_transitions=paired, boundary_rows=len(boundaries),
        terminal_rows=len(terminals), source_outputs_verified=len(checked), variable_seconds=seconds,
        all_capture_bytes_and_packet_constraints_verified=True,
        all_body_and_own_terminal_csv_rows_and_block_means_reproduced=True,
        limits=['Post-hoc descriptive analysis; no new confirmatory endpoint or causal estimate.',
            'Static connectivity, absolute-weight capacities and signed consistency are not functional assays.',
            'Requiring every output-cell sign is stricter than the original port-average criterion.',
            'Whole-cohort and success/failure conditional summaries retain all cases; no rescue is tested.',
            'No new dynamics, terminal-reader change or serial compensated-renewal result.'])


def render(output, result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    groups = result['groups']; n = result['units']['lineages']
    lines = ['# E022 saved-state transmission diagnosis', '',
        '**Post-hoc descriptive analysis; no new dynamics.**', '',
        f"All {result['units']['blocks']} blocks and {n} lineages retained in all eight conditions and all three terminal injury panels.", '',
        f"Original full verdict: {result['source_scientific_status']}. This review does not change it.", '',
        '## Capture boundary', '',
        '| Condition | Averaged body success | Instantaneous capture success | Cue-score disagreements | Intact terminal success |',
        '| --- | --- | --- | --- | --- |']
    for c in CONDITIONS:
        g = groups[c]; b = g['boundary']
        def count(key): return f"{b[key]['count']}/{n}" if key in b else '—'
        lines.append(f"| {c} | {count('body_window_both')} | {count('body_end_both')} | {g.get('body_individual_cue_disagreements', '—')} | {g['terminal']['intact']['assay_both']['count']}/{n} |")
    lines += ['', 'Every computed immediate capture was rebuilt byte-for-byte from saved activity; all copying, erasure and outgoing-record constraints matched.', '',
        '| Condition | Mean zero edges / 512 | Mean extra zeros on surviving edges | Mean absolute surviving weight | Original on same edges | Sign changes vs original | Body cue opposition |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for c in CONDITIONS:
        b = groups[c]['boundary']
        def value(key): return f"{b[key]['mean']:.4f}" if key in b else '—'
        lines.append(f"| {c} | "+' | '.join(value(k) for k in ('outgoing_zero_edges', 'additional_zero_edges', 'surviving_mean_abs', 'original_surviving_mean_abs', 'sign_change_fraction', 'body_cue_opposition'))+' |')
    lines += ['', '## Fresh-body function and static graph checks', '',
        '| Condition | Injury | Both cues correct | Any output disconnected | Signed input component inconsistent | All output cells sign-compatible | Mean weakest-output path capacity |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for c in CONDITIONS:
        for d in DAMAGE:
            t = groups[c]['terminal'][d]
            lines.append(f"| {c} | {d} | {t['assay_both']['count']}/{n} | {t['any_output_disconnected']}/{n} | {n-t['signed_source_consistent']['count']}/{n} | {t['signed_all_outputs_aligned']['count']}/{n} | {t['weakest_output_path_capacity']['mean']:.4f} |")
    lines += ['', '## Strength-compensated lineage transitions', '']
    g = groups['strength_compensated']
    for d in DAMAGE:
        t = g['terminal'][d]
        lines += [f"**{d}:**", '',
            'Capture state → terminal: `'+json.dumps(g['body_to_terminal'][d], sort_keys=True)+'`.', '',
            'Intact terminal → this injury: `'+json.dumps(g['intact_to_terminal'][d], sort_keys=True)+'`.', '',
            'Failure partition (success retained): `'+json.dumps(t['failure_classes'], sort_keys=True)+'`.', '',
            'Individual-cue outcomes: `'+json.dumps(t['individual_cue_errors'], sort_keys=True)+'`.', '']
    lines += ['## Limits', '', *['- '+v for v in result['limits']], '',
        '[Boundary rows](boundaries.csv), [terminal rows](terminal.csv), [full summaries and paired transitions](summary.json), [figure](diagnosis.png), [provenance](provenance.json).', '']
    (output/'REPORT.md').write_text('\n'.join(lines))
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    names = [('baseline','Baseline','#888888'), ('degree_compensated','Degree','#316ba5'),
        ('strength_compensated','Strength','#008d86'), ('intact_renewed','Intact renewal','#4b963c'),
        ('masked_copy','Masked copy','#b77b2a')]
    for c, label, color in names:
        g = groups[c]
        body = g['boundary'].get('body_end_both', {}).get('mean', np.nan)
        axes[0].plot(range(4), [100*body]+[100*g['terminal'][d]['assay_both']['mean'] for d in DAMAGE], 'o-', label=label, color=color)
    axes[0].set(xticks=range(4), xticklabels=['Capture','Intact','Scattered','Square'], ylim=(-3, 103), ylabel='Both cues correct (%)', title='Body behavior and fresh-body function')
    axes[0].legend(fontsize=8)
    pos = np.arange(len(names))
    axes[1].bar(pos-.18, [groups[c]['boundary']['surviving_mean_abs']['mean'] for c, _, _ in names], width=.36, label='Captured / copied')
    axes[1].bar(pos+.18, [groups[c]['boundary']['original_surviving_mean_abs']['mean'] for c, _, _ in names], width=.36, label='Original on same edges', color='#bbbbbb')
    axes[1].set(xticks=pos, xticklabels=[label.replace(' ', '\n') for _, label, _ in names], ylim=(0, 1.05), ylabel='Mean absolute surviving edge weight', title='Record values on surviving edges')
    axes[1].legend(fontsize=8)
    bottom = np.zeros(3)
    for key, label, color in [('disconnected','Output disconnected','#bb5656'),
        ('signed_component_conflict','Signed component conflict','#9768ad'),
        ('output_cell_sign_mismatch','Output-cell sign mismatch','#c28a36'),
        ('compatible_graph_failed','Compatible graph, failed dynamics','#337e9c')]:
        heights = np.array([groups['strength_compensated']['terminal'][d]['failure_classes'].get(key, 0) for d in DAMAGE])
        axes[2].bar(range(3), heights, bottom=bottom, label=label, color=color); bottom += heights
    axes[2].set(xticks=range(3), xticklabels=['Intact','Scattered','Square'], ylabel='Failed lineages (count)', title='Strength candidate: static failure partition')
    axes[2].legend(fontsize=7)
    for ax in axes: ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True)
    fig.suptitle(f'E022 saved evidence — {result["units"]["blocks"]} blocks / {n} lineages; descriptive, no new dynamics')
    fig.tight_layout()
    fig.savefig(output/'diagnosis.png', dpi=170); fig.savefig(output/'diagnosis.svg')
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); destination = args.output.resolve()
    try:
        analyze(args.source.resolve(), destination)
    except BaseException:
        if destination.is_relative_to(HERE) and (destination/'status.json').exists() and not (destination/'COMPLETE.json').exists():
            dump(destination/'FAILED.json', dict(status='FAILED', utc=utc(), traceback=traceback.format_exc()))
            dump(destination/'status.json', dict(status='FAILED', utc=utc()))
        raise
