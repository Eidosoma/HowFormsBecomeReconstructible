"""D174 sealed development orchestration around the unchanged D173 cores.

Only pulse models are fitted here. Reference models/forecasts are selected from
their saved future-mean folds. Outcome loading requires a complete checked seal.
"""
from pathlib import Path
import zipfile
import numpy as np
from . import feedback_pulse_run as qualified
from . import feedback_pulse as pulse, feedback_pulse_check as replay
from . import feedback_pulse_models as model, feedback_pulse_models_check as model_check

io = qualified.io
ROOT = io.ROOT
IDS = tuple(range(90000, 90016))
REFERENCES = ('starting', 'one_copy', 'tied:passive')
PANEL_FILES = ('predictions.npz', 'raw_predictions.npz', 'fits.json',
               'summary.json', 'case_losses.npz', 'verification.json')


def load_npz(path, keys=None):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), 'duplicate NPZ member'
        assert all(n.endswith('.npy') and '/' not in n for n in names)
    return io.load_npz(path, keys)


def cohort_ids(cohort):
    if cohort == 'development':
        return IDS
    assert cohort == 'disposable'
    return (514240,)


def source_paths(index, cohort='development'):
    assert index in cohort_ids(cohort)
    if cohort == 'disposable':
        return qualified.source_paths()
    stem = ROOT / 'outputs/l20_extension1_heldout_v1_attempt1' / f'diagnostic_{index}'
    return stem.with_suffix('.npz'), stem.with_suffix('.json')


def load_source(index, cohort):
    array, record = source_paths(index, cohort)
    raw, meta = load_npz(array, qualified.SOURCE_KEYS), io.read_json(record)
    assert meta['index'] == index and len(meta['lives']) == 4
    assert raw['founder_packets'].shape == (4, 2, 2048)
    for life, row in enumerate(meta['lives']):
        assert row['index'] == row['host']['index'] == index and row['life'] == life
        assert row['tag'] == pulse.namespace(cohort, index, life)
        assert row['cohort'] == ('heldout' if cohort == 'development' else 'disposable')
        assert row['cases'] == [list(c) for c in pulse.CASES]
        assert row['branches'] == ['U0', 'U1', 'C1'] and not row['diagnostic_to_lineage']
        assert row['replay']['full_dynamics_replayed']
    return raw, meta


def block_paths(directory, index):
    return directory / f'diagnostic_{index}.npz', directory / f'diagnostic_{index}.json'


def saved_block(directory, index, cohort, full_replay=False):
    original, source_meta = load_source(index, cohort)
    array, record = block_paths(directory, index)
    raw, meta = load_npz(array), io.read_json(record)
    pulse.validate(raw, 4)
    assert set(meta) == {'index', 'cohort', 'lives', 'proofs'}
    assert meta['index'] == index and meta['cohort'] == cohort
    assert len(meta['lives']) == len(meta['proofs']) == 4
    proofs = []
    for life in range(4):
        expected = replay.check_life(qualified.life(raw, life), meta['lives'][life],
            qualified.life(original, life), source_meta['lives'][life], full_replay)
        prior = meta['proofs'][life]
        assert prior['passes'] and prior['full_physics_replayed']
        if not full_replay:
            expected['full_physics_replayed'] = True
            for k in ('initial_reader_max_abs', 'writer_max_abs', 'final_reader_max_abs'):
                assert 0 <= prior[k] <= 1e-10
                expected[k] = prior[k]
        replay.same(expected, prior)
        proofs.append(expected)
    return dict(index=index, passes=True, lives=4, cases=16, diagnostic_cycles=32,
        original_U1_reproductions=16, writer_paths=32, reader_paths=64,
        full_physics_replayed=bool(full_replay), in_memory_full_replay_passed=True,
        maximum_state_residual=max(p[k] for p in proofs for k in
            ('initial_reader_max_abs', 'writer_max_abs', 'final_reader_max_abs')),
        uncompressed_bytes=sum(v.nbytes for v in raw.values()), actual_outcomes_accessed=False)


def write_block(directory, index, cohort):
    original, source_meta = load_source(index, cohort)
    rows, entries, proofs = [], [], []
    for life in range(4):
        source = qualified.life(original, life)
        raw, meta = pulse.simulate_life(source['founder_packets'], source['guide'], cohort, index, life)
        proof = replay.check_life(raw, meta, source, source_meta['lives'][life], True)
        rows.append(raw); entries.append(meta); proofs.append(proof)
    stacked = {k: np.stack([r[k] for r in rows]) for k in pulse.SHAPES}
    array, record = block_paths(directory, index)
    io.write_npz(array, stacked)
    io.write_json(record, dict(index=index, cohort=cohort, lives=entries, proofs=proofs))
    saved = load_npz(array)
    for key in stacked:
        np.testing.assert_array_equal(saved[key], stacked[key])
    return saved_block(directory, index, cohort)


