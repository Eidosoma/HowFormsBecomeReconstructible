"""Snapshot predetermined, exposed E051 packets and saved native assay checks."""
import hashlib
import json
from pathlib import Path

import numpy as np
import support as s


def main():
    run=(s.HERE.parent/s.PLAN['source_run']).resolve()
    if s.sha(run/'COMPLETE.json')!=s.PLAN['source_complete_sha256']: raise ValueError('Source completion changed')
    complete=json.loads((run/'COMPLETE.json').read_text())
    manifest=json.loads((run/'manifest.json').read_text())
    audit=json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    if audit['status']!='PASS' or audit['complete_sha256']!=s.PLAN['source_complete_sha256']: raise ValueError('Source audit does not pass')
    if s.sha(run/'manifest.json')!=complete['outputs_sha256']['manifest.json']: raise ValueError('Manifest changed')
    refs={}; folder=s.HERE/'reference/e051'; folder.mkdir(parents=True,exist_ok=False)
    for name,expected in manifest['inputs_sha256'].items():
        source=run/'inputs'/name
        if s.sha(source)!=expected: raise ValueError('Native input changed: '+name)
        dest=folder/name; dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(source.read_bytes())
        refs[str(dest.relative_to(s.HERE))]=expected
    for name in ['COMPLETE.json','manifest.json','INDEPENDENT_AUDIT.json']:
        dest=s.HERE/'reference'/name
        with dest.open('xb') as f:f.write((run/name).read_bytes())
        refs[str(dest.relative_to(s.HERE))]=s.sha(dest)
    s.dump(s.HERE/'reference_manifest.json',dict(files_sha256=refs))
    with (s.HERE.parent/'exposure_register.jsonl').open('a') as f:
        f.write(json.dumps(dict(event='TT005_SOURCE_PACKET_REUSE',recorded_utc=s.utc(),study='TT005',classification='DEVELOPMENT',blocks=s.PLAN['blocks'],founders=s.PLAN['founders'],recipient=s.PLAN['recipient'],selection='Identifiers fixed in accepted draft; source outcomes already exposed. No new native assay outcomes.'))+'\n')
    contexts=[]; packets=[]; sources=[]; check_weights=[]; check_masks=[]; check_birth=[]; check_end=[]; check_ports=[]
    native_names=manifest['contract']['conditions']; indices=[native_names.index(name) for name in s.NAMES[:-2]]
    selected=indices+[35]
    for block in s.PLAN['blocks']:
        names=[f'source_{block:06d}.npz',f'boundary_{block:06d}_g32.npz',f'assay_{block:06d}_h32.npz']
        data=[]
        for name in names:
            path=run/name
            if s.sha(path)!=complete['outputs_sha256'][name]: raise ValueError('Source array changed: '+name)
            sources.append(dict(path=str(path),sha256=s.sha(path)))
            with np.load(path,allow_pickle=False) as z:data.append({k:z[k] for k in z.files})
        source,boundary,assay=data
        np.testing.assert_array_equal(source['rules'],[1.,-1.,1.,-1.])
        for f in s.PLAN['founders']:
            r=s.PLAN['recipient']; own=boundary['outgoing'][indices,f,r].copy()
            values=np.concatenate((own,np.zeros((1,4096),np.uint8),source['acquired'][1,f^1][None]),axis=0)
            if values.shape!=(11,4096) or values.dtype!=np.uint8: raise ValueError('Packet schema changed')
            weights=np.frombuffer(values.tobytes(),dtype='<f8')
            if not np.isfinite(weights).all() or np.max(abs(weights))>1: raise ValueError('Invalid weights')
            rows=[]
            for j,name in enumerate(s.NAMES):
                rows.append(dict(name=name,packet_sha256=hashlib.sha256(values[j].tobytes()).hexdigest(),
                    source=(names[1] if j<9 else 'constructed_zero' if j==9 else names[0]),
                    source_founder=f if j<10 else f^1))
            contexts.append(dict(id=f'b{block}_f{f}_r{r}',block=block,founder=f,recipient=r,rule=1 if f%2==0 else -1,packets=rows))
            packets.append(values)
            check_weights.append(values[:10]);check_masks.append(assay['masks'][f,r,1])
            check_birth.append(assay['birth'][f,r,1])
            check_end.append(assay['end'][selected,f,r,:,1]);check_ports.append(assay['mean_ports'][selected,f,r,:,1])
    with (s.HERE/'source_packets.npz').open('xb') as f:np.savez_compressed(f,packets=np.stack(packets))
    with (s.HERE/'native_checks.npz').open('xb') as f:
        np.savez_compressed(f,packets=np.stack(check_weights),masks=np.stack(check_masks),birth=np.stack(check_birth),
                            read_end=np.stack(check_end),mean_ports=np.stack(check_ports))
    s.dump(s.HERE/'source_manifest.json',dict(status='EXPOSED_DEVELOPMENT_PACKETS',created_utc=s.utc(),
        source_complete_sha256=s.PLAN['source_complete_sha256'],source_audit_sha256=s.sha(run/'INDEPENDENT_AUDIT.json'),
        sources=sources,contexts=contexts,prepared_files_sha256={name:s.sha(s.HERE/name) for name in ['source_packets.npz','native_checks.npz']},
        context_count=len(contexts),study_packets=72,controls=16,new_native_assays=0,acquisition_replayed_by_this_lane=False))
    print(json.dumps(dict(status='PREPARED',contexts=len(contexts),study_packets=72,controls=16,saved_assay_checks=80)))


if __name__=='__main__':main()
