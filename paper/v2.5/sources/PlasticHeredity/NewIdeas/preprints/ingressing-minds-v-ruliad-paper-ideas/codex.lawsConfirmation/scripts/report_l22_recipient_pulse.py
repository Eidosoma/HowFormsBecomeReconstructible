"""Render pinned D195 recipient-pulse benchmark results; no dynamics or numerical writes."""

import argparse
import hashlib
import json
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
ROOT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-recipient-pulse-benchmark-v1')
RUN = 'l22_recipient_pulse_v1_benchmark_attempt1'
DATA, RECEIPTS = ROOT/'outputs'/RUN, ROOT/'runs'/RUN
IDENTITIES = {
    ROOT/'FREEZE.json': 'ded7aadbdb12128fa61d5eeda2f36fccbf1c32f20de77214e1e562811088ade1',
    RECEIPTS/'MANIFEST.json': '6d6c76e13f58aaf6dcbf7ea85e9327a0fc94417dcb04abb4706c57ddf74fe280',
    RECEIPTS/'COMPLETE.json': 'f42e86525f0bd041400692a74f25c879cdc73610359d46dd2aba2703c72beea1',
    ROOT/'audits/status_2026-10-28_attempt1.json': 'b43e9cd70ff5fe38a73336678679406b858eede26ebec54f05dc652f20448cb5',
    DATA/'CHECK.json': '4b9cdbfdcc430fecba48980180f482e37910b17d7cf0820e6d4729d635bea41a',
    DATA/'SUMMARY.json': '5713a26931d98975783c5266996699c76cbe98b33b91a6f946bbc4989df80d77',
}
DEST = WS/'L22-active-form/RECIPIENT_PULSE_TABLES.md'
FIELDS = ('accuracy', 'partner_accuracy', 'preference', 'projection_gap',
          'sign_fidelity', 'theta_corr_parent', 'theta_corr_partner')