def diagnostic_sources(input_hashes, cohort):
    return {str(p): input_hashes[str(p)] for index in cohort_ids(cohort) for p in source_paths(index, cohort)}


def seal_diagnostics(directory, cohort, freeze_sha256, input_hashes):
    """No future loader is reachable until all expected blocks pass and are sealed."""
    ids = cohort_ids(cohort)
    sources = diagnostic_sources(input_hashes, cohort)
    io.verify_hashes(sources)
    proofs = [saved_block(directory, i, cohort) for i in ids]
    paths = [p for i in ids for p in block_paths(directory, i)]
    payload = dict(schema='d174_diagnostics_seal_v1', cohort=cohort, blocks=list(ids),
        sealed_utc=io.utc_now(), freeze_sha256=freeze_sha256, source_sha256=sources,
        artifact_sha256=io.hashes(paths), proofs=proofs, cases=16 * len(ids),
        diagnostic_cycles=32 * len(ids), new_fits=0, actual_future_arrays_loaded=False)
    io.write_json(directory / 'DIAGNOSTICS_SEALED.json', payload)
    return verify_seal(directory, cohort, freeze_sha256, input_hashes)


def verify_seal(directory, cohort, freeze_sha256, input_hashes):
    seal = io.read_json(directory / 'DIAGNOSTICS_SEALED.json')
    ids = cohort_ids(cohort)
    assert set(seal) == {'schema', 'cohort', 'blocks', 'sealed_utc', 'freeze_sha256',
        'source_sha256', 'artifact_sha256', 'proofs', 'cases', 'diagnostic_cycles', 'new_fits', 'actual_future_arrays_loaded'}
    assert seal['schema'] == 'd174_diagnostics_seal_v1'
    assert seal['cohort'] == cohort and seal['blocks'] == list(ids)
    assert seal['freeze_sha256'] == freeze_sha256 and seal['sealed_utc']
    assert seal['cases'] == 16 * len(ids) and seal['diagnostic_cycles'] == 32 * len(ids)
    assert seal['new_fits'] == 0 and seal['actual_future_arrays_loaded'] is False
    assert seal['source_sha256'] == diagnostic_sources(input_hashes, cohort)
    assert set(seal['artifact_sha256']) == {str(p) for i in ids for p in block_paths(directory, i)}
    assert len(seal['proofs']) == len(ids)
    for index, proof in zip(ids, seal['proofs']):
        assert proof['index'] == index and proof['passes'] and proof['in_memory_full_replay_passed']
        assert proof['lives'] == 4 and proof['cases'] == proof['original_U1_reproductions'] == 16
        assert proof['diagnostic_cycles'] == proof['writer_paths'] == 32 and proof['reader_paths'] == 64
        assert 0 <= proof['maximum_state_residual'] <= 1e-10 and not proof['actual_outcomes_accessed']
    io.verify_hashes(seal['source_sha256']); io.verify_hashes(seal['artifact_sha256'])
    return seal


def normalize_references(cheap, cp, cr, tied, tp, tr, ids):
    """Select target 5 (future_mean), never original target 0 or pilot fits."""
    prediction, raw, fits = {}, {}, {}
    for name in REFERENCES[:2]:
        source = cheap[name]
        assert source['training_targets'] == ['original', 'future0', 'future1', 'future2', 'future3', 'future_mean']
        assert cp[name].shape == cr[name].shape == (6, 3, len(ids), 4, 4)
        prediction[name], raw[name] = cp[name][5].copy(), cr[name][5].copy()
        fits[name] = dict(observer=name, blocks=source['blocks'], alphas=source['alphas'], target='future_mean',
            folds=[dict(validation_block=f['validation_block'], training_blocks=f['training_blocks'], models=f['models'][5])
                   for f in source['folds']])
    name = 'tied:passive'; source = tied[name]
    fits[name] = {k: source[k] for k in ('observer', 'blocks', 'alphas', 'target')}
    fits[name]['folds'] = [{k: f[k] for k in ('validation_block', 'training_blocks', 'models')} for f in source['folds']]
    prediction[name], raw[name] = tp[name].copy(), tr[name].copy()
    for name in REFERENCES:
        record = fits[name]
        assert record['observer'] == name and record['target'] == 'future_mean'
        assert record['blocks'] == list(ids) and record['alphas'] == list(model.ALPHAS)
        assert len(record['folds']) == len(ids)
        for block, fold in enumerate(record['folds']):
            assert fold['validation_block'] == ids[block]
            assert fold['training_blocks'] == list(ids[:block]) + list(ids[block+1:])
            assert len(fold['models']) == 3
        assert prediction[name].shape == raw[name].shape == (3, len(ids), 4, 4)
        assert np.isfinite(raw[name]).all()
        np.testing.assert_array_equal(prediction[name], np.clip(raw[name], -1, 1))
    return prediction, raw, fits


