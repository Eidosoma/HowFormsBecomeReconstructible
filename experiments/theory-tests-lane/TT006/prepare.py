"""Copy reviewed theory and exposed TT003 inputs, preserving source identities."""
import json
from pathlib import Path
import support as s


def main():
    lane=s.HERE.parent;run=lane/s.PLAN['source_run']
    if s.sha(run/'COMPLETE.json')!=s.PLAN['source_complete_sha256']:raise ValueError('TT003 completion changed')
    complete=json.loads((run/'COMPLETE.json').read_text());files={};sources=[]
    for name in ['COMPLETE.json','manifest.json','summary.json','observations.npz']:
        source=run/name
        if name!='COMPLETE.json' and s.sha(source)!=complete['outputs_sha256'][name]:raise ValueError(name)
        dest=s.HERE/'source/tt003'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(source.read_bytes())
        files[str(dest.relative_to(s.HERE))]=s.sha(dest);sources.append(dict(original=str(source),copy=str(dest.relative_to(s.HERE)),sha256=s.sha(source)))
    theory=lane/'reviews/P01_v0_2_intake/source'
    for name in ['two_mode.py','joint_kernel.py','PROTOCOL.md','prediction_manifest.json']:
        source=theory/name;dest=s.HERE/'source/theory'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(source.read_bytes())
        files[str(dest.relative_to(s.HERE))]=s.sha(dest);sources.append(dict(original=str(source),copy=str(dest.relative_to(s.HERE)),sha256=s.sha(source)))
    s.dump(s.HERE/'source_manifest.json',dict(created_utc=s.utc(),classification='DEVELOPMENT',
        tt003_complete_sha256=s.PLAN['source_complete_sha256'],files_sha256=files,sources=sources,native_trajectories_generated=0))
    print(json.dumps(dict(status='PREPARED',files=len(files))))


if __name__=='__main__':main()
