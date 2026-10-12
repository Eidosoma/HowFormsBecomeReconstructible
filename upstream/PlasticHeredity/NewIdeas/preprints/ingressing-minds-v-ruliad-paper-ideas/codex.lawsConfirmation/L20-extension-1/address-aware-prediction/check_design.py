"""D170 design evidence only: saved assignments/metadata; no fitting or dynamics."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

import numpy as np
from l20_extension1 import pilot_models

HERE = Path(__file__).resolve().parent
WS = HERE.parent.parent
ROOT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
PILOT = 'l20_extension1_pilot64_v1_attempt1'
SWAP = 'l20_extension1_address_swap_v1_attempt1'
PINS = {
    f'runs/{PILOT}/COMPLETE.json': 'd77470be6d251f4d42344a6acfe0173fe3a542b04be2649de6e998bcfd95da53',
    f'logs/{PILOT}_saved_audit_v1.json': '822a61ccf5b8d26ff466a51cce226c12b20d0f5d5293778477e54a06323fd191',
    f'runs/{SWAP}/COMPLETE.json': '898fd26329f89d8123abf6561ded22876e258612195d1b748d18e5df79e8dcd2',
    f'logs/{SWAP}_saved_audit_v1.json': 'f6a78b24b80bb5b1c953b234315e1457dc9cb54ca79da90565dcafafe28505fa',
}
CODE = ('diagnostics', 'heldout_diagnostics', 'pilot_diagnostics', 'probe_system',
        'pilot_probe', 'pilot_models', 'recovery_features', 'difference_ablation',
        'pilot_diagnostic_audit', 'pilot_probe_audit', 'pilot_system',
        'pilot_repeated', 'passive_feedback')
PHASES = (('reader', 'birth_rng'), ('reader', 'read_rng'), ('writer', 'noise_rng'),
          ('terminal_reader', 'birth_rng'), ('terminal_reader', 'read_rng'))


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def bind(path, digest, used):
    path = Path(path)
    assert path.is_file() and not path.is_symlink()
    assert sha(path) == digest, str(path)
    key = str(path.resolve())
    assert key not in used or used[key] == digest
    used[key] = digest


def fingerprints(cell):
    return tuple(cell[section][name] for section, name in PHASES)


def synthetic_checks():
    # The current inference interface accepts measurements, never addresses/IDs.
    a = np.arange(112, dtype=float).reshape(1, 4, 4, 7)
    e = np.arange(288, dtype=float).reshape(1, 4, 4, 3, 6)
    data = dict(start=a, endpoint=e, targeted=e + 1000.)
    base = pilot_models.matrices(data)
    assert base['tied:passive'].shape == base['tied:sham_minus'].shape == (1, 4, 4, 19)
    np.testing.assert_array_equal(base['tied:passive'][..., :13], base['tied:sham_minus'][..., :13])
    changed = {k: v.copy() for k, v in data.items()}
    changed['endpoint'][..., 1, :] += 10
    np.testing.assert_array_equal(pilot_models.matrices(changed)['tied:sham_minus'], base['tied:sham_minus'])
    changed = {k: v.copy() for k, v in data.items()}
    changed['targeted'] += 10
    np.testing.assert_array_equal(pilot_models.matrices(changed)['tied:passive'], base['tied:passive'])
    for key in ('shift', 'q', 'founder_id', 'outcomes'):
        try:
            pilot_models.matrices(dict(data, **{key: np.zeros(1)}))
        except ValueError:
            pass
        else:
            raise AssertionError('extra inference field accepted: ' + key)
    # Independent closed forms for the already defined ideal-q geometry.
    y, x = np.indices((16, 16))
    targets = (np.where(y < 8, 1., -1.), np.where(x % 8 < 4, 1., -1.))
    for code in range(1, 256):
        dy, dx = divmod(code, 16)
        want = (1 - min(dy, 16-dy)/4, 1 - min(dx % 8, 8-dx % 8)/2)
        for role in range(2):
            assert np.mean(targets[role]*np.roll(targets[role], (dy, dx), (0, 1))) == want[role]
    # Address swaps affect a two-reading mean through interaction, not gap A.
    z = np.arange(120, dtype=float).reshape(30, 2, 2)**2 / 113
    original = (z[:, 0, 0] + z[:, 1, 1])/2
    swapped = (z[:, 0, 1] + z[:, 1, 0])/2
    interaction = (z[:, 1, 1]-z[:, 1, 0]) - (z[:, 0, 1]-z[:, 0, 0])
    np.testing.assert_allclose(swapped-original, -interaction/2, atol=2e-14, rtol=0)
    return dict(feature_boundary_checks=8, legal_shift_role_checks=510,
                factorial_identity_cases=30, fits=0, dynamics=0)


def review():
    used = {}
    for rel, digest in PINS.items():
        bind(ROOT/rel, digest, used)
    pilot = read(ROOT/'runs'/PILOT/'COMPLETE.json')
    swap = read(ROOT/'runs'/SWAP/'COMPLETE.json')
    expected = {}
    for name, done in ((PILOT, pilot), (SWAP, swap)):
        assert done['status'] == 'COMPLETE'
        path = ROOT/'runs'/name/'MANIFEST.json'
        bind(path, done['manifest_sha256'], used)
        manifest = read(path)
        audit = read(ROOT/'logs'/f'{name}_saved_audit_v1.json')
        assert audit['passes'] and audit['complete_sha256'] == PINS[f'runs/{name}/COMPLETE.json']
        for key, value in {**manifest['input_sha256'], **done['output_sha256']}.items():
            assert key not in expected or expected[key] == value
            expected[key] = value
    for name in CODE:
        path = WS/'L20-extension-1/src/l20_extension1'/f'{name}.py'
        bind(path, expected[str(path)], used)
    counts = []
    for co, ids in (('development', range(90000, 90016)), ('pilot', range(100000, 100064))):
        comparisons = phases = cases = coincident = 0
        for index in ids:
            if co == 'development':
                base = ROOT/'outputs/l20_extension1_heldout_v1_attempt1'/f'diagnostic_{index}'
                edits = ROOT/'outputs/l20_extension1_targeted_prediction_dev_v1_attempt1'/f'former_test_{index}'
            else:
                base = ROOT/'outputs'/PILOT/f'diagnostic_{index}'
                edits = ROOT/'outputs'/PILOT/f'targeted_{index}'
            for stem in (base, edits):
                for suffix in ('.json', '.npz'):
                    path = stem.with_suffix(suffix)
                    bind(path, expected[str(path)], used)
            bm, em = read(base.with_suffix('.json')), read(edits.with_suffix('.json'))
            assert len(bm['lives']) == len(em['lives']) == 4
            # Do not load diagnostic trajectories, predictions or any actual outcomes.
            with np.load(base.with_suffix('.npz'), allow_pickle=False) as opened:
                bs = opened['shift']
            with np.load(edits.with_suffix('.npz'), allow_pickle=False) as opened:
                es = opened['shift']
            assert bs.shape == es.shape == (4, 4, 3, 2)
            assert bs.dtype == es.dtype == np.int64
            for shifts in (bs, es):
                assert np.all((0 <= shifts) & (shifts < 16))
                assert not np.any(np.all(shifts == 0, axis=-1))
            for life in range(4):
                b, e = bm['lives'][life], em['lives'][life]
                assert b['index'] == e['spec'][1] == index and b['life'] == e['life'] == life
                assert b['tag'] == e['physics_namespace']
                assert b['branches'] == ['U0', 'U1', 'C1']
                assert e['edits'] == ['attenuate', 'sham_plus', 'sham_minus']
                assert not b['diagnostic_to_lineage'] and not e['diagnostic_to_lineage']
                assert not e['rerouted_after_edit'] and not e['independent_new_noise']
                coincident += int(np.array_equal(bs[life, 0, 0], bs[life, 0, 1]))
                for group in range(4):
                    u0, u1, c1 = b['cycles'][group]
                    assert u0['trial'] == 0 and u1['trial'] == c1['trial'] == 1
                    assert all(x != y for x, y in zip(fingerprints(u0), fingerprints(u1)))
                    for branch, cell in enumerate((u0, u1, c1)):
                        np.testing.assert_array_equal(bs[life, group, branch], cell['writer']['shift'])
                    others = [(c1, bs[life, group, 2])]
                    others += [(e['cells'][group][j], es[life, group, j]) for j in range(3)]
                    for cell, shift in others:
                        assert cell['trial'] == 1
                        assert fingerprints(cell) == fingerprints(u1)
                        np.testing.assert_array_equal(shift, bs[life, group, 1])
                        np.testing.assert_array_equal(shift, cell['writer']['shift'])
                        comparisons += 1
                        phases += len(PHASES)
                    np.testing.assert_array_equal(bs[life, group], bs[life, 0])
                    cases += 1
        counts.append(dict(cohort=co, founders=len(ids), lives=len(ids)*4, cases=cases,
                           matched_second_copy_comparisons=comparisons, matched_phase_fingerprints=phases,
                           coincident_first_second_shift_lives=coincident))
    path = ROOT/'outputs'/SWAP/'summary.json'
    bind(path, expected[str(path)], used)
    summary = read(path)
    illustration = []
    for row in summary['rows']:
        if row['group'] == 'B_ordinary' and row['response'] == 'outgoing_own':
            z = np.asarray(row['cell_mean'])
            delta = (z[0, 1]+z[1, 0]-z[0, 0]-z[1, 1])/2
            assert abs(delta + row['contrasts']['interaction']['mean']/2) < 2e-15
            illustration.append(dict(cohort=row['cohort'], passive_mean_swap_change=float(delta),
                                     diagnostic_feature_only=True, forecast_change_calculated=False))
    for path, digest in used.items():
        assert sha(path) == digest
    return dict(passes=True, cohort_checks=counts, pair_mean_identity=illustration,
                source_sha256=used, sources_checked=len(used), synthetic=synthetic_checks(),
                proposed_counts=dict(augmented_observers=7, alphas=3, founder_folds=16,
                                     fits=7*3*16, out_of_fold_prediction_records=7*3*16*16,
                                     diagnostic_cycles=0, new_lineages=0),
                physics_replayed=False, actual_outcome_arrays_loaded=0, new_fits=0,
                new_forecasts=0, new_dynamics=0, new_founders=0, prospective_evidence=False)


def main():
    assert not sys.flags.optimize, 'assertions required'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-receipt', action='store_true')
    args = parser.parse_args()
    start = time.monotonic()
    result = review()
    docs = [HERE/k for k in ('DESIGN_REVIEW.md', 'PROPOSAL_V1.md', 'check_design.py')]
    links = 0
    for path in [HERE/'README.md', *docs[:2]]:
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            assert (HERE/target.split('#')[0]).is_file(), (path, target)
            links += 1
    result.update(checked_utc=datetime.now(timezone.utc).isoformat(), seconds=time.monotonic()-start,
                  documentation_sha256={str(p): sha(p) for p in docs}, local_links=links,
                  status='DESIGN_REVIEW_COMPLETE', future_prediction_run_authorized=False)
    if args.write_receipt:
        path = ROOT/'logs/d170_prediction_design_review_v1.json'
        assert path.parent.resolve() == ROOT/'logs' and not path.is_symlink()
        with path.open('x') as handle:
            json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('source_sha256', 'documentation_sha256')}, sort_keys=True))


if __name__ == '__main__':
    main()
