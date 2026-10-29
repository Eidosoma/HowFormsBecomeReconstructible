"""Snapshot verified native physics and every actual historical packet version."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent
LANE = ROOT.parent
PREVIOUS = LANE/'TT024'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as stream: json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False); stream.write('\n')
def data(p):
    with np.load(p, allow_pickle=False) as f: return {k: f[k].copy() for k in f.files}
def copy(p, target, expected):
    assert sha(p) == expected, str(p)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream: stream.write(p.read_bytes())
    assert sha(target) == expected

def main():
    assert not (ROOT/'BASELINE_MANIFEST.json').exists()
    handoff = read(PREVIOUS/'DIAGNOSTIC_HANDOFF.json'); assert handoff['status'] == 'PASS_SAVED_DIAGNOSTIC_HANDOFF'
    archive = ROOT/'intake_inputs'; archive.mkdir(exist_ok=False); archived = []
    for name, expected in handoff['files'].items():
        p = Path(name); target = archive/p.relative_to(LANE); copy(p, target, expected)
        archived.append(dict(original=name, snapshot=str(target), sha256=expected))
    copy(PREVIOUS/'DIAGNOSTIC_HANDOFF.json', archive/'TT024/DIAGNOSTIC_HANDOFF.json', sha(PREVIOUS/'DIAGNOSTIC_HANDOFF.json'))
    write(archive/'MANIFEST.json', dict(status='PASS', files=archived, previous_handoff_sha256=sha(PREVIOUS/'DIAGNOSTIC_HANDOFF.json')))
    source = read(PREVIOUS/'SOURCE_MANIFEST.json'); files = []
    for row in source['files']:
        p = PREVIOUS/row['snapshot']; copy(p, ROOT/row['snapshot'], row['sha256'])
        files.append(dict(snapshot=row['snapshot'], sha256=row['sha256'], bytes=p.stat().st_size, copied_from=str(p)))
    reference = PREVIOUS/'tt019_reference.py'; copy(reference, ROOT/'physical_reference.py', sha(reference))
    write(ROOT/'SOURCE_MANIFEST.json', dict(files=files, reference_sha256=sha(reference), reference_original=str(reference),
        previous_manifest_sha256=sha(PREVIOUS/'SOURCE_MANIFEST.json')))
    import common as c
    import design
    evidence = {str(p): sha(p) for p in (PREVIOUS/'CLOSEOUT.json', PREVIOUS/'FREEZE.json',
        PREVIOUS/'checks/closeout_v1/ORIGINAL_FILES.json', PREVIOUS/'runs/serial_v1/COMPLETE.json',
        PREVIOUS/'runs/benchmark_v1/COMPLETE.json', PREVIOUS/'diagnostics/serial_changes_v1/AUDIT.json')}
    entries = {}
    for role in ('development', 'excluded'):
        base = PREVIOUS/'runs'/('serial_v1' if role == 'development' else 'benchmark_v1')
        mapping = read(PREVIOUS/'checks/closeout_v1/ORIGINAL_FILES.json') if role == 'development' else read(base/'COMPLETE.json')['outputs']
        indices = c.BLOCKS if role == 'development' else c.DISPOSABLE
        histories, _, cycles = design.schedule('development' if role == 'development' else 'benchmark')
        for index in indices:
            config_path = base/f'tissue_{index}/CONFIG.json'
            assert sha(config_path) == mapping[str(config_path)]; evidence[str(config_path)] = sha(config_path)
            cfg = read(config_path)
            assert cfg['config']['replicates'] == 4 and cfg['generations'] >= cycles
            sweeps = cfg['config']['sweeps']
            for history in range(histories):
                for family in design.FAMILIES:
                    packets = {}; historical = {}; routes = {}; provenance = {}
                    directory = ROOT/f'baseline/{role}/tissue_{index}/future_{history:02d}/{family}'
                    directory.mkdir(parents=True, exist_ok=False)
                    def checked(path):
                        assert sha(path) == mapping[str(path)], str(path)
                        provenance[str(path)] = mapping[str(path)]
                        return path
                    for arm in design.ARMS:
                        original = base/f'tissue_{index}/future_{history:02d}'/family/arm
                        carried = data(checked(original/'packets.npz'))
                        if 'initial' not in packets: packets['initial'] = carried['initial'].copy()
                        assert carried['initial'].tobytes() == packets['initial'].tobytes()
                        historical[arm] = read(checked(original/'records.json'))
                        assert len(historical[arm]) == 16
                        incoming = carried['initial']; routes[arm] = []
                        for g in range(1, cycles+1):
                            meta = read(checked(original/f'g{g:02d}.json'))
                            raw_path = checked(original/f'g{g:02d}_repair.npz'); raw = data(raw_path)
                            assert sha(raw_path) == meta['files']['repair'] and c.identities(raw) == meta['arrays']['repair']
                            assert raw['s0_theta'].tobytes() == incoming.tobytes()
                            outgoing = raw[f's{sweeps}_theta']; assert outgoing.dtype == np.float64 and outgoing.shape == (16, 16, 16)
                            assert np.isfinite(outgoing).all()
                            assert c.digest(incoming.tobytes()) == meta['input_sha256']
                            assert c.digest(outgoing.tobytes()) == meta['outgoing_sha256']
                            name = design.alias(arm, g)
                            if name == 'initial': assert outgoing.tobytes() == packets['initial'].tobytes()
                            else: packets[name] = outgoing.copy()
                            routes[arm].append(dict(generation=g, incoming=design.alias(arm, g-1), outgoing=name,
                                input_sha256=meta['input_sha256'], outgoing_sha256=meta['outgoing_sha256']))
                            incoming = outgoing
                        if cfg['generations'] == cycles: assert incoming.tobytes() == carried['final'].tobytes()
                        for i, r in enumerate(historical[arm]):
                            assert (r['world'], r['message'], r['replicate']) == (i, i//4, i % 4)
                    assert set(packets) == set(design.versions(cycles))
                    c.write_arrays(directory/'packets.npz', packets)
                    write(directory/'HISTORY.json', historical)
                    write(directory/'PROVENANCE.json', dict(role=role, index=index, historical_future=history, family=family,
                        cycles=cycles, config=cfg, routes=routes, arrays=c.identities(packets), original_files=provenance,
                        packet_bytes_per_record=2048, all_cases_retained=True, geometric_filter=False))
                    evidence.update(provenance)
                    entries[f'{role}:{index}:{history}:{family}'] = dict(directory=str(directory.relative_to(ROOT)),
                        files={str(p.relative_to(ROOT)): sha(p) for p in directory.iterdir()})
    write(ROOT/'BASELINE_MANIFEST.json', dict(recorded_utc=datetime.now(timezone.utc).isoformat(), rows=entries,
        evidence=evidence, inherited_outcomes_exposed=True, new_receiving_outcomes_generated=False))
    old_addresses = set(range(21000000, 21000064)) | set(c.DISPOSABLE)
    for index in sorted(old_addresses.copy()):
        for history in range(4):
            for g in range(1, 9):
                for phase in ('develop', 'terminal', 'fission', 'repair'):
                    raw = json.dumps(['TT022_serial_capture_v1', index, history, g, phase], separators=(',', ':')).encode()
                    old_addresses.add(int.from_bytes(hashlib.sha256(raw).digest()[:16], 'little'))
    old_seeds = {int.from_bytes(hashlib.sha256(f'l22-fixed-record-readout-v1:{key}:{phase}'.encode()).digest()[:16], 'little')
                 for key in old_addresses for phase in ('assay_birth', 'assay')}
    rows = []; keys = set(); seeds = set()
    for role in design.ROLES:
        histories, draws, _ = design.schedule(role)
        for index in c.BLOCKS if role == 'development' else c.DISPOSABLE:
            for history in range(histories):
                for draw in range(draws):
                    key = design.address(role, index, history, draw)
                    assert key not in keys and key not in old_addresses; keys.add(key)
                    stream_seeds = {}
                    for phase in ('assay_birth', 'assay'):
                        seed = int.from_bytes(hashlib.sha256(f'l22-fixed-record-readout-v1:{key}:{phase}'.encode()).digest()[:16], 'little')
                        assert seed not in seeds and seed not in old_seeds; seeds.add(seed); stream_seeds[phase] = seed
                    rows.append(dict(role=role, index=index, history=history, draw=draw, address=key, seeds=stream_seeds))
    write(ROOT/'RANDOMNESS.json', dict(status='PASS', namespace=design.TAG, addresses=rows,
        old_addresses_checked=len(old_addresses), old_reader_seeds_checked=len(old_seeds),
        new_addresses=len(keys), new_reader_seeds=len(seeds), production_random_samples_generated=False,
        scope='TT021 full 64-block panel and excluded blocks; TT022-TT024 bounded history/generation/phase schedules'))
    print(json.dumps(dict(status='PASS', native_source_files=len(files), baseline_groups=len(entries),
        baseline_files=sum(len(v['files']) for v in entries.values()), evidence_files=len(evidence),
        new_random_addresses=len(keys), new_dynamics=0), sort_keys=True))

if __name__ == '__main__': main()