def load_references():
    a, b = ROOT / 'outputs' / io.OLD157, ROOT / 'outputs' / io.OLD160
    return normalize_references(io.read_json(a / 'fits.json'),
        load_npz(a / 'predictions.npz', REFERENCES[:2]), load_npz(a / 'raw_predictions.npz', REFERENCES[:2]),
        io.read_json(b / 'tied_fits.json'), load_npz(b / 'tied_full.npz', ('tied:passive',)),
        load_npz(b / 'tied_full_raw.npz', ('tied:passive',)), IDS)


def development_data(directory, freeze_sha256, input_hashes):
    verify_seal(directory, 'development', freeze_sha256, input_hashes)
    source = ROOT / 'outputs' / io.OLD157 / 'dataset.npz'
    assert io.sha256_file(source) == input_hashes[str(source)]
    # First actual-future array access in the entire development executor.
    saved = load_npz(source, ('start', 'endpoint', 'futures', 'block_ids'))
    np.testing.assert_array_equal(saved['block_ids'], np.array(IDS, np.int64))
    assert saved['endpoint'].shape == (16, 4, 4, 3, 6)
    measured = []
    for b, index in enumerate(IDS):
        raw = load_npz(block_paths(directory, index)[0], ('starting_features', 'diagnostic_features'))
        original = load_npz(source_paths(index)[0], ('diagnostic_features',))
        np.testing.assert_array_equal(saved['endpoint'][b], original['diagnostic_features'])
        np.testing.assert_allclose(raw['starting_features'], saved['start'][b], atol=1e-12, rtol=0)
        np.testing.assert_array_equal(raw['diagnostic_features'][..., 0, :], saved['endpoint'][b, ..., 1, :])
        measured.append(raw['diagnostic_features'][..., 1, :])
    data = dict(start=saved['start'], u0=saved['endpoint'][..., 0, :], u1=saved['endpoint'][..., 1, :],
        pulse=np.stack(measured), futures=saved['futures'], block_ids=saved['block_ids'])
    assert model.validate(data) == 16
    return data


def check_panel(directory, data, old, old_raw, references):
    p = load_npz(directory / 'predictions.npz'); raw = load_npz(directory / 'raw_predictions.npz')
    fits = io.read_json(directory / 'fits.json'); report = io.read_json(directory / 'summary.json')
    losses = load_npz(directory / 'case_losses.npz')
    assert set(old) == set(old_raw) == set(references) == set(REFERENCES)
    for name in REFERENCES:
        np.testing.assert_array_equal(p[name], old[name]); np.testing.assert_array_equal(raw[name], old_raw[name])
        assert fits[name] == references[name], 'reference coefficients must be reused, not refitted'
    return dict(passes=True, fits=model_check.check_fits(data, p, raw, fits),
        scores=model_check.check_summary(data, p, raw, report, losses),
        new_models=48, reused_models=144, reference_refits=0, prospective_evidence=False)


def write_panel(directory, data, old, old_raw, references):
    assert model.validate(data) == 16
    assert data['block_ids'].tolist() in (list(IDS), list(range(16)))
    assert set(old) == set(old_raw) == set(references) == set(REFERENCES)
    io.external(directory); directory.mkdir(parents=True, exist_ok=False)
    p, raw, fits = dict(old), dict(old_raw), dict(references)
    p['tied:pulse'], raw['tied:pulse'], fits['tied:pulse'] = model.fit_observer(data, 'tied:pulse')
    report, losses = model.summarize(data, p, raw)
    io.write_npz(directory / 'predictions.npz', p); io.write_npz(directory / 'raw_predictions.npz', raw)
    io.write_json(directory / 'fits.json', fits); io.write_json(directory / 'summary.json', report)
    io.write_npz(directory / 'case_losses.npz', losses)
    proof = check_panel(directory, data, old, old_raw, references)
    io.write_json(directory / 'verification.json', proof)
    return proof


def synthetic_sources():
    directory = qualified.benchmark_dir()
    data = load_npz(directory / 'synthetic_data.npz')
    assert data['block_ids'].tolist() == list(range(16))
    p = load_npz(directory / 'synthetic_predictions.npz', REFERENCES)
    raw = load_npz(directory / 'synthetic_raw.npz', REFERENCES)
    fits = io.read_json(directory / 'synthetic_fits.json')
    return data, p, raw, {k: fits[k] for k in REFERENCES}
