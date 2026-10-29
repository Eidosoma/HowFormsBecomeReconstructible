"""Render pinned D196 saved-state findings; no dynamics or numerical writes."""

import argparse
import hashlib
import json
from pathlib import Path

WS=Path(__file__).resolve().parents[1]
ROOT=Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-pulse-mechanism-v1')
IDS={
    'FREEZE.json':'734b2eeff5c307d9b757c689a22379ec9be681779bddd6850fc190264ef0a982',
    'MANIFEST.json':'ca04d51729d4f4645b8f57a90689f745e2cd81b62691e5ac9b175c350d032fa7',
    'COMPLETE.json':'d4b5d8d119d04102bac0186d58df7c3d05bee1ba2ec66d588971c694c1464a4c',
    'outputs/SUMMARY.json':'c1d6c9f43cdb82e95586bff0d3bc2dbd40dd62679d66af897b7fddb7c34d8304',
    'outputs/CHECK.json':'c6ce07ccac456c2d63acd21c57aa64e2bdae7e05e696838cdaabeddbb2f52a37',
    'SAVED_CHECK.json':'f0cfda4fca431addc794686fd7a2f94c796ff22e89e804d0d9436c0b0d1551d5',
}
DEST=WS/'L22-active-form/PULSE_MECHANISM_TABLES.md'
FAMILIES=('common','residual')
ARMS=('LL','YL','LL_pulse','YL_pulse')
PAIRS=('undisturbed','disturbed','own_pulse','recorded_pulse')
FOCAL=('contingent_body_undisturbed','contingent_body_disturbed','own_disturbance','yoked_disturbance','disturbance_interaction')
FIELDS=('rms_left','rms_right','rms_delta','relative_rms','cosine','max_abs_delta')
BEHAVIOR=('accuracy','partner_accuracy','preference','projection_gap','margin','winner_gap')


