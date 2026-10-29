"""Plan precision using only the sealed H038 diagnostic network summaries."""
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import sys
import numpy as np

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE))
from h007.io import checksum, verify
from h039 import design as d

DEVELOPMENT = LANE/'runs/h038_diagnostic_v1'
MANIFEST = 'd14f6193e8952688aecc30bd31abe533545a819ced97c25a72d1885d8143b48e'


def build_plan():
    assert checksum(DEVELOPMENT/'checksums.json') == MANIFEST
    verify(DEVELOPMENT, 'checksums.json')
    files = sorted((DEVELOPMENT/'raw/diagnostic').glob('*.summary.json'))
    assert len(files) == 8
    points = [d.endpoints(json.loads(p.read_text())) for p in files]
    rows = {}
    for name in d.ENDPOINTS:
        x = np.array([p[name] for p in points])
        sd = float(x.std(ddof=1))
        rows[name] = dict(per_network=x.tolist(), sd=sd, inflated_sd=1.5*sd,
            required_blocks=math.ceil((1.96*1.5*sd/.05)**2))
    largest = max(r['required_blocks'] for r in rows.values())
    blocks = max(64, 8*math.ceil(largest/8))
    for r in rows.values():
        r['planned_marginal_half_width'] = 1.96*r['inflated_sd']/math.sqrt(blocks)
    matches = list((LANE/'runs').rglob('pilot_39039*.npz'))
    if matches:
        raise AssertionError('Proposed fresh block namespace already has raw arrays: '+str(matches[:3]))
    return dict(experiment='H039', created_utc=datetime.now(timezone.utc).isoformat(),
        development=str(DEVELOPMENT), development_manifest_sha256=MANIFEST,
        source_summary_sha256={str(p.relative_to(DEVELOPMENT)): checksum(p) for p in files},
        source_classification='H038 EXPOSED DEVELOPMENT ONLY', source_networks=8,
        target_marginal_95pct_half_width=.05, sd_inflation=1.5, multiplier=1.96,
        minimum_blocks=64, round_up_multiple=8, required_before_rounding=largest,
        blocks=blocks, block_ids=list(range(d.FIRST_BLOCK, d.FIRST_BLOCK+blocks)), endpoints=rows,
        preexisting_raw_artifact_matches=[], no_fresh_inputs_generated=True,
        note='Approximate precision planning using small exposed development sample; no coverage or power guarantee. '
             'Not simultaneous five-point precision; report attained intervals. No interim resizing or exclusions.')


if __name__ == '__main__':
    out = LANE/'h039/SAMPLE_SIZE.json'
    if out.exists():
        raise FileExistsError(out)
    result = build_plan()
    with out.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k: result[k] for k in ('blocks', 'required_before_rounding', 'target_marginal_95pct_half_width')}))
