"""Counterexamples and failure checks for the new causal paired assay."""
import copy
import inspect
import numpy as np
import pytest
from study import C, P, e, ev, read, cached_runner, repair, require
import actions
import analysis
import paired
import run
import verify
from fixtures import panel


def short_reader(monkeypatch):
    for cfg in (C['reader'], P['reader'], e.DESIGN['reader']):
        for name, value in dict(read_steps=24, settling_steps=12, observe_steps=4).items():
            monkeypatch.setitem(cfg, name, value)


def test_prior_closeout_and_complete_fixed_cache():
    assert read(run.ROOT / 'context/02_DECISION.json')['status'] == 'BOUNDED_PILOT_CLOSED'
    assert read(run.ROOT / 'context/03_VERIFICATION.json')['status'] == 'PASS'
    rows, predictions, packets = cached_runner.check_cache()
    assert len(rows) == len(packets) == 63 and len(predictions) == 126
    assert {r['block'] for r in rows} == set(range(16))
    assert C['resources']['hard_wall_seconds'] == 3600
    assert not C['resources']['automatic_extension']
    assert C['future']['namespace'] != P['forcing']['future_namespace']


def test_repair_known_missing_edge_and_empty_history_limit():
    random = np.random.default_rng(92040)
    signs = 1 - 2 * random.integers(0, 2, (16, 16))
    signs[e.PORTS[0]] = 1
    original = np.stack((signs * np.roll(signs, -1, 1), signs * np.roll(signs, -1, 0))).astype(float)
    erased = original.copy(); erased[0, 5, 5] = 0
    fixed, receipt, _ = actions.checked_repair(erased)
    assert fixed.tobytes() == original.tobytes() and receipt['added_edges'] == 1
    empty = np.zeros((2, 16, 16))
    unchanged, stats, _ = actions.checked_repair(empty)
    assert unchanged.tobytes() == empty.tobytes() and stats['added_edges'] == 0
    assert list(inspect.signature(repair.recipient_repair).parameters) == ['outgoing', 'options']


def test_observed_edges_preserved_under_frustration():
    random = np.random.default_rng(9888)
    packet = random.uniform(-1, 1, (2, 16, 16)); packet[:, 4:7, 4:7] = 0
    saved = packet.copy()
    fixed, receipt, _ = actions.checked_repair(packet)
    assert fixed[packet != 0].tobytes() == saved[packet != 0].tobytes()
    assert packet.tobytes() == saved.tobytes() and receipt['independent_check']


def test_weighted_rescue_minus_harm_and_zero_variance_caution():
    rows, predictions, outcomes, _ = panel()
    result = analysis.analyze(rows, predictions, outcomes)
    verify.evaluate(rows, predictions, outcomes, result)
    for regime in ('matched', 'independent'):
        value = result['regimes'][regime]
        assert value['primary']['block_values'] == [.5, -.25]
        assert value['primary']['mean'] == .125
        assert value['events']['counts'] == dict(rescue=1, harm=1, both_pass=0, neither_pass=5)
        assert value['events']['fractions']['rescue'] == .25
        assert value['events']['fractions']['harm'] == .125
    assert analysis.interval([0., 0.])['signal'] == 'UNRESOLVED'
    assert analysis.interval([1., 1.])['signal'] == 'UNRESOLVED'
    assert analysis.interval([-.25, -.5, -.75, -1.])['signal'] == 'NEGATIVE_SIGNAL'


@pytest.mark.parametrize('mutation', ['duplicate', 'missing', 'nonbinary', 'changed_benefit', 'swapped_rescue_harm', 'changed_calibration'])
def test_incomplete_or_corrupt_pair_analysis_rejected(mutation):
    rows, forecasts, outcomes, _ = panel()
    result = analysis.analyze(rows, forecasts, outcomes)
    if mutation == 'duplicate': outcomes.append(copy.deepcopy(outcomes[0]))
    elif mutation == 'missing': outcomes.pop()
    elif mutation == 'nonbinary': outcomes[0]['repaired'] = 2
    elif mutation == 'changed_benefit': result['regimes']['matched']['primary']['mean'] += .1
    elif mutation == 'swapped_rescue_harm':
        events = result['regimes']['matched']['events']['fractions']
        events['rescue'], events['harm'] = events['harm'], events['rescue']
    else: result['control_forecasts']['regimes']['matched']['calibration']['candidate'][7]['observed_fraction'] += .1
    with pytest.raises((ValueError, ArithmeticError)):
        verify.evaluate(rows, forecasts, outcomes, result)


