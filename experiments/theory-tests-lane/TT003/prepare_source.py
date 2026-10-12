"""Prepare the predetermined exposed source packets and immutable references."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LANE = HERE.parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True); f.write('\n')


def main():
    plan = json.loads((HERE/'plan.json').read_text())
    run = (LANE/plan['source_run']).resolve()
    if sha(run/'COMPLETE.json') != plan['source_complete_sha256']:
        raise ValueError('Source completion changed')
    complete = json.loads((run/'COMPLETE.json').read_text())
    manifest = json.loads((run/'manifest.json').read_text())
    if sha(run/'manifest.json') != complete['outputs_sha256']['manifest.json']:
        raise ValueError('Source manifest changed')
    audit = json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    if audit['status'] != 'PASS' or audit['complete_sha256'] != plan['source_complete_sha256']:
        raise ValueError('Source audit mismatch')
    native = HERE/'reference/e041'; native.mkdir(parents=True, exist_ok=False)
    files = {}
    for rel, expected in manifest['inputs_sha256'].items():
        source = run/'inputs'/rel
        if sha(source) != expected: raise ValueError('Native source changed: '+rel)
        dest = native/rel; dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as f: f.write(source.read_bytes())
        files[str(dest.relative_to(HERE))] = expected
    theory = LANE/'reviews/P01_v0_2_intake/source'
    dest = HERE/'reference/theory'; dest.mkdir(parents=True, exist_ok=False)
    for name in ('two_mode.py', 'joint_kernel.py'):
        data = (theory/name).read_bytes()
        with (dest/name).open('xb') as f:f.write(data)
        files[str((dest/name).relative_to(HERE))] = sha(dest/name)
    dump(HERE/'reference_manifest.json', dict(files_sha256=files,
        native_complete_sha256=plan['source_complete_sha256'],
        theory_snapshot_sha256=sha(theory/'snapshot.json')))
    now = datetime.now(timezone.utc).isoformat()
    with (LANE/'exposure_register.jsonl').open('a') as f:
        f.write(json.dumps(dict(event='NATIVE_PILOT_SOURCE_ACCESS', recorded_utc=now,
            study='TT003', classification='DEVELOPMENT', blocks=plan['source_blocks'],
            founders=plan['founders'], source_depths=plan['source_depths'],
            selection='Fixed indices specified in protocol before packet read.'))+'\n')
    records, packets, sources = [], [], []
    for block in plan['source_blocks']:
        for depth in plan['source_depths']:
            name = f'source_{block:06d}.npz' if depth == 0 else f'boundary_{block:06d}_g{depth}.npz'
            path = run/name
            if sha(path) != complete['outputs_sha256'][name]: raise ValueError('Source array changed: '+name)
            sources.append(dict(path=str(path), sha256=sha(path)))
            with np.load(path, allow_pickle=False) as z:
                selected = z['acquired'][1] if depth == 0 else z['outgoing'][plan['source_policy_index'], :, plan['source_recipient']]
                if selected.shape != (4, 4096) or selected.dtype != np.uint8:
                    raise ValueError('Unexpected packet schema')
                if depth == 0:
                    np.testing.assert_array_equal(z['rules'], [1., -1., 1., -1.])
            for founder in plan['founders']:
                packet = selected[founder].copy()
                values = np.frombuffer(packet.tobytes(), dtype='<f8')
                if not np.isfinite(values).all() or np.max(abs(values)) > 1:
                    raise ValueError('Invalid inherited packet')
                records.append(dict(id=f'b{block}_h{depth}_f{founder}', block=block,
                    source_depth=depth, founder=founder, rule=1 if founder % 2 == 0 else -1,
                    source_recipient=None if depth == 0 else plan['source_recipient'],
                    source_array=name, packet_sha256=hashlib.sha256(packet.tobytes()).hexdigest()))
                packets.append(packet)
    with (HERE/'source_packets.npz').open('xb') as f:
        np.savez_compressed(f, packets=np.stack(packets))
    dump(HERE/'source_manifest.json', dict(status='EXPOSED_DEVELOPMENT_PACKETS', created_utc=now,
        source_complete_sha256=plan['source_complete_sha256'], sources=sources,
        packet_file_sha256=sha(HERE/'source_packets.npz'), records=records,
        original_acquisition_replayed=False, selection_on_outcome=False))
    print(json.dumps(dict(status='PREPARED', packets=len(packets), native_reference_files=len(files),
        source_blocks=plan['source_blocks'])))


if __name__ == '__main__':
    main()
