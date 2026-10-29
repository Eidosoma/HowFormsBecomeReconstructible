"""Render audited D195 panel tables from pinned saved summaries; no dynamics."""

import argparse
import hashlib
import json
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
ROOT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-recipient-pulse-panel-v1')
RUN = 'l22_recipient_pulse_v1_panel_attempt1'
DATA, RECEIPTS = ROOT/'outputs'/RUN, ROOT/'runs'/RUN
AUDIT = ROOT/'audits/status_2026-10-28_attempt1.json'
IDENTITIES = {
    ROOT/'FREEZE.json': 'ab30dbb2ff78bf9bbe0f58e874d3f68e5b1f231a078394aa3cdd9b4ddcddd2bf',
    RECEIPTS/'MANIFEST.json': '2e96e46776c103d3c220d022752eb5aad3d548e1b8bb787e1034800873115908',
    RECEIPTS/'COMPLETE.json': '91b42f866eb5a59da4af8181f88835572a887d2592b78de87b6182c8243e7a6c',
    AUDIT: 'fb0e76efd7008cf0a2874c1d3b430f25b286328e04c49b399b518f0fda70a7d3',
    DATA/'SUMMARY.json': '75f1e1252bf173ddceb7497c20012caea9a98fa072e0cd38334355b14333739b',
}
DEST = WS/'L22-active-form/RECIPIENT_PULSE_PANEL_TABLES.md'
FIELDS = ('accuracy', 'partner_accuracy', 'preference', 'projection_gap',
          'sign_fidelity', 'theta_corr_parent', 'theta_corr_partner')
HEADER = ('Recognition', 'Partner', 'Preference', 'Projection gap',
          'Sign fidelity', 'Parent correlation', 'Partner correlation')
FOCAL = ('disturbance_interaction', 'contingent_body_undisturbed',
         'contingent_body_disturbed', 'own_disturbance', 'yoked_disturbance')