def render():
    for path, digest in IDENTITIES.items(): assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    summary = json.loads((DATA/'SUMMARY.json').read_text())
    done = json.loads((RECEIPTS/'COMPLETE.json').read_text())
    audit = json.loads((ROOT/'audits/status_2026-10-28_attempt1.json').read_text())
    assert audit['status']=='SAVED_CHECK_PASSED' and audit['verification']['passes'] and audit['new_dynamics']==0
    assert audit['complete_sha256']==IDENTITIES[RECEIPTS/'COMPLETE.json']
    assert done['status'] == 'COMPLETE' and done['verification']['passes']
    assert done['summary_sha256'] == IDENTITIES[DATA/'SUMMARY.json']
    assert summary['index'] == 603191 and summary['records'] == 16 and summary['comparisons'] == 32
    assert not summary['confirmatory'] and not summary['old_outcomes_pooled'] and summary['new_founders'] == 0
    lines = ['# D195 excluded recipient-pulse pilot: complete saved tables', '',
        '28 October 2026. [Interpretation](RECIPIENT_PULSE_RESULTS.md).',
        'Mechanically rendered from the pinned [summary]('+str(DATA/'SUMMARY.json')+').', '',
        'All sixteen excluded 603191 records; both repair-noise roles and both inherited',
        'reader futures with four draws each. Roles are averaged within record and',
        'paired draw, not treated as extra founders. No fitting or case selection.',
        'Recognition and partner recognition are percentages; preference and signed',
        'behavior changes use percentage points. Other metrics are in native units.',
        'Reciprocal recorded-writer equality is structural, not an empirical null.', '']
    sets = [*summary['by_future'].items(), ('new_mean', summary['new_only'])]
    def add(row): lines.append('| '+' | '.join(str(x).replace('|','\|') for x in row)+' |')
    def values(row): return [f'{row[k]*(100 if k in FIELDS[:3] else 1):.8f}' for k in FIELDS]
    def counts(row, field, level='records'):
        c = row[field][level]
        assert c['n'] == sum(c[k] for k in ('improved', 'worsened', 'tied'))
        return '/'.join(str(c[k]) for k in ('improved', 'worsened', 'tied'))
    header = ['Recognition', 'Partner', 'Preference', 'Projection gap', 'Sign fidelity', 'Parent correlation', 'Partner correlation']
    def table(title, names):
        lines.extend(['', '## '+title, '']); add(names); add(['---']*len(names))
    table('Primary interaction and its four cells', ['Family','Comparison',*header])
    view=summary['new_only']['role_mean']
    for family in ('common','residual'):
        for kind in ('LL','YL','LL_pulse','YL_pulse'):
            add([family,kind,*values(view['arms'][family+'__'+kind]['mean'])])
        row=view['contrasts'][family+'__disturbance_interaction']
        expected={family+'__LL_pulse':1.,family+'__YL_pulse':-1.,family+'__LL':-1.,family+'__YL':1.}
        assert row['coefficients']==expected
        for k in FIELDS:
            assert abs(row['mean'][k]-sum(w*view['arms'][name]['mean'][k] for name,w in expected.items()))<2e-12
        add([family,'disturbance_interaction',*values(row['mean'])])
    table('Primary interaction for all retained records', ['Family','Record','Message','Replicate',*header])
    for family in ('common','residual'):
        rows=view['contrasts'][family+'__disturbance_interaction']['per_record']
        assert len(rows)==16
        for i,row in enumerate(rows): add([family,i,i//4,i%4,*values(dict(zip(FIELDS,row)))])
    table('Every named arm', ['Set', 'Arm', *header])
    for label, data in sets:
        assert len(data['named_arms']) == 37
        for name, row in sorted(data['named_arms'].items()): add([label, name, *values(row['mean'])])
    table('Role-specific and role-mean arms', ['Set', 'Role', 'Arm', *header])
    for label, data in sets:
        for role, view in [*data['by_role'].items(), ('mean', data['role_mean'])]:
            assert len(view['arms']) == 21 and len(view['contrasts']) == 32
            for name, row in sorted(view['arms'].items()): add([label, role, name, *values(row['mean'])])
    count_header = ['Recognition records gain/harm/tie', 'Preference records gain/harm/tie',
                    'Recognition draws gain/harm/tie', 'Preference draws gain/harm/tie']
    table('Every signed comparison', ['Set', 'Role', 'Comparison', *header, *count_header])
    for label, data in sets:
        for role, view in [*data['by_role'].items(), ('mean', data['role_mean'])]:
            for name, row in sorted(view['contrasts'].items()):
                add([label, role, name, *values(row['mean']),
                     *[counts(row['transitions']['pooled'], k, level) for level in ('records', 'draws') for k in ('accuracy', 'preference')]])
    table('All message strata for every comparison', ['Set', 'Role', 'Comparison', 'Message', *header, *count_header])
    for label, data in sets:
        for role, view in [*data['by_role'].items(), ('mean', data['role_mean'])]:
            for name, row in sorted(view['contrasts'].items()):
                for m in range(4):
                    add([label, role, name, m, *values(row['messages'][m]),
                         *[counts(row['transitions']['by_message'][m], k, level) for level in ('records', 'draws') for k in ('accuracy', 'preference')]])
    lines += ['', '## Costs and provenance', '',
        f'- Complete execution: {done["seconds"]:.9f} s; included saved verification: {done["saved_verification_seconds"]:.9f} s.',
        f'- Peak process RSS: {done["process_peak_rss_bytes"]:,} B; uncompressed arrays: {done["uncompressed_array_bytes"]:,} B.',
        f'- Stage retained at completion before final receipt: {done["resources"]["bytes"]:,} B, including qualification.',
        f'- Output files: {len(done["output_sha256"])}; paths: 32; body-free paths: 8; named reads: 74; unique reads: 46.',
        '- Independent execution replay and saved checks passed; separate saved-only audit passed on 28 October.',
        f'- Separate saved audit: {audit["seconds"]:.9f} s; completed {audit["checked_utc"]}.',
        '- Four sealed donors, all twelve pulse paths, pre-event identities and V-only intervention checks passed.',
        '- Twenty unchanged repairs and fifty named reads bridge to the original D193 benchmark.',
        '- Primary outcome: preference interaction; recognition accompanies it. One history, no founder-level interval or equivalence claim.',
        '- Complete record/draw arrays, controls, costs and proofs remain external; no dynamics were rerun for this report.',
        '- Check: `python scripts/report_l22_recipient_pulse.py --check`.', '']
    for path, digest in IDENTITIES.items(): lines.append('- '+str(path.relative_to(ROOT))+' SHA-256: `'+digest+'`.')
    return '\n'.join(lines)+'\n'


if __name__ == '__main__':
    p = argparse.ArgumentParser(); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--patch', action='store_true'); g.add_argument('--check', action='store_true')
    args = p.parse_args(); text = render()
    if args.check:
        assert DEST.read_text() == text
        print(json.dumps(dict(passes=True, primary_cell_and_interaction_rows=10, primary_record_rows=32, named_arm_rows=111, role_arm_rows=189,
            comparison_rows=288, message_comparison_rows=1152, new_dynamics=0)))
    else:
        assert not DEST.exists()
        print('*** Begin Patch\n*** Add File: '+str(DEST.relative_to(WS)))
        print('\n'.join('+'+line for line in text.splitlines()))
        print('*** End Patch')
