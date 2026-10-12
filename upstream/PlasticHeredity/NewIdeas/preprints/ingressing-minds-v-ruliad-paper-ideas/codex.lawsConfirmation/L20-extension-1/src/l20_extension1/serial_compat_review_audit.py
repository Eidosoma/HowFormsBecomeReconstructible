"""Fresh, independent saved-output checks and descriptive phase accounting."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
RUN = 'l20_extension1_serial_compatible_feedback_v1_attempt1'
REVIEW = RUN + '_saved_review_v1_attempt1'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def budget(selected, kind):
    result = []
    for gi in range(3):
        data = []
        for row in selected:
            g = row['paths'][kind]['generations'][gi]
            endpoints = np.array([g['incoming_shape'], g['read_end_shape'],
                                  g['write_end_shape'], g['outgoing_shape']])
            changes = np.diff(endpoints)
            np.testing.assert_allclose(changes.sum(), endpoints[-1]-endpoints[0], atol=1e-14, rtol=0)
            data.append(np.r_[changes, endpoints[-1]-endpoints[0]])
        a = np.array(data)
        result.append(dict(generation=gi+1, count=len(selected),
            columns=['incoming_to_read_R', 'read_R_to_write_R', 'write_R_to_record', 'total'],
            means=a.mean(axis=0).tolist(), negative_counts=(a < 0).sum(axis=0).tolist()))
    return result


def main():
    start = time.monotonic()
    assert len(os.sched_getaffinity(0)) <= 6
    assert all(os.environ.get(k) == '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'))
    dest = ROOT/'logs/d145_saved_review_audit_v1.json'
    if dest.exists():
        raise FileExistsError('single-use audit receipt')
    directory = ROOT/'outputs'/REVIEW
    receipt = load(directory/'COMPLETE.json')
    assert receipt['status'] == 'COMPLETE' and receipt['new_dynamics'] == 0
    assert digest(ROOT/'runs'/RUN/'COMPLETE.json') == receipt['source_complete_sha256']
    for section in ('consumed_inputs', 'review_code_and_plan_sha256', 'output_sha256'):
        for path, expected in receipt[section].items():
            assert digest(path) == expected, path
    xml = ROOT/'logs/d145_saved_review_qualification_a.xml'
    tree = ET.parse(xml).getroot()
    assert len(tree.findall('.//testcase')) == 15
    assert not any(tree.findall('.//'+tag) for tag in ('failure', 'error', 'skipped'))
    rows, summary = load(directory/'rows.json'), load(directory/'summary.json')
    expected_keys = {(b, l, n, r) for b in range(92000, 92016) for l in range(4) for n in range(2) for r in (0, 1)}
    assert len(rows) == 256 and {(r['block'], r['life'], r['noise'], r['role']) for r in rows} == expected_keys
    rows_by_block = {b: [r for r in rows if r['block'] == b] for b in range(92000, 92016)}
    y, x = np.indices((16, 16))
    t = np.stack((y < 8, x % 8 < 4))
    # Re-express original endpoint as qualifying matches, independently of the
    # review module's contribution function. Check every profile against D145.
    original = ROOT/'outputs'/RUN
    for block, current in rows_by_block.items():
        with np.load(original/f'block_{block}.npz', allow_pickle=False) as raw:
            terminal = raw['terminal_states']
            profiles = {phase: raw[phase+'_values'] for phase in ('read', 'write', 'terminal')}
            records = raw['record_values']
            for row in current:
                l, n, r = row['life'], row['noise'], row['role']
                ci = {'zero': 8*r, 'q4': 8*r+1}
                for gi in range(3):
                    v = {k: terminal[l, n, c, gi, -1, 0] for k, c in ci.items()}
                    active = {k: np.abs(value) > .2 for k, value in v.items()}
                    scores = {k: (np.equal(value > 0, t[r]).astype(int)-np.equal(value > 0, t[1-r]).astype(int))*active[k]
                              for k, value in v.items()}
                    delta = scores['q4']-scores['zero']
                    p = row['paired'][gi]['terminal_preference_parts']
                    assert p['net_units'] == int(delta.sum())
                    assert p['changed_contribution_cells'] == np.count_nonzero(delta)
                    assert p['both_active_sign_changed_cells'] == np.count_nonzero((delta != 0) & active['q4'] & active['zero'])
                    for key, mask in (
                        ('both_active_sign_net_units', active['q4'] & active['zero']),
                        ('compatible_only_active_net_units', active['q4'] & ~active['zero']),
                        ('zero_only_active_net_units', ~active['q4'] & active['zero'])):
                        assert p[key] == int(delta[mask].sum())
                    assert row['paired'][gi]['terminal_preference'] == delta.mean()
                    for kind, c in ci.items():
                        g = row['paths'][kind]['generations'][gi]
                        assert g['terminal_preference'] == scores[kind].mean()
                        for phase in ('read', 'write', 'terminal'):
                            saved = profiles[phase][l, n, c, gi]
                            np.testing.assert_allclose(g['profiles'][phase]['preference'], saved[:, 0], atol=1e-14, rtol=0)
                            np.testing.assert_allclose(g['profiles'][phase]['reference_shape'], saved[:, 1], atol=1e-14, rtol=0)
                        np.testing.assert_allclose([g['incoming_shape'], g['outgoing_shape']],
                            records[l, n, c, gi], atol=1e-14, rtol=0)
    families = {}
    for role in (0, 1):
        rr = sorted([r for r in rows if r['role'] == role], key=lambda r:(r['block'], r['life'], r['noise']))
        pref = np.array([r['paired'][-1]['terminal_preference'] for r in rr])
        change = np.array([r['paths']['q4']['generations'][-1]['outgoing_shape']-
                           r['paths']['q4']['generations'][0]['outgoing_shape'] for r in rr])
        f = summary['families'][str(role)]
        np.testing.assert_allclose(pref.reshape(16, 4, 2).mean((1, 2)), f['primary_reproduction']['block_means'], atol=1e-14, rtol=0)
        np.testing.assert_allclose(change.reshape(16, 4, 2).mean((1, 2)),
            f['serial_shape']['original_inference_reproduced']['block_means'], atol=1e-14, rtol=0)
        masks = {'all': np.ones(128, bool), 'late_shape_losses': change < 0,
                 'late_shape_gains': change > 0, 'final_preference_losses': pref < 0}
        groups = {}
        for name, mask in masks.items():
            selected = [r for r, keep in zip(rr, mask) if keep]
            group = dict(count=len(selected), q4=budget(selected, 'q4'), zero=budget(selected, 'zero'))
            group['later_q4_phase_sums'] = np.sum([g['means'] for g in group['q4'][1:]], axis=0).tolist()
            np.testing.assert_allclose(group['later_q4_phase_sums'][-1], change[mask].mean(), atol=1e-14, rtol=0)
            groups[name] = group
        exceptions = [r for r in rr if r['paired'][-1]['terminal_preference'] < 0]
        groups['exception_crosscheck'] = dict(count=len(exceptions),
            outgoing_shape_worse=sum(r['paired'][-1]['outgoing_shape'] < 0 for r in exceptions),
            outgoing_shape_better=sum(r['paired'][-1]['outgoing_shape'] > 0 for r in exceptions),
            no_scoring_sign_changes=sum(r['paired'][-1]['terminal_preference_parts']['both_active_sign_changed_cells'] == 0 for r in exceptions),
            net_sign_component_zero=sum(r['paired'][-1]['terminal_preference_parts']['both_active_sign_net_units'] == 0 for r in exceptions),
            sign_net_total=sum(r['paired'][-1]['terminal_preference_parts']['both_active_sign_net_units'] for r in exceptions),
            total_net_units=sum(r['paired'][-1]['terminal_preference_parts']['net_units'] for r in exceptions))
        groups['late_loss_preference_signs'] = dict(negative=int(np.count_nonzero(pref[change < 0] < 0)),
            positive=int(np.count_nonzero(pref[change < 0] > 0)), zero=int(np.count_nonzero(pref[change < 0] == 0)))
        families[str(role)] = groups
    result = dict(passes=True, utc=datetime.now(timezone.utc).isoformat(), new_dynamics=0,
        review_complete_sha256=digest(directory/'COMPLETE.json'), checker_sha256=digest(__file__),
        qualification_tests=15, qualification_sha256=digest(xml), pairs_checked=256,
        condition_generation_endpoints_checked=1536, post_hoc=True,
        phase_differences_are_shape_accounting_not_causal_information_losses=True,
        wall_seconds=time.monotonic()-start, families=families)
    with dest.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='families'}, indent=2))


if __name__ == '__main__':
    main()
