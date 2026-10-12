"""Recount the saved paired outcomes without importing the experiment runner."""
from collections import Counter
import hashlib

import numpy as np
from common import ROOT, arrays, equal, read, sha, stamp, write


def main():
    manifest = read(ROOT / 'FROZEN.json')
    for name, digest in manifest['files_sha256'].items():
        assert sha(ROOT / name) == digest, name
    selection = read(ROOT / 'SELECTION.json')
    complete = read(ROOT / 'run' / 'COMPLETE.json')
    for name, digest in complete['files_sha256'].items():
        assert sha(ROOT / 'run' / name) == digest, name
    assert len(selection['events']) == len(complete['rows']) == 46
    counts = Counter(dict(rescue=0, both_fail=0, harm=0, both_pass=0))
    groups = {'by_history': {}, 'by_generation': {}}
    once = counts.copy()
    failures = []
    for event, row in zip(selection['events'], complete['rows'], strict=True):
        assert (event['block'], event['case'], event['generation']) == (row['block'], row['case'], row['generation'])
        source = arrays(ROOT / event['fixture'], event['fixture_sha256'])
        data = arrays(ROOT / 'run' / row['file'], row['sha256'])
        assert hashlib.sha256(data['incoming'].tobytes()).hexdigest() == event['incoming_sha256']
        equal(data['packets'][0], source['incoming'], 'no-repair intervention')
        equal(data['packets'][0], source['prepared'][0], 'factual packet')
        for field in ('birth', 'mask'):
            equal(data[field], source[field], 'saved ' + field)
        for field in ('end', 'mean_ports'):
            equal(data[field][:1], source[field], 'factual ' + field)
        equal(data['port_windows'][:, :1], source['port_windows'], 'factual window')
        assert data['port_windows'].shape == (32, 2, 2, 2)
        # Sum each observed time point explicitly, then score all four cue/port values.
        means = np.zeros((2, 2, 2))
        for frame in data['port_windows']:
            means += frame
        means /= 32
        equal(means, data['mean_ports'], 'independent temporal mean')
        signed = []
        for intervention in range(2):
            vals = []
            for cue in range(2):
                for port in range(2):
                    target = (1 if event['case'] // 4 in (0, 2) else -1) * (1 if cue == port else -1)
                    vals.append(float(means[intervention, cue, port]) * target)
            signed.append(min(vals))
        equal(np.array(signed), data['min_margin'], 'independent margins')
        assert signed[0] == event['margin'] == row['no_repair_margin']
        assert signed[1] == row['repair_margin']
        assert signed[0] <= .25 and not source['applied'][0]
        category = 'rescue' if signed[1] > .25 else 'both_fail'
        assert row['outcome'] == category
        equal(np.array([v > .25 for v in signed]), data['both_pass'], 'strict threshold')
        before = np.frombuffer(data['packets'][0].tobytes(), dtype='<f8').reshape(2, 16, 16)
        after = np.frombuffer(data['packets'][1].tobytes(), dtype='<f8').reshape(2, 16, 16)
        equal(after[before != 0], before[before != 0], 'unchanged nonzero edges')
        for plane in range(2):
            for y in range(16):
                for x in range(16):
                    if before[plane, y, x] == 0:
                        yy, xx = (y, (x + 1) % 16) if plane == 0 else ((y + 1) % 16, x)
                        expected = float(data['magnitude']) * int(data['optimizer_signs'][y, x]) * int(data['optimizer_signs'][yy, xx])
                        assert after[plane, y, x] == expected
        assert np.count_nonzero((before == 0) & (after != 0)) == row['added_edges']
        counts[category] += 1
        for name, key in (('by_history', event['history']), ('by_generation', str(event['generation']))):
            groups[name].setdefault(key, Counter(dict(rescue=0, both_fail=0, harm=0, both_pass=0)))[category] += 1
        if event['once_uninterrupted']:
            once[category] += 1
        if category == 'both_fail':
            failures.append(dict(block=event['block'], case=event['case'], generation=event['generation'],
                                 no_repair_margin=signed[0], repair_margin=signed[1]))
    assert dict(counts) == complete['counts'] and counts['rescue'] + counts['both_fail'] == 46
    assert once == complete['once_uninterrupted_subset'] and sum(once.values()) == 20
    for name, value in groups.items():
        # Include empty histories if the selected subset ever changes in a future version.
        assert {k: dict(v) for k, v in value.items()} == complete[name]
    assert complete['independent_optimizer_checks'] == 46
    assert complete['independent_flat_read_contexts'] == complete['primary_read_contexts'] == 92
    assert complete['all_factual_and_independent_bytes_match']
    result = dict(status='PASS', at_utc=stamp(), counts=dict(counts), independent_recount_contexts=46,
        selected_blocks=len({e['block'] for e in selection['events']}), by_history=groups['by_history'],
        by_generation=groups['by_generation'], once_uninterrupted_subset=once,
        both_fail_contexts=failures, frozen_inputs_checked=len(manifest['files_sha256']),
        source_complete_sha256=complete['source_complete_sha256'], run_complete_sha256=sha(ROOT / 'run' / 'COMPLETE.json'),
        selection_sha256=sha(ROOT / 'SELECTION.json'), original_prospective_verdict='UNRESOLVED')
    write(ROOT / 'VERIFICATION.json', result)
    rescue = counts['rescue']
    lines = [f'Current-boundary repair rescued {rescue}/46 ({100 * rescue / 46:.1f}%) selected failures; {counts["both_fail"]}/46 still failed.',
        '', 'These are every first later failure in the six-repair branch of the completed 132-block cohort, drawn from 36 blocks. All occurred at the second consecutive unrepaired reconstruction. The 46-case selection and analysis were frozen before generating these counterfactuals.',
        '', 'Each pair starts from the same saved incoming packet and uses the same injury, reset and ongoing independent cue forcing. The supplied apparatus and strict four-margin >0.25 success test are unchanged.',
        '', 'Acquisition history | Rescued | Still failed', '--- | ---: | ---:']
    for history, counter in groups['by_history'].items():
        lines.append(f'{history} | {counter["rescue"]} | {counter["both_fail"]}')
    lines += ['', f'Among the 20 selected cases where the once-repaired branch had survived uninterrupted, current repair rescued {once["rescue"]}; {once["both_fail"]} still failed. Those branches had different incoming records, so this comparison does not identify how earlier repairs caused their divergence.',
        '', 'Verification passed: all 46 factual reads reproduced saved bytes, all 92 intervention reads agreed byte for byte with the separate flat dynamics implementation, and all 46 repair optimizations agreed with the separate optimizer. Two excluded, already observed qualification cases reproduced both an immediate rescue and an immediate harm. A separate output recount verified the saved windows, margins, strict thresholds and totals.',
        '', 'A rescue establishes that adding this repair at this saved boundary can avert the immediate expression failure under its realized disturbance. Successor writing and continued inheritance after rescue were not simulated. Cases that still fail are not proven irreparable. Because all 46 cases were selected for factual failure, absence of harm in this subset cannot establish safety for passing states. This intervention adds repair calls and does not establish a better policy under the original call budget.',
        '', 'The original prospective doubled-efficiency result remains UNRESOLVED. These findings do not distinguish RDT from ordinary error correction, and the separate implementations belong to the same research programme.',
        '', f'Runtime: {complete["seconds"]:.1f} seconds wall, {complete["cpu_seconds"]:.1f} seconds CPU, one numerical thread. No automatic successor run.',
        '', 'Evidence: [protocol](PROTOCOL.json), [frozen inputs](FROZEN.json), [selection](SELECTION.json), [raw paired results](run/COMPLETE.json), [output verification](VERIFICATION.json).', '']
    with (ROOT / 'REPORT.md').open('x') as f:
        f.write('\n'.join(lines))
    write(ROOT / 'EXPOSURE_AND_DECISIONS.json', dict(at_utc=stamp(), status='COMPLETED_POST_HOC_CAUSAL_AUDIT',
        prior_exposure='All 132-block source outcomes and prior phase/recovery exploration known before design; both qualification interventions already known.',
        newly_exposed='Current-boundary repaired outcomes for all 46 selected first later failures; no new population lineages or stochastic draws.',
        source_complete_sha256=complete['source_complete_sha256'], frozen_sha256=sha(ROOT / 'FROZEN.json'),
        counts=dict(counts), original_prospective_verdict='UNRESOLVED', automatic_successor=False,
        next_research_decision='Use this mechanism audit to design a prospective observable state rule and compare it with ordinary graph diagnostics and timing rules under a fixed call budget; separately test whether an immediate rescue leaves a viable written successor. No such test is launched by this audit.'))
    write(ROOT / 'COMPLETE.json', dict(status='COMPLETE', at_utc=stamp(), counts=dict(counts),
        files_sha256={name: sha(ROOT / name) for name in ('FROZEN.json', 'SELECTION.json', 'qualification/COMPLETE.json',
            'run/COMPLETE.json', 'VERIFICATION.json', 'REPORT.md', 'EXPOSURE_AND_DECISIONS.json')},
        original_prospective_verdict='UNRESOLVED', automatic_successor=False))
    print('Output verification PASS:', dict(counts), flush=True)


if __name__ == '__main__':
    main()
