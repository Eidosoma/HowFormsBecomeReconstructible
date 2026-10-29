"""Verify and restore each actual first-episode body and incoming packet."""
from dataclasses import asdict
from common import *
import design
import audit

def load(ctx, role, history, family):
    name = 'development' if role == 'development' else 'excluded'; index = ctx['index']
    entry = read_json(ROOT/'BASELINE_MANIFEST.json')['rows'][f'{name}:{index}:{history}:{family}']
    for p, expected in entry['files'].items(): assert sha(ROOT/p) == expected
    directory = ROOT/entry['directory']; data = arrays(directory/'initial.npz')
    provenance = read_json(directory/'PROVENANCE.json'); rows = read_json(directory/'HISTORY.json')
    assert identities(data) == provenance['initial_arrays']
    old_cfg = provenance['source_config']['config']; cfg = asdict(ctx['config'])
    assert {k:v for k,v in old_cfg.items() if k not in ('sweeps','times')} == {k:v for k,v in cfg.items() if k not in ('sweeps','times')}
    controls = {short:arrays(directory/f'native_{short}.npz') for short in ('full','corrected','zero')}
    for short, memory in (('full','full'),('corrected','subtract'),('zero','zero')):
        assert identities(controls[short]) == provenance['native_arrays'][short]
        state = audit.initial(data,memory,ctx['tissue'].resting)
        for key in KEYS: ref.exact(controls[short]['s0_'+key],state[key],'original initialized '+key)
    # Reconstruct the original injury independently from its actual developed body.
    raw_key = json.dumps(['TT022_serial_capture_v1',index,history,1,'fission'],separators=(',',':')).encode()
    key = int.from_bytes(hashlib.sha256(raw_key).digest()[:16],'little')
    rng = ref.Coupled(ref.SOURCE_TAG,key,'fission',4)
    axes = rng.integers(0,2,16); sides = rng.integers(0,2,16); grid = np.indices((16,16))
    kept = np.stack([grid[a]//8 == side for a,side in zip(axes,sides)])
    v = np.where(kept,data['developed_V'],ctx['tissue'].resting)+ctx['tissue'].copy_jitter*rng.standard_normal(data['developed_V'].shape)
    ref.exact(data['fresh'],~kept,'actual retained injury mask'); ref.exact(data['injured_V'],v,'actual injured body')
    for meta in provenance['source_metadata'].values(): assert meta['injury']['rng_final'] == rng.digest()
    labels = np.arange(16)//4; polarity = (ctx['codes'][labels]*kept).sum((1,2))/128
    assert set(polarity) <= {-1.,0.,1.}
    strata = [design.STRATA[0] if x == 1 else design.STRATA[1] if x == -1 else design.STRATA[2] for x in polarity]
    for i,row in enumerate(rows):
        assert row == dict(world=i,message=i//4,replicate=i % 4,developed_score=float(data['developed_correctness'][i,0]),injury_stratum=strata[i])
    observed = {k:data['developed_'+k] for k in ('scores','probabilities','correctness','margins')}
    ref.scores(ctx['codes'],dict(observed,**{f's{ctx["readout"].sweeps}_V':data['developed_V']}),ctx['readout'])
    return dict(data=data,controls=controls,history=rows,provenance=provenance)
