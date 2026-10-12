"""D129: post-hoc address ambiguity diagnostics; no dynamics or fitted decoder."""
from __future__ import annotations

import argparse
import hashlib
from functools import lru_cache
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np

from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT, environment_manifest, git_head, sha256_file, utc_now

WS = Path(__file__).resolve().parents[1]
RUN_ID = 'l20_address_ambiguity_audit_v1_attempt1'
SOURCE_RUN = 'l20_inverse_address_v1_attempt1'
SOURCE_COMPLETE = 'a44e28068d9512fe8a96a20c09796fd82dff7b9231d00f8dc6328a63cc471e2a'
SCIENCE = ('scripts/audit_l20_address_ambiguity.py', 'tests/test_l20_address_ambiguity.py',
           'scripts/run_l20_address_ambiguity.sh', 'protocols/L20_ADDRESS_AMBIGUITY_AUDIT_V1.md')
BASES = ('translated', 'rescued', 'aligned', 'aligned_inverse')
KINDS = BASES + tuple(k+'_shuffle' for k in BASES) + ('ideal', 'ideal_shifted', 'ideal_rescued', 'zero')
SOURCE_KINDS = BASES + tuple(k+'_shuffle' for k in BASES) + tuple(k+'_sham' for k in BASES) + tuple(k+'_off' for k in BASES) + ('ideal', 'ideal_shifted', 'ideal_rescued', 'zero')
SOURCE_CASES = tuple((r, k) for r in (0, 1) for k in SOURCE_KINDS)
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
INDICES = tuple(range(70000, 70008))
DISPOSABLE = 514228
ATOL = 1e-12
BUDGET = 32*1024**2
OUTPUTS = ('INPUTS.json', 'records.json', 'scores.npz', 'summary.json', 'verification.json')


def io_helpers():
    from laws_confirmation import l15_repair_speed_run as u
    from laws_confirmation.l16_body_content_run import preflight
    return u, preflight


