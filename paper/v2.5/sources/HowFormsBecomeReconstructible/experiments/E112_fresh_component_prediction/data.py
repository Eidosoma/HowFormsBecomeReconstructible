"""Fresh-ID registry, pinned excluded golden data, and append-only exports."""
import json
from common import dump, sha, utc
from E083_reader_repeatability.data import save, load, equal
from E103_saved_sign_organization.data import output_csv
from E112_fresh_component_prediction.plan import HERE, ROOT, BLOCKS, TECHNICAL, PRIMARY

GOLDEN = {'E098':'E098_writer_pairing_tradeoff', 'E102':'E102_selected_sign_arrangement',
          'E105':'E105_cycle_input_control', 'E109':'E109_noise_phase_factorial',
          'E111':'E111_halfway_component_cross'}


def manifests():
    return sorted(p for p in set(ROOT.glob('E*/runs/*/manifest.json')) |
                  set(ROOT.glob('E*/jobs/*/manifest.json')) if not p.is_relative_to(HERE))


def register():
    target = HERE/'SOURCE_DATA.json'
    assert not target.exists()
    prior = {}; seen = set(); technical = {}; receipts = {}
    for path in manifests():
        blocks = json.loads(path.read_text()).get('contract', {}).get('blocks', [])
        if blocks:
            prior[str(path.relative_to(ROOT))] = sha(path); seen.update(blocks)
    assert set(BLOCKS).isdisjoint(seen) and set(BLOCKS).isdisjoint(TECHNICAL)
    for folder in GOLDEN.values():
        run = ROOT/folder/'runs/benchmark_v1'
        receipt = json.loads((run/'COMPLETE.json').read_text())
        assert receipt['status'] == 'COMPLETE' and receipt['controls_pass']
        receipts[str((run/'COMPLETE.json').relative_to(ROOT))] = sha(run/'COMPLETE.json')
        for path in sorted(run.glob('*.npz')):
            if not any(str(b) in path.name for b in TECHNICAL): continue
            h = sha(path); assert receipt['outputs_sha256'][path.name] == h
            technical[str(path.relative_to(ROOT))] = h
    parent = ROOT/'E111_halfway_component_cross'
    close = parent/'analysis/closeout_v1.json'
    assert json.loads(close.read_text())['status'] == 'PASS'
    for path in (close, parent/'PROTOCOL.md', parent/'SAMPLE_FREEZE.json'):
        receipts[str(path.relative_to(ROOT))] = sha(path)
    dump(target, dict(utc=utc(), blocks=list(BLOCKS), excluded=list(TECHNICAL),
        excluded_ids_deliberately_reused_for_exact_pipeline_validation=True,
        prior_manifest_sha256=prior, prior_block_ids=sorted(seen), receipts=receipts,
        technical_sha256=technical, primary=PRIMARY, outcome_informed_hypothesis=True,
        scientific_sources_generated=False, old_scientific_cases_pooled=False))


def registry(all_files=False):
    reg = json.loads((HERE/'SOURCE_DATA.json').read_text())
    assert reg['blocks'] == list(BLOCKS)
    for path, h in (reg['prior_manifest_sha256'] | reg['receipts']).items():
        assert sha(ROOT/path) == h, path
    seen = set()
    for path in manifests():
        seen.update(json.loads(path.read_text()).get('contract', {}).get('blocks', []))
    assert set(BLOCKS).isdisjoint(seen), 'Fresh source IDs used outside E112'
    if all_files:
        for path, h in reg['technical_sha256'].items(): assert sha(ROOT/path) == h, path
    return reg


def golden(experiment, name):
    path = ROOT/GOLDEN[experiment]/'runs/benchmark_v1'/name
    reg = json.loads((HERE/'SOURCE_DATA.json').read_text())
    assert sha(path) == reg['technical_sha256'][str(path.relative_to(ROOT))]
    return load(path)


def compare_ancestry(run, task):
    """Every retained E098 numerical field, including both endpoint readers."""
    reg = json.loads((HERE/'SOURCE_DATA.json').read_text()); checked = 0
    prefix = GOLDEN['E098'] + '/runs/benchmark_v1/'
    for rel in reg['technical_sha256']:
        if rel.startswith(prefix) and str(task) in rel:
            path = ROOT/rel
            equal(load(run/path.name), golden('E098', path.name)); checked += 1
    assert checked > 40
    return checked
