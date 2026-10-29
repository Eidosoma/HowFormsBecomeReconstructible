"""Render audited D197 preference and secondary-margin tables; no dynamics."""

import argparse
import hashlib
import json
from pathlib import Path

WS=Path(__file__).resolve().parents[1]
ROOT=Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-pulse-founders-v1')
DATA,RECEIPTS=ROOT/'outputs/panel',ROOT/'runs/panel'
AUDIT=ROOT/'audits/panel.json'
DEST=WS/'L22-active-form/PULSE_FOUNDERS_TABLES.md'
IDENTITIES={
    ROOT/'FREEZE.json':'ee1ea56caa2168674673b8f2fe1aa83f36ab8796697987bd70eea41a6978dd2d',
    ROOT/'EXECUTION_FREEZE.json':'50fb823e9f38dabf80e43cadfc54a1582622c0c588223b938b543e5de6e1389c',
    RECEIPTS/'MANIFEST.json':'301a9c3aa9b688b2517fcf6bed50335581e391628ffefa24842fe15b3a87c5fa',
    RECEIPTS/'COMPLETE.json':'bab8c6a350c26a57acc611ff8f7359d898422d565568f8db158694f9dca64152',
    DATA/'PRIMARY.json':'78961a3baee6eb89ca5f93667ea2669fefe50c16996539eed00681ec290c6196',
    DATA/'MARGINS.json':'63f69562fc7954efc47a06a1cf14982151fa81d607b2c2817befaf6261c93ddc',
    AUDIT:'8e1ccc9e8499c9d14bf87c2db20ccc4f709046af4d0937d99d0e41903dd2f98a',
    ROOT/'logs/panel_audit_timing.json':'53296dbbecc40d6e7403c919b166e9a044346b71cb09b6618d109f34cd0bd247',
}
FIELDS=('accuracy','partner_accuracy','preference','projection_gap','sign_fidelity','theta_corr_parent','theta_corr_partner')
HEADER=('Recognition','Partner','Preference','Projection gap','Sign fidelity','Parent correlation','Partner correlation','Secondary margin')
FOCAL=('disturbance_interaction','contingent_body_undisturbed','contingent_body_disturbed','own_disturbance','yoked_disturbance')
BLOCKS=[319700,319701,319702,319703]


