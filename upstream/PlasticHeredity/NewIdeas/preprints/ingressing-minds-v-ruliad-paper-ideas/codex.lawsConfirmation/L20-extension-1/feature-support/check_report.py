"""Verify D166 Markdown numbers/links against the immutable external summary."""
from pathlib import Path
import re
from laws_confirmation import l15_repair_speed_run as io
from laws_confirmation.io import sha256_file,utc_now

ROOT=Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
RUN='l20_extension1_feature_support_v1_attempt1';HERE=Path(__file__).resolve().parent
SUMMARY=ROOT/'outputs'/RUN/'summary.json'
PIN='c1e3f0a58abc77ee1e45b5fe30a15f513825d500e04ad7ef470559adc244e74e'


def expected(s):
    scalars=s['scalar_rows'];vectors=s['vector_rows'];groups=s['groups'];out={}
    scalar=lambda g,n:next(r for r in scalars if r['group']==g and r['feature']==n)
    vector=lambda g,n:next(r for r in vectors if r['group']==g and r['name']==n)
    names=('starting','one_copy','shared:separate:passive','shared:separate:sham_plus','shared:separate:sham_minus')
    out['overview']=[[g,*[vector(g,k)['mean_distance_ratio'] for k in names],
        sum(r['mean_distance_change']<0 for r in vectors if r['group']==g)] for g in groups]
    out['copy_b']=[[k,co,*[scalar('B_ordinary',k+':'+n)[co+'_raw']['mean'] for n in ('own_best','guide_margin')]]
        for k in ('first','second:passive','second:sham_plus','second:sham_minus') for co in ('development','pilot')]
    out['response_b']=[]
    for k in ('passive','shuffle','attenuate','sham_plus','sham_minus'):
        r=scalar('B_ordinary','response:'+k+':guide_margin');own=scalar('B_ordinary','response:'+k+':own_best')
        out['response_b'].append([k,r['development_raw']['mean'],r['pilot_raw']['mean'],r['standardized_mean_shift'],
                                  own['development_raw']['mean'],own['pilot_raw']['mean']])
    out['starting']=[[r['group'],r['feature'],r['development_raw']['mean'],r['pilot_raw']['mean'],r['standardized_mean_shift'],r['sd_ratio'],
        100*r['development']['outside'],100*r['pilot']['outside']] for r in scalars if r['feature'].startswith('start:')]
    top=sorted([r for r in scalars if r['standardized_mean_shift'] is not None],key=lambda r:abs(r['standardized_mean_shift']),reverse=True)[:10]
    out['top10']=[[r['group'],r['feature'],r['standardized_mean_shift'],r['sd_ratio'],100*r['development']['outside'],100*r['pilot']['outside']] for r in top]
    out['scalar_raw']=[[r['group'],r['feature'],*[r[co][key] for co in ('development_raw','pilot_raw') for key in ('mean','sd','minimum','maximum')]] for r in scalars]
    out['scalar_support']=[[r['group'],r['feature'],r['standardized_mean_shift'],r['sd_ratio'],r['active_references'],
        *[100*r[co][k] for co in ('development','pilot') for k in ('below','above')],
        r['development']['standardized_mean'],r['pilot']['standardized_mean'],r['development']['standardized_rms'],r['pilot']['standardized_rms']] for r in scalars]
    out['vector_means']=[[r['group'],r['name'],r['dimensions'],min(r['active_dimensions']),max(r['active_dimensions']),
        r['development']['mean'],r['pilot']['mean'],r['mean_distance_ratio'],100*r['development']['box_outside'],100*r['pilot']['box_outside']] for r in vectors]
    out['vector_quantiles']=[[r['group'],r['name'],*[r[co][k] for k in ('median','q90','maximum') for co in ('development','pilot')]] for r in vectors]
    return out


def verify():
    assert sha256_file(SUMMARY)==PIN;s=io.read_json(SUMMARY);want=expected(s)
    seen=set();rows=0;links=0;documents=[HERE/'RESULTS.md',HERE/'TABLES.md']
    for path in documents:
        text=path.read_text()
        for name,body in re.findall(r'<!-- table:(\w+) -->\n((?:\|[^\n]*\n)+)',text):
            assert name not in seen;seen.add(name);lines=body.splitlines()[2:]
            assert len(lines)==len(want[name])
            for line,target in zip(lines,want[name]):
                cells=[x.strip() for x in line.strip('|').split('|')];assert len(cells)==len(target)
                for value,number in zip(cells,target):
                    if isinstance(number,str):assert value==number,(name,value,number)
                    elif number is None:assert value=='NA'
                    else:
                        digits=len(value.split('.')[1]) if '.' in value else 0
                        tol=.50001*10**(-digits)+1e-12 if digits else 1e-12
                        assert abs(float(value)-number)<=tol,(name,value,number)
                rows+=1
        for target in re.findall(r'\]\(([^)]+)\)',text):
            linked=Path(target) if Path(target).is_absolute() else path.parent/target
            assert linked.exists(),str(linked);links+=1
    assert seen==set(want)
    assert all(r['active_references']==16 for r in s['scalar_rows'])
    assert all(all(v==r['dimensions'] for v in r['active_dimensions']) for r in s['vector_rows'])
    for group in ('B_ordinary','B_aligned'):
        assert sum(r['mean_distance_change']<0 for r in s['vector_rows'] if r['group']==group)==22
    for group in s['groups']:
        for condition in ('passive','shuffle','attenuate','sham_plus','sham_minus'):
            for coordinate in ('own_best','best_margin','guide_margin','canonical_margin','preference','V_rms'):
                row=lambda prefix:next(r for r in s['scalar_rows'] if r['group']==group and r['feature']==prefix+':'+coordinate)
                for co in ('development_raw','pilot_raw'):
                    assert abs(row('second:'+condition)[co]['mean']-row('first')[co]['mean']-row('response:'+condition)[co]['mean'])<1e-12
    audit=io.read_json(ROOT/'logs'/f'{RUN}_saved_audit_v1.json')
    assert audit['passes'] and audit['complete_sha256']==sha256_file(ROOT/'runs'/RUN/'COMPLETE.json')
    return dict(passes=True,checked_utc=utc_now(),summary_sha256=PIN,tables=len(seen),numeric_rows=rows,links=links,
        document_sha256=io.hashes(documents),checker_sha256=sha256_file(Path(__file__)),new_fits=0,new_forecasts=0,new_dynamics=0,
        scope='documentation only; scientific freeze and outputs unchanged')


if __name__=='__main__':
    import json
    proof=verify();io.write_json(ROOT/'logs'/f'{RUN}_documentation_v1.json',proof,ROOT)
    print(json.dumps(proof,sort_keys=True))