def render():
    for name,h in IDS.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
    read=lambda name:json.loads((ROOT/name).read_text())
    done,audit,s=read('COMPLETE.json'),read('SAVED_CHECK.json'),read('outputs/SUMMARY.json')
    assert done['status']=='COMPLETE' and done['verification']['passes']
    assert audit['status']=='SAVED_CHECK_PASSED' and audit['passes'] and audit['new_dynamics']==0
    assert audit['complete_sha256']==IDS['COMPLETE.json'] and done['summary_sha256']==IDS['outputs/SUMMARY.json']
    assert done['freeze_sha256']==IDS['FREEZE.json'] and done['manifest_sha256']==IDS['MANIFEST.json']
    assert s['records']==64 and s['blocks']==[319100,319101,319102,319103]
    assert s['retrospective'] and not s['confirmatory'] and s['new_dynamics']==s['fitted_models']==0
    assert len(s['views'])==1986 and len(s['changed_draws'])==36
    v=s['views'];lines=['# D196 saved pulse mechanism: tables','',
        '28 October 2026. [Interpretation](PULSE_MECHANISM_RESULTS.md).',
        'Rendered from the pinned [summary]('+str(ROOT/'outputs/SUMMARY.json')+').','',
        'All 64 exposed records, both families, roles and futures remain. No new dynamics.',
        'Field distances are computed per record before role/draw/history averaging.',
        'Relative RMS is percent of pooled field amplitude, not percent information lost.',
        'Recognition/partner recognition are percentages; preference and their differences',
        'are percentage points. Projection gaps, margins and winner gaps are native scores.',
        'Margin compares the target to its strongest competitor; projection gap compares',
        'only the designated partner. Winner/tie weights are not calibrated probabilities.',
        'All omitted fine strata and per-record/draw arrays remain external. These are',
        'retrospective descriptions; no close-margin cutoff or equivalence test is used.','']
    def add(row):lines.append('| '+' | '.join(str(x).replace('|','\\|') for x in row)+' |')
    def table(title,headers):
        lines.extend(['','## '+title,'']);add(headers);add(['---']*len(headers))
    def vals(row,fields):
        return [f'{row[k]*(100 if k in ("relative_rms","accuracy","partner_accuracy","preference") else 1):.9f}' for k in fields]
    field_heads=['RMS left','RMS right','RMS difference','Relative RMS %','Cosine','Maximum difference']
    behavior_heads=['Recognition','Partner','Preference','Projection gap','Margin','Winner gap']
    table('Terminal route and pulse separation',['Family','Pair','Field',*field_heads])
    for f in FAMILIES:
        for pair in PAIRS:
            for field in ('body_input','V','R','writer_drive','theta'):
                add([f,pair,field,*vals(v[f'chain|{f}|role_mean|{pair}|{field}|1000']['mean'],FIELDS)])
            add([f,pair,'fresh_reader_V',*vals(v[f'reader|{f}|role_mean|both|{pair}|1000']['mean'],FIELDS)])
    table('All ordinary checkpoint pair means',['Key',*field_heads])
    for key,row in sorted(v.items()):
        if key.startswith('chain|') and '|role_mean|' in key:add([key,*vals(row['mean'],FIELDS)])
    table('All event distance means',['Key',*field_heads])
    for key,row in sorted(v.items()):
        if key.startswith(('event|','event_route|')) and '|role_mean|' in key:add([key,*vals(row['mean'],FIELDS)])
    table('All target projection means',['Key','Own-minus-partner projection'])
    for key,row in sorted(v.items()):
        if key.startswith(('projection|','event_projection|')) and '|role_mean|' in key:
            add([key,*vals(row['mean'],('projection_gap',))])
    table('Fresh-reader checkpoint pair means',['Key',*field_heads])
    for key,row in sorted(v.items()):
        if key.startswith('reader|') and '|role_mean|both|' in key:add([key,*vals(row['mean'],FIELDS)])
    table('All four cells and five contrasts, roles and futures',['Key',*behavior_heads])
    for key,row in sorted(v.items()):
        if key.startswith(('behavior|','contrast|')):add([key,*vals(row['mean'],BEHAVIOR)])
    table('Every behavioral gain, harm and tie count',['Key','Field','Level','Gains','Harms','Ties','N','Net points','Positive contribution','Negative contribution'])
    for key,rows in sorted(s['transitions'].items()):
        for field,levels in rows.items():
            for level,c in levels.items():
                assert c['n']==c['improved']+c['worsened']+c['tied']
                add([key,field,level,*[c[k] for k in ('improved','worsened','tied','n')],
                     *[f'{100*c[k]:.9f}' for k in ('net','positive','negative')]])
    table('All focal distributions and history/message strata',['Family','Contrast','View','Index',*behavior_heads])
    for f in FAMILIES:
        for contrast in FOCAL:
            row=v[f'contrast|{f}|role_mean|both|{contrast}']
            for stat in ('minimum','median','maximum'):add([f,contrast,stat,'all records',*vals(row[stat],BEHAVIOR)])
            for stat in ('by_block','by_message','leave_one_block_out'):
                labels=s['blocks'] if stat!='by_message' else range(4)
                for label,x in zip(labels,row[stat]):add([f,contrast,stat,label,*vals(x,BEHAVIOR)])
    table('All 36 changed paired draws, all four cells',['History','Family','Role','Future','Record','Draw','Arm',*behavior_heads])
    for x in s['changed_draws']:
        for arm in ARMS:
            add([*[x[k] for k in ('block','family','role','future','record','draw')],arm,*vals(x['cells'][arm]['behavior'],BEHAVIOR)])
    table('Template scores and winner weights for every changed draw',['History','Family','Role','Future','Record','Draw','Arm',
        'Score 0','Score 1','Score 2','Score 3','Weight 0','Weight 1','Weight 2','Weight 3'])
    for x in s['changed_draws']:
        for arm in ARMS:
            cell=x['cells'][arm]
            add([*[x[k] for k in ('block','family','role','future','record','draw')],arm,
                 *[f'{z:.9f}' for z in cell['scores']],*cell['probabilities']])
    lines+=['','## Provenance and costs','',
        f'- Execution: {done["seconds"]:.9f} s; completed {done["completed_utc"]}.',
        f'- Separate saved audit passed {audit["checked_utc"]}; zero new dynamics.',
        f'- Peak RSS {done["peak_rss_bytes"]:,} B; stage before final receipt {done["resources"]["bytes"]:,} B, including qualification.',
        '- One CPU/thread, CPU6, nice10; six output files, 1,986 checked views, all 64 records.',
        '- 62,464 scalar-checked field pairs, 30,720 target projections and 8,192 terminal score rows.',
        '- All D195 four-cell means and five focal contrasts bridge, including roles/futures/strata and harms.',
        '- Check: `PYTHONDONTWRITEBYTECODE=1 python3 scripts/report_l22_pulse_mechanism.py --check`.','']
    for name,h in IDS.items():lines.append('- '+name+' SHA-256: `'+h+'`.')
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--patch',action='store_true');g.add_argument('--check',action='store_true')
    args=p.parse_args();document=render()
    if args.check:
        assert DEST.read_text()==document
        print(json.dumps(dict(passes=True,source_views=1986,changed_draws=36,all_records=64,new_dynamics=0)))
    else:
        assert not DEST.exists()
        print('*** Begin Patch\n*** Add File: '+str(DEST.relative_to(WS)))
        print('\n'.join('+'+line for line in document.splitlines()))
        print('*** End Patch')