def test_risk_is_not_repair_benefit():
    # Exact binary joint distributions: failure-prone cases can be less useful
    # to repair. This is a counterexample, not empirical data or a fitted model.
    high_risk = dict(neither=.94, rescue=.01, harm=0., both=.05)
    lower_risk = dict(neither=.10, rescue=.30, harm=0., both=.60)
    assert high_risk['neither'] + high_risk['rescue'] > lower_risk['neither'] + lower_risk['rescue']
    assert high_risk['rescue'] - high_risk['harm'] < lower_risk['rescue'] - lower_risk['harm']


def test_coupling_preserves_marginals_and_stage_separation(monkeypatch):
    short_reader(monkeypatch)
    key = [-200, 'synthetic', 0, 0]
    m = paired.environment('qualification', key, 15, 'writer', 'matched')
    i = paired.environment('qualification', key, 15, 'writer', 'independent')
    assert m[0].sum() == 24 and not (m[0] & e.PORTS.any(axis=0)).any()
    assert m[0].tobytes() == i[0].tobytes()
    assert m[1][0].tobytes() == i[1][0].tobytes() == m[1][1].tobytes()
    assert m[2][:, 0].tobytes() == i[2][:, 0].tobytes() == m[2][:, 1].tobytes()
    assert i[2][:, 0].tobytes() != i[2][:, 1].tobytes()
    other = paired.environment('pilot', key, 15, 'writer', 'matched')
    assert m[2].tobytes() != other[2].tobytes()


def test_seal_gate_noop_pair_and_terminal_chain(monkeypatch, tmp_path):
    short_reader(monkeypatch)
    rows, forecasts, _, packets = panel()
    row, packet = rows[1:2], packets[1:2]
    initial = np.repeat(packet[:, None], 2, axis=1)
    path = tmp_path / 'noop'; path.mkdir()
    seal = tmp_path / 'SEAL.json'
    with pytest.raises(ValueError):
        paired.batch(row, initial, row[0]['key'], 'independent', 'qualification', path, run.Guard(path, 20), seal, 'absent')
    ev.write(seal, dict(stage='qualification'))
    receipt, outcomes = paired.batch(row, initial, row[0]['key'], 'independent', 'qualification', path, run.Guard(path, 20), seal, ev.sha(seal))
    checked = verify.continuation(path, row, initial, 'independent', 'qualification', ev.sha(seal), row[0]['key'])
    raw = ev.load(path / 'future.npz', receipt['raw_sha256'])
    assert checked['status'] == 'PASS'
    for name in ('incoming', 'outgoing', 'end'):
        assert raw[name][:, :, 0].tobytes() == raw[name][:, :, 1].tobytes()
    assert raw['windows'][:, :, :, 0].tobytes() == raw['windows'][:, :, :, 1].tobytes()
    assert outcomes[0]['control'] == outcomes[0]['repaired']
    assert raw['g32_packets'].tobytes() == raw['outgoing'][-2].tobytes()
    # The terminal writer output is retained as evidence but never inherited.
    wrong_initial = initial.copy(); wrong_initial[0, 0, 0, 0, 0] = 1
    with pytest.raises(ValueError):
        verify.continuation(path, row, wrong_initial, 'independent', 'qualification', ev.sha(seal), row[0]['key'])


def test_complete_short_pipeline_and_missing_forecast_barrier(monkeypatch, tmp_path):
    short_reader(monkeypatch)
    rows, forecasts, _, packets = panel()
    incomplete = tmp_path / 'incomplete'; incomplete.mkdir()
    with pytest.raises(ValueError):
        run.work(incomplete, rows, forecasts[:-1], packets, run.Guard(incomplete, 60), 'synthetic', stage='qualification')
    assert not (incomplete / 'PANEL_SEAL.json').exists()
    output = tmp_path / 'complete'; output.mkdir()
    result = run.work(output, rows, forecasts, packets, run.Guard(output, 90), 'synthetic', stage='qualification')
    assert result['case_regimes'] == 14 and result['primary_native_reads'] == 532
    assert result['flat_native_reads'] == 152 and result['physical_repair_calls'] == 7
    assert read(output / 'VERIFICATION.json')['status'] == 'PASS'
    seal = read(output / 'PANEL_SEAL.json')
    assert seal['forecasts'] == forecasts and seal['all_actions_and_forecasts_checked_before_any_future']


def test_deadline_prevents_any_further_read(tmp_path):
    with pytest.raises(TimeoutError): run.Guard(tmp_path, 0).check()
