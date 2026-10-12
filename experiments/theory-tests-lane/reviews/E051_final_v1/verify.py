"""Bounded completed-E051 review; no trajectory generation or dynamics replay."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LANE = HERE.parents[1]
RUN = LANE.parent / 'E051_cue_pairing_robustness/runs/robustness_v1'


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    with path.open('x') as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')


def main():
    assert not (HERE/'SOURCE_RECEIPT.json').exists(), 'Preserve completed review.'
    complete = read(RUN/'COMPLETE.json')
    manifest = read(RUN/'manifest.json')
    summary = read(RUN/'summary.json')
    audit = read(RUN/'INDEPENDENT_AUDIT.json')
    assert complete['status'] == 'COMPLETE' and complete['blocks_completed'] == 32
    assert audit['status'] == 'PASS' and audit['blocks'] == 32
    assert audit['complete_sha256'] == sha(RUN/'COMPLETE.json')
    assert audit['all_teaching_rebuilding_holding_and_assays_replayed'] is True
    assert audit['all_mechanism_counts_and_connectivity_replayed'] is True
    assert audit['audit_code_sha256'] == sha(RUN/'inputs/E051_cue_pairing_robustness/audit.py')
    inputs = manifest['inputs_sha256']
    for name, digest in inputs.items():
        assert sha(RUN/'inputs'/name) == digest, name
    for name in ['manifest.json', 'summary.json', 'REPORT.md']:
        assert sha(RUN/name) == complete['outputs_sha256'][name], name
    assert summary['blocks'] == list(range(34000,34032)) == manifest['contract']['blocks']
    assert summary['lineages_per_condition'] == 512
    assert summary['mode'] == 'scientific'
    # In this audit's schema, false means the scientific run did not redo the
    # excluded fixture/benchmark's legacy compatibility check, not a mismatch.
    assert audit['legacy_three_policies_all_boundaries_and_assays_match'] is False
    assert summary['legacy_reference_match'] is None

    sources = []
    def snapshot(source, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as handle:
            handle.write(source.read_bytes())
        digest = sha(source)
        assert sha(destination) == digest
        sources.append(dict(original_path=str(source.resolve()),
                            snapshot_path=str(destination.relative_to(LANE)), sha256=digest))

    for name in ['COMPLETE.json','manifest.json','summary.json','REPORT.md','INDEPENDENT_AUDIT.json']:
        snapshot(RUN/name, HERE/'source'/name)
    for name in inputs:
        snapshot(RUN/'inputs'/name, HERE/'source/inputs'/name)

    names = [*summary['conditions'], 'erased']
    assert len(names) == 36 and len(set(names)) == 36
    correct, fallback_rates, contrasts, raw_sources, ports = [], [], [], [], []
    rules, cues = [1.,-1.,1.,-1.], [1.,-1.]
    for block in summary['blocks']:
        paths = [RUN/f'cases_{block:06d}.npz', RUN/f'assay_{block:06d}_h32.npz']
        for path in paths:
            digest = sha(path)
            assert complete['outputs_sha256'][path.name] == digest, path.name
            raw_sources.append(dict(path=str(path.resolve()), sha256=digest))
        with np.load(paths[0], allow_pickle=False) as cases, np.load(paths[1], allow_pickle=False) as raw:
            values = raw['mean_ports']
            assert values.shape == (36,4,4,2,3,2)
            assert np.array_equal(values, cases['assay_h32_ports'])
            observed = np.zeros((36,4,4,2,3), dtype=bool)
            margins = np.empty(observed.shape)
            # Scalar endpoint reconstruction, independent of E051 scoring code.
            for n,f,r,c,j in np.ndindex(observed.shape):
                target = rules[f]*cues[c]
                one, two = target*values[n,f,r,c,j,0], -target*values[n,f,r,c,j,1]
                observed[n,f,r,c,j] = one > .25 and two > .25
                margins[n,f,r,c,j] = min(one,two)
            assert np.array_equal(observed, cases['assay_h32_correct'])
            assert np.array_equal(margins, cases['assay_h32_margin'])
            correct.append(observed)
            ports.append(values)
            count = cases['counts'][1:].sum(axis=(0,2,3))
            total = cases['sums'][1:].sum(axis=(0,2,3))
            assert (count[:,3]>0).all()
            fallback_rates.append(count[:,5]/count[:,3])
            contrasts.append(total[:,1]/count[:,3])
    correct, fallback_rates, contrasts = map(np.asarray, (correct, fallback_rates, contrasts))
    rates = correct.all(axis=4).mean(axis=(2,3))
    key = json.dumps(['E051','bootstrap','cue_pairing_robustness'], separators=(',',':')).encode()
    generator = np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16], 'little')))
    draws = generator.integers(0,32,(10000,32))
    checked = []
    def check(key, values):
        expected = dict(mean=float(values.mean()), block_means=values.tolist(),
                        ci95=np.quantile(values[draws].mean(axis=1), [.025,.975]).tolist())
        assert summary['statistics'][key] == expected, key
        checked.append(key)
        return expected
    for n,name in enumerate(names):
        for j,injury in enumerate(['intact','scattered','square']):
            check(f'assay/32/{name}/{injury}', rates[:,n,j])
    for n,name in enumerate(names[:-1]):
        pairing,writer = name.split('/')
        if pairing != 'paired':
            check(f'pairing_effect/{name}', rates[:,n,1]-rates[:,names.index('paired/'+writer),1])
        if writer != 'exact_rewrite':
            check(f'writer_effect/{name}', rates[:,n,1]-rates[:,names.index(pairing+'/exact_rewrite'),1])
        check(f'mechanism/{name}/ordinary_selected_returning', fallback_rates[:,n])
        check(f'mechanism/{name}/mean_abs_returning_contrast', contrasts[:,n])
    stats = summary['statistics']
    gates = dict(paired_baseline_lower_above_075=stats['assay/32/paired/exact_rewrite/scattered']['ci95'][0]>.75)
    for pairing in ['noise_0999','reset_099']:
        gates[pairing+'_lower_above_075'] = stats[f'assay/32/{pairing}/exact_rewrite/scattered']['ci95'][0]>.75
        gates[pairing+'_difference_lower_above_minus_005'] = stats[f'pairing_effect/{pairing}/exact_rewrite']['ci95'][0]>-.05
    assert gates == summary['primary_gates'] and all(gates.values())
    assert summary['primary_decision'] is True and audit['scientific_decision'] is True
    assert summary['status'] == 'PAIRING_ROBUSTNESS_ESTABLISHED'
    with (HERE/'h32_checked_arrays.npz').open('xb') as handle:
        np.savez_compressed(handle, blocks=summary['blocks'], conditions=names,
                            mean_ports=np.asarray(ports), correct=correct,
                            returning_fallback_rate=fallback_rates,
                            returning_mean_abs_contrast=contrasts)
    table = []
    for pairing,_,_ in summary['pairings']:
        table.append(dict(pairing=pairing, successes={writer:int(correct[:,names.index(pairing+'/'+writer),:,:,:,1].all(axis=3).sum())
                      for writer in summary['writers']}))
    receipt = dict(status='PASS', recorded_utc=datetime.now(timezone.utc).isoformat(),
        classification_for_new_RDT_claim='DEVELOPMENT', blocks=summary['blocks'],
        independent_blocks=32, lineages_per_condition=512,
        source_complete_sha256=sha(RUN/'COMPLETE.json'), source_audit_sha256=sha(RUN/'INDEPENDENT_AUDIT.json'),
        source_dynamics_audit_status='PASS', full_dynamics_replayed_by_this_review=False,
        frozen_inputs_verified=len(inputs), hashed_raw_inputs=raw_sources,
        h32_cue_observations_reconstructed=int(correct.size), statistics_verified=len(checked),
        statistics_verified_keys=checked, primary_gates=gates, successes=table, sources=sources,
        verification_code_sha256=sha(Path(__file__)), checked_arrays_sha256=sha(HERE/'h32_checked_arrays.npz'),
        limitation='Endpoint and selected summary verification, not an additional dynamics replay or independent cohort.',
        successor_job_launched=False, automatic_polling=False)
    write(HERE/'SOURCE_RECEIPT.json', receipt)
    print(json.dumps({k:receipt[k] for k in ['status','frozen_inputs_verified','h32_cue_observations_reconstructed','statistics_verified','primary_gates','successes']}, indent=2))


if __name__ == '__main__':
    main()
