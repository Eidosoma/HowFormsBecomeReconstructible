"""Pin E105 arrays and historical endpoints; never use history as a fresh score."""
import csv
import hashlib
import io
import json
import numpy as np
from common import dump,sha,utc
from E083_reader_repeatability.data import save,load,equal
from E103_saved_sign_organization.data import output_csv,identity,verify_endpoints
from E106_fresh_reader_sign_control.plan import HERE,ROOT,PARENT,settings


def register():
    target=HERE/'SOURCE_DATA.json';assert not target.exists()
    close=PARENT/'analysis/closeout_v1.json';assert json.loads(close.read_text())['status']=='PASS'
    receipts={str(p.relative_to(ROOT)):sha(p) for p in (close,PARENT/'SOURCE_DATA.json',PARENT/'SAMPLE_FREEZE.json',
              PARENT/'analysis/preflight_v1.json',PARENT/'PROTOCOL.md')};sources={}
    for mode in ('benchmark','scientific'):
        cfg=settings(mode);run=PARENT/'runs'/cfg['parent_run'];c=json.loads((run/'COMPLETE.json').read_text())
        assert c['status']=='COMPLETE' and c['controls_pass']
        contract=json.loads((run/'manifest.json').read_text())['contract']
        assert contract['blocks']==cfg['blocks'] and contract['reader']==cfg['reader'] and contract['config']==cfg['config']
        if mode=='scientific':assert json.loads(close.read_text())['complete_sha256']==sha(run/'COMPLETE.json')
        names=['cases.csv','summary.json','original_cases.csv','original_summary.json']
        names += [f'{tag}_{b:06d}.npz' for b in cfg['blocks'] for tag in ('interventions','diagnostics')]
        names += [f'{tag}_{b:06d}_r{draw}.npz' for b in cfg['blocks'] for draw in (0,1) for tag in ('assay','scores')]
        hashes={}
        for name in names:
            h=sha(run/name);assert h==c['outputs_sha256'][name],name;hashes[name]=h
        sources[mode]=dict(path=str(run.relative_to(ROOT)),files=hashes)
        for name in ('COMPLETE.json','CHECKS.json','manifest.json'):receipts[str((run/name).relative_to(ROOT))]=sha(run/name)
    dump(target,dict(utc=utc(),sources=sources,receipts=receipts,previous_outcomes_known=True,
        new_scientific_reader_outcomes_seen=False,source_selection=False,witness_reselection=False,new_source_blocks=0))


def registry(all_files=False):
    r=json.loads((HERE/'SOURCE_DATA.json').read_text())
    for p,h in r['receipts'].items():assert sha(ROOT/p)==h,p
    if all_files:
        for s in r['sources'].values():
            for p,h in s['files'].items():assert sha(ROOT/s['path']/p)==h,p
    return r


def raw(mode,name):
    s=registry()['sources'][mode];b=(ROOT/s['path']/name).read_bytes()
    assert hashlib.sha256(b).hexdigest()==s['files'][name],name;return b


def arrays(mode,name):
    with np.load(io.BytesIO(raw(mode,name)),allow_pickle=False) as z:out={k:z[k] for k in z.files}
    assert all(np.isfinite(v).all() for v in out.values());return out


def table(mode,name):
    rows=list(csv.DictReader(io.StringIO(raw(mode,name).decode())))
    cfg=settings(mode);keys=[identity(r)+(int(r['draw']),) for r in rows]
    expected={(b,a,f,r,d) for b in cfg['blocks'] for a in range(4) for f in range(4) for r in range(cfg['recipients']) for d in (0,1)}
    assert len(keys)==len(set(keys)) and set(keys)==expected;return rows


def original(mode):return table(mode,'original_cases.csv')
