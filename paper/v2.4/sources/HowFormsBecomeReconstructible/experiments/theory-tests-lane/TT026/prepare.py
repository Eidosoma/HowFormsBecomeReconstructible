"""Copy checked first-episode states and native controls without simulation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
LANE = ROOT.parent
OLD = LANE/'TT024'
PREVIOUS = LANE/'TT025'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def copy(path, target, expected):
    assert sha(path) == expected
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream: stream.write(path.read_bytes())
    assert sha(target) == expected
def write(path, value):
    with path.open('x') as stream: json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False); stream.write('\n')

def main():
    assert not (ROOT/'BASELINE_MANIFEST.json').exists()
    receipt = read(PREVIOUS/'COMPLETION_HANDOFF.json')
    assert receipt['status'] == 'PASS_COMPLETION_HANDOFF'
    archive = ROOT/'intake_inputs'; archive.mkdir(exist_ok=False); archived = []
    old_files = dict(receipt['files']); old_files[str(PREVIOUS/'COMPLETION_HANDOFF.json')] = sha(PREVIOUS/'COMPLETION_HANDOFF.json')
    for name, expected in old_files.items():
        path = Path(name); target = archive/path.relative_to(LANE); copy(path,target,expected)
        archived.append(dict(original=name,snapshot=str(target),sha256=expected))
    write(archive/'MANIFEST.json',dict(status='PASS',files=archived))
    source = read(PREVIOUS/'SOURCE_MANIFEST.json'); files = []
    for row in source['files']:
        path = PREVIOUS/row['snapshot']; copy(path,ROOT/row['snapshot'],row['sha256'])
        files.append(dict(snapshot=row['snapshot'],sha256=row['sha256'],bytes=path.stat().st_size,copied_from=str(path)))
    inherited = {'physical_reference.py':PREVIOUS/'physical_reference.py',
        'inherited_repair.py':OLD/'inherited23_kernel.py', 'receiving.py':PREVIOUS/'kernel.py'}
    for name, path in inherited.items(): copy(path,ROOT/name,sha(path))
    reader_audit = (PREVIOUS/'audit.py').read_text().replace('TT025_paired_receiving_v1','TT026_writing_window_v1')
    with (ROOT/'receiving_audit.py').open('x') as stream: stream.write(reader_audit)
    write(ROOT/'SOURCE_MANIFEST.json',dict(files=files,inherited_code={name:sha(ROOT/name) for name in inherited},
        inherited_from={name:str(path) for name,path in inherited.items()},
        receiving_audit_adaptation=dict(original=str(PREVIOUS/'audit.py'),original_sha256=sha(PREVIOUS/'audit.py'),
            change='Only receiving address namespace changed to TT026_writing_window_v1',sha256=sha(ROOT/'receiving_audit.py'))))
    import common as c
    import design
    evidence = {str(p):sha(p) for p in (OLD/'CLOSEOUT.json',OLD/'FREEZE.json',
        OLD/'checks/closeout_v1/ORIGINAL_FILES.json',OLD/'runs/serial_v1/COMPLETE.json',
        OLD/'runs/benchmark_v1/COMPLETE.json',PREVIOUS/'CLOSEOUT.json',PREVIOUS/'BASELINE_MANIFEST.json',PREVIOUS/'RANDOMNESS.json')}
    entries = {}
    paired = read(PREVIOUS/'BASELINE_MANIFEST.json')
    for role in ('development','excluded'):
        base = OLD/'runs'/('serial_v1' if role == 'development' else 'benchmark_v1')
        hashes = read(OLD/'checks/closeout_v1/ORIGINAL_FILES.json') if role == 'development' else read(base/'COMPLETE.json')['outputs']
        indices = c.BLOCKS if role == 'development' else c.DISPOSABLE
        for index in indices:
            config_path = base/f'tissue_{index}/CONFIG.json'; assert sha(config_path) == hashes[str(config_path)]
            evidence[str(config_path)] = sha(config_path); config = read(config_path); n = config['config']['sweeps']
            assert config['config']['replicates'] == 4
            for history in range(4 if role == 'development' else 1):
                for family in design.FAMILIES:
                    target = ROOT/f'baseline/{role}/tissue_{index}/future_{history:02d}/{family}'
                    target.mkdir(parents=True,exist_ok=False); originals = {}; controls = {}; meta = {}
                    common_initial = None
                    def checked(path):
                        assert sha(path) == hashes[str(path)], str(path)
                        originals[str(path)] = sha(path); return path
                    for short, arm in (('full','full_on'),('corrected','subtract_on'),('zero','zero_on')):
                        directory = base/f'tissue_{index}/future_{history:02d}'/family/arm
                        m = read(checked(directory/'g01.json'))
                        vals = {label:c.arrays(checked(directory/f'g01_{label}.npz')) for label in ('develop','boundary','repair','body')}
                        for label, values in vals.items():
                            assert c.identities(values) == m['arrays'][label] and sha(directory/f'g01_{label}.npz') == m['files'][label]
                        raw, boundary, developed = vals['repair'], vals['boundary'], vals['develop']
                        d = dict(incoming=raw['s0_theta'],injured_V=boundary['injured_V'],fresh=boundary['fresh'],developed_V=developed[f's{n}_V'])
                        d.update({f'developed_{k}':developed[k] for k in ('scores','probabilities','correctness','margins')})
                        if common_initial is None: common_initial = d
                        else: assert c.identities(d) == c.identities(common_initial)
                        assert raw['s0_V'].tobytes() == boundary['injured_V'].tobytes()
                        assert m['input_sha256'] == c.digest(d['incoming'].tobytes())
                        controls[short] = raw; meta[short] = m
                        c.write_arrays(target/f'native_{short}.npz',raw)
                        if short == 'full':
                            history_rows = read(checked(directory/'records.json'))
                    prior = paired['rows'][f'{role}:{index}:{history}:{family}']
                    packet_path = PREVIOUS/prior['directory']/'packets.npz'
                    assert sha(packet_path) == prior['files'][str(packet_path.relative_to(PREVIOUS))]
                    originals[str(packet_path)] = sha(packet_path)
                    assert c.arrays(packet_path)['initial'].tobytes() == common_initial['incoming'].tobytes()
                    c.write_arrays(target/'initial.npz',common_initial)
                    write(target/'HISTORY.json',[dict(world=r['world'],message=r['message'],replicate=r['replicate'],
                        developed_score=r['development'][0],injury_stratum=r['injury_strata'][0]) for r in history_rows])
                    write(target/'PROVENANCE.json',dict(role=role,index=index,history=history,family=family,
                        source_config=config,source_metadata=meta,original_files=originals,
                        initial_arrays=c.identities(common_initial),native_arrays={k:c.identities(v) for k,v in controls.items()},
                        first_episode=1,all_cases_retained=True,new_dynamics=0))
                    evidence.update(originals)
                    entries[f'{role}:{index}:{history}:{family}'] = dict(directory=str(target.relative_to(ROOT)),
                        files={str(p.relative_to(ROOT)):sha(p) for p in target.iterdir()})
    write(ROOT/'BASELINE_MANIFEST.json',dict(recorded_utc=datetime.now(timezone.utc).isoformat(),rows=entries,
        evidence=evidence,source_states_and_outcomes_exposed=True,new_production_dynamics=0))
    # New receiving streams; historical repair streams are intentionally retained.
    old_addresses = set(range(21000000,21000064)) | set(c.DISPOSABLE)
    for index in list(old_addresses):
        for history in range(4):
            for generation in range(1,9):
                for phase in ('develop','terminal','repair','fission'):
                    material = json.dumps(['TT022_serial_capture_v1',index,history,generation,phase],separators=(',',':')).encode()
                    old_addresses.add(int.from_bytes(hashlib.sha256(material).digest()[:16],'little'))
    old_addresses |= {v['address'] for v in read(PREVIOUS/'RANDOMNESS.json')['addresses']}
    seed = lambda key,phase: int.from_bytes(hashlib.sha256(f'l22-fixed-record-readout-v1:{key}:{phase}'.encode()).digest()[:16],'little')
    old_seeds = {seed(key,phase) for key in old_addresses for phase in ('assay_birth','assay')}
    addresses = set(); seeds = set(); rows = []
    for role in design.ROLES:
        histories,draws = design.schedule(role)
        for index in c.BLOCKS if role == 'development' else c.DISPOSABLE:
            for history in range(histories):
                for draw in range(draws):
                    key = design.address(role,index,history,draw)
                    assert key not in old_addresses and key not in addresses; addresses.add(key)
                    phases = {phase:seed(key,phase) for phase in ('assay_birth','assay')}
                    for v in phases.values(): assert v not in old_seeds and v not in seeds; seeds.add(v)
                    rows.append(dict(role=role,index=index,history=history,draw=draw,address=key,seeds=phases))
    write(ROOT/'RANDOMNESS.json',dict(status='PASS',namespace=design.TAG,addresses=rows,new_addresses=len(addresses),
        new_reader_seeds=len(seeds),old_addresses_checked=len(old_addresses),old_reader_seeds_checked=len(old_seeds),
        repair_streams='Intentionally restore the TT022 generation-one repair address for each historical future',
        production_random_samples_generated=False,scope='TT021 64 blocks plus excluded; TT022-TT024 bounded serial schedules; all TT025 recipient addresses'))
    print(json.dumps(dict(status='PASS',source_files=len(files),baseline_groups=len(entries),
        evidence_files=len(evidence),new_receiving_addresses=len(addresses),new_dynamics=0),sort_keys=True))

if __name__ == '__main__': main()