def render():
    for path,h in IDENTITIES.items():assert hashlib.sha256(path.read_bytes()).hexdigest()==h,path
    read=lambda p:json.loads(p.read_text())
    p,m=read(DATA/'PRIMARY.json'),read(DATA/'MARGINS.json')
    done,audit=read(RECEIPTS/'COMPLETE.json'),read(AUDIT)
    timing=read(ROOT/'logs/panel_audit_timing.json')
    assert timing['audit_sha256']==IDENTITIES[AUDIT] and timing['new_dynamics']==0
    seal=read(ROOT/'EXECUTION_FREEZE.json')
    assert done['status']=='COMPLETE' and done['verification']['passes']
    assert done['stage']==audit['stage']=='panel' and done['new_founders']==4 and done['source_regenerated']
    assert done['primary_sha256']==IDENTITIES[DATA/'PRIMARY.json'] and done['margin_sha256']==IDENTITIES[DATA/'MARGINS.json']
    assert done['freeze_sha256']==seal['design_freeze_sha256']==IDENTITIES[ROOT/'FREEZE.json']
    assert done['execution_freeze_sha256']==IDENTITIES[ROOT/'EXECUTION_FREEZE.json']
    assert audit['status']=='SAVED_CHECK_PASSED' and audit['verification']==done['verification']
    assert audit['new_dynamics']==0 and audit['complete_sha256']==IDENTITIES[RECEIPTS/'COMPLETE.json']
    assert p['blocks']==m['blocks']==seal['blocks']==BLOCKS and p['records']==m['records']==64
    assert p['new_founders']==4 and p['source_regenerated'] and p['prospective'] and m['prospective']
    assert p['benchmark_excluded'] and not p['old_outcomes_pooled'] and m['primary_unchanged']
    assert not p['confirmatory'] and p['fitted_models']==0 and p['uncertainty_interval'] is None
    lines=['# D197 fresh pulse histories: complete saved tables','',
        '29 October 2026. [Interpretation](PULSE_FOUNDERS_RESULTS.md).',
        'Rendered from the pinned primary and secondary summaries after separate saved-only audit.','',
        'All four fresh histories / 64 records remain, with both families/roles/futures',
        'and every control. The timing history and old development outcomes are excluded.',
        'Preference interaction remains primary; continuous margin is secondary.',
        'Histories and futures have equal weight; roles are averaged within each',
        'record and paired draw. The 512 pooled draw entries are role-averaged',
        'cells, not independent founder histories. No powered confirmation or',
        'equivalence claim, fitted model or uncertainty interval is introduced.','',
        'Recognition and partner recognition are percentages; preference and signed',
        'behavior differences are percentage points. Other metrics use native units.',
        'Margin is target-template score minus strongest other-template score.',
        'Gain/harm/tie counts refer to the named contrast, including interactions.',
        'Positive interaction does not imply absolute post-pulse superiority.',
        'Both focal arms contain recipient bodies and own-state writers. Reciprocal',
        'trace-writer equality is structural. Full record/draw arrays, nonfocal strata',
        'and signed contributions remain in the external summaries.','']
    def add(row):lines.append('| '+' | '.join(str(x).replace('|','\\|') for x in row)+' |')
    def table(title,names):
        lines.extend(['','## '+title,'']);add(names);add(['---']*len(names))
    def values(pr,mr):return [f'{pr[k]*(100 if k in FIELDS[:3] else 1):.9f}' for k in FIELDS]+[f'{mr["margin"]:.12f}']
    def counts(pr,mr):
        result=[]
        for level in ('records','draws'):
            for row in (pr['accuracy'][level],pr['preference'][level],mr[level]):
                assert row['n']==sum(row[k] for k in ('improved','worsened','tied'))
                result.append('/'.join(str(row[k]) for k in ('improved','worsened','tied')))
        return result
    count_names=[f'{metric} {level} gain/harm/tie' for level in ('records','draws') for metric in ('Recognition','Preference','Margin')]
    streams=[(f,p['by_future'][f],m['by_future'][f]) for f in p['by_future']]+[('both_futures',p['new_only'],m['new_only'])]
    pp,mm=p['new_only']['role_mean'],m['new_only']['role_mean']
    table('Four cells and primary interaction',['Family','Cell or contrast',*HEADER])
    for family in ('common','residual'):
        for kind in ('LL','YL','LL_pulse','YL_pulse'):
            n=family+'__'+kind;add([family,kind,*values(pp['arms'][n]['mean'],mm['arms'][n]['mean'])])
        n=family+'__disturbance_interaction';a,b=pp['contrasts'][n],mm['contrasts'][n]
        terms={family+'__LL_pulse':1.,family+'__YL_pulse':-1.,family+'__LL':-1.,family+'__YL':1.}
        assert a['coefficients']==b['coefficients']==terms
        for k in FIELDS:assert abs(a['mean'][k]-sum(w*pp['arms'][q]['mean'][k] for q,w in terms.items()))<2e-12
        assert abs(b['mean']['margin']-sum(w*mm['arms'][q]['mean']['margin'] for q,w in terms.items()))<2e-12
        add([family,'disturbance_interaction',*values(a['mean'],b['mean'])])
    table('Every named arm',['Future','Arm',*HEADER])
    for label,pv,mv in streams:
        assert set(pv['named_arms'])==set(mv['named_arms']) and len(pv['named_arms'])==37
        for name,row in sorted(pv['named_arms'].items()):add([label,name,*values(row['mean'],mv['named_arms'][name]['mean'])])
    table('Role-specific and role-mean arms',['Future','Role','Arm',*HEADER])
    for label,pv,mv in streams:
        for role in ('A','B','mean'):
            a,b=(pv['role_mean'],mv['role_mean']) if role=='mean' else (pv['by_role'][role],mv['by_role'][role])
            assert len(a['arms'])==len(b['arms'])==21
            for name,row in sorted(a['arms'].items()):add([label,role,name,*values(row['mean'],b['arms'][name]['mean'])])
    table('Every signed comparison',['Future','Role','Comparison',*HEADER,*count_names])
    for label,pv,mv in streams:
        for role in ('A','B','mean'):
            a,b=(pv['role_mean'],mv['role_mean']) if role=='mean' else (pv['by_role'][role],mv['by_role'][role])
            assert len(a['contrasts'])==len(b['contrasts'])==32
            for name,row in sorted(a['contrasts'].items()):
                mr=b['contrasts'][name];assert row['coefficients']==mr['coefficients']
                add([label,role,name,*values(row['mean'],mr['mean']),*counts(row['transitions']['pooled'],mr['transitions']['pooled'])])
    table('Focal blocks, messages and intersections',['Family','Comparison','Stratum','Value',*HEADER,*count_names])
    for family in ('common','residual'):
        for kind in FOCAL:
            a,b=pp['contrasts'][family+'__'+kind],mm['contrasts'][family+'__'+kind]
            for key,labels in [('by_block',BLOCKS),('by_message',range(4))]:
                for i,label in enumerate(labels):add([family,kind,key,label,*values(a[key][i],b[key][i]),*counts(a['transitions'][key][i],b['transitions'][key][i])])
            for i,history in enumerate(BLOCKS):
                for j in range(4):add([family,kind,'block/message',f'{history}/{j}',*values(a['by_block_message'][i][j],b['by_block_message'][i][j]),*counts(a['transitions']['by_block_message'][i][j],b['transitions']['by_block_message'][i][j])])
    table('Focal leave-one-history-out means',['Family','Comparison','Omitted history',*HEADER])
    for family in ('common','residual'):
        for kind in FOCAL:
            a,b=pp['contrasts'][family+'__'+kind],mm['contrasts'][family+'__'+kind]
            for i,history in enumerate(BLOCKS):
                x,y=a['leave_one_block_out'][i],b['leave_one_block_out'][i]
                for k in FIELDS:assert abs(x[k]-sum(v[k] for j,v in enumerate(a['by_block']) if i!=j)/3)<2e-12
                assert abs(y['margin']-sum(v['margin'] for j,v in enumerate(b['by_block']) if i!=j)/3)<2e-12
                add([family,kind,history,*values(x,y)])
    table('Every focal record, retaining all individual harms',['Family','Comparison','History','Record','Message','Replicate',*HEADER])
    for family in ('common','residual'):
        for kind in FOCAL:
            a,b=pp['contrasts'][family+'__'+kind],mm['contrasts'][family+'__'+kind]
            assert len(a['per_record'])==len(b['per_record'])==4
            for i,history in enumerate(BLOCKS):
                assert len(a['per_record'][i])==len(b['per_record'][i])==16
                for j,row in enumerate(a['per_record'][i]):add([family,kind,history,j,j//4,j%4,*values(dict(zip(FIELDS,row)),{'margin':b['per_record'][i][j]})])
    table('Signed contributions to the primary and secondary interaction',['Family','Level','Preference positive','Preference negative','Preference net','Margin positive','Margin negative','Margin net'])
    for family in ('common','residual'):
        a,b=pp['contrasts'][family+'__disturbance_interaction'],mm['contrasts'][family+'__disturbance_interaction']
        for level in ('records','draws'):
            x,y=a['transitions']['pooled']['preference'][level],b['transitions']['pooled'][level]
            assert abs(x['positive']+x['negative']-x['net'])<2e-12 and abs(y['positive']+y['negative']-y['net'])<2e-12
            add([family,level,*[f'{100*x[k]:.9f}' for k in ('positive','negative','net')],*[f'{y[k]:.12f}' for k in ('positive','negative','net')]])
    lines+=['','## Costs and provenance','',
        f'- Execution, independent replay and saved checks: {done["seconds"]:.9f} s; completed {done["completed_utc"]}.',
        f'- Separate saved-only audit: {timing["seconds"]:.9f} s; {audit["checked_utc"]}; zero new dynamics.',
        f'- Peak process RSS: {done["process_peak_rss_bytes"]:,} B; uncompressed arrays: {done["uncompressed_array_bytes"]:,} B.',
        f'- Stage retained before final completion receipt: {done["resources"]["bytes"]:,} B including qualification; cap 4 GiB.',
        '- 994 outputs; 128 paths (32 body-free); 16 donors; 296 named / 184 unique reads; 32 comparisons.',
        '- Four new acquisitions; full independent source/repair/reader replay and donor barriers passed.',
        '- One CPU6/thread, nice10. All numerical files, logs, fixtures and caches stay under /mnt/bioIce1.',
        '- This fresh recurrence check retains preference as primary. A secondary margin gain is not a primary preference win.',
        '- Check: `PYTHONDONTWRITEBYTECODE=1 python3 scripts/report_l22_pulse_founders.py --check`.','']
    for path,h in IDENTITIES.items():lines.append('- '+str(path.relative_to(ROOT))+' SHA-256: `'+h+'`.')
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    parser=argparse.ArgumentParser();modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--patch',action='store_true');modes.add_argument('--check',action='store_true')
    args=parser.parse_args();document=render()
    if args.check:
        assert DEST.read_text()==document
        print(json.dumps(dict(passes=True,four_cell_rows=10,named_arm_rows=111,role_arm_rows=189,
            comparison_rows=288,focal_stratum_rows=240,omission_rows=40,focal_record_rows=640,contribution_rows=4,new_dynamics=0)))
    else:
        assert not DEST.exists()
        print('*** Begin Patch\n*** Add File: '+str(DEST.relative_to(WS)))
        print('\n'.join('+'+line for line in document.splitlines()))
        print('*** End Patch')
