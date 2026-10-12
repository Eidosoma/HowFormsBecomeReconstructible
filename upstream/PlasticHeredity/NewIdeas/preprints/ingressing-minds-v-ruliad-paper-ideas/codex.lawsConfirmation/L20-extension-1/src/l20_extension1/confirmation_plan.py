"""D161 saved-data planning only: no fitting, founder generation or dynamics.

Normal-approximation widths are hypothetical design calculations, not confidence
intervals or power claims for the reused, overlapping development folds.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
from statistics import NormalDist, mean, stdev
import time
import xml.etree.ElementTree as ET

import numpy as np

ALPHAS = (.001, .01, .1)
CONDITIONS = ('passive', 'shuffle', 'attenuate', 'sham_plus', 'sham_minus')
COUNTS = (16, 32, 64, 128, 256, 512, 768, 1024)
MULTIPLIERS = (1., 1.5, 2.)
RESOLUTIONS = (.0025, .005, .01, .02)
Z = NormalDist().inv_cdf(.975)
PRIMARY = ('tied:sham_minus', 'tied:passive')
PAIRS = tuple(
    [('tied:'+c, 'separate:'+c) for c in CONDITIONS]
    + [(e+':'+c, e+':passive') for e in ('separate', 'tied')
       for c in CONDITIONS[1:]+('mean_sham_loss',)]
    + [(c, r) for c in ('tied:passive', 'tied:sham_minus', 'separate:sham_minus')
       for r in ('starting', 'one_copy')]
    + [('mean:passive', 'separate:passive'), ('tied:passive', 'mean:passive')])
RUN = 'l20_extension1_confirmation_design_v1_attempt1'
SOURCE_COMPLETE = '5466b207c1abfd79e673a13b1534b70f4882849c099f57747170c02c33266ab4'
SOURCE_AUDIT = 'cd587bf743b061d7388e7395a584663ecaef486b3e744317bb4078297cdf3272'


def choose(scores):
    """Minimum common absolute loss; ties within 1e-12 prefer larger alpha."""
    values = np.asarray(scores, dtype=float)
    if values.shape != (3,) or not np.isfinite(values).all() or np.min(values) < 0:
        raise ValueError('three finite nonnegative losses required')
    return max(i for i in range(3) if values[i] <= values.min()+1e-12)


def width(sd, n, multiplier=1.):
    if not math.isfinite(sd) or sd < 0 or type(n) is not int or n < 2:
        raise ValueError('nonnegative finite SD and at least two founders')
    if not math.isfinite(multiplier) or multiplier < 1:
        raise ValueError('SD sensitivity multiplier at least one')
    return Z*sd*multiplier/math.sqrt(n)


def required(sd, reference, resolution, multiplier=1.):
    if not math.isfinite(reference) or reference <= 0:
        raise ValueError('positive finite reference MSE required')
    if not math.isfinite(resolution) or resolution <= 0:
        raise ValueError('positive finite relative resolution required')
    width(sd, 2, multiplier)  # input checks, including zero SD
    return max(2, math.ceil((Z*sd*multiplier/(reference*resolution))**2))


def losses(predictions, futures):
    y = np.asarray(futures)
    if y.ndim != 4 or y.shape[0] < 2 or y.shape[1:] != (4, 4, 4):
        raise ValueError('founder, four lives, four groups, four futures')
    if not np.isfinite(y).all() or np.max(abs(y)) > 1:
        raise ValueError('finite bounded labels required')
    expected = {'starting', 'one_copy'} | {e+':'+c for e in ('separate', 'mean', 'tied') for c in CONDITIONS}
    if set(predictions) != expected:
        raise ValueError('retain all seventeen observers')
    out = {}
    for name, p in predictions.items():
        if p.shape != (3,)+y.shape[:3] or not np.isfinite(p).all() or np.max(abs(p)) > 1:
            raise ValueError('three finite bounded setting panels required')
        out[name] = (p[..., None]-y[None, ...])**2
    for e in ('separate', 'mean', 'tied'):
        out[e+':mean_sham_loss'] = (out[e+':sham_plus']+out[e+':sham_minus'])/2
    return out


def design(predictions, futures, ids):
    loss = losses(predictions, futures)
    if np.asarray(ids).shape != (len(futures),) or len(set(ids)) != len(ids):
        raise ValueError('unique founder identities required')
    absolute = {k: v.mean(axis=(1, 2, 3, 4)).tolist() for k, v in loss.items()}
    joint = (np.asarray(absolute[PRIMARY[0]])+absolute[PRIMARY[1]])/2
    selected = choose(joint)
    rows = []
    for a, alpha in enumerate(ALPHAS):
        for c, r in PAIRS:
            per_future = (loss[r][a]-loss[c][a]).mean(axis=(1, 2))
            block = per_future.mean(-1)
            ref = float(loss[r][a].mean())
            sd = float(block.std(ddof=1))
            # No independence claimed between related cases, repeats, or CV fits.
            record = dict(alpha=alpha, candidate=c, reference=r, reference_mse=ref,
                candidate_mse=float(loss[c][a].mean()), mean_gain=float(block.mean()),
                relative_gain_percent=100*float(block.mean())/ref if ref else None,
                block_gains=block.tolist(), block_future_gains=per_future.tolist(), block_sd=sd,
                widths=[dict(founders=n, sd_multiplier=m, absolute=width(sd, n, m),
                    percent_of_development_reference=100*width(sd, n, m)/ref if ref else None)
                    for n in COUNTS for m in MULTIPLIERS],
                required=[dict(relative_resolution=h, sd_multiplier=m,
                    founders=required(sd, ref, h, m) if ref else None)
                    for h in RESOLUTIONS for m in MULTIPLIERS])
            rows.append(record)
    primary = next(r for r in rows if (r['candidate'], r['reference']) == PRIMARY and r['alpha'] == ALPHAS[selected])
    needed = required(primary['block_sd'], primary['reference_mse'], .0025, 1.5)
    proposed = max(128, 128*math.ceil(needed/128))
    cheap = {k: ALPHAS[choose(absolute[k])] for k in ('starting', 'one_copy')}
    return dict(schema='d161_confirmation_design_v1', stage='DESIGN_ONLY',
        source_founders=list(map(int, ids)), all_cases_retained=True,
        absolute_future_mse=absolute, comparisons=rows, primary_pair=list(PRIMARY),
        symmetric_alpha_scores=joint.tolist(), common_alpha=ALPHAS[selected], cheap_alphas=cheap,
        proposed_founders=proposed, required_founders_unrounded=needed,
        planning_resolution_fraction=.0025, planning_sd_multiplier=1.5,
        qualification_of_new_executor=False, prospective_evidence=False,
        confidence_intervals_for_development=False, posthoc_power=False,
        new_fits=0, new_forecasts=0, new_founders=0, new_lineages=0,
        automatic_successor=False)


def check_design(result, predictions, futures, ids):
    """Separate scalar-loop calculation of losses, SDs and the selection rule."""
    model_loss = {}
    for k, p in predictions.items():
        model_loss[k] = [[[[mean([(float(p[a,b,l,g])-float(y))**2 for y in futures[b,l,g]])
            for g in range(4)] for l in range(4)] for b in range(len(ids))] for a in range(3)]
    for e in ('separate', 'mean', 'tied'):
        model_loss[e+':mean_sham_loss'] = ((np.array(model_loss[e+':sham_plus'])+
            np.array(model_loss[e+':sham_minus']))/2).tolist()
    assert len(result['comparisons']) == len(PAIRS)*3
    for row, (a, c, r) in zip(result['comparisons'], [(a,c,r) for a in range(3) for c,r in PAIRS]):
        assert (row['alpha'], row['candidate'], row['reference']) == (ALPHAS[a], c, r)
        ref = model_loss[r][a]; cand = model_loss[c][a]
        blocks = [mean([ref[b][l][g]-cand[b][l][g] for l in range(4) for g in range(4)]) for b in range(len(ids))]
        np.testing.assert_allclose(row['block_gains'], blocks, rtol=0, atol=2e-16)
        np.testing.assert_allclose([row['mean_gain'], row['block_sd']], [mean(blocks), stdev(blocks)], rtol=0, atol=2e-16)
        for w in row['widths']:
            expected = NormalDist().inv_cdf(.975)*stdev(blocks)*w['sd_multiplier']/math.sqrt(w['founders'])
            np.testing.assert_allclose(w['absolute'], expected, rtol=0, atol=2e-16)
        for item in row['required']:
            if row['reference_mse']:
                n = item['founders']; h = item['relative_resolution']*row['reference_mse']
                assert width(stdev(blocks), n, item['sd_multiplier']) <= h+2e-16
                if n > 2: assert width(stdev(blocks), n-1, item['sd_multiplier']) > h-2e-16
    abs_scores = {k: [mean([v for block in a for life in block for v in life]) for a in values]
                  for k, values in model_loss.items()}
    for k in abs_scores: np.testing.assert_allclose(result['absolute_future_mse'][k], abs_scores[k], atol=2e-16, rtol=0)
    scores = [(abs_scores[PRIMARY[0]][i]+abs_scores[PRIMARY[1]][i])/2 for i in range(3)]
    picked = sorted([i for i, v in enumerate(scores) if v <= min(scores)+1e-12], reverse=True)[0]
    assert result['common_alpha'] == ALPHAS[picked]
    for k in ('starting', 'one_copy'):
        i = max(i for i,v in enumerate(abs_scores[k]) if v <= min(abs_scores[k])+1e-12)
        assert result['cheap_alphas'][k] == ALPHAS[i]
    return dict(passes=True, block_loss_rows=len(PAIRS)*3, scalar_loss_check=True, no_simulations=True)


def resource_projection(timings, n):
    if type(n) is not int or n < 2: raise ValueError('founder count')
    h, r, p = timings
    for t in timings:
        if t['status'] != 'COMPLETE' or t['checked_block_seconds'] <= 0: raise ValueError('completed positive timing')
    # D141: acquisition, original diagnostics, full controls + first primary
    # future. D142: four extra primary futures. D151: three extra diagnostics.
    per_block = h['checked_block_seconds']+.75*r['checked_block_seconds']+p['checked_block_seconds']
    per_bytes = h['uncompressed_block_bytes']+.75*r['uncompressed_block_bytes']+p['block_proof']['uncompressed_bytes']
    seconds = 1.25*n*per_block+600
    size = math.ceil(2*n*per_bytes)+512*1024**2
    return dict(founders=n, primary_cases=16*n, primary_future_outcomes=64*n,
        diagnostic_cycles=96*n, historical_serial_block_seconds=per_block,
        historical_serial_hours_with_margin=seconds/3600, projected_bytes=size,
        projected_gib=size/1024**3, free_required_gib=(size+4*1024**3)/1024**3,
        workers_maximum=6, parallel_speedup_assumed=False, actual_runtime_benchmark_required=True,
        full_controls_future0_only=True, preliminary_not_execution_authority=True,
        must_detach=seconds>600)


def sources():
    from . import difference_run as d
    from laws_confirmation.io import sha256_file
    run, out = d.paths(); c = d.io.read_json(run/'COMPLETE.json'); m = d.io.read_json(run/'MANIFEST.json')
    assert sha256_file(run/'COMPLETE.json') == SOURCE_COMPLETE
    assert c == d.io.read_json(run/'STATUS.json') and c['status'] == 'COMPLETE'
    assert not (run/'FAILED.json').exists() and len(m['input_sha256']) == 2252 and len(c['output_sha256']) == 9
    assert sha256_file(run/'MANIFEST.json') == c['manifest_sha256']
    audit = d.ROOT/'logs/l20_extension1_difference_ablation_dev_v1_attempt1_saved_audit_v1.json'
    assert sha256_file(audit) == SOURCE_AUDIT and d.io.read_json(audit)['passes']
    expected = {**m['input_sha256'], **c['output_sha256']}
    assert expected == d.io.hashes([Path(p) for p in expected])
    assert sha256_file(out/'output_hashes.sha256') == c['hash_index_sha256']
    assert (out/'output_hashes.sha256').read_text() == d.io.hash_text(c['output_sha256'])
    paths = [run/'COMPLETE.json', run/'MANIFEST.json', run/'STATUS.json', out/'output_hashes.sha256', audit]
    timings = []
    for name in ('heldout', 'repeated_futures', 'targeted_prediction_dev'):
        path = d.ROOT/'tmp'/f'l20_extension1_{name}_v1_attempt1_benchmark.json'
        assert str(path) in expected  # inherit previously sealed apparatus times
        timings.append(d.io.read_json(path))
    paths += [d.WS/p for p in ('difference-ablation/RESULTS.md', 'confirmation/PLAN_V1.md',
        'src/l20_extension1/confirmation_plan.py', 'tests/test_confirmation_plan.py')]
    return d, {**expected, **d.io.hashes(paths)}, timings


def calculate():
    d, hashes, timings = sources()
    from . import influence_run
    data, base, _ = influence_run.source_data()
    predictions = {**base, **d.io.load_npz(d.paths()[1]/'tied_full.npz')}
    result = design(predictions, data['futures'], data['block_ids'])
    checked = check_design(result, predictions, data['futures'], data['block_ids'])
    result['resource_scenarios'] = [resource_projection(timings, n) for n in COUNTS]
    result['recommended_resources'] = resource_projection(timings, result['proposed_founders'])
    return d, hashes, result, checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualification', type=Path)
    parser.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    tick = time.monotonic()
    d, inputs, result, proof = calculate()
    d.previous.resources(False)
    out = d.ROOT/'outputs'/RUN
    from laws_confirmation.io import utc_now, sha256_file
    if args.audit:
        complete = d.io.read_json(out/'COMPLETE.json')
        assert complete['status'] == 'DESIGN_COMPLETE' and complete['new_lineages'] == 0
        saved = d.io.read_json(out/'planning.json')
        assert saved == result and d.io.read_json(out/'verification.json') == proof
        assert complete['source_sha256'] == inputs
        assert complete['output_sha256'] == d.io.hashes([Path(p) for p in complete['output_sha256']])
        assert sha256_file(Path(complete['qualification']['path'])) == complete['qualification']['sha256']
        print(json.dumps(dict(passes=True, source_hashes=len(inputs), **proof_without_pass(proof), seconds=time.monotonic()-tick)))
        return
    if args.qualification is None: parser.error('--qualification required for saved design')
    d.io.require_beneath(args.qualification, d.ROOT/'logs')
    tree = ET.parse(args.qualification).getroot(); cases = tree.findall('.//testcase')
    assert len(cases) >= 20 and not any(tree.findall('.//'+k) for k in ('error','failure','skipped'))
    assert shutil.disk_usage(d.ROOT).free >= 4*1024**3+64*1024**2
    out.mkdir()  # single use; existing reports may never be overwritten
    try:
        d.io.write_json(out/'planning.json', result, d.ROOT)
        d.io.write_json(out/'verification.json', proof, d.ROOT)
        assert d.io.read_json(out/'planning.json') == result
        assert inputs == d.io.hashes([Path(p) for p in inputs])
        outputs = d.io.hashes([out/'planning.json', out/'verification.json'])
        complete = dict(status='DESIGN_COMPLETE', completed_utc=utc_now(), source_sha256=inputs,
            output_sha256=outputs, new_lineages=0, new_fits=0,
            qualification=dict(path=str(args.qualification), sha256=sha256_file(args.qualification), tests=len(cases)),
            seconds=time.monotonic()-tick, proposed_founders=result['proposed_founders'],
            actual_execution_authorized=False)
        d.io.write_json(out/'COMPLETE.json', complete, d.ROOT)
        print(json.dumps({k:v for k,v in complete.items() if k not in ('source_sha256','output_sha256')}, indent=2))
    except Exception as error:
        d.io.failure(out, error, d.ROOT)
        raise


def proof_without_pass(proof):
    return {k:v for k,v in proof.items() if k != 'passes'}


if __name__ == '__main__':
    main()
