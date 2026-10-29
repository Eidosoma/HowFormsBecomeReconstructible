"""Fresh-ID register and pinned technical projections; no old scientific cases."""
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from common import dump,sha,utc
from E065_fresh_compatibility_confirmation.plan import HERE,ROOT,BLOCKS,TECH_BLOCK


def register():
    target=HERE/'SOURCE_DATA.json';assert not target.exists()
    manifests={};seen=set()
    for p in sorted(ROOT.glob('E*/runs/*/manifest.json')):
        if p.is_relative_to(HERE):continue
        blocks=json.loads(p.read_text()).get('contract',{}).get('blocks',[])
        if blocks:
            manifests[str(p.relative_to(ROOT))]=sha(p);seen.update(blocks)
    assert not seen.intersection(BLOCKS) and TECH_BLOCK not in BLOCKS
    predecessors={}
    for name in ('E057_fresh_capture_confirmation','E058_capture_benefit_persistence',
                 'E062_cross_stage_compatibility','E064_magnitude_subset_intervention'):
        p=ROOT/name/'analysis/closeout_v1.json';assert json.loads(p.read_text())['status']=='PASS'
        predecessors[str(p.relative_to(ROOT))]=sha(p)
    technical={}
    for mode in ('fixture','benchmark'):
        refs={}
        for number,name,names in (
            ('E057','E057_fresh_capture_confirmation', ['acquisition_900041.npz','body_900041.npz','outgoing_900041.npz']+
                [f'boundary_900041_g{g}.npz' for g in range(1,33)]),
            ('E058','E058_capture_benefit_persistence',[f'boundary_900041_g{g}.npz' for g in (1,2,3)]),
            ('E062','E062_cross_stage_compatibility',['source_900041.npz','interventions_900041.npz']),
            ('E064','E064_magnitude_subset_intervention',['interventions_900041.npz'])):
            run=ROOT/name/'runs'/f'{mode}_v1'
            complete=json.loads((run/'COMPLETE.json').read_text());audit=json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
            assert complete['status']=='COMPLETE' and audit['status']=='PASS'
            assert audit['complete_sha256']==sha(run/'COMPLETE.json')
            refs[number]=dict(path=str(run.relative_to(ROOT)),
                receipts={str((run/n).relative_to(ROOT)):sha(run/n) for n in ('COMPLETE.json','INDEPENDENT_AUDIT.json','manifest.json')},
                files={n:complete['outputs_sha256'][n] for n in names})
        technical[mode]=refs
    dump(target,dict(utc=utc(),blocks=list(BLOCKS),excluded_block=TECH_BLOCK,
        prior_manifest_sha256=manifests,prior_block_ids=sorted(seen),predecessors=predecessors,
        technical_references=technical,old_scientific_cases_pooled=False,scientific_outcomes_seen=False))


def verify_receipts(mode):
    reg=json.loads((HERE/'SOURCE_DATA.json').read_text());seen=set()
    for rel,digest in reg['prior_manifest_sha256'].items():
        assert sha(ROOT/rel)==digest,rel
        seen.update(json.loads((ROOT/rel).read_text())['contract']['blocks'])
    assert sorted(seen)==reg['prior_block_ids'] and not seen.intersection(BLOCKS)
    assert reg['blocks']==list(BLOCKS) and reg['excluded_block']==TECH_BLOCK
    for rel,digest in reg['predecessors'].items():assert sha(ROOT/rel)==digest,rel
    if mode!='scientific':
        for entry in reg['technical_references'][mode].values():
            for rel,digest in entry['receipts'].items():assert sha(ROOT/rel)==digest,rel


def reference(mode,experiment,name):
    assert mode in ('fixture','benchmark')
    entry=json.loads((HERE/'SOURCE_DATA.json').read_text())['technical_references'][mode][experiment]
    raw=(ROOT/entry['path']/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==entry['files'][name]
    with np.load(io.BytesIO(raw),allow_pickle=False) as z:return {k:z[k] for k in z.files}


def save(path,arrays):
    assert all(np.isfinite(x).all() for x in arrays.values())
    with Path(path).open('xb') as f:np.savez_compressed(f,**arrays)


def load(path):
    with np.load(path,allow_pickle=False) as z:out={k:z[k] for k in z.files}
    assert all(np.isfinite(x).all() for x in out.values())
    return out


def equal(a,b):
    assert set(a)==set(b),(set(a)-set(b),set(b)-set(a))
    for k in a:
        assert a[k].shape==b[k].shape and a[k].dtype==b[k].dtype,(k,a[k].shape,b[k].shape)
        assert a[k].tobytes()==b[k].tobytes(),k


def legacy_boundary(mode,stage,g,raw):
    if mode=='scientific':return
    old=reference(mode,'E057' if stage=='source' else 'E058',f'boundary_900041_g{g}.npz')
    equal({'masks':raw['masks']},{'masks':old['masks']})
    names=('incoming','effective_packets','denominator','end','late_ports','mean_ports',
           'ordinary','contrast','fallback','outgoing','write_end')
    if stage=='source':
        for k in names:
            want=old[k][:,:1] if k=='late_ports' else old[k][:1]
            equal({k:raw[k]},{k:want})
        equal({'birth':np.broadcast_to(raw['birth'][None,:,:,None],old['birth'][:1].shape)}, {'birth':old['birth'][:1]})
        for k in ('read_state_hashes','write_state_hashes'):equal({k:raw[k]},{k:old[k][:,0]})
    else:
        for k in names:
            if k in ('incoming','outgoing'):want=old[k][1,0,:2]
            elif k=='late_ports':want=old[k][:,10:12]
            else:want=old[k][10:12]
            equal({k:raw[k]},{k:want})
        equal({'birth':raw['birth']},{'birth':old['birth']})


def legacy_body(mode,body,outgoing):
    if mode=='scientific':return
    old=reference(mode,'E057','body_900041.npz')
    shared=('masks','available','birth','pulse_field','pulse_sites')
    for k in shared:equal({k:body[k]},{k:old[k]})
    for k in ('effective','denominator','coupling','initial','requested_squared','delivered_squared','clipping_count'):
        equal({k:body[k]},{k:old[k][1:2]})
    for k in ('states','port_windows','mean_ports'):equal({k:body[k]},{k:old[k][1:2,:,:2]})
    previous=reference(mode,'E057','outgoing_900041.npz')
    for k in outgoing:equal({k:outgoing[k]},{k:previous[k][1,:2]})