def targets():
    y, x = np.indices((16, 16))
    return np.stack((np.where(y < 8, 1., -1.), np.where((x//4) % 2 == 0, 1., -1.)))


def decode(packet):
    if type(packet) is not bytes or len(packet) != 2048:
        raise ValueError('exactly 2048 packet bytes required')
    field = np.frombuffer(packet, dtype='<f8').reshape(16, 16).copy()
    if not np.isfinite(field).all():
        raise ValueError('finite packet required')
    return field


def encode(field):
    if field.shape != (16, 16) or field.dtype != np.float64 or not np.isfinite(field).all():
        raise ValueError('finite float64 16x16 field required')
    return field.astype('<f8').tobytes()


def move(field, shift):
    return np.roll(field, tuple(int(x) for x in shift), (0, 1))


@lru_cache(maxsize=1)
def bank():
    """Declared canonical-template prior, not learned from this cohort."""
    result = np.stack([[move(t, (dy, dx)) for dy in range(16) for dx in range(16)]
                       for t in targets()]).reshape(2, 16, 16, 16, 16)
    result.setflags(write=False)
    return result


def template_geometry():
    library = bank()
    rows, orbits = [], []
    for role, target in enumerate(targets()):
        orbit = library[role].reshape(256, 16, 16)
        distinct = {encode(t) for t in orbit}
        fixed = [list(divmod(i, 16)) for i, t in enumerate(orbit) if np.array_equal(t, target)]
        assert len(distinct)*len(fixed) == 256
        rows.append(dict(role=role, stabilizer_offsets=fixed, stabilizer_size=len(fixed),
            distinct_phases=len(distinct), ideal_exact_offset_ceiling_uniform_256=len(distinct)/256,
            ideal_exact_offset_ceiling_uniform_nonzero_255=len(distinct)/255,
            nonzero_alias_count_if_canonical=len(fixed)-1, nonzero_alias_count_otherwise=len(fixed)))
        orbits.append(distinct)
    assert not orbits[0] & orbits[1]
    return dict(target_prior='two supplied canonical binary templates', roles=rows,
        cross_family_orbit_collisions=0, shifts=256, rotations_tested=False,
        ceiling_scope='ideal translated templates with known family and uniform shift; NOT noisy developmental packets')


def byte_features(packet):
    """No target, label, historical shift, source state or RNG access."""
    field = decode(packet); centered = field-field.mean(); std = float(centered.std())
    if not np.isfinite(std):
        raise ValueError('finite packet scale required')
    energy = float(np.mean(centered*centered))
    distances = []
    fixed = 0
    for dy in range(16):
        for dx in range(16):
            shifted = move(field, (dy, dx))
            fixed += int(np.array_equal(shifted, field))
            if dy or dx:
                distances.append(float(np.sqrt(np.mean((shifted-field)**2))))
    return dict(packet_sha256=hashlib.sha256(packet).hexdigest(), mean=float(field.mean()),
        std=std, constant=bool(np.ptp(field) == 0),
        row_mean_variance_fraction=float(np.mean(centered.mean(axis=1)**2)/energy) if energy else 0.,
        column_mean_variance_fraction=float(np.mean(centered.mean(axis=0)**2)/energy) if energy else 0.,
        exact_self_symmetries=fixed, nearest_nonidentity_relative_rms=min(distances)/std if std else 0.)


def correlations(packet, library):
    """All template fits, retaining all shifts; never chooses a correction."""
    field = decode(packet); centered = field-field.mean(); std = float(centered.std())
    if library.shape != (2, 16, 16, 16, 16) or not np.array_equal(library, bank()):
        raise ValueError('fixed disclosed template bank required')
    if std == 0:
        return np.zeros((2, 16, 16))
    values = np.einsum('rabij,ij->rab', library, centered, optimize=False)/(256*std)
    if not np.isfinite(values).all():
        raise ValueError('finite correlations required')
    return values


def fft_check(packet, scores):
    """Independent circular-correlation indexing; no direct-score helper."""
    field = np.frombuffer(packet, dtype='<f8').reshape(16, 16)
    centered = field-np.mean(field); scale = np.sqrt(np.mean(centered**2))
    y, x = np.indices((16, 16))
    templates = (2.*(y < 8)-1., 2.*((x//4) % 2 == 0)-1.)
    expected = np.stack([np.fft.ifft2(np.fft.fft2(centered)*np.conj(np.fft.fft2(t))).real/(256*scale)
                         if scale else np.zeros((16, 16)) for t in templates])
    error = float(np.max(np.abs(expected-scores)))
    assert error <= ATOL
    return error


def expected_offset(kind, shift):
    """Post-scoring analyst comparator ONLY; never an inference input."""
    if kind not in KINDS or not isinstance(shift, np.ndarray) or shift.dtype != np.int64 or shift.shape != (2,) or not np.all((shift >= 0) & (shift < 16)):
        raise ValueError('declared kind and int64 toroidal shift required')
    if kind in ('translated', 'ideal_shifted'):
        return np.asarray(shift, dtype=np.int64)
    if kind == 'aligned_inverse':
        return (-np.asarray(shift, dtype=np.int64)) % 16
    if kind in ('rescued', 'aligned', 'ideal', 'ideal_rescued'):
        return np.zeros(2, dtype=np.int64)
    return None


def interpret(scores, role, expected):
    if scores.shape != (2, 16, 16) or not np.isfinite(scores).all() or type(role) is not int or role not in (0, 1):
        raise ValueError('complete finite score bank and evaluation role required')
    maxima = scores.max(axis=(1, 2))
    tied_roles = np.flatnonzero(maxima >= float(maxima.max())-ATOL)
    own_mask = scores[role] >= maxima[role]-ATOL
    result = dict(own_best_correlation=float(maxima[role]), other_best_correlation=float(maxima[1-role]),
        family_margin=float(maxima[role]-maxima[1-role]),
        unique_family_correct=bool(len(tied_roles) == 1 and tied_roles[0] == role),
        unique_family_wrong=bool(len(tied_roles) == 1 and tied_roles[0] != role),
        family_tied=bool(len(tied_roles) == 2), own_optimal_offsets=int(own_mask.sum()),
        joint_optimal_offsets=int((scores >= float(scores.max())-ATOL).sum()))
    if expected is None:
        result.update(expected_offset=None, expected_phase_in_own_optima=None,
            expected_phase_in_joint_optima=None, expected_correlation=None,
            own_fit_gap_at_expected=None, distance_to_own_optima=None)
    else:
        offset = np.asarray(expected)
        if offset.shape != (2,) or offset.dtype != np.int64 or not np.all((offset >= 0) & (offset < 16)):
            raise ValueError('declared toroidal offset required')
        value = float(scores[role, offset[0], offset[1]])
        delta = abs(np.argwhere(own_mask)-offset); delta = np.minimum(delta, 16-delta)
        result.update(expected_offset=offset.tolist(), expected_phase_in_own_optima=bool(own_mask[tuple(offset)]),
            expected_phase_in_joint_optima=bool(value >= float(scores.max())-ATOL),
            expected_correlation=value, own_fit_gap_at_expected=float(maxima[role]-value),
            distance_to_own_optima=int(delta.sum(axis=1).min()))
    return result


def gauge_check(packet):
    """Algebraic observation model only, not alternative valid D127 histories."""
    observed = decode(packet); maximum = 0.
    for dy in range(16):
        for dx in range(16):
            latent = move(observed, (-dy, -dx))
            rebuilt = move(latent, (dy, dx))
            assert encode(rebuilt) == packet
            maximum = max(maximum, float(abs(rebuilt-observed).max()))
    return dict(equivalent_latent_shift_descriptions=256, nonzero_shift_descriptions=255, exact=True, max_abs=maximum,
        scope='unanchored translation observation model, NOT a bound for the fixed D127 source distribution')


def load_panel(index, root=DEFAULT_EXTERNAL_ROOT):
    if type(index) is not int or index not in (*INDICES, DISPOSABLE):
        raise ValueError('declared retained index required')
    directory = root/('tmp' if index == DISPOSABLE else 'outputs')/(SOURCE_RUN+'_benchmark' if index == DISPOSABLE else SOURCE_RUN)
    with np.load(directory/f'block_{index}.npz', allow_pickle=False) as saved:
        # Deliberately do not decompress/read recipient outcomes or dynamics.
        raw = {k: saved[k] for k in ('packets', 'targets', 'source_shifts')}
    validate_panel(index, raw)
    return raw


def validate_panel(index, raw):
    if type(index) is not int or index not in (*INDICES, DISPOSABLE):
        raise ValueError('declared retained index required')
    assert set(raw) == {'packets', 'targets', 'source_shifts'}
    assert raw['packets'].shape == (4, 40, 3, 2048) and raw['packets'].dtype == np.uint8
    assert raw['targets'].shape == (4, 2, 16, 16) and raw['targets'].dtype == np.float64
    assert raw['source_shifts'].shape == (4, 3, 2) and raw['source_shifts'].dtype == np.int64
    for target in raw['targets']:
        np.testing.assert_array_equal(target, targets())
    assert np.all((raw['source_shifts'] >= 0) & (raw['source_shifts'] < 16))
    assert np.all(np.any(raw['source_shifts'] != 0, axis=-1))
    source_index = 514227 if index == DISPOSABLE else index-1000
    for life in range(4):
        for gi in range(3):
            key = hashlib.sha256(f'l20-source-translation-v1:{source_index}:{life}:g{gi+1}:source_shift'.encode()).digest()
            random = np.random.Generator(np.random.PCG64(int.from_bytes(key[:16], 'little')))
            expected = np.asarray(divmod(int(random.integers(1, 256)), 16), dtype=np.int64)
            np.testing.assert_array_equal(raw['source_shifts'][life, gi], expected)


def analyze_panel(index, raw, library=None):
    validate_panel(index, raw)
    library = bank() if library is None else library
    rows, maps, maximum = [], [], 0.
    cache = {}
    for life in range(4):
        for role, kind in CASES:
            for gi in range(3):
                packet = raw['packets'][life, SOURCE_CASES.index((role, kind)), gi].tobytes()
                if packet not in cache:
                    features = byte_features(packet)
                    scores = correlations(packet, library)
                    error = fft_check(packet, scores)
                    cache[packet] = features, scores, error
                features, scores, error = cache[packet]; maximum = max(maximum, error)
                expected = expected_offset(kind, raw['source_shifts'][life, gi])
                rows.append(dict(index=index, life=life, role=role, kind=kind, stratum=gi+1,
                    **features, **interpret(scores, role, expected)))
                maps.append(scores)
    assert len(rows) == 288
    return rows, np.stack(maps), maximum


def statistics(rows):
    result = {}
    for key in rows[0]:
        if key in ('index', 'life', 'role', 'kind', 'stratum', 'packet_sha256', 'expected_offset'):
            continue
        selected = [r for r in rows if type(r[key]) in (bool, int, float)]
        if not selected:
            result[key] = dict(n=0)
            continue
        values = np.asarray([r[key] for r in selected], dtype=np.float64)
        entry = dict(n=len(selected), mean=float(values.mean()), minimum=float(values.min()),
            maximum=float(values.max()), block_means=[float(np.mean([r[key] for r in selected if r['index'] == i]))
                                                     for i in sorted({r['index'] for r in selected})])
        if all(type(r[key]) is bool for r in selected):
            entry['true_count'] = sum(r[key] for r in selected)
        result[key] = entry
    return result


def summarize(rows, errors):
    assert len(rows) == 2304
    assert len({(r['index'], r['life'], r['role'], r['kind'], r['stratum']) for r in rows}) == 2304
    assert [r['index'] for r in errors] == list(INDICES)
    return dict(schema='l20_address_ambiguity_audit_v1', decision='D129',
        status='DESCRIPTIVE_AUDIT_COMPLETE', post_hoc=True, independent_confirmation=False,
        new_trajectories=0, new_reader_paths=0, fitted_decoder=False, reader_outcomes_used=False,
        source_run=SOURCE_RUN, packet_bytes=2048, rows=2304, source_contexts=192,
        unique_packets=len({r['packet_sha256'] for r in rows}), blocks=8, lives_per_block=4, strata_reused=3,
        cases=[list(c) for c in CASES], geometry=template_geometry(),
        gauge=gauge_check(encode(np.arange(256, dtype=np.float64).reshape(16, 16))),
        packet_only_features=['mean', 'std', 'row_mean_variance_fraction', 'column_mean_variance_fraction',
                              'exact_self_symmetries', 'nearest_nonidentity_relative_rms'],
        template_access='two supplied canonical patterns, all 256 shifts; not learned',
        evaluation_only=['true_role', 'saved_source_shift', 'route_identity'],
        tie_atol=ATOL, tie_rule='retain all maxima within numerical tolerance; never argmax-select one offset',
        intervals=None, qualification_gate=None, automatic_successor=False,
        inference_unit='eight retained blocks; all rows are descriptive and previously observed, not fresh n',
        groups=[dict(role=role, kind=kind, statistics=statistics([r for r in rows if (r['role'], r['kind']) == (role, kind)]))
                for role, kind in CASES], score_check_max_abs=max(r['fft_max_abs'] for r in errors),
        limitations=['no standalone proof of exact-shift impossibility for noisy D127 records',
                     'unique noisy texture is not proof of an identifiable historical origin',
                     'ideal shift ceilings assume the specified template and shift prior',
                     'static template fit is not fresh-reader performance or inherited address learning'])


def source_inputs(root):
    """Flat pinned D128 closure; never call its dynamics or ancestral runners."""
    u, _ = io_helpers()
    run, out = root/'runs'/SOURCE_RUN, root/'outputs'/SOURCE_RUN
    assert sha256_file(run/'COMPLETE.json') == SOURCE_COMPLETE
    complete, manifest = u.read_json(run/'COMPLETE.json'), u.read_json(run/'MANIFEST.json')
    assert complete['status'] == 'COMPLETE' and u.read_json(run/'STATUS.json') == complete
    assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
    assert sha256_file(run/'MANIFEST.json') == complete['manifest_sha256']
    inputs, outputs = [Path(x) for x in manifest['input_sha256']], [Path(x) for x in complete['output_sha256']]
    assert u.hashes(inputs) == manifest['input_sha256']
    assert u.hashes(outputs) == complete['output_sha256'] and len(outputs) == 19
    assert sha256_file(out/'output_hashes.sha256') == complete['hash_file_sha256']
    assert (out/'output_hashes.sha256').read_text() == u.hash_text(complete['output_sha256'])
    assert {p.name for p in out.iterdir()} == {p.name for p in outputs} | {'output_hashes.sha256'}
    paths = inputs+outputs+[run/n for n in ('MANIFEST.json', 'COMPLETE.json', 'STATUS.json')]
    paths += [out/'output_hashes.sha256', WS/'reviews/L20_INVERSE_ADDRESS_2026-09-15.md']
    paths += [WS/n for n in SCIENCE]
    return sorted(set(paths))


def test_report(path, root):
    u, _ = io_helpers(); path = u.require_beneath(path, root/'logs')
    assert path.name.startswith('d129_') and path.suffix == '.xml' and not path.is_symlink()
    tree = ET.parse(path).getroot(); cases = tree.findall('.//testcase')
    assert cases and not any(tree.findall('.//'+k) for k in ('failure', 'error', 'skipped'))
    current = [c for c in cases if c.get('classname', '').endswith('test_l20_address_ambiguity')]
    assert len(current) >= 280 and len({(c.get('classname'), c.get('name')) for c in cases}) == len(cases)
    names = {c.get('name', '').split('[', 1)[0] for c in current}
    required = {'test_geometry', 'test_all_ideal_shifts', 'test_gauge_alias', 'test_template_free_features',
        'test_features_translation_invariant', 'test_independent_fft', 'test_no_offset_selection',
        'test_family_tie', 'test_useful_phase_not_exact_shift', 'test_disposable_panel',
        'test_no_dynamics', 'test_no_outcome_loading', 'test_source_hashes', 'test_panel_corruption',
        'test_byte_corruption', 'test_score_corruption', 'test_summary_corruption', 'test_external_roundtrip',
        'test_resource_guards', 'test_reservation_guard', 'test_long_forecast_guard'}
    assert required <= names
    assert {c.get('name') for c in current if c.get('name', '').startswith('test_all_ideal_shifts[')} == {
        f'test_all_ideal_shifts[{i}]' for i in range(256)}
    duration = max(float(c.get('time', '0')) for c in current if c.get('name') == 'test_disposable_panel')
    return dict(path=str(path), tests=len(cases), new_tests=len(current), failed=0, skipped=0,
        disposable_panel_seconds=duration, forecast_seconds=32*duration+120)


def inputs_checked(root, report):
    u, _ = io_helpers()
    return u.hashes(source_inputs(root)+[report])


def analyze(root):
    rows, maps, verification = [], [], []
    for index in INDICES:
        panel, scores, error = analyze_panel(index, load_panel(index, root))
        rows.extend(panel); maps.append(scores)
        verification.append(dict(index=index, records=len(panel), fft_max_abs=error))
    return rows, np.concatenate(maps), summarize(rows, verification), verification


def saved_check(root, complete=True):
    u, preflight = io_helpers(); preflight(root, False)
    directory = root/'outputs'/RUN_ID
    expected_names = set(OUTPUTS) | ({'COMPLETE.json'} if complete else set())
    assert {p.name for p in directory.iterdir()} == expected_names
    inputs = u.read_json(directory/'INPUTS.json'); report = Path(inputs['test_proof']['path'])
    assert inputs['input_sha256'] == inputs_checked(root, report)
    assert inputs['test_proof'] == test_report(report, root)
    assert inputs['environment'] == environment_manifest()
    rows = u.read_json(directory/'records.json'); summary = u.read_json(directory/'summary.json')
    verification = u.read_json(directory/'verification.json')
    with np.load(directory/'scores.npz', allow_pickle=False) as saved:
        assert saved.files == ['correlations']
        maps = saved['correlations']
    rebuilt, expected, s, checks = analyze(root)
    assert rows == rebuilt and summary == s and verification == checks
    np.testing.assert_array_equal(maps, expected)
    assert maps.shape == (2304, 2, 16, 16)
    if complete:
        marker = u.read_json(directory/'COMPLETE.json')
        assert marker['status'] == 'COMPLETE' and marker['new_trajectories'] == 0
        assert marker['output_sha256'] == u.hashes([directory/n for n in OUTPUTS])
        assert marker['output_bytes_without_sentinel'] == sum((directory/n).stat().st_size for n in OUTPUTS)
        assert sum(p.stat().st_size for p in directory.iterdir()) < BUDGET
    return dict(passes=True, records=len(rows), correlations=int(maps.size),
        input_hashes=len(inputs['input_sha256']), output_hashes=len(OUTPUTS) if complete else 0,
        independent_fft_max_abs=s['score_check_max_abs'], new_trajectories=0, decoder_trained=False)


def execute(root, report):
    u, preflight = io_helpers(); preflight(root)
    proof = test_report(report, root)
    assert proof['forecast_seconds'] <= 600, 'forecast exceeds short-audit scope; a detached design is required before execution'
    directory = root/'outputs'/RUN_ID
    if directory.exists():
        raise FileExistsError('single-use audit identity already exists')
    inputs = inputs_checked(root, report)
    directory.mkdir(); start = time.monotonic()
    try:
        u.write_json(directory/'INPUTS.json', dict(started_utc=utc_now(), input_sha256=inputs,
            test_proof=proof, environment=environment_manifest(), git_head=git_head(WS),
            post_hoc=True, known_outcomes=True, new_trajectories=0, new_reader_paths=0,
            decoder_trained=False, cpu_affinity=preflight(root), workers=1, output_budget=BUDGET,
            protocol=SCIENCE[-1], source_complete_sha256=SOURCE_COMPLETE), root)
        rows, scores, summary, verification = analyze(root)
        u.write_json(directory/'records.json', rows, root)
        u.write_npz(directory/'scores.npz', dict(correlations=scores), root)
        u.write_json(directory/'summary.json', summary, root)
        u.write_json(directory/'verification.json', verification, root)
        checked = saved_check(root, complete=False)
        size = sum(p.stat().st_size for p in directory.iterdir())
        assert size+65536 < BUDGET
        assert inputs == inputs_checked(root, report)
        preflight(root, False)
        complete = dict(status='COMPLETE', completed_utc=utc_now(), elapsed_seconds=time.monotonic()-start,
            output_sha256=u.hashes([directory/n for n in OUTPUTS]), output_bytes_without_sentinel=size,
            new_trajectories=0, automatic_successor=False, saved_audit=checked)
        u.write_json(directory/'COMPLETE.json', complete, root)
        print(json.dumps(dict(status='COMPLETE', elapsed_seconds=complete['elapsed_seconds'],
            output_bytes_without_sentinel=size, saved_audit=checked), indent=2), flush=True)
    except Exception as error:
        u.failure(directory, error, root)
        raise


def main():
    if sys.flags.optimize:
        raise RuntimeError('assertions must remain enabled')
    from laws_confirmation.io import external_root
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root', type=Path, default=DEFAULT_EXTERNAL_ROOT)
    parser.add_argument('--test-report', type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--execute', action='store_true'); mode.add_argument('--audit', action='store_true')
    args = parser.parse_args(); root = external_root(args.external_root)
    if args.execute != (args.test_report is not None):
        parser.error('--test-report required only for execute')
    if args.execute:
        execute(root, args.test_report)
    else:
        print(json.dumps(saved_check(root), indent=2))


if __name__ == '__main__':
    main()
