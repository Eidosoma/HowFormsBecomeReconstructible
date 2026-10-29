#!/usr/bin/env python3
"""Verify and summarize the retained v1.2 selection; no dynamics or inference.

Uses the portable text/JSON package, not the external NPZ archives. Recognition
and every native summary comparison are recomputed from saved per-record scores.
This is an arithmetic check, not a replay of the original field trajectories.
"""
from pathlib import Path
import hashlib
import json
import math
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('accuracy', 'partner_accuracy', 'preference', 'projection_gap',
          'sign_fidelity', 'theta_corr_parent', 'theta_corr_partner')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((ROOT / 'reviews/V1.2_EVIDENCE_SOURCES.json').read_text())
    package = ROOT / manifest['package']['path']
    assert sha(package.read_bytes()) == manifest['package']['sha256']
    with zipfile.ZipFile(package) as archive:
        raw = {item['member']: archive.read(item['member']) for item in manifest['sources']}
    for item in manifest['sources']:
        assert len(raw[item['member']]) == item['bytes']
        assert sha(raw[item['member']]) == item['sha256']
    read = lambda name: json.loads(raw[name])
    checks = 0

    def equal(actual, expected):
        nonlocal checks
        assert math.isfinite(actual) and abs(actual - expected) <= 2e-12, (actual, expected)
        checks += 1

    studies = {}
    for study in ('D184', 'D186'):
        summary = read(f'external/{study}/SUMMARY.json')
        complete = read(f'external/{study}/COMPLETE.json')
        assert complete['status'] == 'COMPLETE' and not complete['confirmation']
        assert complete['summary_sha256'] == sha(raw[f'external/{study}/SUMMARY.json'])
        assert complete['verification']['passes']
        blocks = summary['blocks']
        assert blocks == [30056, 30057, 30058, 30059]
        records = {b: read(f'external/{study}/tissue_{b}/records.json') for b in blocks}
        arms = summary['arm_summaries']
        assert all(set(records[b]) == set(arms) for b in blocks)
        for name, arm in arms.items():
            pooled = []
            for b in blocks:
                rows = records[b][name]
                assert [(r['world'], r['message'], r['replicate']) for r in rows] == [(i, i // 4, i % 4) for i in range(16)]
                pooled.extend(rows)
                if 'block_arm_summaries' in summary:
                    declared = summary['block_arm_summaries'][str(b)][name]
                    for message, values in [(None, declared['mean']), *enumerate(declared['messages'])]:
                        selected = [r for r in rows if message is None or r['message'] == message]
                        for field in values:
                            equal(math.fsum(r[field] for r in selected) / len(selected), values[field])
            for message, values in [(None, arm['mean']), *enumerate(arm['messages'])]:
                selected = [r for r in pooled if message is None or r['message'] == message]
                for field in values:
                    equal(math.fsum(r[field] for r in selected) / len(selected), values[field])
        for name, contrast in summary['equal_block_contrasts'].items():
            for message, values in [(None, contrast['mean']), *enumerate(contrast['messages'])]:
                pairs = [(a, b) for block in blocks for a, b in zip(records[block][contrast['left']], records[block][contrast['right']])
                         if message is None or a['message'] == message]
                for field in values:
                    equal(math.fsum(a[field] - b[field] for a, b in pairs) / len(pairs), values[field])
        studies[study] = {'blocks': blocks, 'records': 64, 'arm_summaries': arms,
                          'block_arm_summaries': summary.get('block_arm_summaries', {}),
                          'equal_block_contrasts': summary['equal_block_contrasts'],
                          'native_verification': complete['verification'],
                          'completed_utc': complete['completed_utc']}
    d = studies['D186']['arm_summaries']
    for arm, expected in {'input__common': .5, 'common__own__live': .5,
                          'capture__common__own__live': .77734375,
                          'capture__common__own__fixed': .734375,
                          'capture__common__own__average': .640625,
                          'capture__common__partner__live': .21875,
                          'capture__common__own__writer_off': .5,
                          'residual__own__live': .87890625,
                          'capture__residual__own__live': .84765625}.items():
        equal(d[arm]['mean']['accuracy'], expected)
    assert [x['accuracy'] for x in d['capture__common__own__live']['messages']] == [.5625, .984375, 1., .5625]
    # Keep the review-facing extract below the public snapshot's ordinary size
    # cap. Every arm/message was checked above and remains in the source ZIP.
    shown = {'input__common', 'input__residual', 'common__own__live',
             'residual__own__live', 'residual__own__average',
             'intact_parent', 'supplied_positive', 'reader_off'}
    for packet in ('common', 'residual'):
        shown.update('capture__' + packet + '__' + arm for arm in
                     ('own__live', 'own__fixed', 'own__average', 'own__reference_held',
                      'own__writer_off', 'partner__live', 'own_scrambled__live',
                      'history_erased__live'))
    for study in studies.values():
        study['arm_summaries'] = {k: v for k, v in study['arm_summaries'].items() if k in shown}
        study['block_arm_summaries'] = {b: {k: v['mean'] for k, v in arms.items() if k in shown}
                                        for b, arms in study['block_arm_summaries'].items()}
        study['equal_block_contrasts'] = {k: {f: v for f, v in c.items() if f != 'messages'}
                                          for k, c in study['equal_block_contrasts'].items()}
    result = {'version': '1.2', 'scope': 'Saved-score arithmetic and frozen identities; no trajectory replay, fitting or new confidence intervals.',
              'estimates_checked': checks, 'sources_checked': len(raw), 'studies': studies,
              'D185_recorded_check': read('external/D185/SAVED_CHECK.json'),
              'all_conditions_and_message_strata_retained_in_source_package': True}
    serialized = json.dumps(result, indent=2) + '\n'
    assert len(serialized.encode()) <= 256 * 1024
    (ROOT / 'paper_assets/data/evidence-update-v1.2.json').write_text(serialized)
    receipt = {k: v for k, v in result.items() if k not in ('studies', 'D185_recorded_check')}
    receipt.update(status='PASS', new_dynamics=False, original_qualification_changed=False)
    (ROOT / 'reviews/V1.2_EVIDENCE_VALIDATION.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
