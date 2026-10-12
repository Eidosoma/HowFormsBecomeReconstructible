"""Writer-only synthetic continuity check; no new body or lineage trajectories."""
import hashlib
import json
import os
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from common import sha,utc
# At most one CPU, within the shared experiment budget.
if hasattr(os,'sched_getaffinity'): os.sched_setaffinity(0,{max(os.sched_getaffinity(0))})
import numpy as np
from E041_full_rewrite_confirmation import model,audit


def main():
    run=ROOT/'E041_full_rewrite_confirmation/runs/serial_v1'
    manifest=json.loads((run/'manifest.json').read_text())
    for rel,digest in manifest['inputs_sha256'].items():
        assert sha(ROOT/rel)==sha(run/'inputs'/rel)==digest,rel
    samples=[]
    # An available horizontal edge between sites (0,0) and (0,1).
    # Both cues have activity .2 initially; perturb one cue at selected endpoints.
    for name,delta,endpoints in (
        ('matched',0.,()),('one_endpoint_1e-12',1e-12,(0,)),
        ('both_endpoints_1e-12',1e-12,(0,1)),('both_endpoints_1e-8',1e-8,(0,1))):
        body=np.full((9,4,1,2,16,16),.2,dtype=np.float64)
        for x in endpoints: body[:,:,:,0,0,x]+=(delta)
        packet=model.capture(body,3.)
        independent=audit.capture(body,3.)
        assert packet.dtype==independent.dtype and packet.shape==independent.shape
        assert packet.tobytes()==independent.tobytes()
        states=np.tanh(3.*body[3,0,0,:,0,:2])
        differences=(states[0]-states[1])/2
        contrast=float(differences[0]*differences[1])
        ordinary=float(np.mean(states[:,0]*states[:,1]))
        written=float(model.base.decode(packet)[3,0,0,0,0,0])
        fallback=contrast==0.
        assert written==(ordinary if fallback else contrast)
        assert fallback==(len(endpoints)<2)
        samples.append(dict(case=name,activity_perturbation=delta,perturbed_endpoints=list(endpoints),
            endpoint_cue_differences=differences.tolist(),contrast_product=contrast,
            ordinary_coactivity=ordinary,fallback_selected=fallback,written_weight=written))
    assert samples[0]['written_weight']>.28
    assert 0.<samples[2]['written_weight']<1e-22
    for rel,digest in manifest['inputs_sha256'].items(): assert sha(ROOT/rel)==digest
    result=dict(status='PASS',utc=utc(),scope='Synthetic writer-only check, no rebuilding trajectories or robustness outcome',
        source_run=str(run.relative_to(ROOT)),frozen_inputs_verified=len(manifest['inputs_sha256']),
        model_sha256=sha(ROOT/'E041_full_rewrite_confirmation/model.py'),
        audit_sha256=sha(ROOT/'E041_full_rewrite_confirmation/audit.py'),check_code_sha256=sha(__file__),
        manuscript_v013_sha256=sha(ROOT.parent/'PRE_PRINT_PAPER_DRAFT_V0.13.md'),
        samples=samples,production_and_independent_capture_byte_exact=True,
        fresh_scientific_runs_started=False,existing_jobs_polled=False,
        numerical_threads=1,cpu_affinity=sorted(os.sched_getaffinity(0)))
    dest=HERE/'writer_check.json'
    with dest.open('x') as f: f.write(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