def render():
    for path, digest in IDENTITIES.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path
    summary = json.loads((DATA/'SUMMARY.json').read_text())
    done = json.loads((RECEIPTS/'COMPLETE.json').read_text())
    audit = json.loads(AUDIT.read_text())
    assert done['status'] == 'COMPLETE' and done['verification']['passes']
    assert done['summary_sha256'] == IDENTITIES[DATA/'SUMMARY.json']
    assert audit['status'] == 'SAVED_CHECK_PASSED' and audit['verification'] == done['verification']
    assert audit['new_dynamics'] == 0 and audit['complete_sha256'] == IDENTITIES[RECEIPTS/'COMPLETE.json']
    assert audit['freeze_sha256'] == done['freeze_sha256'] == IDENTITIES[ROOT/'FREEZE.json']
    assert summary['blocks'] == [319100, 319101, 319102, 319103]
    assert summary['records'] == 64 and summary['comparisons'] == 32
    assert summary['benchmark_excluded'] and not summary['confirmatory']
    assert summary['new_founders'] == summary['fitted_models'] == 0
    assert not summary['source_regenerated'] and not summary['old_outcomes_pooled']
    assert summary['uncertainty_interval'] is None
    lines = ['# D195 four-history recipient-pulse panel: saved tables', '',
        '28 October 2026. [Interpretation](RECIPIENT_PULSE_PANEL_RESULTS.md).',
        'Mechanically rendered from the pinned [summary]('+str(DATA/'SUMMARY.json')+').', '',
        'All 64 exposed records, both families, both repair-noise roles and both',
        'reader futures remain. Equal history/future weights; roles averaged within',
        'record and paired draw. The pilot and synthetic qualification cases are excluded.',
        'These are descriptive development results, with no fitted models or intervals.',
        'Recognition and partner recognition are percentages; preference and signed',
        'behavior differences use percentage points. Other metrics use native units.',
        'Gain/harm/tie counts describe the named contrast, including an interaction',
        'when so labelled; a positive interaction need not mean absolute improvement.',
        'Averaged roles are not independent founders. Reciprocal trace-writer equality',
        'is structural. Full record/draw arrays, all nonfocal strata and signed',
        'positive/negative contributions remain in the external summary.', '']

    def add(row):
        lines.append('| '+' | '.join(str(x).replace('|', '\\|') for x in row)+' |')

    def table(title, names):
        lines.extend(['', '## '+title, ''])
        add(names)
        add(['---']*len(names))

    def values(row):
        return [f'{row[k]*(100 if k in FIELDS[:3] else 1):.8f}' for k in FIELDS]

    def counts(transitions):
        cells = []
        for level in ('records', 'draws'):
            for field in ('accuracy', 'preference'):
                c = transitions[field][level]
                assert c['n'] == sum(c[k] for k in ('improved', 'worsened', 'tied'))
                cells.append('/'.join(str(c[k]) for k in ('improved', 'worsened', 'tied')))
        return cells

    count_header = ['Recognition records gain/harm/tie', 'Preference records gain/harm/tie',
                    'Recognition draws gain/harm/tie', 'Preference draws gain/harm/tie']
    sets = [*summary['by_future'].items(), ('both_futures', summary['new_only'])]
    pooled = summary['new_only']['role_mean']
    table('Primary interaction and four cells', ['Family', 'Comparison', *HEADER])
    for family in ('common', 'residual'):
        for kind in ('LL', 'YL', 'LL_pulse', 'YL_pulse'):
            add([family, kind, *values(pooled['arms'][family+'__'+kind]['mean'])])
        row = pooled['contrasts'][family+'__disturbance_interaction']
        coefficients = {family+'__LL_pulse': 1., family+'__YL_pulse': -1.,
                        family+'__LL': -1., family+'__YL': 1.}
        assert row['coefficients'] == coefficients
        for k in FIELDS:
            assert abs(row['mean'][k]-sum(w*pooled['arms'][n]['mean'][k]
                       for n, w in coefficients.items())) < 2e-12
        add([family, 'disturbance_interaction', *values(row['mean'])])

    table('Every named arm', ['Future', 'Arm', *HEADER])
    for label, data in sets:
        assert len(data['named_arms']) == 37
        for name, row in sorted(data['named_arms'].items()):
            add([label, name, *values(row['mean'])])

    table('Role-specific and role-mean arms', ['Future', 'Role', 'Arm', *HEADER])
    for label, data in sets:
        for role, view in [*data['by_role'].items(), ('mean', data['role_mean'])]:
            assert len(view['arms']) == 21 and len(view['contrasts']) == 32
            for name, row in sorted(view['arms'].items()):
                add([label, role, name, *values(row['mean'])])

    table('Every signed comparison', ['Future', 'Role', 'Comparison', *HEADER, *count_header])
    for label, data in sets:
        for role, view in [*data['by_role'].items(), ('mean', data['role_mean'])]:
            for name, row in sorted(view['contrasts'].items()):
                add([label, role, name, *values(row['mean']), *counts(row['transitions']['pooled'])])

    table('Focal block and message strata', ['Family', 'Comparison', 'Stratum', 'Value', *HEADER, *count_header])
    for family in ('common', 'residual'):
        for kind in FOCAL:
            row = pooled['contrasts'][family+'__'+kind]
            for key, labels in [('by_block', summary['blocks']), ('by_message', range(4))]:
                for i, label in enumerate(labels):
                    add([family, kind, key, label, *values(row[key][i]),
                         *counts(row['transitions'][key][i])])
            for b, block in enumerate(summary['blocks']):
                for m in range(4):
                    add([family, kind, 'block/message', f'{block}/{m}',
                         *values(row['by_block_message'][b][m]),
                         *counts(row['transitions']['by_block_message'][b][m])])

    table('Focal leave-one-history-out means', ['Family', 'Comparison', 'Omitted history', *HEADER])
    for family in ('common', 'residual'):
        for kind in FOCAL:
            row = pooled['contrasts'][family+'__'+kind]
            for b, block in enumerate(summary['blocks']):
                omitted = row['leave_one_block_out'][b]
                for k in FIELDS:
                    expected = sum(r[k] for i, r in enumerate(row['by_block']) if i != b)/3
                    assert abs(omitted[k]-expected) < 2e-12
                add([family, kind, block, *values(omitted)])

    table('Primary interaction for every retained record', ['Family', 'History', 'Record', 'Message', 'Replicate', *HEADER])
    for family in ('common', 'residual'):
        records = pooled['contrasts'][family+'__disturbance_interaction']['per_record']
        assert len(records) == 4 and all(len(rows) == 16 for rows in records)
        for block, rows in zip(summary['blocks'], records):
            for i, row in enumerate(rows):
                add([family, block, i, i//4, i%4, *values(dict(zip(FIELDS, row)))])

    lines += ['', '## Costs and provenance', '',
        f'- Execution including independent replay and saved checks: {done["seconds"]:.9f} s; complete {done["completed_utc"]}.',
        f'- Separate saved-only audit: {audit["seconds"]:.9f} s; complete {audit["checked_utc"]}; zero new dynamics.',
        f'- Peak process RSS: {done["process_peak_rss_bytes"]:,} B; uncompressed arrays: {done["uncompressed_array_bytes"]:,} B.',
        f'- Stage retained at completion before final receipt: {done["resources"]["bytes"]:,} B including qualification; 3 GiB cap.',
        '- One CPU/thread, CPU6, nice10. All numerical files, logs, caches and fixtures remain external.',
        '- 981 output files; 128 paths (32 body-free); 16 donors; 296 named / 184 distinct physical reads; 32 comparisons.',
        '- All controls and donor seals passed; 80 unchanged paths and 200 named reads bridge to D193.',
        '- Source acquisition was reused without regeneration. Both physical arms have bodies and own-reference writers.',
        '- The excluded pilot remains a separate negative result. This panel is not fresh confirmation or equivalence evidence.',
        '- Check: `PYTHONDONTWRITEBYTECODE=1 python3 scripts/report_l22_recipient_pulse_panel.py --check`.', '']
    for path, digest in IDENTITIES.items():
        lines.append('- '+str(path.relative_to(ROOT))+' SHA-256: `'+digest+'`.')
    return '\n'.join(lines)+'\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--patch', action='store_true')
    modes.add_argument('--check', action='store_true')
    args = parser.parse_args()
    document = render()
    if args.check:
        assert DEST.read_text() == document
        print(json.dumps(dict(passes=True, primary_rows=10, named_arm_rows=111,
            role_arm_rows=189, comparison_rows=288, focal_stratum_rows=240,
            omission_rows=40, primary_record_rows=128, new_dynamics=0)))
    else:
        assert not DEST.exists()
        print('*** Begin Patch\n*** Add File: '+str(DEST.relative_to(WS)))
        print('\n'.join('+'+line for line in document.splitlines()))
        print('*** End Patch')
