"""Independent registry of completed E112 outcomes and E113 size descriptions."""
import csv
import hashlib
import io
import json
import numpy as np
from common import dump, sha, utc
from E083_reader_repeatability.data import save, equal
from E103_saved_sign_organization.data import output_csv
from E114_matched_component_amplitude.plan import HERE, ROOT, COPY_NAMES, settings, key


def register():
    target=HERE/'SOURCE_DATA.json';assert not target.exists()
    parent=ROOT/'E113_component_threshold_diagnosis'
    close=parent/'analysis/closeout_v1.json';closed=json.loads(close.read_text());assert closed['status']=='PASS'
    previous=json.loads((parent/'SOURCE_DATA.json').read_text());receipts=dict(previous['receipts'])
    receipts.update({str(p.relative_to(ROOT)):sha(p) for p in (close,parent/'SOURCE_DATA.json',parent/'PROTOCOL.md',parent/'SAMPLE_FREEZE.json')})
    sources={}
    for mode,old in previous['sources'].items():
        for name,h in old['files'].items():assert sha(ROOT/old['path']/name)==h
        run=parent/'runs'/('diagnosis_v1' if mode=='scientific' else 'benchmark_v1')
        complete=json.loads((run/'COMPLETE.json').read_text());assert complete['status']=='COMPLETE' and complete['controls_pass']
        if mode=='scientific':assert closed['complete_sha256']==sha(run/'COMPLETE.json')
        files={}
        for name in ('all_cases.csv','summary.json'):
            h=sha(run/name);assert h==complete['outputs_sha256'][name];files[name]=h
        for name in ('COMPLETE.json','CHECKS.json','manifest.json'):
            p=run/name;receipts[str(p.relative_to(ROOT))]=sha(p)
        sources[mode]=dict(original=old,diagnosis=dict(path=str(run.relative_to(ROOT)),files=files))
    dump(target,dict(utc=utc(),sources=sources,receipts=receipts,old_outcomes_known=True,
        matched_outcomes_seen=False,source_selection=False,prior_primary='UNRESOLVED'))


def registry(all_files=False):
    r=json.loads((HERE/'SOURCE_DATA.json').read_text())
    for p,h in r['receipts'].items():assert sha(ROOT/p)==h,p
    if all_files:
        for mode in r['sources'].values():
            for source in mode.values():
                for p,h in source['files'].items():assert sha(ROOT/source['path']/p)==h,p
    return r


def raw(mode,era,name):
    source=json.loads((HERE/'SOURCE_DATA.json').read_text())['sources'][mode][era]
    value=(ROOT/source['path']/name).read_bytes();assert hashlib.sha256(value).hexdigest()==source['files'][name],name
    return value


def arrays(mode,name):
    with np.load(io.BytesIO(raw(mode,'original',name)),allow_pickle=False) as z:out={k:z[k] for k in z.files}
    assert all(np.isfinite(v).all() for v in out.values());return out


def table(mode,era,name):return list(csv.DictReader(io.StringIO(raw(mode,era,name).decode())))


def known(mode,era='original'):
    rows=table(mode,era,'cases.csv' if era=='original' else 'all_cases.csv');cfg=settings(mode)
    expected={(b,a,f,r,d) for b in cfg['blocks'] for a in range(4) for f in range(4) for r in range(cfg['recipients']) for d in (0,1)}
    assert len(rows)==len(expected) and {key(r) for r in rows}==expected
    return {key(r):r for r in rows}


def export(path,rows,fields):output_csv(path,[{k:r.get(k) for k in fields} for r in rows],fields)
